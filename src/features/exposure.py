
from src.utils.dummy_data import generate_uniform, generate_int

def compute_exposure_population(gdf):
    gdf["exposure_population"] = generate_int(100, 3000, len(gdf))
    return gdf

def compute_exposure_housing(gdf):
    gdf["exposure_housing"] = generate_int(50, 1000, len(gdf))
    return gdf

def compute_exposure_building_value(gdf):
    gdf["exposure_building_value"] = generate_uniform(1e5, 1e8, len(gdf))
    return gdf
