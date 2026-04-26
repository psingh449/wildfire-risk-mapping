# Refreshing `data/real/*.csv`, `data/real_cache/…`, and geospatial inputs

Run everything from the **repository root** with `PYTHONPATH` set so `import src` works.

**Canonical store for reproducible per-county imports:** this repo standardizes on **`data/real_cache/counties/{state+county_fips}/<source_id>/<quantity_id>/`**, with a `data.csv` plus `manifest.json` and optional `response.json` (see [`calculations.csv`](calculations.csv) `cache_primary` / `code_locations`). The older flat files under `data/real/*.csv` remain **fallbacks** in some code paths. Use **`python scripts/real_import.py --county <5-digit FIPS> --all`** (or the prefetch script in the README) to fill `real_cache` from Census, ACS, OSM, HIFLD, and raster-side helpers.

**ACS caveats:** for variables such as **poverty (B17001)** and **vehicle access (B08201)**, the API often returns all-nulls at *block group*; the importer then writes **tract** tables (`poverty_tract`, `vehicle_access_tract`) and the feature layer uses tract→block-group assignment with `ESTIMATED` provenance (`scripts/real_import.py`, `src/utils/real_data.py`).

## PowerShell (Windows)

```powershell
cd path\to\wildfire-risk-mapping
$env:PYTHONPATH = "."
```

## Bash / macOS / Linux

```bash
cd /path/to/wildfire-risk-mapping
export PYTHONPATH=.
```

---

## 1. Produce block geometries (`data/processed/blocks.geojson`)

Most downstream scripts read **`data/processed/blocks.geojson`**. Create it with the pipeline:

```bash
python -m src.pipeline.run_pipeline
```

If you only need geometry and already have raw block groups:

- Input polygons: `data/raw/block_groups.geojson`
- The pipeline writes outputs under `data/processed/`.

---

## 2. Census + ACS → `data/real/*.csv`

This project uses **2020 Decennial PL at the block-group level** for population and housing (12-digit GEOIDs that match `block_groups.geojson`).

It uses **ACS 2021 5-year** tables at the block-group level for poverty, elderly, vehicle access, uninsured rate, median home value, median household income, and internet access.

**Preferred command (writes `data/real_cache/…`):**

```bash
python scripts/real_import.py --county <5-digit FIPS> --all
```

**Legacy wrapper (DEPRECATED; calls `real_import.py` under the hood):**

```bash
python scripts/refresh_real_data.py
```

**Legacy flat-file outputs (optional / fallback paths):**

| File | Source |
|------|--------|
| `census_population.csv` | Census PL P1_001N, block group |
| `census_housing.csv` | Census PL H1_001N, block group |
| `acs_poverty.csv` | ACS B17001 |
| `acs_elderly.csv` | ACS B01001 |
| `acs_vehicle_access.csv` | ACS B08201 |
| `acs_building_value.csv` | ACS B25077 |
| `acs_uninsured.csv` | ACS B27010 |
| `acs_median_household_income.csv` | ACS B19013 |
| `acs_internet_access.csv` | ACS B28002 |

**Requirements:** Internet access to `api.census.gov`. No API key is required for typical volume; if you see HTTP 429, wait and retry or use off-peak hours.

**Configure another state/county** (optional): set environment variables before running (see `src/utils/real_data.py`):

- `WILDFIRE_STATE_CODE` (default `06`)
- `WILDFIRE_COUNTY_CODE` (default `007`)

---

## 3. NLCD + WHP rasters (large downloads)

Download archives (hundreds of MB to a few GB):

```bash
python scripts/download_environmental_data.py
```

This fetches **NLCD** and **WHP** zips into `data/geospatial/nlcd/` and `data/geospatial/whp/`. Extract them:

```bash
python scripts/extract_geospatial_zips.py
```

After extraction you should have:

- NLCD: `data/geospatial/nlcd/nlcd_2019_land_cover_l48_20210604.img` (path may vary slightly)
- WHP: a `*.tif` under `data/geospatial/whp/` (name varies by USFS product version)

**Raster-derived CSVs** (require `geopandas`, `rasterio`):

```bash
python scripts/process_whp_zonal_stats.py
python scripts/process_nlcd_vegetation.py
python scripts/process_nlcd_forest_distance.py
```

**Outputs:**

| File | Role |
|------|------|
| `data/real/whp_zonal_stats.csv` | Mean WHP per block group → `hazard_wildfire` |
| `data/real/nlcd_vegetation.csv` | Forest/shrub fraction → `hazard_vegetation` |
| `data/real/nlcd_forest_distance.csv` | Distance to forest edge → `hazard_forest_distance` |

---

## 4. Emergency facilities distances (OSM)

Nearest distances (km) to **fire stations** and **hospitals** from OpenStreetMap in the study-area bbox (via OSMnx):

```bash
python scripts/build_hifld_distances_arcgis.py
```

**Outputs:**

- `data/real/fire_station_dist.csv`
- `data/real/hospital_dist.csv`

*(Despite the script name, the implementation uses OSM, not ArcGIS, for reliability.)*

---

## 5. Road length (OSM)

```bash
python scripts/process_osm_road_length.py
```

Writes `data/real/road_length.csv` (uses OSMnx `features_from_bbox` / graph; may take several minutes on first run).

---

## 6. Re-run the pipeline

After refreshing caches and/or `data/real_cache` imports:

```bash
python -m src.pipeline.run_pipeline
```

Check `data/real/diagnostics_report.csv` and feature `*_source` columns in `data/processed/blocks.geojson` for `REAL` / `ESTIMATED` / `PROXY` / `MISSING` (the pipeline does not generate random “DUMMY” feature values in the production paths).

---

## Quick reference (ordered)

```text
$env:PYTHONPATH="."   # PowerShell
python -m src.pipeline.run_pipeline
python scripts/real_import.py --county 06073 --all
python scripts/download_environmental_data.py
python scripts/extract_geospatial_zips.py
python scripts/process_whp_zonal_stats.py
python scripts/process_nlcd_vegetation.py
python scripts/process_nlcd_forest_distance.py
python scripts/build_hifld_distances_arcgis.py
python scripts/process_osm_road_length.py
python -m src.pipeline.run_pipeline
```

---

## Troubleshooting

- **HTTP 204 with empty body from `api.census.gov`:** A normal successful Census response is **HTTP 200** with a JSON array. If you see **204** or empty content, the request is not reaching the real Census API (common in some CI/sandbox environments, or strict proxies). Run `python scripts/test_census_connection.py` **on your own PC** (where your VPN applies), not only inside an isolated agent terminal.
- **Empty Census/ACS responses:** Confirm you can reach `https://api.census.gov` in a browser; corporate proxies may block automated requests.
- **WHP raster not found:** Open `data/geospatial/whp/` and locate the `*.tif`; adjust `process_whp_zonal_stats.py` if the filename differs.
- **NLCD path:** Ensure `nlcd_2019_land_cover_l48_20210604.img` exists (or update paths in the `process_nlcd_*.py` scripts).
- **OSMnx slow / timeout:** Run again; Overpass/OSM can throttle during peak times.
