# How to Add a New Feature

1. **Define the feature** in `calculations.csv` with min, max, units, formula, and data source.
2. **Implement the feature function** in `src/features/` (e.g., `hazard.py`, `exposure.py`).
3. **Add provenance tracking** using `mark_real` or `mark_dummy`.
4. **Update the feature pipeline** in `src/pipeline/feature_pipeline.py` to include your new feature.
5. **Add validation rules** if needed in `src/utils/validator.py`.
6. **Add tests** in `tests/` for your new feature.
7. **Update the data dictionary** in the README if appropriate.
8. **Run the pipeline and tests** to verify your feature is integrated and robust.
