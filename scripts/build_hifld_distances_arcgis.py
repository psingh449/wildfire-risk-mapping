"""
Build data/real/fire_station_dist.csv and data/real/hospital_dist.csv.

Uses OpenStreetMap via OSMnx (amenity=fire_station and amenity=hospital) within the
blocks bounding box. This matches the pipeline contract (km distances to nearest facility)
used in src/utils/real_data.py. For many study areas OSM aligns closely with HIFLD coverage;
if you require official HIFLD layers, replace this script with a shapefile-based workflow.

Requires: data/processed/blocks.geojson, osmnx, geopandas
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def nearest_km_from_centroids(blocks: gpd.GeoDataFrame, facilities: gpd.GeoDataFrame) -> pd.Series:
    """Minimum distance in km from each block centroid to nearest facility (projected)."""
    b = blocks.to_crs(3857)
    b["centroid"] = b.geometry.centroid
    b = b.set_geometry("centroid")
    if facilities is None or len(facilities) == 0:
        return pd.Series([1e6] * len(blocks), index=blocks.index)
    f = facilities.to_crs(3857)
    dists_km = []
    for _, row in b.iterrows():
        d = f.geometry.distance(row.geometry).min()
        dists_km.append(d / 1000.0)
    return pd.Series(dists_km, index=blocks.index)


def load_osm_facilities(bbox_tuple, tags: dict) -> gpd.GeoDataFrame:
    """bbox = (west, south, east, north) per OSMnx."""
    try:
        return ox.features_from_bbox(bbox_tuple, tags=tags)
    except Exception as e:
        print(f"OSM fetch failed for {tags}: {e}")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def run():
    p = argparse.ArgumentParser()
    p.add_argument("--blocks", default=str(REPO / "data" / "processed" / "blocks.geojson"))
    p.add_argument("--out-dir", default=str(REPO / "data" / "real"))
    args = p.parse_args()

    blocks_path = Path(args.blocks)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    blocks = gpd.read_file(blocks_path)
    minx, miny, maxx, maxy = blocks.total_bounds
    pad = 0.02
    bbox = (minx - pad, miny - pad, maxx + pad, maxy + pad)

    print("Downloading OSM fire_station features (bbox)...")
    fire = load_osm_facilities(bbox, {"amenity": "fire_station"})
    print(f"  {len(fire)} features")

    print("Downloading OSM hospital features (bbox)...")
    hosp = load_osm_facilities(bbox, {"amenity": "hospital"})
    print(f"  {len(hosp)} features")

    fs_km = nearest_km_from_centroids(blocks, fire)
    hp_km = nearest_km_from_centroids(blocks, hosp)

    out_fs = out_dir / "fire_station_dist.csv"
    out_hp = out_dir / "hospital_dist.csv"
    pd.DataFrame({"block_id": blocks["block_id"], "fire_station_dist": fs_km}).to_csv(
        out_fs, index=False
    )
    pd.DataFrame({"block_id": blocks["block_id"], "hospital_dist": hp_km}).to_csv(
        out_hp, index=False
    )
    print(f"Wrote {out_fs}")
    print(f"Wrote {out_hp}")


if __name__ == "__main__":
    run()
