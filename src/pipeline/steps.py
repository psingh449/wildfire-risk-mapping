from src.utils.logger import get_logger
from src.utils.validator import (
    validate_ingestion_schema,
    validate_ingestion_nulls,
    validate_ranges,
)
from src.preprocessing.preprocess_blocks import preprocess
from src.features.build_features import build_features

from src.ingestion.load_blocks import generate_mock_blocks
from src.ingestion.load_real_blocks import load_real_blocks

logger = get_logger()

USE_REAL_DATA = True

def step_ingestion():
    logger.info("Step 1: Ingestion")

    try:
        if USE_REAL_DATA:
            gdf = load_real_blocks()
            logger.info(f"Loaded REAL geometry: {len(gdf)} rows")
        else:
            gdf = generate_mock_blocks()
            logger.info("Loaded MOCK data")
    except Exception as e:
        logger.warning(f"Falling back to mock due to error: {e}")
        gdf = generate_mock_blocks()

    validate_ingestion_schema(gdf)
    validate_ingestion_nulls(gdf)

    return gdf

def step_preprocessing(gdf):
    logger.info("Step 2: Preprocessing")
    return preprocess(gdf)

def step_features(gdf):
    logger.info("Step 3: Feature Engineering")
    gdf = build_features(gdf)
    validate_ranges(gdf)
    return gdf

def step_model(gdf):
    logger.info("Step 4: Risk Model (NO-OP, unified in build_features)")
    # Risk calculation is now unified in build_features/compute_risk
    return gdf
