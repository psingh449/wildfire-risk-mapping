
from src.pipeline.steps import step_ingestion, step_preprocessing, step_features, step_model

# NEW
try:
    from src.pipeline.feature_pipeline import run_feature_pipeline
    USE_NEW_FEATURE_PIPELINE = False  # keep OFF by default (non-breaking)
except:
    USE_NEW_FEATURE_PIPELINE = False


def run():
    print("Starting pipeline")

    gdf = step_ingestion()
    gdf = step_preprocessing(gdf)

    if USE_NEW_FEATURE_PIPELINE:
        gdf = run_feature_pipeline(gdf)
    else:
        gdf = step_features(gdf)

    gdf = step_model(gdf)
    # Export happens inside model or elsewhere (no-op for now)

    print("Pipeline completed")


if __name__ == "__main__":
    run()
