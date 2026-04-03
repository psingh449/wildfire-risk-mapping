import os
import requests

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# Download NLCD raster (CONUS)
def download_nlcd():
    url = "https://s3-us-west-2.amazonaws.com/mrlc/nlcd_2019_land_cover_l48_20210604.zip"
    out_dir = "data/geospatial/nlcd"
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "nlcd_2019_land_cover_l48_20210604.zip")
    if not os.path.exists(out_path):
        print(f"Downloading NLCD to {out_path}...")
        r = requests.get(url, stream=True)
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Done.")
    else:
        print("NLCD already downloaded.")

# Download WHP raster (USFS)
def download_whp():
    url = "https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047/RDS-2015-0047.zip"
    out_dir = "data/geospatial/whp"
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "RDS-2015-0047.zip")
    if not os.path.exists(out_path):
        print(f"Downloading WHP to {out_path}...")
        r = requests.get(url, stream=True)
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Done.")
    else:
        print("WHP already downloaded.")

# Download HIFLD fire stations and hospitals
def download_hifld():
    hifld_urls = {
        "fire_stations": "https://opendata.arcgis.com/api/v3/datasets/1e5b5b8b7e2d4e7e8e7e8e7e8e7e8e7e_0/downloads/data?format=shp&spatialRefId=4326",
        "hospitals": "https://opendata.arcgis.com/api/v3/datasets/2e5b5b8b7e2d4e7e8e7e8e7e8e7e8e7e_0/downloads/data?format=shp&spatialRefId=4326"
    }
    out_dir = "data/geospatial/hifld"
    ensure_dir(out_dir)
    for name, url in hifld_urls.items():
        out_path = os.path.join(out_dir, f"{name}.zip")
        if not os.path.exists(out_path):
            print(f"Downloading {name} to {out_path}...")
            r = requests.get(url, stream=True)
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Done.")
        else:
            print(f"{name} already downloaded.")

# Download OSM data for Butte County (via Geofabrik)
def download_osm():
    url = "https://download.geofabrik.de/north-america/us/california-latest.osm.pbf"
    out_dir = "data/geospatial/osm"
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "california-latest.osm.pbf")
    if not os.path.exists(out_path):
        print(f"Downloading OSM to {out_path}...")
        r = requests.get(url, stream=True)
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Done.")
    else:
        print("OSM already downloaded.")

if __name__ == "__main__":
    download_nlcd()
    download_whp()
    download_hifld()
    download_osm()
    print("All environmental datasets downloaded. (You may need to extract and process them for Butte County)")
