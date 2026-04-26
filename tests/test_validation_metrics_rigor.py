import numpy as np
import pandas as pd

from src.validation import metrics


def test_mtbs_labels_do_not_fallback_to_risk_score_threshold():
    # When MTBS perimeters are absent, we must NOT synthesize burned labels from risk_score.
    gdf = pd.DataFrame({"risk_score": [0.1, 0.9, 0.2, 0.8]})
    labels, src = metrics._compute_burned_labels_with_source(gdf, fire_path="this_file_does_not_exist.geojson")
    assert src == "MISSING"
    assert set(pd.to_numeric(labels, errors="coerce").fillna(0).astype(int).tolist()) <= {0, 1}
    # With missing source, we currently return all-zero labels rather than a score-derived split.
    assert int(labels.sum()) == 0


def test_auc_and_overlap_are_nan_without_external_labels():
    gdf = pd.DataFrame({"risk_score": [0.1, 0.9, 0.2, 0.8]})
    gdf = metrics.compute_historical_fire_overlap(gdf, fire_path="this_file_does_not_exist.geojson")
    gdf = metrics.compute_auc_fire_prediction(gdf)
    assert "_burned_label_source" in gdf.columns
    assert str(gdf["_burned_label_source"].iloc[0]).upper() == "MISSING"
    assert "fire_overlap_ratio" in gdf.columns and np.isnan(float(gdf["fire_overlap_ratio"].iloc[0]))
    assert "auc_score" in gdf.columns and np.isnan(float(gdf["auc_score"].iloc[0]))

