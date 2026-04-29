import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def simulate_recommendation_exposures(config, users_df, courses_df, seed=42):
    np.random.seed(seed)
    exposures_per_user_per_day = config['recommendations']['exposures_per_user_per_day']
    timeline_days = config['timeline_days']
    start_date = datetime.utcnow() - timedelta(days=timeline_days)
    course_ids = courses_df.course_id.values
    top_popularity = max(2, int(len(course_ids) * config['recommendations']['top_popularity_boost_fraction']))
    top_popularity = min(top_popularity, len(course_ids))
    popular_subset = np.random.choice(course_ids, size=top_popularity, replace=False)

    rows = []
    for _, user in users_df.iterrows():
        for day in range(timeline_days):
            date = start_date + timedelta(days=day)
            # Candidate generation (simplistic hybrid)
            num_boosted = min(2, len(popular_subset))
            boosted = np.random.choice(popular_subset, size=num_boosted, replace=False)
            
            remaining_courses = np.setdiff1d(course_ids, boosted)
            num_candidates = min(exposures_per_user_per_day - num_boosted, len(remaining_courses))
            candidates = np.random.choice(remaining_courses, size=num_candidates, replace=False)
            
            rec_list = np.concatenate([candidates, boosted])
            for course_id in rec_list:
                score = np.random.rand() * 0.7 + (0.3 if course_id in boosted else 0)
                clicked = np.random.rand() < config['recommendations']['click_through_rate_target'] * (1 + (score - 0.5))
                rows.append({
                    "user_id": user.user_id,
                    "course_id": course_id,
                    "exposed_at": (date + timedelta(minutes=np.random.randint(0, 1440))).isoformat(),
                    "model_version": "synthetic_ranker_v1",
                    "score": round(score,3),
                    "clicked": int(clicked)
                })
    return pd.DataFrame(rows)