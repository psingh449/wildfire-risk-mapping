import pandas as pd
from src.features import exposure
from src.utils import validator

def test_empty_dataframe():
    gdf = pd.DataFrame()
    # Should not raise
    try:
        validator.run_all_validations(gdf)
    except Exception as e:
        assert False, f"Validation failed on empty DataFrame: {e}"

def test_missing_columns():
    gdf = pd.DataFrame({"hazard_wildfire": [0.5, 0.6]})
    # Should log warnings but not raise
    try:
        validator.run_all_validations(gdf)
    except Exception as e:
        assert False, f"Validation failed on missing columns: {e}"

def test_all_null_column():
    gdf = pd.DataFrame({"hazard_wildfire": [None, None]})
    try:
        validator.run_all_validations(gdf)
    except Exception as e:
        assert False, f"Validation failed on all-null column: {e}"
