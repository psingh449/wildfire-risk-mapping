
def mark_real(gdf, column):
    gdf[f"{column}_source"] = "REAL"
    return gdf

def mark_dummy(gdf, column):
    gdf[f"{column}_source"] = "DUMMY"
    return gdf
