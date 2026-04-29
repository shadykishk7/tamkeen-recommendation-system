"""
Generate course embeddings using Cohere embed-multilingual-v3.0
and upsert them into a Qdrant Cloud collection.

Usage:
    python scripts/generate_cohere_embeddings.py
"""

import sys
import os
import json
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

import cohere
import numpy as np
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

# ──────────────────────────── Configuration ────────────────────────────
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
COHERE_MODEL   = "embed-multilingual-v3.0"
EMBED_DIM      = 1024  # embed-multilingual-v3.0 outputs 1024

QDRANT_URL     = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION     = "tamkeen-RS"

# Paths relative to the repo root
REPO_ROOT      = Path(__file__).resolve().parent.parent
COURSES_CSV    = REPO_ROOT / "out_small" / "courses.csv"
CONTENT_ROOT   = REPO_ROOT.parent / "Tamkeen Content" / "project_data" / "courses"
MANIFEST_PATH  = REPO_ROOT.parent / "Tamkeen Content" / "project_data" / "global_manifest.json"
EMBEDDINGS_DIR = REPO_ROOT / "out_small" / "embeddings"


# ──────────────────────────── Helpers ──────────────────────────────────

def load_transcript_text(course_id: str, lang: str = "ar") -> str:
    """Concatenate all unified transcripts for a course into one string."""
    transcript_dir = CONTENT_ROOT / course_id / "transcripts_unified"
    if not transcript_dir.exists():
        return ""
    
    texts = []
    for fp in sorted(transcript_dir.glob(f"*.{lang}.txt")):
        texts.append(fp.read_text(encoding="utf-8").strip())
    return "\n\n".join(texts)


def build_course_documents(courses_df: pd.DataFrame) -> list[dict]:
    """
    Build a rich text document for every course by combining:
      - course metadata (id, category, difficulty, rating)
      - full Arabic transcript text
      - full English transcript text (if available)
    Returns a list of dicts with keys: course_id, text, metadata.
    """
    docs = []
    for _, row in courses_df.iterrows():
        cid = row["course_id"]
        ar_text = load_transcript_text(cid, "ar")
        en_text = load_transcript_text(cid, "en")

        # Build a composite text blob for embedding
        title = row.get('title', cid.replace('_', ' ').title())
        description = row.get('description', '')
        tags = row.get('tags', '[]')
        
        header = (
            f"Course: {title}\n"
            f"Category: {row['category']}\n"
            f"Difficulty: {row['difficulty_level']}/5\n"
            f"Rating: {row['rating']}\n"
            f"Description: {description}\n"
            f"Tags: {tags}\n"
        )
        body_parts = [header]
        if ar_text:
            body_parts.append(f"[Arabic Transcript]\n{ar_text}")
        if en_text:
            body_parts.append(f"[English Transcript]\n{en_text}")

        full_text = "\n\n".join(body_parts)

        docs.append({
            "course_id": cid,
            "text": full_text,
            "metadata": {
                "category": row["category"],
                "difficulty_level": int(row["difficulty_level"]),
                "duration_hours": float(row["duration_hours"]),
                "rating": float(row["rating"]),
                "completion_rate": float(row["completion_rate"]),
                "has_ar_transcript": bool(ar_text),
                "has_en_transcript": bool(en_text),
            },
        })
    return docs


def chunk_text(text: str, max_tokens: int = 450, overlap: int = 50) -> list[str]:
    """
    Naively chunk a long text into segments that fit within the Cohere
    token window.  Uses whitespace word count as a rough proxy for tokens.
    """
    words = text.split()
    if len(words) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + max_tokens
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
    return chunks


# ──────────────────────────── Main ─────────────────────────────────────

def main():
    print("=" * 60)
    print("  Tamkeen RS — Cohere Embeddings + Qdrant Uploader")
    print("=" * 60)

    # ── 1.  Load courses ──────────────────────────────────────────────
    print(f"\n[1/5] Loading courses from {COURSES_CSV} ...")
    courses_df = pd.read_csv(COURSES_CSV)
    print(f"       Found {len(courses_df)} courses: {list(courses_df.course_id)}")

    # ── 2.  Build rich documents ──────────────────────────────────────
    print("\n[2/5] Building composite documents (metadata + transcripts) ...")
    docs = build_course_documents(courses_df)
    for d in docs:
        word_count = len(d["text"].split())
        print(f"       {d['course_id']:25s}  ~{word_count:,} words")

    # ── 3.  Chunk & embed with Cohere ─────────────────────────────────
    print(f"\n[3/5] Embedding with Cohere ({COHERE_MODEL}) ...")
    co = cohere.Client(api_key=COHERE_API_KEY)

    all_points: list[PointStruct] = []
    all_vectors: list[np.ndarray] = []

    for doc in docs:
        chunks = chunk_text(doc["text"])
        print(f"       {doc['course_id']:25s}  -> {len(chunks)} chunk(s)")

        for idx, chunk in enumerate(chunks):
            # Cohere rate-limit guard (trial keys: ~100 calls/min)
            time.sleep(0.6)

            resp = co.embed(
                texts=[chunk],
                model=COHERE_MODEL,
                input_type="search_document",
            )
            vec = resp.embeddings[0]
            all_vectors.append(np.array(vec, dtype=np.float32))

            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc['course_id']}_chunk_{idx}"))
            all_points.append(
                PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "course_id": doc["course_id"],
                        "chunk_index": idx,
                        "chunk_total": len(chunks),
                        "text": chunk[:2000],  # store searchable snippet
                        **doc["metadata"],
                    },
                )
            )

    print(f"\n       Total points to upsert: {len(all_points)}")

    # ── 4.  Save local copy ───────────────────────────────────────────
    print(f"\n[4/5] Saving local embeddings to {EMBEDDINGS_DIR} ...")
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    matrix = np.stack(all_vectors)
    np.save(EMBEDDINGS_DIR / "course_cohere.npy", matrix)

    index_map = {
        str(i): {
            "course_id": p.payload["course_id"],
            "chunk_index": p.payload["chunk_index"],
        }
        for i, p in enumerate(all_points)
    }
    with open(EMBEDDINGS_DIR / "course_cohere_index.json", "w") as f:
        json.dump(index_map, f, indent=2)

    meta = {
        "model": COHERE_MODEL,
        "embedding_dim": EMBED_DIM,
        "num_vectors": len(all_vectors),
        "num_courses": len(docs),
        "generated_at": pd.Timestamp.utcnow().isoformat(),
    }
    with open(EMBEDDINGS_DIR / "course_cohere_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"       Saved {matrix.shape} matrix + metadata.")

    # ── 5.  Upsert to Qdrant Cloud ────────────────────────────────────
    print(f"\n[5/5] Upserting to Qdrant collection '{COLLECTION}' ...")
    qd = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Recreate collection fresh
    qd.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    print(f"       Collection '{COLLECTION}' created ({EMBED_DIM}d, cosine).")

    # Upsert in a single batch (small dataset)
    qd.upsert(collection_name=COLLECTION, points=all_points)
    print(f"       Upserted {len(all_points)} points ✓")

    # Quick sanity check
    info = qd.get_collection(COLLECTION)
    print(f"\n       Collection info:")
    print(f"         vectors_count : {info.vectors_count}")
    print(f"         points_count  : {info.points_count}")

    print("\n" + "=" * 60)
    print("  Done! Embeddings generated & uploaded successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
