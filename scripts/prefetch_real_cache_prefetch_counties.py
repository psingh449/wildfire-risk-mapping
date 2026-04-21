#!/usr/bin/env python3
"""
Import all real_cache datasets for counties listed under `prefetched_county_ids`
in data/county_manifest.json (the same counties bolded in the UI dropdown).

First-pass workflow (prefetch counties only):
  python scripts/prefetch_real_cache_prefetch_counties.py
  python scripts/prefetch_real_cache_prefetch_counties.py --refresh

Requires per-county blocks GeoJSON where available (see scripts/real_import.py).
"""
from __future__ import annotations

import argparse
import os
import sys

# Repo root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from scripts.real_import import _all_sources, run_for_county  # noqa: E402
from src.utils.prefetch_counties import load_prefetch_county_fips  # noqa: E402


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Run real_import --all for prefetch counties only.")
    p.add_argument("--refresh", action="store_true", help="Re-download even if cached")
    args = p.parse_args(argv)

    counties = load_prefetch_county_fips()
    if not counties:
        print("No prefetched_county_ids in data/county_manifest.json", file=sys.stderr)
        return 1

    sources = _all_sources()
    print(f"Prefetch real_cache for counties: {counties}")
    for c in counties:
        try:
            run_for_county(c, sources=sources, quantities=None, refresh=args.refresh)
        except Exception as e:
            print(f"ERROR {c}: {e}", file=sys.stderr)
            # Continue other counties (offline-friendly)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
