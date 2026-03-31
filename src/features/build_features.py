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

    # Normalize
    for col in gdf.columns:
        if col.startswith(("hazard_", "exposure_", "vuln_", "res_")):
            gdf[col] = minmax(gdf[col])

    # Inversions
    gdf["hazard_forest_distance"] = 1 - gdf["hazard_forest_distance"]
    gdf["res_fire_station_dist"] = 1 - gdf["res_fire_station_dist"]
    gdf["res_hospital_dist"] = 1 - gdf["res_hospital_dist"]
    gdf["vuln_vehicle_access"] = 1 - gdf["vuln_vehicle_access"]

    # Weighted component scores
    gdf["hazard_score"] = weighted_sum(gdf, HAZARD_WEIGHTS)
    gdf["exposure_score"] = weighted_sum(gdf, EXPOSURE_WEIGHTS)
    gdf["vulnerability_score"] = weighted_sum(gdf, VULNERABILITY_WEIGHTS)
    gdf["resilience_score"] = weighted_sum(gdf, RESILIENCE_WEIGHTS)

    return gdf
