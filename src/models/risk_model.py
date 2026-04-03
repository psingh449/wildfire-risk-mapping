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

    # EAL: risk_score * building_value_est
    gdf["eal"] = gdf["risk_score"] * gdf.get("building_value_est", 0)

    # Normalize EAL for visualization
    min_eal = gdf["eal"].min()
    max_eal = gdf["eal"].max()
    gdf["eal_norm"] = (gdf["eal"] - min_eal) / (max_eal - min_eal + EPSILON)

    return gdf
