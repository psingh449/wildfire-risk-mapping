import os
import json
import numpy as np
import pandas as pd


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
    gdf = compute_historical_fire_overlap(gdf)
    gdf = compute_auc_fire_prediction(gdf)
    gdf = compute_risk_concentration(gdf)
    gdf = compute_lorenz_curve(gdf)
    return gdf
