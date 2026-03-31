"""Central configuration for the project"""

# Paths
OUTPUT_GEOJSON = "data/processed/blocks.geojson"

# Numerical stability
EPSILON = 1e-6

# Weights (equal for now but configurable later)
HAZARD_WEIGHTS = {
    "hazard_wildfire": 1/3,
    "hazard_vegetation": 1/3,
    "hazard_forest_distance": 1/3,
}

EXPOSURE_WEIGHTS = {
    "exposure_population_norm": 1/3,
    "exposure_housing": 1/3,
    "exposure_building_value": 1/3,
}

VULNERABILITY_WEIGHTS = {
    "vuln_poverty": 1/3,
    "vuln_elderly": 1/3,
    "vuln_vehicle_access": 1/3,
}

RESILIENCE_WEIGHTS = {
    "res_fire_station_dist": 1/3,
    "res_hospital_dist": 1/3,
    "res_road_access": 1/3,
}
