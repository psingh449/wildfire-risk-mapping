from src.validation.lineage import build_lineage_report


def test_lineage_report_contains_all_geojson_properties():
    report = build_lineage_report()
    assert report["schema_version"] == 1
    items = report["items"]
    # Spot checks: a few canonical properties must exist
    for prop in ("hazard_wildfire", "risk_score", "eal", "block_to_county_mapping", "gini_risk"):
        assert prop in items
        assert "code_locations" in items[prop]

