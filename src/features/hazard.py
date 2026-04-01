
from src.utils.dummy_data import generate_uniform

def compute_hazard_wildfire(gdf):
    gdf["hazard_wildfire"] = generate_uniform(0, 1, len(gdf))
    return gdf

def compute_hazard_vegetation(gdf):
    gdf["hazard_vegetation"] = generate_uniform(0, 1, len(gdf))
    return gdf

def compute_hazard_forest_distance(gdf):
    gdf["hazard_forest_distance"] = generate_uniform(0, 50, len(gdf))
    return gdf
