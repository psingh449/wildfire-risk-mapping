# Methods summary (research reproducibility)

This document complements `calculations.csv` and the code in `src/`. It is suitable to adapt into a paper Methods section.

## Study units

Census block groups in the study area (default: Butte County, California), identified by `GEOID` and represented as polygons in `data/raw/block_groups.geojson`.

## Risk components

For each block group, three hazard features, three exposure features, three vulnerability features, and three resilience features are computed (see `calculations.csv`). Raw values are min–max normalized within the run to `[0, 1]` at the block-group scale, then combined into component scores using weights from `calculations.csv` (`weight_group` / `weight`).

- **Hazard score:** Weighted average of normalized `hazard_wildfire`, `hazard_vegetation`, `hazard_forest_distance`.
- **Exposure score:** Weighted average of normalized `exposure_population`, `exposure_housing`, `exposure_building_value` (building value in USD before normalization).
- **Vulnerability score:** Weighted average of normalized `vuln_poverty`, `vuln_elderly`, and inverted `vuln_vehicle_access` (ACS “vehicle access” is defined so that higher means more vehicle access; the inverted normalized value enters vulnerability so that higher score reflects higher vulnerability).
- **Resilience score:** Weighted average of normalized `res_fire_station_dist`, `res_hospital_dist`, `res_road_access` (distance-based features are already expressed as larger-closer-is-better before normalization).

## Multiplicative risk index

\[
\text{risk\_score} = \text{hazard\_score} \times \text{exposure\_score} \times \text{vulnerability\_score} \times (1 - \text{resilience\_score})
\]

Values are clipped to `[0, 1]`.

## Economic exposure and expected annual loss (EAL)

**Total residential building value proxy** for each block group:

\[
\text{exposure\_building\_value} = \text{housing\_units} \times \text{median\_home\_value}_{BG}
\]

where `housing_units` is from the Decennial Census (H1) and `median_home_value_BG` is ACS variable `B25077_001E` at the block-group level, mapped from the block group prefix of `GEOID`.

**Expected annual loss (USD):**

\[
\text{eal} = \text{risk\_score} \times \text{exposure\_building\_value}
\]

**Mapped EAL:** `eal_norm` is the min–max scaling of `eal` across block groups for choropleth visualization (canonical name `eal_norm`).

## Data provenance

Each feature column has companion `*_source` and `*_provenance` fields (`REAL` vs `DUMMY`) where implemented in `src/utils/source_tracker.py`. Fallback synthetic values are drawn within bounds implied by `calculations.csv` where applicable.

## Outputs

- `data/processed/blocks.geojson` — block-group geometries and all model fields.
- `data/processed/run_summary.json` — aggregate statistics for the run.
- `data/real/diagnostics_report.csv` — validation issue counts from row-level checks against `calculations.csv` bounds.

## Validation metrics

County-level aggregates, FEMA NRI comparison (if `data/external/fema_nri_county.csv` is present), MTBS overlap and AUC-style metrics (if fire perimeters are present), concentration, and Gini are computed in `src/validation/metrics.py` and attached to the GeoDataFrame for QA (see `calculations.csv` rows 20–27).
