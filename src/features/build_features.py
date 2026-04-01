from src.utils.config import (
    HAZARD_WEIGHTS,
    EXPOSURE_WEIGHTS,
    VULNERABILITY_WEIGHTS,
    RESILIENCE_WEIGHTS
)

# -------------------------------
# Utility functions
# -------------------------------

def minmax(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9)


def weighted_sum(df, weights):
    return sum(df[col] * w for col, w in weights.items())


# -------------------------------
# Feature Engineering
# -------------------------------

def build_features(gdf):

    # -------------------------------
    # 1. Normalize ONLY into *_norm columns
    # -------------------------------

    for col in gdf.columns:
        if col.startswith(("hazard_", "exposure_", "vuln_", "res_")):

            # 🚫 Skip raw population (keep as-is)
            if col == "exposure_population":
                continue

            norm_col = f"{col}_norm"
            gdf[norm_col] = minmax(gdf[col])

    # Explicit normalization for population
    if "exposure_population" in gdf.columns:
        gdf["exposure_population_norm"] = minmax(gdf["exposure_population"])

    # -------------------------------
    # 2. Inversions (apply on normalized fields)
    # -------------------------------

    # Hazard: closer distance = higher risk
    if "hazard_forest_distance_norm" in gdf.columns:
        gdf["hazard_forest_distance_norm"] = 1 - gdf["hazard_forest_distance_norm"]

    # Resilience: shorter distance = better resilience
    if "res_fire_station_dist_norm" in gdf.columns:
        gdf["res_fire_station_dist_norm"] = 1 - gdf["res_fire_station_dist_norm"]

    if "res_hospital_dist_norm" in gdf.columns:
        gdf["res_hospital_dist_norm"] = 1 - gdf["res_hospital_dist_norm"]

    # Vulnerability: better access → lower vulnerability
    if "vuln_vehicle_access_norm" in gdf.columns:
        gdf["vuln_vehicle_access_norm"] = 1 - gdf["vuln_vehicle_access_norm"]

    # -------------------------------
    # 3. Compute component scores
    # -------------------------------

    gdf["hazard_score"] = weighted_sum(gdf, HAZARD_WEIGHTS)
    gdf["exposure_score"] = weighted_sum(gdf, EXPOSURE_WEIGHTS)
    gdf["vulnerability_score"] = weighted_sum(gdf, VULNERABILITY_WEIGHTS)
    gdf["resilience_score"] = weighted_sum(gdf, RESILIENCE_WEIGHTS)

    assert gdf["hazard_score"].between(0, 1).all()
    assert gdf["exposure_score"].between(0, 1).all()
    assert gdf["resilience_score"].between(0, 1).all()

    return gdf