from src.utils.real_data import fallback_uniform
from src.utils.source_tracker import mark_dummy

def compute_res_fire_station_dist(gdf):
    # TODO: Implement real fire station distance calculation
    gdf["res_fire_station_dist"] = fallback_uniform(gdf, "res_fire_station_dist")
    return mark_dummy(gdf, "res_fire_station_dist")

def compute_res_hospital_dist(gdf):
    # TODO: Implement real hospital distance calculation
    gdf["res_hospital_dist"] = fallback_uniform(gdf, "res_hospital_dist")
    return mark_dummy(gdf, "res_hospital_dist")

def compute_res_road_access(gdf):
    # TODO: Implement real road access calculation
    gdf["res_road_access"] = fallback_uniform(gdf, "res_road_access")
    return mark_dummy(gdf, "res_road_access")
