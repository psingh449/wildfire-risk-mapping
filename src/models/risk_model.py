import numpy as np
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
    eal_s = pd.to_numeric(gdf["eal"], errors="coerce").fillna(0.0).astype("float64")
    min_eal = float(eal_s.min())
    max_eal = float(eal_s.max())
    if (not np.isfinite(min_eal) or not np.isfinite(max_eal)) or (max_eal == min_eal):
        # One block / constant EAL: avoid 0/ε → 0. If all EAL are zero, keep 0; else use neutral 0.5.
        gdf["eal_norm"] = 0.0 if max_eal == 0.0 else 0.5
    else:
        gdf["eal_norm"] = ((eal_s - min_eal) / (max_eal - min_eal + EPSILON)).clip(0.0, 1.0)

    return gdf
