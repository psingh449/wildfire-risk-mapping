# Wildfire Risk Mapping: Complete Documentation

---

## 1. Project Overview and Quickstart

### 1.1 Overview of the Wildfire Risk System

This wildfire risk mapping system predicts how much wildfire danger each geographic block (a small neighborhood-sized area) faces. It combines information about four key risk components:

- **Hazard** (how likely is a wildfire to start or spread here?)
- **Exposure** (how many people and buildings are in the way?)
- **Vulnerability** (which people are most at-risk if a wildfire happens?)
- **Resilience** (what resources exist to help people escape or recover?)

The final output is a **Risk Score** (0-1 range) and **Expected Annual Loss (EAL)** — a dollar amount representing how much damage we expect in a typical year for each block.

**Key Features:**
- Specification-Driven architecture (calculations.csv documents WHAT, Python code implements HOW)
- Only weights and min/max bounds are dynamically read from calculations.csv at runtime
- Everything else (URLs, formulas, API parameters) is hardcoded in Python
- Comprehensive validation with 8 quality check metrics
- Fallback/dummy data generation when APIs fail
- Full provenance tracking (all data marked REAL or DUMMY)

### 1.2 Quick Start (6 Steps)

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
   # Open index.html in your browser at http://localhost:8000
   ```

6. **Run tests:**
   ```bash
   # On CMD:
   set PYTHONPATH=. & pytest tests/ --maxfail=10 --disable-warnings -q

   # On PowerShell:
   $env:PYTHONPATH='.'; pytest tests/ --maxfail=10 --disable-warnings -q
   
   # For verbose output:
   $env:PYTHONPATH='.'; pytest tests/ -v
   ```

### 1.3 Project Components Overview

The system has four major risk components combined into a unified risk model:

| Component | Purpose | Features | Examples |
|-----------|---------|----------|----------|
| **Hazard** | Fire likelihood & intensity | Wildfire probability, vegetation density, distance to forests | Forest cover, fuel moisture, historical burn patterns |
| **Exposure** | People and assets at risk | Population count, housing units, building value | Census data, property assessments, infrastructure |
| **Vulnerability** | Social fragility & sensitivity | Poverty rate, elderly percentage, vehicle access | ACS socioeconomic data, demographic characteristics |
| **Resilience** | Response and recovery capacity | Fire station proximity, hospital access, road connectivity | Emergency services locations, network access |

### 1.4 Running the Pipeline

**The pipeline executes in 5 stages:**

1. **Stage 1 - Ingestion:** Load raw geographic and attribute data
2. **Stage 2 - Preprocessing:** Standardize coordinates, geographic clipping, ID generation
3. **Stage 3 - Feature Engineering:** Calculate all 17 features from external data sources
4. **Stage 4 - Risk Modeling:** Compute composite scores and final risk metrics
5. **Stage 5 - Validation & Export:** Quality checks and GeoJSON output

**Output files:**
- `data/processed/blocks.geojson` — Main output with all calculations
- `data/real/diagnostics_report.csv` — Validation issues summary
- Logs with warnings and errors for debugging

### 1.5 Serving the Frontend

The frontend visualizes results on an interactive map with:
- Choropleth layers for each metric (Risk, Hazard, Exposure, Vulnerability, Resilience, EAL)
- Hover tooltips showing block details and diagnostics
- Debug mode for viewing data provenance and validation status
- Layer toggle controls for comparing metrics

To serve:
```bash
python -m http.server 8000
```
Open your browser to `http://localhost:8000` and view `index.html`.

### 1.6 Running Tests

The test suite validates all calculations, data sources, and features:

```bash
# Run all tests with summary
$env:PYTHONPATH='.'; pytest tests/ --maxfail=10 --disable-warnings -q

# Run with full details
$env:PYTHONPATH='.'; pytest tests/ -v

# Run specific test file
pytest tests/test_features.py -v

# Run specific test class
pytest tests/test_features.py::TestHazardFeatures -v
```

---

## 2. System Architecture and Pipeline

### 2.1 Entry Point: run_pipeline.py

**Which Python File Runs First?**

File: `src/pipeline/run_pipeline.py`

**How to start it:**
```bash
python -m src.pipeline.run_pipeline
```

**What happens when you run it:**

The program calls the `run()` function which orchestrates a 5-stage pipeline:

```
run_pipeline.py → run() function
    ↓
    [Stage 1] step_ingestion()         → Load raw blocks and attributes
    [Stage 2] step_preprocessing()      → Standardize coordinates
    [Stage 3] run_feature_pipeline()    → Calculate all 17 features
    [Stage 4] step_features()           → Organize features into components
    [Stage 5] step_model()              → Calculate risk scores and EAL
    ↓
    [Export] Save to blocks.geojson
    [Validate] Run quality checks
```

**Entry Point Code Flow:**
```python
def run():
    print("Starting pipeline")
    
    # Stage 1: Load raw data (blocks and attributes)
    gdf = step_ingestion()
    
    # Stage 2: Prepare data (standardize coordinates, geographic clipping)
    gdf = step_preprocessing(gdf)
    
    # Stage 3: Calculate all features (hazard, exposure, vulnerability, resilience)
    gdf = run_feature_pipeline(gdf)
    gdf = step_features(gdf)
    
    # Stage 4: Calculate final risk scores
    gdf = step_model(gdf)
    
    # Stage 5: Export results and validate
    # (Results saved to data/processed/blocks.geojson)
    
    print("Pipeline completed")
```

**Key files involved at entry:**
- `src/pipeline/run_pipeline.py` — Main orchestrator
- `src/pipeline/steps.py` — Individual stage implementations
- `src/pipeline/feature_pipeline.py` — Feature engineering coordinator

### 2.2 5-Stage Pipeline Orchestration

#### Stage 1: Ingestion
**Purpose:** Load raw geographic and attribute data

**Outputs:**
- GeoDataFrame with block geometries and attributes
- Basic columns: GEOID, geometry, block_id

**Files involved:**
- `src/pipeline/steps.py:step_ingestion()`
- `src/utils/real_data.py` — Data fetching functions
- Input: `data/raw/block_groups.geojson` (or mock geometry)

#### Stage 2: Preprocessing
**Purpose:** Standardize data for analysis

**Operations:**
- Coordinate reference system (CRS) transformation to Web Mercator
- Geographic clipping to analysis boundary
- Geographic ID generation
- Block centroid calculation for distance-based features

**Files involved:**
- `src/pipeline/steps.py:step_preprocessing()`
- `src/utils/validator.py` — Basic validation

#### Stage 3: Feature Engineering
**Purpose:** Calculate all 17 features from 9 data sources

**Operations:**
- Fetch data from external APIs and local files
- Compute hazard, exposure, vulnerability, and resilience features
- Normalize features to 0-1 range
- Handle missing data with fallback dummy values
- Track data provenance (REAL vs. DUMMY)

**Files involved:**
- `src/pipeline/feature_pipeline.py:run_feature_pipeline()`
- `src/features/hazard.py` — Hazard features (wildfire, vegetation, forest distance)
- `src/features/exposure.py` — Exposure features (population, housing, building value)
- `src/features/vulnerability.py` — Vulnerability features (poverty, elderly, vehicle access)
- `src/features/resilience.py` — Resilience features (fire stations, hospitals, road access)
- `src/utils/real_data.py` — All 9 data source fetching functions
- `src/utils/dummy_data.py` — Fallback dummy value generation

#### Stage 4: Risk Modeling
**Purpose:** Calculate composite scores and final risk metrics

**Calculations:**
1. **Component Scores:** Weighted averages of constituent features
   - Hazard Score = weighted average of (hazard_wildfire, hazard_vegetation, hazard_forest_distance)
   - Exposure Score = weighted average of (exposure_population, exposure_housing, exposure_building_value)
   - Vulnerability Score = weighted average of (vuln_poverty, vuln_elderly, vuln_vehicle_access)
   - Resilience Score = weighted average of (res_fire_station_dist, res_hospital_dist, res_road_access)

2. **Risk Score:** Multiplicative model
   - `risk_score = hazard_score × exposure_score × vulnerability_score × (1 - resilience_score)`
   - Range: 0 to 1 (0 = no risk, 1 = maximum risk)

3. **Expected Annual Loss (EAL):** Financial impact
   - `eal = risk_score × building_value_est`
   - Represents expected monetary damage per year

4. **Normalized Metrics:** For visualization
   - `risk_score_norm` = min-max normalized across all blocks
   - `eal_norm` = min-max normalized across all blocks

**Files involved:**
- `src/pipeline/steps.py:step_model()`
- `src/models/risk_model.py` — Risk calculation functions
- `src/features/build_features.py` — Composite score computation

#### Stage 5: Validation & Export
**Purpose:** Verify data quality and save results

**Operations:**
- Run 8 validation metrics
- Generate diagnostics report
- Export to GeoJSON
- Save diagnostics CSV
- Log warnings and errors

**Files involved:**
- `src/validation/metrics.py` — Validation metric functions
- `src/utils/validator.py` — Basic validation checks
- `src/utils/diagnostics.py` — Diagnostics generation

### 2.3 Pipeline Contract and Schema

Each step must follow a contract:

**Input Requirements:**
- GeoDataFrame with required schema
- Valid geometries and CRS

**Output Requirements:**
- GeoDataFrame with additional columns
- No step should remove existing columns
- All new columns must be documented in calculations.csv

**Rules:**
- No step should depend on internal logic of another
- Only depend on schema (columns and data types)
- **All feature and validation definitions are maintained in `calculations.csv`**
- Every output column must have a corresponding row in calculations.csv

**Data Flow:**
```
Step 1 Output → Step 2 Input
Step 2 Output → Step 3 Input
Step 3 Output → Step 4 Input
Step 4 Output → Step 5 Input
Step 5 Output → blocks.geojson
```

### 2.4 Architecture Patterns (Specification-Driven Design)

This system follows a **SPECIFICATION-DRIVEN** architecture:

```
calculations.csv (What features should exist)
         ↓ (mostly documentation)
         ↓ (humans read to understand)
         ↓
Python Code (How to compute them)
         ↓ (reads only weights + min/max dynamically)
         ↓ (hardcodes everything else)
         ↓
Runtime Behavior (Actual calculations)
```

**Why This Design?**

| Aspect | Pros | Cons |
|--------|------|------|
| **Simplicity** | Code is straightforward and readable | Less flexibility for configuration |
| **Type Safety** | Python enforces types at compile time | Schema-code mismatch risk |
| **Debuggability** | Easy to trace execution | Duplication between CSV and code |
| **Performance** | No CSV parsing overhead | Maintenance burden |
| **IDE Support** | Code editors can autocomplete | Two places to update |

**Dynamic vs. Static Columns:**

| Column | Dynamically Read? | Used By | Updated By |
|--------|-------------------|---------|-----------|
| weight_group, weight | ✅ YES | `src/features/build_features.py` | CSV only (no code change needed) |
| min, max | ✅ YES | `src/utils/real_data.py` | CSV only (for fallback bounds) |
| data_source | ❌ NO | Documentation only | Manual (CSV + code must sync) |
| source_url | ❌ NO | Documentation only | Manual (CSV + code must sync) |
| api_endpoint | ❌ NO | Hardcoded in code | Manual (CSV + code must sync) |
| api_params | ❌ NO | Hardcoded in code | Manual (CSV + code must sync) |
| calculation_formula | ❌ NO | Hardcoded in code | Manual (CSV + code must sync) |
| All others | ❌ NO | Documentation only | Manual (CSV + code must sync) |

### 2.5 Code-to-Documentation Mapping

**Where Feature Definitions Live:**

| Feature | Definition in | Implementation in | Data Source |
|---------|---|---|---|
| hazard_wildfire | calculations.csv row 1 | `src/features/hazard.py` | WHP raster |
| hazard_vegetation | calculations.csv row 2 | `src/features/hazard.py` | NLCD raster |
| hazard_forest_distance | calculations.csv row 3 | `src/features/hazard.py` | NLCD raster |
| exposure_population | calculations.csv row 5 | `src/features/exposure.py` | Census API |
| exposure_housing | calculations.csv row 6 | `src/features/exposure.py` | Census API |
| exposure_building_value | calculations.csv row 7 | `src/features/exposure.py` | ACS API |
| vuln_poverty | calculations.csv row 9 | `src/features/vulnerability.py` | ACS API |
| vuln_elderly | calculations.csv row 10 | `src/features/vulnerability.py` | ACS API |
| vuln_vehicle_access | calculations.csv row 11 | `src/features/vulnerability.py` | ACS API |
| res_fire_station_dist | calculations.csv row 13 | `src/features/resilience.py` | HIFLD data |
| res_hospital_dist | calculations.csv row 14 | `src/features/resilience.py` | HIFLD data |
| res_road_access | calculations.csv row 15 | `src/features/resilience.py` | OSM data |
| hazard_score | calculations.csv row 4 | `src/features/build_features.py` | Composite |
| exposure_score | calculations.csv row 8 | `src/features/build_features.py` | Composite |
| vuln_score | calculations.csv row 12 | `src/features/build_features.py` | Composite |
| resilience_score | calculations.csv row 16 | `src/features/build_features.py` | Composite |
| risk_score | calculations.csv row 17 | `src/models/risk_model.py` | Model |
| eal | calculations.csv row 18 | `src/models/risk_model.py` | Model |

---

## 3. Data Sources and Ingestion

The program retrieves information from **9 external sources**. Each source is fetched through dedicated Python functions, cached locally, and can generate fallback dummy data if APIs fail.

### 3.1 WHP (Wildland-Urban Interface Hazard Potential)

**What it measures:** Wildfire probability and intensity potential

**Source:** US Forest Service (USFS)  
**URL:** https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_whp_data()`
- Feature: `src/features/hazard.py` → `compute_hazard_wildfire()`

**Data Storage:**
- **Cached locally:** `data/real/whp_butte.csv` or `data/real/whp_butte.tif` (raster)
- **Output column:** `hazard_wildfire` (range: 0-1)

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | USFS WHP |
| source_url | https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047 |
| api_endpoint | (direct file download, not API) |
| calculation_formula | mean(WHP_pixels_in_block) |

**Step-by-Step Process:**
1. Download WHP raster data (grid-based map where each pixel has a wildfire risk value)
2. Overlay block boundaries on top of the raster
3. Calculate average risk value of all pixels within each block
4. Normalize to 0-1 range (if needed)
5. Store in `hazard_wildfire` column

**Fallback Behavior:** If download fails, generate random values in [0, 1]

### 3.2 NLCD (National Land Cover Database)

**What it measures:** Land cover type (forest, shrub, urban, water, etc.)

**Source:** US Geological Survey  
**URL:** https://www.mrlc.gov/data

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_nlcd_data()`
- Features: `src/features/hazard.py` → Multiple functions

**Data Storage:**
- **Cached locally:** `data/real/nlcd_butte.tif` (raster file)
- **Output columns:**
  - `hazard_vegetation` (fuel density, range: 0-1)
  - `hazard_forest_distance` (inverted distance to forest, range: 0-1)

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | NLCD - National Land Cover Database |
| source_url | https://www.mrlc.gov/data |
| transform_steps | Classify forest/shrub; count pixels; invert distance |
| calculation_formula | forest_pixels / total_pixels (for vegetation); 1/(1+distance) (for distance) |

**Step-by-Step Process:**
1. Download NLCD raster (each pixel labeled with land type)
2. Classify pixels as "forest" or "shrub" (fire-prone) vs. "urban" or "water" (fire-resistant)
3. For each block:
   - Count forest/shrub pixels → `hazard_vegetation` (0-1)
   - Find distance to nearest forest edge → `hazard_forest_distance` (0-1)

**Fallback Behavior:** If download fails, generate random values in [0, 1]

### 3.3 Census Population Data

**What it measures:** Number of people living in each block

**Source:** US Census Bureau, 2020 Census (Decennial)  
**API:** https://api.census.gov/data/2020/dec/pl

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_census_population()`, `compute_exposure_population_real()`
- Feature: `src/features/exposure.py` → Population feature

**Data Storage:**
- **Cached locally:** `data/real/census_population.csv` (GEOID → population)
- **Live API:** Fetches if local file doesn't exist
- **Output column:** `exposure_population` (range: 0-1 normalized)

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | Census PL (Public Law) 2020 |
| api_endpoint | /data/2020/dec/pl |
| api_params | get=P1_001N&for=block:*&in=state:06 county:007 |
| join_keys | GEOID |
| calculation_formula | P1_001N (direct value, no transformation) |

**Step-by-Step Process:**
1. Check if local file `data/real/census_population.csv` exists
2. If not, construct Census API request:
   - `get=P1_001N` → Request total population variable
   - `for=block:*` → For all census blocks
   - `in=state:06 county:007` → In Butte County, California
3. Parse response into GEOID → population dictionary
4. Save to `data/real/census_population.csv` for future use
5. Join to blocks using GEOID
6. Normalize to 0-1 using min/max from calculations.csv

**Fallback Behavior:** If API fails, generate random integers in [0, max_population] from CSV

### 3.4 Census Housing Units

**What it measures:** Number of housing units in each block

**Source:** US Census Bureau, 2020 Census  
**API:** https://api.census.gov/data/2020/dec/pl

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_census_housing()`, `compute_exposure_housing_real()`
- Feature: `src/features/exposure.py` → Housing feature

**Data Storage:**
- **Cached locally:** `data/real/census_housing.csv` (GEOID → housing units)
- **Output column:** `exposure_housing` (range: 0-1 normalized)

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | Census H1 (Housing) 2020 |
| api_endpoint | /data/2020/dec/pl |
| api_params | get=H1_001N&for=block:*&in=state:06 county:007 |
| calculation_formula | H1_001N (direct value) |

**Fallback Behavior:** If API fails, generate random integers in [0, max_housing] from CSV

### 3.5 ACS (American Community Survey)

**What it measures:** Socioeconomic characteristics (poverty, elderly, vehicle ownership, building value)

**Source:** US Census Bureau, 2021 American Community Survey (5-year)  
**API:** https://api.census.gov/data/2021/acs/acs5

**Python Files:**
- Fetcher: `src/utils/real_data.py` → Multiple functions:
  - `fetch_acs_blockgroup()` — Generic ACS fetcher
  - `compute_vuln_poverty_real()` → poverty rate
  - `compute_vuln_elderly_real()` → elderly percentage
  - `compute_vuln_vehicle_access_real()` → vehicle access
  - `compute_exposure_building_value_real()` → building value
- Features: `src/features/vulnerability.py` and `src/features/exposure.py`

**Data Storage:**
- **Cached locally:** Multiple CSVs in `data/real/`:
  - `acs_poverty.csv`
  - `acs_elderly.csv`
  - `acs_vehicle.csv`
  - `acs_building_value.csv`
- **Output columns:**
  - `vuln_poverty` (poverty rate, 0-1)
  - `vuln_elderly` (elderly percentage, 0-1)
  - `vuln_vehicle_access` (households without vehicles, 0-1)
  - `exposure_building_value` (median home value in dollars)

**How calculations.csv Directs This (Example: Poverty):**

| CSV Column | Value |
|------------|-------|
| data_source | ACS American Community Survey |
| api_endpoint | /data/2021/acs/acs5 |
| api_params | get=B17001_002E,B17001_001E&for=tract:* |
| transform_steps | compute poverty rate; map tract to block; normalize |
| calculation_formula | B17001_002E / B17001_001E |

**Step-by-Step Process for Each ACS Feature:**
1. Fetch tract-level or block group-level data via API
2. Calculate the metric (poverty percentage, elderly percentage, etc.)
3. Map from tract/block group down to individual blocks (spatial join)
4. Normalize to 0-1 scale using min/max from calculations.csv
5. Store in appropriate column

**Fallback Behavior:** If API fails, generate random values in [0, 1]

### 3.6 HIFLD (Homeland Infrastructure Foundation-Level Data)

**What it measures:** Locations of fire stations and hospitals

**Source:** HIFLD via ArcGIS Open Data  
**URL:** https://hifld-geoplatform.opendata.arcgis.com

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_hifld_data()`
- Features: `src/features/resilience.py` → Distance features

**Data Storage:**
- **Cached locally:**
  - `data/real/fire_stations.csv` (lat, lon, name)
  - `data/real/hospitals.csv` (lat, lon, name)
- **Output columns:**
  - `res_fire_station_dist` (inverted distance, 0-1, closer = higher)
  - `res_hospital_dist` (inverted distance, 0-1, closer = higher)

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | HIFLD Emergency Infrastructure |
| source_url | https://hifld-geoplatform.opendata.arcgis.com |
| transform_steps | nearest distance; invert |
| calculation_formula | 1/(1+distance_km) |

**Step-by-Step Process:**
1. Download fire station point locations (lat/lon, names)
2. Download hospital point locations (lat/lon, names)
3. For each block's geographic center (centroid):
   - Calculate distance to nearest fire station (in km)
   - Apply inversion formula: `1 / (1 + distance_km)` → normalize to 0-1
   - Store in `res_fire_station_dist`
4. Repeat for hospitals → `res_hospital_dist`

**Fallback Behavior:** If download fails, generate random values in [0, 1]

### 3.7 OpenStreetMap (OSM) Roads

**What it measures:** Road network connectivity and accessibility

**Source:** OpenStreetMap via Overpass API  
**URL:** https://overpass-api.de/api/interpreter

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_osm_roads()`, `compute_res_road_access_real()`
- Feature: `src/features/resilience.py` → Road access feature

**Data Storage:**
- **Cached locally:** `data/real/osm_roads.geojson` (road network geometries)
- **Output column:** `res_road_access` (road density or network accessibility, 0-1)

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | OpenStreetMap |
| source_url | https://www.openstreetmap.org |
| api_endpoint | https://overpass-api.de/api/interpreter |
| transform_steps | query road network; calculate connectivity |
| calculation_formula | road_length_in_block / area (or connectivity metric) |

**Step-by-Step Process:**
1. Query Overpass API for roads in analysis area
2. Cache road geometries as GeoJSON
3. For each block:
   - Calculate road length within block
   - Divide by block area to get road density
   - Normalize to 0-1 range
   - Store in `res_road_access`

**Fallback Behavior:** If API fails, generate random values in [0, 1]

### 3.8 MTBS (Monitoring Trends in Burn Severity)

**What it measures:** Historical fire perimeters and severity from 1984-present

**Source:** USGS / USDA  
**URL:** https://www.mtbs.gov/

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_mtbs_perimeters()`
- Validation: `src/validation/metrics.py` → Validation only

**Data Storage:**
- **External reference:** `data/external/mtbs_fire_perimeters.geojson`
- **Used by:** Validation metrics (fire overlap ratio)
- **Not a direct feature:** Used only for validation comparison

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | MTBS Fire Perimeters |
| source_url | https://www.mtbs.gov/ |
| validation_use | fire_overlap_ratio metric |

**Step-by-Step Process:**
1. Download historical fire perimeters (1984-present)
2. Cache as GeoJSON
3. During validation:
   - Calculate overlap between each block and historical burns
   - Express as percentage of block area
   - Compare hazard prediction against actual fire occurrence

**Fallback Behavior:** If data not available, validation metric returns 0/null

### 3.9 FEMA NRI (National Risk Index)

**What it measures:** Nationally-standardized risk assessment across multiple hazards

**Source:** FEMA  
**URL:** https://www.fema.gov/disaster/national-risk-index

**Python Files:**
- Fetcher: `src/utils/real_data.py` → `fetch_fema_nri()`
- Validation: `src/validation/metrics.py` → Validation only

**Data Storage:**
- **External reference:** `data/external/fema_nri_county.csv` (county-level aggregates)
- **Used by:** Validation metrics (FEMA comparison)
- **Not a direct feature:** Used only for validation

**How calculations.csv Directs This:**

| CSV Column | Value |
|------------|-------|
| data_source | FEMA National Risk Index |
| source_url | https://www.fema.gov/disaster/national-risk-index |
| validation_use | fema_nri_comparison metric |

**Step-by-Step Process:**
1. Download FEMA NRI county-level risk scores
2. Cache as CSV
3. During validation:
   - Aggregate our block-level scores to county level
   - Compare against FEMA county-level scores
   - Measure correlation and difference

**Fallback Behavior:** If data not available, validation metric returns 0/null

---

## 4. Feature Engineering and calculations.csv

### 4.1 Understanding calculations.csv

**Purpose:** calculations.csv is the canonical specification document that describes what features should exist, how they should be calculated, what data sources they use, and what validation rules apply.

**Structure:** 27 feature rows × 28 columns

**8 Column Categories:**

#### 1. **Identification Columns**
- `geojson_property` — Column name in output GeoJSON
- `feature_name` — Human-readable feature name
- `component` — Which risk component (Hazard, Exposure, Vulnerability, Resilience, Composite, Model, Validation)

#### 2. **Data Source Columns**
- `data_source` — Which system provides the data (USFS, Census, ACS, HIFLD, etc.)
- `source_url` — Where humans can download the data
- `api_endpoint` — API endpoint path (if applicable)
- `api_params` — Query parameters (if applicable)
- `dependencies` — Which other features must exist first

#### 3. **Calculation Columns**
- `calculation_formula` — Mathematical formula or code logic
- `join_keys` — How to spatially match data to blocks (GEOID, centroid distance, etc.)
- `transform_steps` — Preprocessing operations

#### 4. **Bounds and Ranges Columns**
- `min` — Minimum expected value (used for validation and fallback generation)
- `max` — Maximum expected value
- `units` — Measurement units (count, percentage, distance, dollars, etc.)

#### 5. **Weighting Columns**
- `weight_group` — Group for weighted composite (e.g., "hazard_score")
- `weight` — Weight value for composite score (e.g., 0.333333)

#### 6. **Metadata Columns**
- `description` — Detailed explanation
- `interpretation` — What higher values mean
- `data_type` — Python/database type (int, float, boolean, category)
- `validation_rule` — Specific validation logic
- `update_frequency` — How often data is refreshed

#### 7. **Status Columns**
- `status` — Implementation status (IMPLEMENTED, EXPERIMENTAL, etc.)
- `notes` — Special considerations
- `priority` — Implementation priority

#### 8. **Reference Columns**
- `canonical_source` — Primary reference document
- `last_updated` — Last time row was updated

**Example Row (Hazard Wildfire):**
```
geojson_property: hazard_wildfire
feature_name: Wildfire Hazard Potential
component: Hazard
data_source: USFS WHP
source_url: https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047
calculation_formula: mean(WHP_pixels_in_block)
min: 0
max: 1
units: normalized (0-1)
weight_group: hazard_score
weight: 0.333333
description: Average wildfire probability and intensity potential
interpretation: Higher values indicate greater wildfire threat
data_type: float
```

### 4.2 Dynamic vs. Static Columns (Specification vs. Implementation)

**CRITICAL INSIGHT:** Only 2 of 28 columns are **dynamically read** at runtime. The rest are **static documentation**.

#### ✅ DYNAMICALLY READ (2 columns only)

**1. weight_group + weight**
```
Read by: src/features/build_features.py, lines 37-72
Function: _load_component_weights_from_calculations()

Example:
    row.weight_group = "hazard_score"
    row.weight = 0.333333
    
Used for: Computing composite scores
    hazard_score = 0.333*wildfire + 0.333*vegetation + 0.333*forest_distance

Verification: Change weight 0.333→0.5 in CSV, run pipeline → score changes ✓
```

**2. min + max**
```
Read by: src/utils/real_data.py, lines 26-52
Function: get_limits(var)

Example:
    row.min = 0
    row.max = 100000
    
Used for: Fallback dummy data generation
    If API fails: generate random integers between min and max

Verification: Delete API cache, run pipeline → dummy data stays within min/max ✓
```

#### ❌ STATIC DOCUMENTATION (26 columns)

**Hardcoded in Python Code:**
- data_source, source_url, api_endpoint, api_params
- join_keys, dependencies
- calculation_formula, transform_steps
- units, interpretation, validation_rule
- All other columns

**Example: Hardcoded URLs**
```python
# src/utils/real_data.py, lines 103-104 (NOT read from CSV)
CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"
# Even though calculations.csv row 5 specifies source_url, 
# Python hardcodes this constant
# Changing CSV doesn't change behavior ❌
```

**Example: Hardcoded API Parameters**
```python
# src/utils/real_data.py, lines 108-113 (NOT read from CSV)
params = {
    "get": "P1_001N,GEOID",         # Hardcoded, not read from api_params
    "for": "block:*",               # Hardcoded, not read
    "in": f"state:{STATE_CODE} county:{COUNTY_CODE}"  # Hardcoded
}
# Changing CSV api_params doesn't affect code ❌
```

**Example: Hardcoded Formulas**
```python
# src/features/hazard.py (NOT read from CSV)
hazard_wildfire = gdf["WHP_zonal_mean"]
# calculation_formula in CSV says "mean(WHP_pixels)" 
# but formula is hardcoded in Python as accessing specific column ❌

# src/utils/real_data.py (NOT read from CSV)
res_fire_station_dist = 1 / (1 + distance_km)
# CSV says formula "1/(1+distance_km)" but code hardcodes this logic ❌
```

### 4.3 Composite Score Weighting System

**How Composite Scores Are Calculated:**

All composite scores (Hazard, Exposure, Vulnerability, Resilience) are **weighted averages** of their constituent features.

**Formula:**
```
component_score = Σ (feature_normalized × weight) / Σ weights
```

**Process:**

1. **Normalize each feature to 0-1** using min/max from calculations.csv:
   ```
   feature_normalized = (feature_value - min) / (max - min)
   clipped to [0, 1] range
   ```

2. **Load weights from calculations.csv:**
   ```
   weights = _load_component_weights_from_calculations()
   # Reads weight_group + weight columns
   ```

3. **Compute weighted average:**
   ```
   hazard_score = (
       0.333 * hazard_wildfire_norm +
       0.333 * hazard_vegetation_norm +
       0.333 * hazard_forest_distance_norm
   ) / 1.0
   ```

4. **Repeat for each component:**
   - Exposure Score (population, housing, building value)
   - Vulnerability Score (poverty, elderly, vehicle access)
   - Resilience Score (fire stations, hospitals, road access)

**Current Weights (from calculations.csv):**

| Feature | Weight | Total |
|---------|--------|-------|
| **Hazard** | | 1.0 |
| hazard_wildfire | 0.333333 | |
| hazard_vegetation | 0.333333 | |
| hazard_forest_distance | 0.333334 | |
| **Exposure** | | 1.0 |
| exposure_population | 0.333333 | |
| exposure_housing | 0.333333 | |
| exposure_building_value | 0.333334 | |
| **Vulnerability** | | 1.0 |
| vuln_poverty | 0.333333 | |
| vuln_elderly | 0.333333 | |
| vuln_vehicle_access | 0.333334 | |
| **Resilience** | | 1.0 |
| res_fire_station_dist | 0.333333 | |
| res_hospital_dist | 0.333333 | |
| res_road_access | 0.333334 | |

### 4.4 Fallback and Dummy Data Generation

**When Fallback is Needed:**

If an API call fails (network error, rate limit, service down), the system generates dummy/synthetic data using bounds from calculations.csv.

**Fallback Generation Process:**

1. **API call fails** (network error, timeout, 503 Service Unavailable)

2. **Get bounds from calculations.csv:**
   ```python
   min_val, max_val = get_limits("exposure_population")
   # Returns: (0, 100000) for population
   ```

3. **Generate random data within bounds:**
   ```python
   # For integer features (counts)
   dummy_value = random.randint(min_val, max_val)
   
   # For float features (normalized)
   dummy_value = random.uniform(min_val, max_val)
   ```

4. **Mark data as DUMMY in provenance:**
   ```python
   gdf["exposure_population_source"] = "DUMMY"
   gdf["exposure_population_provenance"] = "API failed; generated random [0, 100000]"
   ```

5. **Log warning and continue pipeline**

**Why Fallback Bounds?**

- **Validation:** Dummy data must stay within expected ranges
- **Plotting:** Visualization min/max are realistic
- **Quality:** Diagnostics flag DUMMY vs. REAL data

**Columns Used for Fallback:**
- `min` — Lower bound for random generation
- `max` — Upper bound for random generation

**Example:**
```
Feature: exposure_population
Expected range: 0 to 100,000 people per block
If API fails: Generate random integers between 0 and 100,000
Output: exposure_population = random value in [0, 100000]
Marked: exposure_population_source = "DUMMY"
```

### 4.5 Column-by-Column Usage Mapping

| Row | Feature | Group | Dynamic Columns | Static Columns | Purpose |
|-----|---------|-------|---|---|---------|
| 1 | hazard_wildfire | Hazard | weight: 0.333 | source_url, formula | Direct feature |
| 2 | hazard_vegetation | Hazard | weight: 0.333 | source_url, formula | Direct feature |
| 3 | hazard_forest_distance | Hazard | weight: 0.333 | source_url, formula | Direct feature |
| 4 | hazard_score | Hazard | weights: 0.333 ea | formula | Composite |
| 5 | exposure_population | Exposure | weight: 0.333, min/max | source_url, API | Direct feature |
| 6 | exposure_housing | Exposure | weight: 0.333, min/max | source_url, API | Direct feature |
| 7 | exposure_building_value | Exposure | weight: 0.333, min/max | source_url, API | Direct feature |
| 8 | exposure_score | Exposure | weights: 0.333 ea | formula | Composite |
| 9 | vuln_poverty | Vulnerability | weight: 0.333, min/max | source_url, API | Direct feature |
| 10 | vuln_elderly | Vulnerability | weight: 0.333, min/max | source_url, API | Direct feature |
| 11 | vuln_vehicle_access | Vulnerability | weight: 0.333, min/max | source_url, API | Direct feature |
| 12 | vuln_score | Vulnerability | weights: 0.333 ea | formula | Composite |
| 13 | res_fire_station_dist | Resilience | weight: 0.333, min/max | source_url | Direct feature |
| 14 | res_hospital_dist | Resilience | weight: 0.333, min/max | source_url | Direct feature |
| 15 | res_road_access | Resilience | weight: 0.333, min/max | source_url, API | Direct feature |
| 16 | resilience_score | Resilience | weights: 0.333 ea | formula | Composite |
| 17 | risk_score | Model | min/max | formula | Output metric |
| 18 | eal | Model | min/max | formula | Output metric |
| 19 | eal_normalized | Model | min/max | formula | Output metric |
| 20-27 | validation_* | Validation | — | formula | Quality checks |

### 4.6 Risk Score Calculation Formula

**The Risk Model:**

```
risk_score = hazard_score × exposure_score × vulnerability_score × (1 - resilience_score)
```

**Interpretation:**
- **Multiplicative model:** All factors must be present for risk
- **0 to 1 range:** 0 = no risk, 1 = maximum risk
- **Hazard × Exposure × Vulnerability:** Risk increases with threat × consequences
- **(1 - Resilience):** More resilience → Lower risk

**Example Calculation:**
```
hazard_score = 0.7        (High hazard)
exposure_score = 0.6      (Moderate exposure)
vulnerability_score = 0.8 (High vulnerability)
resilience_score = 0.4    (Moderate resilience)

risk_score = 0.7 × 0.6 × 0.8 × (1 - 0.4)
           = 0.7 × 0.6 × 0.8 × 0.6
           = 0.2016
           → 20% risk (on 0-1 scale)
```

**Implementation:**
```python
# src/models/risk_model.py
risk_score = (
    gdf["hazard_score"] *
    gdf["exposure_score"] *
    gdf["vulnerability_score"] *
    (1 - gdf["resilience_score"])
)
gdf["risk_score"] = risk_score.clip(0, 1)  # Ensure 0-1 range
```

### 4.7 Expected Annual Loss (EAL) Model

**Formula:**
```
eal = risk_score × building_value_est
```

**Interpretation:**
- **Financial impact:** Expected monetary damage per year
- **building_value_est:** Total residential building value in block
  - Estimated as: `exposure_housing × avg_home_value`
  - Average home value typically ~$300,000 (regional parameter)

**Example Calculation:**
```
risk_score = 0.2016
housing_units = 100 houses
avg_value_per_house = $300,000
building_value_est = 100 × $300,000 = $30,000,000

eal = 0.2016 × $30,000,000
    = $6,048,000
    → Expected $6M damage per year for this block
```

**Implementation:**
```python
# src/models/risk_model.py
building_value_est = gdf["exposure_housing"] * 300000
eal = gdf["risk_score"] * building_value_est
gdf["eal"] = eal
```

**Normalization for Visualization:**
```python
# Min-max normalization for choropleth display
eal_min = gdf["eal"].min()
eal_max = gdf["eal"].max()
gdf["eal_normalized"] = (gdf["eal"] - eal_min) / (eal_max - eal_min)
gdf["eal_normalized"] = gdf["eal_normalized"].clip(0, 1)
```

### 4.8 Architecture Insight: Why Only Weights Are Dynamic

**The Trade-off:**

| Aspect | If Everything Were Dynamic | Current (Weights Only) |
|--------|---|---|
| **Flexibility** | High (change CSV, change behavior) | Lower (code changes needed) |
| **Simplicity** | Complex (CSV interpreter needed) | Simple (Python code straightforward) |
| **Performance** | Slower (CSV parsing per run) | Faster (no parsing overhead) |
| **Maintainability** | Hard (sync between CSV and code) | Medium (weights auto-sync) |
| **Type Safety** | Weak (everything strings) | Strong (Python types enforced) |
| **Debuggability** | Hard (trace through interpreter) | Easy (IDE debugging) |

**Why Weights Make Sense to Be Dynamic:**
1. Frequently adjusted (parameter tuning)
2. Different stakeholders want different weights
3. No code changes needed for new combinations
4. Easy to express in CSV format (single number)

**Why Everything Else Remains Hardcoded:**
1. URLs are stable (don't change)
2. API parameters are complex (specific to each source)
3. Formulas are implementation logic (harder to express in CSV)
4. Python code is more maintainable than configuration interpreter
5. Type safety and performance matter

**Recommendation:**
- ✅ Keep weights dynamic (in CSV)
- ✅ Keep formulas in code (clearer and faster)
- ⚠️ Document both CSV and code when schemas change
- ⚠️ Add tests to catch sync mismatches

---

## 5. Validation, Quality Checks, and Diagnostics

### 5.1 Basic Validation Checks (4 Functions)

Located in: `src/utils/validator.py`

#### 1. validate_columns()
**Purpose:** Check all required features exist with correct column names

**Implementation:**
```python
def validate_columns(gdf):
    required_columns = [
        'hazard_wildfire', 'hazard_vegetation', 'hazard_forest_distance', 'hazard_score',
        'exposure_population', 'exposure_housing', 'exposure_building_value', 'exposure_score',
        'vuln_poverty', 'vuln_elderly', 'vuln_vehicle_access', 'vuln_score',
        'res_fire_station_dist', 'res_hospital_dist', 'res_road_access', 'resilience_score',
        'risk_score', 'eal'
    ]
    missing = [col for col in required_columns if col not in gdf.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return True
```

**What it checks:**
- All 17 features present
- All 4 component scores present
- Risk and EAL columns exist

#### 2. validate_nulls()
**Purpose:** Check for missing/null values that would indicate incomplete computation

**Implementation:**
```python
def validate_nulls(gdf):
    null_cols = gdf.isnull().sum()
    if null_cols[null_cols > 0].any():
        return {
            "status": "WARNING",
            "message": f"Null values found: {null_cols[null_cols > 0].to_dict()}",
            "impact": "These blocks may have invalid scores"
        }
    return {"status": "PASS"}
```

**What it checks:**
- No null values in any feature or score columns
- All blocks have complete data

#### 3. validate_ranges()
**Purpose:** Check all normalized features are within 0-1 range

**Implementation:**
```python
def validate_ranges(gdf):
    normalized_cols = [col for col in gdf.columns if col not in ['geometry', 'GEOID', ...]]
    out_of_range = {}
    for col in normalized_cols:
        out_of_range_count = ((gdf[col] < 0) | (gdf[col] > 1)).sum()
        if out_of_range_count > 0:
            out_of_range[col] = out_of_range_count
    
    if out_of_range:
        return {"status": "WARNING", "out_of_range_counts": out_of_range}
    return {"status": "PASS"}
```

**What it checks:**
- Hazard score: [0, 1]
- Exposure score: [0, 1]
- Vulnerability score: [0, 1]
- Resilience score: [0, 1]
- Risk score: [0, 1]

**Known Issues:**
- res_fire_station_dist, res_hospital_dist occasionally exceed 1.0 (distance formula issue)
- hazard_forest_distance occasionally exceeds 1.0

#### 4. validate_types()
**Purpose:** Check all columns have expected data types

**Implementation:**
```python
def validate_types(gdf):
    expected_types = {
        'hazard_wildfire': 'float',
        'exposure_population': 'int',
        'risk_score': 'float',
        'eal': 'float'
    }
    errors = {}
    for col, expected_type in expected_types.items():
        if col in gdf.columns:
            actual_type = str(gdf[col].dtype)
            if expected_type not in actual_type:
                errors[col] = f"Expected {expected_type}, got {actual_type}"
    
    if errors:
        return {"status": "WARNING", "type_mismatches": errors}
    return {"status": "PASS"}
```

**What it checks:**
- Integer columns (population, housing)
- Float columns (scores, normalized values)
- Consistent types across all blocks

### 5.2 Advanced Validation Metrics (8 Functions)

Located in: `src/validation/metrics.py`

#### 1. aggregate_block_to_county()
**Purpose:** Validate geographic aggregation from blocks to counties

**Calculation:**
```python
county_risk = gdf.groupby('county_code')['risk_score'].mean()
county_eal = gdf.groupby('county_code')['eal'].sum()
```

**Output columns:**
- `county_code` — FIPS county code
- `county_risk` — Mean risk across all blocks in county
- `county_eal` — Total EAL for county

#### 2. compute_county_risk_from_blocks()
**Purpose:** Verify county-level risk makes sense when aggregated

**Validation:**
```python
# Check if mean is reasonable
if county_risk > 1.0:
    # Warning: some blocks have invalid risk scores
elif county_risk < 0:
    # Error: negative risk detected
```

#### 3. compute_county_eal_from_blocks()
**Purpose:** Verify county-level EAL is sensible

**Validation:**
```python
# Check total EAL is reasonable for county size
total_eal = county_eal
blocks_in_county = len(gdf[gdf['county_code'] == county])
avg_eal_per_block = total_eal / blocks_in_county
if avg_eal_per_block < 0:
    # Warning: negative EAL detected
```

**Known Issues:**
- ~55 blocks (~27.5%) have negative EAL values due to int32 overflow in building_value_est calculation
- Bug: `building_value_est = exposure_housing * 300000` should be `float64` not `int32`
- Fix: Convert to float64: `gdf["building_value_est"] = gdf["exposure_housing"].astype("float64") * 300000`

#### 4. compare_with_fema_nri()
**Purpose:** Compare our risk scores against FEMA's National Risk Index

**Comparison:**
```python
# Aggregate to county level
our_county_risk = gdf.groupby('county_code')['risk_score'].mean()

# Load FEMA county-level risk
fema_risk = pd.read_csv('data/external/fema_nri_county.csv')

# Compute correlation
correlation = our_county_risk.corr(fema_risk['risk_index'])
```

**Output:**
- Correlation coefficient (should be 0.7+ for reasonable agreement)
- Outlier counties (large differences from FEMA)

#### 5. compute_historical_fire_overlap()
**Purpose:** Check our hazard predictions against actual fire occurrences

**Calculation:**
```python
# Load historical fire perimeters
fires = gpd.read_file('data/external/mtbs_fire_perimeters.geojson')

# For each block, calculate overlap with historical burns
for idx, block in gdf.iterrows():
    burned_blocks = fires.sjoin(gpd.GeoDataFrame([block], geometry='geometry'))
    overlap_ratio = burned_area / block_area
    gdf.loc[idx, 'fire_overlap_ratio'] = overlap_ratio
```

**Validation:**
```python
# Blocks with high overlap should have high hazard scores
high_overlap = gdf[gdf['fire_overlap_ratio'] > 0.5]
correlation = high_overlap['hazard_score'].corr(high_overlap['fire_overlap_ratio'])
# Should be 0.6+ (some positive correlation)
```

#### 6. compute_auc_fire_prediction()
**Purpose:** Measure accuracy of hazard predictions using historical fires as ground truth

**Calculation:**
```python
# Binary classification: burned (1) or not burned (0)
gdf['actually_burned'] = gdf.apply(lambda row: 1 if row['fire_overlap_ratio'] > 0, else 0)

# Use hazard_score as predictor
from sklearn.metrics import roc_auc_score
auc = roc_auc_score(gdf['actually_burned'], gdf['hazard_score'])
```

**Output:**
- AUC score (0.5 = random, 1.0 = perfect, >0.7 = good)

#### 7. compute_risk_concentration()
**Purpose:** Measure how concentrated risk is (are a few blocks very high risk?)

**Calculation:**
```python
# Calculate what fraction of total risk comes from top N% of blocks
total_risk = gdf['risk_score'].sum()
gdf_sorted = gdf.sort_values('risk_score', ascending=False)

cumsum = gdf_sorted['risk_score'].cumsum() / total_risk
concentration_80 = (cumsum <= 0.8).sum() / len(gdf)  # % of blocks for 80% of risk
```

**Output:**
- If concentration_80 = 0.2: 20% of blocks account for 80% of risk (concentrated)
- If concentration_80 = 0.5: 50% of blocks account for 80% of risk (distributed)

#### 8. compute_lorenz_curve()
**Purpose:** Calculate Gini coefficient (inequality measure for risk distribution)

**Calculation:**
```python
# Lorenz curve: cumulative risk vs. cumulative population
gdf_sorted = gdf.sort_values('risk_score')
cumsum_risk = gdf_sorted['risk_score'].cumsum() / gdf_sorted['risk_score'].sum()
cumsum_pop = range(len(gdf)) / len(gdf)

# Gini = 1 - 2 * AUC(Lorenz curve)
from sklearn.metrics import auc
gini = 1 - 2 * auc(cumsum_pop, cumsum_risk)
```

**Output:**
- Gini = 0: Risk equally distributed
- Gini = 1: All risk concentrated in one block

### 5.3 Diagnostics and Provenance Tracking

**Every block has three tracking columns:**

#### 1. diagnostics
Validation issues found for this block:
```
"null_hazard_wildfire" — Missing hazard data
"out_of_range_exposure_score" — Score >1.0 or <0
"negative_eal" — EAL is negative (likely int32 overflow)
"dummy_exposure_housing" — Using fallback data
Multiple issues separated by semicolons
```

#### 2. [column]_source
Data origin for each feature:
```
"REAL" — Fetched from API
"DUMMY" — Generated fallback
"COMPUTED" — Derived from other features
```

#### 3. [column]_provenance
Detailed explanation:
```
"Census API 2020 PL P1_001N" — Direct API result
"API failed; generated random [0, 100000]" — Fallback reason
"Computed from hazard_score weights" — Derivation
```

### 5.4 Troubleshooting Issues

#### Issue: Negative EAL Values in Output
**Symptom:** EAL column contains negative values for some blocks
**Root Cause:** Integer overflow in building_value_est calculation
```python
# WRONG (int32):
building_value_est = exposure_housing * 300000
# When exposure_housing > 7155: overflows to negative

# CORRECT (float64):
building_value_est = exposure_housing.astype("float64") * 300000
```
**Fix Location:** `src/features/build_features.py` line 132
**Impact:** ~55 blocks (~27.5%) affected in typical data

#### Issue: Out-of-Range Scores (>1.0 or <0)
**Symptom:** Validation warns "out_of_range_resilience_score"
**Possible Causes:**
1. Distance normalization formula error
2. Missing min/max bounds in calculations.csv
3. Floating-point precision edge cases

**Affected Columns:**
- res_fire_station_dist
- res_hospital_dist
- hazard_forest_distance
**Status:** Under investigation

#### Issue: Null Values in Specific Columns
**Symptom:** Validation warns "null_hazard_wildfire"
**Root Cause:** API failed and no fallback generated
**Solution:**
1. Check network connection
2. Verify API credentials
3. Check data/real/ for cached files
4. Delete cache and retry: `rm data/real/*.csv`

#### Issue: Diagnostics Report Showing Many DUMMY Values
**Symptom:** diagnostics_report.csv shows most features as DUMMY
**Meaning:** APIs are failing; using fallback data
**Solution:**
1. Verify internet connectivity
2. Check for rate limiting (Census API limit ~500 calls/day)
3. Check API credentials
4. Run `python scripts/refresh_real_data.py` to force fresh downloads

### 5.5 Running Validation Manually

```python
from src.utils.validator import (
    validate_columns, validate_nulls, validate_ranges, validate_types
)
from src.validation.metrics import (
    aggregate_block_to_county,
    compute_auc_fire_prediction,
    compute_risk_concentration,
    compute_lorenz_curve
)
import geopandas as gpd

# Load output
gdf = gpd.read_file('data/processed/blocks.geojson')

# Run basic checks
print(validate_columns(gdf))      # Check all features exist
print(validate_nulls(gdf))        # Check no nulls
print(validate_ranges(gdf))       # Check 0-1 ranges
print(validate_types(gdf))        # Check data types

# Run advanced metrics
county_stats = aggregate_block_to_county(gdf)
auc = compute_auc_fire_prediction(gdf)
concentration = compute_risk_concentration(gdf)
gini = compute_lorenz_curve(gdf)

print(f"AUC Score: {auc:.3f}")
print(f"Concentration (80%): {concentration:.1%}")
print(f"Gini Coefficient: {gini:.3f}")
```

---

## 6. Visualization, Frontend, and Reference

### 6.1 Color Palette (7-Layer Semantic Colors)

The frontend should use a distinct, semantically meaningful color for each major layer so users can easily distinguish between wildfire threat, human consequence, and recovery capacity.

| Layer | Color Name | Hex | Rationale |
|-------|-----------|-----|-----------|
| Risk | Crimson Red | `#D73027` | Primary danger signal; highest visual weight |
| Hazard | Burnt Orange | `#F46D43` | Fire, heat, ignition intuition |
| Exposure | Golden Orange | `#FDAE61` | Population and asset presence; warmth |
| Vulnerability | Purple | `#8073AC` | Social fragility; distinct from hazard/exposure |
| Resilience | Teal Green | `#1A9850` | Response and recovery capacity; positive (green) |
| Expected Annual Loss (EAL) | Deep Blue | `#4575B4` | Economic/financial interpretation |
| Diagnostics / Missing | Neutral Gray | `#9E9E9E` | Non-data or warning state; neutral |

### 6.2 Suggested Choropleth Ramps

Use these three-color ramps for visualizing metrics from low to high:

| Layer | Low (0) | Mid (0.5) | High (1.0) |
|-------|---------|-----------|-----------|
| Risk | `#FEE0D2` | `#FC9272` | `#D73027` |
| Hazard | `#FEE8C8` | `#FDBB84` | `#F46D43` |
| Exposure | `#FFF7BC` | `#FEC44F` | `#FDAE61` |
| Vulnerability | `#EFEDF5` | `#BCBDDC` | `#8073AC` |
| Resilience | `#E5F5E0` | `#74C476` | `#1A9850` |
| EAL | `#DEEBF7` | `#9ECAE1` | `#4575B4` |

### 6.3 Visualization Guidelines

**Color Usage:**
- Keep `risk` visually strongest using red (primary layer)
- Keep `hazard` orange rather than red so it's distinguishable from overall `risk`
- Keep `resilience` green because higher resilience reduces overall risk
- Use the same base hue for legends, layer buttons, tooltips, and map ramps

**Interactive Features:**
- **Layer toggle:** Allow users to switch between Risk, Hazard, Exposure, Vulnerability, Resilience, EAL
- **Hover tooltip:** Show block details (values, data sources, diagnostics)
- **Debug mode:** Option to show provenance and diagnostics
- **Zoom levels:** Aggregate to county at low zoom, show blocks at high zoom
- **Export:** Download filtered blocks as GeoJSON or CSV

### 6.4 Data Dictionary and Economic Model

**Economic Model:**

```
building_value_est = exposure_housing × $300,000 (avg home value)
risk_score = hazard × exposure × vulnerability × (1 - resilience)
eal = risk_score × building_value_est
```

**Example for a Block:**
```
Exposure housing: 100 houses
Building value: 100 × $300,000 = $30,000,000

Risk score: 0.15
EAL = 0.15 × $30,000,000 = $4,500,000
Expected annual damage for this block: $4.5 million
```

**Data Dictionary:**

All fields are documented in `calculations.csv` with:
- Feature name and description
- Data source and collection method
- Expected range and units
- Validation rules
- Update frequency

To view all fields:
```bash
cat calculations.csv | column -t -s, | less
```

### 6.5 How-To Guides

#### How to Add a New Feature

1. **Define in calculations.csv:**
   - Add new row with feature name, data source, formula
   - Specify min/max bounds for validation
   - Specify weight if part of composite score

2. **Implement Python function:**
   - Create function in appropriate module (`src/features/hazard.py`, etc.)
   - Load data from external source or API
   - Handle errors with fallback generation
   - Track provenance (REAL vs. DUMMY)

3. **Update feature pipeline:**
   - Add function call to `src/pipeline/feature_pipeline.py`
   - Ensure proper sequencing (dependencies first)

4. **Add tests:**
   - Create test file in `tests/test_features.py`
   - Test normal case, edge cases, missing data
   - Test fallback generation

5. **Run pipeline and validate:**
   - Execute full pipeline: `python -m src.pipeline.run_pipeline`
   - Check diagnostics for errors
   - Verify new column in output GeoJSON

#### How to Refresh Data

1. **Refresh Census/ACS data:**
   ```bash
   python scripts/refresh_real_data.py
   ```

2. **Download environmental datasets:**
   ```bash
   python scripts/download_environmental_data.py
   ```

3. **Process geospatial data:**
   ```bash
   python scripts/process_nlcd_zonal_stats.py
   python scripts/process_hifld_nearest.py
   python scripts/process_osm_road_length.py
   ```

4. **Rerun pipeline:**
   ```bash
   python -m src.pipeline.run_pipeline
   ```

5. **Check diagnostics:**
   - Review `data/real/diagnostics_report.csv`
   - Check logs for warnings/errors

#### How to Debug Diagnostics

1. **Run pipeline and generate output**
2. **Check diagnostics column:**
   ```python
   import geopandas as gpd
   gdf = gpd.read_file('data/processed/blocks.geojson')
   print(gdf[gdf['diagnostics'].notna()][['GEOID', 'diagnostics']])
   ```

3. **Review diagnostics report:**
   ```bash
   cat data/real/diagnostics_report.csv | head -20
   ```

4. **Check specific column:**
   ```python
   # Find out-of-range values
   print(gdf[gdf['risk_score'] > 1.0][['GEOID', 'risk_score']])
   ```

5. **Check provenance:**
   ```python
   # See which columns have dummy data
   print(gdf[[col for col in gdf.columns if 'source' in col]])
   ```

### 6.6 API Reference

For auto-generated API documentation:
```bash
cd docs
make html
# Open docs/_build/html/index.html in browser
```

**Main Modules:**
- `src.pipeline.run_pipeline` — Main entry point
- `src.pipeline.steps` — Stage implementations
- `src.features.*` — Feature computation
- `src.models.risk_model` — Risk calculations
- `src.utils.validator` — Validation functions
- `src.validation.metrics` — Advanced metrics
- `src.utils.real_data` — All data fetching functions

### 6.7 Data Flow Diagram

See `calculations_diagram_dev.mmd` for comprehensive visual flowchart.

**7 Pipeline Stages:**
1. 🔍 **Data Sources** — 9 external providers
2. 📥 **Ingestion** — Fetch functions
3. 🧹 **Preprocessing** — Standardization
4. ⚙️ **Feature Engineering** — 17 features in 4 components
5. 🎲 **Risk Model** — Final calculations
6. ✅ **Validation** — 8 quality checks
7. 📤 **Export** — Output formats

---

## Additional Resources

### Files to Know About

- **`calculations.csv`** — Canonical feature specification (28 columns, 27 rows)
- **`calculations_diagram_dev.mmd`** — Visual flowchart (Mermaid format)
- **`data/processed/blocks.geojson`** — Main output with all calculations
- **`data/real/diagnostics_report.csv`** — Validation issues summary
- **`src/pipeline/run_pipeline.py`** — Entry point
- **`requirements.txt`** — Python dependencies

### Quick Command Reference

```bash
# Install and setup
pip install -r requirements.txt

# Refresh data
python scripts/refresh_real_data.py

# Run pipeline
python -m src.pipeline.run_pipeline

# Serve frontend
python -m http.server 8000

# Run tests
pytest tests/ --maxfail=10 --disable-warnings -q

# Generate documentation
cd docs && make html

# View output
cat data/processed/blocks.geojson | jq '.features[0]'
```

### Support and Issues

For bug reports and questions:
1. Check `data/real/diagnostics_report.csv` for validation issues
2. Review logs for error messages
3. Consult this documentation for common issues
4. Check GitHub issues for known problems

---

**Last Updated:** 2024  
**Version:** 1.0  
**Status:** Complete Documentation
