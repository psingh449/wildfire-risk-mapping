from src.utils.logger import get_logger
from src.utils.validator import validate_columns, validate_nulls, validate_ranges
from src.preprocessing.preprocess_blocks import preprocess
from src.features.build_features import build_features
from src.models.risk_model import compute_risk

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

    validate_columns(gdf)
    validate_nulls(gdf)

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
    logger.info("Step 4: Risk Model")
    return compute_risk(gdf)
