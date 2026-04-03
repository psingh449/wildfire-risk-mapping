import numpy as np
import logging
import requests
import os
import pandas as pd
from src.utils.dummy_data import generate_uniform, generate_int
from src.utils.source_tracker import mark_real, mark_dummy
from src.utils.config import REAL_DATA_DIR, USE_STORED_REAL_DATA

logger = logging.getLogger("real_data")

# Helper to get min/max from calculations.csv for fallback
def get_limits(var):
    import csv
    with open("calculations.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["geojson_property"] == var:
                try:
                    min_val = float(row["min"])
                except Exception:
                    min_val = 0
                try:
                    max_val = float(row["max"])
                except Exception:
                    max_val = 1
                return min_val, max_val
    return 0, 1

def fallback_uniform(gdf, var, size=None, reason=None):
    min_val, max_val = get_limits(var)
    if size is None:
        size = len(gdf)
    logger.warning(f"Falling back to dummy for {var} in range [{min_val},{max_val}] ({reason})")
    return generate_uniform(min_val, max_val, size)

def fallback_int(gdf, var, size=None, reason=None):
    min_val, max_val = get_limits(var)
    if size is None:
        size = len(gdf)
    logger.warning(f"Falling back to dummy for {var} in range [{min_val},{max_val}] ({reason})")
    return generate_int(int(min_val), int(max_val) + 1, size)

# --- Census API integration for population and housing ---
CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"
CENSUS_HOUSING_URL = "https://api.census.gov/data/2020/dec/pl"

# Helper to fetch census block population
def fetch_census_population(block_geoid_list):
    params = {
        "get": "P1_001N,GEOID",
        "for": "block:*",
        "in": "state:06 county:007"
    }
    try:
        resp = requests.get(CENSUS_POP_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        header = data[0]
        rows = data[1:]
        pop_dict = {row[1]: int(row[0]) for row in rows}
        return pop_dict
    except Exception as e:
        logger.warning(f"Census API population fetch failed: {e}")
        return None

def fetch_census_population_local():
    path = os.path.join(REAL_DATA_DIR, "census_population.csv")
    if not os.path.exists(path):
        logger.warning(f"Local census_population.csv not found at {path}")
        return None
    df = pd.read_csv(path, dtype={"GEOID": str, "population": int})
    return dict(zip(df["GEOID"], df["population"]))

def compute_exposure_population_real(gdf):
    if "GEOID" not in gdf.columns:
        gdf["exposure_population"] = fallback_int(gdf, "exposure_population", reason="No GEOID column")
        return mark_dummy(gdf, "exposure_population", reason="No GEOID column")
    if USE_STORED_REAL_DATA:
        pop_dict = fetch_census_population_local()
        provenance = "local_census_population.csv"
    else:
        pop_dict = fetch_census_population(gdf["GEOID"].tolist())
        provenance = "Census API"
        # Save to local CSV for refresh
        if pop_dict is not None:
            df = pd.DataFrame(list(pop_dict.items()), columns=["GEOID", "population"])
            os.makedirs(REAL_DATA_DIR, exist_ok=True)
            df.to_csv(os.path.join(REAL_DATA_DIR, "census_population.csv"), index=False)
    if pop_dict is None:
        gdf["exposure_population"] = fallback_int(gdf, "exposure_population", reason="No real data available")
        return mark_dummy(gdf, "exposure_population", reason="No real data available")
    gdf["exposure_population"] = gdf["GEOID"].map(pop_dict).fillna(0).astype(int)
    return mark_real(gdf, "exposure_population", source=provenance)

# Helper to fetch census block housing units
def fetch_census_housing(block_geoid_list):
    params = {
        "get": "H1_001N,GEOID",
        "for": "block:*",
        "in": "state:06 county:007"
    }
    try:
        resp = requests.get(CENSUS_HOUSING_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        header = data[0]
        rows = data[1:]
        housing_dict = {row[1]: int(row[0]) for row in rows}
        return housing_dict
    except Exception as e:
        logger.warning(f"Census API housing fetch failed: {e}")
        return None

def fetch_census_housing_local():
    path = os.path.join(REAL_DATA_DIR, "census_housing.csv")
    if not os.path.exists(path):
        logger.warning(f"Local census_housing.csv not found at {path}")
        return None
    df = pd.read_csv(path, dtype={"GEOID": str, "housing_units": int})
    return dict(zip(df["GEOID"], df["housing_units"]))

def compute_exposure_housing_real(gdf):
    if "GEOID" not in gdf.columns:
        gdf["exposure_housing"] = fallback_int(gdf, "exposure_housing", reason="No GEOID column")
        return mark_dummy(gdf, "exposure_housing", reason="No GEOID column")
    if USE_STORED_REAL_DATA:
        housing_dict = fetch_census_housing_local()
        provenance = "local_census_housing.csv"
    else:
        housing_dict = fetch_census_housing(gdf["GEOID"].tolist())
        provenance = "Census API"
        # Save to local CSV for refresh
        if housing_dict is not None:
            df = pd.DataFrame(list(housing_dict.items()), columns=["GEOID", "housing_units"])
            os.makedirs(REAL_DATA_DIR, exist_ok=True)
            df.to_csv(os.path.join(REAL_DATA_DIR, "census_housing.csv"), index=False)
    if housing_dict is None:
        gdf["exposure_housing"] = fallback_int(gdf, "exposure_housing", reason="No real data available")
        return mark_dummy(gdf, "exposure_housing", reason="No real data available")
    gdf["exposure_housing"] = gdf["GEOID"].map(housing_dict).fillna(0).astype(int)
    return mark_real(gdf, "exposure_housing", source=provenance)

# --- ACS API integration for poverty, elderly, vehicle access, building value ---
# TODO: Implement ACS API fetches for these features as per calculations.csv
# For now, fallback logic is used for all

def compute_exposure_building_value_real(gdf):
    # TODO: Implement ACS median value fetch and join
    gdf["exposure_building_value"] = fallback_uniform(gdf, "exposure_building_value", reason="No real data available")
    return mark_dummy(gdf, "exposure_building_value", reason="No real data available")

def compute_vuln_poverty_real(gdf):
    # TODO: Implement ACS poverty fetch and allocation
    gdf["vuln_poverty"] = fallback_uniform(gdf, "vuln_poverty", reason="No real data available")
    return mark_dummy(gdf, "vuln_poverty", reason="No real data available")

def compute_vuln_elderly_real(gdf):
    # TODO: Implement ACS elderly fetch and allocation
    gdf["vuln_elderly"] = fallback_uniform(gdf, "vuln_elderly", reason="No real data available")
    return mark_dummy(gdf, "vuln_elderly", reason="No real data available")

def compute_vuln_vehicle_access_real(gdf):
    # TODO: Implement ACS vehicle access fetch and allocation
    gdf["vuln_vehicle_access"] = fallback_uniform(gdf, "vuln_vehicle_access", reason="No real data available")
    return mark_dummy(gdf, "vuln_vehicle_access", reason="No real data available")

# Add similar stubs for all features as per calculations.csv
