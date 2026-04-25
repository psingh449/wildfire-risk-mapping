from src.utils.config import (
    HAZARD_WEIGHTS,
    EXPOSURE_WEIGHTS,
    VULNERABILITY_WEIGHTS,
    RESILIENCE_WEIGHTS,
)
from src.models.risk_model import compute_risk
from src.utils.diagnostics import add_diagnostics_to_gdf
from src.validation.metrics import apply_validation_metrics
import csv
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("build_features")


def _resolve_calculations_csv() -> Path:
    candidates = [
        Path.cwd() / "calculations.csv",
        Path(__file__).resolve().parents[2] / "calculations.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not locate calculations.csv")


def _normalize_weight_dict(weights):
    total = sum(weights.values())
    if total <= 0:
        return weights
    return {k: v / total for k, v in weights.items()}


def _load_component_weights_from_calculations():
    groups = {}
    try:
        csv_path = _resolve_calculations_csv()
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                weight_group = str(row.get("weight_group", "")).strip()
                weight_raw = str(row.get("weight", "")).strip()
                variable = str(row.get("geojson_property") or row.get("variable") or "").strip()

                if not weight_group or not weight_raw or not variable:
                    continue

                try:
                    weight = float(weight_raw)
                except ValueError:
                    logger.warning(f"Skipping invalid weight '{weight_raw}' for {variable} in {weight_group}")
                    continue

                groups.setdefault(weight_group, {})[f"{variable}_norm"] = weight

        return {group: _normalize_weight_dict(weights) for group, weights in groups.items()}
    except Exception as e:
        logger.warning(f"Unable to load component weights from calculations.csv: {e}")
        return {}


def _get_component_weights():
    csv_weights = _load_component_weights_from_calculations()
    return {
        "hazard_score": csv_weights.get("hazard_score", HAZARD_WEIGHTS),
        "exposure_score": csv_weights.get("exposure_score", EXPOSURE_WEIGHTS),
        "vulnerability_score": csv_weights.get("vulnerability_score", VULNERABILITY_WEIGHTS),
        "resilience_score": csv_weights.get("resilience_score", RESILIENCE_WEIGHTS),
    }


def minmax(series):
    return (series - series.min()) / (series.max() - series.min() + 1e-9)


def weighted_sum(df, weights):
    available = {col: w for col, w in weights.items() if col in df.columns}
    missing = set(weights) - set(available)
    if missing:
        logger.warning(f"Missing normalized columns for weighted sum: {sorted(missing)}")
    if not available:
        return pd.Series(0.0, index=df.index)
    return sum(df[col] * w for col, w in available.items())


def build_features(gdf):
    component_weights = _get_component_weights()

    # 1. Normalize into *_norm (preserve raw)
    for col in gdf.columns:
        if (
            col.startswith(("hazard_", "exposure_", "vuln_", "res_"))
            and not col.endswith("_source")
            and gdf[col].dtype != "object"
        ):
            if col == "exposure_population":
                continue
            gdf[f"{col}_norm"] = minmax(gdf[col])

    if "exposure_population" in gdf.columns:
        gdf["exposure_population_norm"] = minmax(gdf["exposure_population"])

    # 2. Direction fixes on normalized fields (single inversion per feature)
    # hazard_forest_distance raw: 1/(1+d_km) — higher = closer to forest = higher hazard (keep norm).
    # Legacy note: older resilience used distances (1/(1+d_km)) to stations/hospitals.
    # Note: previously we inverted vehicle access when used as a vulnerability signal.
    # In the current model vehicle access is part of resilience (higher = more capacity), so no inversion here.

    # 3. Component scores (read weights from calculations.csv when available)
    gdf["hazard_score"] = weighted_sum(gdf, component_weights["hazard_score"])
    gdf["exposure_score"] = weighted_sum(gdf, component_weights["exposure_score"])
    gdf["vulnerability_score"] = weighted_sum(gdf, component_weights["vulnerability_score"])
    gdf["resilience_score"] = weighted_sum(gdf, component_weights["resilience_score"])

    # Safety checks (0-1)
    for c in ["hazard_score", "exposure_score", "vulnerability_score", "resilience_score"]:
        gdf[c] = gdf[c].clip(0, 1)

    # 5. Risk score and EAL (exposure_building_value = housing * ACS median; set in feature pipeline)
    gdf = compute_risk(gdf)

    # 6. Validation metrics (rows 20-27 in calculations.csv)
    gdf = apply_validation_metrics(gdf)

    # 7. Diagnostics
    gdf = add_diagnostics_to_gdf(gdf)

    return gdf
