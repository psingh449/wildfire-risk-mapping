import pandas as pd
import numpy as np
import logging
import csv
from src.utils.config import REAL_DATA_DIR
import os

logger = logging.getLogger("diagnostics")

# Parse calculations.csv for validation rules and min/max
VALIDATION_RULES = {}
FIELD_LIMITS = {}
FIELD_NULLABLE = {}
FIELD_DESCRIPTIONS = {}

with open("calculations.csv", newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        var = row["geojson_property"]
        if not var:
            continue
        # Min/max
        try:
            min_val = float(row["min"])
        except Exception:
            min_val = None
        try:
            max_val = float(row["max"])
        except Exception:
            max_val = None
        FIELD_LIMITS[var] = (min_val, max_val)
        # Nullable
        FIELD_NULLABLE[var] = (row["nullable"].strip().lower() == "yes")
        # Description
        FIELD_DESCRIPTIONS[var] = row["description"]
        # Validation rule (string)
        VALIDATION_RULES[var] = row["validation_rules"]

def validate_row(row):
    """
    Validate a single row (Series) and return a dict of field: [issues]
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
        # Add more rule-based checks here if needed
        if field_issues:
            issues[field] = field_issues
    return issues

def add_diagnostics_to_gdf(gdf):
    """
    For each row, validate and add a 'diagnostics' column (dict of field: [issues])
    Also, write a summary diagnostics report to data/real/diagnostics_report.csv
    """
    diagnostics = []
    summary = {}
    for idx, row in gdf.iterrows():
        issues = validate_row(row)
        diagnostics.append(issues)
        for field, problems in issues.items():
            for p in problems:
                summary.setdefault(field, {}).setdefault(p, 0)
                summary[field][p] += 1
        if issues:
            logger.warning(f"Diagnostics for row {idx}: {issues}")
    gdf["diagnostics"] = diagnostics
    # Write summary report
    try:
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
