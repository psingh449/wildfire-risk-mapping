"""
DEPRECATED: Use scripts/real_import.py

This script is kept for backwards compatibility with older docs, but it now
delegates to the new per-county cache under data/real_cache/.

Run from repository root with PYTHONPATH set, e.g. PowerShell:
  $env:PYTHONPATH='.'; python scripts/refresh_real_data.py

Optional:
  $env:WILDFIRE_COUNTY_FIPS='06007'
  python scripts/refresh_real_data.py --refresh
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.real_import import main as real_import_main


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--refresh", action="store_true", help="force re-download into data/real_cache/")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse(argv)
    county = os.environ.get("WILDFIRE_COUNTY_FIPS", "06007")
    cmd = ["--county", county, "--all"]
    if args.refresh:
        cmd.append("--refresh")
    return real_import_main(cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
