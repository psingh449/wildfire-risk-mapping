import geopandas as gpd
import rasterio
import rasterio.mask
import numpy as np
import os
import pandas as pd
import argparse
from shapely.geometry import mapping

# NLCD forest/shrub codes (2019): 41, 42, 43, 52
FOREST_CODES = {41, 42, 43, 52}


def compute_nlcd_vegetation(blocks_path, nlcd_raster_path, out_csv):
    gdf = gpd.read_file(blocks_path)
    with rasterio.open(nlcd_raster_path) as src:
        ratios = []
        for idx, row in gdf.iterrows():
            geom = [mapping(row['geometry'])]
            try:
                out_image, out_transform = rasterio.mask.mask(src, geom, crop=True)
                data = out_image[0]
                data = data[data != src.nodata]
                if data.size == 0:
                    ratio = np.nan
                else:
                    forest = np.isin(data, list(FOREST_CODES)).sum()
                    ratio = forest / data.size
                ratios.append(ratio)
            except Exception as e:
                ratios.append(np.nan)
        gdf['nlcd_vegetation'] = ratios
    gdf[['block_id', 'nlcd_vegetation']].to_csv(out_csv, index=False)
    print(f"Saved NLCD vegetation ratios to {out_csv}")

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
