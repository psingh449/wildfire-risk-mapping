# Quick Start Guide to New Documentation

## 📚 Three New Documents Created

This guide helps you understand what was created and how to use it.

---

## 1️⃣ explain.md — The Complete Novice Guide
**Location:** Root directory → `explain.md`  
**Size:** ~2,500 lines  
**Audience:** Anyone from non-technical to intermediate developers  

### What It Answers

✅ **"Which Python program runs first?"**
- Answer: `src/pipeline/run_pipeline.py` → run() function
- How to execute: `python -m src.pipeline.run_pipeline`

✅ **"Where does each data source come from and where is it stored?"**
- 9 data sources explained in detail:
  - Source URL
  - Python files that fetch it
  - Storage location (local cache)
  - What happens if it fails (fallback)
  
✅ **"Which files do validation?"**
- `src/utils/validator.py` — Basic checks (columns, nulls, ranges, types)
- `src/validation/metrics.py` — Advanced validation (county aggregation, FEMA comparison, fire overlap, AUC, concentration, Gini)

✅ **"How does calculations.csv work?"**
- Detailed breakdown of all 8 column categories
- How each column is used during data retrieval
- Complete mapping table showing code-to-CSV relationships

### How to Navigate

```
explain.md Structure:
├─ Overview ........................... What the system does
├─ Entry Point ........................ Which file runs first + 5-stage pipeline
├─ Data Sources ....................... 9 sources with URLs + storage + fallback
├─ Data Flow .......................... 5-stage pipeline explained with file paths
├─ Understanding calculations.csv ..... All 8 columns with examples
├─ Validation ......................... 8 validation checks explained
├─ What Happens When Data Fails ....... Fallback logic for each source
└─ Summary ............................ Quick reference tables
```

### Example: Finding Census Population Logic

**Question:** "How does the system get population data and where is it stored?"

**Answer in explain.md:**
- Section 3, Subsection "3. Census Population Data"
- Python file: `src/utils/real_data.py`
- API: `https://api.census.gov/data/2020/dec/pl`
- Storage: `data/real/census_population.csv`
- Fallback: Random integers in range [0, max_population]
- Function: `compute_exposure_population_real()`

---

## 2️⃣ calculations_diagram_dev.mmd — Visual Architecture
**Location:** Root directory → `calculations_diagram_dev.mmd`  
**Type:** Mermaid flowchart  
**Purpose:** Visual reference showing entire pipeline  

### What It Shows

**7 Pipeline Stages (color-coded):**
1. 🔍 **DATA SOURCES** (9 providers with URLs, storage, fallback)
2. 📥 **INGESTION** (fetch functions mapping to 17 raw features)
3. 🧹 **PREPROCESSING** (4 standardization steps)
4. ⚙️ **FEATURE ENGINEERING** (17 features organized by component)
   - 🔥 HAZARD (3 features + score)
   - 👥 EXPOSURE (3 features + score)
   - 😟 VULNERABILITY (3 features + score)
   - 🛡️ RESILIENCE (3 features + score)
5. 🎲 **RISK MODEL** (3 final calculations)
6. ✅ **VALIDATION** (8 quality checks)
7. 📤 **EXPORT** (output formats)

### How to Read It

**Each node contains:**
- Function name (e.g., `compute_hazard_wildfire`)
- Data source or formula
- Output column name
- Data type and range
- Computation type (API call, raster stats, distance calc, etc.)

**Example: Hazard Wildfire Node**
```
compute_hazard_wildfire
Source: WHP raster
Formula: mean pixel value
Range: 0-1
```

**How to Use:**
- **Visual planning:** See entire pipeline at glance
- **Dependency understanding:** Follow arrows to see which features depend on others
- **File location finding:** Each layer labeled with source file path
- **Stakeholder presentation:** Show non-technical audience how it works

### How to View

- Open in VS Code: Click Preview icon on .mmd file
- View online: Copy content to https://mermaid.live
- Share with team: Diagram is self-contained documentation

---

## 3️⃣ DOCUMENTATION_SUMMARY.md — Meta-Index
**Location:** Root directory → `DOCUMENTATION_SUMMARY.md`  
**Size:** ~400 lines  
**Purpose:** Guide to all documentation resources  

### What It Contains

- Detailed breakdown of explain.md sections
- Visual guide to calculations_diagram_dev.mmd layers
- Code-to-documentation mappings
- FAQ showing where to find answers
- Usage recommendations by audience type

### How to Use It

**If you're unsure which document to read:**
→ Check DOCUMENTATION_SUMMARY.md "How to Use These Resources" section

**If you need to map documentation to code:**
→ Check DOCUMENTATION_SUMMARY.md "Mapping between Documents and Code" table

**If you need to find a specific answer:**
→ Check DOCUMENTATION_SUMMARY.md "Questions Answered" section

---

## 🎯 Quick Reference: Finding Answers

### "I need to know..."

| Your Question | Read This | Section |
|---|---|---|
| Where does data come from? | explain.md | "Data Sources" |
| How are features calculated? | calculations_diagram_dev.mmd | FEATURE ENGINEERING layer |
| What if an API is down? | explain.md | "What Happens When Data Can't Be Retrieved" |
| What is calculations.csv? | explain.md | "Understanding calculations.csv" |
| How is risk calculated? | calculations_diagram_dev.mmd | RISK MODEL layer |
| What validation happens? | explain.md | "Validation" |
| How do I run the program? | explain.md | "Entry Point" |
| Which Python file does X? | DOCUMENTATION_SUMMARY.md | "Mapping" table |
| What's the overall pipeline? | calculations_diagram_dev.mmd | Entire diagram |
| How to explain to non-technical? | explain.md | "Overview" section |

---

## 📊 Document Comparison

| Aspect | explain.md | calculations_diagram_dev.mmd | DOCUMENTATION_SUMMARY.md |
|--------|-----------|------|----------|
| **Format** | Markdown (text) | Mermaid (diagram) | Markdown (index) |
| **Length** | ~2,500 lines | ~180 lines | ~400 lines |
| **Best for** | Deep explanation | Quick visual reference | Navigation |
| **Audience** | Novices → Intermediate | Visual learners | Everyone |
| **Reads like** | Tutorial | Flowchart | Meta-guide |
| **Update frequency** | When logic changes | When pipeline changes | When docs change |

---

## 💡 Usage Examples

### Example 1: New Team Member Onboarding
**Goal:** Understand how the system works in 30 minutes

**Steps:**
1. Read explain.md "Overview" → 5 min
2. Read explain.md "Entry Point" → 5 min
3. Look at calculations_diagram_dev.mmd → 5 min
4. Skim explain.md "Data Sources" → 10 min
5. Skim explain.md "Data Flow Through Pipeline" → 5 min

### Example 2: Debugging Census Population Fetch Failure
**Goal:** Fix a broken Census API call

**Steps:**
1. Open explain.md → Section "3. Census Population Data"
2. Find Python file: `src/utils/real_data.py`
3. Find function: `compute_exposure_population_real()`
4. Check fallback logic: "What Happens When Data Can't Be Retrieved"
5. Check calculations.csv for api_params to see what was requested

### Example 3: Understanding Why a Feature Has Bad Values
**Goal:** Trace a specific feature through the pipeline

**Steps:**
1. Open calculations_diagram_dev.mmd
2. Find feature in one of the 4 FEATURE ENGINEERING subgraphs
3. Read formula and data type
4. Follow arrow backward to see dependencies
5. Check explain.md section for that specific data source

### Example 4: Explaining Risk Calculation to Stakeholders
**Goal:** Explain the math in simple terms

**Steps:**
1. Show calculations_diagram_dev.mmd RISK MODEL layer
2. Explain each component (Hazard, Exposure, Vulnerability, Resilience)
3. Show the formula: H × E × V × (1-R)
4. Explain EAL: Risk score × Building value
5. Reference explain.md for definitions

### Example 5: Validating Model Quality
**Goal:** Check that results are reasonable

**Steps:**
1. Read explain.md "Validation" section
2. Understand 8 validation checks
3. Check which metrics are available
4. Review calculations_diagram_dev.mmd VALIDATION layer
5. Cross-reference with src/validation/metrics.py

---

## 🔗 Navigation Between Documents

```
Start Here
    ↓
explain.md "Overview"
    ↓
Want visual? → calculations_diagram_dev.mmd
    ↓
Want details? → explain.md relevant section
    ↓
Need to map to code? → DOCUMENTATION_SUMMARY.md mapping table
    ↓
Ready to code? → src/ file paths from mapping
```

---

## 📋 Checklist: What's Been Documented

✅ **Pipeline Architecture**
- 5-stage pipeline with file paths
- Data flow between stages
- Dependency relationships

✅ **Data Sources (9 Total)**
- Source names and URLs
- Python fetch functions
- Local storage locations
- Fallback mechanisms
- API parameters

✅ **Feature Engineering (17 Features)**
- 4 components (Hazard, Exposure, Vulnerability, Resilience)
- Each component: 3 raw features + 1 composite score
- Formulas for each feature
- Data types and ranges

✅ **Risk Calculation**
- Mathematical formula
- Component weighting
- EAL calculation
- Normalization

✅ **Validation (8 Checks)**
- What each check validates
- Why it matters
- Which file implements it

✅ **Error Handling**
- Fallback logic for each data source
- How to detect if using dummy data
- How to refresh data

✅ **calculations.csv Usage**
- All 8 column categories explained
- Examples for each column
- Code-to-schema mapping

---

## 🚀 Next Steps

1. **Share with team:** Send explain.md link to non-technical members
2. **Reference in PRs:** Link to calculations_diagram_dev.mmd in architecture discussions
3. **Use for docs:** Embed DOCUMENTATION_SUMMARY in project wiki
4. **Keep updated:** When code changes, update corresponding doc section
5. **Version control:** Commit all three docs to Git

---

## ❓ FAQ

**Q: Which document should I read first?**  
A: explain.md Section 1-2, then look at the diagram

**Q: Can I share these with non-technical people?**  
A: Yes! explain.md Overview + diagram work well for stakeholders

**Q: Do these replace the code comments?**  
A: No, they complement code comments. Use docs for big picture, code for details

**Q: What if something changes in the code?**  
A: Update the corresponding section in explain.md and/or the diagram

**Q: How often should these be updated?**  
A: Whenever pipeline architecture or data sources change significantly

**Q: Can I print the diagram?**  
A: Yes, export from https://mermaid.live or use print-to-PDF in VS Code

---

## 📞 Support

**If you have questions:**
- Check explain.md for conceptual understanding
- Check DOCUMENTATION_SUMMARY.md for navigation help
- Check calculations_diagram_dev.mmd for visual understanding
- Check code files for implementation details

**If documentation is unclear:**
- Add comments to the specific section
- Create an issue in the repo
- Update the doc with clearer examples
