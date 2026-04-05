# Wildfire Risk Mapping Pipeline: A Step-by-Step Explanation for Novices

## Table of Contents
1. [Overview](#overview)
2. [Entry Point: Starting the Program](#entry-point-starting-the-program)
3. [Data Sources: Where Information Comes From](#data-sources-where-information-comes-from)
4. [Data Flow Through the Pipeline](#data-flow-through-the-pipeline)
5. [Understanding calculations.csv](#understanding-calculationscsv)
6. [Validation: Checking That Everything Makes Sense](#validation-checking-that-everything-makes-sense)
7. [What Happens When Data Can't Be Retrieved](#what-happens-when-data-cant-be-retrieved)

---

## Overview

This wildfire risk mapping system predicts how much wildfire danger each geographic block (a small neighborhood-sized area) faces. It combines information about:
- **Hazard** (how likely is a wildfire to start or spread here?)
- **Exposure** (how many people and buildings are in the way?)
- **Vulnerability** (which people are most at-risk if a wildfire happens?)
- **Resilience** (what resources exist to help people escape or recover?)

The final output is **Risk Score** and **Expected Annual Loss (EAL)** — a number representing how much damage we expect in a typical year.

---

## Entry Point: Starting the Program

### Which Python File Runs First?

**File:** `src/pipeline/run_pipeline.py`

**How to start it:**
```bash
python -m src.pipeline.run_pipeline
```

**What happens when you run it:**

The program calls the `run()` function which orchestrates a 5-stage pipeline:

```
run_pipeline.py → run() function
    ↓
    [Stage 1] step_ingestion()
    [Stage 2] step_preprocessing()
    [Stage 3] run_feature_pipeline() + step_features()
    [Stage 4] step_model()
    [Stage 5] Export & Validation
```

**Entry Point Code Flow:**
```python
def run():
    print("Starting pipeline")
    
    # Stage 1: Load raw data (blocks and attributes)
    gdf = step_ingestion()
    
    # Stage 2: Prepare data (standardize coordinates, geographic clipping)
    gdf = step_preprocessing(gdf)
    
    # Stage 3: Calculate all features (hazard, exposure, vulnerability, resilience, risk)
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

---

## Data Sources: Where Information Comes From

The program retrieves information from **9 external sources**. Let's explore each one:

### 1. **WHP (Wildland-Urban Interface Hazard Potential) Data**

**What it measures:** Wildfire probability and intensity potential

**Source URL:** `https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains `fetch_whp_data()` function
- `src/features/hazard.py` — Processes the data into `hazard_wildfire` feature

**Where data is stored:**
- **Downloaded/cached:** `data/real/whp_butte.csv` (if downloaded and stored locally)
- **Processed:** Column `hazard_wildfire` in output GeoJSON

**How calculations.csv directs this:**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | USFS WHP | Identifies the data provider |
| source_url | https://www.fs.usda.gov/... | Where to find the data |
| api_endpoint | (empty) | Not an API, it's a direct file download |
| api_params | (empty) | No parameters needed |
| calculation_formula | `mean(WHP_pixels_in_block)` | Calculate average wildfire risk for each block |

**Step-by-step process:**
1. Program downloads WHP raster data (a grid-based map where each pixel has a wildfire risk value)
2. Overlays the block boundaries on top of the raster
3. Calculates the average risk value of all pixels within each block
4. Stores result in `hazard_wildfire` column (range: 0-1, where 0=no risk, 1=highest risk)

---

### 2. **NLCD (National Land Cover Database) Data**

**What it measures:** Type of land cover (forest, shrub, urban, water, etc.)

**Source URL:** `https://www.mrlc.gov/data`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains `fetch_nlcd_data()` function
- `src/features/hazard.py` — Processes into `hazard_vegetation` and `hazard_forest_distance`

**Where data is stored:**
- **Downloaded/cached:** `data/real/nlcd_butte.tif` (raster file)
- **Processed:** 
  - Column `hazard_vegetation` (fuel density)
  - Column `hazard_forest_distance` (distance to forests)

**How calculations.csv directs this:**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | NLCD | US Geological Survey National Land Cover Database |
| source_url | https://www.mrlc.gov/data | Data download portal |
| api_endpoint | (empty) | Download directly, not via API |
| transform_steps | "classify forest/shrub; count pixels" | Algorithm: Count forested pixels, divide by total |
| calculation_formula | `forest_pixels / total_pixels` | Creates hazard_vegetation (0-1) |

**Step-by-step process:**
1. Download NLCD raster (each pixel labeled with land type)
2. Classify pixels as "forest" or "shrub" (fire-prone) vs. "urban" or "water" (fire-resistant)
3. For each block:
   - Count forest/shrub pixels → `hazard_vegetation`
   - Find nearest forest edge → `hazard_forest_distance` (inverted: closer forests = higher hazard)

---

### 3. **Census Population Data**

**What it measures:** How many people live in each block

**Source URL:** `https://api.census.gov/data/2020/dec/pl`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains `fetch_census_population()` and `compute_exposure_population_real()` functions
- `src/features/exposure.py` — Creates `exposure_population` feature

**Where data is stored:**
- **Downloaded/cached:** `data/real/census_population.csv` (CSV with GEOID → population)
- **Live API:** Fetches from Census API if local file doesn't exist
- **Processed:** Column `exposure_population` in output

**How calculations.csv directs this:**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | Census PL (Public Law) | 2020 Census Population |
| api_endpoint | `/data/2020/dec/pl` | Census API endpoint path |
| api_params | `get=P1_001N&for=block:*&in=state:06 county:007` | Fetch total population (P1_001N) for all blocks in CA county 007 (Butte) |
| join_keys | GEOID | Join using Census geographic ID |
| calculation_formula | `P1_001N` | Direct value (no transformation) |

**Step-by-step process:**
1. Check if local file `data/real/census_population.csv` exists
2. If not, construct Census API request:
   - `get=P1_001N` → Request total population variable
   - `for=block:*` → For all census blocks
   - `in=state:06 county:007` → In Butte County, California
3. Parse response into dictionary: `GEOID → population`
4. Save to `data/real/census_population.csv` for future use
5. Join to blocks using GEOID
6. Store in `exposure_population` column

---

### 4. **Census Housing Units Data**

**What it measures:** How many houses and apartments are in each block

**Source URL:** `https://api.census.gov/data/2020/dec/pl`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains `fetch_census_housing()` and `compute_exposure_housing_real()` functions
- `src/features/exposure.py` — Creates `exposure_housing` feature

**Where data is stored:**
- **Downloaded/cached:** `data/real/census_housing.csv` (CSV with GEOID → housing units)
- **Live API:** Fetches from Census API if local file doesn't exist
- **Processed:** Column `exposure_housing` in output

**How calculations.csv directs this:**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | Census H1 (Housing) | 2020 Census Housing Units |
| api_endpoint | `/data/2020/dec/pl` | Census API endpoint path |
| api_params | `get=H1_001N&for=block:*&in=state:06 county:007` | Fetch total housing units (H1_001N) for all blocks |
| join_keys | GEOID | Join using Census geographic ID |
| calculation_formula | `H1_001N` | Direct value (no transformation) |

**Step-by-step process:** (Similar to population, but requests housing variable H1_001N instead)

---

### 5. **ACS (American Community Survey) Data**

**What it measures:** Socioeconomic characteristics: poverty rate, elderly population percentage, vehicle ownership

**Source URL:** `https://api.census.gov/data/2021/acs/acs5`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains multiple functions:
  - `fetch_acs_blockgroup()` — Generic ACS fetcher
  - `compute_vuln_poverty_real()` → poverty
  - `compute_vuln_elderly_real()` → elderly
  - `compute_vuln_vehicle_access_real()` → vehicle access
  - `compute_exposure_building_value_real()` → building value
- `src/features/vulnerability.py` — Processes vulnerability features
- `src/features/exposure.py` — Processes building value

**Where data is stored:**
- **Downloaded/cached:** Multiple CSV files in `data/real/`:
  - `acs_poverty.csv`
  - `acs_elderly.csv`
  - `acs_vehicle.csv`
  - `acs_building_value.csv`
- **Processed:** Columns `vuln_poverty`, `vuln_elderly`, `vuln_vehicle_access`, `exposure_building_value`

**How calculations.csv directs this (Example: Poverty):**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | ACS | American Community Survey |
| api_endpoint | `/data/2021/acs/acs5` | 2021 5-year ACS |
| api_params | `get=B17001_002E,B17001_001E&for=tract:*` | B17001_002E = persons in poverty, B17001_001E = total persons |
| transform_steps | "compute poverty rate; map tract to block group; normalize" | Calculate ratio and convert to 0-1 scale |
| calculation_formula | `B17001_002E / B17001_001E` | Poverty rate |

**Step-by-step process for each ACS feature:**
1. Fetch tract-level or block group-level data via API
2. Calculate the metric (e.g., poverty percentage, elderly percentage)
3. Map from tract/block group down to individual blocks (spatial join)
4. Normalize to 0-1 scale using min-max normalization
5. Store in appropriate column

---

### 6. **HIFLD (Homeland Infrastructure Foundation-Level Data)**

**What it measures:** Locations of fire stations and hospitals

**Source URL:** `https://hifld-geoplatform.opendata.arcgis.com`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains:
  - `fetch_hifld_data()` → retrieves fire station and hospital locations
- `src/features/resilience.py` — Processes into:
  - `res_fire_station_dist` (distance to nearest fire station)
  - `res_hospital_dist` (distance to nearest hospital)

**Where data is stored:**
- **Downloaded/cached:** `data/real/fire_stations.csv` and `data/real/hospitals.csv`
- **Processed:** 
  - Column `res_fire_station_dist` (closer station = higher resilience = higher score)
  - Column `res_hospital_dist` (closer hospital = higher resilience = higher score)

**How calculations.csv directs this:**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | HIFLD | Emergency response infrastructure |
| source_url | https://hifld-geoplatform.opendata.arcgis.com | ArcGIS Open Data portal |
| transform_steps | "nearest distance; invert" | Calculate distance to nearest facility, then invert (1/(1+distance)) |
| calculation_formula | `1/(1+distance_km)` | Inverted distance: closer = higher score (0-1) |

**Step-by-step process:**
1. Download fire station point locations (lat/lon)
2. Download hospital point locations (lat/lon)
3. For each block's geographic center (centroid):
   - Calculate distance to nearest fire station → store distance
   - Apply inversion formula: `1 / (1 + distance_km)` → normalize to 0-1
   - Store in `res_fire_station_dist`
4. Repeat for hospitals → `res_hospital_dist`

---

### 7. **OpenStreetMap (OSM) Roads**

**What it measures:** Road network and connectivity

**Source URL:** `https://overpass-api.de/api/interpreter`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains `fetch_osm_roads()` function
- `src/features/resilience.py` — Processes into `res_road_access`

**Where data is stored:**
- **Downloaded/cached:** `data/real/osm_roads_butte.geojson`
- **Processed:** Column `res_road_access` (road connectivity as evacuation indicator)

**How calculations.csv directs this:**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | OSM | OpenStreetMap volunteer-maintained data |
| api_endpoint | `interpreter` | Overpass API endpoint |
| api_params | `[out:json];way["highway"](bbox);out;` | Query for all ways (roads) tagged as 'highway' in bounding box |
| transform_steps | "sum length / area" | Total road kilometers per block / block area = road density |
| calculation_formula | `road_length / area` | Road density as connectivity measure |

**Step-by-step process:**
1. Query Overpass API for all roads in Butte County bounding box
2. Filter for highways (roads where traffic is possible)
3. For each block:
   - Overlay roads on block geometry
   - Sum total length of all roads within block
   - Divide by block area → road density (km of road per km² of block)
   - Normalize to 0-1 scale
   - Store in `res_road_access` (higher density = better evacuation = higher resilience)

---

### 8. **MTBS (Monitoring Trends in Burn Severity) Dataset**

**What it measures:** Historical fire perimeters and burn severity

**Source URL:** `https://mtbs.gov/`

**Relevant Python Files:**
- `src/utils/real_data.py` — Contains `fetch_fire_perimeters()` function
- `src/validation/metrics.py` — Used in `compute_historical_fire_overlap()` validation function

**Where data is stored:**
- **Downloaded/cached:** `data/real/fire_perimeters_butte.geojson`
- **Used in:** Validation metric to check prediction accuracy

**How calculations.csv directs this:**
| Column | Value | Meaning |
|--------|-------|---------|
| data_source | MTBS | USGS fire perimeter database |
| transform_steps | "overlay; top decile" | Overlay historical fires; check if predicted high-risk blocks overlap with burned areas |
| calculation_formula | `burned_in_top_decile / total_burned` | Fraction of historically burned area predicted by model |

**Purpose:** Not used for main risk calculation, but **for validation** — we check if our model's highest-risk blocks align with where fires actually occurred in the past.

---

### 9. **FEMA NRI (National Risk Index) Dataset**

**What it measures:** FEMA's own comprehensive hazard and risk assessment

**Source URL:** `https://hazards.fema.gov/nri/`

**Relevant Python Files:**
- `src/validation/metrics.py` — Contains `compare_with_fema_nri()` function
- **Not** used for main calculation, only for validation

**Where data is stored:**
- **Downloaded/cached:** `data/external/fema_nri_county.csv`
- **Used in:** Validation metric

**Purpose:** **Validation only** — We compare our county-level risk calculations with FEMA's published risk index to verify our model produces reasonable results.

---

## Data Flow Through the Pipeline

### Stage 1: Ingestion
**What happens:** Raw block geometry and attributes are loaded

**Python File:** `src/ingestion/load_real_blocks.py` → `load_real_blocks()`

**Input:** GIS shapefiles or GeoJSON with Butte County census blocks

**Output:** GeoDataFrame with columns:
- `geometry` (polygon shape of each block)
- `GEOID` (unique block identifier)
- `county` (Butte)

### Stage 2: Preprocessing
**What happens:** Standardize coordinates, ensure all blocks are in same coordinate system, clip to county boundary

**Python File:** `src/preprocessing/preprocess_blocks.py`

**Key operations:**
1. Standardize Coordinate Reference System (CRS) to EPSG:3857 (Web Mercator)
2. Ensure all blocks are within Butte County boundary
3. Generate block IDs and compute block centroids (center point of each polygon)
4. Remove any duplicate or invalid geometries

**Output:** Cleaned GeoDataFrame ready for feature engineering

### Stage 3: Feature Engineering
**What happens:** Calculate all 17 features by fetching and processing external data

**Python File:** `src/pipeline/feature_pipeline.py` → runs all feature computation

**The feature computation happens in this order:**
1. **Hazard features** (3 features)
   - `hazard_wildfire` — from WHP data
   - `hazard_vegetation` — from NLCD data
   - `hazard_forest_distance` — from NLCD data
   - `hazard_score` — weighted average of above 3

2. **Exposure features** (3 features)
   - `exposure_population` — from Census API
   - `exposure_housing` — from Census API
   - `exposure_building_value` — from ACS API
   - `exposure_score` — weighted average of above 3

3. **Vulnerability features** (3 features)
   - `vuln_poverty` — from ACS poverty data
   - `vuln_elderly` — from ACS elderly data
   - `vuln_vehicle_access` — from ACS vehicle ownership data
   - `vulnerability_score` — weighted average of above 3

4. **Resilience features** (3 features)
   - `res_fire_station_dist` — from HIFLD fire station locations
   - `res_hospital_dist` — from HIFLD hospital locations
   - `res_road_access` — from OSM road network
   - `resilience_score` — weighted average of above 3

### Stage 4: Risk Modeling
**What happens:** Calculate final risk metrics

**Python File:** `src/models/risk_model.py`

**Calculations:**
- `risk_score = hazard_score × exposure_score × vulnerability_score × (1 - resilience_score)`
  - Interpretation: Multiply hazard and exposure and vulnerability, but subtract resilience's effect
  - Range: 0 to 1 (0 = no risk, 1 = extreme risk)

- `eal = risk_score × exposure_building_value`
  - Expected Annual Loss in dollars
  - Interpretation: What economic damage we expect in a typical year
  - Example: If risk_score=0.1 and building_value=$10M, then eal=$1M annually

- `eal_norm = (eal - min_eal) / (max_eal - min_eal)`
  - Normalized EAL to 0-1 scale for visualization

### Stage 5: Validation & Export
**What happens:** Validate data quality, compute validation metrics, export results

**Python Files:**
- `src/validation/metrics.py` — Compute validation metrics
- `src/utils/validator.py` — Check ranges, nulls, types
- Export functions → write GeoJSON

**Validation steps:**
1. Check all required columns exist
2. Check for null values
3. Check normalized fields are in [0,1]
4. Aggregate to county level
5. Compare with FEMA NRI
6. Compute fire overlap ratio
7. Compute AUC (how well does our model match historical burns?)
8. Compute risk concentration (are high risks concentrated or spread out?)

**Final Output:**
- `data/processed/blocks.geojson` — All 200 Butte County blocks with all calculated fields
- Can be loaded into web map for visualization

---

## Understanding calculations.csv

This is the **single source of truth** for the entire project. Every row defines one variable, and the columns tell the data scientist exactly how that variable should be retrieved, transformed, and validated.

⚠️ **IMPORTANT ARCHITECTURAL NOTE:**
`calculations.csv` is primarily a **SPECIFICATION DOCUMENT**, not a configuration file that drives behavior. Only **2 columns are actually read dynamically** by the Python code at runtime:
- `weight` and `weight_group` — Used to compute composite scores dynamically
- `min` and `max` — Used to generate fallback dummy data bounds when APIs fail

**All other columns** (data_source, source_url, api_endpoint, api_params, join_keys, transform_steps, calculation_formula, dependencies) are **static documentation** that describe the implementation in code. These are NOT read by the program—they are hardcoded in Python functions.

**Think of it this way:**
- calculations.csv = **"What should the system do? How should each feature be computed?"** (specification)
- Python code = **"How are we actually doing it?"** (implementation)
- For most columns, they must stay in sync manually

This is different from a fully "schema-driven" system where all parameters are read from a config file.

### All 8 Column Categories Explained

#### **1. data_source** → Which system provides the raw data?
Examples:
- `USFS WHP` — Wildfire Hazard Potential from USFS
- `Census PL` — 2020 Census Population data
- `ACS` — American Community Survey (economic data)
- `HIFLD` — Emergency infrastructure locations
- `OSM` — OpenStreetMap roads
- `Derived` — Calculated from other features (e.g., hazard_score calculated from 3 hazard features)

#### **2. source_url** → Where can a human find or download this data?
Full URL to the data provider's website or API:
- `https://www.fs.usda.gov/rds/archive/products/RDS-2015-0047` — Direct link to WHP data
- `https://api.census.gov/data/2020/dec/pl` — Census API base URL
- `https://api.census.gov/data/2021/acs/acs5` — ACS API base URL

#### **3. api_endpoint** → Which specific part of the API to call?
For Census and ACS (APIs with multiple endpoints):
- `/data/2020/dec/pl` — Census API 2020 endpoint
- `/data/2021/acs/acs5` — ACS 2021 5-year endpoint
- `interpreter` — Overpass (OSM) API interpreter endpoint

For non-API sources (WHP, NLCD), this is empty.

#### **4. api_params** → What specific variables and geography to request?
Examples:
```
get=P1_001N&for=block:*&in=state:06 county:007
  ↓
  Request total population (P1_001N)
  for all blocks (for=block:*)
  in state 06, county 007 (Butte County, CA)
```

Another example:
```
get=B17001_002E,B17001_001E&for=tract:*
  ↓
  Request persons in poverty (B17001_002E)
  and total persons (B17001_001E)
  for all tracts
```

#### **5. dependencies** → Which other features must exist first?
Examples:
- `hazard_wildfire,hazard_vegetation,hazard_forest_distance` → hazard_score depends on these 3
- `eal` depends on `risk_score` and `exposure_building_value` being calculated first

#### **6. join_keys** → How do we match data to blocks?
How we connect external data to our blocks:
- `GEOID` → Census geographic ID (matches block ID)
- `block_id` → Our block identifier
- `TRACT (derived from GEOID)` → Map tract-level data to blocks by extracting tract code from GEOID
- `geometry` → Spatial join (overlay on map)

#### **7. transform_steps** → What operations must the code perform?
English description of the algorithm:
- `"clip raster to blocks; zonal stats mean"` → Overlay raster on blocks, calculate average
- `"nearest distance; invert"` → Calculate distance to nearest facility, apply `1/(1+distance)` formula
- `"classify forest/shrub; count pixels"` → Classify pixels by type, count forest pixels
- `"compute poverty rate; map tract to block group; normalize"` → Calculate ratio, apply spatial join, scale to 0-1

#### **8. calculation_formula** → The exact mathematical formula

For **direct measurements** (copied from source):
```
P1_001N  → Population (Census variable P1_001N, used directly)
H1_001N  → Housing units (Census variable H1_001N, used directly)
```

For **derived calculations** (computed from other data):
```
mean(WHP_pixels_in_block)  → Average of raster pixels in block
forest_pixels / total_pixels  → Fuel density percentage
B17001_002E / B17001_001E  → Poverty rate (poverty persons / total persons)
1 / (1 + distance_km)  → Inverted distance (closer = higher score)
road_length / area  → Road density (km of road per km² of block)
```

For **composite scores** (weighted average of components):
```
Σ(weight_i * norm(feature_i)) for features with weight_group='hazard_score'
  ↓
  Example: hazard_score = 0.333*norm(hazard_wildfire) 
                         + 0.333*norm(hazard_vegetation)
                         + 0.333*norm(hazard_forest_distance)
```

For **risk calculation** (multiplicative formula):
```
H * E * V * (1 - R)
  ↓
  risk_score = hazard_score × exposure_score × vulnerability_score × (1 - resilience_score)
```

For **economic loss** (risk applied to assets):
```
risk_score * exposure_building_value
  ↓
  eal = risk_score × total_building_value_in_block
```

### How the Code Uses calculations.csv

**IMPORTANT ARCHITECTURAL INSIGHT:**
Only **2 out of 28 columns** are actually **read dynamically at runtime**:
- `weight` + `weight_group` — Used to compute composite scores
- `min` + `max` — Used to generate fallback dummy data bounds

**Everything else is static documentation** hardcoded in Python code. See `CALCULATIONS_CSV_ARCHITECTURE.md` for detailed explanation of this design pattern.

**Step 1:** Program reads weights at feature engineering time
```python
# In build_features.py
weights = _load_component_weights_from_calculations()
# Returns: {"hazard_score": {"hazard_wildfire_norm": 0.333, ...}, ...}
```

**Step 2:** Program reads min/max when generating fallback data
```python
# In real_data.py
min_val, max_val = get_limits("exposure_population")
# Returns: bounds for generating dummy integers if API fails
```

**Step 3:** Program uses hardcoded API URLs (NOT read from CSV)
```python
# NOT from CSV - hardcoded
CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"
params = {
    "get": "P1_001N,GEOID",  # Hardcoded, not from api_params column
    "for": "block:*",
    "in": f"state:{STATE_CODE} county:{COUNTY_CODE}"
}
```

**Step 4:** Program uses hardcoded computation formulas (NOT read from CSV)
```python
# NOT from CSV - hardcoded as Python logic
poverty_rate = persons_in_poverty / total_persons  # calculation_formula is documented but hardcoded
res_score = 1 / (1 + distance_km)  # calculation_formula documented but hardcoded
```

**Step 5:** Program validates using hardcoded rules (NOT read from CSV)
```python
# NOT from CSV - validation rules hardcoded
if hazard_score < 0 or hazard_score > 1:
    logger.warning(f"Field out of range")
```

### Mapping: Which columns are used where?

| Column | Used Dynamically? | Where | Files |
|--------|---|---|---|
| `weight_group` | ✅ YES | Composite score computation | build_features.py:44 |
| `weight` | ✅ YES | Composite score computation | build_features.py:45 |
| `min` | ✅ YES | Fallback data generation | real_data.py:42 |
| `max` | ✅ YES | Fallback data generation | real_data.py:46 |
| `data_source` | ❌ NO | Static documentation | (reference only) |
| `source_url` | ❌ NO | Hardcoded in code | real_data.py (URLS hardcoded) |
| `api_endpoint` | ❌ NO | Hardcoded in code | real_data.py (endpoints hardcoded) |
| `api_params` | ❌ NO | Hardcoded in code | real_data.py (params hardcoded) |
| `dependencies` | ❌ NO | Hardcoded in pipeline order | feature_pipeline.py (order hardcoded) |
| `join_keys` | ❌ NO | Hardcoded in functions | features/*.py (joins hardcoded) |
| `transform_steps` | ❌ NO | Static documentation | (reference only) |
| `calculation_formula` | ❌ NO | Hardcoded as logic | Various (formulas hardcoded) |

### Why This Design?

This is a **Specification-Driven Architecture** (not Configuration-Driven). See `CALCULATIONS_CSV_ARCHITECTURE.md` for detailed pros/cons and recommendations.

````````
