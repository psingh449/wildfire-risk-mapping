import pandas as pd

def load_population(path="data/raw/population.csv"):
    try:
        df = pd.read_csv(path, dtype={"GEOID": str})
        return df
    except Exception:
        return None
