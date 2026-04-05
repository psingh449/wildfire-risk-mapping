# Architecture Insight: calculations.csv as Specification vs. Configuration

## The Question

> "calculations.csv basically documents the Python code and the only value which is read dynamically from calculations.csv and used in the actual programme is the weights column. Is that correct?"

## The Answer

**Mostly YES, with nuance.** 

Only **2 out of 28 columns** in calculations.csv are actually **dynamically read and used by the Python program** at runtime:

### ✅ DYNAMICALLY READ (2 columns)
1. **weight_group + weight** → Used to compute composite scores
2. **min + max** → Used to generate fallback dummy data bounds

### ❌ STATIC DOCUMENTATION (26 columns)
- **data_source, source_url, api_endpoint, api_params**
- **dependencies, join_keys, transform_steps, calculation_formula**
- Everything else

---

## Where Columns Are Used

### ✅ Runtime (Actual Behavior)

**Location: `src/features/build_features.py` lines 37-72**
```python
def _load_component_weights_from_calculations():
    """Reads weight_group and weight from CSV"""
    for row in reader:
        weight_group = row.get("weight_group")  # e.g., "hazard_score"
        weight = float(row.get("weight"))        # e.g., 0.333333
        variable = row.get("geojson_property")   # e.g., "hazard_wildfire"
        
        groups[weight_group][f"{variable}_norm"] = weight
    return groups
```

**Location: `src/utils/real_data.py` lines 26-52**
```python
def get_limits(var: str) -> Tuple[float, float]:
    """Reads min and max from CSV for fallback generation"""
    for row in reader:
        if row.get("geojson_property") == var:
            min_val = float(row.get("min"))      # e.g., 0
            max_val = float(row.get("max"))      # e.g., 1
            return min_val, max_val
    return 0, 1  # Defaults if not found
```

### ❌ Static/Hardcoded

**Location: `src/utils/real_data.py` and `src/features/*.py`**
```python
# NOT READ FROM CSV - Hardcoded
CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"  # data_source, source_url hardcoded
STATE_CODE = "06"  # api_params hardcoded
COUNTY_CODE = "007"

# Formulas are in functions
def compute_exposure_population_real(gdf):
    # calculation_formula hardcoded as logic
    gdf["exposure_population"] = gdf["GEOID"].map(pop_dict).fillna(0).astype(int)
```

---

## Architectural Pattern: Specification vs. Configuration

This system follows a **SPECIFICATION-DRIVEN** architecture, not a **CONFIGURATION-DRIVEN** architecture.

### Specification-Driven (Current Design)
```
calculations.csv
    ↓ (mostly documentation)
    ↓ (humans read to understand WHAT should happen)
    ↓
Python Code
    ↓ (implements HOW to do it)
    ↓ (reads only weights + min/max)
    ↓
Runtime Behavior
```

### Configuration-Driven (Alternative Design)
```
calculations.csv
    ↓ (all parameters in CSV)
    ↓ (program reads ALL columns)
    ↓
Generic Python Framework
    ↓ (no hardcoded logic)
    ↓ (fully interpreted from CSV)
    ↓
Runtime Behavior
```

**Current system = Specification-Driven**

---

## Why This Design?

### Pros ✅
1. **Simplicity** — Code is straightforward and readable
2. **Type Safety** — Python enforces types at compile time
3. **Debuggability** — Easy to trace execution (no interpretation layer)
4. **Performance** — No CSV parsing overhead during feature computation
5. **IDE Support** — Code editors can autocomplete and lint

### Cons ❌
1. **Schema-Code Sync** — calculations.csv and code can diverge
   - If you update calculations.csv formulas, code doesn't automatically change
   - If you update code, calculations.csv must be manually synced
2. **Configuration Inflexibility** — Changing data sources requires code edits
3. **Duplication** — Information appears in both CSV and code
4. **Maintenance Burden** — Two places to update when schemas change

---

## Risk: Schema-Code Mismatch

The biggest risk is **calculations.csv and code getting out of sync**.

### Example of Mismatch

**In calculations.csv (row 18):**
```
calculation_formula: risk_score * exposure_building_value
```

**But in code (`src/models/risk_model.py` line 12):**
```python
eal = risk_score * building_value_est  # Uses 'building_value_est', not 'exposure_building_value'
```

**Problem:** These should be the same variable, but the CSV specifies `exposure_building_value` while the code uses `building_value_est`.

**Result:** If someone reads calculations.csv to understand EAL calculation, they'll be confused when they look at the code.

---

## What Gets Dynamically Read? (Precise List)

### During Feature Engineering

**Phase 1: Load Weights**
```python
# src/features/build_features.py
weights = _load_component_weights_from_calculations()  # Reads CSV
# Returns: {"hazard_score": {"hazard_wildfire_norm": 0.333, ...}, ...}
```

**Phase 2: Compute Composite Scores**
```python
# Uses dynamically loaded weights
hazard_score = sum(weights[feat] * normalized_value[feat] for feat in hazard_features)
```

### During Fallback Generation

**Phase 1: Get Bounds**
```python
# src/utils/real_data.py
min_val, max_val = get_limits("exposure_population")  # Reads CSV min/max
# Returns: (0, 100000) for exposure_population
```

**Phase 2: Generate Dummy Data**
```python
# Uses dynamically loaded bounds
dummy_values = fallback_int(gdf, "exposure_population", reason="API failed")
# Generates random integers between min_val and max_val
```

### Everything Else

❌ **Hardcoded in code:**
- Data source URLs
- API parameters
- Feature transformations
- Risk calculation formula
- Validation rules
- Export formats

---

## Maintenance Implications

### When Code Changes

**If Python code changes feature computation:**
1. ✅ Update the Python function
2. ⚠️ **MUST manually update calculations.csv**
3. Otherwise: CSV documentation becomes stale

### When calculations.csv Changes

**If you update calculation_formula in CSV:**
1. ✅ Code doesn't change automatically
2. ⚠️ You must update Python code to match
3. Otherwise: Code doesn't implement what CSV specifies

### When Weights Change

**If you update weight_group or weight column:**
1. ✅ Code AUTOMATICALLY uses new weights next run
2. No code changes needed
3. ✅ This is the main advantage of dynamic reading

---

## Recommendations

### 1. Accept the Current Pattern
- This is a reasonable design for a scientific project
- The "contract" between CSV and code is clear
- Weights ARE dynamically configured as intended

### 2. Be Explicit About It
- ✅ **Document this in explain.md** (DONE)
- ✅ **Add comments in code** mentioning calculations.csv
- ✅ **Use a validation test** that checks CSV-code alignment

### 3. Consider Future Improvements (Optional)
- Add a CSV validation function that checks if code matches CSV
- Example: Verify all variables in calculations.csv have corresponding Python functions
- Run as part of CI/CD pipeline to catch mismatches

### 4. Treat calculations.csv Properly
- Keep it as **Specification/Schema** document
- Treat it as **source of truth for feature definitions**
- When changing features:
  - Update calculations.csv FIRST
  - Then update Python code
  - Both must match

---

## Comparison to Other Architectures

### Apache Airflow (DAG-driven)
```
Airflow DAG (YAML/Python)
    ↓ (fully configurable)
    ↓ (all tasks defined in YAML)
    ↓
Generic Executor
    ↓ (interprets DAG)
    ↓
Task Execution
```

### MLflow (Experiment-driven)
```
experiment config (YAML)
    ↓ (defines hyperparameters)
    ↓ (Python reads config)
    ↓
Training loop
    ↓ (uses config values)
    ↓
Model artifacts
```

### This Project (Specification + Code)
```
calculations.csv (YAML-like specification)
    ↓ (humans read; code mostly hardcoded)
    ↓ (only weights + bounds read at runtime)
    ↓
Python functions
    ↓ (implements logic)
    ↓
Risk outputs
```

---

## Conclusion

**Your observation is accurate:** calculations.csv is primarily a specification document describing *what* the code should do. The Python code implements *how* to do it.

Only **weights and min/max bounds** are dynamically read. Everything else is hardcoded but documented in the CSV.

**This is neither a problem nor a mistake.** It's a deliberate architectural choice that prioritizes:
- Clarity (code is self-documenting)
- Simplicity (no CSV interpretation layer)
- Type safety (Python enforces types)

**Best practice going forward:**
- Keep calculations.csv as the *source of truth* for "what features should exist"
- Keep Python code as the *implementation* of "how to compute them"
- When one changes, manually update the other
- The weight columns will stay in sync automatically ✓

