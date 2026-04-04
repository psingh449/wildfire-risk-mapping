import geopandas as gpd
import rasterio
import numpy as np
import os
import pandas as pd
from shapely.geometry import shape, mapping, Point
from rasterio.features import shapes

FOREST_CODES = {41, 42, 43, 52}

def extract_forest_polygons(nlcd_raster_path, bounds):
    with rasterio.open(nlcd_raster_path) as src:
        window = src.window(*bounds)
        data = src.read(1, window=window)
        mask = np.isin(data, list(FOREST_CODES))
        results = (
            {'properties': {'raster_val': v}, 'geometry': s}
            for s, v in shapes(data, mask=mask, transform=src.window_transform(window))
        )
        geoms = [shape(feat['geometry']) for feat in results if feat['properties']['raster_val'] in FOREST_CODES]
        return geoms

def compute_nlcd_forest_distance(blocks_path, nlcd_raster_path, out_csv):
    gdf = gpd.read_file(blocks_path)
    bounds = gdf.total_bounds
    forest_polys = extract_forest_polygons(nlcd_raster_path, bounds)
    if not forest_polys:
        gdf['nlcd_forest_distance'] = np.nan
    else:
        forest_union = gpd.GeoSeries(forest_polys).unary_union
        dists = []
        for idx, row in gdf.iterrows():
            centroid = row['geometry'].centroid
            dist_km = centroid.distance(forest_union) / 1000.0
            inv = 1 / (1 + dist_km)
            dists.append(inv)
        gdf['nlcd_forest_distance'] = dists
    gdf[['block_id', 'nlcd_forest_distance']].to_csv(out_csv, index=False)
    print(f"Saved NLCD forest distance to {out_csv}")

if __name__ == "__main__":
    compute_nlcd_forest_distance(
        blocks_path="data/processed/blocks.geojson",
        nlcd_raster_path="data/geospatial/nlcd/nlcd_2019_land_cover_l48_20210604.img",
        out_csv="data/real/nlcd_forest_distance.csv"
    )
