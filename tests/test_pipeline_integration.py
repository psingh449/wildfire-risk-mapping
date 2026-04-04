import pandas as pd
from src.pipeline import steps
from src.utils import validator

def test_pipeline_with_mock():
    gdf = steps.step_ingestion()
    gdf = steps.step_preprocessing(gdf)
    gdf = steps.step_features(gdf)
    gdf = steps.step_model(gdf)
    validator.run_all_validations(gdf)
    assert "diagnostics" in gdf
    assert not gdf.empty

def test_pipeline_with_empty():
    gdf = pd.DataFrame()
    validator.run_all_validations(gdf)
