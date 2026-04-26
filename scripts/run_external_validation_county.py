from __future__ import annotations

import argparse
from pathlib import Path
import sys

import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.validation.metrics import apply_validation_metrics  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compute validation metrics for one packaged county GeoJSON.")
    ap.add_argument("--county-fips", required=True, help="5-digit county FIPS (e.g., 06073)")
    ap.add_argument(
        "--in",
        dest="in_path",
        default="",
        help="Optional input path; default is data/processed/counties/{fips}/blocks.geojson",
    )
    ap.add_argument(
        "--out",
        dest="out_path",
        default="",
        help="Optional output path; default is data/processed/counties/{fips}/blocks_validated.geojson",
    )
    args = ap.parse_args(argv)

    county_fips = str(args.county_fips).strip().zfill(5)
    in_path = Path(args.in_path) if args.in_path else (REPO_ROOT / "data" / "processed" / "counties" / county_fips / "blocks.geojson")
    if not in_path.exists():
        raise FileNotFoundError(f"Missing county GeoJSON: {in_path}")

    out_path = Path(args.out_path) if args.out_path else (REPO_ROOT / "data" / "processed" / "counties" / county_fips / "blocks_validated.geojson")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(in_path)
    gdf = apply_validation_metrics(gdf)
    gdf.to_file(out_path, driver="GeoJSON")
    print(f"[validation] wrote {out_path} ({len(gdf)} features)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

