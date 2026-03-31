from src.utils.logger import get_logger

logger = get_logger()

def export_geojson(gdf, path):
    gdf.to_file(path, driver="GeoJSON")
    logger.info(f"Saved GeoJSON to {path}")
