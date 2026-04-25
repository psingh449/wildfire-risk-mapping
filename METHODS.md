# Methods summary (research reproducibility)

This document complements [`calculations.csv`](calculations.csv) and the code in `src/`. It is suitable to adapt into a paper Methods section.

## Study units

Census **block group** polygons in the study area, identified by `GEOID` (and `block_id` in exports) and represented as multipolygons in `data/raw/block_groups.geojson` (processed to `data/processed/blocks.geojson`).

## Risk components

For each block group, three hazard features, three exposure features, three vulnerability features, and three resilience features are computed (rows 1–3, 5–7, 9–11, 13–15 in `calculations.csv`). Raw values are min–max normalized **within the run** to a comparable 0–1 scale (`minmax` in `src/features/build_features.py`), then combined into component scores using weights from `calculations.csv` (`weight_group` / `weight` on `*_norm` column names built from `geojson_property`).

- **Hazard score:** Weighted sum of `hazard_wildfire_norm`, `hazard_vegetation_norm`, `hazard_forest_distance_norm`.
- **Exposure score:** Weighted sum of `exposure_population_norm`, `exposure_housing_norm`, `exposure_building_value_norm` (note: building value is in USD *before* normalization; normalization is applied in the `*_norm` copy).
- **Vulnerability score:** Weighted sum of `vuln_poverty_norm`, `vuln_elderly_norm`, and `vuln_uninsured_norm` (uninsured share from ACS `B27010`). Higher values mean higher vulnerability (no inversion step required).
- **Resilience score:** Weighted sum of `res_vehicle_access_norm`, `res_median_household_income_norm`, `res_internet_access_norm` (all expressed so that larger values mean higher resilience before the weighted sum).

**ACS block-group sparsity:** For some American Community Survey (ACS) 5-year tables, the Census returns null estimates at *block group* for every row in a county. In that case, **tract**-level estimates are fetched or read from per-county cache (`*_tract` quantities), joined by tract `GEOID`, and attached to every block group in that tract; those fields are marked **ESTIMATED** in provenance. This is implemented for **poverty** and **vehicle access** in `src/utils/real_data.py` and `scripts/real_import.py` (stale all-null block-group files are not persisted).

**Median home value imputation:** If `B25077_001E` is missing for a block group, the county mean median is used for `exposure_building_value` and flagged in provenance, per `calculations.csv` row 7.

## Multiplicative risk index

\[
\text{risk\_score} = \text{hazard\_score} \times \text{exposure\_score} \times \text{vulnerability\_score} \times (1 - \text{resilience\_score})
\]

Values are clipped to `[0, 1]`.

## Economic exposure and expected annual loss (EAL)

**Total residential building value proxy** for each block group:

\[
\text{exposure\_building\_value} = \text{exposure\_housing} \times \text{median\_home\_value}_{BG}
\]

where `exposure_housing` is from the 2020 Decennial Census (H1) and `median_home_value_BG` is ACS variable `B25077_001E` at the block group level, mapped from the 12-digit block group prefix of `GEOID`, with imputation as above.

**Expected annual loss (USD):**

\[
\text{eal} = \text{risk\_score} \times \text{exposure\_building\_value}
\]

**Mapped EAL in the app:** `eal_norm` is the min–max scaling of `eal` **across all block groups in the run** (canonical name `eal_norm`, not `eal_normalized`).

**Mapped risk in the app:** the stored field remains `risk_score`. The **browser** color scale for the Risk map uses the min and max of `risk_score` **within the selected county** only, to improve visual contrast (see `main.js:_computeDomainForMetric`).

## Data provenance and quality tiers

Each feature has companion `*_source` and `*_provenance` fields where applicable. Tiers follow `calculations.csv` (`REAL`, `ESTIMATED`, `PROXY`, `MISSING`) rather than a binary REAL/DUMMY split only.

Per-county cached tables live under `data/real_cache/counties/{county_fips}/...` (see the `cache_primary` column in `calculations.csv`).

## Outputs

- `data/processed/blocks.geojson` — block-group geometries and all model fields.
- `data/processed/run_summary.json` — aggregate statistics for the run.
- `data/real/diagnostics_report.csv` — validation issue counts from row-level checks against `calculations.csv` bounds (pipeline logs **warnings** for schema drift, not a hard fail).

## Validation metrics

County-level aggregates, FEMA NRI comparison (if `data/external/fema_nri_county.csv` is present), MTBS overlap and AUC-style metrics (if fire perimeters are present), concentration, and Gini are computed in `src/validation/metrics.py` and attached to the GeoDataFrame for QA (see `calculations.csv` rows 20–27).

For interpretability, the validation layer also records:

- `_burned_label_source`: whether burned labels were derived from MTBS perimeters (`MTBS`) or a proxy fallback (`PROXY`).
- `fema_nri_comparison.n_counties`: how many county points participated in the FEMA join (correlations are only meaningful when many counties are present; the repo avoids enforcing correlation thresholds on tiny `n_counties`).
