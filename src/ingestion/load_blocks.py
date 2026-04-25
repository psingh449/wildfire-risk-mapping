import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

def generate_mock_blocks(n=49):
    data = []
    size = int(np.sqrt(n))

    for i in range(size):
        for j in range(size):
            idx = i * size + j

            poly = Polygon([
                (i, j),
                (i+1, j),
                (i+1, j+1),
                (i, j+1)
            ])

            row = {
                "block_id": f"B{idx}",
                "GEOID": f"06007{idx:07d}",
                "county": "Butte",
                "geometry": poly,

                # Hazard
                "hazard_wildfire": np.random.rand(),
                "hazard_vegetation": np.random.rand(),
                "hazard_forest_distance": np.random.uniform(0, 50),

                # Exposure
                "exposure_population": np.random.randint(0, 3000),
                "exposure_housing": np.random.randint(0, 1200),
                "exposure_building_value": np.random.uniform(1e5, 5e8),

                # Vulnerability
                "vuln_poverty": np.random.rand(),
                "vuln_elderly": np.random.rand(),
                "vuln_uninsured": np.random.rand(),

                # Resilience
                "res_vehicle_access": np.random.rand(),
                "res_median_household_income": np.random.uniform(30000, 140000),
                "res_internet_access": np.random.rand(),
            }

            data.append(row)

    gdf = gpd.GeoDataFrame(data, geometry="geometry")
    gdf.set_crs(epsg=4326, inplace=True)
    return gdf
