import geopandas as gpd
import numpy as np
import os
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger()


def load_real_blocks(path="data/raw/block_groups.geojson"):
    logger.info("Loading real block group geometry")

    # If the pipeline is run with a specific county target (same env used by real_data cache),
    # prefer the per-county processed GeoJSON so the frontend bundle stays in sync.
    # NOTE: For multi-county runs (e.g. scripts/run_all_california.py) we *must* ingest from the
    # freshly extracted raw TIGER geometry for the current county. Otherwise we risk re-reading a
    # previously processed per-county export and repeatedly merging/deriving fields.
    county_fips = os.environ.get("WILDFIRE_COUNTY_FIPS")
    use_raw = str(os.environ.get("WILDFIRE_USE_RAW_BLOCK_GROUPS", "")).strip() not in ("", "0", "false", "False")
    if use_raw:
        logger.info("WILDFIRE_USE_RAW_BLOCK_GROUPS=1 → ingesting from raw block_groups.geojson")
    else:
        # Single-county/dev runs: if a processed per-county GeoJSON exists, use it.
        if county_fips:
            county_fips = str(county_fips).strip().zfill(5)
            per_county = Path("data") / "processed" / "counties" / county_fips / "blocks.geojson"
            if per_county.exists():
                # If the file doesn't look like real TIGER/processed geometry, fall back to the raw geometry path.
                try:
                    tmp = gpd.read_file(per_county)
                    if "STATEFP" in tmp.columns and "COUNTYFP" in tmp.columns and not tmp.empty:
                        path = str(per_county.as_posix())
                    else:
                        logger.warning("Per-county GeoJSON did not look like real geometry; using default raw path instead.")
                except Exception:
                    logger.warning("Failed to read per-county GeoJSON; using default raw path instead.")

    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError("GeoDataFrame is empty")

    if gdf.crs is None:
        logger.warning("CRS missing → setting to EPSG:4326")
        gdf.set_crs(epsg=4326, inplace=True)
    else:
        gdf = gdf.to_crs(epsg=4326)

    if "GEOID" not in gdf.columns:
        logger.warning("GEOID missing → using index as fallback")
        gdf["GEOID"] = gdf.index.astype(str)

    gdf["GEOID"] = (
        gdf["GEOID"]
        .astype(str)
        .str.strip()
        .str.zfill(12)
    )

    gdf["block_id"] = gdf["GEOID"]

    # Provide county identifiers for export routing (steps_export uses this when present).
    if "COUNTYFP" in gdf.columns:
        gdf["county_fips"] = "06" + gdf["COUNTYFP"].astype(str).str.zfill(3)
    else:
        if county_fips:
            gdf["county_fips"] = county_fips

    # Display name (best-effort; keep old default if not discoverable).
    if "county" not in gdf.columns:
        gdf["county"] = "Butte"

    # Do not merge legacy data/raw/population.csv here.
    # The canonical population feature is computed in the feature pipeline from Census PL
    # (data/real_cache), and merging here can cause duplicate columns when re-reading processed exports.
    gdf["exposure_population"] = 0

    return gdf
