
from src.pipeline.steps import step_ingestion, step_preprocessing, step_features, step_model
from src.pipeline.steps_export import step_export

from src.pipeline.feature_pipeline import run_feature_pipeline
from src.utils.validator import validate_columns

USE_NEW_FEATURE_PIPELINE = True


def run():
    print("Starting pipeline")

    gdf = step_ingestion()
    gdf = step_preprocessing(gdf)

    if USE_NEW_FEATURE_PIPELINE:
        gdf = run_feature_pipeline(gdf)
        gdf = step_features(gdf)
    else:
        gdf = step_features(gdf)

    gdf = step_model(gdf)
    validate_columns(gdf)
    gdf = step_export(gdf)

    print("Pipeline completed")


if __name__ == "__main__":
    run()
