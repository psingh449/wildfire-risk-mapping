import pandas as pd
import numpy as np
import logging
import csv
from pathlib import Path
from typing import Dict, Any
from src.utils.config import REAL_DATA_DIR

logger = logging.getLogger("diagnostics")

# Parse calculations.csv for validation rules and min/max
VALIDATION_RULES: Dict[str, Any] = {}
FIELD_LIMITS: Dict[str, Any] = {}
FIELD_NULLABLE: Dict[str, Any] = {}
FIELD_DESCRIPTIONS: Dict[str, Any] = {}


def _resolve_calculations_csv() -> Path:
    candidates = [
        Path.cwd() / "calculations.csv",
        Path(__file__).resolve().parents[2] / "calculations.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not locate calculations.csv")


def _parse_limit(raw) -> Any:
    """Parse min/max from calculations.csv including inf bounds."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    sl = s.lower()
    if sl in ("inf", "+inf", "infinity"):
        return float("inf")
    if sl in ("-inf", "-infinity"):
        return float("-inf")
    try:
        return float(s)
    except ValueError:
        return None


def _load_calculation_rules() -> None:
    try:
        csv_path = _resolve_calculations_csv()
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                var = row.get("geojson_property", "")
                if not var:
                    continue
                min_val = _parse_limit(row.get("min", ""))
                max_val = _parse_limit(row.get("max", ""))
                FIELD_LIMITS[var] = (min_val, max_val)
                FIELD_NULLABLE[var] = (str(row.get("nullable", "")).strip().lower() == "yes")
                FIELD_DESCRIPTIONS[var] = row.get("description", "")
                VALIDATION_RULES[var] = row.get("validation_rules", "")
    except Exception as e:
        logger.warning(f"Unable to load calculations.csv for diagnostics: {e}")


_load_calculation_rules()


def validate_row(row: pd.Series) -> Dict[str, Any]:
    """
    Validate a single row (Series) and return a dict of field: [issues].
    Args:
        row: Pandas Series representing a row
    Returns:
        Dict mapping field to list of issues
    """
    issues = {}
    for field, (min_val, max_val) in FIELD_LIMITS.items():
        val = row.get(field, None)
        field_issues = []
        if val is None or (isinstance(val, float) and np.isnan(val)):
            if not FIELD_NULLABLE.get(field, False):
                field_issues.append("Missing value")
        else:
            if min_val is not None and val < min_val:
                field_issues.append(f"Value {val} < min {min_val}")
            if max_val is not None and val > max_val:
                field_issues.append(f"Value {val} > max {max_val}")
        if field_issues:
            issues[field] = field_issues
    return issues


def add_diagnostics_to_gdf(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    For each row, validate and add a 'diagnostics' column (dict of field: [issues]).
    Ensures diagnostics is always present and non-null.
    Args:
        gdf: DataFrame to validate
    Returns:
        DataFrame with diagnostics column
    """
    diagnostics = []
    summary = {}
    for idx, row in gdf.iterrows():
        issues = validate_row(row)
        diagnostics.append(issues if issues is not None else {})
        for field, problems in issues.items():
            for p in problems:
                summary.setdefault(field, {}).setdefault(p, 0)
                summary[field][p] += 1
        if issues:
            logger.warning(f"Diagnostics for row {idx}: {issues}")
    if len(gdf) == 0:
        gdf["diagnostics"] = []
    else:
        gdf["diagnostics"] = diagnostics
    try:
        import os
        os.makedirs(REAL_DATA_DIR, exist_ok=True)
        with open(f"{REAL_DATA_DIR}/diagnostics_report.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["field", "issue", "count"])
            for field, problems in summary.items():
                for issue, count in problems.items():
                    writer.writerow([field, issue, count])
    except Exception as e:
        logger.warning(f"Could not write diagnostics report: {e}")
    return gdf
