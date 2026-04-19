import geopandas as gpd
import numpy as np
from src.ingestion.load_population import load_population
from src.utils.logger import get_logger

logger = get_logger()


def load_real_blocks(path="data/raw/block_groups.geojson"):
    logger.info("Loading real block group geometry")

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

        matched = gdf["population"].notna().sum()
        logger.info(f"Population matched for {matched}/{before_merge} blocks")

        gdf["exposure_population"] = gdf["population"].fillna(0).astype(int)
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
