import requests
import pandas as pd

# -------------------------------
# 1. Config
# -------------------------------
URL = "https://api.census.gov/data/2022/acs/acs5"

PARAMS = {
    "get": "NAME,B01003_001E",
    "for": "block group:*",
    "in": "state:06 county:007"  # California, Butte County
}

OUTPUT_PATH = "data/raw/population.csv"

# -------------------------------
# 2. Fetch Data
# -------------------------------
print("Fetching population data from Census API...")

response = requests.get(URL, params=PARAMS)

if response.status_code != 200:
    raise RuntimeError(f"API request failed: {response.status_code}")

data = response.json()

# -------------------------------
# 3. Convert to DataFrame
# -------------------------------
df = pd.DataFrame(data[1:], columns=data[0])

# -------------------------------
# 4. Clean + Normalize Fields
# -------------------------------

# Ensure correct types + padding
df["state"] = df["state"].astype(str).str.zfill(2)
df["county"] = df["county"].astype(str).str.zfill(3)
df["tract"] = df["tract"].astype(str).str.zfill(6)
df["block group"] = df["block group"].astype(str).str.zfill(1)

# Build GEOID (CRITICAL)
df["GEOID"] = (
    df["state"] +
    df["county"] +
    df["tract"] +
    df["block group"]
)

# -------------------------------
# 5. Clean Population Column
# -------------------------------
df["population"] = pd.to_numeric(df["B01003_001E"], errors="coerce").fillna(0).astype(int)

# -------------------------------
# 6. Final Selection
# -------------------------------
df = df[["GEOID", "population"]]

# -------------------------------
# 7. Validation (VERY IMPORTANT)
# -------------------------------

print("\nValidation checks:")

# Check GEOID length
invalid_geoids = df[df["GEOID"].str.len() != 12]
print(f"Invalid GEOIDs (not 12 digits): {len(invalid_geoids)}")

# Check duplicates
duplicates = df["GEOID"].duplicated().sum()
print(f"Duplicate GEOIDs: {duplicates}")

# Check population stats
print(f"Population min: {df['population'].min()}")
print(f"Population max: {df['population'].max()}")

# Sample preview
print("\nSample data:")
print(df.head())

# -------------------------------
# 8. Save
# -------------------------------
df.to_csv(OUTPUT_PATH, index=False)

print(f"\nSaved {len(df)} rows to {OUTPUT_PATH}")