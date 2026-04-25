import os
import json
import numpy as np
import pandas as pd
import math
from statistics import NormalDist


def _safe_series(gdf: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col not in gdf.columns:
        return pd.Series([default] * len(gdf), index=gdf.index, dtype=float)
    return pd.to_numeric(gdf[col], errors="coerce").fillna(default)


def _derive_county_fips(gdf: pd.DataFrame) -> pd.Series:
    if "county_fips" in gdf.columns:
        return gdf["county_fips"].astype(str).str.zfill(5)
    if "GEOID" in gdf.columns:
        return gdf["GEOID"].astype(str).str[:5].str.zfill(5)
    if "county" in gdf.columns:
        county_map = {"butte": "06007"}
        return gdf["county"].astype(str).str.lower().map(county_map).fillna("00000")
    return pd.Series(["00000"] * len(gdf), index=gdf.index)


def aggregate_block_to_county(gdf: pd.DataFrame) -> pd.DataFrame:
    gdf = gdf.copy()
    gdf["county_fips"] = _derive_county_fips(gdf)
    gdf["block_to_county_mapping"] = gdf["county_fips"]
    return gdf


def compute_county_risk_from_blocks(gdf: pd.DataFrame) -> pd.DataFrame:
    gdf = gdf.copy()
    if "county_fips" not in gdf.columns:
        gdf = aggregate_block_to_county(gdf)
    risk = _safe_series(gdf, "risk_score", 0.0)
    county_risk = risk.groupby(gdf["county_fips"]).mean()
    gdf["county_risk"] = gdf["county_fips"].map(county_risk).fillna(0.0).clip(0, 1)
    return gdf


def compute_county_eal_from_blocks(gdf: pd.DataFrame) -> pd.DataFrame:
    gdf = gdf.copy()
    if "county_fips" not in gdf.columns:
        gdf = aggregate_block_to_county(gdf)
    eal = _safe_series(gdf, "eal", 0.0)
    county_eal = eal.groupby(gdf["county_fips"]).sum()
    gdf["county_eal"] = gdf["county_fips"].map(county_eal).fillna(0.0)
    return gdf


def _rmse(a: pd.Series, b: pd.Series) -> float:
    diff = pd.to_numeric(a, errors="coerce") - pd.to_numeric(b, errors="coerce")
    diff = diff.dropna()
    if len(diff) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(diff))))


def compare_with_fema_nri(gdf: pd.DataFrame, fema_path: str = "data/external/fema_nri_county.csv") -> pd.DataFrame:
    gdf = gdf.copy()
    if "county_fips" not in gdf.columns:
        gdf = aggregate_block_to_county(gdf)
    if "county_risk" not in gdf.columns:
        gdf = compute_county_risk_from_blocks(gdf)
    if "county_eal" not in gdf.columns:
        gdf = compute_county_eal_from_blocks(gdf)

    summary = {
        "corr_risk": None,
        "rmse_risk": 0.0,
        "corr_eal": None,
        "rmse_eal": 0.0,
        "source": "DUMMY",
        "n_counties": 0,
    }

    if os.path.exists(fema_path):
        fema = pd.read_csv(fema_path, dtype={"county_fips": str})
        fema["county_fips"] = fema["county_fips"].astype(str).str.zfill(5)

        risk_col = "nri_risk" if "nri_risk" in fema.columns else ("risk" if "risk" in fema.columns else None)
        eal_col = "nri_eal" if "nri_eal" in fema.columns else ("eal" if "eal" in fema.columns else None)

        county_df = gdf[["county_fips", "county_risk", "county_eal"]].drop_duplicates("county_fips")
        merged = county_df.merge(fema, on="county_fips", how="inner")
        summary["n_counties"] = int(len(merged))

        if risk_col and not merged.empty:
            r1 = pd.to_numeric(merged["county_risk"], errors="coerce")
            r2 = pd.to_numeric(merged[risk_col], errors="coerce")
            summary["corr_risk"] = float(r1.corr(r2)) if r1.notna().sum() > 1 and r2.notna().sum() > 1 else None
            summary["rmse_risk"] = _rmse(r1, r2)

        if eal_col and not merged.empty:
            e1 = pd.to_numeric(merged["county_eal"], errors="coerce")
            e2 = pd.to_numeric(merged[eal_col], errors="coerce")
            summary["corr_eal"] = float(e1.corr(e2)) if e1.notna().sum() > 1 and e2.notna().sum() > 1 else None
            summary["rmse_eal"] = _rmse(e1, e2)

        summary["source"] = "REAL"

    gdf["fema_nri_comparison"] = json.dumps(summary)
    return gdf


def _pearson_r_and_p_fisher_z(x: pd.Series, y: pd.Series) -> tuple[float | None, float | None, int]:
    """
    Pearson r and an approximate two-sided p-value.

    We avoid SciPy by using a Fisher z-transform with a normal approximation:
      z = atanh(r) * sqrt(n - 3),  p = 2 * (1 - Φ(|z|))
    This is accurate for moderate/large n (typical when aggregating many block groups).
    """
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")
    mask = x.notna() & y.notna()
    n = int(mask.sum())
    if n < 4:
        return None, None, n
    r = float(x[mask].corr(y[mask]))
    if not math.isfinite(r):
        return None, None, n
    # Perfect correlation => p ~= 0
    if abs(r) >= 1.0:
        return float(np.clip(r, -1.0, 1.0)), 0.0, n
    z = math.atanh(r) * math.sqrt(max(1, n - 3))
    p = 2.0 * (1.0 - NormalDist().cdf(abs(z)))
    return float(np.clip(r, -1.0, 1.0)), float(max(0.0, min(1.0, p))), n


def compute_module_sensitivity(gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Experiment 1 — Weight sensitivity analysis proxy:
    Pearson correlations between each module score and final risk score.

    Stored as a JSON blob repeated across rows so the static UI can read it from any feature.
    """
    gdf = gdf.copy()
    risk = _safe_series(gdf, "risk_score", 0.0)

    modules = {
        "hazard": _safe_series(gdf, "hazard_score", 0.0),
        "exposure": _safe_series(gdf, "exposure_score", 0.0),
        "vulnerability": _safe_series(gdf, "vulnerability_score", 0.0),
        "resilience": _safe_series(gdf, "resilience_score", 0.0),
    }

    out: dict[str, dict[str, float | int | None]] = {}
    for name, s in modules.items():
        r, p, n = _pearson_r_and_p_fisher_z(s, risk)
        out[name] = {"r": r, "p": p, "n": n}

    counties = None
    if "county_fips" in gdf.columns:
        try:
            counties = sorted(gdf["county_fips"].astype(str).str.zfill(5).dropna().unique().tolist())
        except Exception:
            counties = None

    summary = {
        "method": "pearson_r_fisher_z_normal_approx",
        "scope": "all_rows_in_frame",
        "counties": counties,
        "risk": {"field": "risk_score"},
        "modules": out,
    }
    gdf["module_sensitivity"] = json.dumps(summary)
    return gdf


def compute_calfire_historical_validation(
    gdf: pd.DataFrame,
    fire_path: str = "data/external/calfire_perimeters_2015_2024.geojson",
    *,
    top_pct: float = 0.10,
    year_min: int = 2015,
    year_max: int = 2024,
) -> pd.DataFrame:
    """
    Experiment 2 — Historical Fire Validation (CAL FIRE FRAP perimeters).

    - Ground truth: a block group is "burned" if its polygon intersects ANY perimeter.
    - Prediction: "high risk" if risk_score is in the top `top_pct` fraction.
    - Outputs: TP/FP/FN/TN, precision/recall/F1, accuracy, AUC (continuous ranking).

    Stored as a JSON blob (`calfire_validation`) repeated across rows so the static UI can
    read it from any single feature.
    """
    gdf = gdf.copy()

    def _binary_metrics(y_true: pd.Series, scores: pd.Series, pred: pd.Series) -> dict:
        y_true = pd.to_numeric(y_true, errors="coerce").fillna(0).astype(int)
        pred = pd.to_numeric(pred, errors="coerce").fillna(0).astype(int)
        tp = int(((y_true == 1) & (pred == 1)).sum())
        fp = int(((y_true == 0) & (pred == 1)).sum())
        fn = int(((y_true == 1) & (pred == 0)).sum())
        tn = int(((y_true == 0) & (pred == 0)).sum())
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float((2 * precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = float((tp + tn) / max(1, (tp + fp + fn + tn)))
        auc = float(_roc_auc_from_scores(y_true, scores))
        return {
            "n_total": int(len(y_true)),
            "burned_total": int((y_true == 1).sum()),
            "predicted_high_risk": int((pred == 1).sum()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": float(np.clip(precision, 0.0, 1.0)),
            "recall": float(np.clip(recall, 0.0, 1.0)),
            "f1": float(np.clip(f1, 0.0, 1.0)),
            "accuracy": float(np.clip(accuracy, 0.0, 1.0)),
            "auc": float(np.clip(auc, 0.0, 1.0)),
        }

    # Always populate a JSON cell so the contract is stable even when the external file is absent.
    summary: dict = {
        "source": "DUMMY",
        "perimeters_path": fire_path,
        "year_min": int(year_min),
        "year_max": int(year_max),
        "method": "intersects(perimeter_union) + threshold(risk_score)",
        "overall": {},
        "by_county": {},
    }

    if len(gdf) == 0:
        gdf["calfire_validation"] = json.dumps(summary)
        return gdf

    risk = _safe_series(gdf, "risk_score", 0.0)
    # Guardrails: top_pct in (0,1).
    try:
        top_pct = float(top_pct)
    except Exception:
        top_pct = 0.10
    top_pct = min(0.99, max(0.01, top_pct))
    threshold = float(risk.quantile(1.0 - top_pct)) if len(risk) else 0.0
    pred_top_pct = (risk >= threshold).astype(int)

    burned = None
    if os.path.exists(fire_path) and "geometry" in gdf.columns:
        try:
            import geopandas as gpd

            fire = gpd.read_file(fire_path)
            if fire.empty:
                raise ValueError("empty fire perimeter file")

            if (
                hasattr(gdf, "crs")
                and hasattr(fire, "crs")
                and getattr(gdf, "crs", None) is not None
                and getattr(fire, "crs", None) is not None
            ):
                fire = fire.to_crs(gdf.crs)

            fire_union = fire.geometry.unary_union
            burned = gdf["geometry"].apply(
                lambda geom: int(geom is not None and not geom.is_empty and geom.intersects(fire_union))
            )
            summary["source"] = "CALFIRE"
        except Exception:
            burned = None

    # If no external perimeters, we can't compute the experiment metrics.
    if burned is None:
        gdf["calfire_validation"] = json.dumps(summary)
        return gdf

    burned = pd.to_numeric(burned, errors="coerce").fillna(0).astype(int)
    pred_top_pct = pd.to_numeric(pred_top_pct, errors="coerce").fillna(0).astype(int)

    # Prevalence-matched: predict the top K where K = number of burned positives.
    burned_total_all = int((burned == 1).sum())
    k = int(max(1, min(len(risk), burned_total_all))) if len(risk) else 1
    # Mark top-k by risk score (ties resolved by rank order).
    order = risk.rank(method="first", ascending=False)
    pred_top_k = (order <= k).astype(int)

    summary["overall"] = {
        "top_pct": float(top_pct),
        "top_pct_metrics": _binary_metrics(burned, risk, pred_top_pct),
        "top_k": int(k),
        "top_k_metrics": _binary_metrics(burned, risk, pred_top_k),
    }

    # Per-county metrics (meaningful only when there are enough positives).
    if "county_fips" not in gdf.columns:
        gdf = aggregate_block_to_county(gdf)
    by: dict = {}
    for cf, idx in gdf.groupby("county_fips").groups.items():
        cf = str(cf).zfill(5)
        yy = burned.loc[idx]
        ss = risk.loc[idx]
        # top_pct within county
        thr_c = float(ss.quantile(1.0 - top_pct)) if len(ss) else 0.0
        pred_c_pct = (ss >= thr_c).astype(int)
        burned_total_c = int((yy == 1).sum())
        kc = int(max(1, min(len(ss), burned_total_c))) if len(ss) else 1
        order_c = ss.rank(method="first", ascending=False)
        pred_c_k = (order_c <= kc).astype(int)
        by[cf] = {
            "top_pct": float(top_pct),
            "top_pct_metrics": _binary_metrics(yy, ss, pred_c_pct),
            "top_k": int(kc),
            "top_k_metrics": _binary_metrics(yy, ss, pred_c_k),
        }
    summary["by_county"] = by

    gdf["calfire_validation"] = json.dumps(summary)
    return gdf


def _compute_burned_labels_with_source(
    gdf: pd.DataFrame, fire_path: str = "data/external/mtbs_fire_perimeters.geojson"
) -> tuple[pd.Series, str]:
    if os.path.exists(fire_path) and "geometry" in gdf.columns:
        try:
            import geopandas as gpd
            fire = gpd.read_file(fire_path)
            if fire.empty:
                raise ValueError("empty fire perimeter file")
            if hasattr(gdf, "crs") and hasattr(fire, "crs") and getattr(gdf, "crs", None) is not None and getattr(fire, "crs", None) is not None:
                fire = fire.to_crs(gdf.crs)
            fire_union = fire.geometry.unary_union
            labels = gdf["geometry"].apply(lambda geom: int(geom is not None and not geom.is_empty and geom.intersects(fire_union)))
            return labels, "MTBS"
        except Exception:
            pass

    risk = _safe_series(gdf, "risk_score", 0.0)
    threshold = float(risk.quantile(0.75)) if len(risk) else 0.0
    return (risk >= threshold).astype(int), "PROXY"


def _compute_burned_labels(gdf: pd.DataFrame, fire_path: str = "data/external/mtbs_fire_perimeters.geojson") -> pd.Series:
    labels, _ = _compute_burned_labels_with_source(gdf, fire_path)
    return labels


def compute_historical_fire_overlap(gdf: pd.DataFrame, fire_path: str = "data/external/mtbs_fire_perimeters.geojson") -> pd.DataFrame:
    gdf = gdf.copy()
    risk = _safe_series(gdf, "risk_score", 0.0)
    burned, burned_source = _compute_burned_labels_with_source(gdf, fire_path)

    if len(gdf) == 0:
        gdf["fire_overlap_ratio"] = []
        gdf["_burned_label"] = []
        gdf["_burned_label_source"] = []
        return gdf

    threshold = float(risk.quantile(0.9)) if len(risk) else 0.0
    top_mask = risk >= threshold
    total_burned = int(burned.sum())
    burned_in_top = int(((burned == 1) & top_mask).sum())
    ratio = float(burned_in_top / total_burned) if total_burned > 0 else 0.0

    gdf["fire_overlap_ratio"] = np.clip(ratio, 0.0, 1.0)
    gdf["_burned_label"] = burned
    gdf["_burned_label_source"] = burned_source
    return gdf


def _roc_auc_from_scores(y_true: pd.Series, y_score: pd.Series) -> float:
    y_true = pd.to_numeric(y_true, errors="coerce").fillna(0).astype(int)
    y_score = pd.to_numeric(y_score, errors="coerce").fillna(0.0)

    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5

    ranks = y_score.rank(method="average")
    rank_sum_pos = float(ranks[y_true == 1].sum())
    auc = (rank_sum_pos - (n_pos * (n_pos + 1) / 2.0)) / (n_pos * n_neg)
    return float(np.clip(auc, 0.0, 1.0))


def compute_auc_fire_prediction(gdf: pd.DataFrame) -> pd.DataFrame:
    gdf = gdf.copy()
    if "_burned_label" not in gdf.columns:
        labels, src = _compute_burned_labels_with_source(gdf)
        gdf["_burned_label"] = labels
        gdf["_burned_label_source"] = src
    elif "_burned_label_source" not in gdf.columns:
        # Best-effort source inference for older frames.
        gdf["_burned_label_source"] = "UNKNOWN"

    auc = _roc_auc_from_scores(gdf["_burned_label"], _safe_series(gdf, "risk_score", 0.0)) if len(gdf) else 0.5
    gdf["auc_score"] = np.clip(float(auc), 0.0, 1.0)
    return gdf


def compute_risk_concentration(gdf: pd.DataFrame) -> pd.DataFrame:
    gdf = gdf.copy()
    risk = _safe_series(gdf, "risk_score", 0.0)
    if len(risk) == 0 or float(risk.sum()) == 0.0:
        concentration = 0.0
    else:
        top_n = max(1, int(np.ceil(0.1 * len(risk))))
        concentration = float(risk.sort_values(ascending=False).head(top_n).sum() / risk.sum())
    gdf["risk_concentration"] = np.clip(concentration, 0.0, 1.0)
    return gdf


def compute_lorenz_curve(gdf: pd.DataFrame) -> pd.DataFrame:
    gdf = gdf.copy()
    x = _safe_series(gdf, "risk_score", 0.0).clip(lower=0).sort_values().values
    n = len(x)
    if n == 0:
        gini = 0.0
    else:
        total = float(np.sum(x))
        if total <= 0:
            gini = 0.0
        else:
            idx = np.arange(1, n + 1)
            gini = float((2 * np.sum(idx * x) / (n * total)) - (n + 1) / n)
            gini = float(np.clip(gini, 0.0, 1.0))
    gdf["gini_risk"] = gini
    return gdf


def apply_validation_metrics(gdf: pd.DataFrame) -> pd.DataFrame:
    gdf = aggregate_block_to_county(gdf)
    gdf = compute_county_risk_from_blocks(gdf)
    gdf = compute_county_eal_from_blocks(gdf)
    gdf = compare_with_fema_nri(gdf)
    gdf = compute_module_sensitivity(gdf)
    gdf = compute_calfire_historical_validation(gdf)
    gdf = compute_historical_fire_overlap(gdf)
    gdf = compute_auc_fire_prediction(gdf)
    gdf = compute_risk_concentration(gdf)
    gdf = compute_lorenz_curve(gdf)
    return gdf
