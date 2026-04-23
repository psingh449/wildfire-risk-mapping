from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LineageItem:
    geojson_property: str
    function_name: str
    code_locations: str
    dependencies: str
    exists_in_code: str
    used_in_validation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "geojson_property": self.geojson_property,
            "function_name": self.function_name,
            "code_locations": self.code_locations,
            "dependencies": self.dependencies,
            "exists_in_code": self.exists_in_code,
            "used_in_validation": self.used_in_validation,
        }


def _resolve_repo_file(path: str) -> Path:
    candidates = [
        Path.cwd() / path,
        Path(__file__).resolve().parents[2] / path,
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_calculations_rows(csv_path: Optional[str] = None) -> List[LineageItem]:
    path = Path(csv_path) if csv_path else _resolve_repo_file("calculations.csv")
    out: List[LineageItem] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prop = (row.get("geojson_property") or "").strip()
            if not prop:
                continue
            out.append(
                LineageItem(
                    geojson_property=prop,
                    function_name=str(row.get("function_name") or "").strip(),
                    code_locations=str(row.get("code_locations") or "").strip(),
                    dependencies=str(row.get("dependencies") or "").strip(),
                    exists_in_code=str(row.get("exists_in_code") or "").strip(),
                    used_in_validation=str(row.get("used_in_validation") or "").strip(),
                )
            )
    return out


def build_lineage_report(*, csv_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Lineage is spec-driven: we treat `calculations.csv` as the canonical registry.
    This report is used for coverage checks and for human-readable evidence.
    """
    rows = load_calculations_rows(csv_path)
    by_prop: Dict[str, Any] = {}
    for item in rows:
        by_prop[item.geojson_property] = item.to_dict()

    return {
        "schema_version": 1,
        "source": "calculations.csv",
        "items": by_prop,
        "counts": {
            "properties": len(by_prop),
        },
    }


def write_lineage_report(path: str, *, csv_path: Optional[str] = None) -> Dict[str, Any]:
    report = build_lineage_report(csv_path=csv_path)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report

