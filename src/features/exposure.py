from src.utils.real_data import (
    compute_exposure_population_real,
    compute_exposure_housing_real,
    compute_exposure_building_value_real,
)
from src.utils.source_tracker import mark_missing

def compute_exposure_population(gdf):
    try:
        return compute_exposure_population_real(gdf)
    except Exception as e:
        gdf["exposure_population"] = 0
        return mark_missing(gdf, "exposure_population", reason=f"real_data_error: {type(e).__name__}")

def compute_exposure_housing(gdf):
    try:
        return compute_exposure_housing_real(gdf)
    except Exception as e:
        gdf["exposure_housing"] = 0
        return mark_missing(gdf, "exposure_housing", reason=f"real_data_error: {type(e).__name__}")

def compute_exposure_building_value(gdf):
    try:
        return compute_exposure_building_value_real(gdf)
    except Exception as e:
        gdf["exposure_building_value"] = 0.0
        return mark_missing(gdf, "exposure_building_value", reason=f"real_data_error: {type(e).__name__}")
