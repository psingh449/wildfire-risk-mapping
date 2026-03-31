def export_geojson(gdf, path):
    gdf.to_file(path, driver="GeoJSON")
    print(f"Saved: {path}")
