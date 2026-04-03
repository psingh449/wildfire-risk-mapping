
from src.utils.dummy_data import generate_uniform, generate_int
from src.utils.source_tracker import mark_real, mark_dummy

def compute_exposure_population(gdf):
    # keep existing real values
    if "exposure_population" not in gdf:
        gdf["exposure_population"] = generate_int(100, 3000, len(gdf))
        gdf = mark_dummy(gdf, "exposure_population")
    else:
        gdf = mark_real(gdf, "exposure_population")
    return gdf

def compute_exposure_housing(gdf):
    gdf["exposure_housing"] = generate_int(50, 1000, len(gdf))
    gdf = mark_dummy(gdf, "exposure_housing")
    return gdf

def compute_exposure_building_value(gdf):
    gdf["exposure_building_value"] = generate_uniform(1e5, 1e8, len(gdf))
    gdf = mark_dummy(gdf, "exposure_building_value")
    return gdf
