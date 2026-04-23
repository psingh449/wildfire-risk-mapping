from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import pandas as pd

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
        "external_sources": {
            "fema_nri": str(fema.get("source", "UNKNOWN")),
            "burned_labels": burned_src,
            "burned_pos": burned_pos,
            "burned_neg": burned_neg,
        },
    }


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
        # Build a representative frame through the existing pipeline.
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
    args = parser.parse_args(argv)

    counties = [c.strip() for c in str(args.counties).split(",") if c.strip()]
    report = run_validation_runner(
        use_real_data=bool(args.use_real_data),
        counties=counties or None,
        thresholds_path=str(args.thresholds),
        write_reports=not bool(args.no_write),
        reports_dir=str(args.reports_dir),
    )
    return 0 if report.get("passed", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())

