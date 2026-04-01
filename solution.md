# Wildfire Risk Mapping -- Implementation Plan (solution.md)

## 1. Current Status (Baseline)

-   Repo: wildfire-risk-mapping
-   Live demo: GitHub Pages working
-   Data: Mock dataset (49 grid cells)
-   Features:
    -   Risk calculation pipeline
    -   GeoJSON export
    -   D3 visualization (choropleth)
    -   Dropdown for metrics (risk, hazard, exposure, etc.)
-   Architecture:
    -   Python pipeline (no backend)
    -   Static frontend (D3)
    -   GitHub Pages deployment

------------------------------------------------------------------------

## 2. Key Design Principles

-   Schema-first approach
-   Modular pipeline (ingestion → features → model → export)
-   Precomputed data (no backend)
-   Parallel development enabled
-   Start with mock → replace with real data
-   Scalable naming (blocks.geojson)

------------------------------------------------------------------------

## 3. Development Environment

-   Visual Studio 2026 (Windows 11)
-   Python + D3.js
-   GitHub + GitHub Pages

------------------------------------------------------------------------

## 4. Roadmap

1.  Stabilize pipeline
2.  Improve visualization
3.  Add real data
4.  Multi-region support
5.  Advanced analysis

------------------------------------------------------------------------

## 5. Commit Plan

### Phase 1 --- Stabilization (1--5)

1.  Cleanup repo + documentation
2.  Centralize config
3.  Add logging
4.  Data validation checks
5.  Pipeline refactor

### Phase 2 --- Visualization (6--10)

6.  Add legend
7.  Improve tooltip
8.  UI enhancements
9.  Metric descriptions
10. Reset/default view

### Phase 3 --- Real Data (11--16)

11. Load real geometry
12. Replace mock geometry
13. Add population data
14. Improve exposure
15. Improve hazard proxy
16. Separate mock vs real pipeline

### Phase 4 --- Multi-region (17--20)

17. Add region parameter
18. Multi-county support
19. Flexible GeoJSON naming
20. UI region selector

### Phase 5 --- Advanced Modeling (21--25)

21. Configurable weights
22. Sensitivity analysis
23. Risk distribution plots
24. Validation module
25. Risk concentration metrics

### Phase 6 --- Polish (26--30)

26. Geometry simplification
27. Performance optimization
28. Code cleanup
29. Documentation updates
30. Final demo polish

------------------------------------------------------------------------

## 6. Parallel Work

-   Data
-   Features
-   Model
-   UI
-   Validation

------------------------------------------------------------------------

## 7. Future

-   PostGIS integration
-   Full USA scaling
-   Real wildfire datasets

------------------------------------------------------------------------

## 8. Summary

You have a working prototype. Execute commits incrementally to reach
final system.
