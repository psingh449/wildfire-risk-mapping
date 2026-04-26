from src.utils.real_data import (
    compute_res_vehicle_access_real,
    compute_res_median_household_income_real,
    compute_res_internet_access_real,
)
from src.utils.source_tracker import mark_missing

def compute_res_vehicle_access(gdf):
    try:
        return compute_res_vehicle_access_real(gdf)
    except Exception as e:
        gdf["res_vehicle_access"] = 0.0
        return mark_missing(gdf, "res_vehicle_access", reason=f"real_data_error: {type(e).__name__}")

def compute_res_median_household_income(gdf):
    try:
        return compute_res_median_household_income_real(gdf)
    except Exception as e:
        gdf["res_median_household_income"] = 0.0
        return mark_missing(gdf, "res_median_household_income", reason=f"real_data_error: {type(e).__name__}")

def compute_res_internet_access(gdf):
    try:
        return compute_res_internet_access_real(gdf)
    except Exception as e:
        gdf["res_internet_access"] = 0.0
        return mark_missing(gdf, "res_internet_access", reason=f"real_data_error: {type(e).__name__}")
