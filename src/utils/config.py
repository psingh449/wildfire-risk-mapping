"""Central configuration for the project"""

# Paths
OUTPUT_GEOJSON = "data/processed/blocks.geojson"
REAL_DATA_DIR = "data/real"

# Real data usage flag
USE_STORED_REAL_DATA = True  # Set to False to fetch live from APIs and refresh local CSVs

# Numerical stability
EPSILON = 1e-6

# Weights (fallback defaults).
# The pipeline prefers per-component weights loaded from `calculations.csv` when available
# (see `src/features/build_features.py::_load_component_weights_from_calculations`).
HAZARD_WEIGHTS = {
    "hazard_wildfire_norm": 0.2713,
    "hazard_vegetation_norm": 0.3044,
    "hazard_forest_distance_norm": 0.4243,
}

EXPOSURE_WEIGHTS = {
    "exposure_population_norm": 1/3,
    "exposure_housing_norm": 1/3,
    "exposure_building_value_norm": 1/3
}

VULNERABILITY_WEIGHTS = {
    "vuln_uninsured_norm": 0.3972,
    "vuln_poverty_norm": 0.3903,
    "vuln_elderly_norm": 0.2126,
}

RESILIENCE_WEIGHTS = {
    "res_internet_access_norm": 0.5272,
    "res_median_household_income_norm": 0.3967,
    "res_vehicle_access_norm": 0.0761,
}
