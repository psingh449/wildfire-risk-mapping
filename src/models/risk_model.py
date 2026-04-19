import pandas as pd

from src.utils.config import EPSILON


def compute_risk(gdf):
    # Unified risk calculation (matches build_features.py)
    # Risk = hazard_score * exposure_score * vulnerability_score * (1 - resilience_score)
    gdf["risk_score"] = (
        gdf["hazard_score"] *
        gdf["exposure_score"] *
        gdf["vulnerability_score"] *
        (1 - gdf["resilience_score"])
    ).clip(0, 1)

    # EAL (USD): risk_score * exposure_building_value
    # exposure_building_value = housing_units * ACS median home value (B25077) at block group
    if "exposure_building_value" in gdf.columns:
        bv = pd.to_numeric(gdf["exposure_building_value"], errors="coerce").fillna(0.0).astype("float64")
    else:
        bv = pd.Series(0.0, index=gdf.index, dtype="float64")
    gdf["eal"] = gdf["risk_score"].astype("float64") * bv
    gdf["eal"] = gdf["eal"].clip(lower=0.0)

    # Normalized EAL for maps (canonical name: eal_norm)
    min_eal = float(gdf["eal"].min())
    max_eal = float(gdf["eal"].max())
    gdf["eal_norm"] = (gdf["eal"] - min_eal) / (max_eal - min_eal + EPSILON)
    gdf["eal_norm"] = gdf["eal_norm"].clip(0.0, 1.0)

    return gdf
