import argparse
import yaml
import os
import json
from tqdm import tqdm
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from data_generators.users import generate_users
from data_generators.courses import generate_courses, generate_lessons
from data_generators.assessments import generate_assessments
from data_generators.interactions import simulate_interactions
from data_generators.recommendations import simulate_recommendation_exposures
from data_generators.features import build_user_features, build_course_features, export_parquet
from data_generators.utils import set_seed

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def ensure_dirs(base):
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base,"interactions"), exist_ok=True)
    os.makedirs(os.path.join(base,"recommendation_exposures"), exist_ok=True)
    os.makedirs(os.path.join(base,"feature_store"), exist_ok=True)
    os.makedirs(os.path.join(base,"embeddings"), exist_ok=True)

def partition_by_date(df, timestamp_col, out_dir, prefix):
    df['__date'] = pd.to_datetime(df[timestamp_col]).dt.date
    for date, part in df.groupby('__date'):
        part.drop(columns=['__date']).to_csv(os.path.join(out_dir,f"{prefix}-{date}.csv"), index=False)

def validate(users_df, courses_df, interactions_df, recs_df):
    report = {}
    report['users_count'] = len(users_df)
    report['courses_count'] = len(courses_df)
    report['interactions_count'] = len(interactions_df)
    report['recommendation_exposures_count'] = len(recs_df)
    report['null_rates'] = interactions_df.isnull().mean().to_dict()
    # Funnel approximation
    views = interactions_df[interactions_df.event_type=="view_course"].course_id.count()
    enrolls = interactions_df[interactions_df.event_type=="enroll_course"].course_id.count()
    completes = interactions_df[interactions_df.event_type=="complete_course"].course_id.count()
    report['funnel'] = {
        "views": int(views),
        "enrolls": int(enrolls),
        "completes": int(completes),
        "view_to_enroll_rate": round(enrolls / views, 4) if views else 0,
        "enroll_to_complete_rate": round(completes / enrolls, 4) if enrolls else 0
    }
    # CTR
    ctr = recs_df.clicked.mean() if len(recs_df) else 0
    report['recommendation_ctr'] = round(ctr,4)
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-forum", action="store_true")
    parser.add_argument("--embedding-stub", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.seed is not None:
        config['seed'] = args.seed
    seed = config.get('seed', 42)
    set_seed(seed)

    ensure_dirs(args.out)
    print(f"[INFO] Generating synthetic data with seed={seed}")

    users_df = generate_users(config, seed)
    courses_df = generate_courses(config, seed)
    lessons_df = generate_lessons(courses_df)
    assessments_df, questions_df = generate_assessments(config, courses_df, seed)

    print("[INFO] Simulating interactions...")
    interactions_df = simulate_interactions(config, users_df, courses_df, lessons_df, seed)

    print("[INFO] Simulating recommendation exposures...")
    recs_df = simulate_recommendation_exposures(config, users_df, courses_df, seed)

    print("[INFO] Building feature store snapshots...")
    user_features_df = build_user_features(users_df, interactions_df, config)
    course_features_df = build_course_features(courses_df, interactions_df, config)

    # Export core CSVs
    users_df.to_csv(os.path.join(args.out,"users.csv"), index=False)
    courses_df.to_csv(os.path.join(args.out,"courses.csv"), index=False)
    lessons_df.to_csv(os.path.join(args.out,"lessons.csv"), index=False)
    assessments_df.to_csv(os.path.join(args.out,"assessments.csv"), index=False)
    questions_df.to_csv(os.path.join(args.out,"questions.csv"), index=False)

    if config.get("output_partitioning", True):
        partition_by_date(interactions_df, "event_ts", os.path.join(args.out,"interactions"), "part")
        partition_by_date(recs_df, "exposed_at", os.path.join(args.out,"recommendation_exposures"), "part")
    else:
        interactions_df.to_csv(os.path.join(args.out,"interactions.csv"), index=False)
        recs_df.to_csv(os.path.join(args.out,"recommendation_exposures.csv"), index=False)

    export_parquet(user_features_df, os.path.join(args.out,"feature_store","users.parquet"))
    export_parquet(course_features_df, os.path.join(args.out,"feature_store","courses.parquet"))

    # Stub embeddings (random vectors) if requested
    if config['embeddings']['model'] == 'stub' or args.embedding_stub:
        emb_dim = config['embeddings']['reduced_dim']
        course_vectors = np.random.normal(0,1,(len(courses_df), emb_dim))
        np.save(os.path.join(args.out,"embeddings","course_text.npy"), course_vectors)
    else:
        # Placeholder: integrate SentenceTransformer here
        pass

    # Validation
    val_report = validate(users_df, courses_df, interactions_df, recs_df)
    with open(os.path.join(args.out,"validation_report.json"), "w") as f:
        json.dump(val_report, f, indent=2)

    print("[INFO] Validation Report:")
    print(json.dumps(val_report, indent=2))
    print("[INFO] Done.")

if __name__ == "__main__":
    main()