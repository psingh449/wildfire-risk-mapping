import numpy as np
import logging
import requests
import json
import os
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from src.utils.dummy_data import generate_uniform, generate_int
from src.utils.source_tracker import mark_real, mark_missing, mark_dummy, mark_estimated
from src.utils.config import REAL_DATA_DIR, USE_STORED_REAL_DATA
from src.utils.real_cache import DatasetRef, normalize_county_fips, split_county_fips, write_dataset

logger = logging.getLogger("real_data")

# Block IDs are expected to be 12-digit strings (same as block-group GEOID in this project).
BLOCK_ID_LEN = 12


def _block_id_series(df: pd.DataFrame, col: str = "block_id") -> pd.Series:
    """Normalize block_id to a zero-padded string for stable joins."""
    if col not in df.columns:
        return pd.Series([], dtype=str)
    return df[col].astype(str).str.strip().str.zfill(BLOCK_ID_LEN)

# Census/API endpoints may return empty or HTML errors without a proper User-Agent.
HTTP_HEADERS = {
    "User-Agent": "wildfire-risk-mapping/1.0 (research; +https://github.com)",
    "Accept": "application/json",
}


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

# Block-group tabulation GEOID length (state + county + tract + block group)
BG_GEOID_LEN = 12
TRACT_GEOID_LEN = 11


def block_group_geoid_series(gdf: pd.DataFrame) -> pd.Series:
    """First 12 characters of GEOID = block-group id (matches ACS/Census BG GEOID)."""
    return gdf["GEOID"].astype(str).str.strip().str[:BG_GEOID_LEN]

def tract_geoid_series(gdf: pd.DataFrame) -> pd.Series:
    """First 11 characters of GEOID = tract id (state+county+tract)."""
    return gdf["GEOID"].astype(str).str.strip().str[:TRACT_GEOID_LEN]


# --- Census API integration for population and housing ---
CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"
CENSUS_HOUSING_URL = "https://api.census.gov/data/2020/dec/pl"
# Preferred county selector (5-digit state+county FIPS)
DEFAULT_COUNTY_FIPS = "06007"


def _get_state_county_codes() -> Tuple[str, str]:
    """
    Resolve the selected county into (state_code, county_code).
    Preferred: WILDFIRE_COUNTY_FIPS=SSCCC (5 digits).
    Legacy: WILDFIRE_STATE_CODE=SS and WILDFIRE_COUNTY_CODE=CCC.
    """
    cf = os.environ.get("WILDFIRE_COUNTY_FIPS")
    if cf:
        st, co = split_county_fips(cf)
        return st, co
    st = os.environ.get("WILDFIRE_STATE_CODE", DEFAULT_COUNTY_FIPS[:2])
    co = os.environ.get("WILDFIRE_COUNTY_CODE", DEFAULT_COUNTY_FIPS[2:])
    return str(st).zfill(2), str(co).zfill(3)


def _get_county_fips() -> str:
    cf = os.environ.get("WILDFIRE_COUNTY_FIPS")
    if cf:
        return normalize_county_fips(cf)
    st, co = _get_state_county_codes()
    return f"{st}{co}"

def _bg_geoid_from_pl_row(header: list, row: list) -> str:
    """Build 12-digit block-group GEOID from 2020 PL geographic components."""
    idx = {name: i for i, name in enumerate(header)}
    st = str(row[idx["state"]]).zfill(2)
    co = str(row[idx["county"]]).zfill(3)
    tr = str(row[idx["tract"]]).zfill(6)
    bg = str(row[idx["block group"]]).strip()
    return f"{st}{co}{tr}{bg}"


# Helper to fetch census block-group population (matches 12-char GEOIDs in block_groups.geojson)
def fetch_census_population(block_geoid_list: list) -> Optional[Dict[str, int]]:
    """
    Fetch population for all block groups in the configured county (2020 Decennial PL).
    Args:
        block_geoid_list: Unused; fetches all block groups for the county.
    Returns:
        Dictionary mapping GEOID (str) to population
    """
    st, co = _get_state_county_codes()
    params = {
        "get": "P1_001N",
        "for": "block group:*",
        "in": f"state:{st} county:{co}",
    }
    try:
        resp = requests.get(
            CENSUS_POP_URL, params=params, timeout=120, headers=HTTP_HEADERS
        )
        resp.raise_for_status()
        if not resp.content.strip():
            logger.error("Census population: empty response body (status=%s)", resp.status_code)
            return None
        data = resp.json()
        header = data[0]
        rows = data[1:]
        pop_dict = {}
        for row in rows:
            geoid = _bg_geoid_from_pl_row(header, row)
            pop_dict[geoid] = int(row[0])
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
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="census_pl_2020", quantity_id="population")
    path = ref.data_path
    try:
        if not path.exists():
            # Legacy fallback
            legacy = Path(os.path.join(REAL_DATA_DIR, "census_population.csv"))
            if not legacy.exists():
                logger.warning(f"Local census population not found at {path} (or legacy {legacy})")
                return None
            path = legacy
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
        gdf["exposure_population"] = 0
        return mark_missing(gdf, "exposure_population", reason="No GEOID column")
    if USE_STORED_REAL_DATA:
        pop_dict = fetch_census_population_local()
        provenance = "local_census_population.csv"
    else:
        pop_dict = fetch_census_population(gdf["GEOID"].tolist())
        provenance = "Census API"
        # Save to real_cache for future runs
        if pop_dict is not None:
            county_fips = _get_county_fips()
            df = pd.DataFrame(list(pop_dict.items()), columns=["GEOID", "population"])
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="census_pl_2020", quantity_id="population"),
                df,
                response_json={"dict": pop_dict},
                request={"api": CENSUS_POP_URL, "params": {"for": "block group:*", "in": f"county_fips:{county_fips}"}},
                overwrite=True,
            )
    if pop_dict is None:
        gdf["exposure_population"] = 0
        return mark_missing(gdf, "exposure_population", reason="No real data available")
    gdf["exposure_population"] = gdf["GEOID"].map(pop_dict).fillna(0).astype(int)
    return mark_real(gdf, "exposure_population", source=provenance)

# Helper to fetch census block-group housing units
def fetch_census_housing(block_geoid_list: list) -> Optional[Dict[str, int]]:
    """
    Fetch housing units for all block groups in the configured county (2020 Decennial PL).
    """
    st, co = _get_state_county_codes()
    params = {
        "get": "H1_001N",
        "for": "block group:*",
        "in": f"state:{st} county:{co}",
    }
    try:
        resp = requests.get(
            CENSUS_HOUSING_URL, params=params, timeout=120, headers=HTTP_HEADERS
        )
        resp.raise_for_status()
        if not resp.content.strip():
            logger.error("Census housing: empty response body (status=%s)", resp.status_code)
            return None
        data = resp.json()
        header = data[0]
        rows = data[1:]
        housing_dict = {}
        for row in rows:
            geoid = _bg_geoid_from_pl_row(header, row)
            housing_dict[geoid] = int(row[0])
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
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="census_pl_2020", quantity_id="housing")
    path = ref.data_path
    try:
        if not path.exists():
            legacy = Path(os.path.join(REAL_DATA_DIR, "census_housing.csv"))
            if not legacy.exists():
                logger.warning(f"Local census housing not found at {path} (or legacy {legacy})")
                return None
            path = legacy
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
        gdf["exposure_housing"] = 0
        return mark_missing(gdf, "exposure_housing", reason="No GEOID column")
    if USE_STORED_REAL_DATA:
        housing_dict = fetch_census_housing_local()
        provenance = "local_census_housing.csv"
    else:
        housing_dict = fetch_census_housing(gdf["GEOID"].tolist())
        provenance = "Census API"
        if housing_dict is not None:
            county_fips = _get_county_fips()
            df = pd.DataFrame(list(housing_dict.items()), columns=["GEOID", "housing_units"])
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="census_pl_2020", quantity_id="housing"),
                df,
                response_json={"dict": housing_dict},
                request={"api": CENSUS_HOUSING_URL, "params": {"for": "block group:*", "in": f"county_fips:{county_fips}"}},
                overwrite=True,
            )
    if housing_dict is None:
        gdf["exposure_housing"] = 0
        return mark_missing(gdf, "exposure_housing", reason="No real data available")
    gdf["exposure_housing"] = gdf["GEOID"].map(housing_dict).fillna(0).astype(int)
    return mark_real(gdf, "exposure_housing", source=provenance)

# --- ACS API integration for poverty, elderly, vehicle access, building value ---
ACS_URL = "https://api.census.gov/data/2021/acs/acs5"

# Helper to fetch ACS block group data (poverty, elderly, vehicle access, building value)
def fetch_acs_blockgroup(fields: list, for_clause: str, in_clause: str) -> Optional[pd.DataFrame]:
    """
    Fetch ACS block group data for specified fields and geography.
    Args:
        fields: List of field names to fetch (GEOID is synthesized from geographic columns)
        for_clause: 'for' clause of API request (e.g., "block group:*")
        in_clause: 'in' clause (e.g., "state:06 county:007")
    Returns:
        DataFrame with ACS data, or None on error
    """
    fields_req = [f for f in fields if f != "GEOID"]
    # Request only measure variables; ACS appends state/county/tract/block group automatically.
    seen = set()
    get_unique = []
    for x in fields_req:
        if x not in seen:
            seen.add(x)
            get_unique.append(x)
    params = {
        "get": ",".join(get_unique),
        "for": for_clause,
        "in": in_clause,
    }
    try:
        resp = requests.get(ACS_URL, params=params, timeout=120, headers=HTTP_HEADERS)
        resp.raise_for_status()
        if not resp.content.strip():
            logger.error(
                "ACS API empty body (status=%s). Check VPN/firewall to api.census.gov",
                resp.status_code,
            )
            return None
        data = resp.json()
        header = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=header)
        # Synthesize a stable join key. ACS does NOT include GEOID by default.
        if "GEOID" not in df.columns and all(c in df.columns for c in ("state", "county", "tract")):
            base = (
                df["state"].astype(str).str.zfill(2)
                + df["county"].astype(str).str.zfill(3)
                + df["tract"].astype(str).str.zfill(6)
            )
            if "block group" in df.columns:
                df["GEOID"] = base + df["block group"].astype(str).str.strip()
            else:
                df["GEOID"] = base
        return df
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
    county_fips = _get_county_fips()
    filename = str(filename).strip()
    quantity_map = {
        "acs_poverty.csv": "poverty",
        "acs_elderly.csv": "elderly",
        "acs_vehicle_access.csv": "vehicle_access",
        "acs_building_value.csv": "median_home_value",
        "acs_uninsured.csv": "uninsured",
        "acs_median_household_income.csv": "median_household_income",
        "acs_internet_access.csv": "internet_access",
    }
    ref = None
    if filename in quantity_map:
        ref = DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id=quantity_map[filename])
        path = ref.data_path
    else:
        path = Path(os.path.join(REAL_DATA_DIR, filename))
    try:
        if isinstance(path, Path) and path.exists():
            return pd.read_csv(path, dtype=str)
        # Legacy fallback
        legacy = Path(os.path.join(REAL_DATA_DIR, filename))
        if legacy.exists():
            return pd.read_csv(legacy, dtype=str)
        logger.warning(f"Local {filename} not found at {path} (or legacy {legacy})")
        return None
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
        gdf["vuln_poverty"] = 0.0
        return mark_missing(gdf, "vuln_poverty", reason="No GEOID column")
    bg_col = block_group_geoid_series(gdf)
    tr_col = tract_geoid_series(gdf)
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_poverty.csv")
        provenance = "local_acs_poverty.csv"
        # If BG cache is missing (or intentionally skipped because ACS returned all-nulls), prefer tract fallback.
        if acs is None:
            try:
                ref_tr = DatasetRef(county_fips=_get_county_fips(), source_id="acs_2021_5yr", quantity_id="poverty_tract")
                acs_tr = pd.read_csv(ref_tr.data_path, dtype=str) if ref_tr.data_path.exists() else None
            except Exception:
                acs_tr = None
            if acs_tr is not None:
                acs_tr["B17001_002E"] = pd.to_numeric(acs_tr.get("B17001_002E"), errors="coerce")
                acs_tr["B17001_001E"] = pd.to_numeric(acs_tr.get("B17001_001E"), errors="coerce")
                acs_tr["poverty_rate"] = acs_tr["B17001_002E"] / acs_tr["B17001_001E"]
                poverty_map = dict(zip(acs_tr["GEOID"].astype(str), acs_tr["poverty_rate"]))
                gdf["tract"] = tr_col
                gdf["vuln_poverty"] = pd.to_numeric(gdf["tract"].map(poverty_map), errors="coerce")
                county_mean = float(pd.to_numeric(acs_tr["poverty_rate"], errors="coerce").dropna().mean()) if acs_tr["poverty_rate"].notna().any() else 0.0
                gdf["vuln_poverty"] = gdf["vuln_poverty"].fillna(county_mean).clip(lower=0.0)
                return mark_estimated(gdf, "vuln_poverty", method="ACS tract poverty_rate (cache) -> BG (assign by tract GEOID)")
    else:
        st, co = _get_state_county_codes()
        acs = fetch_acs_blockgroup(["B17001_002E", "B17001_001E", "GEOID"], "block group:*", f"state:{st} county:{co}")
        provenance = "ACS API (block group)"
        if acs is not None:
            county_fips = _get_county_fips()
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id="poverty"),
                acs,
                response_json=json.loads(acs.to_json(orient="records")),
                request={"api": ACS_URL, "params": {"in": f"state:{st} county:{co}"}},
                overwrite=True,
            )
    if acs is None:
        gdf["vuln_poverty"] = 0.0
        return mark_missing(gdf, "vuln_poverty", reason="No real data available")
    acs["B17001_002E"] = pd.to_numeric(acs.get("B17001_002E"), errors="coerce")
    acs["B17001_001E"] = pd.to_numeric(acs.get("B17001_001E"), errors="coerce")
    acs["poverty_rate"] = acs["B17001_002E"] / acs["B17001_001E"]

    # If BG-level estimates are unavailable (often returned as nulls), fall back to tract-level ACS.
    if acs["poverty_rate"].notna().sum() == 0:
        # Prefer cached tract fallback if present (keeps runs offline-friendly).
        try:
            ref_tr = DatasetRef(county_fips=_get_county_fips(), source_id="acs_2021_5yr", quantity_id="poverty_tract")
            if ref_tr.data_path.exists():
                acs_tr = pd.read_csv(ref_tr.data_path, dtype=str)
            else:
                acs_tr = None
        except Exception:
            acs_tr = None
        if acs_tr is None:
            acs_tr = None
        st, co = _get_state_county_codes()
        if acs_tr is None:
            acs_tr = fetch_acs_blockgroup(["B17001_002E", "B17001_001E", "GEOID"], "tract:*", f"state:{st} county:{co}")
        if acs_tr is not None:
            acs_tr["B17001_002E"] = pd.to_numeric(acs_tr.get("B17001_002E"), errors="coerce")
            acs_tr["B17001_001E"] = pd.to_numeric(acs_tr.get("B17001_001E"), errors="coerce")
            acs_tr["poverty_rate"] = acs_tr["B17001_002E"] / acs_tr["B17001_001E"]
            poverty_map = dict(zip(acs_tr["GEOID"].astype(str), acs_tr["poverty_rate"]))
            gdf["tract"] = tr_col
            gdf["vuln_poverty"] = gdf["tract"].map(poverty_map)
            # Last-resort: fill remaining missing with county mean rather than hard 0.
            county_mean = float(pd.to_numeric(acs_tr["poverty_rate"], errors="coerce").dropna().mean()) if acs_tr["poverty_rate"].notna().any() else 0.0
            gdf["vuln_poverty"] = pd.to_numeric(gdf["vuln_poverty"], errors="coerce").fillna(county_mean).clip(lower=0.0)
            return mark_estimated(gdf, "vuln_poverty", method="ACS tract poverty_rate -> BG (assign by tract GEOID)")

    poverty_map = dict(zip(acs["GEOID"].astype(str), acs["poverty_rate"]))
    gdf["blockgroup"] = bg_col
    gdf["vuln_poverty"] = pd.to_numeric(gdf["blockgroup"].map(poverty_map), errors="coerce")
    county_mean = float(pd.to_numeric(acs["poverty_rate"], errors="coerce").dropna().mean()) if acs["poverty_rate"].notna().any() else 0.0
    gdf["vuln_poverty"] = gdf["vuln_poverty"].fillna(county_mean).clip(lower=0.0)
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
        gdf["vuln_elderly"] = 0.0
        return mark_missing(gdf, "vuln_elderly", reason="No GEOID column")
    bg_col = block_group_geoid_series(gdf)
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_elderly.csv")
        provenance = "local_acs_elderly.csv"
    else:
        fields = ["B01001_001E"] + [f"B01001_{i:03d}E" for i in range(20, 26)] + ["GEOID"]
        st, co = _get_state_county_codes()
        acs = fetch_acs_blockgroup(fields, "block group:*", f"state:{st} county:{co}")
        provenance = "ACS API"
        if acs is not None:
            county_fips = _get_county_fips()
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id="elderly"),
                acs,
                response_json=json.loads(acs.to_json(orient="records")),
                request={"api": ACS_URL, "params": {"in": f"state:{st} county:{co}"}},
                overwrite=True,
            )
    if acs is None:
        gdf["vuln_elderly"] = 0.0
        return mark_missing(gdf, "vuln_elderly", reason="No real data available")
    # Convert only measure columns to numeric; keep GEOID as a string join key.
    for c in ["B01001_001E"] + [f"B01001_{i:03d}E" for i in range(20, 26)]:
        if c in acs.columns:
            acs[c] = pd.to_numeric(acs[c], errors="coerce")
    acs["elderly_sum"] = acs[[f"B01001_{i:03d}E" for i in range(20, 26)]].sum(axis=1)
    acs["elderly_ratio"] = acs["elderly_sum"] / acs["B01001_001E"]
    elderly_map = dict(zip(acs["GEOID"].astype(str), acs["elderly_ratio"]))
    gdf["blockgroup"] = bg_col
    gdf["vuln_elderly"] = pd.to_numeric(gdf["blockgroup"].map(elderly_map), errors="coerce")
    county_mean = float(pd.to_numeric(acs["elderly_ratio"], errors="coerce").dropna().mean()) if acs["elderly_ratio"].notna().any() else 0.0
    gdf["vuln_elderly"] = gdf["vuln_elderly"].fillna(county_mean).clip(lower=0.0)
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
        gdf["vuln_vehicle_access"] = 0.0
        return mark_missing(gdf, "vuln_vehicle_access", reason="No GEOID column")
    bg_col = block_group_geoid_series(gdf)
    tr_col = tract_geoid_series(gdf)
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_vehicle_access.csv")
        provenance = "local_acs_vehicle_access.csv"
        # If BG cache is missing (or intentionally skipped because ACS returned all-nulls), prefer tract fallback.
        if acs is None:
            try:
                ref_tr = DatasetRef(county_fips=_get_county_fips(), source_id="acs_2021_5yr", quantity_id="vehicle_access_tract")
                acs_tr = pd.read_csv(ref_tr.data_path, dtype=str) if ref_tr.data_path.exists() else None
            except Exception:
                acs_tr = None
            if acs_tr is not None:
                for c in ["B08201_002E", "B08201_001E"]:
                    if c in acs_tr.columns:
                        acs_tr[c] = pd.to_numeric(acs_tr[c], errors="coerce")
                acs_tr["vehicle_access"] = 1 - (acs_tr["B08201_002E"] / acs_tr["B08201_001E"])
                vehicle_map = dict(zip(acs_tr["GEOID"].astype(str), acs_tr["vehicle_access"]))
                gdf["tract"] = tr_col
                gdf["vuln_vehicle_access"] = pd.to_numeric(gdf["tract"].map(vehicle_map), errors="coerce")
                county_mean = float(pd.to_numeric(acs_tr["vehicle_access"], errors="coerce").dropna().mean()) if acs_tr["vehicle_access"].notna().any() else 0.0
                gdf["vuln_vehicle_access"] = gdf["vuln_vehicle_access"].fillna(county_mean).clip(lower=0.0, upper=1.0)
                return mark_estimated(gdf, "vuln_vehicle_access", method="ACS tract vehicle_access (cache) -> BG (assign by tract GEOID)")
    else:
        fields = ["B08201_002E", "B08201_001E", "GEOID"]
        st, co = _get_state_county_codes()
        acs = fetch_acs_blockgroup(fields, "block group:*", f"state:{st} county:{co}")
        provenance = "ACS API (block group)"
        if acs is not None:
            county_fips = _get_county_fips()
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id="vehicle_access"),
                acs,
                response_json=json.loads(acs.to_json(orient="records")),
                request={"api": ACS_URL, "params": {"in": f"state:{st} county:{co}"}},
                overwrite=True,
            )
    if acs is None:
        gdf["vuln_vehicle_access"] = 0.0
        return mark_missing(gdf, "vuln_vehicle_access", reason="No real data available")
    # Convert only measure columns to numeric; keep GEOID as a string join key.
    for c in ["B08201_002E", "B08201_001E"]:
        if c in acs.columns:
            acs[c] = pd.to_numeric(acs[c], errors="coerce")
    acs["vehicle_access"] = 1 - (acs["B08201_002E"] / acs["B08201_001E"])

    # If BG-level estimates are unavailable (often returned as nulls), fall back to tract-level ACS.
    if acs["vehicle_access"].notna().sum() == 0:
        # Prefer cached tract fallback if present (keeps runs offline-friendly).
        try:
            ref_tr = DatasetRef(county_fips=_get_county_fips(), source_id="acs_2021_5yr", quantity_id="vehicle_access_tract")
            if ref_tr.data_path.exists():
                acs_tr = pd.read_csv(ref_tr.data_path, dtype=str)
            else:
                acs_tr = None
        except Exception:
            acs_tr = None
        st, co = _get_state_county_codes()
        if acs_tr is None:
            acs_tr = fetch_acs_blockgroup(["B08201_002E", "B08201_001E", "GEOID"], "tract:*", f"state:{st} county:{co}")
        if acs_tr is not None:
            for c in ["B08201_002E", "B08201_001E"]:
                if c in acs_tr.columns:
                    acs_tr[c] = pd.to_numeric(acs_tr[c], errors="coerce")
            acs_tr["vehicle_access"] = 1 - (acs_tr["B08201_002E"] / acs_tr["B08201_001E"])
            vehicle_map = dict(zip(acs_tr["GEOID"].astype(str), acs_tr["vehicle_access"]))
            gdf["tract"] = tr_col
            gdf["vuln_vehicle_access"] = pd.to_numeric(gdf["tract"].map(vehicle_map), errors="coerce")
            county_mean = float(pd.to_numeric(acs_tr["vehicle_access"], errors="coerce").dropna().mean()) if acs_tr["vehicle_access"].notna().any() else 0.0
            gdf["vuln_vehicle_access"] = gdf["vuln_vehicle_access"].fillna(county_mean).clip(lower=0.0, upper=1.0)
            return mark_estimated(gdf, "vuln_vehicle_access", method="ACS tract vehicle_access -> BG (assign by tract GEOID)")

    vehicle_map = dict(zip(acs["GEOID"].astype(str), acs["vehicle_access"]))
    gdf["blockgroup"] = bg_col
    gdf["vuln_vehicle_access"] = pd.to_numeric(gdf["blockgroup"].map(vehicle_map), errors="coerce")
    county_mean = float(pd.to_numeric(acs["vehicle_access"], errors="coerce").dropna().mean()) if acs["vehicle_access"].notna().any() else 0.0
    gdf["vuln_vehicle_access"] = gdf["vuln_vehicle_access"].fillna(county_mean).clip(lower=0.0, upper=1.0)
    return mark_real(gdf, "vuln_vehicle_access", source=provenance)


# Uninsured rate (sum no-insurance by age / total)
def compute_vuln_uninsured_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute vulnerability based on health insurance coverage using ACS B27010.
    We treat higher uninsured share as higher vulnerability.

    Formula:
      uninsured_rate = (B27010_017E + B27010_033E + B27010_050E + B27010_066E) / B27010_001E
    """
    if "GEOID" not in gdf.columns:
        gdf["vuln_uninsured"] = 0.0
        return mark_missing(gdf, "vuln_uninsured", reason="No GEOID column")
    bg_col = block_group_geoid_series(gdf)
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_uninsured.csv")
        provenance = "local_acs_uninsured.csv"
    else:
        fields = ["B27010_001E", "B27010_017E", "B27010_033E", "B27010_050E", "B27010_066E", "GEOID"]
        st, co = _get_state_county_codes()
        acs = fetch_acs_blockgroup(fields, "block group:*", f"state:{st} county:{co}")
        provenance = "ACS API"
        if acs is not None:
            county_fips = _get_county_fips()
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id="uninsured"),
                acs,
                response_json=json.loads(acs.to_json(orient="records")),
                request={"api": ACS_URL, "params": {"in": f"state:{st} county:{co}"}},
                overwrite=True,
            )
    if acs is None:
        gdf["vuln_uninsured"] = 0.0
        return mark_missing(gdf, "vuln_uninsured", reason="No real data available")
    for c in ["B27010_001E", "B27010_017E", "B27010_033E", "B27010_050E", "B27010_066E"]:
        if c in acs.columns:
            acs[c] = pd.to_numeric(acs[c], errors="coerce")
    denom = acs["B27010_001E"].replace({0: np.nan})
    uninsured = (
        acs["B27010_017E"].fillna(0)
        + acs["B27010_033E"].fillna(0)
        + acs["B27010_050E"].fillna(0)
        + acs["B27010_066E"].fillna(0)
    )
    acs["uninsured_rate"] = uninsured / denom
    uninsured_map = dict(zip(acs["GEOID"].astype(str), acs["uninsured_rate"]))
    gdf["blockgroup"] = bg_col
    gdf["vuln_uninsured"] = pd.to_numeric(gdf["blockgroup"].map(uninsured_map), errors="coerce")
    county_mean = float(pd.to_numeric(acs["uninsured_rate"], errors="coerce").dropna().mean()) if acs["uninsured_rate"].notna().any() else 0.0
    had_missing = gdf["vuln_uninsured"].isna().any()
    gdf["vuln_uninsured"] = gdf["vuln_uninsured"].fillna(county_mean).clip(lower=0.0, upper=1.0)
    if had_missing:
        return mark_estimated(gdf, "vuln_uninsured", method=f"{provenance}; fill missing with county mean")
    return mark_real(gdf, "vuln_uninsured", source=provenance)


def compute_res_vehicle_access_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """Resilience input: vehicle access share (higher = more evacuation capacity)."""
    tmp = compute_vuln_vehicle_access_real(gdf.copy())
    # The helper already marks/copies provenance for vuln_vehicle_access. Mirror into res_vehicle_access.
    gdf["res_vehicle_access"] = pd.to_numeric(tmp.get("vuln_vehicle_access"), errors="coerce")
    if "vuln_vehicle_access_source" in tmp.columns:
        gdf["res_vehicle_access_source"] = tmp["vuln_vehicle_access_source"]
    if "vuln_vehicle_access_provenance" in tmp.columns:
        gdf["res_vehicle_access_provenance"] = tmp["vuln_vehicle_access_provenance"]
    # If vehicle access is missing entirely, fall back to dummy.
    if gdf["res_vehicle_access"].notna().sum() == 0:
        gdf["res_vehicle_access"] = 0.0
        return mark_missing(gdf, "res_vehicle_access", reason="No vehicle access available")
    return gdf


def compute_res_median_household_income_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """Resilience input: ACS median household income (B19013_001E)."""
    if "GEOID" not in gdf.columns:
        gdf["res_median_household_income"] = 0.0
        return mark_missing(gdf, "res_median_household_income", reason="No GEOID column")
    bg_col = block_group_geoid_series(gdf)
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_median_household_income.csv")
        provenance = "local_acs_median_household_income.csv"
    else:
        fields = ["B19013_001E", "GEOID"]
        st, co = _get_state_county_codes()
        acs = fetch_acs_blockgroup(fields, "block group:*", f"state:{st} county:{co}")
        provenance = "ACS API"
        if acs is not None:
            county_fips = _get_county_fips()
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id="median_household_income"),
                acs,
                response_json=json.loads(acs.to_json(orient="records")),
                request={"api": ACS_URL, "params": {"in": f"state:{st} county:{co}"}},
                overwrite=True,
            )
    if acs is None:
        gdf["res_median_household_income"] = 0.0
        return mark_missing(gdf, "res_median_household_income", reason="No real data available")
    if "B19013_001E" in acs.columns:
        acs["B19013_001E"] = pd.to_numeric(acs["B19013_001E"], errors="coerce")
        acs.loc[acs["B19013_001E"] == -666666666, "B19013_001E"] = np.nan
    income_map = dict(zip(acs["GEOID"].astype(str), acs["B19013_001E"]))
    gdf["blockgroup"] = bg_col
    gdf["res_median_household_income"] = pd.to_numeric(gdf["blockgroup"].map(income_map), errors="coerce").astype("float64")
    county_mean = float(pd.to_numeric(acs["B19013_001E"], errors="coerce").dropna().mean()) if acs["B19013_001E"].notna().any() else 0.0
    had_missing = gdf["res_median_household_income"].isna().any()
    gdf["res_median_household_income"] = gdf["res_median_household_income"].fillna(county_mean).clip(lower=0.0)
    if had_missing:
        return mark_estimated(gdf, "res_median_household_income", method=f"{provenance}; fill missing with county mean")
    return mark_real(gdf, "res_median_household_income", source=provenance)


def compute_res_internet_access_real(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Resilience input: internet access share from ACS B28002.
      internet_access = 1 - (B28002_013E / B28002_001E)
    """
    if "GEOID" not in gdf.columns:
        gdf["res_internet_access"] = 0.0
        return mark_missing(gdf, "res_internet_access", reason="No GEOID column")
    bg_col = block_group_geoid_series(gdf)
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_internet_access.csv")
        provenance = "local_acs_internet_access.csv"
    else:
        fields = ["B28002_001E", "B28002_013E", "GEOID"]
        st, co = _get_state_county_codes()
        acs = fetch_acs_blockgroup(fields, "block group:*", f"state:{st} county:{co}")
        provenance = "ACS API"
        if acs is not None:
            county_fips = _get_county_fips()
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id="internet_access"),
                acs,
                response_json=json.loads(acs.to_json(orient="records")),
                request={"api": ACS_URL, "params": {"in": f"state:{st} county:{co}"}},
                overwrite=True,
            )
    if acs is None:
        gdf["res_internet_access"] = 0.0
        return mark_missing(gdf, "res_internet_access", reason="No real data available")
    for c in ["B28002_001E", "B28002_013E"]:
        if c in acs.columns:
            acs[c] = pd.to_numeric(acs[c], errors="coerce")
    denom = acs["B28002_001E"].replace({0: np.nan})
    acs["internet_access"] = 1 - (acs["B28002_013E"] / denom)
    ia_map = dict(zip(acs["GEOID"].astype(str), acs["internet_access"]))
    gdf["blockgroup"] = bg_col
    gdf["res_internet_access"] = pd.to_numeric(gdf["blockgroup"].map(ia_map), errors="coerce")
    county_mean = float(pd.to_numeric(acs["internet_access"], errors="coerce").dropna().mean()) if acs["internet_access"].notna().any() else 0.0
    had_missing = gdf["res_internet_access"].isna().any()
    gdf["res_internet_access"] = gdf["res_internet_access"].fillna(county_mean).clip(lower=0.0, upper=1.0)
    if had_missing:
        return mark_estimated(gdf, "res_internet_access", method=f"{provenance}; fill missing with county mean")
    return mark_real(gdf, "res_internet_access", source=provenance)

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
        gdf["exposure_building_value"] = 0.0
        return mark_missing(gdf, "exposure_building_value", reason="No GEOID column")
    bg_col = block_group_geoid_series(gdf)
    if USE_STORED_REAL_DATA:
        acs = fetch_acs_bg_local("acs_building_value.csv")
        provenance = "local_acs_building_value.csv"
    else:
        fields = ["B25077_001E", "GEOID"]
        st, co = _get_state_county_codes()
        acs = fetch_acs_blockgroup(fields, "block group:*", f"state:{st} county:{co}")
        provenance = "ACS API"
        if acs is not None:
            county_fips = _get_county_fips()
            write_dataset(
                DatasetRef(county_fips=county_fips, source_id="acs_2021_5yr", quantity_id="median_home_value"),
                acs,
                response_json=json.loads(acs.to_json(orient="records")),
                request={"api": ACS_URL, "params": {"in": f"state:{st} county:{co}"}},
                overwrite=True,
            )
    if acs is None:
        gdf["exposure_building_value"] = 0.0
        return mark_missing(gdf, "exposure_building_value", reason="No real data available")
    # Convert only measure columns to numeric; keep GEOID as a string join key.
    if "B25077_001E" in acs.columns:
        acs["B25077_001E"] = pd.to_numeric(acs["B25077_001E"], errors="coerce")
        # ACS missing-value sentinel(s)
        acs.loc[acs["B25077_001E"] == -666666666, "B25077_001E"] = np.nan
    value_map = dict(zip(acs["GEOID"].astype(str), acs["B25077_001E"]))
    gdf["blockgroup"] = bg_col
    median_val = pd.to_numeric(gdf["blockgroup"].map(value_map), errors="coerce").astype("float64")
    housing = pd.to_numeric(gdf.get("exposure_housing", 0), errors="coerce").fillna(0.0).astype("float64")
    # If a BG median is missing, use county mean rather than hard 0 to avoid collapsing EAL.
    county_mean = float(pd.to_numeric(acs["B25077_001E"], errors="coerce").dropna().mean()) if acs["B25077_001E"].notna().any() else 0.0
    had_missing = pd.isna(median_val).any()
    median_val = pd.Series(median_val, index=gdf.index).fillna(county_mean)
    gdf["exposure_building_value"] = (housing * median_val).clip(lower=0.0)
    if had_missing:
        return mark_estimated(
            gdf,
            "exposure_building_value",
            method=f"{provenance}; impute missing BG medians with county mean",
        )
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
    from src.utils.source_tracker import mark_real, mark_missing, mark_proxy
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="whp", quantity_id="wildfire")
    csv_path = ref.data_path
    legacy = Path(os.path.join(REAL_DATA_DIR, "whp_zonal_stats.csv"))
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"block_id": str, "whp_mean": float})
    elif legacy.exists():
        df = pd.read_csv(legacy, dtype={"block_id": str, "whp_mean": float})
    else:
        df = None
    if df is not None:
        gdf = gdf.copy()
        gdf["block_id"] = _block_id_series(gdf, "block_id")
        df = df.copy()
        df["block_id"] = _block_id_series(df, "block_id")
        gdf = gdf.merge(df, on="block_id", how="left")
        gdf["hazard_wildfire"] = gdf["whp_mean"].fillna(0)
        return mark_real(gdf, "hazard_wildfire", source=str(csv_path if csv_path.exists() else legacy))

    # Proxy fallback (REAL): derive wildfire hazard from available landcover proxies.
    #
    # Rationale: WHP rasters can be multi-GB and some environments block direct downloads.
    # If the WHP zonal-stats CSV is missing, we still produce a deterministic, explainable
    # hazard proxy based on (a) vegetation cover and (b) proximity to forest/woodland.
    try:
        from src.utils.calculations_reference import (
            HAZARD_WILDFIRE_PROXY_FOREST_WEIGHT,
            HAZARD_WILDFIRE_PROXY_VEG_WEIGHT,
        )

        gdf2 = compute_hazard_vegetation_real(gdf.copy())
        gdf2 = compute_hazard_forest_distance_real(gdf2)
        veg = pd.to_numeric(gdf2.get("hazard_vegetation"), errors="coerce").fillna(0.0)
        prox = pd.to_numeric(gdf2.get("hazard_forest_distance"), errors="coerce").fillna(0.0)
        wv, wf = HAZARD_WILDFIRE_PROXY_VEG_WEIGHT, HAZARD_WILDFIRE_PROXY_FOREST_WEIGHT
        proxy = (wv * veg + wf * prox).clip(lower=0.0, upper=1.0)
        gdf["hazard_wildfire"] = proxy.astype(float)
        return mark_proxy(
            gdf,
            "hazard_wildfire",
            method=f"{wv}*vegetation + {wf}*forest_proximity (OSM proxy)",
        )
    except Exception:
        gdf["hazard_wildfire"] = 0.0
        return mark_missing(gdf, "hazard_wildfire", reason="No WHP zonal stats CSV found")

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
    from src.utils.source_tracker import mark_missing, mark_proxy
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="nlcd", quantity_id="vegetation")
    csv_path = ref.data_path
    legacy = Path(os.path.join(REAL_DATA_DIR, "nlcd_vegetation.csv"))
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"block_id": str, "nlcd_vegetation": float})
    elif legacy.exists():
        df = pd.read_csv(legacy, dtype={"block_id": str, "nlcd_vegetation": float})
    else:
        df = None
    if df is not None:
        gdf = gdf.copy()
        gdf["block_id"] = _block_id_series(gdf, "block_id")
        df = df.copy()
        df["block_id"] = _block_id_series(df, "block_id")
        gdf = gdf.merge(df, on="block_id", how="left")
        gdf["hazard_vegetation"] = gdf["nlcd_vegetation"].fillna(0)
        return mark_proxy(gdf, "hazard_vegetation", method="OSM landcover proxy (generated CSV)")

    # If per-county cache is missing, compute a deterministic OSM-based proxy on the fly
    # (same approach as scripts/process_nlcd_vegetation.py), and write it to real_cache
    # so future runs do not re-query OSM.
    try:
        import geopandas as gpd  # type: ignore
        import osmnx as ox  # type: ignore

        blocks = gpd.GeoDataFrame(gdf.copy(), geometry="geometry", crs=getattr(gdf, "crs", None))
        if blocks.crs is None:
            # Most pipeline frames are already in EPSG:4326; assume that if CRS is missing.
            blocks = blocks.set_crs(4326, allow_override=True)
        blocks_ll = blocks.to_crs(4326)
        minx, miny, maxx, maxy = blocks_ll.total_bounds
        pad = 0.02
        bbox = (minx - pad, miny - pad, maxx + pad, maxy + pad)

        tags_list = [
            {"landuse": "forest"},
            {"natural": "wood"},
            {"natural": "scrub"},
            {"landuse": "meadow"},
            {"leisure": "nature_reserve"},
            {"boundary": "national_park"},
        ]
        frames: list[gpd.GeoDataFrame] = []
        for tags in tags_list:
            try:
                f = ox.features_from_bbox(bbox, tags=tags)
                if f is None or len(f) == 0:
                    continue
                f = f.reset_index(drop=True)
                frames.append(f)
            except Exception:
                continue

        if frames:
            forest = pd.concat(frames, ignore_index=True)
            forest = gpd.GeoDataFrame(forest, geometry="geometry", crs="EPSG:4326")
            forest = forest[forest.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        else:
            forest = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

        blocks_m = blocks_ll.to_crs(3857)
        if len(forest) == 0:
            ratio = pd.Series(0.0, index=blocks_m.index, dtype="float64")
        else:
            forest_m = forest.to_crs(3857)
            forest_union = forest_m.geometry.unary_union
            block_area = blocks_m.geometry.area
            inter_area = blocks_m.geometry.intersection(forest_union).area
            ratio = (inter_area / block_area).fillna(0.0).clip(lower=0.0, upper=1.0).astype("float64")

        out_df = pd.DataFrame({"block_id": _block_id_series(blocks, "block_id"), "nlcd_vegetation": ratio.astype(float).values})
        write_dataset(
            ref,
            out_df,
            response_json={"generated": True, "method": "OSM polygons (live)"},
            request={"generator": "src/utils/real_data.py:compute_hazard_vegetation_real"},
            schema={"columns": ["block_id", "nlcd_vegetation"], "join_key": "block_id"},
            overwrite=True,
        )

        gdf = gdf.copy()
        gdf["hazard_vegetation"] = ratio.astype(float).values
        return mark_proxy(gdf, "hazard_vegetation", method="OSM polygons proxy (auto-cached)")
    except Exception:
        gdf["hazard_vegetation"] = 0.0
        return mark_missing(gdf, "hazard_vegetation", reason="No vegetation proxy available")

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
    from src.utils.source_tracker import mark_missing, mark_proxy
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="nlcd", quantity_id="forest_distance")
    csv_path = ref.data_path
    legacy = Path(os.path.join(REAL_DATA_DIR, "nlcd_forest_distance.csv"))
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"block_id": str, "nlcd_forest_distance": float})
    elif legacy.exists():
        df = pd.read_csv(legacy, dtype={"block_id": str, "nlcd_forest_distance": float})
    else:
        df = None
    if df is not None:
        gdf = gdf.copy()
        gdf["block_id"] = _block_id_series(gdf, "block_id")
        df = df.copy()
        df["block_id"] = _block_id_series(df, "block_id")
        gdf = gdf.merge(df, on="block_id", how="left")
        gdf["hazard_forest_distance"] = gdf["nlcd_forest_distance"].fillna(0)
        return mark_proxy(gdf, "hazard_forest_distance", method="OSM forest-distance proxy (generated CSV)")

    # On-the-fly OSM proxy + auto-cache (same approach as scripts/process_nlcd_forest_distance.py).
    try:
        import geopandas as gpd  # type: ignore
        import osmnx as ox  # type: ignore

        blocks = gpd.GeoDataFrame(gdf.copy(), geometry="geometry", crs=getattr(gdf, "crs", None))
        if blocks.crs is None:
            blocks = blocks.set_crs(4326, allow_override=True)
        blocks_ll = blocks.to_crs(4326)
        minx, miny, maxx, maxy = blocks_ll.total_bounds
        pad = 0.02
        bbox = (minx - pad, miny - pad, maxx + pad, maxy + pad)

        tags_list = [
            {"landuse": "forest"},
            {"natural": "wood"},
            {"natural": "scrub"},
            {"leisure": "nature_reserve"},
            {"boundary": "national_park"},
        ]

        frames: list[gpd.GeoDataFrame] = []
        for tags in tags_list:
            try:
                f = ox.features_from_bbox(bbox, tags=tags)
                if f is None or len(f) == 0:
                    continue
                frames.append(f.reset_index(drop=True))
            except Exception:
                continue

        if frames:
            forest = pd.concat(frames, ignore_index=True)
            forest = gpd.GeoDataFrame(forest, geometry="geometry", crs="EPSG:4326")
            forest = forest[forest.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        else:
            forest = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

        blocks_m = blocks_ll.to_crs(3857)
        if len(forest) == 0:
            inv = pd.Series(0.0, index=blocks_m.index, dtype="float64")
        else:
            forest_m = forest.to_crs(3857)
            forest_union = forest_m.geometry.unary_union
            centroids = blocks_m.geometry.centroid
            dist_km = centroids.distance(forest_union) / 1000.0
            inv = (1.0 / (1.0 + dist_km)).fillna(0.0).astype("float64")

        out_df = pd.DataFrame({"block_id": _block_id_series(blocks, "block_id"), "nlcd_forest_distance": inv.astype(float).values})
        write_dataset(
            ref,
            out_df,
            response_json={"generated": True, "method": "OSM polygons (live)"},
            request={"generator": "src/utils/real_data.py:compute_hazard_forest_distance_real"},
            schema={"columns": ["block_id", "nlcd_forest_distance"], "join_key": "block_id"},
            overwrite=True,
        )

        gdf = gdf.copy()
        gdf["hazard_forest_distance"] = inv.astype(float).values
        return mark_proxy(gdf, "hazard_forest_distance", method="OSM polygons distance proxy (auto-cached)")
    except Exception:
        gdf["hazard_forest_distance"] = 0.0
        return mark_missing(gdf, "hazard_forest_distance", reason="No forest-distance proxy available")

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
    from src.utils.source_tracker import mark_real, mark_missing
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="hifld", quantity_id="fire_stations_distance")
    csv_path = ref.data_path
    legacy = Path(os.path.join(REAL_DATA_DIR, "fire_station_dist.csv"))
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"block_id": str, "fire_station_dist": float})
    elif legacy.exists():
        df = pd.read_csv(legacy, dtype={"block_id": str, "fire_station_dist": float})
    else:
        df = None
    if df is not None:
        gdf = gdf.copy()
        gdf["block_id"] = _block_id_series(gdf, "block_id")
        df = df.copy()
        df["block_id"] = _block_id_series(df, "block_id")
        gdf = gdf.merge(df, on="block_id", how="left")
        # Invert and scale: 1/(1+distance_km)
        gdf["res_fire_station_dist"] = 1 / (1 + gdf["fire_station_dist"].fillna(0))
        return mark_real(gdf, "res_fire_station_dist", source=str(csv_path if csv_path.exists() else legacy))
    gdf["res_fire_station_dist"] = 0.0
    return mark_missing(gdf, "res_fire_station_dist", reason="No fire station dist CSV found")

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
    from src.utils.source_tracker import mark_real, mark_missing
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="hifld", quantity_id="hospitals_distance")
    csv_path = ref.data_path
    legacy = Path(os.path.join(REAL_DATA_DIR, "hospital_dist.csv"))
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"block_id": str, "hospital_dist": float})
    elif legacy.exists():
        df = pd.read_csv(legacy, dtype={"block_id": str, "hospital_dist": float})
    else:
        df = None
    if df is not None:
        gdf = gdf.copy()
        gdf["block_id"] = _block_id_series(gdf, "block_id")
        df = df.copy()
        df["block_id"] = _block_id_series(df, "block_id")
        gdf = gdf.merge(df, on="block_id", how="left")
        # Invert and scale: 1/(1+distance_km)
        gdf["res_hospital_dist"] = 1 / (1 + gdf["hospital_dist"].fillna(0))
        return mark_real(gdf, "res_hospital_dist", source=str(csv_path if csv_path.exists() else legacy))
    gdf["res_hospital_dist"] = 0.0
    return mark_missing(gdf, "res_hospital_dist", reason="No hospital dist CSV found")

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
    from src.utils.source_tracker import mark_real, mark_missing
    county_fips = _get_county_fips()
    ref = DatasetRef(county_fips=county_fips, source_id="osm", quantity_id="roads_access")
    csv_path = ref.data_path
    legacy = Path(os.path.join(REAL_DATA_DIR, "road_length.csv"))
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"block_id": str, "road_length": float})
    elif legacy.exists():
        df = pd.read_csv(legacy, dtype={"block_id": str, "road_length": float})
    else:
        df = None
    if df is not None:
        gdf = gdf.copy()
        gdf["block_id"] = _block_id_series(gdf, "block_id")
        df = df.copy()
        df["block_id"] = _block_id_series(df, "block_id")
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
        return mark_real(gdf, "res_road_access", source=str(csv_path if csv_path.exists() else legacy))
    gdf["res_road_access"] = 0.0
    return mark_missing(gdf, "res_road_access", reason="No road length CSV found")
