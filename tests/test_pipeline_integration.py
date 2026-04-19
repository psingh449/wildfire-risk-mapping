import pandas as pd
from src.pipeline import steps
from src.pipeline.feature_pipeline import run_feature_pipeline
from src.utils import validator


def test_pipeline_with_mock():
    gdf = steps.step_ingestion()
    gdf = steps.step_preprocessing(gdf)
    gdf = run_feature_pipeline(gdf)
    gdf = steps.step_features(gdf)
    gdf = steps.step_model(gdf)
    validator.run_all_validations(gdf)
    assert "diagnostics" in gdf
    assert not gdf.empty
    assert "exposure_building_value" in gdf.columns
    assert "eal_norm" in gdf.columns


def test_pipeline_with_empty():
    gdf = pd.DataFrame()
    validator.run_all_validations(gdf)
