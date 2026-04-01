
def export_geojson(gdf, path="data/processed/blocks.geojson"):
    gdf.to_file(path, driver="GeoJSON")
