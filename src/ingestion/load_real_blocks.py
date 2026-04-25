import geopandas as gpd
import numpy as np
import os
from pathlib import Path
from src.ingestion.load_population import load_population
from src.utils.logger import get_logger

logger = get_logger()


def load_real_blocks(path="data/raw/block_groups.geojson"):
    logger.info("Loading real block group geometry")

    # If the pipeline is run with a specific county target (same env used by real_data cache),
    # prefer the per-county processed GeoJSON so the frontend bundle stays in sync.
    county_fips = os.environ.get("WILDFIRE_COUNTY_FIPS")
    if county_fips:
        county_fips = str(county_fips).strip().zfill(5)
        per_county = Path("data") / "processed" / "counties" / county_fips / "blocks.geojson"
        if per_county.exists():
            # Guard against accidentally overwriting the per-county file with mock output.
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

    pop_df = load_population()

    if pop_df is not None and "GEOID" in pop_df.columns:
        logger.info("Merging real population data")

        pop_df["GEOID"] = (
            pop_df["GEOID"]
            .astype(str)
            .str.strip()
            .str.zfill(12)
        )

        before_merge = len(gdf)

        gdf = gdf.merge(pop_df, on="GEOID", how="left")

        if "population" in gdf.columns:
            matched = gdf["population"].notna().sum()
            logger.info(f"Population matched for {matched}/{before_merge} blocks")
            gdf["exposure_population"] = gdf["population"].fillna(0).astype(int)
        else:
            logger.warning("Population merge did not produce a 'population' column; setting exposure_population=0")
            gdf["exposure_population"] = 0
    else:
        logger.warning("Population data missing → exposure_population set to 0")
        gdf["exposure_population"] = 0

    logger.info("Sample population values:")
    logger.info(gdf[["GEOID", "exposure_population"]].head().to_string())
    logger.info("GeoJSON GEOID sample:")
    logger.info(gdf["GEOID"].head().to_string())

    if pop_df is not None:
        logger.info("CSV GEOID sample:")
        logger.info(pop_df["GEOID"].head().to_string())

    return gdf
