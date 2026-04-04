# Calculation/Function Status Report

| # | Variable | Function | Data Source | Real-Time Data | Comments |
|---|----------|----------|-------------|---------------|----------|
| 1 | hazard_wildfire | compute_hazard_wildfire_real | USFS WHP | YES (if whp_zonal_stats.csv exists) | Uses raster zonal stats if processed, else fallback |
| 2 | hazard_vegetation | compute_hazard_vegetation | NLCD | PARTIAL (stub, needs raster processing) | Script provided, needs processing for Butte County |
| 3 | hazard_forest_distance | compute_hazard_forest_distance | NLCD | PARTIAL (stub, needs raster processing) | Script provided, needs processing for Butte County |
| 4 | hazard_score | compute_hazard_score | Derived | YES | Weighted sum of hazard components |
| 5 | exposure_population | compute_exposure_population_real | Census | YES | Uses Census API or local CSV |
| 6 | exposure_housing | compute_exposure_housing_real | Census | YES | Uses Census API or local CSV |
| 7 | exposure_building_value | compute_exposure_building_value_real | ACS | YES | Uses ACS API or local CSV |
| 8 | exposure_score | compute_exposure_score | Derived | YES | Weighted sum of exposure components |
| 9 | vuln_poverty | compute_vuln_poverty_real | ACS | YES | Uses ACS API or local CSV |
| 10 | vuln_elderly | compute_vuln_elderly_real | ACS | YES | Uses ACS API or local CSV |
| 11 | vuln_vehicle_access | compute_vuln_vehicle_access_real | ACS | YES | Uses ACS API or local CSV |
| 12 | vulnerability_score | compute_vulnerability_score | Derived | YES | Weighted sum of vulnerability components |
| 13 | res_fire_station_dist | compute_res_fire_station_dist | HIFLD | PARTIAL (script, needs shapefile processing) | Script provided, needs processing for Butte County |
| 14 | res_hospital_dist | compute_res_hospital_dist | HIFLD | PARTIAL (script, needs shapefile processing) | Script provided, needs processing for Butte County |
| 15 | res_road_access | compute_res_road_access | OSM | PARTIAL (script, needs OSM processing) | Script provided, needs processing for Butte County |
| 16 | resilience_score | compute_resilience_score | Derived | YES | Weighted sum of resilience components |
| 17 | risk_score | compute_risk_score | Derived | YES | Unified risk calculation |
| 18 | eal | compute_eal | Derived | YES | risk_score * exposure_building_value |
| 19 | eal_norm | normalize_eal | Derived | YES | Min-max normalization |
| ... | ... | ... | ... | ... | ... |

- For all validation and model metrics (rows 20+), see calculations.csv for details. Most are derived and can be computed from the pipeline outputs.
- For any row marked PARTIAL, a script is provided but you must run the processing locally for Butte County.
- For any row marked YES, real data is used if available, otherwise robust fallback is used.
- For any row marked NO, only fallback/dummy logic is available.

*This file is updated with every major code or data integration change.*
