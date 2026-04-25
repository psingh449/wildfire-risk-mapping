from src.utils.real_data import (
    fallback_uniform,
    compute_res_vehicle_access_real,
    compute_res_median_household_income_real,
    compute_res_internet_access_real,
)
from src.utils.source_tracker import mark_dummy

def compute_res_vehicle_access(gdf):
    try:
        return compute_res_vehicle_access_real(gdf)
    except Exception as e:
        gdf["res_vehicle_access"] = fallback_uniform(gdf, "res_vehicle_access")
        return mark_dummy(gdf, "res_vehicle_access")

def compute_res_median_household_income(gdf):
    try:
        return compute_res_median_household_income_real(gdf)
    except Exception as e:
        gdf["res_median_household_income"] = fallback_uniform(gdf, "res_median_household_income")
        return mark_dummy(gdf, "res_median_household_income")

def compute_res_internet_access(gdf):
    try:
        return compute_res_internet_access_real(gdf)
    except Exception as e:
        gdf["res_internet_access"] = fallback_uniform(gdf, "res_internet_access")
        return mark_dummy(gdf, "res_internet_access")
