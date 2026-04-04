# How to Debug Diagnostics

1. **Run the pipeline** and generate output GeoJSON and diagnostics report.
2. **Check the `diagnostics` column** in the output GeoJSON for each block.
3. **Open `data/real/diagnostics_report.csv`** to see a summary of all validation issues.
4. **Review logs** for warnings and errors about missing or out-of-range values.
5. **Use the UI debug mode** to see diagnostics for each block on hover.
6. **Fix data or code issues** as indicated by diagnostics, then rerun the pipeline and tests.
