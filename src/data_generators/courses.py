import numpy as np
import pandas as pd
import json
from pathlib import Path
from data_generators.utils import generate_id, truncated_normal, sigmoid

def get_manifest_path():
    return Path(__file__).resolve().parent.parent.parent.parent / "Tamkeen Content" / "project_data" / "global_manifest.json"

def generate_courses(config, seed=42):
    np.random.seed(seed)
    
    with open(get_manifest_path(), 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    difficulty_probs = config['courses']['difficulty_distribution']
    
    rows = []
    for course_id, course_data in manifest.get('courses', {}).items():
        difficulty_level = np.random.choice([1,2,3,4,5], p=difficulty_probs)
        category = course_id
        duration_hours = np.random.gamma(shape=2.0, scale=3.0)
        rating = truncated_normal(4.1, 0.4, 2.5, 5.0)[0]

        accessibility_bonus = np.random.rand() * 0.5
        base = 1.5 - (difficulty_level * 0.25)
        completion_rate = sigmoid(base + accessibility_bonus + np.random.normal(0,0.2))
        
        rows.append({
            "course_id": course_id,
            "category": category,
            "difficulty_level": difficulty_level,
            "duration_hours": round(duration_hours, 2),
            "rating": round(rating, 2),
            "completion_rate": round(completion_rate, 3)
        })
    return pd.DataFrame(rows)

def generate_lessons(courses_df):
    with open(get_manifest_path(), 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    rows = []
    for _, c in courses_df.iterrows():
        lesson_count = manifest.get('courses', {}).get(c.course_id, {}).get('lessons', 10)
        for order in range(1, lesson_count+1):
            lesson_id = f"lesson_{c.course_id}_{order}"
            content_type = np.random.choice(["video","text","interactive"], p=[0.5,0.35,0.15])
            duration_minutes = int(np.clip(np.random.normal(12,5),3,40))
            rows.append({
                "lesson_id": lesson_id,
                "course_id": c.course_id,
                "order_number": order,
                "content_type": content_type,
                "duration_minutes": duration_minutes
            })
    return pd.DataFrame(rows)