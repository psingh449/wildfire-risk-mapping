from src.utils.config import (
    HAZARD_WEIGHTS,
    EXPOSURE_WEIGHTS,
    VULNERABILITY_WEIGHTS,
    RESILIENCE_WEIGHTS
)

def minmax(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9)

def weighted_sum(df, weights):
    return sum(df[col] * w for col, w in weights.items())

def build_features(gdf):

    # 1. Normalize into *_norm (preserve raw)
    for col in gdf.columns:
        if col.startswith(("hazard_", "exposure_", "vuln_", "res_")):
            if col == "exposure_population":
                continue
            gdf[f"{col}_norm"] = minmax(gdf[col])

    if "exposure_population" in gdf.columns:
        gdf["exposure_population_norm"] = minmax(gdf["exposure_population"])

    # 2. Inversions on normalized fields
    if "hazard_forest_distance_norm" in gdf:
        gdf["hazard_forest_distance_norm"] = 1 - gdf["hazard_forest_distance_norm"]

    if "res_fire_station_dist_norm" in gdf:
        gdf["res_fire_station_dist_norm"] = 1 - gdf["res_fire_station_dist_norm"]

    if "res_hospital_dist_norm" in gdf:
        gdf["res_hospital_dist_norm"] = 1 - gdf["res_hospital_dist_norm"]

    if "vuln_vehicle_access_norm" in gdf:
        gdf["vuln_vehicle_access_norm"] = 1 - gdf["vuln_vehicle_access_norm"]

    # 3. Component scores (all use *_norm via config)
    gdf["hazard_score"] = weighted_sum(gdf, HAZARD_WEIGHTS)
    gdf["exposure_score"] = weighted_sum(gdf, EXPOSURE_WEIGHTS)
    gdf["vulnerability_score"] = weighted_sum(gdf, VULNERABILITY_WEIGHTS)
    gdf["resilience_score"] = weighted_sum(gdf, RESILIENCE_WEIGHTS)

    # Safety checks (0-1)
    # Clip for numerical safety
    for c in ["hazard_score","exposure_score","vulnerability_score","resilience_score"]:
        gdf[c] = gdf[c].clip(0,1)

    # 4. Economic exposure proxy (raw dollars)
    AVG_HOME_VALUE = 300000  # placeholder
    if "exposure_housing" in gdf.columns:
        gdf["building_value_est"] = gdf["exposure_housing"] * AVG_HOME_VALUE
    else:
        gdf["building_value_est"] = 0

    # 5. Risk score (multiplicative, bounded 0-1)
    gdf["risk_score"] = (
        gdf["hazard_score"] *
        gdf["exposure_score"] *
        gdf["vulnerability_score"] *
        (1 - gdf["resilience_score"])
    ).clip(0,1)

    # 6. Expected Annual Loss (EAL)
    gdf["eal"] = gdf["risk_score"] * gdf["building_value_est"]

    # Normalize EAL for visualization
    gdf["eal_norm"] = minmax(gdf["eal"])

    return gdf
