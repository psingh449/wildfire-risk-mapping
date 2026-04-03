import geopandas as gpd
import rasterio
import rasterio.mask
import numpy as np
import os
import pandas as pd
from shapely.geometry import mapping

def compute_zonal_stats(blocks_path, nlcd_raster_path, out_csv):
    gdf = gpd.read_file(blocks_path)
    with rasterio.open(nlcd_raster_path) as src:
        stats = []
        for idx, row in gdf.iterrows():
            geom = [mapping(row['geometry'])]
            try:
                out_image, out_transform = rasterio.mask.mask(src, geom, crop=True)
                data = out_image[0]
                data = data[data != src.nodata]
                if data.size == 0:
                    mean_val = np.nan
                else:
                    mean_val = np.mean(data)
                stats.append(mean_val)
            except Exception as e:
                stats.append(np.nan)
        gdf['nlcd_mean'] = stats
    gdf[['block_id', 'nlcd_mean']].to_csv(out_csv, index=False)
    print(f"Saved NLCD zonal stats to {out_csv}")

if __name__ == "__main__":
    compute_zonal_stats(
        blocks_path="data/processed/blocks.geojson",
        nlcd_raster_path="data/geospatial/nlcd/nlcd_2019_land_cover_l48_20210604.img",
        out_csv="data/real/nlcd_zonal_stats.csv"
    )
