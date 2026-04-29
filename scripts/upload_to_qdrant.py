"""
Upload locally saved Cohere embeddings to Qdrant Cloud.
Batched upserts with extended timeout to avoid write timeouts.
"""
import json
import uuid
import numpy as np
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

QDRANT_URL     = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION     = "tamkeen-RS"
EMBED_DIM      = 1024
BATCH_SIZE     = 50

REPO_ROOT      = Path(__file__).resolve().parent.parent
EMBEDDINGS_DIR = REPO_ROOT / "out_small" / "embeddings"

def main():
    print("Loading local embeddings ...")
    matrix = np.load(EMBEDDINGS_DIR / "course_cohere.npy")
    with open(EMBEDDINGS_DIR / "course_cohere_index.json") as f:
        index_map = json.load(f)
    
    print(f"  Loaded {matrix.shape[0]} vectors of dim {matrix.shape[1]}")

    # Rebuild points
    points = []
    for i in range(matrix.shape[0]):
        info = index_map[str(i)]
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{info['course_id']}_chunk_{info['chunk_index']}"))
        points.append(PointStruct(
            id=point_id,
            vector=matrix[i].tolist(),
            payload={
                "item_type": "course",
                "course_id": info["course_id"],
                "chunk_index": info["chunk_index"],
            },
        ))

    print(f"  Built {len(points)} points.")

    # Connect with extended timeout
    qd = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)

    # Create collection if it doesn't exist
    if not qd.collection_exists(COLLECTION):
        qd.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        print(f"  Collection '{COLLECTION}' created.")
    else:
        # Delete and recreate for a clean slate
        qd.delete_collection(COLLECTION)
        qd.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        print(f"  Collection '{COLLECTION}' recreated.")

    # Batch upsert
    total = len(points)
    for start in range(0, total, BATCH_SIZE):
        batch = points[start:start + BATCH_SIZE]
        qd.upsert(collection_name=COLLECTION, points=batch)
        end = min(start + BATCH_SIZE, total)
        print(f"  Upserted batch [{start+1}..{end}] / {total}")

    # Verify
    info = qd.get_collection(COLLECTION)
    print(f"\n  Collection '{COLLECTION}' stats:")
    print(f"    vectors_count : {info.vectors_count}")
    print(f"    points_count  : {info.points_count}")
    print("\n  Done!")

if __name__ == "__main__":
    main()
