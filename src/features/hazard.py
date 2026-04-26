from src.utils.real_data import (
    compute_hazard_wildfire_real,
    compute_hazard_forest_distance_real,
    compute_hazard_vegetation_real,
)
from src.utils.source_tracker import mark_missing

def compute_hazard_wildfire(gdf):
    try:
        return compute_hazard_wildfire_real(gdf)
    except Exception as e:
        gdf["hazard_wildfire"] = 0.0
        return mark_missing(gdf, "hazard_wildfire", reason=f"real_data_error: {type(e).__name__}")

def compute_hazard_vegetation(gdf):
    try:
        return compute_hazard_vegetation_real(gdf)
    except Exception as e:
        gdf["hazard_vegetation"] = 0.0
        return mark_missing(gdf, "hazard_vegetation", reason=f"real_data_error: {type(e).__name__}")

def compute_hazard_forest_distance(gdf):
    try:
        return compute_hazard_forest_distance_real(gdf)
    except Exception as e:
        gdf["hazard_forest_distance"] = 0.0
        return mark_missing(gdf, "hazard_forest_distance", reason=f"real_data_error: {type(e).__name__}")

def compute_hazard_weather(gdf):
    # Deprecated placeholder; kept only so older notebooks don't break.
    gdf["hazard_weather"] = 0.0
    return mark_missing(gdf, "hazard_weather", reason="deprecated_placeholder")

def compute_hazard_temperature(gdf):
    # Deprecated placeholder; kept only so older notebooks don't break.
    gdf["hazard_temperature"] = 0.0
    return mark_missing(gdf, "hazard_temperature", reason="deprecated_placeholder")

def compute_hazard_wind(gdf):
    # Deprecated placeholder; kept only so older notebooks don't break.
    gdf["hazard_wind"] = 0.0
    return mark_missing(gdf, "hazard_wind", reason="deprecated_placeholder")
