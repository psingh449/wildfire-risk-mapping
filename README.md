# Wildfire Risk Mapping

---

## Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/psingh449/wildfire-risk-mapping.git
   cd wildfire-risk-mapping
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install geopandas rasterio shapely fiona pyproj rtree osmnx
   ```
3. **Download and process data:**
   ```bash
   python scripts/refresh_real_data.py
   python scripts/download_environmental_data.py
   python scripts/process_nlcd_zonal_stats.py
   python scripts/process_hifld_nearest.py
   python scripts/process_osm_road_length.py
   ```
4. **Run the pipeline:**
   ```bash
   python -m src.pipeline.run_pipeline
   ```
5. **Serve the frontend:**
   ```bash
   python -m http.server 8000
   # Open index.html in your browser
   ```
6. **Run tests:**
   ```bash
   # CMD
   set PYTHONPATH=. & pytest tests/ --maxfail=10 --disable-warnings -q

   # PowerShell
   $env:PYTHONPATH='.'; pytest tests/ --maxfail=10 --disable-warnings -q
   ```

   If you want full verbose output instead:
   ```bash
   $env:PYTHONPATH='.'; pytest tests/ -v
   ```

---

## Diagnostics & Provenance

- Every field has a `_source` and `_provenance` column indicating data origin (REAL/DUMMY and details).
- Every block has a `diagnostics` column with validation issues (if any).
- All validations (range, null, type, provenance, diagnostics) are enforced and tested.
- **All calculation logic, feature definitions, and validation rules are defined in `calculations.csv` (canonical source).**
- `calculations.csv` now includes optional `weight_group` and `weight` columns for weighted composite features.
- The current codebase reads `calculations.csv` by header name, so column order may be reorganized without affecting repo behavior as long as header names remain unchanged.
- Validation metrics (rows 20-27) are computed in the pipeline and written back to the main GeoDataFrame for visualization.

---

## Validation Metrics (Rows 20-27)

The following validation outputs are now computed and attached to each block record:

- `block_to_county_mapping`
- `county_risk`
- `county_eal`
- `fema_nri_comparison`
- `fire_overlap_ratio`
- `auc_score`
- `risk_concentration`
- `gini_risk`

Default external data paths used by validation modules:

- FEMA NRI: `data/external/fema_nri_county.csv`
- MTBS fire perimeters: `data/external/mtbs_fire_perimeters.geojson`

If external datasets are missing, the pipeline computes safe fallback values so the workflow and visualization remain operational.

---

## Troubleshooting Tips

- **Missing dependencies:** Ensure all required Python packages are installed. Use the provided requirements and geospatial libraries.
- **API errors:** Check your internet connection and VPN if accessing Census/ACS APIs. Retry if rate-limited.
- **Geospatial errors:** Ensure all environmental datasets are downloaded and processed before running the pipeline.
- **File not found:** Check that all scripts output to the correct folders (`data/real/`, `data/geospatial/`).
- **Visualization not updating:** Refresh the browser and ensure the GeoJSON output is up to date.
- **Diagnostics issues:** Check the `diagnostics` column in the output and the logs for validation errors.

---

## Example Output

- Example processed GeoJSON: `data/processed/blocks.geojson`
- Example diagnostics report: `data/real/diagnostics_report.csv`
- Example UI screenshot: ![UI Screenshot](docs/example_ui_screenshot.png)  <!-- Replace with your screenshot -->

---

## Economic Model

- `building_value_est = exposure_housing * avg_home_value`
- `risk_score = H * E * V * (1 - R)`  (bounded 0–1)
- `eal = risk_score * building_value_est`
- `eal_norm` for visualization

---

## Pipeline Contract

Each step must:

### Input
- GeoDataFrame with required schema

### Output
- GeoDataFrame with additional columns

### Steps
1. Ingestion: Produces raw dataset
2. Preprocessing: Cleans and standardizes
3. Feature Engineering: Adds hazard, exposure, vulnerability, resilience
4. Model: Computes risk_score, EAL
5. Export: Outputs GeoJSON

### Rules
- No step should depend on internal logic of another
- Only depend on schema
- **All feature and validation definitions are maintained in `calculations.csv`.**

---

## Population Data

- Replace mock population with real Census population.
- Expected file: `data/raw/population.csv`
- Format: `GEOID,population`
- GEOID must match `block_groups.geojson`
- If missing → fallback to mock data

---

## Real Data Setup

- Enable switching between mock and real geometry.
- Download Census Block Group GeoJSON for Butte County and place at `data/raw/block_groups.geojson`.
- In code: `src/pipeline/steps.py`, set `USE_REAL_DATA = True`.
- If file not found → fallback to mock data.
- Geometry only for now (attributes still mock).

---

## Data Dictionary

- See `calculations.csv` for the full data dictionary, feature definitions, validation rules, and optional weight metadata for composite features. This file is the canonical source for all pipeline features and validation logic.

---

## How-To Guides

### How to Add a New Feature
1. Define the feature in `calculations.csv` with min, max, units, formula, and data source.
2. If the feature is an input to a weighted composite metric, set its `weight_group` and `weight` values in `calculations.csv`.
3. Implement the feature function in `src/features/` (e.g., `hazard.py`, `exposure.py`).
4. Add provenance tracking using `mark_real` or `mark_dummy`.
5. Update the feature pipeline in `src/pipeline/feature_pipeline.py` to include your new feature.
6. Add validation rules if needed in `src/utils/validator.py`.
7. Add tests in `tests/` for your new feature.
8. Update the data dictionary in `calculations.csv` if appropriate.
9. Run the pipeline and tests to verify your feature is integrated and robust.

### How to Refresh Data
1. Refresh Census/ACS data:
   ```bash
   python scripts/refresh_real_data.py
   ```
2. Download environmental datasets:
   ```bash
   python scripts/download_environmental_data.py
   ```
3. Process geospatial data:
   ```bash
   python scripts/process_nlcd_zonal_stats.py
   python scripts/process_hifld_nearest.py
   python scripts/process_osm_road_length.py
   ```
4. Rerun the pipeline:
   ```bash
   python -m src.pipeline.run_pipeline
   ```
5. Check diagnostics:
   - Review `data/real/diagnostics_report.csv` for validation issues.
   - Check logs for warnings/errors.

### How to Debug Diagnostics
1. Run the pipeline and generate output GeoJSON and diagnostics report.
2. Check the `diagnostics` column in the output GeoJSON for each block.
3. Open `data/real/diagnostics_report.csv` to see a summary of all validation issues.
4. Review logs for warnings and errors about missing or out-of-range values.
5. Use the UI debug mode to see diagnostics for each block on hover.
6. Fix data or code issues as indicated by diagnostics, then rerun the pipeline and tests.

---

## API Reference

- See [docs/](docs/) for auto-generated API documentation (Sphinx/MkDocs).
- To build the docs locally:
  ```bash
  cd docs
  make html
  # Open docs/_build/html/index.html in your browser
  ```

---

## Data Flow Diagram

See [docs/data_flow_diagram.md](docs/data_flow_diagram.md) for a full data flow, including diagnostics and provenance.

