# How to Refresh Data

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
4. **Rerun the pipeline:**
   ```bash
   python -m src.pipeline.run_pipeline
   ```
5. **Check diagnostics:**
   - Review `data/real/diagnostics_report.csv` for validation issues.
   - Check logs for warnings/errors.
