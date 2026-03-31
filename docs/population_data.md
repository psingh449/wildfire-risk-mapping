# Population Data (Commit 13)

## Goal
Replace mock population with real Census population.

## Expected File
data/raw/population.csv

## Format
GEOID,population
060070001001,1200
060070001002,800

## Notes
- GEOID must match block_groups.geojson
- If missing → fallback to mock data
