
import numpy as np

def generate_uniform(min_val, max_val, size):
    return np.random.uniform(min_val, max_val, size)

def generate_int(min_val, max_val, size):
    return np.random.randint(min_val, max_val, size)
