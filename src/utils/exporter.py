import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd

logger = logging.getLogger(__name__)


def prepare_geojson_properties(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Serialize nested properties so GeoJSON driver can write valid output."""
    out = gdf.copy()

    if "centroid" in out.columns:
        out = out.drop(columns=["centroid"])

    def _ser(x):
        if isinstance(x, (dict, list)):
            return json.dumps(x)
        return x

    if "diagnostics" in out.columns:
        out["diagnostics"] = out["diagnostics"].apply(_ser)
    return out


def export_geojson(gdf: gpd.GeoDataFrame, path: str = "data/processed/blocks.geojson") -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = prepare_geojson_properties(gdf)
    out.to_file(dest, driver="GeoJSON")
    logger.info("Wrote %s (%d features)", path, len(out))


def write_run_summary(gdf: gpd.GeoDataFrame, path: str = "data/processed/run_summary.json") -> None:
    """Research-oriented run statistics for reproducibility reporting."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_blocks": int(len(gdf)),
    }
    if "risk_score" in gdf.columns:
        summary["mean_risk_score"] = float(gdf["risk_score"].mean())
        summary["std_risk_score"] = float(gdf["risk_score"].std())
    if "eal" in gdf.columns:
        summary["total_eal_usd"] = float(gdf["eal"].sum())
        summary["mean_eal_usd"] = float(gdf["eal"].mean())
    if "exposure_building_value" in gdf.columns:
        summary["total_exposure_building_value_usd"] = float(
            gdf["exposure_building_value"].sum()
        )
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
