import pandas as pd
from src.utils import validator

def test_validation_on_good_data():
    gdf = pd.DataFrame({
        "hazard_wildfire": [0.5, 0.7],
        "hazard_vegetation": [0.2, 0.3],
        "hazard_forest_distance": [0.1, 0.9],
        "exposure_population": [100, 200],
        "exposure_housing": [50, 60],
        "exposure_building_value": [100000.0, 200000.0],
        "vuln_poverty": [0.1, 0.2],
        "vuln_elderly": [0.1, 0.2],
        "vuln_uninsured": [0.1, 0.2],
        "res_vehicle_access": [0.5, 0.6],
        "res_median_household_income": [60000.0, 80000.0],
        "res_internet_access": [0.5, 0.6],
        "hazard_score": [0.5, 0.6],
        "exposure_score": [0.5, 0.6],
        "vulnerability_score": [0.5, 0.6],
        "resilience_score": [0.5, 0.6],
        "risk_score": [0.5, 0.6],
        "eal": [10000.0, 20000.0],
        "eal_norm": [0.5, 0.6],
        "hazard_wildfire_source": ["REAL", "REAL"],
        "hazard_wildfire_provenance": ["test", "test"],
        "diagnostics": [{}, {}],
    })
    validator.run_all_validations(gdf)

def test_validation_on_bad_data():
    gdf = pd.DataFrame({
        "hazard_wildfire": [-0.5, 1.2],
        "hazard_vegetation": [0.2, 0.3],
        "hazard_forest_distance": [0.1, 0.9],
        "exposure_population": [100.5, None],
        "exposure_housing": [50, 60],
        "exposure_building_value": [100000.0, 200000.0],
        "vuln_poverty": [0.1, 0.2],
        "vuln_elderly": [0.1, 0.2],
        "vuln_uninsured": [0.1, 0.2],
        "res_vehicle_access": [0.5, 0.6],
        "res_median_household_income": [60000.0, 80000.0],
        "res_internet_access": [0.5, 0.6],
        "hazard_score": [0.5, 0.6],
        "exposure_score": [0.5, 0.6],
        "vulnerability_score": [0.5, 0.6],
        "resilience_score": [0.5, 0.6],
        "risk_score": [0.5, 0.6],
        "eal": [10000.0, 20000.0],
        "eal_norm": [0.5, 0.6],
        "hazard_wildfire_source": ["REAL", "REAL"],
        "hazard_wildfire_provenance": ["test", "test"],
        "diagnostics": [{}, {}],
    })
    validator.run_all_validations(gdf)
