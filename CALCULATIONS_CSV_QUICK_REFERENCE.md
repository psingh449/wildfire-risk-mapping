# Quick Reference: What Gets Read from calculations.csv

## TL;DR

| Question | Answer | Details |
|----------|--------|---------|
| **Are weights dynamically read?** | ✅ YES | `src/features/build_features.py:44-45` |
| **Are min/max dynamically read?** | ✅ YES | `src/utils/real_data.py:42,46` |
| **Are API params dynamically read?** | ❌ NO | Hardcoded in `src/utils/real_data.py` |
| **Are formulas dynamically read?** | ❌ NO | Hardcoded in feature functions |
| **Are data sources dynamically read?** | ❌ NO | Hardcoded URLs as constants |
| **Is calculations.csv used at runtime?** | ⚠️ PARTIALLY | Only weights + bounds |

---

## The Evidence

### ✅ What IS Read (Find by searching these files)

**Weights:**
```bash
File: src/features/build_features.py
Search: "_load_component_weights_from_calculations"
Lines: 37-72
Evidence: 
    row.get("weight_group")  # Line 44
    row.get("weight")        # Line 45
    Reads CSV and uses values to compute scores
```

**Min/Max Bounds:**
```bash
File: src/utils/real_data.py
Search: "get_limits"
Lines: 26-52
Evidence:
    row.get("min")   # Line 42
    row.get("max")   # Line 46
    Reads CSV and uses bounds for fallback generation
```

### ❌ What IS NOT Read (Find these to verify)

**URLs (hardcoded):**
```bash
File: src/utils/real_data.py
Lines: 103-104
Code:
    CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"
NOT from source_url column!
```

**API Parameters (hardcoded):**
```bash
File: src/utils/real_data.py
Lines: 108-113, 200-207, etc.
Code:
    params = {"get": "P1_001N,GEOID", "for": "block:*", ...}
NOT from api_params column!
```

**Formulas (hardcoded in logic):**
```bash
File: src/features/hazard.py, exposure.py, etc.
Examples:
    forest_density = forest_pixels / total_pixels
    distance_score = 1 / (1 + distance_km)
NOT read from calculation_formula column!
```

---

## Reading calculations.csv at Runtime - Code Path

```
START: python -m src.pipeline.run_pipeline
    ↓
run_pipeline.py:run()
    ↓
step_features() calls build_features()
    ↓
src/features/build_features.py:build_features()
    ↓
_get_component_weights() [line 65]
    ├─ calls _load_component_weights_from_calculations() [line 37]
    │   └─ Opens calculations.csv
    │   └─ Reads weight_group + weight columns  ✅ READ
    │   └─ Returns: {"hazard_score": {weights}, ...}
    │
    └─ Returns component weights
        └─ Used in weighted_sum() to compute scores [line 79]

PLUS:

During feature engineering, when APIs fail:
    src/utils/real_data.py:fallback_int() or fallback_uniform()
        ├─ calls get_limits(var) [line 66]
        │   └─ Opens calculations.csv
        │   └─ Reads min + max columns  ✅ READ
        │   └─ Returns: (min_val, max_val)
        │
        └─ Uses bounds to generate dummy data [line 71]
```

---

## CSV Column Usage Matrix

```
LEGEND:
🔥 = Read at runtime
📋 = Documentation only (hardcoded in code)
⚙️ = Ignored completely

Column              | Used? | Evidence
--------------------|-------|------------------------------------------
weight_group        | 🔥    | build_features.py:44
weight              | 🔥    | build_features.py:45, real_data.py:66
min                 | 🔥    | real_data.py:42
max                 | 🔥    | real_data.py:46
--------------------|-------|------------------------------------------
data_source         | 📋    | Described in code docs, not read
source_url          | 📋    | URLs hardcoded as constants
api_endpoint        | 📋    | Hardcoded in API calls
api_params          | 📋    | Hardcoded in params dict
calculation_formula | 📋    | Implemented as Python logic
dependencies        | 📋    | Pipeline order hardcoded
join_keys           | 📋    | Hardcoded in feature functions
transform_steps     | 📋    | Implemented as Python code
--------------------|-------|------------------------------------------
geojson_property    | 🔥    | Used as lookup key in get_limits()
function_name       | ⚙️    | Not used in code
variable            | 🔥    | Used as lookup key in get_limits()
Implemented         | 📋    | Status tracking only
Implementation Notes| 📋    | Reference documentation
Test Coverage       | 📋    | Reference documentation
frontend_field      | 📋    | Frontend configuration only
data_type           | 📋    | Documentation only
unit                | 📋    | Documentation only
nullable            | 📋    | Documentation only
validation_rules    | 📋    | Hardcoded in validator.py
description         | 📋    | Documentation only
exists_in_code      | 📋    | Status tracking
used_in_validation  | 📋    | Status tracking
output_column       | 📋    | Documentation only
notes               | 📋    | Documentation only
```

---

## How to Verify This Yourself

### Test 1: Change Weights and See if Behavior Changes

```bash
# Before:
calculations.csv row 1: weight: 0.333333 (for hazard_wildfire)

# Run pipeline:
python -m src.pipeline.run_pipeline

# Save results.
# Now change:
calculations.csv row 1: weight: 0.7 (increase hazard_wildfire weight)

# Run pipeline again:
python -m src.pipeline.run_pipeline

# Compare: hazard_score values should be different ✓ CONFIRMS weights are read
```

### Test 2: Change API Parameter and See if it's Ignored

```bash
# In calculations.csv row 5 (Census Population):
api_params: "get=P1_001N&for=block:*&in=state:06 county:007"

# Change to something invalid:
api_params: "get=INVALID_FIELD&for=block:*"

# Run pipeline:
python -m src.pipeline.run_pipeline

# Check: Pipeline still works with original parameter ✗ CONFIRMS api_params ignored
# (It uses hardcoded parameter in code, not CSV)
```

### Test 3: Change Min/Max and See Fallback Data Bounds Change

```bash
# In calculations.csv row 5 (Census Population):
min: 0
max: 100000

# Change to:
min: 0
max: 1000

# Stop Census API from working (comment out in code or disconnect internet)
# Run pipeline (forces fallback)

# Check: Dummy data generated between 0-1000 ✓ CONFIRMS min/max are read
```

---

## The Verdict

**Your statement: "Only weights column is read dynamically"**

**Fact check:**
- ✅ Weights ARE read dynamically
- ⚠️ Also min/max are read dynamically (for fallback bounds)
- ❌ Everything else is static (despite being in CSV)

**Corrected statement:**
"Only weights, weight_group, min, and max columns are read dynamically at runtime. Everything else in calculations.csv is static documentation that describes the implementation in Python code."

---

## Why Does This Matter?

### If you want to configure the system:
- ✅ Change weights in calculations.csv
- ✅ Change min/max bounds in calculations.csv
- ❌ Don't change anything else in CSV; update Python code instead

### If you're debugging data issues:
- ✓ Check calculations.csv weights if composite scores seem wrong
- ✓ Check calculations.csv min/max if fallback data seems wrong
- ✗ Don't blame CSV if API calls fail; check Python code

### If you're onboarding new people:
- ✓ Tell them: "calculations.csv is primarily documentation"
- ✓ Tell them: "Only weights are configurable via CSV"
- ✓ Tell them: "Most behavior is hardcoded in Python"

---

## Files to Read for More Details

| Question | Read This |
|----------|-----------|
| What exactly gets read? | `CALCULATIONS_CSV_ANSWER.md` |
| Why is it designed this way? | `CALCULATIONS_CSV_ARCHITECTURE.md` |
| How to understand the full flow? | `explain.md` Section 5 |
| How to find specific code? | See "Evidence" sections above |
