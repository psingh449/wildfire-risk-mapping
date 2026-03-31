"""Data validation utilities"""

from src.utils.logger import get_logger

logger = get_logger()

REQUIRED_COLUMNS = [
    # Hazard
    "hazard_wildfire",
    "hazard_vegetation",
    "hazard_forest_distance",

    # Exposure
    "exposure_population",
    "exposure_housing",
    "exposure_building_value",

    # Vulnerability
    "vuln_poverty",
    "vuln_elderly",
    "vuln_vehicle_access",

    # Resilience
    "res_fire_station_dist",
    "res_hospital_dist",
    "res_road_access",
]

def validate_columns(gdf):
    missing = [col for col in REQUIRED_COLUMNS if col not in gdf.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    logger.info("Validation passed: all required columns present")


def validate_nulls(gdf):
    null_counts = gdf.isnull().sum()
    problematic = null_counts[null_counts > 0]

    if len(problematic) > 0:
        logger.warning(f"Columns with null values: {problematic.to_dict()}")
    else:
        logger.info("Validation passed: no null values")


def validate_ranges(gdf):
    for col in REQUIRED_COLUMNS:
        if col in gdf.columns:
            if gdf[col].dtype != "object":
                if (gdf[col] < 0).any():
                    logger.warning(f"Column {col} has negative values")

    logger.info("Validation check: ranges completed")
