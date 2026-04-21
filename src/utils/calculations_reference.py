"""
Single source of truth for formula constants that are documented in calculations.csv.

Keep numeric weights and other shared constants here so Python matches the canonical
`calculations.csv` row for `hazard_wildfire` (proxy_method / fallback when WHP CSV is absent).
See `calculations.csv` column `proxy_method` and row `hazard_wildfire`.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List

# Documented in calculations.csv (hazard_wildfire): 0.5*vegetation + 0.5*forest_proximity (OSM)
HAZARD_WILDFIRE_PROXY_VEG_WEIGHT: float = 0.5
HAZARD_WILDFIRE_PROXY_FOREST_WEIGHT: float = 0.5


def _resolve_calculations_csv() -> Path:
    candidates = [
        Path.cwd() / "calculations.csv",
        Path(__file__).resolve().parents[2] / "calculations.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not locate calculations.csv")


def documented_geojson_properties(*, exists_in_code_only: bool = True) -> List[str]:
    """
    Property names from calculations.csv `geojson_property` column.
    If exists_in_code_only, only rows with exists_in_code == Yes (pipeline-exported metrics).
    """
    out: List[str] = []
    path = _resolve_calculations_csv()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prop = (row.get("geojson_property") or "").strip()
            if not prop:
                continue
            if exists_in_code_only:
                flag = (row.get("exists_in_code") or "").strip().lower()
                if flag != "yes":
                    continue
            out.append(prop)
    return out
