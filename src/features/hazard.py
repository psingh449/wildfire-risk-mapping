
from src.utils.dummy_data import generate_uniform
from src.utils.source_tracker import mark_dummy

def compute_hazard_wildfire(gdf):
    gdf["hazard_wildfire"] = generate_uniform(0, 1, len(gdf))
    return mark_dummy(gdf, "hazard_wildfire")

def compute_hazard_vegetation(gdf):
    gdf["hazard_vegetation"] = generate_uniform(0, 1, len(gdf))
    return mark_dummy(gdf, "hazard_vegetation")

def compute_hazard_forest_distance(gdf):
    gdf["hazard_forest_distance"] = generate_uniform(0, 50, len(gdf))
    return mark_dummy(gdf, "hazard_forest_distance")

def compute_hazard_weather(gdf):
    gdf["hazard_weather"] = generate_uniform(0, 1, len(gdf))
    return mark_dummy(gdf, "hazard_weather")

def compute_hazard_temperature(gdf):
    gdf["hazard_temperature"] = generate_uniform(0, 1, len(gdf))
    return mark_dummy(gdf, "hazard_temperature")

def compute_hazard_wind(gdf):
    gdf["hazard_wind"] = generate_uniform(0, 1, len(gdf))
    return mark_dummy(gdf, "hazard_wind")
