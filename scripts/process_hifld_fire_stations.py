import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os

def compute_hifld_fire_station_distance(blocks_path, fire_stations_shp_path, out_csv):
    """
    Compute nearest fire station distance for each block.
    Args:
        blocks_path: Path to blocks GeoJSON
        fire_stations_shp_path: Path to fire stations shapefile
        out_csv: Output CSV path
    """
    gdf_blocks = gpd.read_file(blocks_path)
    gdf_stations = gpd.read_file(fire_stations_shp_path)
    
    # Ensure same CRS
    gdf_stations = gdf_stations.to_crs(gdf_blocks.crs)
    
    # Compute centroids
    gdf_blocks['centroid'] = gdf_blocks.geometry.centroid
    
    nearest_dists = []
    for idx, block_row in gdf_blocks.iterrows():
        centroid = block_row['centroid']
        # Compute distances to all fire stations
        dists = gdf_stations.geometry.distance(centroid)
        if len(dists) > 0:
            min_dist_km = dists.min() / 1000.0
            # Invert and normalize
            inv = 1 / (1 + min_dist_km)
        else:
            inv = 0.0
        nearest_dists.append(inv)
    
    gdf_blocks['res_fire_station_dist'] = nearest_dists
    gdf_blocks[['block_id', 'res_fire_station_dist']].to_csv(out_csv, index=False)
    print(f"Saved fire station distances to {out_csv}")

if __name__ == "__main__":
    compute_hifld_fire_station_distance(
        blocks_path="data/processed/blocks.geojson",
        fire_stations_shp_path="data/geospatial/hifld/fire_stations.shp",
        out_csv="data/real/fire_station_dist.csv"
    )
