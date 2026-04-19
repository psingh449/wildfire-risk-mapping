"""
Extract downloaded NLCD and WHP zip archives into data/geospatial/{nlcd,whp}/.

Run after scripts/download_environmental_data.py (or manual downloads to the same paths).
"""
import os
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def extract_if_exists(zip_path: Path, dest: Path) -> bool:
    if not zip_path.is_file():
        print(f"Skip (missing): {zip_path}")
        return False
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {zip_path} -> {dest}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    print("Done.")
    return True


def main():
    nlcd_zip = REPO / "data" / "geospatial" / "nlcd" / "nlcd_2019_land_cover_l48_20210604.zip"
    whp_zip = REPO / "data" / "geospatial" / "whp" / "RDS-2015-0047.zip"
    extract_if_exists(nlcd_zip, nlcd_zip.parent)
    extract_if_exists(whp_zip, whp_zip.parent)


if __name__ == "__main__":
    main()
