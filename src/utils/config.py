"""Central configuration for the project"""

# Paths
OUTPUT_GEOJSON = "data/processed/blocks.geojson"

# Numerical stability
EPSILON = 1e-6

# Weights (equal for now but configurable later)
HAZARD_WEIGHTS = {
    "hazard_wildfire_norm": 1/3,
    "hazard_vegetation_norm": 1/3,
    "hazard_forest_distance_norm": 1/3
}

EXPOSURE_WEIGHTS = {
    "exposure_population_norm": 1/3,
    "exposure_housing_norm": 1/3,
    "exposure_building_value_norm": 1/3
}

VULNERABILITY_WEIGHTS = {
    "vuln_poverty_norm": 1/3,
    "vuln_elderly_norm": 1/3,
    "vuln_vehicle_access_norm": 1/3
}

RESILIENCE_WEIGHTS = {
    "res_fire_station_dist_norm": 1/3,
    "res_hospital_dist_norm": 1/3,
    "res_road_access_norm": 1/3
}
