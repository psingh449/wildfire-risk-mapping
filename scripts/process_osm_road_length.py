import geopandas as gpd
import osmnx as ox
import pandas as pd
import argparse

def compute_road_length(blocks_path, osm_pbf_path, out_csv):
    gdf_blocks = gpd.read_file(blocks_path)
    # Download/parse OSM roads for Butte County bounding box
    bounds = gdf_blocks.total_bounds  # minx, miny, maxx, maxy
    # OSMnx 2.x: bbox is (left, bottom, right, top) == (minx, miny, maxx, maxy) in WGS84
    G = ox.graph_from_bbox(
        bbox=(bounds[0], bounds[1], bounds[2], bounds[3]),
        network_type="drive",
        simplify=True,
    )
    gdf_edges = ox.graph_to_gdfs(G, nodes=False)
    gdf_edges = gdf_edges.to_crs(gdf_blocks.crs)
    road_lengths = []
    for idx, row in gdf_blocks.iterrows():
        roads_in_block = gdf_edges[gdf_edges.intersects(row.geometry)]
        total_length = roads_in_block.length.sum()
        road_lengths.append(total_length)
    gdf_blocks['road_length'] = road_lengths
    gdf_blocks[['block_id', 'road_length']].to_csv(out_csv, index=False)
    print(f"Saved OSM road length per block to {out_csv}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--blocks", default="data/processed/blocks.geojson")
    p.add_argument("--out", default="data/real/road_length.csv")
    args = p.parse_args()

    # NOTE: this script currently ignores osm_pbf_path and uses OSMnx online APIs via graph_from_bbox.
    compute_road_length(
        blocks_path=args.blocks,
        osm_pbf_path="",
        out_csv=args.out,
    )
