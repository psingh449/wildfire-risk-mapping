from src.utils.real_data import fallback_uniform, compute_res_fire_station_dist_real, compute_res_hospital_dist_real, compute_res_road_access_real
from src.utils.source_tracker import mark_dummy

def compute_res_fire_station_dist(gdf):
    try:
        return compute_res_fire_station_dist_real(gdf)
    except Exception as e:
        gdf["res_fire_station_dist"] = fallback_uniform(gdf, "res_fire_station_dist")
        return mark_dummy(gdf, "res_fire_station_dist")

def compute_res_hospital_dist(gdf):
    try:
        return compute_res_hospital_dist_real(gdf)
    except Exception as e:
        gdf["res_hospital_dist"] = fallback_uniform(gdf, "res_hospital_dist")
        return mark_dummy(gdf, "res_hospital_dist")

def compute_res_road_access(gdf):
    try:
        return compute_res_road_access_real(gdf)
    except Exception as e:
        gdf["res_road_access"] = fallback_uniform(gdf, "res_road_access")
        return mark_dummy(gdf, "res_road_access")
