# `calculations.csv` companion notes

This repo’s canonical metric contract is [`calculations.csv`](calculations.csv). This file is a lightweight companion that explains how to **use** the CSV in practice, and how it connects to validation + UI.

## What `calculations.csv` is

- **Single source of truth for KPI meaning**: one row per exported GeoJSON property (and its `_source` / `_provenance` companions where applicable).
- **Where to look first**: the `code_locations` / `canonical_source` columns point to the implementation modules in `src/`.
- **Cache paths**: `cache_primary` documents the expected per-county cache layout under `data/real_cache/counties/{county_fips}/...`.
- **Weights + bounds**: composite weights (`weight_group`, `weight`) and expected ranges (`min`, `max`, units) are documented alongside each metric.

## Validation rows (20–27)

Rows 20–27 in `calculations.csv` are validation/QA outputs that are computed during the pipeline and embedded into each county GeoJSON.

- **County rollups**: `block_to_county_mapping`, `county_risk`, `county_eal`
- **External comparisons**:
  - **FEMA NRI** (`fema_nri_comparison`): `{n_counties, corr_risk, rmse_risk, corr_eal, rmse_eal, source}`
  - **MTBS** (`fire_overlap_ratio`, `auc_score`) when `data/external/mtbs_fire_perimeters.geojson` exists
- **Distribution diagnostics**: `risk_concentration`, `gini_risk`

Supporting metadata:

- `_burned_label_source`: `MTBS` when burned labels come from MTBS perimeters. If MTBS perimeters are unavailable, labels are `MISSING` and MTBS-derived metrics (overlap/AUC) are not computed.

## Where validation KPIs show up in the UI

The static frontend (`index.html` + `main.js`) displays:

1. **Current county** (values embedded in that county’s packaged GeoJSON)
2. **Joint run (06007 + 06073)**, if `data/validation/merged_06007_06073.json` exists

The joint run exists because FEMA’s correlations are county-level comparisons and are not informative when computed from a single county (`n_counties: 1`).

To generate / refresh the joint file:

```bash
python -m src.validation.run_all --counties "06007,06073" --no-write --export-ui data/validation/merged_06007_06073.json
```

## How to update metrics safely

When you change logic or add a KPI:

1. Update the row in `calculations.csv` (definition + range + data source + cache path + code pointers).
2. Ensure the value exists in the pipeline output GeoDataFrame.
3. Run `python -m src.validation.run_all` (or multi-county run) to regenerate validation KPIs and reports.
4. If the KPI is user-visible, update the UI panel / tooltip rendering in `main.js`.

