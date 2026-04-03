from src.utils.real_data import compute_exposure_population_real, compute_exposure_housing_real, fallback_int, fallback_uniform
from src.utils.source_tracker import mark_real, mark_dummy

def compute_exposure_population(gdf):
    try:
        return compute_exposure_population_real(gdf)
    except Exception as e:
        gdf["exposure_population"] = fallback_int(gdf, "exposure_population")
        return mark_dummy(gdf, "exposure_population")

def compute_exposure_housing(gdf):
    try:
        return compute_exposure_housing_real(gdf)
    except Exception as e:
        gdf["exposure_housing"] = fallback_int(gdf, "exposure_housing")
        return mark_dummy(gdf, "exposure_housing")

def compute_exposure_building_value(gdf):
    # TODO: Implement real building value calculation
    gdf["exposure_building_value"] = fallback_uniform(gdf, "exposure_building_value")
    return mark_dummy(gdf, "exposure_building_value")
