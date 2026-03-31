import geopandas as gpd

gdf = gpd.read_file("data/raw/census/tl_2023_06_bg.shp")

# Butte County FIPS = 06007
butte = gdf[gdf["COUNTYFP"] == "007"]

butte.to_file("data/raw/block_groups.geojson", driver="GeoJSON")

print("Saved Butte County block groups")