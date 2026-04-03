import pandas as pd
from src.utils.diagnostics import add_diagnostics_to_gdf

def test_diagnostics():
    gdf = pd.DataFrame({
        "hazard_wildfire": [0.5, -0.1, 1.2],
        "exposure_population": [100, None, 200],
        "vuln_poverty": [0.2, 0.5, 1.1],
    })
    gdf = add_diagnostics_to_gdf(gdf)
    assert "diagnostics" in gdf
    # At least one row should have issues
    assert any(len(d) > 0 for d in gdf["diagnostics"])
