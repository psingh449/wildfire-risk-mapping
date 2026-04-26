"""
Fetch CAL FIRE FRAP historical fire perimeters (2015–2024) for Experiment 2 validation.

This pulls from the public ArcGIS FeatureServer backing the CNRA Open Data dataset and writes
one repo-local GeoJSON:

  data/external/calfire_perimeters_2015_2024.geojson

We also clip perimeters to the union bbox of the packaged counties in `data/county_manifest.json`
to keep the artifact small (the validation runner uses the packaged counties as its evaluation frame).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]

# Resolved from CNRA Hub dataset → ArcGIS serviceItemId → arcgis.com item url.
CALFIRE_FEATURESERVER = (
    "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/"
    "California_Historic_Fire_Perimeters/FeatureServer/0/query"
)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _request_json(url: str, params: Dict[str, Any], *, timeout_s: int = 120) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=timeout_s)
    r.raise_for_status()
    return r.json()


def _iter_offsets(total: int, page_size: int) -> Iterable[int]:
    off = 0
    while off < total:
        yield off
        off += page_size


def _packaged_union_wgs84() -> Any:
    """
    Union of all packaged county geometries in WGS84. Used for clipping.
    """
    try:
        import geopandas as gpd
    except Exception as e:
        raise RuntimeError("geopandas is required to clip perimeters") from e

    manifest_path = REPO_ROOT / "data" / "county_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = manifest.get("datasets", {}) or {}
    if not datasets:
        raise RuntimeError("county_manifest.json has no datasets.")

    frames: List["gpd.GeoDataFrame"] = []
    for _, rel in datasets.items():
        p = (REPO_ROOT / str(rel)).resolve()
        if not p.exists():
            continue
        gdf = gpd.read_file(p)
        if gdf.empty or "geometry" not in gdf.columns:
            continue
        if getattr(gdf, "crs", None) is not None:
            try:
                gdf = gdf.to_crs("EPSG:4326")
            except Exception:
                pass
        frames.append(gdf[["geometry"]].copy())

    if not frames:
        raise RuntimeError("No packaged county geometries found for clipping.")

    merged = pd.concat(frames, ignore_index=True)
    merged = gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")
    return merged.geometry.unary_union


def fetch_calfire_perimeters_2015_2024(out_geojson: Path) -> None:
    _ensure_dir(out_geojson.parent)

    try:
        import geopandas as gpd
    except Exception as e:
        raise RuntimeError("geopandas is required to write the output GeoJSON") from e

    # Use the packaged counties' bounding box to keep the query and output small.
    # (We already spatially filter in the ArcGIS query, so an additional clip step is optional.)
    union = _packaged_union_wgs84()
    minx, miny, maxx, maxy = union.bounds
    bbox = f"{minx},{miny},{maxx},{maxy}"

    where = "YEAR_ >= 2015 AND YEAR_ <= 2024"
    base = {
        "where": where,
        "geometry": bbox,
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        # Keep to fields that exist on the public layer (see layer pjson fields).
        "outFields": "FIRE_NAME,YEAR_,ALARM_DATE,CONT_DATE,AGENCY,UNIT_ID,CAUSE,GIS_ACRES,INC_NUM",
        "outSR": 4326,
        "returnGeometry": "true",
        "f": "geojson",
        "resultRecordCount": 2000,
    }

    # Count first (ArcGIS count endpoint uses f=json).
    count_params = {**base, "f": "json", "returnCountOnly": "true", "outFields": "", "returnGeometry": "false"}
    count = _request_json(CALFIRE_FEATURESERVER, count_params).get("count", 0)
    if not isinstance(count, int) or count < 0:
        raise RuntimeError(f"Unexpected CAL FIRE count: {count}")

    feats: List[Dict[str, Any]] = []
    if count == 0:
        payload = _request_json(CALFIRE_FEATURESERVER, {**base, "resultOffset": 0})
        feats = list(payload.get("features", []) or [])
    else:
        for offset in _iter_offsets(count, 2000):
            payload = _request_json(CALFIRE_FEATURESERVER, {**base, "resultOffset": offset})
            feats.extend(list(payload.get("features", []) or []))

    if not feats:
        out_geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}, indent=2), encoding="utf-8")
        return

    gdf = gpd.GeoDataFrame.from_features({"type": "FeatureCollection", "features": feats}["features"], crs="EPSG:4326")
    if gdf.empty:
        out_geojson.write_text(json.dumps({"type": "FeatureCollection", "features": []}, indent=2), encoding="utf-8")
        return

    # Drop empty/missing geometries (query already intersects the bbox).
    gdf = gdf[~gdf["geometry"].is_empty & gdf["geometry"].notna()].copy()

    # De-dupe by FIRE_NAME + YEAR_ when present.
    if "FIRE_NAME" in gdf.columns and "YEAR_" in gdf.columns:
        gdf = gdf.drop_duplicates(subset=["FIRE_NAME", "YEAR_"]).copy()

    gdf.to_file(out_geojson, driver="GeoJSON")


def main() -> int:
    out = REPO_ROOT / "data" / "external" / "calfire_perimeters_2015_2024.geojson"
    print(f"[external] Fetching CAL FIRE perimeters (2015–2024) -> {out}")
    fetch_calfire_perimeters_2015_2024(out)
    print("[external] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

