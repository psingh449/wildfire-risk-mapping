"""
Fetch and normalize external datasets used for validation metrics.

Outputs (small, repo-friendly extracts):
- data/external/fema_nri_county.csv
- data/external/mtbs_fire_perimeters.geojson

This script is intentionally scoped to California + the packaged Butte county geometry
to keep artifacts small and reproducible for the course project.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
    df.to_csv(out_csv, index=False)


def _butte_county_union_wgs84() -> Tuple[float, float, float, float, Any]:
    """
    Load the packaged Butte county blocks geometry and build a union polygon + bbox.
    """
    try:
        import geopandas as gpd
    except Exception as e:
        raise RuntimeError("geopandas is required to build the MTBS clip geometry") from e

    blocks_path = REPO_ROOT / "data" / "processed" / "counties" / "06007" / "blocks.geojson"
    if not blocks_path.exists():
        raise FileNotFoundError(f"Expected packaged Butte blocks at {blocks_path}")
    gdf = gpd.read_file(blocks_path)
    if gdf.empty or "geometry" not in gdf.columns:
        raise RuntimeError("Butte blocks.geojson is empty or missing geometry.")

    # Force WGS84 for querying MTBS (layer SR is EPSG:4269; WGS84 compatible for bbox purposes).
    if getattr(gdf, "crs", None) is not None:
        try:
            gdf = gdf.to_crs("EPSG:4326")
        except Exception:
            pass

    union = gdf.geometry.unary_union
    minx, miny, maxx, maxy = gdf.total_bounds
    return float(minx), float(miny), float(maxx), float(maxy), union


def fetch_mtbs_perimeters_butte(out_geojson: Path) -> None:
    """
    Fetch MTBS burned area boundaries intersecting Butte county bbox, then clip to the county union
    derived from packaged block geometries.
    """
    _ensure_dir(out_geojson.parent)

    try:
        import geopandas as gpd
    except Exception as e:
        raise RuntimeError("geopandas is required to write MTBS geojson") from e

    minx, miny, maxx, maxy, county_union = _butte_county_union_wgs84()

    # ArcGIS geometry envelope: xmin,ymin,xmax,ymax
    geom = f"{minx},{miny},{maxx},{maxy}"

    # Count first (respect 2000 max record count)
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
        raise RuntimeError(f"Unexpected MTBS count: {count}")

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

    # Some ArcGIS servers are picky: include resultOffset even for 0.
    if count == 0:
        geo = _request_json(MTBS_MAPSERVER_LAYER_URL, {**base, "resultOffset": 0})
        feats = list(geo.get("features", []) or [])
    else:
        for offset in _iter_offsets(count, 2000):
            geo = _request_json(MTBS_MAPSERVER_LAYER_URL, {**base, "resultOffset": offset})
            feats.extend(list(geo.get("features", []) or []))

    if not feats:
        # Still write an empty FeatureCollection for deterministic behavior.
        out_geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}, indent=2), encoding="utf-8")
        return

    raw = {"type": "FeatureCollection", "features": feats}
    gdf = gpd.GeoDataFrame.from_features(raw["features"], crs="EPSG:4326")
    if gdf.empty:
        out_geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}, indent=2), encoding="utf-8")
        return

    # Clip to Butte union
    gdf["geometry"] = gdf["geometry"].intersection(county_union)
    gdf = gdf[~gdf["geometry"].is_empty & gdf["geometry"].notna()].copy()
    gdf.to_file(out_geojson, driver="GeoJSON")


def main() -> int:
    external_dir = REPO_ROOT / "data" / "external"
    _ensure_dir(external_dir)

    fema_out = external_dir / "fema_nri_county.csv"
    mtbs_out = external_dir / "mtbs_fire_perimeters.geojson"

    print(f"[external] Fetching FEMA NRI (CA counties) -> {fema_out}")
    fetch_fema_nri_counties_ca(fema_out)

    print(f"[external] Fetching MTBS perimeters (Butte clip) -> {mtbs_out}")
    fetch_mtbs_perimeters_butte(mtbs_out)

    print("[external] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

