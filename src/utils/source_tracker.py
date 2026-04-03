import logging
logger = logging.getLogger("provenance")

def mark_real(gdf, column, source=None):
    gdf[f"{column}_source"] = "REAL"
    if source:
        gdf[f"{column}_provenance"] = source
        logger.info(f"{column}: REAL from {source}")
    else:
        gdf[f"{column}_provenance"] = "REAL"
        logger.info(f"{column}: REAL")
    return gdf

def mark_dummy(gdf, column, reason=None):
    gdf[f"{column}_source"] = "DUMMY"
    if reason:
        gdf[f"{column}_provenance"] = f"DUMMY: {reason}"
        logger.warning(f"{column}: DUMMY ({reason})")
    else:
        gdf[f"{column}_provenance"] = "DUMMY"
        logger.warning(f"{column}: DUMMY")
    return gdf
