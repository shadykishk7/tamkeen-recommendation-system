import os
import json
import uuid
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

QDRANT_URL     = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION     = "tamkeen-RS"

REPO_ROOT      = Path(__file__).resolve().parent.parent
OUT_DIR        = REPO_ROOT / "out_small"

EVENT_WEIGHTS = {
    'complete_course': 10.0,
    'enroll_course': 5.0,
    'rate_course': 4.0,
    'complete_lesson': 3.0,
    'video_play': 2.0,
    'click_course': 1.5,
    'view_course': 1.0,
}

def main():
    print("Loading courses and interactions...")
    users_df = pd.read_csv(OUT_DIR / "users.csv")
    courses_df = pd.read_csv(OUT_DIR / "courses.csv")
    
    # Load all interactions
    interactions_dir = OUT_DIR / "interactions"
    interactions_parts = []
    for file in os.listdir(interactions_dir):
        if file.endswith(".csv"):
            interactions_parts.append(pd.read_csv(interactions_dir / file))
    interactions_df = pd.concat(interactions_parts, ignore_index=True) if interactions_parts else pd.DataFrame()
    
    # Load course embeddings (we use these to compute user embeddings locally for speed)
    matrix = np.load(OUT_DIR / "embeddings" / "course_cohere.npy")
    with open(OUT_DIR / "embeddings" / "course_cohere_index.json") as f:
        index_map = json.load(f)
        
    print(f"Loaded {len(users_df)} users, {len(interactions_df)} interactions, and {matrix.shape[0]} course chunks.")

    # We need to map course_id to an average embedding of its chunks
    # Since Qdrant is already populated with chunk vectors, we'll build a fast lookup for course_id -> chunk vectors average
    course_vectors = {}
    for i in range(matrix.shape[0]):
        cid = index_map[str(i)]["course_id"]
        if cid not in course_vectors:
            course_vectors[cid] = []
        course_vectors[cid].append(matrix[i])
        
    for cid in course_vectors:
        # Average the chunks for this course to get a single course vector
        course_vectors[cid] = np.mean(course_vectors[cid], axis=0)

    # Compute User Embeddings
    user_points = []
    for uid in users_df["user_id"]:
        user_interactions = interactions_df[interactions_df["user_id"] == uid]
        if user_interactions.empty:
            continue
            
        course_weights = {}
        for _, row in user_interactions.iterrows():
            cid = row['course_id']
            weight = EVENT_WEIGHTS.get(row['event_type'], 1.0)
            course_weights[cid] = course_weights.get(cid, 0.0) + weight
            
        weighted_sum = np.zeros(matrix.shape[1], dtype=np.float64)
        total_weight = 0.0
        
        for cid, weight in course_weights.items():
            if cid in course_vectors:
                weighted_sum += course_vectors[cid] * weight
                total_weight += weight
                
        if total_weight > 0:
            user_embedding = (weighted_sum / total_weight).tolist()
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user_{uid}"))
            user_points.append(
                PointStruct(
                    id=point_id,
                    vector=user_embedding,
                    payload={
                        "item_type": "user",
                        "user_id": uid
                    }
                )
            )

    print(f"Computed {len(user_points)} valid user embeddings.")
    
    # Upload to Qdrant
    print("Uploading to Qdrant...")
    qd = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)
    
    BATCH_SIZE = 50
    total = len(user_points)
    for start in range(0, total, BATCH_SIZE):
        batch = user_points[start:start + BATCH_SIZE]
        qd.upsert(collection_name=COLLECTION, points=batch)
        end = min(start + BATCH_SIZE, total)
        print(f"  Upserted batch [{start+1}..{end}] / {total}")
        
    info = qd.get_collection(COLLECTION)
    print(f"Done! Qdrant collection '{COLLECTION}' now has {info.points_count} total points (courses + users).")

if __name__ == "__main__":
    main()
