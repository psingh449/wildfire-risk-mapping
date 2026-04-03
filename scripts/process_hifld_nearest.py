import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os

def compute_nearest(blocks_path, hifld_path, out_csv, facility_type):
    gdf_blocks = gpd.read_file(blocks_path)
    gdf_fac = gpd.read_file(hifld_path)
    gdf_blocks['centroid'] = gdf_blocks.geometry.centroid
    gdf_blocks = gdf_blocks.set_geometry('centroid')
    gdf_blocks = gdf_blocks.to_crs(gdf_fac.crs)
    gdf_fac = gdf_fac.to_crs(gdf_blocks.crs)
    nearest_dist = []
    for idx, row in gdf_blocks.iterrows():
        dists = gdf_fac.distance(row.geometry)
        nearest_dist.append(dists.min())
    gdf_blocks[f'{facility_type}_dist'] = nearest_dist
    gdf_blocks[['block_id', f'{facility_type}_dist']].to_csv(out_csv, index=False)
    print(f"Saved nearest {facility_type} distances to {out_csv}")

if __name__ == "__main__":
    compute_nearest(
        blocks_path="data/processed/blocks.geojson",
        hifld_path="data/geospatial/hifld/fire_stations.shp",
        out_csv="data/real/fire_station_dist.csv",
        facility_type="fire_station"
    )
    compute_nearest(
        blocks_path="data/processed/blocks.geojson",
        hifld_path="data/geospatial/hifld/hospitals.shp",
        out_csv="data/real/hospital_dist.csv",
        facility_type="hospital"
    )
