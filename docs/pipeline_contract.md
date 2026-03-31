# Pipeline Contract

Each step must:

## Input
- GeoDataFrame with required schema

## Output
- GeoDataFrame with additional columns

## Steps

1. Ingestion
   - Produces raw dataset

2. Preprocessing
   - Cleans and standardizes

3. Feature Engineering
   - Adds hazard, exposure, vulnerability, resilience

4. Model
   - Computes risk_score, EAL

5. Export
   - Outputs GeoJSON

## Rules
- No step should depend on internal logic of another
- Only depend on schema
