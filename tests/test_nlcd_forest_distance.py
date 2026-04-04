import pandas as pd
from src.utils.real_data import compute_hazard_forest_distance_real

def test_hazard_forest_distance_real():
    gdf = pd.DataFrame({"block_id": ["1", "2"], "geometry": [None, None]})
    out = compute_hazard_forest_distance_real(gdf)
    assert "hazard_forest_distance" in out
    assert "hazard_forest_distance_source" in out
    assert "hazard_forest_distance_provenance" in out
