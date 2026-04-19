from src.utils.config import OUTPUT_GEOJSON
from src.utils.exporter import export_geojson, write_run_summary


def step_export(gdf, path: str = OUTPUT_GEOJSON):
    export_geojson(gdf, path=path)
    write_run_summary(gdf)
    return gdf
