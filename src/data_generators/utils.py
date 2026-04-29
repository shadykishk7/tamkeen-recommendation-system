import random
import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(0)

def choice_dist(values, probs):
    return np.random.choice(values, p=probs)

def truncated_normal(mean, std, low, high, size=1):
    vals = np.random.normal(mean, std, size)
    return np.clip(vals, low, high)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def time_decay(days, lam=0.02):
    return np.exp(-lam * days)

def generate_id(prefix, idx):
    return f"{prefix}_{idx}"

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    Faker.seed(seed)