from src.ingestion.load_blocks import generate_mock_blocks
from src.preprocessing.preprocess_blocks import preprocess
from src.features.build_features import build_features
from src.models.risk_model import compute_risk
from src.export.export_geojson import export_geojson
from src.utils.config import OUTPUT_GEOJSON

def run():
    gdf = generate_mock_blocks()
    gdf = preprocess(gdf)
    gdf = build_features(gdf)
    gdf = compute_risk(gdf)
    export_geojson(gdf, OUTPUT_GEOJSON)

if __name__ == "__main__":
    run()
