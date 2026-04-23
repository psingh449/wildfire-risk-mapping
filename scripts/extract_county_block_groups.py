from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extract one CA county's block groups from TIGER shapefile.")
    p.add_argument("--county-fips", required=True, help="5-digit county FIPS, e.g. 06073 for San Diego")
    p.add_argument(
        "--tiger-shp",
        default="data/raw/census/tl_2023_06_bg.shp",
        help="Path to CA block-group TIGER shapefile",
    )
    p.add_argument(
        "--out",
        default="data/raw/block_groups.geojson",
        help="Output GeoJSON path (used by load_real_blocks by default)",
    )
    args = p.parse_args(argv)

    county_fips = str(args.county_fips).strip()
    if len(county_fips) != 5 or not county_fips.isdigit():
        raise ValueError("--county-fips must be 5 digits (e.g., 06073)")

    countyfp3 = county_fips[-3:]
    in_path = Path(args.tiger_shp)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gdf = gpd.read_file(in_path)
    if "COUNTYFP" not in gdf.columns:
        raise ValueError("Input TIGER layer missing COUNTYFP column")

    county = gdf[gdf["COUNTYFP"].astype(str).str.zfill(3) == countyfp3].copy()
    if county.empty:
        raise ValueError(f"No block groups found for COUNTYFP={countyfp3} in {in_path}")

    county.to_file(out_path, driver="GeoJSON")
    print(f"[blocks] wrote {len(county)} block groups -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

