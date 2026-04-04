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

## Data Dictionary

| Field | Description | Source | Type | Units | Min | Max | Formula | Example | Provenance |
|-------|-------------|--------|------|-------|-----|-----|---------|---------|-----------|
| hazard_wildfire | Wildfire probability | USFS WHP | float | 0-1 | 0 | 1 | mean(WHP_pixels_in_block) | 0.23 | REAL/DUMMY |
| hazard_vegetation | Fuel density | NLCD | float | 0-1 | 0 | 1 | forest_pixels/total_pixels | 0.45 | REAL/DUMMY |
| hazard_forest_distance | Distance to forest (inverted) | NLCD | float | 0-1 | 0 | 1 | 1/(1+distance_km) | 0.67 | REAL/DUMMY |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

See `calculations.csv` for the full expanded data dictionary.

---

## How-To Guides

- [How to add a new feature](docs/howto/add_feature.md)
- [How to refresh data](docs/howto/refresh_data.md)
- [How to debug diagnostics](docs/howto/debug_diagnostics.md)

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of major changes and releases.

---

*This README was auto-generated and includes quickstart, troubleshooting, API docs, data flow, and a data dictionary.*
