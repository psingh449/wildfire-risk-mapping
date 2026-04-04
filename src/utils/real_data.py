import numpy as np
import logging
import requests
import os
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from src.utils.dummy_data import generate_uniform, generate_int
from src.utils.source_tracker import mark_real, mark_dummy
from src.utils.config import REAL_DATA_DIR, USE_STORED_REAL_DATA

logger = logging.getLogger("real_data")


def _resolve_calculations_csv() -> Path:
    candidates = [
        Path.cwd() / "calculations.csv",
        Path(__file__).resolve().parents[2] / "calculations.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not locate calculations.csv")


def get_limits(var: str) -> Tuple[float, float]:
    """
    Get min and max values for a variable from calculations.csv.
    Args:
        var: Variable name (geojson_property)
    Returns:
        (min_val, max_val): Tuple of min and max values (float)
    """
    import csv
    try:
        csv_path = _resolve_calculations_csv()
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("geojson_property") == var:
                    try:
                        min_val = float(row.get("min", ""))
                    except Exception:
                        min_val = 0
                    try:
                        max_val = float(row.get("max", ""))
                    except Exception:
                        max_val = 1
                    return min_val, max_val
    except Exception as e:
        logger.error(f"Error reading calculations.csv for {var}: {e}")
    return 0, 1


def fallback_uniform(gdf: pd.DataFrame, var: str, size: Optional[int] = None, reason: Optional[str] = None) -> np.ndarray:
    """
    Generate fallback uniform random values for a variable, handling infinite max.
    Args:
        gdf: DataFrame
        var: Variable name
        size: Number of values
        reason: Reason for fallback
    Returns:
        np.ndarray of random values
    """
    min_val, max_val = get_limits(var)
    if size is None:
        size = len(gdf)
    logger.warning(f"Falling back to dummy for {var} in range [{min_val},{max_val}] ({reason})")
    safe_max = max_val if np.isfinite(max_val) else min_val + 1e6
    return generate_uniform(min_val, safe_max, size)


def fallback_int(gdf: pd.DataFrame, var: str, size: Optional[int] = None, reason: Optional[str] = None) -> np.ndarray:
    """
    Generate fallback integer random values for a variable, handling infinite max.
    Args:
        gdf: DataFrame
        var: Variable name
        size: Number of values
        reason: Reason for fallback
    Returns:
        np.ndarray of random integer values
    """
    min_val, max_val = get_limits(var)
    if size is None:
        size = len(gdf)
    logger.warning(f"Falling back to dummy for {var} in range [{min_val},{max_val}] ({reason})")
    safe_max = int(max_val) if np.isfinite(max_val) else int(min_val) + 10000
    return generate_int(int(min_val), safe_max + 1, size)

# --- Census API integration for population and housing ---
CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"
CENSUS_HOUSING_URL = "https://api.census.gov/data/2020/dec/pl"
STATE_CODE = os.environ.get("WILDFIRE_STATE_CODE", "06")
COUNTY_CODE = os.environ.get("WILDFIRE_COUNTY_CODE", "007")

# Helper to fetch census block population
def fetch_census_population(block_geoid_list: list) -> Optional[Dict[str, int]]:
    """
    Fetch population for all blocks in Butte County from Census API.
    Args:
        block_geoid_list: List of block GEOIDs (unused, fetches all for county)
    Returns:
        Dictionary mapping GEOID to population
    """
    params = {
        "get": "P1_001N,GEOID",
        "for": "block:*",
        "in": f"state:{STATE_CODE} county:{COUNTY_CODE}"
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
        logger.error(f"Census API population fetch failed: {e}")
        return None

def fetch_census_population_local() -> Optional[Dict[str, int]]:
    """
    Load local census population CSV.
    Returns:
        Dictionary mapping GEOID to population
    """
    path = os.path.join(REAL_DATA_DIR, "census_population.csv")
    try:
        if not os.path.exists(path):
            logger.warning(f"Local census_population.csv not found at {path}")
            return None
        df = pd.read_csv(path, dtype={"GEOID": str, "population": int})
        return dict(zip(df["GEOID"], df["population"]))
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return None

def compute_exposure_population_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute exposure_population using real Census data or fallback.
    Args:
        gdf: DataFrame with GEOID column
    Returns:
        DataFrame with exposure_population column
    """
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
def fetch_census_housing(block_geoid_list: list) -> Optional[Dict[str, int]]:
    """
    Fetch housing units for all blocks in Butte County from Census API.
    Args:
        block_geoid_list: List of block GEOIDs (unused, fetches all for county)
    Returns:
        Dictionary mapping GEOID to number of housing units
    """
    params = {
        "get": "H1_001N,GEOID",
        "for": "block:*",
        "in": f"state:{STATE_CODE} county:{COUNTY_CODE}"
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
        logger.error(f"Census API housing fetch failed: {e}")
        return None

def fetch_census_housing_local() -> Optional[Dict[str, int]]:
    """
    Load local census housing CSV.
    Returns:
        Dictionary mapping GEOID to number of housing units
    """
    path = os.path.join(REAL_DATA_DIR, "census_housing.csv")
    try:
        if not os.path.exists(path):
            logger.warning(f"Local census_housing.csv not found at {path}")
            return None
        df = pd.read_csv(path, dtype={"GEOID": str, "housing_units": int})
        return dict(zip(df["GEOID"], df["housing_units"]))
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return None

def compute_exposure_housing_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute exposure_housing using real Census data or fallback.
    Args:
        gdf: DataFrame with GEOID column
    Returns:
        DataFrame with exposure_housing column
    """
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
def fetch_acs_blockgroup(fields: list, for_clause: str, in_clause: str) -> Optional[pd.DataFrame]:
    """
    Fetch ACS block group data for specified fields and geography.
    Args:
        fields: List of field names to fetch
        for_clause: 'for' clause of API request (e.g., "block group:*")
        in_clause: 'in' clause of API request (e.g., "state:06 county:007")
    Returns:
        DataFrame with ACS data, or None on error
    """
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
        logger.error(f"ACS API fetch failed: {e}")
        return None

def fetch_acs_bg_local(filename: str) -> Optional[pd.DataFrame]:
    """
    Load local ACS block group CSV.
    Args:
        filename: Name of the CSV file (e.g., "acs_poverty.csv")
    Returns:
        DataFrame with ACS block group data, or None if not found
    """
    path = os.path.join(REAL_DATA_DIR, filename)
    try:
        if not os.path.exists(path):
            logger.warning(f"Local {filename} not found at {path}")
            return None
        return pd.read_csv(path, dtype=str)
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return None

# Poverty rate (B17001_002E/B17001_001E)
def compute_vuln_poverty_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute vulnerability to poverty using real ACS data or fallback.
    Args:
        gdf: DataFrame with GEOID column
    Returns:
        DataFrame with vuln_poverty and blockgroup columns
    """
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
def compute_vuln_elderly_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute vulnerability to elderly population using real ACS data or fallback.
    Args:
        gdf: DataFrame with GEOID column
    Returns:
        DataFrame with vuln_elderly and blockgroup columns
    """
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
def compute_vuln_vehicle_access_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute vulnerability based on vehicle access using real ACS data or fallback.
    Args:
        gdf: DataFrame with GEOID column
    Returns:
        DataFrame with vuln_vehicle_access and blockgroup columns
    """
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
def compute_exposure_building_value_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute exposure_building_value using real ACS data or fallback.
    Args:
        gdf: DataFrame with GEOID column
    Returns:
        DataFrame with exposure_building_value and blockgroup columns
    """
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

def compute_hazard_wildfire_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute hazard_wildfire using local WHP zonal stats CSV or fallback.
    Args:
        gdf: DataFrame with block_id column
    Returns:
        DataFrame with hazard_wildfire column
    """
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

def compute_hazard_vegetation_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute hazard_vegetation using NLCD forest/shrub ratio CSV or fallback.
    Args:
        gdf: DataFrame with block_id column
    Returns:
        DataFrame with hazard_vegetation column
    """
    import os
    import pandas as pd
    from src.utils.source_tracker import mark_real, mark_dummy
    csv_path = os.path.join(REAL_DATA_DIR, "nlcd_vegetation.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={"block_id": str, "nlcd_vegetation": float})
        gdf = gdf.merge(df, on="block_id", how="left")
        gdf["hazard_vegetation"] = gdf["nlcd_vegetation"].fillna(0)
        return mark_real(gdf, "hazard_vegetation", source="local_nlcd_vegetation.csv")
    else:
        gdf["hazard_vegetation"] = fallback_uniform(gdf, "hazard_vegetation", reason="No NLCD vegetation CSV found")
        return mark_dummy(gdf, "hazard_vegetation", reason="No NLCD vegetation CSV found")

def compute_hazard_forest_distance_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute hazard_forest_distance using NLCD forest distance CSV or fallback.
    Args:
        gdf: DataFrame with block_id column
    Returns:
        DataFrame with hazard_forest_distance column
    """
    import os
    import pandas as pd
    from src.utils.source_tracker import mark_real, mark_dummy
    csv_path = os.path.join(REAL_DATA_DIR, "nlcd_forest_distance.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={"block_id": str, "nlcd_forest_distance": float})
        gdf = gdf.merge(df, on="block_id", how="left")
        gdf["hazard_forest_distance"] = gdf["nlcd_forest_distance"].fillna(0)
        return mark_real(gdf, "hazard_forest_distance", source="local_nlcd_forest_distance.csv")
    else:
        gdf["hazard_forest_distance"] = fallback_uniform(gdf, "hazard_forest_distance", reason="No NLCD forest distance CSV found")
        return mark_dummy(gdf, "hazard_forest_distance", reason="No NLCD forest distance CSV found")

# --- HIFLD Fire Station, Hospital, and Road Access ---
HIFLD_URL_BASE = "https://services1.arcgis.com/"
HIFLD_FIRE_STATION_LAYER = "B4TjvmT8Fm8ZuJtY/FeatureServer/0"
HIFLD_HOSPITAL_LAYER = "B4TjvmT8Fm8ZuJtY/FeatureServer/1"
OSM_ROAD_LENGTH_LAYER = "B4TjvmT8Fm8ZuJtY/FeatureServer/2"

# Helper to fetch HIFLD fire station data
def fetch_hifld_fire_station() -> Optional[pd.DataFrame]:
    """
    Fetch fire station data from HIFLD Fire Station Layer.
    Returns:
        DataFrame with fire station data, or None on error
    """
    url = f"{HIFLD_URL_BASE}{HIFLD_FIRE_STATION_LAYER}/query"
    params = {
        "where": "1=1",
        "outFields": "OBJECTID,NAME,STREET,POSTCODE,CITY,County,STATE,PHONE,Cross_Street,Latitude,Longitude",
        "f": "pjson"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            logger.warning("No fire station data found")
            return None
        # Convert to DataFrame
        df = pd.json_normalize(features)
        # Simplify columns
        df = df.rename(columns={
            "attributes.OBJECTID": "object_id",
            "attributes.NAME": "name",
            "attributes.STREET": "street",
            "attributes.POSTCODE": "postcode",
            "attributes.CITY": "city",
            "attributes.County": "county",
            "attributes.STATE": "state",
            "attributes.PHONE": "phone",
            "attributes.Cross_Street": "cross_street",
            "geometry.coordinates": "coordinates"
        })
        df["layer"] = "fire_station"
        return df
    except Exception as e:
        logger.error(f"Error fetching fire station data: {e}")
        return None

# Helper to fetch HIFLD hospital data
def fetch_hifld_hospital() -> Optional[pd.DataFrame]:
    """
    Fetch hospital data from HIFLD Hospital Layer.
    Returns:
        DataFrame with hospital data, or None on error
    """
    url = f"{HIFLD_URL_BASE}{HIFLD_HOSPITAL_LAYER}/query"
    params = {
        "where": "1=1",
        "outFields": "OBJECTID,NAME,STREET,POSTCODE,CITY,COUNTY,STATE,PHONE,Cross_Street,Latitude,Longitude",
        "f": "pjson"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            logger.warning("No hospital data found")
            return None
        # Convert to DataFrame
        df = pd.json_normalize(features)
        # Simplify columns
        df = df.rename(columns={
            "attributes.OBJECTID": "object_id",
            "attributes.NAME": "name",
            "attributes.STREET": "street",
            "attributes.POSTCODE": "postcode",
            "attributes.CITY": "city",
            "attributes.COUNTY": "county",
            "attributes.STATE": "state",
            "attributes.PHONE": "phone",
            "attributes.Cross_Street": "cross_street",
            "geometry.coordinates": "coordinates"
        })
        df["layer"] = "hospital"
        return df
    except Exception as e:
        logger.error(f"Error fetching hospital data: {e}")
        return None

# Helper to fetch OSM road length data
def fetch_osm_road_length() -> Optional[pd.DataFrame]:
    """
    Fetch road length data from OSM Road Length Layer.
    Returns:
        DataFrame with road length data, or None on error
    """
    url = f"{HIFLD_URL_BASE}{OSM_ROAD_LENGTH_LAYER}/query"
    params = {
        "where": "1=1",
        "outFields": "OBJECTID,block_id,road_length",
        "f": "pjson"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        if not features:
            logger.warning("No road length data found")
            return None
        # Convert to DataFrame
        df = pd.json_normalize(features)
        # Simplify columns
        df = df.rename(columns={
            "attributes.OBJECTID": "object_id",
            "attributes.block_id": "block_id",
            "attributes.road_length": "road_length",
            "geometry.coordinates": "coordinates"
        })
        df["layer"] = "road_length"
        return df
    except Exception as e:
        logger.error(f"Error fetching road length data: {e}")
        return None

def compute_res_fire_station_dist_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute res_fire_station_dist using HIFLD fire station CSV or fallback.
    Args:
        gdf: DataFrame with block_id column
    Returns:
        DataFrame with res_fire_station_dist column
    """
    import os
    import pandas as pd
    from src.utils.source_tracker import mark_real, mark_dummy
    csv_path = os.path.join(REAL_DATA_DIR, "fire_station_dist.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={"block_id": str, "fire_station_dist": float})
        gdf = gdf.merge(df, on="block_id", how="left")
        # Invert and scale: 1/(1+distance_km)
        gdf["res_fire_station_dist"] = 1 / (1 + gdf["fire_station_dist"].fillna(0))
        return mark_real(gdf, "res_fire_station_dist", source="local_fire_station_dist.csv")
    else:
        gdf["res_fire_station_dist"] = fallback_uniform(gdf, "res_fire_station_dist", reason="No fire station dist CSV found")
        return mark_dummy(gdf, "res_fire_station_dist", reason="No fire station dist CSV found")

def compute_res_hospital_dist_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute res_hospital_dist using HIFLD hospital CSV or fallback.
    Args:
        gdf: DataFrame with block_id column
    Returns:
        DataFrame with res_hospital_dist column
    """
    import os
    import pandas as pd
    from src.utils.source_tracker import mark_real, mark_dummy
    csv_path = os.path.join(REAL_DATA_DIR, "hospital_dist.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={"block_id": str, "hospital_dist": float})
        gdf = gdf.merge(df, on="block_id", how="left")
        # Invert and scale: 1/(1+distance_km)
        gdf["res_hospital_dist"] = 1 / (1 + gdf["hospital_dist"].fillna(0))
        return mark_real(gdf, "res_hospital_dist", source="local_hospital_dist.csv")
    else:
        gdf["res_hospital_dist"] = fallback_uniform(gdf, "res_hospital_dist", reason="No hospital dist CSV found")
        return mark_dummy(gdf, "res_hospital_dist", reason="No hospital dist CSV found")

def compute_res_road_access_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute res_road_access using OSM road length CSV or fallback.
    Args:
        gdf: DataFrame with block_id and geometry columns
    Returns:
        DataFrame with res_road_access column
    """
    import os
    import pandas as pd
    from src.utils.source_tracker import mark_real, mark_dummy
    csv_path = os.path.join(REAL_DATA_DIR, "road_length.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={"block_id": str, "road_length": float})
        gdf = gdf.merge(df, on="block_id", how="left")
        # Compute road access = road_length / area, then min-max normalize
        if "geometry" in gdf.columns:
            gdf["block_area"] = gdf["geometry"].area
        else:
            gdf["block_area"] = 1.0
        gdf["road_access_raw"] = gdf["road_length"].fillna(0) / gdf["block_area"].replace(0, 1)
        # Min-max normalization
        min_val = gdf["road_access_raw"].min()
        max_val = gdf["road_access_raw"].max()
        if max_val > min_val:
            gdf["res_road_access"] = (gdf["road_access_raw"] - min_val) / (max_val - min_val)
        else:
            gdf["res_road_access"] = 0.0
        return mark_real(gdf, "res_road_access", source="local_road_length.csv")
    else:
        gdf["res_road_access"] = fallback_uniform(gdf, "res_road_access", reason="No road length CSV found")
        return mark_dummy(gdf, "res_road_access", reason="No road length CSV found")
