# Documentation Summary: explain.md and Enhanced calculations_diagram_dev.mmd

## 📄 New Documentation Files Created

### 1. **explain.md** (Root Directory)
**Purpose:** Comprehensive step-by-step explanation for novices who don't have Python or GIS background

**Contents (7 Main Sections):**

#### Section 1: Overview
- What the system does (combines 4 risk components into risk score + EAL)

#### Section 2: Entry Point 
- **Answer:** `src/pipeline/run_pipeline.py` runs first
- Entry point function: `run()` 
- Command to execute: `python -m src.pipeline.run_pipeline`
- 5-stage pipeline orchestration shown with diagram

#### Section 3: Data Sources (9 External Providers)
**Each source documented with:**
- What it measures
- Source URL
- Relevant Python files that fetch it
- Where data is stored (local cache location)
- How calculations.csv directs its usage
- Step-by-step process explanation
- Fallback behavior when unavailable

**9 Sources covered:**
1. ✅ WHP (Wildland-Urban Interface) — Wildfire probability
2. ✅ NLCD (Land Cover) — Vegetation/fuel density
3. ✅ Census Population API — People count
4. ✅ Census Housing API — Building count
5. ✅ ACS (American Community Survey) — Socioeconomic data (poverty, elderly, vehicles)
6. ✅ HIFLD — Fire stations & hospitals
7. ✅ OSM (OpenStreetMap) — Road network
8. ✅ MTBS — Historical fire perimeters (validation only)
9. ✅ FEMA NRI — Risk index (validation comparison only)

#### Section 4: Data Flow Through Pipeline
- 5 stages explained with file locations
- Ingestion → Preprocessing → Feature Engineering → Risk Modeling → Validation/Export
- What each stage inputs, processes, outputs

#### Section 5: Understanding calculations.csv
**All 8 column categories explained with examples:**
- `data_source` → which system provides raw data
- `source_url` → where humans can find the data
- `api_endpoint` → which API endpoint to call
- `api_params` → specific query parameters
- `dependencies` → which features must exist first
- `join_keys` → how to spatially match data to blocks
- `transform_steps` → what operations to perform
- `calculation_formula` → mathematical formula or code logic

**Detailed table showing:**
- How code uses calculations.csv at each step
- Which Python function reads each column
- When each column is applied

#### Section 6: Validation
**8 validation functions explained:**
- `validate_columns()` — check all 17 features exist
- `validate_nulls()` — check for missing values
- `validate_ranges()` — check normalized fields are 0-1
- `validate_types()` — check data types are correct
- `aggregate_block_to_county()` — validate geographic aggregation
- `compute_county_risk_from_blocks()` — validate county-level scores
- `compute_county_eal_from_blocks()` — validate county totals
- `compare_with_fema_nri()` — compare with FEMA's index
- `compute_historical_fire_overlap()` — check against historical burns
- `compute_auc_fire_prediction()` — measure prediction accuracy
- `compute_risk_concentration()` — measure risk distribution
- `compute_lorenz_curve()` — compute Gini coefficient

#### Section 7: What Happens When Data Can't Be Retrieved
**For each data source, explains:**
- Normal retrieval flow
- Where data is cached locally
- Fallback mechanism when API fails
- How to tell if you're using fake data
- How to force fresh data (delete cache, re-run)

---

### 2. **calculations_diagram_dev.mmd** (Enhanced)
**Purpose:** Visual flowchart with detailed technical annotations

**Enhancements Made:**

#### Before vs After
- **Before:** Basic flowchart showing 7 stages with simple node names
- **After:** Comprehensive technical diagram with:
  - 🔍 **Data Sources Layer** — All 9 sources with URLs, storage locations, fallback behaviors
  - 📥 **Ingestion Layer** — 9 fetch functions with their outputs and computation types
  - 🧹 **Preprocessing Layer** — 4 standardization steps (CRS, clipping, IDs, centroids)
  - ⚙️ **Feature Engineering Layer** — All 17 features organized by component
    - 🔥 Hazard (3+1 features with formulas and weights)
    - 👥 Exposure (3+1 features with data types)
    - 😟 Vulnerability (3+1 features with ratios)
    - 🛡️ Resilience (3+1 features with distance logic)
  - 🎲 **Risk Model Layer** — Final calculations (risk score, EAL, normalized EAL)
  - ✅ **Validation Layer** — All 8 validation metrics
  - 📤 **Export Layer** — Output formats and locations

#### Technical Details Now Visible in Diagram
Each node includes:
- **What it calculates** (e.g., `compute_hazard_wildfire`)
- **Data source** (e.g., "WHP raster", "Census API")
- **Formula/transformation** (e.g., `mean pixel value`, `1/(1+distance_km)`)
- **Data type** (Integer, Float, Normalized 0-1)
- **Python file** (e.g., `src/features/hazard.py`)
- **URL** (for data source identification)
- **Storage location** (e.g., `data/real/census_population.csv`)
- **Fallback behavior** (e.g., "Random 0-1", "Random integers")

#### Visual Organization
- **Color-coded subgraphs** for each pipeline stage
- **Emoji icons** for quick visual reference
- **Arrows showing data flow** between stages
- **Hierarchical grouping** (e.g., Hazard features feeding into Hazard Score)
- **Self-contained documentation** — no need to reference separate files to understand it

---

## 🎯 How to Use These Resources

### For **Novices** (non-technical audience):
1. Start with `explain.md` **Section 1-2** (Overview + Entry Point)
2. Read **Section 3** to understand where data comes from
3. Follow **Section 4** to see data flowing through the system
4. Skim the diagram to visualize the flow

### For **Developers** (implementing or debugging):
1. Use **calculations_diagram_dev.mmd** as visual reference
2. Look up specific data source in `explain.md` **Section 3**
3. Find file locations and fallback logic in **Section 7**
4. Cross-reference `calculations.csv` column usage in **Section 5**

### For **Data Scientists** (analyzing results):
1. Read `explain.md` **Section 5** (Understanding calculations.csv)
2. Review **Section 6** (Validation) to understand quality checks
3. Check **Section 4** (Data Flow) to trace specific feature calculations
4. Use diagram to understand feature dependencies

### For **Project Managers** (explaining to stakeholders):
1. Show the enhanced **calculations_diagram_dev.mmd** diagram
2. Reference `explain.md` **Section 1** (Overview) + diagram legend
3. Explain 9 data sources using **Section 3**
4. Share validation section showing quality checks

---

## 📊 Mapping between Documents and Code

### explain.md → Source Code Mapping

| explain.md Section | Key Files | Line Numbers |
|-------------------|-----------|--------------|
| Entry Point | `src/pipeline/run_pipeline.py` | 1-30 |
| Data Sources: Census Population | `src/utils/real_data.py` | 149-182 |
| Data Sources: Census Housing | `src/utils/real_data.py` | 184-217 |
| Data Sources: ACS | `src/utils/real_data.py` | 300-340 |
| Data Sources: HIFLD | `src/utils/real_data.py` | 420-460 |
| Data Sources: OSM | `src/utils/real_data.py` | 480-515 |
| Data Flow: Ingestion | `src/ingestion/load_real_blocks.py` | ALL |
| Data Flow: Preprocessing | `src/preprocessing/preprocess_blocks.py` | ALL |
| Data Flow: Feature Engineering | `src/pipeline/feature_pipeline.py` | ALL |
| Data Flow: Risk Model | `src/models/risk_model.py` | ALL |
| Understanding calculations.csv | `calculations.csv` | All 27 rows |
| Validation | `src/validation/metrics.py` | ALL |
| Validation | `src/utils/validator.py` | ALL |
| Fallback Logic | `src/utils/real_data.py` | Lines with `fallback_*` calls |

### calculations_diagram_dev.mmd → Source Code Mapping

| Diagram Section | Python Files |
|-----------------|--------------|
| DATA SOURCES | URLs in `src/utils/real_data.py` comments |
| INGESTION LAYER | `src/utils/real_data.py` fetch functions |
| PREPROCESSING LAYER | `src/preprocessing/preprocess_blocks.py` |
| FEATURE ENGINEERING: HAZARD | `src/features/hazard.py` |
| FEATURE ENGINEERING: EXPOSURE | `src/features/exposure.py` |
| FEATURE ENGINEERING: VULNERABILITY | `src/features/vulnerability.py` |
| FEATURE ENGINEERING: RESILIENCE | `src/features/resilience.py` |
| RISK MODEL LAYER | `src/models/risk_model.py` |
| VALIDATION LAYER | `src/validation/metrics.py` + `src/utils/validator.py` |
| EXPORT LAYER | `src/pipeline/export.py` |

---

## ✅ Questions Answered

### Question 1: Which Python program runs first?
**Answer in explain.md:** Section 2 "Entry Point"
- File: `src/pipeline/run_pipeline.py`
- Function: `run()`
- Command: `python -m src.pipeline.run_pipeline`

### Question 2: For each data source, which .py file runs it and where is data stored?
**Answer in explain.md:** Section 3 "Data Sources"
- Each of the 9 data sources has:
  - Relevant Python file(s)
  - Storage location (local cache)
  - URL
  - Fallback behavior

### Question 3: Which files do validation?
**Answer in explain.md:** Section 6 "Validation"
- `src/utils/validator.py` — Column, null, range, type validation
- `src/validation/metrics.py` — Aggregation, comparison, prediction, concentration, Gini validation

### Question 4: Are calculations.csv columns used during data retrieval?
**Answer in explain.md:** Section 5 "Understanding calculations.csv"
- Detailed explanation of all 8 columns
- How each column is used by the code
- Mapping table showing which files use which columns

---

## 📌 Key Resources for Reference

| Document | Best For | Length | Key Sections |
|----------|----------|--------|--------------|
| `explain.md` | Comprehensive explanation for anyone | ~1,500 lines | All sections |
| `calculations_diagram_dev.mmd` | Visual architecture reference | ~180 lines (compact) | Entire diagram |
| `README.md` | Setup and API reference | ~200 lines | Quickstart + API |
| `calculations.csv` | Canonical schema | 27 data rows | All rows for detailed specs |
| `team155report.md` | Academic methodology | ~100 pages | Problem statement + Methods |

---

## 🔄 Next Steps

These documentation files serve as **foundation for:**
1. ✅ Onboarding new team members
2. ✅ Debugging data issues (consult Section 7 of explain.md)
3. ✅ Explaining architecture to stakeholders
4. ✅ Understanding feature dependencies (use diagram)
5. ✅ Reference when modifying pipeline (consult calculations.csv mapping)

**These documents are independent of code fixes** — they document the current state of the system as-is, including known issues like integer overflow in `build_features.py`.
