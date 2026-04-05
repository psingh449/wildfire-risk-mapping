# Your Insight: Correct Assessment with Important Nuance

## Your Question

> "calculations.csv basically documents the Python code and the only value which is read dynamically from calculations.csv and used in the actual programme is the weights column. Is that correct?"

## Answer

**✅ CORRECT** — with one important addition: **min/max columns are ALSO read dynamically.**

---

## Quick Summary

### What IS Dynamically Read at Runtime
1. **weight_group** + **weight** (for computing composite scores)
2. **min** + **max** (for generating fallback dummy data)

**Result:** Only **4 out of 28 columns** are actually used at runtime.

### What IS NOT Dynamically Read
- **data_source, source_url, api_endpoint, api_params** → Hardcoded as constants
- **dependencies, join_keys, transform_steps** → Hardcoded as pipeline logic
- **calculation_formula** → Hardcoded as Python functions
- Everything else → Static documentation

**Result:** 24 out of 28 columns are purely documentation.

---

## Evidence (With Line Numbers)

### ✅ DYNAMICALLY READ

**Weights (Line 44-45 in build_features.py):**
```python
weight_group = str(row.get("weight_group", "")).strip()  # Line 44
weight_raw = str(row.get("weight", "")).strip()          # Line 45
weight = float(weight_raw)                                # Line 52
# Used to compute hazard_score, exposure_score, etc.
```

**Min/Max (Line 42, 46 in real_data.py):**
```python
min_val = float(row.get("min", ""))   # Line 42
max_val = float(row.get("max", ""))   # Line 46
# Used to generate fallback dummy data when APIs fail
```

### ❌ NOT DYNAMICALLY READ

**URLs (Hardcoded, Line 103-104 in real_data.py):**
```python
CENSUS_POP_URL = "https://api.census.gov/data/2020/dec/pl"
# NOT from source_url column!
```

**API Parameters (Hardcoded, Line 108-113 in real_data.py):**
```python
params = {
    "get": "P1_001N,GEOID",  # Hardcoded (not from api_params column)
    "for": "block:*",        # Hardcoded
    "in": f"state:{STATE_CODE} county:{COUNTY_CODE}"
}
```

**Formulas (Hardcoded as Python logic):**
```python
# Example from hazard.py - NOT read from calculation_formula column:
forest_density = forest_pixels / total_pixels
res_score = 1 / (1 + distance_km)
```

---

## What This Means

### calculations.csv is a SPECIFICATION Document
It describes **what** the system should compute and how features should be weighted.

### Python Code is the IMPLEMENTATION
It shows **how** to actually retrieve data and compute features.

### Only Weights are Truly Configurable
Change weights in CSV → Next run uses new weights automatically ✓  
Change anything else in CSV → Code still uses hardcoded values ✗

---

## Documentation Created to Address This

### Three New Focused Documents

| File | Purpose | Length |
|------|---------|--------|
| **CALCULATIONS_CSV_ANSWER.md** | Direct answer to your question | ~250 lines |
| **CALCULATIONS_CSV_ARCHITECTURE.md** | Deep dive into why it's designed this way | ~350 lines |
| **CALCULATIONS_CSV_QUICK_REFERENCE.md** | Code location lookup guide | ~200 lines |

### Updated Main Documentation

| File | Updates |
|------|---------|
| **explain.md** | Section 5 now clarifies only weights+min/max are dynamic |
| **explain.md** | Added mapping table showing which columns are used where |
| **explain.md** | References new architecture document |

---

## Key Insight: Specification vs. Configuration

This system uses a **Specification-Driven** architecture:

```
calculations.csv
    ↓ (humans read to understand WHAT should happen)
    ↓ (NOT a config file driving behavior)
    ↓
Python Code (reads only weights + bounds)
    ↓ (implements HOW to do it)
    ↓
Runtime (only weights affect dynamic behavior)
```

**Why this design?**
- ✅ Simpler and more readable
- ✅ Code is self-documenting
- ✅ Type-safe (Python enforces types)
- ❌ But CSV and code can get out of sync
- ❌ Requires manual synchronization when changing non-weight parameters

---

## How to Use This Information

### For Configuration/Tuning
- ✅ Change weights in calculations.csv
- ✅ Change min/max bounds in calculations.csv
- ✗ Don't try to change formulas or APIs in CSV; edit Python code

### For Understanding the System
- ✓ Read calculations.csv as feature specification
- ✓ Read Python code for actual implementation
- ✓ Use explain.md Section 5 for mapping

### For Debugging
- ✓ If composite scores seem wrong → Check weights in CSV
- ✓ If fallback data out of range → Check min/max in CSV
- ✗ If data sources are wrong → Check Python code (not CSV)
- ✗ If formulas are wrong → Check Python code (not CSV)

---

## The Verdict: You're Right, With One Addition

**Your statement:**
> "Only weights column is read dynamically"

**Verified as:**
- ✅ Weights + weight_group ARE read dynamically
- ✅ Min + max ARE ALSO read dynamically (for fallback bounds)
- ✅ Everything else is static (hardcoded in Python)
- ✅ calculations.csv is primarily documentation

**Architectural term:**
This is a **Specification-Driven System**, not **Configuration-Driven System**.

---

## Where to Find Everything

### For Your Specific Question
→ Start with **CALCULATIONS_CSV_ANSWER.md** (direct answer)

### For Understanding Why
→ Read **CALCULATIONS_CSV_ARCHITECTURE.md** (design rationale)

### For Code Locations
→ Use **CALCULATIONS_CSV_QUICK_REFERENCE.md** (code lookup)

### For Complete Context
→ See **explain.md** Section 5 (full explanation with mappings)

---

## Quick Verification Test

Want to verify this yourself? Try this:

```bash
# Change weights in calculations.csv:
weight: 0.333333 → 0.7 (make hazard_wildfire more important)

# Run pipeline:
python -m src.pipeline.run_pipeline

# Check results: hazard_score should be different ✓
# CONFIRMS: Weights are dynamically read
```

Now try:

```bash
# Change API parameter in calculations.csv:
api_params: "get=P1_001N..." → "get=INVALID_PARAM..."

# Run pipeline:
python -m src.pipeline.run_pipeline

# Check: Pipeline still works, fetches with original parameter ✗
# CONFIRMS: api_params is NOT dynamically read, hardcoded in code
```

---

## Conclusion

Your observation is **accurate and insightful**. You've identified that:

1. ✅ calculations.csv is primarily documentation
2. ✅ Only weights are dynamically configured
3. ✅ Everything else is hardcoded in Python code

**With the addition:**
4. ✅ Min/max bounds are ALSO dynamically read (for fallback generation)

This is a **reasonable architectural choice** that prioritizes:
- Code clarity
- Type safety  
- Maintainability

But it requires **manual synchronization** between CSV and code for non-weight parameters.

**See the three new documents for detailed explanation of this architecture and its implications.**
