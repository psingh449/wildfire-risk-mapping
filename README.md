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
   set PYTHONPATH=. & pytest tests/ --maxfail=10 --disable-warnings -q
   ```

---

## Diagnostics & Provenance

- Every field has a `_source` and `_provenance` column indicating data origin (REAL/DUMMY and details).
- Every block has a `diagnostics` column with validation issues (if any).
- All validations (range, null, type, provenance, diagnostics) are enforced and tested.

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

## Calculation/Function Status Report

| # | Variable | Function | Data Source | Real-Time Data | Comments |
|---|----------|----------|-------------|---------------|----------|
| 1 | hazard_wildfire | compute_hazard_wildfire_real | USFS WHP | YES (if whp_zonal_stats.csv exists) | Uses raster zonal stats if processed, else fallback |
| 2 | hazard_vegetation | compute_hazard_vegetation | NLCD | PARTIAL (stub, needs raster processing) | Script provided, needs processing for Butte County |
| 3 | hazard_forest_distance | compute_hazard_forest_distance | NLCD | PARTIAL (stub, needs raster processing) | Script provided, needs processing for Butte County |
| 4 | hazard_score | compute_hazard_score | Derived | YES | Weighted sum of hazard components |
| 5 | exposure_population | compute_exposure_population_real | Census | YES | Uses Census API or local CSV |
| 6 | exposure_housing | compute_exposure_housing_real | Census | YES | Uses Census API or local CSV |
| 7 | exposure_building_value | compute_exposure_building_value_real | ACS | YES | Uses ACS API or local CSV |
| 8 | exposure_score | compute_exposure_score | Derived | YES | Weighted sum of exposure components |
| 9 | vuln_poverty | compute_vuln_poverty_real | ACS | YES | Uses ACS API or local CSV |
| 10 | vuln_elderly | compute_vuln_elderly_real | ACS | YES | Uses ACS API or local CSV |
| 11 | vuln_vehicle_access | compute_vuln_vehicle_access_real | ACS | YES | Uses ACS API or local CSV |
| 12 | vulnerability_score | compute_vulnerability_score | Derived | YES | Weighted sum of vulnerability components |
| 13 | res_fire_station_dist | compute_res_fire_station_dist | HIFLD | PARTIAL (script, needs shapefile processing) | Script provided, needs processing for Butte County |
| 14 | res_hospital_dist | compute_res_hospital_dist | HIFLD | PARTIAL (script, needs shapefile processing) | Script provided, needs processing for Butte County |
| 15 | res_road_access | compute_res_road_access | OSM | PARTIAL (script, needs OSM processing) | Script provided, needs processing for Butte County |
| 16 | resilience_score | compute_resilience_score | Derived | YES | Weighted sum of resilience components |
| 17 | risk_score | compute_risk_score | Derived | YES | Unified risk calculation |
| 18 | eal | compute_eal | Derived | YES | risk_score * exposure_building_value |
| 19 | eal_norm | normalize_eal | Derived | YES | Min-max normalization |
| ... | ... | ... | ... | ... | ... |

- For all validation and model metrics (rows 20+), see calculations.csv for details. Most are derived and can be computed from the pipeline outputs.
- For any row marked PARTIAL, a script is provided but you must run the processing locally for Butte County.
- For any row marked YES, real data is used if available, otherwise robust fallback is used.
- For any row marked NO, only fallback/dummy logic is available.

---

## Data Dictionary

### Hazard
- hazard_wildfire: wildfire probability (0–1)
- hazard_vegetation: vegetation density
- hazard_forest_distance: distance to forest (km, inverted)

### Exposure
- exposure_population: population count
- exposure_housing: number of houses
- exposure_building_value: estimated value

### Vulnerability
- vuln_poverty: poverty rate
- vuln_elderly: elderly population ratio
- vuln_vehicle_access: vehicle access (inverted)

### Resilience
- res_fire_station_dist: distance to fire station (inverted)
- res_hospital_dist: distance to hospital (inverted)
- res_road_access: road connectivity

### Outputs
- hazard_score
- exposure_score
- vulnerability_score
- resilience_score
- risk_score
- eal

---

## How-To Guides

### How to Add a New Feature
1. Define the feature in `calculations.csv` with min, max, units, formula, and data source.
2. Implement the feature function in `src/features/` (e.g., `hazard.py`, `exposure.py`).
3. Add provenance tracking using `mark_real` or `mark_dummy`.
4. Update the feature pipeline in `src/pipeline/feature_pipeline.py` to include your new feature.
5. Add validation rules if needed in `src/utils/validator.py`.
6. Add tests in `tests/` for your new feature.
7. Update the data dictionary in the README if appropriate.
8. Run the pipeline and tests to verify your feature is integrated and robust.

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

---

## Changelog

All notable changes to this project will be documented in this file.

### [Unreleased]
- Add type annotations, docstrings, and structured logging to all core modules.
- Add robust validation, diagnostics, and provenance tracking.
- Add geospatial processing scripts and integration.
- Add comprehensive test suite and CI workflow.
- Add expanded documentation, how-to guides, and data flow diagrams.

### [1.0.0] - 2024-06-01
- Initial release: End-to-end wildfire risk mapping pipeline with modular features, diagnostics, and D3.js frontend.

---

*This README was auto-generated and includes quickstart, troubleshooting, API docs, data flow, and a data dictionary.*
