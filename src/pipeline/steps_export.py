import os
from pathlib import Path

from src.utils.config import OUTPUT_GEOJSON
from src.utils.exporter import export_geojson, write_run_summary
from src.utils.real_cache import normalize_county_fips


def step_export(gdf, path: str = OUTPUT_GEOJSON):
    export_geojson(gdf, path=path)

    # Also publish per-county GeoJSON for the UI.
    # The frontend loads `data/processed/counties/{county_fips}/blocks.geojson` as configured
    # in `data/county_manifest.json`, so we keep that path updated whenever we run the pipeline.
    county_fips = None
    if "county_fips" in getattr(gdf, "columns", []):
        vals = list({str(x) for x in gdf["county_fips"].dropna().unique().tolist()})
        if len(vals) == 1:
            county_fips = vals[0]
    if not county_fips:
        county_fips = os.environ.get("WILDFIRE_COUNTY_FIPS")

    if county_fips:
        county_fips = normalize_county_fips(county_fips)
        per_county_path = Path("data") / "processed" / "counties" / county_fips / "blocks.geojson"
        export_geojson(gdf, path=str(per_county_path.as_posix()))

    write_run_summary(gdf)
    return gdf
