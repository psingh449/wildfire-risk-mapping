"""Pipeline Orchestrator (Refactored)"""

from src.pipeline.steps import (
    step_ingestion,
    step_preprocessing,
    step_features,
    step_model
)
from src.export.export_geojson import export_geojson
from src.utils.config import OUTPUT_GEOJSON
from src.utils.logger import get_logger

logger = get_logger()

def run():
    logger.info("Starting pipeline")

    gdf = step_ingestion()
    gdf = step_preprocessing(gdf)
    gdf = step_features(gdf)
    gdf = step_model(gdf)

    logger.info("Step 5: Export")
    export_geojson(gdf, OUTPUT_GEOJSON)

    logger.info("Pipeline completed")

if __name__ == "__main__":
    run()
