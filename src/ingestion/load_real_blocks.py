import geopandas as gpd
import numpy as np

def load_real_blocks(path="data/raw/block_groups.geojson"):
    gdf = gpd.read_file(path)

    # Ensure CRS is WGS84
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    else:
        gdf = gdf.to_crs(epsg=4326)

    # Required identifiers
    gdf["block_id"] = gdf.index.astype(str)
    gdf["county"] = "Butte"

    # 🔥 ADD MOCK ATTRIBUTES (temporary bridge)
    n = len(gdf)

    # Hazard
    gdf["hazard_wildfire"] = np.random.rand(n)
    gdf["hazard_vegetation"] = np.random.rand(n)
    gdf["hazard_forest_distance"] = np.random.uniform(0, 50, n)

    # Exposure
    gdf["exposure_population"] = np.random.randint(0, 3000, n)
    gdf["exposure_housing"] = np.random.randint(0, 1200, n)
    gdf["exposure_building_value"] = np.random.uniform(1e5, 5e8, n)

    # Vulnerability
    gdf["vuln_poverty"] = np.random.rand(n)
    gdf["vuln_elderly"] = np.random.rand(n)
    gdf["vuln_vehicle_access"] = np.random.rand(n)

    # Resilience
    gdf["res_fire_station_dist"] = np.random.uniform(0, 30, n)
    gdf["res_hospital_dist"] = np.random.uniform(0, 50, n)
    gdf["res_road_access"] = np.random.rand(n)

    return gdf