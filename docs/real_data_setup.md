# Real Data Setup (Commit 11)

## Goal
Enable switching between mock and real geometry.

## How to use real data
1. Download Census Block Group GeoJSON for Butte County
2. Place file at:
   data/raw/block_groups.geojson

3. In code:
   src/pipeline/steps.py
   set:
   USE_REAL_DATA = True

## Notes
- If file not found → fallback to mock data
- Geometry only for now (attributes still mock)
