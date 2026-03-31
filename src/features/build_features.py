def minmax(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9)

def build_features(gdf):

    for col in gdf.columns:
        if col.startswith(("hazard_", "exposure_", "vuln_", "res_")):
            gdf[col] = minmax(gdf[col])

    # Inversions
    gdf["hazard_forest_distance"] = 1 - gdf["hazard_forest_distance"]
    gdf["res_fire_station_dist"] = 1 - gdf["res_fire_station_dist"]
    gdf["res_hospital_dist"] = 1 - gdf["res_hospital_dist"]
    gdf["vuln_vehicle_access"] = 1 - gdf["vuln_vehicle_access"]

    # Component scores
    gdf["hazard_score"] = gdf[
        ["hazard_wildfire", "hazard_vegetation", "hazard_forest_distance"]
    ].mean(axis=1)

    gdf["exposure_score"] = gdf[
        ["exposure_population", "exposure_housing", "exposure_building_value"]
    ].mean(axis=1)

    gdf["vulnerability_score"] = gdf[
        ["vuln_poverty", "vuln_elderly", "vuln_vehicle_access"]
    ].mean(axis=1)

    gdf["resilience_score"] = gdf[
        ["res_fire_station_dist", "res_hospital_dist", "res_road_access"]
    ].mean(axis=1)

    return gdf
