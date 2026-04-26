"""
Fetch and normalize external datasets used for validation metrics.

Outputs (small, repo-friendly extracts):
- data/external/fema_nri_county.csv
- data/external/mtbs_fire_perimeters.geojson

This script is intentionally scoped to California + packaged county geometries
to keep artifacts small and reproducible for the course project.
"""

from __future__ import annotations

import csv
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]

FEMA_NRI_FEATURE_URL = "https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/National_Risk_Index_Counties/FeatureServer/0/query"
MTBS_MAPSERVER_LAYER_URL = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MTBS_01/MapServer/63/query"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _request_json(url: str, params: Dict[str, Any], *, timeout_s: int = 60) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout_s)
    r.raise_for_status()
    return r.json()


def _iter_offsets(total: int, page_size: int) -> Iterable[int]:
    off = 0
    while off < total:
        yield off
        off += page_size


def fetch_fema_nri_counties_ca(out_csv: Path) -> None:
    """
    Pull county-level NRI composite risk score and composite EAL (total) for CA counties.
    """
    _ensure_dir(out_csv.parent)

    base = {
        "where": "STATEABBRV='CA'",
        "outFields": "STCOFIPS,STATEABBRV,COUNTY,RISK_SCORE,EAL_VALT,RISK_RATNG,NRI_VER",
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 2000,
    }
    # Get count first
    count = _request_json(FEMA_NRI_FEATURE_URL, {**base, "returnCountOnly": "true"}).get("count", 0)
    if not isinstance(count, int) or count <= 0:
        raise RuntimeError(f"Unexpected FEMA NRI count: {count}")

    rows: List[Dict[str, Any]] = []
    for offset in _iter_offsets(count, 2000):
        payload = _request_json(FEMA_NRI_FEATURE_URL, {**base, "resultOffset": offset})
        feats = payload.get("features", [])
        for f in feats:
            attrs = f.get("attributes", {}) or {}
            stco = str(attrs.get("STCOFIPS") or "").strip()
            if not stco:
                continue
            rows.append(
                {
                    "county_fips": stco.zfill(5),
                    "state": attrs.get("STATEABBRV"),
                    "county_name": attrs.get("COUNTY"),
                    "nri_risk": attrs.get("RISK_SCORE"),
                    "nri_eal": attrs.get("EAL_VALT"),
                    "nri_risk_rating": attrs.get("RISK_RATNG"),
                    "nri_version": attrs.get("NRI_VER"),
                }
            )

    df = pd.DataFrame(rows).drop_duplicates("county_fips").sort_values("county_fips")
    if df.empty:
        raise RuntimeError("FEMA NRI query returned no rows.")
    required = {"county_fips", "nri_risk", "nri_eal", "nri_version"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(f"FEMA NRI extract missing required columns: {missing}")
    df.to_csv(out_csv, index=False)


def _county_union_wgs84(county_fips: str) -> Tuple[float, float, float, float, Any]:
    """Load a packaged county blocks geometry and build a union polygon + bbox."""
    county_fips = str(county_fips).strip().zfill(5)
    try:
        import geopandas as gpd
    except Exception as e:
        raise RuntimeError("geopandas is required to build the MTBS clip geometry") from e

    base = REPO_ROOT / "data" / "processed" / "counties" / county_fips
    blocks_path = base / "blocks_validated.geojson"
    if not blocks_path.exists():
        blocks_path = base / "blocks.geojson"
    if not blocks_path.exists():
        raise FileNotFoundError(f"Expected packaged county blocks at {blocks_path}")
    gdf = gpd.read_file(blocks_path)
    if gdf.empty or "geometry" not in gdf.columns:
        raise RuntimeError(f"County {county_fips} blocks file is empty or missing geometry.")

    # Force WGS84 for querying MTBS (layer SR is EPSG:4269; WGS84 compatible for bbox purposes).
    if getattr(gdf, "crs", None) is not None:
        try:
            gdf = gdf.to_crs("EPSG:4326")
        except Exception:
            pass

    union = gdf.geometry.unary_union
    minx, miny, maxx, maxy = gdf.total_bounds
    return float(minx), float(miny), float(maxx), float(maxy), union


def fetch_mtbs_perimeters_for_counties(
    county_fips_list: List[str],
    out_geojson: Path,
    *,
    year_min: int = 2015,
    year_max: int = 2024,
) -> None:
    """Fetch MTBS perimeters intersecting each county bbox, clip to each county union, then merge."""
    _ensure_dir(out_geojson.parent)

    try:
        import geopandas as gpd
    except Exception as e:
        raise RuntimeError("geopandas is required to write MTBS geojson") from e

    merged_parts: List["gpd.GeoDataFrame"] = []
    for county_fips in county_fips_list:
        county_fips = str(county_fips).strip().zfill(5)
        minx, miny, maxx, maxy, county_union = _county_union_wgs84(county_fips)
        geom = f"{minx},{miny},{maxx},{maxy}"

        count_params = {
            "where": "1=1",
            "geometry": geom,
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "returnCountOnly": "true",
            "f": "json",
        }
        count = _request_json(MTBS_MAPSERVER_LAYER_URL, count_params).get("count", 0)
        if not isinstance(count, int) or count < 0:
            raise RuntimeError(f"Unexpected MTBS count for {county_fips}: {count}")

        feats: List[Dict[str, Any]] = []
        base = {
            "where": "1=1",
            "geometry": geom,
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "FIRE_ID,FIRE_NAME,YEAR,FIRE_TYPE,ACRES",
            "outSR": 4326,
            "f": "geojson",
            "resultRecordCount": 2000,
        }

        if count == 0:
            geo = _request_json(MTBS_MAPSERVER_LAYER_URL, {**base, "resultOffset": 0})
            feats = list(geo.get("features", []) or [])
        else:
            for offset in _iter_offsets(count, 2000):
                geo = _request_json(MTBS_MAPSERVER_LAYER_URL, {**base, "resultOffset": offset})
                feats.extend(list(geo.get("features", []) or []))

        if not feats:
            continue

        raw = {"type": "FeatureCollection", "features": feats}
        part = gpd.GeoDataFrame.from_features(raw["features"], crs="EPSG:4326")
        if part.empty:
            continue
        # Filter by year window if present (avoid including extra decades of perimeters).
        if "YEAR" in part.columns:
            yrs = pd.to_numeric(part["YEAR"], errors="coerce")
            part = part[yrs.notna() & (yrs >= int(year_min)) & (yrs <= int(year_max))].copy()
            if part.empty:
                continue
        part["geometry"] = part["geometry"].intersection(county_union)
        part = part[~part["geometry"].is_empty & part["geometry"].notna()].copy()
        if not part.empty:
            merged_parts.append(part)

    if not merged_parts:
        out_geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}, indent=2), encoding="utf-8")
        return

    gdf = pd.concat(merged_parts, ignore_index=True)
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    # De-dupe perimeters by FIRE_ID+YEAR when available.
    if "FIRE_ID" in gdf.columns and "YEAR" in gdf.columns:
        gdf = gdf.drop_duplicates(subset=["FIRE_ID", "YEAR"]).copy()
    gdf.to_file(out_geojson, driver="GeoJSON")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Fetch external validation datasets (FEMA NRI + MTBS).")
    ap.add_argument(
        "--counties",
        default="06007",
        help="Comma-separated 5-digit county FIPS to include in MTBS clip (e.g., 06007,06073)",
    )
    ap.add_argument("--year-min", type=int, default=2015, help="Minimum MTBS YEAR to include.")
    ap.add_argument("--year-max", type=int, default=2024, help="Maximum MTBS YEAR to include.")
    args = ap.parse_args()

    external_dir = REPO_ROOT / "data" / "external"
    _ensure_dir(external_dir)

    fema_out = external_dir / "fema_nri_county.csv"
    mtbs_out = external_dir / "mtbs_fire_perimeters.geojson"
    meta_out = external_dir / "external_validation_manifest.json"
    counties = [str(c).strip().zfill(5) for c in str(args.counties).split(",") if str(c).strip()]

    print(f"[external] Fetching FEMA NRI (CA counties) -> {fema_out}")
    fetch_fema_nri_counties_ca(fema_out)

    print(f"[external] Fetching MTBS perimeters (county clip: {counties}) -> {mtbs_out}")
    fetch_mtbs_perimeters_for_counties(counties, mtbs_out, year_min=int(args.year_min), year_max=int(args.year_max))

    # Lightweight manifest so experiments can be audited and refreshed reproducibly.
    def sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fema_nri": {
            "source_url": FEMA_NRI_FEATURE_URL,
            "where": "STATEABBRV='CA'",
            "out_fields": ["STCOFIPS", "STATEABBRV", "COUNTY", "RISK_SCORE", "EAL_VALT", "RISK_RATNG", "NRI_VER"],
            "path": str(fema_out.relative_to(REPO_ROOT)),
            "sha256": sha256(fema_out) if fema_out.exists() else None,
        },
        "mtbs": {
            "source_url": MTBS_MAPSERVER_LAYER_URL,
            "county_clip": counties,
            "year_min": int(args.year_min),
            "year_max": int(args.year_max),
            "out_fields": ["FIRE_ID", "FIRE_NAME", "YEAR", "FIRE_TYPE", "ACRES"],
            "path": str(mtbs_out.relative_to(REPO_ROOT)),
            "sha256": sha256(mtbs_out) if mtbs_out.exists() else None,
        },
    }
    meta_out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print("[external] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

