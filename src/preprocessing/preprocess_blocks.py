import geopandas as gpd


def preprocess(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure geographic CRS for web mapping and spatial joins."""
    if not isinstance(gdf, gpd.GeoDataFrame):
        return gdf
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    return gdf
