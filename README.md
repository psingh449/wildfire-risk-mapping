# Wildfire Risk Mapping

A modular, end-to-end system for block-group level wildfire risk mapping, combining hazard, exposure, vulnerability, and resilience into interpretable scores and an Expected Annual Loss (EAL) proxy. The project features a Python pipeline for data processing and a D3.js-based frontend for interactive visualization.

---

## Usage Examples

- **Run the pipeline:**
  ```bash
  python -m src.pipeline.run_pipeline
  ```
- **Refresh real data (Census/ACS):**
  ```bash
  python scripts/refresh_real_data.py
  ```
- **Download environmental datasets (NLCD, WHP, HIFLD, OSM):**
  ```bash
  python scripts/download_environmental_data.py
  ```
- **Process NLCD zonal stats:**
  ```bash
  python scripts/process_nlcd_zonal_stats.py
  ```
- **Process HIFLD nearest facility distances:**
  ```bash
  python scripts/process_hifld_nearest.py
  ```
- **Process OSM road length per block:**
  ```bash
  python scripts/process_osm_road_length.py
  ```
- **Run tests:**
  ```bash
  pytest tests/
  ```
- **Serve frontend:**
  ```bash
  python -m http.server 8000
  # then open index.html in your browser
  ```

---

## Geospatial Processing Requirements

- Install geospatial libraries:
  ```bash
  pip install geopandas rasterio shapely fiona pyproj rtree osmnx
  ```
- Download environmental datasets and process them as above before running the pipeline for full real data integration.

---

## API Docs

- **Census API:** https://api.census.gov/data/2020/dec/pl
- **ACS API:** https://api.census.gov/data/2021/acs/acs5
- **NLCD:** https://www.mrlc.gov/data
- **WHP:** https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047
- **HIFLD:** https://hifld-geoplatform.opendata.arcgis.com/
- **OSM:** https://download.geofabrik.de/north-america/us/california.html

---

## Data Dictionary

| Field | Description | Source | Type | Min | Max | Provenance |
|-------|-------------|--------|------|-----|-----|-----------|
| hazard_wildfire | Wildfire probability | USFS WHP | float | 0 | 1 | REAL/DUMMY |
| hazard_vegetation | Fuel density | NLCD | float | 0 | 1 | REAL/DUMMY |
| hazard_forest_distance | Distance to forest (inverted) | NLCD | float | 0 | 1 | REAL/DUMMY |
| hazard_score | Combined hazard | Derived | float | 0 | 1 | Derived |
| exposure_population | Population | Census | int | 0 | inf | REAL/DUMMY |
| exposure_housing | Housing units | Census | int | 0 | inf | REAL/DUMMY |
| exposure_building_value | Building value | ACS | float | 0 | inf | REAL/DUMMY |
| exposure_score | Combined exposure | Derived | float | 0 | 1 | Derived |
| vuln_poverty | Poverty rate | ACS | float | 0 | 1 | REAL/DUMMY |
| vuln_elderly | Elderly ratio | ACS | float | 0 | 1 | REAL/DUMMY |
| vuln_vehicle_access | Vehicle access (inverted) | ACS | float | 0 | 1 | REAL/DUMMY |
| vulnerability_score | Combined vulnerability | Derived | float | 0 | 1 | Derived |
| res_fire_station_dist | Fire station access | HIFLD | float | 0 | 1 | REAL/DUMMY |
| res_hospital_dist | Hospital access | HIFLD | float | 0 | 1 | REAL/DUMMY |
| res_road_access | Road connectivity | OSM | float | 0 | 1 | REAL/DUMMY |
| resilience_score | Combined resilience | Derived | float | 0 | 1 | Derived |
| risk_score | Risk score | Derived | float | 0 | 1 | Derived |
| eal | Expected annual loss | Derived | float | 0 | inf | Derived |
| eal_norm | Normalized EAL | Derived | float | 0 | 1 | Derived |
| diagnostics | Validation issues | Internal | object | - | - | - |
| *_source | Provenance (REAL/DUMMY) | Internal | str | - | - | - |
| *_provenance | Data source or fallback reason | Internal | str | - | - | - |

---

## Notes
- All environmental/geospatial data is stored in `data/geospatial/` (not tracked by git).
- All real Census/ACS data is stored in `data/real/`.
- To refresh or update any data, rerun the appropriate script.
- See `calculations.csv` and `calculations_diagram.md` for formulas and data flow.

---

*This README was auto-generated and includes usage, API docs, and a data dictionary for all fields.*
