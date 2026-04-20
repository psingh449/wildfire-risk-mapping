import logging
import pandas as pd
from typing import Optional
logger = logging.getLogger("provenance")

REAL = "REAL"
ESTIMATED = "ESTIMATED"
PROXY = "PROXY"
MISSING = "MISSING"
DUMMY = "DUMMY"


def _set(gdf: pd.DataFrame, column: str, source: str, provenance: Optional[str]) -> pd.DataFrame:
    gdf[f"{column}_source"] = source
    if provenance:
        gdf[f"{column}_provenance"] = provenance
    else:
        gdf[f"{column}_provenance"] = source
    if f"{column}_provenance" not in gdf.columns:
        gdf[f"{column}_provenance"] = source
    return gdf


def mark_real(gdf: pd.DataFrame, column: str, source: Optional[str] = None) -> pd.DataFrame:
    """
    Mark a column as REAL and set provenance.
    Args:
        gdf: DataFrame
        column: Column name
        source: Provenance/source string
    Returns:
        DataFrame with provenance columns set
    """
    _set(gdf, column, REAL, source)
    if source:
        logger.info(f"{column}: REAL from {source}")
    else:
        logger.info(f"{column}: REAL")
    return gdf


def mark_estimated(gdf: pd.DataFrame, column: str, method: Optional[str] = None) -> pd.DataFrame:
    """
    Mark a column as ESTIMATED (derived from coarser geography or imputation).
    """
    _set(gdf, column, ESTIMATED, method)
    if method:
        logger.info(f"{column}: ESTIMATED ({method})")
    else:
        logger.info(f"{column}: ESTIMATED")
    return gdf


def mark_proxy(gdf: pd.DataFrame, column: str, method: Optional[str] = None) -> pd.DataFrame:
    """
    Mark a column as PROXY (computed from a proxy datasource, e.g. OSM landcover proxy).
    """
    _set(gdf, column, PROXY, method)
    if method:
        logger.info(f"{column}: PROXY ({method})")
    else:
        logger.info(f"{column}: PROXY")
    return gdf


def mark_missing(gdf: pd.DataFrame, column: str, reason: Optional[str] = None) -> pd.DataFrame:
    """
    Mark a column as MISSING (no defensible estimate available).
    """
    prov = f"{MISSING}: {reason}" if reason else MISSING
    _set(gdf, column, MISSING, prov)
    if reason:
        logger.warning(f"{column}: MISSING ({reason})")
    else:
        logger.warning(f"{column}: MISSING")
    return gdf

def mark_dummy(gdf: pd.DataFrame, column: str, reason: Optional[str] = None) -> pd.DataFrame:
    """
    Mark a column as DUMMY and set provenance.
    Args:
        gdf: DataFrame
        column: Column name
        reason: Reason for fallback
    Returns:
        DataFrame with provenance columns set
    """
    prov = f"{DUMMY}: {reason}" if reason else DUMMY
    _set(gdf, column, DUMMY, prov)
    if reason:
        logger.warning(f"{column}: DUMMY ({reason})")
    else:
        logger.warning(f"{column}: DUMMY")
    return gdf
