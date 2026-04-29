import numpy as np
import pandas as pd
from datetime import datetime, timedelta

EVENT_TYPES = [
    "view_course","click_course","enroll_course","video_play",
    "complete_lesson","complete_course","rate_course"
]

def simulate_interactions(config, users_df, courses_df, lessons_df, seed=42):
    np.random.seed(seed)
    target_total = config['interactions']['target_total']
    timeline_days = config['timeline_days']
    start_date = datetime.utcnow() - timedelta(days=timeline_days)
    events = []
    # Precompute user accessible preferences for potential weighting
    course_ids = courses_df.course_id.values

    # Activity intensity by tier
    tier_sessions = config['interactions']['session_lambda_by_tier']

    # Estimate sessions to approximate target_total events
    for _, user in users_df.iterrows():
        sessions_per_day = tier_sessions[user.activity_tier]
        for day in range(timeline_days):
            if np.random.rand() < min(1, sessions_per_day):  # probability of at least one session
                date = start_date + timedelta(days=day)
                # number of actions in session
                actions = np.random.randint(3, 15)
                chosen_course = np.random.choice(course_ids)
                course_lessons = lessons_df[lessons_df.course_id == chosen_course]
                for a in range(actions):
                    etype = np.random.choice(EVENT_TYPES, p=[0.25,0.15,0.05,0.25,0.15,0.02,0.13])
                    lesson_id = None
                    value = None
                    if etype in ["video_play","complete_lesson"]:
                        if not course_lessons.empty:
                            lesson_id = np.random.choice(course_lessons.lesson_id.values)
                            if etype == "video_play":
                                value = {"duration_seconds": int(np.clip(np.random.gamma(2.5, 180),60,1800))}
                    if etype == "rate_course":
                        value = {"rating": int(np.clip(np.random.normal(4.1,0.6),1,5))}
                    events.append({
                        "user_id": user.user_id,
                        "course_id": chosen_course,
                        "lesson_id": lesson_id,
                        "event_type": etype,
                        "event_ts": (date + timedelta(minutes=np.random.randint(0, 1440))).isoformat(),
                        "value": value
                    })

    df = pd.DataFrame(events)
    # Downsample if we exceeded target
    if len(df) > target_total:
        df = df.sample(target_total, random_state=seed).reset_index(drop=True)
    return df