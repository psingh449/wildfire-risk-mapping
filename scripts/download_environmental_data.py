"""
Download large raster archives (NLCD land cover, USFS WHP) into data/geospatial/.

Does not extract zips — run scripts/extract_geospatial_zips.py after this.

HIFLD shapefiles and statewide OSM .pbf are not downloaded here; facility distances
use OSM via scripts/build_hifld_distances_arcgis.py, and roads use OSMnx in
scripts/process_osm_road_length.py. See DATA_REFRESH.md.
"""
import os

import requests


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def download_nlcd():
    url = "https://s3-us-west-2.amazonaws.com/mrlc/nlcd_2019_land_cover_l48_20210604.zip"
    out_dir = "data/geospatial/nlcd"
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "nlcd_2019_land_cover_l48_20210604.zip")
    if not os.path.exists(out_path):
        print(f"Downloading NLCD to {out_path} (large file)...")
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Done.")
    else:
        print("NLCD zip already present.")


def download_whp():
    url = "https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047/RDS-2015-0047.zip"
    out_dir = "data/geospatial/whp"
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "RDS-2015-0047.zip")
    if not os.path.exists(out_path):
        print(f"Downloading WHP to {out_path} (large file)...")
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Done.")
    else:
        print("WHP zip already present.")


if __name__ == "__main__":
    download_nlcd()
    download_whp()
    print("Next: python scripts/extract_geospatial_zips.py")
