from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(argv: list[str]) -> None:
    proc = subprocess.run(argv, cwd=str(REPO_ROOT), text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed (exit={proc.returncode}): {' '.join(argv)}")


def _load_ca_counties() -> list[str]:
    county_list = json.loads((REPO_ROOT / "data" / "county_list.json").read_text(encoding="utf-8"))
    out = []
    for c in county_list.get("counties", []):
        cid = str(c.get("id", "")).strip()
        if len(cid) == 5 and cid.startswith("06"):
            out.append(cid)
    return out


def _update_manifest(counties: list[str]) -> None:
    manifest_path = REPO_ROOT / "data" / "county_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = manifest.get("datasets", {}) or {}
    for fips in counties:
        datasets[fips] = f"data/processed/counties/{fips}/blocks_validated.geojson"
    manifest["datasets"] = dict(sorted(datasets.items()))
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run pipeline + per-county validation export for all CA counties.")
    ap.add_argument("--counties", nargs="*", default=[], help="Optional list of 5-digit CA county FIPS to run.")
    ap.add_argument("--start-at", default="", help="Optional FIPS to start at (for resume).")
    ap.add_argument("--limit", type=int, default=0, help="Optional max counties to run (for batching).")
    ap.add_argument("--skip-manifest", action="store_true", help="Do not update data/county_manifest.json")
    args = ap.parse_args(argv)

    counties = [str(x).strip().zfill(5) for x in (args.counties or _load_ca_counties())]
    counties = [c for c in counties if c.startswith("06") and len(c) == 5]
    counties = sorted(set(counties))

    if args.start_at:
        start = str(args.start_at).strip().zfill(5)
        if start in counties:
            counties = counties[counties.index(start) :]

    if args.limit and args.limit > 0:
        counties = counties[: int(args.limit)]

    if not counties:
        print("No counties selected.")
        return 0

    tiger = REPO_ROOT / "data" / "raw" / "census" / "tl_2023_06_bg.shp"
    if not tiger.exists():
        raise FileNotFoundError(f"Missing CA TIGER BG shapefile: {tiger}")

    # IMPORTANT: The pipeline ingestion reads data/raw/block_groups.geojson by default.
    # We overwrite it per-county (sequentially) to keep code changes minimal.
    raw_out = REPO_ROOT / "data" / "raw" / "block_groups.geojson"

    completed: list[str] = []
    for fips in counties:
        print(f"\n=== {fips} ===")

        # 1) Extract county block groups -> data/raw/block_groups.geojson
        _run([sys.executable, "scripts/extract_county_block_groups.py", "--county-fips", fips, "--tiger-shp", str(tiger), "--out", str(raw_out)])

        # 2) Run pipeline with county context so exports route to data/processed/counties/{fips}/blocks.geojson
        env = dict(os.environ)
        env["WILDFIRE_COUNTY_FIPS"] = fips
        # Force ingestion from freshly extracted raw TIGER BG GeoJSON (avoid re-reading processed exports).
        env["WILDFIRE_USE_RAW_BLOCK_GROUPS"] = "1"
        proc = subprocess.run([sys.executable, "-m", "src.pipeline.run_pipeline"], cwd=str(REPO_ROOT), env=env, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Pipeline failed for {fips} (exit={proc.returncode})")

        # 3) Apply validation metrics -> blocks_validated.geojson (this is what UI consumes via county_manifest)
        _run([sys.executable, "scripts/run_external_validation_county.py", "--county-fips", fips])

        completed.append(fips)

    if not args.skip_manifest:
        _update_manifest(completed)
        print(f"\n[manifest] updated data/county_manifest.json for {len(completed)} counties")

    print(f"\nDone. Completed {len(completed)} counties.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

