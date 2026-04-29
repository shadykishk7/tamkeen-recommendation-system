import json
import uuid
from qdrant_client import QdrantClient

QDRANT_URL     = "https://62566cb2-b215-4f6e-8129-4fe54c24f102.eu-west-2-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6ZGU0ZGVmMmUtZmQ0My00NDMzLWFjYjMtNjNkOGU5MzRmY2YxIn0.sC0tfHzs5GWcaHugPzNzHaSkiqZ-To5qI7jG5ssUc74"
COLLECTION     = "tamkeen-RS"

try:
    qd = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)
    info = qd.get_collection(COLLECTION)
    print(f"Collection '{COLLECTION}' stats:")
    print(f"  points_count: {info.points_count}")
    print(f"  vectors_count: {info.vectors_count}")
    print(f"  status: {info.status}")
except Exception as e:
    print(f"Error checking Qdrant: {e}")
