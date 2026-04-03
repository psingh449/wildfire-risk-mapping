import pandas as pd
from src.models.risk_model import compute_risk

def test_compute_risk():
    gdf = pd.DataFrame({
        "hazard_score": [0.5, 0.8, 0.2],
        "exposure_score": [0.6, 0.7, 0.1],
        "vulnerability_score": [0.4, 0.9, 0.3],
        "resilience_score": [0.2, 0.1, 0.5],
        "building_value_est": [100000, 200000, 150000],
    })
    gdf = compute_risk(gdf)
    assert "risk_score" in gdf
    assert gdf["risk_score"].between(0, 1).all()
    assert "eal" in gdf
    assert (gdf["eal"] >= 0).all()
    assert "eal_norm" in gdf
    assert gdf["eal_norm"].between(0, 1).all()
