"""
Compute mean WHP raster value per block group -> data/real/whp_zonal_stats.csv

Requires:
  - data/processed/blocks.geojson
  - WHP GeoTIFF under data/geospatial/whp/ (extract RDS-2015-0047.zip first; see extract_geospatial_zips.py)
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import rasterio
import rasterio.mask
from shapely.geometry import mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import geopandas as gpd  # noqa: E402


def find_whp_raster(whp_dir: Path) -> Path:
    for pattern in ("**/*.tif", "**/*.tiff"):
        matches = list(whp_dir.glob(pattern))
        if matches:
            # Prefer filename containing WHP or wildfire
            for m in matches:
                if "whp" in m.name.lower() or "wildfire" in m.name.lower():
                    return m
            return matches[0]
    raise FileNotFoundError(f"No WHP .tif found under {whp_dir}")


def compute_whp_means(blocks_path: Path, whp_raster_path: Path, out_csv: Path) -> None:
    gdf = gpd.read_file(blocks_path)
    stats = []
    with rasterio.open(whp_raster_path) as src:
        gdf_proj = gdf.to_crs(src.crs) if gdf.crs != src.crs else gdf
        for _, row in gdf_proj.iterrows():
            geom = [mapping(row["geometry"])]
            try:
                out_image, _ = rasterio.mask.mask(src, geom, crop=True)
                data = out_image[0]
                nodata = src.nodata
                if nodata is not None:
                    data = data[data != nodata]
                data = data[np.isfinite(data)]
                mean_val = float(np.nanmean(data)) if data.size else np.nan
            except Exception:
                mean_val = np.nan
            stats.append(mean_val)
    gdf["whp_mean"] = stats
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    gdf[["block_id", "whp_mean"]].to_csv(out_csv, index=False)
    print(f"Saved {out_csv} ({len(gdf)} rows)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--blocks", default=str(REPO / "data" / "processed" / "blocks.geojson"))
    p.add_argument("--out", default=str(REPO / "data" / "real" / "whp_zonal_stats.csv"))
    args = p.parse_args()

    blocks = Path(args.blocks)
    whp_dir = REPO / "data" / "geospatial" / "whp"
    out = Path(args.out)
    raster = find_whp_raster(whp_dir)
    print(f"Using WHP raster: {raster}")
    compute_whp_means(blocks, raster, out)


if __name__ == "__main__":
    main()
