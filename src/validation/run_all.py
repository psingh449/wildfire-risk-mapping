from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import pandas as pd
import math
from statistics import NormalDist

from src.pipeline import steps
from src.pipeline.feature_pipeline import run_feature_pipeline
from src.utils import validator
from src.validation.lineage import write_lineage_report
from src.validation.metrics import apply_validation_metrics


def _resolve_repo_file(path: str) -> Path:
    candidates = [
        Path.cwd() / path,
        Path(__file__).resolve().parents[2] / path,
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _load_thresholds(path: str) -> Dict[str, Any]:
    p = _resolve_repo_file(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _parse_json_cell(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return {}


def _extract_scalar_metrics(gdf: pd.DataFrame) -> Dict[str, Any]:
    # These are stored as constants repeated across rows; take first non-null.
    def first_value(col: str, default: Any = None) -> Any:
        if col not in gdf.columns or len(gdf) == 0:
            return default
        s = gdf[col]
        s = s.dropna()
        return s.iloc[0] if len(s) else default

    fema = _parse_json_cell(first_value("fema_nri_comparison", "{}"))
    module_sens = _parse_json_cell(first_value("module_sensitivity", "{}"))
    calfire = _parse_json_cell(first_value("calfire_validation", "{}"))
    burned_src = str(first_value("_burned_label_source", "UNKNOWN") or "UNKNOWN")
    burned_pos = None
    burned_neg = None
    if "_burned_label" in gdf.columns and len(gdf) > 0:
        s = pd.to_numeric(gdf["_burned_label"], errors="coerce").fillna(0).astype(int)
        burned_pos = int((s == 1).sum())
        burned_neg = int((s == 0).sum())

    return {
        "block_rows": int(len(gdf)),
        "fire_overlap_ratio": float(first_value("fire_overlap_ratio", 0.0) or 0.0),
        "auc_score": float(first_value("auc_score", 0.5) or 0.5),
        "risk_concentration": float(first_value("risk_concentration", 0.0) or 0.0),
        "gini_risk": float(first_value("gini_risk", 0.0) or 0.0),
        "fema_nri_comparison": fema,
        "module_sensitivity": module_sens,
        "calfire_validation": calfire,
        "external_sources": {
            "fema_nri": str(fema.get("source", "UNKNOWN")),
            "burned_labels": burned_src,
            "burned_pos": burned_pos,
            "burned_neg": burned_neg,
        },
    }


def _pearson_r_and_p_fisher_z(x: pd.Series, y: pd.Series) -> tuple[float | None, float | None, int]:
    """
    Pearson r and approximate two-sided p-value without SciPy.

    Fisher z-transform with normal approximation:
      z = atanh(r) * sqrt(n - 3), p = 2 * (1 - Φ(|z|))
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
    if abs(r) >= 1.0:
        return max(-1.0, min(1.0, r)), 0.0, n
    z = math.atanh(r) * math.sqrt(max(1, n - 3))
    p = 2.0 * (1.0 - NormalDist().cdf(abs(z)))
    return max(-1.0, min(1.0, r)), max(0.0, min(1.0, float(p))), n


def _compute_top10_share(values: pd.Series) -> float:
    v = pd.to_numeric(values, errors="coerce").fillna(0.0)
    total = float(v.sum())
    if total <= 0 or len(v) == 0:
        return 0.0
    top_n = max(1, int(math.ceil(0.1 * len(v))))
    top_sum = float(v.sort_values(ascending=False).head(top_n).sum())
    return float(top_sum / total)


def _compute_experiments_summary(gdf: pd.DataFrame) -> Dict[str, Any]:
    """
    Summaries aligned to `team155report.md` Experiment 1–6.
    Computed across the full validation frame (all packaged counties when available).
    """
    out: Dict[str, Any] = {"schema_version": 1}

    if gdf is None or len(gdf) == 0:
        return out

    # Ensure county_fips exists (apply_validation_metrics already does, but be defensive).
    if "county_fips" not in gdf.columns:
        if "GEOID" in gdf.columns:
            gdf = gdf.copy()
            gdf["county_fips"] = gdf["GEOID"].astype(str).str[:5].str.zfill(5)
        else:
            return out

    # --- Per-county aggregations used by multiple experiments ---
    risk = pd.to_numeric(gdf.get("risk_score", 0.0), errors="coerce").fillna(0.0)
    eal = pd.to_numeric(gdf.get("eal", 0.0), errors="coerce").fillna(0.0)
    pop = pd.to_numeric(gdf.get("exposure_population", 0.0), errors="coerce").fillna(0.0)

    grp = gdf.groupby("county_fips", dropna=False)
    county_df = pd.DataFrame(
        {
            "county_fips": grp.size().index.astype(str).str.zfill(5),
            "n_blocks": grp.size().values,
            "mean_risk": grp["risk_score"].mean().astype(float).values if "risk_score" in gdf.columns else 0.0,
            "max_risk": grp["risk_score"].max().astype(float).values if "risk_score" in gdf.columns else 0.0,
            "sum_eal": grp["eal"].sum().astype(float).values if "eal" in gdf.columns else 0.0,
        }
    )

    # Population-weighted mean risk per county
    by_pop = (
        pd.DataFrame({"county_fips": gdf["county_fips"].astype(str).str.zfill(5), "risk": risk, "pop": pop})
        .groupby("county_fips", as_index=False)
        .apply(lambda d: float((d["risk"] * d["pop"]).sum() / max(1.0, float(d["pop"].sum()))))
    )
    by_pop = by_pop.rename(columns={None: "mean_risk_popw"})
    county_df = county_df.merge(by_pop[["county_fips", "mean_risk_popw"]], on="county_fips", how="left")

    # Exp5: within-county top10 share + max/mean ratio
    top10_share = grp["risk_score"].apply(_compute_top10_share) if "risk_score" in gdf.columns else 0.0
    county_df["top10_share"] = [float(top10_share.get(cf, 0.0)) for cf in county_df["county_fips"]]
    county_df["max_mean_ratio"] = county_df.apply(
        lambda r: float(r["max_risk"] / r["mean_risk"]) if float(r["mean_risk"]) > 0 else None, axis=1
    )

    # Attach FEMA NRI fields (if present)
    fema_path = _resolve_repo_file("data/external/fema_nri_county.csv")
    fema_df = None
    if fema_path.exists():
        try:
            fema_df = pd.read_csv(fema_path, dtype={"county_fips": str})
            fema_df["county_fips"] = fema_df["county_fips"].astype(str).str.zfill(5)
        except Exception:
            fema_df = None

    merged = county_df.copy()
    if fema_df is not None and not fema_df.empty:
        # Prefer a wildfire-specific field if present; otherwise fall back to `nri_risk`.
        if "nri_wfir_risks" in fema_df.columns:
            nri_col = "nri_wfir_risks"
        elif "WFIR_RISKS" in fema_df.columns:
            nri_col = "WFIR_RISKS"
        else:
            nri_col = "nri_risk" if "nri_risk" in fema_df.columns else None
        if nri_col:
            merged = merged.merge(
                fema_df[["county_fips", nri_col] + (["county_name"] if "county_name" in fema_df.columns else [])],
                on="county_fips",
                how="left",
            )
            merged = merged.rename(columns={nri_col: "nri_wildfire_risk"})

    # --- Experiment 1 (report): FEMA NRI comparison ---
    exp1: Dict[str, Any] = {"counties_compared": int(merged["nri_wildfire_risk"].notna().sum()) if "nri_wildfire_risk" in merged.columns else 0}
    if "nri_wildfire_risk" in merged.columns:
        r_u, p_u, n_u = _pearson_r_and_p_fisher_z(merged["mean_risk"], merged["nri_wildfire_risk"])
        r_w, p_w, n_w = _pearson_r_and_p_fisher_z(merged["mean_risk_popw"], merged["nri_wildfire_risk"])
        exp1.update(
            {
                "pearson_unweighted": {"r": r_u, "p": p_u, "n": n_u},
                "pearson_pop_weighted": {"r": r_w, "p": p_w, "n": n_w},
            }
        )
    out["experiment1_fema_nri"] = exp1

    # --- Experiment 2 (report): county EAL aggregation ---
    top_eal = merged.sort_values("sum_eal", ascending=False).head(10)
    out["experiment2_county_eal_top10"] = top_eal[
        [c for c in ["county_fips", "county_name", "sum_eal", "mean_risk", "mean_risk_popw"] if c in top_eal.columns]
    ].to_dict(orient="records")

    # --- Experiment 3/4 (report): historical overlap + AUC ---
    # Use the scalar metrics already computed for the full frame.
    # The UI will also show per-county CAL FIRE overlap/AUC via the calfire_validation blob.
    out["experiment3_fire_overlap_ratio"] = float(gdf["fire_overlap_ratio"].dropna().iloc[0]) if "fire_overlap_ratio" in gdf.columns and gdf["fire_overlap_ratio"].notna().any() else None
    out["experiment4_auc_score"] = float(gdf["auc_score"].dropna().iloc[0]) if "auc_score" in gdf.columns and gdf["auc_score"].notna().any() else None
    out["fire_labels_source"] = str(gdf["_burned_label_source"].dropna().iloc[0]) if "_burned_label_source" in gdf.columns and gdf["_burned_label_source"].notna().any() else "UNKNOWN"

    # --- Experiment 5 (report): concentration + inequality + selected heterogeneity table ---
    out["experiment5_concentration"] = float(gdf["risk_concentration"].dropna().iloc[0]) if "risk_concentration" in gdf.columns and gdf["risk_concentration"].notna().any() else None
    out["experiment5_gini"] = float(gdf["gini_risk"].dropna().iloc[0]) if "gini_risk" in gdf.columns and gdf["gini_risk"].notna().any() else None

    # Full heterogeneity table (used for UI display; keep to key columns).
    het_cols = [c for c in ["county_fips", "county_name", "mean_risk", "max_risk", "max_mean_ratio", "top10_share"] if c in merged.columns]
    out["experiment5_heterogeneity_by_county"] = merged[het_cols].sort_values("max_mean_ratio", ascending=False).to_dict(orient="records")

    # --- Experiment 6 (report): qualitative UI evaluation (status) ---
    out["experiment6_ui"] = {
        "detail_toggle": True,
        "six_maps": True,
        "tooltip": True,
        "validation_dashboard": True,
        "note": "Qualitative experiment is assessed via interface inspection; this dashboard reports feature availability."
    }

    return out


def _apply_external_thresholds(metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Only enforce thresholds when the required external inputs are present.
    """
    failures: Dict[str, Any] = {}
    ok = True

    ext = (thresholds or {}).get("external", {})

    fema = metrics.get("fema_nri_comparison", {}) or {}
    # Enforce FEMA thresholds only when:
    # - normalized FEMA extract exists
    # - we used REAL
    # - correlation is defined (requires >=2 counties in the comparison join)
    fema_path = _resolve_repo_file("data/external/fema_nri_county.csv")
    n_counties = fema.get("n_counties")
    if (
        fema_path.exists()
        and str(fema.get("source", "")).upper() == "REAL"
        and fema.get("corr_risk") is not None
        and isinstance(n_counties, int)
        and n_counties >= 5
    ):
        fema_thr = ext.get("fema_nri", {})
        min_corr_risk = fema_thr.get("min_corr_risk")
        min_corr_eal = fema_thr.get("min_corr_eal")
        if min_corr_risk is not None and float(fema.get("corr_risk", 0.0) or 0.0) < float(min_corr_risk):
            ok = False
            failures["fema_nri.corr_risk"] = {"value": fema.get("corr_risk"), "min": min_corr_risk}
        if min_corr_eal is not None and fema.get("corr_eal") is not None and float(fema.get("corr_eal", 0.0) or 0.0) < float(min_corr_eal):
            ok = False
            failures["fema_nri.corr_eal"] = {"value": fema.get("corr_eal"), "min": min_corr_eal}

    # Enforce MTBS thresholds only when MTBS perimeters are present AND labels came from MTBS.
    mtbs_path = _resolve_repo_file("data/external/mtbs_fire_perimeters.geojson")
    mtbs_thr = ext.get("mtbs", {})
    labels_src = str((metrics.get("external_sources", {}) or {}).get("burned_labels", "UNKNOWN")).upper()
    burned_pos = (metrics.get("external_sources", {}) or {}).get("burned_pos")
    burned_neg = (metrics.get("external_sources", {}) or {}).get("burned_neg")
    has_both_classes = (
        isinstance(burned_pos, int)
        and isinstance(burned_neg, int)
        and burned_pos > 0
        and burned_neg > 0
    )
    if mtbs_path.exists() and mtbs_thr and labels_src == "MTBS" and has_both_classes:
        min_auc = mtbs_thr.get("min_auc")
        if min_auc is not None and float(metrics.get("auc_score", 0.5) or 0.5) < float(min_auc):
            ok = False
            failures["mtbs.auc_score"] = {"value": metrics.get("auc_score"), "min": min_auc}
        min_overlap = mtbs_thr.get("min_fire_overlap_ratio")
        if min_overlap is not None and float(metrics.get("fire_overlap_ratio", 0.0) or 0.0) < float(min_overlap):
            ok = False
            failures["mtbs.fire_overlap_ratio"] = {"value": metrics.get("fire_overlap_ratio"), "min": min_overlap}

    return ok, failures


def run_validation_runner(
    *,
    use_real_data: bool = False,
    counties: Optional[List[str]] = None,
    thresholds_path: str = "validation_thresholds.json",
    write_reports: bool = True,
    reports_dir: str = "reports",
) -> Dict[str, Any]:
    # If counties are provided, run validation directly on packaged county GeoJSONs
    # (this is how we make FEMA/MTBS comparisons meaningful across multiple counties).
    if counties:
        try:
            import geopandas as gpd
        except Exception as e:
            raise RuntimeError("geopandas is required for --counties validation runs") from e

        manifest = json.loads(_resolve_repo_file("data/county_manifest.json").read_text(encoding="utf-8"))
        datasets = manifest.get("datasets", {}) or {}
        frames = []
        for cf in counties:
            path = datasets.get(cf)
            if not path:
                raise FileNotFoundError(f"county_manifest.json has no dataset path for {cf}")
            frames.append(gpd.read_file(_resolve_repo_file(path)))
        gdf = pd.concat(frames, ignore_index=True)
    else:
        # Prefer "all packaged counties" when available so cross-county validation metrics
        # (including Experiment 1 sensitivity) are meaningful by default.
        gdf = None
        try:
            import geopandas as gpd  # type: ignore
            manifest_path = _resolve_repo_file("data/county_manifest.json")
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                datasets = manifest.get("datasets", {}) or {}
                frames = []
                for cf, rel in datasets.items():
                    p = _resolve_repo_file(str(rel))
                    if p.exists():
                        frames.append(gpd.read_file(p))
                if len(frames) >= 2:
                    gdf = pd.concat(frames, ignore_index=True)
        except Exception:
            gdf = None

        if gdf is None:
            # Fallback: build a representative frame through the existing pipeline.
            steps.USE_REAL_DATA = bool(use_real_data)
            gdf = steps.step_ingestion()
            gdf = steps.step_preprocessing(gdf)
            gdf = run_feature_pipeline(gdf)
            gdf = steps.step_features(gdf)
            gdf = steps.step_model(gdf)

    # Existing schema/range/provenance validations (warning-level logging).
    validator.run_all_validations(gdf)

    # Ensure validation metrics are present even if feature step changes order later.
    gdf = apply_validation_metrics(gdf)

    thresholds = _load_thresholds(thresholds_path)
    scalars = _extract_scalar_metrics(gdf)
    scalars["experiments"] = _compute_experiments_summary(gdf)
    passed, failures = _apply_external_thresholds(scalars, thresholds)

    lineage_path = str(Path(reports_dir) / "lineage_report.json")
    lineage = write_lineage_report(lineage_path)

    report: Dict[str, Any] = {
        "schema_version": 1,
        "passed": bool(passed),
        "threshold_failures": failures,
        "metrics": scalars,
        "lineage": {
            "path": lineage_path,
            "counts": lineage.get("counts", {}),
        },
    }

    if write_reports:
        out_dir = Path(reports_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "validation_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )
        (out_dir / "validation_report.md").write_text(
            _render_report_md(report),
            encoding="utf-8",
        )

    return report


def _render_report_md(report: Dict[str, Any]) -> str:
    metrics = report.get("metrics", {}) or {}
    fema = metrics.get("fema_nri_comparison", {}) or {}
    failures = report.get("threshold_failures", {}) or {}

    lines = []
    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"- passed: **{report.get('passed')}**")
    lines.append(f"- block_rows: **{metrics.get('block_rows')}**")
    lines.append("")
    lines.append("## External comparisons (when present)")
    lines.append("")
    lines.append(f"- FEMA NRI source: **{fema.get('source', 'UNKNOWN')}**")
    if fema:
        lines.append(f"- corr_risk: {fema.get('corr_risk')}")
        lines.append(f"- rmse_risk: {fema.get('rmse_risk')}")
        lines.append(f"- corr_eal: {fema.get('corr_eal')}")
        lines.append(f"- rmse_eal: {fema.get('rmse_eal')}")
    lines.append("")
    lines.append("## Fire-history validation (MTBS if present)")
    lines.append("")
    lines.append(f"- fire_overlap_ratio: {metrics.get('fire_overlap_ratio')}")
    lines.append(f"- auc_score: {metrics.get('auc_score')}")
    lines.append("")
    lines.append("## Distribution diagnostics")
    lines.append("")
    lines.append(f"- risk_concentration: {metrics.get('risk_concentration')}")
    lines.append(f"- gini_risk: {metrics.get('gini_risk')}")
    lines.append("")

    if failures:
        lines.append("## Threshold failures")
        lines.append("")
        for k, v in failures.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    lines.append("## Lineage registry")
    lines.append("")
    lineage = report.get("lineage", {}) or {}
    lines.append(f"- path: `{lineage.get('path')}`")
    lines.append(f"- counts: {lineage.get('counts')}")
    lines.append("")
    lines.append("## Contract")
    lines.append("")
    lines.append("- See `docs/validation_contract.md`")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end validation and emit a report.")
    parser.add_argument("--use-real-data", action="store_true", help="Run ingestion with real data if available.")
    parser.add_argument("--counties", default="", help="Comma-separated county FIPS to validate together (e.g., 06007,06073).")
    parser.add_argument("--no-write", action="store_true", help="Do not write reports to disk.")
    parser.add_argument("--reports-dir", default="reports", help="Where to write reports.")
    parser.add_argument("--thresholds", default="validation_thresholds.json", help="Thresholds JSON path.")
    parser.add_argument(
        "--export-ui",
        default="",
        help=(
            "After validation, write a small JSON file for the static map UI. "
            "Use with e.g. --counties 06007,06073 --export-ui data/validation/merged_06007_06073.json"
        ),
    )
    args = parser.parse_args(argv)

    counties = [str(c.strip()).zfill(5) for c in str(args.counties).split(",") if c.strip()]
    report = run_validation_runner(
        use_real_data=bool(args.use_real_data),
        counties=counties or None,
        thresholds_path=str(args.thresholds),
        write_reports=not bool(args.no_write),
        reports_dir=str(args.reports_dir),
    )
    export_ui = str(getattr(args, "export_ui", "") or "").strip()
    if export_ui:
        out = _resolve_repo_file(export_ui)
        out.parent.mkdir(parents=True, exist_ok=True)
        ui_doc: Dict[str, Any] = {
            "schema_version": 1,
            "county_fips": counties,
            "passed": bool(report.get("passed", False)),
            "threshold_failures": report.get("threshold_failures") or {},
            "metrics": report.get("metrics") or {},
        }
        out.write_text(json.dumps(ui_doc, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if report.get("passed", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())

