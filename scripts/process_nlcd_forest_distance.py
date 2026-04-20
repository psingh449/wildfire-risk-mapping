import argparse

def extract_forest_polygons(nlcd_raster_path, bounds):
    raise NotImplementedError("This script no longer uses NLCD rasters; it uses OSM forest polygons instead.")

def compute_nlcd_forest_distance(blocks_path, nlcd_raster_path, out_csv):
    from pathlib import Path

    import geopandas as gpd
    import numpy as np
    import osmnx as ox
    import pandas as pd

    blocks = gpd.read_file(blocks_path)
    blocks_ll = blocks.to_crs(4326)
    minx, miny, maxx, maxy = blocks_ll.total_bounds
    pad = 0.02
    bbox = (minx - pad, miny - pad, maxx + pad, maxy + pad)

    tags_list = [
        {"landuse": "forest"},
        {"natural": "wood"},
        {"natural": "scrub"},
        {"leisure": "nature_reserve"},
        {"boundary": "national_park"},
    ]

    frames = []
    for tags in tags_list:
        try:
            g = ox.features_from_bbox(bbox, tags=tags)
            if g is None or len(g) == 0:
                continue
            frames.append(g.reset_index(drop=True))
        except Exception:
            continue

    if frames:
        forest = pd.concat(frames, ignore_index=True)
        forest = gpd.GeoDataFrame(forest, geometry="geometry", crs="EPSG:4326")
        forest = forest[forest.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    else:
        forest = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    blocks_m = blocks.to_crs(3857)
    if len(forest) == 0:
        blocks["nlcd_forest_distance"] = 0.0
    else:
        forest_m = forest.to_crs(3857)
        forest_union = forest_m.geometry.unary_union
        centroids = blocks_m.geometry.centroid
        dist_km = centroids.distance(forest_union) / 1000.0
        inv = 1.0 / (1.0 + dist_km)
        blocks["nlcd_forest_distance"] = inv.fillna(0.0).astype(float)

    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    blocks[["block_id", "nlcd_forest_distance"]].to_csv(out_csv, index=False)
    print(f"Saved forest-distance proxy (OSM) to {out_csv}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--blocks", default="data/processed/blocks.geojson")
    p.add_argument("--nlcd", default="data/geospatial/nlcd/nlcd_2019_land_cover_l48_20210604.img")
    p.add_argument("--out", default="data/real/nlcd_forest_distance.csv")
    args = p.parse_args()

    compute_nlcd_forest_distance(
        blocks_path=args.blocks,
        nlcd_raster_path=args.nlcd,
        out_csv=args.out,
    )
