"""Pipeline Orchestrator with Logging"""

from src.ingestion.load_blocks import generate_mock_blocks
from src.preprocessing.preprocess_blocks import preprocess
from src.features.build_features import build_features
from src.models.risk_model import compute_risk
from src.export.export_geojson import export_geojson
from src.utils.config import OUTPUT_GEOJSON
from src.utils.logger import get_logger

logger = get_logger()

def run():
    logger.info("Starting pipeline")

    logger.info("Step 1: Loading data")
    gdf = generate_mock_blocks()

    logger.info(f"Loaded {len(gdf)} records")

    logger.info("Step 2: Preprocessing")
    gdf = preprocess(gdf)

    logger.info("Step 3: Feature engineering")
    gdf = build_features(gdf)

    logger.info("Step 4: Risk computation")
    gdf = compute_risk(gdf)

    logger.info("Step 5: Exporting GeoJSON")
    export_geojson(gdf, OUTPUT_GEOJSON)

    logger.info("Pipeline completed successfully")

if __name__ == "__main__":
    run()
