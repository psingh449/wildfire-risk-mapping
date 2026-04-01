
from src.utils.dummy_data import generate_uniform

def compute_res_fire_station_dist(gdf):
    gdf["res_fire_station_dist"] = generate_uniform(0, 30, len(gdf))
    return gdf

def compute_res_hospital_dist(gdf):
    gdf["res_hospital_dist"] = generate_uniform(0, 50, len(gdf))
    return gdf

def compute_res_road_access(gdf):
    gdf["res_road_access"] = generate_uniform(0, 1, len(gdf))
    return gdf
