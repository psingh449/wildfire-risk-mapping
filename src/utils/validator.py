"""Data validation utilities"""

import numpy as np
import pandas as pd
from typing import Any
from src.utils.logger import get_logger

logger = get_logger()

INGESTION_REQUIRED = ["GEOID", "geometry", "block_id"]

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
    "vuln_uninsured",
    # Resilience
    "res_vehicle_access",
    "res_median_household_income",
    "res_internet_access",
]

NORMALIZED_FIELDS = [
    "hazard_wildfire", "hazard_vegetation", "hazard_forest_distance",
    "hazard_score", "exposure_score", "vulnerability_score", "resilience_score",
    "vuln_poverty", "vuln_elderly", "vuln_uninsured",
    # Note: res_median_household_income is in USD (not 0-1); only its *_norm column is 0-1.
    "res_vehicle_access", "res_internet_access",
    "eal_norm", "risk_score"
]

CRITICAL_FIELDS = [
    "hazard_score", "exposure_score", "vulnerability_score", "resilience_score", "risk_score", "eal"
]


def validate_ingestion_schema(gdf: pd.DataFrame) -> None:
    missing = [col for col in INGESTION_REQUIRED if col not in gdf.columns]
    if missing:
        logger.warning(f"Missing ingestion columns: {missing}")
    else:
        logger.info("Validation passed: ingestion schema (GEOID, geometry, block_id)")


def validate_ingestion_nulls(gdf: pd.DataFrame) -> None:
    for col in ("GEOID", "geometry"):
        if col in gdf.columns and gdf[col].isnull().any():
            logger.warning(f"Ingestion: null values in {col}")
    logger.info("Validation check: ingestion nulls completed")


def validate_columns(gdf: pd.DataFrame) -> None:
    """
    Check for missing required columns in the DataFrame.
    Logs a warning if any are missing.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in gdf.columns]
    if missing:
        logger.warning(f"Missing required columns: {missing}")
    else:
        logger.info("Validation passed: all required columns present")

def validate_nulls(gdf: pd.DataFrame) -> None:
    """
    Check for null values in the DataFrame.
    Logs a warning if any columns have nulls.
    """
    null_counts = gdf.isnull().sum()
    problematic = null_counts[null_counts > 0]
    if len(problematic) > 0:
        logger.warning(f"Columns with null values: {problematic.to_dict()}")
    else:
        logger.info("Validation passed: no null values")

def validate_ranges(gdf: pd.DataFrame) -> None:
    """
    Check that all normalized fields are within [0, 1].
    Logs a warning if any are out of range.
    """
    for col in NORMALIZED_FIELDS:
        if col in gdf.columns and gdf[col].dtype != "object":
            if (gdf[col] < 0).any() or (gdf[col] > 1).any():
                logger.warning(f"Column {col} has values outside [0, 1]")
    logger.info("Validation check: normalized field ranges completed")

def validate_types(gdf: pd.DataFrame) -> None:
    """
    Check that columns have expected types (int for counts, float for scores).
    Logs a warning if types are incorrect.
    """
    for col in REQUIRED_COLUMNS:
        if col not in gdf.columns:
            continue
        if col in ("exposure_population", "exposure_housing"):
            if not np.issubdtype(gdf[col].dtype, np.integer):
                logger.warning(f"Column {col} is not integer type")
        elif col == "exposure_building_value":
            if not np.issubdtype(gdf[col].dtype, np.floating):
                logger.warning(f"Column {col} is not float type")
        elif col.endswith("score") or col.startswith("hazard_") or col.startswith("vuln_") or col.startswith("res_"):
            if not np.issubdtype(gdf[col].dtype, np.floating):
                logger.warning(f"Column {col} is not float type")
    logger.info("Validation check: types completed")

def validate_provenance(gdf: pd.DataFrame) -> None:
    """
    Check that provenance columns (_source, _provenance) exist for all required fields.
    Logs a warning if any are missing.
    """
    for col in REQUIRED_COLUMNS:
        src_col = f"{col}_source"
        prov_col = f"{col}_provenance"
        if src_col not in gdf.columns:
            logger.warning(f"Missing provenance column: {src_col}")
        if prov_col not in gdf.columns:
            logger.warning(f"Missing provenance column: {prov_col}")
    logger.info("Validation check: provenance completed")

def validate_diagnostics(gdf: pd.DataFrame) -> None:
    """
    Check that diagnostics column exists and is non-null for all rows.
    Logs a warning if missing or null.
    """
    if "diagnostics" not in gdf.columns:
        logger.warning("Missing diagnostics column")
    elif gdf["diagnostics"].isnull().any():
        logger.warning("Some diagnostics entries are null")
    logger.info("Validation check: diagnostics completed")

def validate_consistency(gdf: pd.DataFrame) -> None:
    """
    Placeholder for consistency checks (e.g., derived fields match components).
    """
    logger.info("Validation check: consistency (placeholder)")

def run_all_validations(gdf: pd.DataFrame) -> None:
    """
    Run all validation checks on the DataFrame.
    """
    validate_columns(gdf)
    validate_nulls(gdf)
    validate_ranges(gdf)
    validate_types(gdf)
    validate_provenance(gdf)
    validate_diagnostics(gdf)
    validate_consistency(gdf)
