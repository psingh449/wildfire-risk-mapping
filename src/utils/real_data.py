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
    # Fix: handle infinite max_val
    safe_max = max_val if np.isfinite(max_val) else min_val + 1e6  # reasonable upper bound
    return generate_uniform(min_val, safe_max, size)

def fallback_int(gdf, var, size=None, reason=None):
    min_val, max_val = get_limits(var)
    if size is None:
        size = len(gdf)
    logger.warning(f"Falling back to dummy for {var} in range [{min_val},{max_val}] ({reason})")
    # Fix: handle infinite max_val
    safe_max = int(max_val) if np.isfinite(max_val) else int(min_val) + 10000  # reasonable upper bound
    return generate_int(int(min_val), safe_max + 1, size)

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
ACS_URL = "https://api.census.gov/data/2021/acs/acs5"

# Helper to fetch ACS block group data (poverty, elderly, vehicle access, building value)
def fetch_acs_blockgroup(fields, for_clause, in_clause):
    params = {
        "get": ",".join(fields),
        "for": for_clause,
        "in": in_clause
    }
    try:
        resp = requests.get(ACS_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        header = data[0]
        rows = data[1:]
        return pd.DataFrame(rows, columns=header)
    except Exception as e:
        logger.warning(f"ACS API fetch failed: {e}")
        return None

def fetch_acs_bg_local(filename):
    path = os.path.join(REAL_DATA_DIR, filename)
    if not os.path.exists(path):
        logger.warning(f"Local {filename} not found at {path}")
        return None
    return pd.read_csv(path, dtype=str)

# Poverty rate (B17001_002E/B17001_001E)
def compute_vuln_poverty_real(gdf):
    # Map block to block group
    if "GEOID" not in gdf.columns:
        gdf["vuln_poverty"] = fallback_uniform(gdf, "vuln_poverty", reason="No GEOID column")
        return mark_dummy(gdf, "vuln_poverty", reason="No GEOID column")
    bg_col = gdf["GEOID"].str[:12-3]  # block group = first 12-3=9 digits
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_poverty.csv")
        provenance = "local_acs_poverty.csv"
    else:
        acs = fetch_acs_blockgroup(["B17001_002E", "B17001_001E", "GEOID"], "block group:*", "state:06 county:007")
        provenance = "ACS API"
        if acs is not None:
            acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_poverty.csv"), index=False)
    if acs is None:
        gdf["vuln_poverty"] = fallback_uniform(gdf, "vuln_poverty", reason="No real data available")
        return mark_dummy(gdf, "vuln_poverty", reason="No real data available")
    acs["B17001_002E"] = pd.to_numeric(acs["B17001_002E"], errors="coerce")
    acs["B17001_001E"] = pd.to_numeric(acs["B17001_001E"], errors="coerce")
    acs["poverty_rate"] = acs["B17001_002E"] / acs["B17001_001E"]
    poverty_map = dict(zip(acs["GEOID"], acs["poverty_rate"]))
    gdf["blockgroup"] = bg_col
    gdf["vuln_poverty"] = gdf["blockgroup"].map(poverty_map).fillna(0)
    return mark_real(gdf, "vuln_poverty", source=provenance)

# Elderly ratio (sum B01001_020E..B01001_025E / B01001_001E)
def compute_vuln_elderly_real(gdf):
    if "GEOID" not in gdf.columns:
        gdf["vuln_elderly"] = fallback_uniform(gdf, "vuln_elderly", reason="No GEOID column")
        return mark_dummy(gdf, "vuln_elderly", reason="No GEOID column")
    bg_col = gdf["GEOID"].str[:9]
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_elderly.csv")
        provenance = "local_acs_elderly.csv"
    else:
        fields = ["B01001_001E"] + [f"B01001_{i:03d}E" for i in range(20, 26)] + ["GEOID"]
        acs = fetch_acs_blockgroup(fields, "block group:*", "state:06 county:007")
        provenance = "ACS API"
        if acs is not None:
            acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_elderly.csv"), index=False)
    if acs is None:
        gdf["vuln_elderly"] = fallback_uniform(gdf, "vuln_elderly", reason="No real data available")
        return mark_dummy(gdf, "vuln_elderly", reason="No real data available")
    acs = acs.apply(pd.to_numeric, errors="coerce")
    acs["elderly_sum"] = acs[[f"B01001_{i:03d}E" for i in range(20, 26)]].sum(axis=1)
    acs["elderly_ratio"] = acs["elderly_sum"] / acs["B01001_001E"]
    elderly_map = dict(zip(acs["GEOID"], acs["elderly_ratio"]))
    gdf["blockgroup"] = bg_col
    gdf["vuln_elderly"] = gdf["blockgroup"].map(elderly_map).fillna(0)
    return mark_real(gdf, "vuln_elderly", source=provenance)

# Vehicle access (1 - B08201_002E / B08201_001E)
def compute_vuln_vehicle_access_real(gdf):
    if "GEOID" not in gdf.columns:
        gdf["vuln_vehicle_access"] = fallback_uniform(gdf, "vuln_vehicle_access", reason="No GEOID column")
        return mark_dummy(gdf, "vuln_vehicle_access", reason="No GEOID column")
    bg_col = gdf["GEOID"].str[:9]
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_vehicle_access.csv")
        provenance = "local_acs_vehicle_access.csv"
    else:
        fields = ["B08201_002E", "B08201_001E", "GEOID"]
        acs = fetch_acs_blockgroup(fields, "block group:*", "state:06 county:007")
        provenance = "ACS API"
        if acs is not None:
            acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_vehicle_access.csv"), index=False)
    if acs is None:
        gdf["vuln_vehicle_access"] = fallback_uniform(gdf, "vuln_vehicle_access", reason="No real data available")
        return mark_dummy(gdf, "vuln_vehicle_access", reason="No real data available")
    acs = acs.apply(pd.to_numeric, errors="coerce")
    acs["vehicle_access"] = 1 - (acs["B08201_002E"] / acs["B08201_001E"])
    vehicle_map = dict(zip(acs["GEOID"], acs["vehicle_access"]))
    gdf["blockgroup"] = bg_col
    gdf["vuln_vehicle_access"] = gdf["blockgroup"].map(vehicle_map).fillna(0)
    return mark_real(gdf, "vuln_vehicle_access", source=provenance)

# Building value (B25077_001E * housing units)
def compute_exposure_building_value_real(gdf):
    if "GEOID" not in gdf.columns:
        gdf["exposure_building_value"] = fallback_uniform(gdf, "exposure_building_value", reason="No GEOID column")
        return mark_dummy(gdf, "exposure_building_value", reason="No GEOID column")
    bg_col = gdf["GEOID"].str[:9]
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_building_value.csv")
        provenance = "local_acs_building_value.csv"
    else:
        fields = ["B25077_001E", "GEOID"]
        acs = fetch_acs_blockgroup(fields, "block group:*", "state:06 county:007")
        provenance = "ACS API"
        if acs is not None:
            acs.to_csv(os.path.join(REAL_DATA_DIR, "acs_building_value.csv"), index=False)
    if acs is None:
        gdf["exposure_building_value"] = fallback_uniform(gdf, "exposure_building_value", reason="No real data available")
        return mark_dummy(gdf, "exposure_building_value", reason="No real data available")
    acs = acs.apply(pd.to_numeric, errors="coerce")
    value_map = dict(zip(acs["GEOID"], acs["B25077_001E"]))
    gdf["blockgroup"] = bg_col
    gdf["exposure_building_value"] = gdf["blockgroup"].map(value_map).fillna(0) * gdf.get("exposure_housing", 1)
    return mark_real(gdf, "exposure_building_value", source=provenance)

def compute_hazard_wildfire_real(gdf):
    import os
    import pandas as pd
    from src.utils.source_tracker import mark_real, mark_dummy
    csv_path = os.path.join(REAL_DATA_DIR, "whp_zonal_stats.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={"block_id": str, "whp_mean": float})
        gdf = gdf.merge(df, on="block_id", how="left")
        gdf["hazard_wildfire"] = gdf["whp_mean"].fillna(0)
        return mark_real(gdf, "hazard_wildfire", source="local_whp_zonal_stats.csv")
    else:
        gdf["hazard_wildfire"] = fallback_uniform(gdf, "hazard_wildfire", reason="No WHP zonal stats CSV found")
        return mark_dummy(gdf, "hazard_wildfire", reason="No WHP zonal stats CSV found")
