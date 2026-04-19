# Refreshing `data/real/*.csv` and geospatial inputs

Run everything from the **repository root** with `PYTHONPATH` set so `import src` works.

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

It uses **ACS 2021 5-year** tables at the block-group level for poverty, elderly, vehicle access, and median home value.

**Single command:**

```bash
python scripts/refresh_real_data.py
```

**Expected files:**

| File | Source |
|------|--------|
| `census_population.csv` | Census PL P1_001N, block group |
| `census_housing.csv` | Census PL H1_001N, block group |
| `acs_poverty.csv` | ACS B17001 |
| `acs_elderly.csv` | ACS B01001 |
| `acs_vehicle_access.csv` | ACS B08201 |
| `acs_building_value.csv` | ACS B25077 |

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

After refreshing caches:

```bash
python -m src.pipeline.run_pipeline
```

Check `data/real/diagnostics_report.csv` and feature `*_source` columns in `data/processed/blocks.geojson` for `REAL` vs `DUMMY`.

---

## Quick reference (ordered)

```text
$env:PYTHONPATH="."   # PowerShell
python -m src.pipeline.run_pipeline
python scripts/refresh_real_data.py
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
