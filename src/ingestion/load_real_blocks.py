import geopandas as gpd
import numpy as np
from src.ingestion.load_population import load_population
from src.utils.logger import get_logger

logger = get_logger()


def load_real_blocks(path="data/raw/block_groups.geojson"):
    logger.info("Loading real block group geometry")

    # -------------------------------
    # 1. Load GeoJSON
    # -------------------------------
    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError("GeoDataFrame is empty")

    # -------------------------------
    # 2. Ensure CRS = EPSG:4326
    # -------------------------------
    if gdf.crs is None:
        logger.warning("CRS missing → setting to EPSG:4326")
        gdf.set_crs(epsg=4326, inplace=True)
    else:
        gdf = gdf.to_crs(epsg=4326)

    # -------------------------------
    # 3. Ensure GEOID exists + clean
    # -------------------------------
    if "GEOID" not in gdf.columns:
        logger.warning("GEOID missing → using index as fallback")
        gdf["GEOID"] = gdf.index.astype(str)

    # Normalize GEOID (critical step)
    gdf["GEOID"] = (
        gdf["GEOID"]
        .astype(str)
        .str.strip()
        .str.zfill(12)
    )

    # Standard identifiers
    gdf["block_id"] = gdf["GEOID"]
    gdf["county"] = "Butte"

    # -------------------------------
    # 4. Load population data
    # -------------------------------
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

        # Fill missing safely
        gdf["exposure_population"] = gdf["population"].fillna(0)

    else:
        logger.warning("Population data missing → using mock values")
        gdf["exposure_population"] = np.random.randint(100, 3000, len(gdf))

    # -------------------------------
    # 5. Generate placeholder variables
    # -------------------------------
    n = len(gdf)

    # Hazard
    gdf["hazard_wildfire"] = np.random.rand(n)
    gdf["hazard_vegetation"] = np.random.rand(n)
    gdf["hazard_forest_distance"] = np.random.uniform(0, 50, n)

    # Exposure (partial real, partial mock)
    gdf["exposure_housing"] = np.random.randint(50, 1200, n)
    gdf["exposure_building_value"] = np.random.uniform(1e5, 5e8, n)

    # Vulnerability
    gdf["vuln_poverty"] = np.random.rand(n)
    gdf["vuln_elderly"] = np.random.rand(n)
    gdf["vuln_vehicle_access"] = np.random.rand(n)

    # Resilience
    gdf["res_fire_station_dist"] = np.random.uniform(0, 30, n)
    gdf["res_hospital_dist"] = np.random.uniform(0, 50, n)
    gdf["res_road_access"] = np.random.rand(n)

    # -------------------------------
    # 6. Debug (safe + controlled)
    # -------------------------------
    logger.info("Sample population values:")
    logger.info(gdf[["GEOID", "exposure_population"]].head().to_string())

    logger.info("GeoJSON GEOID sample:")
    logger.info(gdf["GEOID"].head().to_string())

    if pop_df is not None:
        logger.info("CSV GEOID sample:")
        logger.info(pop_df["GEOID"].head().to_string())

    return gdf