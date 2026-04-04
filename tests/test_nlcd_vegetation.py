import pandas as pd
from src.utils.real_data import compute_hazard_vegetation_real

def test_hazard_vegetation_real():
    # Simulate blocks with block_id
    gdf = pd.DataFrame({"block_id": ["1", "2"], "geometry": [None, None]})
    # Should not raise, even if CSV missing
    out = compute_hazard_vegetation_real(gdf)
    assert "hazard_vegetation" in out
    assert "hazard_vegetation_source" in out
    assert "hazard_vegetation_provenance" in out
