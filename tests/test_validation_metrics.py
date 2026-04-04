import pandas as pd
from shapely.geometry import Polygon

from src.validation.metrics import (
    aggregate_block_to_county,
    compute_county_risk_from_blocks,
    compute_county_eal_from_blocks,
    compare_with_fema_nri,
    compute_historical_fire_overlap,
    compute_auc_fire_prediction,
    compute_risk_concentration,
    compute_lorenz_curve,
    apply_validation_metrics,
)


def _sample_gdf():
    return pd.DataFrame(
        {
            "block_id": ["b1", "b2", "b3", "b4"],
            "county": ["Butte", "Butte", "Butte", "Butte"],
            "risk_score": [0.1, 0.4, 0.8, 0.9],
            "eal": [10.0, 20.0, 50.0, 70.0],
            "geometry": [
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
                Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
            ],
        }
    )


def test_validation_metric_functions():
    gdf = _sample_gdf()

    gdf = aggregate_block_to_county(gdf)
    assert "block_to_county_mapping" in gdf
    assert "county_fips" in gdf

    gdf = compute_county_risk_from_blocks(gdf)
    assert "county_risk" in gdf
    assert gdf["county_risk"].between(0, 1).all()

    gdf = compute_county_eal_from_blocks(gdf)
    assert "county_eal" in gdf
    assert (gdf["county_eal"] >= 0).all()

    gdf = compare_with_fema_nri(gdf)
    assert "fema_nri_comparison" in gdf

    gdf = compute_historical_fire_overlap(gdf)
    assert "fire_overlap_ratio" in gdf
    assert gdf["fire_overlap_ratio"].between(0, 1).all()

    gdf = compute_auc_fire_prediction(gdf)
    assert "auc_score" in gdf
    assert gdf["auc_score"].between(0, 1).all()

    gdf = compute_risk_concentration(gdf)
    assert "risk_concentration" in gdf
    assert gdf["risk_concentration"].between(0, 1).all()

    gdf = compute_lorenz_curve(gdf)
    assert "gini_risk" in gdf
    assert gdf["gini_risk"].between(0, 1).all()


def test_apply_validation_metrics():
    gdf = apply_validation_metrics(_sample_gdf())
    for col in [
        "block_to_county_mapping",
        "county_risk",
        "county_eal",
        "fema_nri_comparison",
        "fire_overlap_ratio",
        "auc_score",
        "risk_concentration",
        "gini_risk",
    ]:
        assert col in gdf.columns
