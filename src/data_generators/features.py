import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from collections import defaultdict

def build_user_features(users_df, interactions_df, config):
    version = config['features']['version']
    # Aggregate completions & session stats
    completions = interactions_df[interactions_df.event_type=="complete_course"].groupby("user_id").course_id.nunique()
    enrolls = interactions_df[interactions_df.event_type=="enroll_course"].groupby("user_id").course_id.nunique()
    durations = interactions_df[interactions_df.event_type=="video_play"].groupby("user_id").value.apply(lambda vs: sum(v['duration_seconds'] for v in vs if v))
    feature_rows = []
    for _, user in users_df.iterrows():
        uid = user.user_id
        feature_rows.append({
            "user_id": uid,
            "courses_completed": int(completions.get(uid,0)),
            "courses_enrolled": int(enrolls.get(uid,0)),
            "total_video_seconds": int(durations.get(uid,0)),
            "activity_tier": user.activity_tier,
            "disability_type": user.disability_type,
            "feature_version": version,
            "data_origin": "synthetic_v1"
        })
    return pd.DataFrame(feature_rows)

def build_course_features(courses_df, interactions_df, config):
    version = config['features']['version']
    enroll_counts = interactions_df[interactions_df.event_type=="enroll_course"].groupby("course_id").user_id.nunique()
    complete_counts = interactions_df[interactions_df.event_type=="complete_course"].groupby("course_id").user_id.nunique()
    feature_rows = []
    for _, c in courses_df.iterrows():
        cid = c.course_id
        feature_rows.append({
            "course_id": cid,
            "difficulty_level": c.difficulty_level,
            "enroll_count": int(enroll_counts.get(cid,0)),
            "complete_count": int(complete_counts.get(cid,0)),
            "rating": c.rating,
            "feature_version": version,
            "data_origin": "synthetic_v1"
        })
    return pd.DataFrame(feature_rows)

def export_parquet(df, path):
    table = pa.Table.from_pandas(df)
    pq.write_table(table, path)