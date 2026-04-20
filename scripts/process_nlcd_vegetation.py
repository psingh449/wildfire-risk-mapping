import argparse
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd


def _load_osm_forest_polygons(blocks: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Fetch "forest-like" polygons from OSM within the blocks bbox.

    This is a pragmatic fallback when NLCD rasters are unavailable: it yields a
    reproducible, explainable vegetation proxy that does not require multi-GB downloads.
    """
    # OSMnx expects (left, bottom, right, top) in lat/lon (EPSG:4326)
    blocks_ll = blocks.to_crs(4326)
    minx, miny, maxx, maxy = blocks_ll.total_bounds
    pad = 0.02
    bbox = (minx - pad, miny - pad, maxx + pad, maxy + pad)

    # Broad set of tags commonly used for forest/wooded areas.
    # We intentionally include multiple tags; downstream we just need polygons.
    tags_list = [
        {"landuse": "forest"},
        {"natural": "wood"},
        {"natural": "scrub"},
        {"landuse": "meadow"},
        {"leisure": "nature_reserve"},
        {"boundary": "national_park"},
    ]

    frames: list[gpd.GeoDataFrame] = []
    for tags in tags_list:
        try:
            g = ox.features_from_bbox(bbox, tags=tags)
            if g is None or len(g) == 0:
                continue
            g = g.reset_index(drop=True)
            frames.append(g)
        except Exception:
            continue

    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    out = pd.concat(frames, ignore_index=True)
    if "geometry" not in out.columns:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(out, geometry="geometry", crs="EPSG:4326")
    # Keep polygons/multipolygons only
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    return gdf


def compute_nlcd_vegetation(blocks_path, nlcd_raster_path, out_csv):
    # NOTE: `nlcd_raster_path` is kept only for backwards compatible CLI shape.
    blocks = gpd.read_file(blocks_path)
    forest = _load_osm_forest_polygons(blocks)

    # Compute fraction of each block covered by forest polygons (area-based).
    blocks_m = blocks.to_crs(3857)
    forest_m = forest.to_crs(3857) if len(forest) else forest

    if len(forest_m) == 0:
        blocks["nlcd_vegetation"] = 0.0
    else:
        forest_union = forest_m.geometry.unary_union
        block_area = blocks_m.geometry.area
        inter_area = blocks_m.geometry.intersection(forest_union).area
        ratio = (inter_area / block_area).fillna(0.0)
        # Clamp to [0, 1] in case of numeric quirks
        blocks["nlcd_vegetation"] = ratio.clip(lower=0.0, upper=1.0).astype(float)

    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    blocks[["block_id", "nlcd_vegetation"]].to_csv(out_csv, index=False)
    print(f"Saved vegetation proxy (OSM) to {out_csv}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--blocks", default="data/processed/blocks.geojson")
    p.add_argument("--nlcd", default="data/geospatial/nlcd/nlcd_2019_land_cover_l48_20210604.img")
    p.add_argument("--out", default="data/real/nlcd_vegetation.csv")
    args = p.parse_args()

    compute_nlcd_vegetation(
        blocks_path=args.blocks,
        nlcd_raster_path=args.nlcd,
        out_csv=args.out,
    )
