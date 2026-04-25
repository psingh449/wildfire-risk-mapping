
from src.features.hazard import *
from src.features.exposure import *
from src.features.vulnerability import *
from src.features.resilience import *

def run_feature_pipeline(gdf):
    # Hazard
    gdf = compute_hazard_wildfire(gdf)
    gdf = compute_hazard_vegetation(gdf)
    gdf = compute_hazard_forest_distance(gdf)

    # Exposure
    gdf = compute_exposure_population(gdf)
    gdf = compute_exposure_housing(gdf)
    gdf = compute_exposure_building_value(gdf)

    # Vulnerability
    gdf = compute_vuln_poverty(gdf)
    gdf = compute_vuln_elderly(gdf)
    gdf = compute_vuln_uninsured(gdf)

    # Resilience
    gdf = compute_res_vehicle_access(gdf)
    gdf = compute_res_median_household_income(gdf)
    gdf = compute_res_internet_access(gdf)

    return gdf
