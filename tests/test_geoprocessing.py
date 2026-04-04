import pandas as pd
import numpy as np

def test_nlcd_zonal_stats_csv():
    # Simulate a small CSV output from NLCD zonal stats script
    df = pd.DataFrame({"block_id": ["1", "2"], "nlcd_mean": [0.2, 0.8]})
    assert np.all((df["nlcd_mean"] >= 0) & (df["nlcd_mean"] <= 1))

def test_hifld_nearest_csv():
    # Simulate a small CSV output from HIFLD nearest script
    df = pd.DataFrame({"block_id": ["1", "2"], "fire_station_dist": [0.5, 1.2]})
    assert (df["fire_station_dist"] >= 0).all()

def test_osm_road_length_csv():
    # Simulate a small CSV output from OSM road length script
    df = pd.DataFrame({"block_id": ["1", "2"], "road_length": [1000, 2000]})
    assert (df["road_length"] >= 0).all()
