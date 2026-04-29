import numpy as np
import pandas as pd
from data_generators.utils import choice_dist, generate_id

def generate_users(config, seed=42):
    np.random.seed(seed)
    count = config['users']['count']
    dist = config['users']['disability_distribution']
    disability_types = list(dist.keys())
    disability_probs = list(dist.values())

    tiers_dist = config['users']['activity_tier_distribution']
    tier_types = list(tiers_dist.keys())
    tier_probs = list(tiers_dist.values())

    education_levels = config['users']['education_levels']

    rows = []
    for i in range(count):
        user_id = generate_id("user", i)
        disability_type = choice_dist(disability_types, disability_probs)
        activity_tier = choice_dist(tier_types, tier_probs)
        education_level = np.random.choice(education_levels, p=[0.4,0.2,0.3,0.1])
        signup_days_ago = np.random.randint(0, config['timeline_days'])
        accessibility_prefs = derive_accessibility(disability_type)
        rows.append({
            "user_id": user_id,
            "disability_type": disability_type,
            "activity_tier": activity_tier,
            "education_level": education_level,
            "signup_days_ago": signup_days_ago,
            **accessibility_prefs
        })
    return pd.DataFrame(rows)

def derive_accessibility(disability_type):
    # Simple heuristic probabilities
    prefs = {
        "pref_high_contrast": False,
        "pref_screen_reader": False,
        "pref_sign_language": False,
        "pref_tts": False,
        "pref_simplified_mode": False
    }
    if disability_type == "visual":
        prefs["pref_high_contrast"] = np.random.rand() < 0.7
        prefs["pref_screen_reader"] = np.random.rand() < 0.65
        prefs["pref_tts"] = np.random.rand() < 0.5
    if disability_type == "hearing":
        prefs["pref_sign_language"] = np.random.rand() < 0.6
        prefs["pref_simplified_mode"] = np.random.rand() < 0.3
    if disability_type == "motor":
        prefs["pref_tts"] = np.random.rand() < 0.45
        prefs["pref_simplified_mode"] = np.random.rand() < 0.35
    if disability_type == "cognitive":
        prefs["pref_simplified_mode"] = np.random.rand() < 0.7
        prefs["pref_tts"] = np.random.rand() < 0.4
    return prefs