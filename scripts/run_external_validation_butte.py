from __future__ import annotations

import json
from pathlib import Path
import sys

import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.validation.metrics import apply_validation_metrics


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Compute validation metrics for one packaged county.")
    ap.add_argument("--county-fips", default="06007", help="5-digit county FIPS (default: 06007)")
    args = ap.parse_args()

    county_fips = str(args.county_fips).strip()

    in_path = REPO_ROOT / "data" / "processed" / "counties" / county_fips / "blocks.geojson"
    if not in_path.exists():
        raise FileNotFoundError(f"Missing Butte county GeoJSON: {in_path}")

    gdf = gpd.read_file(in_path)
    gdf = apply_validation_metrics(gdf)

    # Summaries are constant columns; take first row.
    first = gdf.iloc[0].to_dict() if len(gdf) else {}
    fema = first.get("fema_nri_comparison", "{}")
    if isinstance(fema, str):
        try:
            fema = json.loads(fema)
        except Exception:
            pass

    print("[butte] fire_overlap_ratio:", first.get("fire_overlap_ratio"))
    print("[butte] auc_score:", first.get("auc_score"))
    print("[butte] risk_concentration:", first.get("risk_concentration"))
    print("[butte] gini_risk:", first.get("gini_risk"))
    print("[butte] fema_nri_comparison:", fema)

    # Write to a new file to avoid Windows file-lock collisions (and to keep the original packaged file intact).
    out_path = REPO_ROOT / "data" / "processed" / "counties" / county_fips / "blocks_validated.geojson"
    gdf.to_file(out_path, driver="GeoJSON")
    print("[butte] updated:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

