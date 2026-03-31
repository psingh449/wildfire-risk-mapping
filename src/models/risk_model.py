from src.utils.config import EPSILON

def compute_risk(gdf):

    gdf["risk_score"] = (
        gdf["hazard_score"]
        * gdf["exposure_score"]
        * gdf["vulnerability_score"]
    ) / (gdf["resilience_score"] + EPSILON)

    gdf["risk_score"] = (
        (gdf["risk_score"] - gdf["risk_score"].min()) /
        (gdf["risk_score"].max() - gdf["risk_score"].min() + EPSILON)
    )

    gdf["eal"] = gdf["hazard_wildfire"] * gdf["exposure_building_value"]

    return gdf
