"""Load real (or placeholder) geometry for block groups"""

import geopandas as gpd

def load_real_blocks(path="data/raw/block_groups.geojson"):
    try:
        gdf = gpd.read_file(path)
        gdf["block_id"] = gdf.index.astype(str)
        gdf["county"] = "Butte"
        return gdf
    except Exception:
        print("WARNING: Real data not found, falling back to mock grid")
        from src.ingestion.load_blocks import generate_mock_blocks
        return generate_mock_blocks()
