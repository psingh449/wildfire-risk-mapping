import os
import pandas as pd
from src.utils.real_data import fetch_census_population, fetch_census_housing
from src.utils.config import REAL_DATA_DIR

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def refresh_census_population():
    print("Refreshing Census population data...")
    pop_dict = fetch_census_population([])  # Fetch all for Butte County
    df = pd.DataFrame(list(pop_dict.items()), columns=["GEOID", "population"])
    ensure_dir(REAL_DATA_DIR)
    df.to_csv(os.path.join(REAL_DATA_DIR, "census_population.csv"), index=False)
    print(f"Saved to {os.path.join(REAL_DATA_DIR, 'census_population.csv')}")

def refresh_census_housing():
    print("Refreshing Census housing data...")
    housing_dict = fetch_census_housing([])
    df = pd.DataFrame(list(housing_dict.items()), columns=["GEOID", "housing_units"])
    ensure_dir(REAL_DATA_DIR)
    df.to_csv(os.path.join(REAL_DATA_DIR, "census_housing.csv"), index=False)
    print(f"Saved to {os.path.join(REAL_DATA_DIR, 'census_housing.csv')}")

def main():
    refresh_census_population()
    refresh_census_housing()
    print("All real data refreshed.")

if __name__ == "__main__":
    main()
