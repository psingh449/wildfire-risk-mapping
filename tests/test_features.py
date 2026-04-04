import pandas as pd
import numpy as np
from src.features import hazard, exposure, vulnerability, resilience

def test_hazard_features():
    gdf = pd.DataFrame({"block_id": [1, 2, 3]})
    gdf = hazard.compute_hazard_wildfire(gdf)
    gdf = hazard.compute_hazard_vegetation(gdf)
    gdf = hazard.compute_hazard_forest_distance(gdf)
    assert "hazard_wildfire" in gdf
    assert gdf["hazard_wildfire"].between(0, 1).all()
    assert "hazard_vegetation" in gdf
    assert gdf["hazard_vegetation"].between(0, 1).all()
    assert "hazard_forest_distance" in gdf
    assert gdf["hazard_forest_distance"].min() >= 0
    assert "hazard_forest_distance_source" in gdf
    assert "hazard_forest_distance_provenance" in gdf

def test_exposure_features():
    gdf = pd.DataFrame({"block_id": [1, 2, 3]})
    gdf = exposure.compute_exposure_population(gdf)
    gdf = exposure.compute_exposure_housing(gdf)
    gdf = exposure.compute_exposure_building_value(gdf)
    assert "exposure_population" in gdf
    assert (gdf["exposure_population"] >= 0).all()
    assert "exposure_housing" in gdf
    assert (gdf["exposure_housing"] >= 0).all()
    assert "exposure_building_value" in gdf
    assert (gdf["exposure_building_value"] >= 0).all()

def test_vulnerability_features():
    gdf = pd.DataFrame({"block_id": [1, 2, 3]})
    gdf = vulnerability.compute_vuln_poverty(gdf)
    gdf = vulnerability.compute_vuln_elderly(gdf)
    gdf = vulnerability.compute_vuln_vehicle_access(gdf)
    assert "vuln_poverty" in gdf
    assert gdf["vuln_poverty"].between(0, 1).all()
    assert "vuln_elderly" in gdf
    assert gdf["vuln_elderly"].between(0, 1).all()
    assert "vuln_vehicle_access" in gdf
    assert gdf["vuln_vehicle_access"].between(0, 1).all()

def test_resilience_features():
    gdf = pd.DataFrame({"block_id": ["1", "2", "3"], "geometry": [None, None, None]})
    gdf = resilience.compute_res_fire_station_dist(gdf)
    gdf = resilience.compute_res_hospital_dist(gdf)
    gdf = resilience.compute_res_road_access(gdf)
    assert "res_fire_station_dist" in gdf
    assert gdf["res_fire_station_dist"].between(0, 1).all() or gdf["res_fire_station_dist"].min() >= 0
    assert "res_fire_station_dist_source" in gdf
    assert "res_fire_station_dist_provenance" in gdf
    assert "res_hospital_dist" in gdf
    assert gdf["res_hospital_dist"].between(0, 1).all() or gdf["res_hospital_dist"].min() >= 0
    assert "res_hospital_dist_source" in gdf
    assert "res_hospital_dist_provenance" in gdf
    assert "res_road_access" in gdf
    assert gdf["res_road_access"].between(0, 1).all()
    assert "res_road_access_source" in gdf
    assert "res_road_access_provenance" in gdf
