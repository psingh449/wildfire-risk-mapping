
from src.pipeline.steps import step_ingestion, step_preprocessing, step_features, step_model

# NEW
from src.pipeline.feature_pipeline import run_feature_pipeline
USE_NEW_FEATURE_PIPELINE = True


def run():
    print("Starting pipeline")

    gdf = step_ingestion()
    gdf = step_preprocessing(gdf)

    if USE_NEW_FEATURE_PIPELINE:
        gdf = run_feature_pipeline(gdf)
        gdf = step_features(gdf) # computes scores
    else:
        gdf = step_features(gdf)

    gdf = step_model(gdf)
    # Export happens inside model or elsewhere (no-op for now)

    print("Pipeline completed")


if __name__ == "__main__":
    run()
