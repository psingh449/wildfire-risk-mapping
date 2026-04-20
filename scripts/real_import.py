#!/usr/bin/env python3
"""
Robust real-data importer that writes once to data/real_cache/ (per-county, per-source, per-quantity).

Examples:
  python scripts/real_import.py --county 06007 --all
  python scripts/real_import.py --county 06007 --sources census_pl_2020 acs_2021_5yr
  python scripts/real_import.py --county 06007 --source acs_2021_5yr --quantity poverty
  python scripts/real_import.py --counties 06007 06073 08013 --source census_pl_2020

By default, cached datasets are not re-downloaded if manifest.json exists.
Use --refresh to re-fetch and overwrite.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd
import requests

# Allow running as script from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.real_cache import DatasetRef, normalize_county_fips, split_county_fips, write_dataset
from src.utils.real_data import HTTP_HEADERS


SOURCE_CENSUS_PL_2020 = "census_pl_2020"
SOURCE_ACS_2021_5YR = "acs_2021_5yr"
SOURCE_WHP = "whp"
SOURCE_NLCD = "nlcd"
SOURCE_HIFLD = "hifld"
SOURCE_OSM = "osm"

Q_POPULATION = "population"
Q_HOUSING = "housing"
Q_POVERTY = "poverty"
Q_POVERTY_TRACT = "poverty_tract"
Q_ELDERLY = "elderly"
Q_VEHICLE_ACCESS = "vehicle_access"
Q_VEHICLE_ACCESS_TRACT = "vehicle_access_tract"
Q_MEDIAN_HOME_VALUE = "median_home_value"
Q_WILDFIRE = "wildfire"
Q_VEGETATION = "vegetation"
Q_FOREST_DISTANCE = "forest_distance"
Q_FIRE_STATIONS_DISTANCE = "fire_stations_distance"
Q_HOSPITALS_DISTANCE = "hospitals_distance"
Q_ROADS_ACCESS = "roads_access"


def _zfill_geoid_12(df: pd.DataFrame, col: str = "GEOID") -> None:
    df[col] = df[col].astype(str).str.strip().str.zfill(12)

def _zfill_geoid_11(df: pd.DataFrame, col: str = "GEOID") -> None:
    df[col] = df[col].astype(str).str.strip().str.zfill(11)

def _all_null_measures(df: pd.DataFrame, cols: list[str]) -> bool:
    present = [c for c in cols if c in df.columns]
    if not present:
        return True
    non_null = 0
    for c in present:
        s = pd.to_numeric(df[c], errors="coerce")
        non_null += int(s.notna().sum())
    return non_null == 0


def _response_to_json(resp: requests.Response) -> Any:
    """
    Parse response as JSON; if not possible, raise a helpful error.
    """
    body = (resp.content or b"").strip()
    if not body:
        raise RuntimeError(f"Empty response body (status={resp.status_code}) from {resp.url}")
    try:
        return resp.json()
    except Exception:
        snippet = body[:500].decode("utf-8", errors="replace")
        ctype = resp.headers.get("Content-Type")
        raise RuntimeError(
            "Non-JSON response from Census API. "
            f"status={resp.status_code} content-type={ctype!r} url={resp.url} "
            f"body_snippet={snippet!r}"
        )


def _require_blocks_for_county(county_fips: str) -> Path:
    """
    Non-API datasets are computed from blocks GeoJSON.
    Prefer per-county path: data/processed/counties/{county_fips}/blocks.geojson
    Fallback: data/processed/blocks.geojson
    """
    county_fips = normalize_county_fips(county_fips)
    per_county = Path("data") / "processed" / "counties" / county_fips / "blocks.geojson"
    blocks_path = per_county if per_county.exists() else (Path("data") / "processed" / "blocks.geojson")
    if not blocks_path.exists():
        raise FileNotFoundError(
            f"Missing blocks GeoJSON for {county_fips}. Expected one of:\n"
            f"- {per_county.as_posix()}\n"
            f"- {(Path('data') / 'processed' / 'blocks.geojson').as_posix()}\n"
            "Generate geometry/features for the county first (e.g., run the pipeline) and then retry."
        )
    try:
        # Read just the first feature properties (lightweight)
        import json as _json

        with open(blocks_path, "rb") as f:
            obj = _json.loads(f.read().decode("utf-8", errors="replace"))
        feats = obj.get("features") or []
        if feats:
            props = (feats[0] or {}).get("properties") or {}
            st = str(props.get("STATEFP", "")).zfill(2) if props.get("STATEFP") is not None else ""
            co = str(props.get("COUNTYFP", "")).zfill(3) if props.get("COUNTYFP") is not None else ""
            if st and co:
                if f"{st}{co}" != county_fips:
                    raise RuntimeError(
                        f"{blocks_path.as_posix()} appears to be for county {st}{co}, but you requested {county_fips}. "
                        "Regenerate blocks.geojson for the requested county before importing NLCD/WHP/HIFLD/OSM."
                    )
    except Exception:
        # If parsing fails, we still allow downstream scripts to attempt reading it (they'll error if invalid).
        pass
    return blocks_path


def _run_python_script(script_rel: str) -> dict[str, Any]:
    """
    Run a repo script and capture stdout/stderr for provenance.
    """
    script = Path(script_rel)
    if not script.exists():
        raise FileNotFoundError(f"Missing script: {script_rel}")
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    result = {
        "script": script_rel,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if proc.returncode != 0:
        raise RuntimeError(f"Script failed: {script_rel} (exit={proc.returncode})\\n{proc.stderr or proc.stdout}")
    return result


def _run_python_script_with_args(argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    result = {
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if proc.returncode != 0:
        raise RuntimeError(f"Script failed: {' '.join(argv)} (exit={proc.returncode})\n{proc.stderr or proc.stdout}")
    return result


def _cache_generated_csv(
    *,
    county_fips: str,
    source_id: str,
    quantity_id: str,
    generated_csv_path: str,
    script_rel: str,
    refresh: bool,
    expected_columns: list[str],
) -> None:
    county_fips = normalize_county_fips(county_fips)
    csv_path = Path(generated_csv_path)
    ref = DatasetRef(county_fips=county_fips, source_id=source_id, quantity_id=quantity_id)
    if (not refresh) and ref.manifest_path.exists():
        print(f"SKIP (cached): {ref.manifest_path.as_posix()}")
        return

    # Generate/update the CSV first (scripts write into data/real/)
    # Pass per-county blocks + explicit out path so scripts don’t rely on global defaults.
    blocks_path = _require_blocks_for_county(county_fips)
    argv = [sys.executable, script_rel, "--blocks", str(blocks_path), "--out", generated_csv_path]
    run_meta = _run_python_script_with_args(argv)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Expected generated CSV not found after running {script_rel}: {generated_csv_path}. "
            f"See script stderr in response.json when re-run with --refresh."
        )

    # Read the freshly generated CSV
    df = pd.read_csv(csv_path)
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        raise RuntimeError(f"{generated_csv_path} missing expected columns: {missing}. Found: {list(df.columns)}")
    write_dataset(
        ref,
        df,
        response_json={
            "generated": True,
            "script_run": run_meta,
            "inputs": {
                "blocks_geojson": str(blocks_path.as_posix()),
            },
            "source_csv": generated_csv_path,
        },
        request={"generator": script_rel},
        schema={"columns": list(df.columns), "join_key": "block_id"},
        overwrite=True,
        notes="Generated locally by script; response.json contains script stdout/stderr and inputs.",
    )
    print(f"WROTE: {ref.data_path.as_posix()}")


def _write_if_needed(ref: DatasetRef, df: pd.DataFrame, *, response_json: Any, request: dict, overwrite: bool) -> None:
    if (not overwrite) and ref.manifest_path.exists():
        print(f"SKIP (cached): {ref.manifest_path.as_posix()}")
        return
    out = write_dataset(
        ref,
        df,
        response_json=response_json,
        request=request,
        schema={"columns": list(df.columns), "join_key": "GEOID"},
        overwrite=True,
    )
    print(f"WROTE: {out.as_posix()}")


def import_census_population(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    st, co = split_county_fips(county_fips)
    # Request only the measure; Census returns state/county/tract/block group automatically.
    params = {"get": "P1_001N", "for": "block group:*", "in": f"state:{st} county:{co}"}
    resp = requests.get("https://api.census.gov/data/2020/dec/pl", params=params, timeout=180, headers=HTTP_HEADERS)
    resp.raise_for_status()
    raw = _response_to_json(resp)
    header = raw[0]
    rows = raw[1:]
    idx = {name: i for i, name in enumerate(header)}
    out_rows = []
    for r in rows:
        geoid = f"{str(r[idx['state']]).zfill(2)}{str(r[idx['county']]).zfill(3)}{str(r[idx['tract']]).zfill(6)}{str(r[idx['block group']]).strip()}"
        out_rows.append((geoid, int(r[idx["P1_001N"]]) if "P1_001N" in idx else int(r[0])))
    df = pd.DataFrame(out_rows, columns=["GEOID", "population"])
    _zfill_geoid_12(df, "GEOID")
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_CENSUS_PL_2020, quantity_id=Q_POPULATION)
    _write_if_needed(ref, df, response_json=raw, request={"api": resp.url.split("?")[0], "params": params}, overwrite=refresh)


def import_census_housing(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    st, co = split_county_fips(county_fips)
    params = {"get": "H1_001N", "for": "block group:*", "in": f"state:{st} county:{co}"}
    resp = requests.get("https://api.census.gov/data/2020/dec/pl", params=params, timeout=180, headers=HTTP_HEADERS)
    resp.raise_for_status()
    raw = _response_to_json(resp)
    header = raw[0]
    rows = raw[1:]
    idx = {name: i for i, name in enumerate(header)}
    out_rows = []
    for r in rows:
        geoid = f"{str(r[idx['state']]).zfill(2)}{str(r[idx['county']]).zfill(3)}{str(r[idx['tract']]).zfill(6)}{str(r[idx['block group']]).strip()}"
        out_rows.append((geoid, int(r[idx["H1_001N"]]) if "H1_001N" in idx else int(r[0])))
    df = pd.DataFrame(out_rows, columns=["GEOID", "housing_units"])
    _zfill_geoid_12(df, "GEOID")
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_CENSUS_PL_2020, quantity_id=Q_HOUSING)
    _write_if_needed(ref, df, response_json=raw, request={"api": resp.url.split("?")[0], "params": params}, overwrite=refresh)


def import_acs_poverty(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    st, co = split_county_fips(county_fips)
    inc = f"state:{st} county:{co}"
    params = {"get": "B17001_002E,B17001_001E", "for": "block group:*", "in": inc}
    resp = requests.get("https://api.census.gov/data/2021/acs/acs5", params=params, timeout=180, headers=HTTP_HEADERS)
    resp.raise_for_status()
    raw = _response_to_json(resp)
    header = raw[0]
    rows = raw[1:]
    df = pd.DataFrame(rows, columns=header)
    if "GEOID" not in df.columns:
        df["GEOID"] = (
            df["state"].astype(str).str.zfill(2)
            + df["county"].astype(str).str.zfill(3)
            + df["tract"].astype(str).str.zfill(6)
            + df["block group"].astype(str).str.strip()
        )
    _zfill_geoid_12(df, "GEOID")
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_ACS_2021_5YR, quantity_id=Q_POVERTY)
    _write_if_needed(ref, df, response_json=raw, request={"api": resp.url.split("?")[0], "params": params}, overwrite=refresh)

    # If ACS returns all-null estimates at block-group level, also cache tract-level as a defensible fallback.
    if _all_null_measures(df, ["B17001_002E", "B17001_001E"]):
        params_tr = {"get": "B17001_002E,B17001_001E", "for": "tract:*", "in": inc}
        resp_tr = requests.get("https://api.census.gov/data/2021/acs/acs5", params=params_tr, timeout=180, headers=HTTP_HEADERS)
        resp_tr.raise_for_status()
        raw_tr = _response_to_json(resp_tr)
        header_tr = raw_tr[0]
        rows_tr = raw_tr[1:]
        df_tr = pd.DataFrame(rows_tr, columns=header_tr)
        if "GEOID" not in df_tr.columns:
            df_tr["GEOID"] = (
                df_tr["state"].astype(str).str.zfill(2)
                + df_tr["county"].astype(str).str.zfill(3)
                + df_tr["tract"].astype(str).str.zfill(6)
            )
        _zfill_geoid_11(df_tr, "GEOID")
        ref_tr = DatasetRef(county_fips=county_fips, source_id=SOURCE_ACS_2021_5YR, quantity_id=Q_POVERTY_TRACT)
        _write_if_needed(ref_tr, df_tr, response_json=raw_tr, request={"api": resp_tr.url.split('?')[0], "params": params_tr}, overwrite=refresh)


def import_acs_elderly(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    st, co = split_county_fips(county_fips)
    inc = f"state:{st} county:{co}"
    fields = ["B01001_001E"] + [f"B01001_{i:03d}E" for i in range(20, 26)]
    params = {"get": ",".join(fields), "for": "block group:*", "in": inc}
    resp = requests.get("https://api.census.gov/data/2021/acs/acs5", params=params, timeout=180, headers=HTTP_HEADERS)
    resp.raise_for_status()
    raw = _response_to_json(resp)
    header = raw[0]
    rows = raw[1:]
    df = pd.DataFrame(rows, columns=header)
    df["GEOID"] = (
        df["state"].astype(str).str.zfill(2)
        + df["county"].astype(str).str.zfill(3)
        + df["tract"].astype(str).str.zfill(6)
        + df["block group"].astype(str).str.strip()
    )
    _zfill_geoid_12(df, "GEOID")
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_ACS_2021_5YR, quantity_id=Q_ELDERLY)
    _write_if_needed(ref, df, response_json=raw, request={"api": resp.url.split("?")[0], "params": params}, overwrite=refresh)


def import_acs_vehicle_access(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    st, co = split_county_fips(county_fips)
    inc = f"state:{st} county:{co}"
    params = {"get": "B08201_002E,B08201_001E", "for": "block group:*", "in": inc}
    resp = requests.get("https://api.census.gov/data/2021/acs/acs5", params=params, timeout=180, headers=HTTP_HEADERS)
    resp.raise_for_status()
    raw = _response_to_json(resp)
    header = raw[0]
    rows = raw[1:]
    df = pd.DataFrame(rows, columns=header)
    df["GEOID"] = (
        df["state"].astype(str).str.zfill(2)
        + df["county"].astype(str).str.zfill(3)
        + df["tract"].astype(str).str.zfill(6)
        + df["block group"].astype(str).str.strip()
    )
    _zfill_geoid_12(df, "GEOID")
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_ACS_2021_5YR, quantity_id=Q_VEHICLE_ACCESS)
    _write_if_needed(ref, df, response_json=raw, request={"api": resp.url.split("?")[0], "params": params}, overwrite=refresh)

    # If ACS returns all-null estimates at block-group level, also cache tract-level as a defensible fallback.
    if _all_null_measures(df, ["B08201_002E", "B08201_001E"]):
        params_tr = {"get": "B08201_002E,B08201_001E", "for": "tract:*", "in": inc}
        resp_tr = requests.get("https://api.census.gov/data/2021/acs/acs5", params=params_tr, timeout=180, headers=HTTP_HEADERS)
        resp_tr.raise_for_status()
        raw_tr = _response_to_json(resp_tr)
        header_tr = raw_tr[0]
        rows_tr = raw_tr[1:]
        df_tr = pd.DataFrame(rows_tr, columns=header_tr)
        df_tr["GEOID"] = (
            df_tr["state"].astype(str).str.zfill(2)
            + df_tr["county"].astype(str).str.zfill(3)
            + df_tr["tract"].astype(str).str.zfill(6)
        )
        _zfill_geoid_11(df_tr, "GEOID")
        ref_tr = DatasetRef(county_fips=county_fips, source_id=SOURCE_ACS_2021_5YR, quantity_id=Q_VEHICLE_ACCESS_TRACT)
        _write_if_needed(ref_tr, df_tr, response_json=raw_tr, request={"api": resp_tr.url.split('?')[0], "params": params_tr}, overwrite=refresh)


def import_acs_median_home_value(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    st, co = split_county_fips(county_fips)
    inc = f"state:{st} county:{co}"
    params = {"get": "B25077_001E", "for": "block group:*", "in": inc}
    resp = requests.get("https://api.census.gov/data/2021/acs/acs5", params=params, timeout=180, headers=HTTP_HEADERS)
    resp.raise_for_status()
    raw = _response_to_json(resp)
    header = raw[0]
    rows = raw[1:]
    df = pd.DataFrame(rows, columns=header)
    df["GEOID"] = (
        df["state"].astype(str).str.zfill(2)
        + df["county"].astype(str).str.zfill(3)
        + df["tract"].astype(str).str.zfill(6)
        + df["block group"].astype(str).str.strip()
    )
    _zfill_geoid_12(df, "GEOID")
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_ACS_2021_5YR, quantity_id=Q_MEDIAN_HOME_VALUE)
    _write_if_needed(ref, df, response_json=raw, request={"api": resp.url.split("?")[0], "params": params}, overwrite=refresh)


def import_whp_wildfire(county_fips: str, *, refresh: bool) -> None:
    _require_blocks_for_county(county_fips)
    whp_dir = Path("data") / "geospatial" / "whp"
    has_whp = any(whp_dir.glob("**/*.tif")) or any(whp_dir.glob("**/*.tiff"))
    if not has_whp:
        print(
            "SKIP (missing raster): whp/wildfire. "
            f"No WHP GeoTIFF found under {whp_dir.as_posix()}. "
            "Download/extract the WHP raster there, then re-run with `--source whp --refresh`."
        )
        return
    # Generates data/real/whp_zonal_stats.csv with columns: block_id, whp_mean
    _cache_generated_csv(
        county_fips=county_fips,
        source_id=SOURCE_WHP,
        quantity_id=Q_WILDFIRE,
        generated_csv_path="data/real/whp_zonal_stats.csv",
        script_rel="scripts/process_whp_zonal_stats.py",
        refresh=refresh,
        expected_columns=["block_id", "whp_mean"],
    )


def import_nlcd_vegetation(county_fips: str, *, refresh: bool) -> None:
    _require_blocks_for_county(county_fips)
    _cache_generated_csv(
        county_fips=county_fips,
        source_id=SOURCE_NLCD,
        quantity_id=Q_VEGETATION,
        generated_csv_path="data/real/nlcd_vegetation.csv",
        script_rel="scripts/process_nlcd_vegetation.py",
        refresh=refresh,
        expected_columns=["block_id", "nlcd_vegetation"],
    )


def import_nlcd_forest_distance(county_fips: str, *, refresh: bool) -> None:
    _require_blocks_for_county(county_fips)
    _cache_generated_csv(
        county_fips=county_fips,
        source_id=SOURCE_NLCD,
        quantity_id=Q_FOREST_DISTANCE,
        generated_csv_path="data/real/nlcd_forest_distance.csv",
        script_rel="scripts/process_nlcd_forest_distance.py",
        refresh=refresh,
        expected_columns=["block_id", "nlcd_forest_distance"],
    )


def import_hifld_fire_stations_distance(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_HIFLD, quantity_id=Q_FIRE_STATIONS_DISTANCE)
    if (not refresh) and ref.manifest_path.exists():
        print(f"SKIP (cached): {ref.manifest_path.as_posix()}")
        return

    blocks_path = _require_blocks_for_county(county_fips)
    out_dir = Path("data") / "real"
    argv = [sys.executable, "scripts/build_hifld_distances_arcgis.py", "--blocks", str(blocks_path), "--out-dir", str(out_dir)]
    run_meta = _run_python_script_with_args(argv)

    src_csv = out_dir / "fire_station_dist.csv"
    if not src_csv.exists():
        raise FileNotFoundError(f"Expected generated CSV not found: {src_csv.as_posix()}")
    df = pd.read_csv(src_csv)
    for c in ("block_id", "fire_station_dist"):
        if c not in df.columns:
            raise RuntimeError(f"{src_csv.as_posix()} missing column {c}. Found: {list(df.columns)}")
    write_dataset(
        ref,
        df,
        response_json={"generated": True, "script_run": run_meta, "inputs": {"blocks_geojson": blocks_path.as_posix()}},
        request={"generator": "scripts/build_hifld_distances_arcgis.py"},
        schema={"columns": list(df.columns), "join_key": "block_id"},
        overwrite=True,
    )
    print(f"WROTE: {ref.data_path.as_posix()}")


def import_hifld_hospitals_distance(county_fips: str, *, refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    ref = DatasetRef(county_fips=county_fips, source_id=SOURCE_HIFLD, quantity_id=Q_HOSPITALS_DISTANCE)
    if (not refresh) and ref.manifest_path.exists():
        print(f"SKIP (cached): {ref.manifest_path.as_posix()}")
        return

    blocks_path = _require_blocks_for_county(county_fips)
    out_dir = Path("data") / "real"
    argv = [sys.executable, "scripts/build_hifld_distances_arcgis.py", "--blocks", str(blocks_path), "--out-dir", str(out_dir)]
    run_meta = _run_python_script_with_args(argv)

    src_csv = out_dir / "hospital_dist.csv"
    if not src_csv.exists():
        raise FileNotFoundError(f"Expected generated CSV not found: {src_csv.as_posix()}")
    df = pd.read_csv(src_csv)
    for c in ("block_id", "hospital_dist"):
        if c not in df.columns:
            raise RuntimeError(f"{src_csv.as_posix()} missing column {c}. Found: {list(df.columns)}")
    write_dataset(
        ref,
        df,
        response_json={"generated": True, "script_run": run_meta, "inputs": {"blocks_geojson": blocks_path.as_posix()}},
        request={"generator": "scripts/build_hifld_distances_arcgis.py"},
        schema={"columns": list(df.columns), "join_key": "block_id"},
        overwrite=True,
    )
    print(f"WROTE: {ref.data_path.as_posix()}")


def import_osm_roads_access(county_fips: str, *, refresh: bool) -> None:
    _require_blocks_for_county(county_fips)
    _cache_generated_csv(
        county_fips=county_fips,
        source_id=SOURCE_OSM,
        quantity_id=Q_ROADS_ACCESS,
        generated_csv_path="data/real/road_length.csv",
        script_rel="scripts/process_osm_road_length.py",
        refresh=refresh,
        expected_columns=["block_id", "road_length"],
    )


IMPORTERS: dict[str, dict[str, Callable[[str], None]]] = {
    SOURCE_CENSUS_PL_2020: {
        Q_POPULATION: lambda c, refresh=False: import_census_population(c, refresh=refresh),  # type: ignore[misc]
        Q_HOUSING: lambda c, refresh=False: import_census_housing(c, refresh=refresh),  # type: ignore[misc]
    },
    SOURCE_ACS_2021_5YR: {
        Q_POVERTY: lambda c, refresh=False: import_acs_poverty(c, refresh=refresh),  # type: ignore[misc]
        Q_ELDERLY: lambda c, refresh=False: import_acs_elderly(c, refresh=refresh),  # type: ignore[misc]
        Q_VEHICLE_ACCESS: lambda c, refresh=False: import_acs_vehicle_access(c, refresh=refresh),  # type: ignore[misc]
        Q_MEDIAN_HOME_VALUE: lambda c, refresh=False: import_acs_median_home_value(c, refresh=refresh),  # type: ignore[misc]
    },
    SOURCE_WHP: {
        Q_WILDFIRE: lambda c, refresh=False: import_whp_wildfire(c, refresh=refresh),  # type: ignore[misc]
    },
    SOURCE_NLCD: {
        Q_VEGETATION: lambda c, refresh=False: import_nlcd_vegetation(c, refresh=refresh),  # type: ignore[misc]
        Q_FOREST_DISTANCE: lambda c, refresh=False: import_nlcd_forest_distance(c, refresh=refresh),  # type: ignore[misc]
    },
    SOURCE_HIFLD: {
        Q_FIRE_STATIONS_DISTANCE: lambda c, refresh=False: import_hifld_fire_stations_distance(c, refresh=refresh),  # type: ignore[misc]
        Q_HOSPITALS_DISTANCE: lambda c, refresh=False: import_hifld_hospitals_distance(c, refresh=refresh),  # type: ignore[misc]
    },
    SOURCE_OSM: {
        Q_ROADS_ACCESS: lambda c, refresh=False: import_osm_roads_access(c, refresh=refresh),  # type: ignore[misc]
    },
}


def _all_sources() -> list[str]:
    return list(IMPORTERS.keys())


def _quantities_for_source(source_id: str) -> list[str]:
    return list(IMPORTERS[source_id].keys())


def run_for_county(county_fips: str, *, sources: Iterable[str], quantities: Optional[Iterable[str]], refresh: bool) -> None:
    county_fips = normalize_county_fips(county_fips)
    for src in sources:
        if src not in IMPORTERS:
            raise ValueError(f"Unknown source: {src}. Known: {sorted(IMPORTERS)}")
        qs = list(quantities) if quantities is not None else _quantities_for_source(src)
        for q in qs:
            if q not in IMPORTERS[src]:
                raise ValueError(f"Unknown quantity {q!r} for source {src!r}. Known: {sorted(IMPORTERS[src])}")
            print(f"IMPORT {county_fips} :: {src}/{q}")
            IMPORTERS[src][q](county_fips, refresh=refresh)  # type: ignore[call-arg]


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--county", help="5-digit county FIPS like 06007")
    g.add_argument("--counties", nargs="+", help="one or more 5-digit county FIPS values")

    p.add_argument("--all", action="store_true", help="import all supported sources/quantities")
    p.add_argument("--sources", nargs="+", help="import all quantities for these sources")
    p.add_argument("--source", help="import from a single source")
    p.add_argument("--quantity", help="import a single quantity (requires --source)")
    p.add_argument("--refresh", action="store_true", help="re-download even if cached")

    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.quantity and not args.source:
        raise SystemExit("--quantity requires --source")

    counties: list[str] = []
    if args.county:
        counties = [args.county]
    elif args.counties:
        counties = list(args.counties)

    if args.all:
        sources = _all_sources()
        quantities = None
    elif args.sources:
        sources = args.sources
        quantities = None
    elif args.source and args.quantity:
        sources = [args.source]
        quantities = [args.quantity]
    elif args.source:
        sources = [args.source]
        quantities = None
    else:
        raise SystemExit("Must provide one of: --all, --sources, --source [--quantity]")

    for c in counties:
        run_for_county(c, sources=sources, quantities=quantities, refresh=args.refresh)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

