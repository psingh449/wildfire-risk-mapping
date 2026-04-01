
from src.utils.exporter import export_geojson

def step_export(gdf):
    export_geojson(gdf)
    return gdf
