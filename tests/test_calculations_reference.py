import pytest

from src.utils.calculations_reference import (
    HAZARD_WILDFIRE_PROXY_FOREST_WEIGHT,
    HAZARD_WILDFIRE_PROXY_VEG_WEIGHT,
    documented_geojson_properties,
)


def test_hazard_wildfire_proxy_weights_sum_to_one():
    assert HAZARD_WILDFIRE_PROXY_VEG_WEIGHT + HAZARD_WILDFIRE_PROXY_FOREST_WEIGHT == pytest.approx(1.0)


def test_documented_properties_includes_hazard_wildfire():
    props = documented_geojson_properties(exists_in_code_only=True)
    assert "hazard_wildfire" in props
