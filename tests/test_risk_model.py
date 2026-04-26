import pandas as pd
from src.models.risk_model import compute_risk

def test_compute_risk():
    gdf = pd.DataFrame({
        "hazard_score": [0.5, 0.8, 0.2],
        "exposure_score": [0.6, 0.7, 0.1],
        "vulnerability_score": [0.4, 0.9, 0.3],
        "resilience_score": [0.2, 0.1, 0.5],
        "exposure_building_value": [100000.0, 200000.0, 150000.0],
    })
    gdf = compute_risk(gdf)
    assert "risk_score" in gdf
    assert gdf["risk_score"].between(0, 1).all()
    assert "eal" in gdf
    assert (gdf["eal"] >= 0).all()
    assert "eal_norm" in gdf
    assert gdf["eal_norm"].between(0, 1).all()


def test_eal_norm_single_block_group_is_neutral():
    gdf = pd.DataFrame(
        {
            "hazard_score": [0.2],
            "exposure_score": [0.3],
            "vulnerability_score": [0.4],
            "resilience_score": [0.1],
            "exposure_building_value": [1_000_000.0],
        }
    )
    gdf = compute_risk(gdf)
    assert gdf["eal"].iloc[0] > 0
    assert float(gdf["eal_norm"].iloc[0]) == 0.5


def test_eal_norm_all_eal_zero_stays_zero():
    gdf = pd.DataFrame(
        {
            "hazard_score": [0.0],
            "exposure_score": [0.0],
            "vulnerability_score": [0.0],
            "resilience_score": [0.0],
            "exposure_building_value": [100.0],
        }
    )
    gdf = compute_risk(gdf)
    assert float(gdf["eal"].iloc[0]) == 0.0
    assert float(gdf["eal_norm"].iloc[0]) == 0.0
