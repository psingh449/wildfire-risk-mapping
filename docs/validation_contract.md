# Validation Contract (Specification + Evidence)

This document defines what “validated” means for every metric listed in `calculations.csv`, and how the repo proves it.

## Definition of “100% validation”

For each `calculations.csv` row that has a `geojson_property`, we require:

- **Definition**: formula/logic, units, and expected range.
- **Lineage**: where it is computed in code, plus required upstream inputs.
- **Evidence**:
  - **Unit / property tests** for core math and invariants.
  - **Integration (golden) tests** for a fixed small dataset where feasible.
  - **External-truth validation** when the metric is explicitly a comparison against an external dataset (e.g., FEMA NRI, MTBS).

The automation entrypoint is `python -m src.validation.run_all`, which writes a report to `reports/`.

## Contract sections (one per GeoJSON property)

The runner expects anchors in this file with the form:

- `## geojson_property:<name>`

Example:

- `## geojson_property:risk_score`

### Validation / quality metrics (rows 20–27)

## geojson_property:block_to_county_mapping
- **Definition**: `county_fips` derived from `GEOID` first 5 digits (or existing `county_fips`), then copied into `block_to_county_mapping`.
- **Range / type**: string, 5-digit FIPS; may be `"00000"` in mock/fallback paths.
- **Lineage**: `src/validation/metrics.py:aggregate_block_to_county`
- **Evidence**: unit tests in `tests/test_validation_metrics.py`; lineage coverage test in `tests/test_validation_lineage.py`.

## geojson_property:fema_nri_comparison
- **Definition**: JSON object with `{n_counties, corr_risk, rmse_risk, corr_eal, rmse_eal, source}` comparing county aggregates to FEMA NRI.
- **Range / type**: JSON string; correlations in `[-1,1]`, RMSE `>=0`.
- **Dependencies**: `data/external/fema_nri_county.csv` (normalized extract).
- **Lineage**: `src/validation/metrics.py:compare_with_fema_nri`
- **Evidence**:
  - Unit tests validate schema + bounds.
  - External-truth job (optional) validates thresholds from `validation_thresholds.json` when FEMA data is present.

## geojson_property:county_risk
- **Definition**: `mean(risk_score)` grouped by `county_fips` and mapped back to each block group.
- **Range / type**: float in `[0,1]` (clipped).
- **Lineage**: `src/validation/metrics.py:compute_county_risk_from_blocks`
- **Evidence**: unit tests + runner report.

## geojson_property:county_eal
- **Definition**: `sum(eal)` grouped by `county_fips` and mapped back to each block group.
- **Range / type**: float `>=0`.
- **Lineage**: `src/validation/metrics.py:compute_county_eal_from_blocks`
- **Evidence**: unit tests + runner report.

## geojson_property:fire_overlap_ratio
- **Definition**: share of *burned* labels (MTBS-derived) that fall in the top decile of `risk_score`. Computed only when MTBS perimeters are present; otherwise the value is `null`.
- **Range / type**: `null` or float in `[0,1]`.
- **Dependencies**: `data/external/mtbs_fire_perimeters.geojson` (optional).
- **Lineage**: `src/validation/metrics.py:compute_historical_fire_overlap`
- **Evidence**:
  - Unit tests validate schema + bounds.
  - External-truth job (optional) validates thresholds when MTBS perimeters are present.

## geojson_property:auc_score
- **Definition**: ROC AUC of `risk_score` vs `_burned_label` (MTBS-derived). Computed only when MTBS perimeters are present; otherwise the value is `null`.
- **Range / type**: `null` or float in `[0,1]` (uses `0.5` for degenerate label sets when MTBS labels exist but are single-class).
- **Lineage**: `src/validation/metrics.py:compute_auc_fire_prediction`
- **Evidence**: unit tests + runner report.

### Runner-only / UI-only metadata

The validation runner and frontend also surface a few supporting fields to make the validation KPIs interpretable:

- `_burned_label_source`: string label provenance (`MTBS` when perimeters are used, else `MISSING`).
- `external_sources.burned_pos` / `external_sources.burned_neg`: counts of positive/negative burned labels used for MTBS overlap/AUC.

## geojson_property:risk_concentration
- **Definition**: share of total `risk_score` held by the top 10% highest-risk block groups.
- **Range / type**: float in `[0,1]`.
- **Lineage**: `src/validation/metrics.py:compute_risk_concentration`
- **Evidence**: unit tests + property invariants.

## geojson_property:gini_risk
- **Definition**: Gini coefficient of the `risk_score` distribution.
- **Range / type**: float in `[0,1]`.
- **Lineage**: `src/validation/metrics.py:compute_lorenz_curve`
- **Evidence**: unit tests + property invariants.

