import numpy as np
import logging
from src.utils.dummy_data import generate_uniform, generate_int
from src.utils.source_tracker import mark_real, mark_dummy

logger = logging.getLogger("real_data")

# Helper to get min/max from calculations.csv for fallback
def get_limits(var):
    import csv
    with open("calculations.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["geojson_property"] == var:
                try:
                    min_val = float(row["min"])
                except Exception:
                    min_val = 0
                try:
                    max_val = float(row["max"])
                except Exception:
                    max_val = 1
                return min_val, max_val
    return 0, 1

def fallback_uniform(gdf, var, size=None):
    min_val, max_val = get_limits(var)
    if size is None:
        size = len(gdf)
    logger.warning(f"Falling back to dummy for {var} in range [{min_val},{max_val}]")
    return generate_uniform(min_val, max_val, size)

def fallback_int(gdf, var, size=None):
    min_val, max_val = get_limits(var)
    if size is None:
        size = len(gdf)
    logger.warning(f"Falling back to dummy for {var} in range [{min_val},{max_val}]")
    return generate_int(int(min_val), int(max_val) + 1, size)

# Example: Real data stub for hazard_wildfire (USFS WHP raster)
def compute_hazard_wildfire_real(gdf):
    # TODO: Implement raster zonal stats using WHP raster
    # For now, fallback
    gdf["hazard_wildfire"] = fallback_uniform(gdf, "hazard_wildfire")
    return mark_dummy(gdf, "hazard_wildfire")

# Example: Real data stub for exposure_population (Census API)
def compute_exposure_population_real(gdf):
    # TODO: Implement Census API fetch and join
    # For now, fallback
    gdf["exposure_population"] = fallback_int(gdf, "exposure_population")
    return mark_dummy(gdf, "exposure_population")

# Add similar stubs for all features as per calculations.csv
