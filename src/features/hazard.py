from src.utils.real_data import compute_hazard_wildfire_real
from src.utils.real_data import fallback_uniform
from src.utils.source_tracker import mark_dummy

def compute_hazard_wildfire(gdf):
    # Try real data, fallback to dummy
    try:
        return compute_hazard_wildfire_real(gdf)
    except Exception as e:
        gdf["hazard_wildfire"] = fallback_uniform(gdf, "hazard_wildfire")
        return mark_dummy(gdf, "hazard_wildfire")

def compute_hazard_vegetation(gdf):
    # TODO: Implement real vegetation calculation
    gdf["hazard_vegetation"] = fallback_uniform(gdf, "hazard_vegetation")
    return mark_dummy(gdf, "hazard_vegetation")

def compute_hazard_forest_distance(gdf):
    # TODO: Implement real forest distance calculation
    gdf["hazard_forest_distance"] = fallback_uniform(gdf, "hazard_forest_distance")
    return mark_dummy(gdf, "hazard_forest_distance")

def compute_hazard_weather(gdf):
    gdf["hazard_weather"] = fallback_uniform(gdf, "hazard_weather")
    return mark_dummy(gdf, "hazard_weather")

def compute_hazard_temperature(gdf):
    gdf["hazard_temperature"] = fallback_uniform(gdf, "hazard_temperature")
    return mark_dummy(gdf, "hazard_temperature")

def compute_hazard_wind(gdf):
    gdf["hazard_wind"] = fallback_uniform(gdf, "hazard_wind")
    return mark_dummy(gdf, "hazard_wind")
