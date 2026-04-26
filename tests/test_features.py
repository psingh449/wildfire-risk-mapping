import pandas as pd
import numpy as np
from src.features import hazard, exposure, vulnerability, resilience
from src.features.build_features import _get_component_weights, minmax


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
    gdf = vulnerability.compute_vuln_uninsured(gdf)
    assert "vuln_poverty" in gdf
    assert gdf["vuln_poverty"].between(0, 1).all()
    assert "vuln_elderly" in gdf
    assert gdf["vuln_elderly"].between(0, 1).all()
    assert "vuln_uninsured" in gdf
    assert gdf["vuln_uninsured"].between(0, 1).all()


def test_resilience_features():
    gdf = pd.DataFrame({"block_id": ["1", "2", "3"], "geometry": [None, None, None]})
    gdf = resilience.compute_res_vehicle_access(gdf)
    gdf = resilience.compute_res_median_household_income(gdf)
    gdf = resilience.compute_res_internet_access(gdf)
    assert "res_vehicle_access" in gdf
    assert gdf["res_vehicle_access"].between(0, 1).all()
    assert "res_vehicle_access_source" in gdf
    assert "res_vehicle_access_provenance" in gdf
    assert "res_median_household_income" in gdf
    assert (gdf["res_median_household_income"] >= 0).all()
    assert "res_median_household_income_source" in gdf
    assert "res_median_household_income_provenance" in gdf
    assert "res_internet_access" in gdf
    assert gdf["res_internet_access"].between(0, 1).all()
    assert "res_internet_access_source" in gdf
    assert "res_internet_access_provenance" in gdf


def test_minmax_singleton_and_constant_columns_use_neutral_not_zero():
    # Alpine County (CA) is a single 2020 census block group: min==max for every in-county column.
    # Old behavior: (x - min) / (max - min + eps) → 0, wiping all *_norm and risk_score.
    s1 = pd.Series([0.73], dtype="float64")
    assert (minmax(s1) - 0.5).abs().max() < 1e-9
    s2 = pd.Series([0.2, 0.2, 0.2], dtype="float64")
    assert (minmax(s2) - 0.5).abs().max() < 1e-9
    s3 = pd.Series([0.0, 0.5, 1.0], dtype="float64")
    m3 = minmax(s3)
    assert m3.iloc[0] < 1e-12
    assert m3.iloc[2] > 0.99  # (1-0)/(range+EPSILON) < 1 when EPSILON>0
    assert 0.45 < m3.iloc[1] < 0.55


def test_component_weights_loaded_from_calculations_csv():
    weights = _get_component_weights()
    assert set(weights.keys()) == {"hazard_score", "exposure_score", "vulnerability_score", "resilience_score"}
    assert np.isclose(sum(weights["hazard_score"].values()), 1.0)
    assert np.isclose(sum(weights["exposure_score"].values()), 1.0)
    assert np.isclose(sum(weights["vulnerability_score"].values()), 1.0)
    assert np.isclose(sum(weights["resilience_score"].values()), 1.0)
    assert "hazard_wildfire_norm" in weights["hazard_score"]
    assert "vuln_poverty_norm" in weights["vulnerability_score"]
    assert "res_vehicle_access_norm" in weights["resilience_score"]
