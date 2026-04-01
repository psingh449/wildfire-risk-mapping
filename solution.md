# Wildfire Risk Mapping --- Solution Guide (Revised)

## 1. Overview & Architecture

-   End-to-end system:
    -   Python pipeline → GeoJSON → D3.js frontend → GitHub Pages
-   No backend:
    -   All data is **precomputed**
    -   Frontend is **static + interactive**
-   Pipeline stages:
    -   Ingestion → Preprocessing → Features → Model → Export
-   Key outputs:
    -   `risk_score` (0--1)
    -   `eal` (economic loss)
-   Design principles:
    -   Code = source of truth
    -   Modular functions per metric
    -   Dummy-first → replace with real data
    -   Always keep system runnable

------------------------------------------------------------------------

## 2. Development Workflow

-   Setup:
    -   Run pipeline:
        -   `python -m src.pipeline.run_pipeline`
    -   Run UI:
        -   `python -m http.server 8000`
-   Iteration cycle:
    -   Modify Python → regenerate GeoJSON → refresh UI
-   Team workflow:
    -   Each dev owns a module:
        -   hazard / exposure / vulnerability / resilience / model
    -   Replace dummy values independently
-   Debug mode:
    -   Toggle in UI
    -   Shows full variable breakdown per block
-   Naming:
    -   Raw: `exposure_population`
    -   Normalized: `*_norm`
    -   Scores: `*_score`

------------------------------------------------------------------------

## 3. Core Concepts

-   Hazard:
    -   Fire likelihood (vegetation, distance, etc.)
-   Exposure:
    -   Population + assets
-   Vulnerability:
    -   Socio-economic sensitivity
-   Resilience:
    -   Response/recovery capability
-   Risk:
    -   `H × E × V × (1 - R)`
-   EAL:
    -   `risk × building_value`

------------------------------------------------------------------------

## 4. Commit History (Latest → Oldest)

-   **18 --- Debug toggle + tooltip refactor**
    -   Added UI checkbox for debug mode
    -   Refactored tooltip into `buildTooltip()`
    -   Clean separation of dev vs production UI
    -   Added export structure (modular)
-   **17 --- Feature pipeline toggle + debug support**
    -   Introduced `USE_NEW_FEATURE_PIPELINE`
    -   Enabled safe switching between old/new pipeline
    -   Added debug flag (backend concept)
-   **16 --- Modular skeleton (major milestone)**
    -   Created feature modules:
        -   hazard / exposure / vulnerability / resilience
    -   Added dummy data generators
    -   Enabled parallel development
-   **15 --- EAL exposed in UI**
    -   Added EAL to dropdown
    -   Improved descriptions + legend
    -   UI now supports economic interpretation
-   **14 --- Economic model (EAL)**
    -   Added building value estimation
    -   Introduced risk formula (multiplicative)
    -   Computed Expected Annual Loss
-   **13 --- Real population integration**
    -   Pulled Census data
    -   GEOID-based merge
    -   First real dataset in system
-   **12 --- Real geometry integration**
    -   Replaced mock grid with block groups
    -   Introduced real GeoJSON pipeline
-   **11 --- Data ingestion improvements**
    -   Structured ingestion layer
    -   Better logging and validation
-   **10 --- Reset/default UI**
    -   Added reset button
    -   Standardized initial state
-   **9 --- Metric descriptions**
    -   Added explanatory text per metric
    -   Improved usability
-   **8 --- UI enhancements**
    -   Improved layout and controls
    -   Better readability
-   **7 --- Tooltip improvements**
    -   Added detailed hover info
    -   Introduced structured display
-   **6 --- Legend**
    -   Added color scale legend
    -   Enabled interpretation of values
-   **5 --- Pipeline refactor**
    -   Clean separation of steps
    -   Improved maintainability
-   **4 --- Validation**
    -   Column checks
    -   Null checks
-   **3 --- Logging**
    -   Added pipeline logs
    -   Easier debugging
-   **2 --- Config centralization**
    -   Moved weights/config to single place
-   **1 --- Initial setup**
    -   Basic pipeline + UI
    -   Mock data visualization

------------------------------------------------------------------------

## 5. Current Status & Next Steps

-   Current:
    -   Fully working end-to-end system
    -   Modular + scalable architecture
    -   UI supports multiple metrics + debug mode
-   Remaining:
    -   Replace dummy variables with real APIs
    -   Add data source tracking (REAL vs DUMMY)
    -   Improve hazard + resilience realism
-   Goal:
    -   Transition from prototype → decision-support system
