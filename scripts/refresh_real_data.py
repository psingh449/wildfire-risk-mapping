"""
Refresh local CSV caches under data/real/ from Census and ACS APIs (Butte County, CA).

Run from repository root with PYTHONPATH set, e.g. PowerShell:
  $env:PYTHONPATH='.'; python scripts/refresh_real_data.py
"""
import os
import sys

import pandas as pd

# Allow running as script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.config import REAL_DATA_DIR
from src.utils.real_data import (
    fetch_acs_blockgroup,
    fetch_census_housing,
    fetch_census_population,
)


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def _zfill_geoid(df: pd.DataFrame, col: str = "GEOID", block_level: bool = True) -> None:
    """Census block GEOIDs are 15 digits; ACS block-group GEOIDs are 12."""
    n = 15 if block_level else 12
    df[col] = df[col].astype(str).str.strip().str.zfill(n)


def refresh_census_population():
    print("Refreshing Census population data...")
    pop_dict = fetch_census_population([])
    if not pop_dict:
        print("ERROR: Census population fetch failed.")
        return
    df = pd.DataFrame(list(pop_dict.items()), columns=["GEOID", "population"])
    _zfill_geoid(df, "GEOID", block_level=True)
    ensure_dir(REAL_DATA_DIR)
    out = os.path.join(REAL_DATA_DIR, "census_population.csv")
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")


def refresh_census_housing():
    print("Refreshing Census housing data...")
    housing_dict = fetch_census_housing([])
    if not housing_dict:
        print("ERROR: Census housing fetch failed.")
        return
    df = pd.DataFrame(list(housing_dict.items()), columns=["GEOID", "housing_units"])
    _zfill_geoid(df, "GEOID", block_level=True)
    ensure_dir(REAL_DATA_DIR)
    out = os.path.join(REAL_DATA_DIR, "census_housing.csv")
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")


def refresh_acs_blockgroups():
    """Fetch ACS 2021 5-year block-group tables for CA county 007 (Butte)."""
    ensure_dir(REAL_DATA_DIR)
    inc = "state:06 county:007"

    print("Refreshing ACS poverty (B17001)...")
    acs = fetch_acs_blockgroup(["B17001_002E", "B17001_001E", "GEOID"], "block group:*", inc)
    if acs is not None:
        _zfill_geoid(acs, "GEOID", block_level=False)
        acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_poverty.csv"), index=False)
        print(f"  -> acs_poverty.csv ({len(acs)} rows)")
    else:
        print("  -> FAILED acs_poverty")

    print("Refreshing ACS elderly (B01001)...")
    fields = ["B01001_001E"] + [f"B01001_{i:03d}E" for i in range(20, 26)] + ["GEOID"]
    acs = fetch_acs_blockgroup(fields, "block group:*", inc)
    if acs is not None:
        _zfill_geoid(acs, "GEOID", block_level=False)
        acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_elderly.csv"), index=False)
        print(f"  -> acs_elderly.csv ({len(acs)} rows)")
    else:
        print("  -> FAILED acs_elderly")

    print("Refreshing ACS vehicle access (B08201)...")
    acs = fetch_acs_blockgroup(["B08201_002E", "B08201_001E", "GEOID"], "block group:*", inc)
    if acs is not None:
        _zfill_geoid(acs, "GEOID", block_level=False)
        acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_vehicle_access.csv"), index=False)
        print(f"  -> acs_vehicle_access.csv ({len(acs)} rows)")
    else:
        print("  -> FAILED acs_vehicle_access")

    print("Refreshing ACS median home value (B25077)...")
    acs = fetch_acs_blockgroup(["B25077_001E", "GEOID"], "block group:*", inc)
    if acs is not None:
        _zfill_geoid(acs, "GEOID", block_level=False)
        acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_building_value.csv"), index=False)
        print(f"  -> acs_building_value.csv ({len(acs)} rows)")
    else:
        print("  -> FAILED acs_building_value")


def main():
    refresh_census_population()
    refresh_census_housing()
    refresh_acs_blockgroups()
    print("Census + ACS refresh complete. See data/real/*.csv")


if __name__ == "__main__":
    main()
