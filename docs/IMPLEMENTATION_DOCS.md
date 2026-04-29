# Implementation Documentation

**Version:** 1.0.0  
**Last Updated:** January 2026

---

## 1. System Architecture

```
+------------------+     +------------------+     +------------------+
|    Frontend      |     |    API Layer     |     |  Engine Layer    |
|  React/TypeScript| --> |     FastAPI      | --> |  Python/NumPy    |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
                                                  +------------------+
                                                  |   ML Layer       |
                                                  | SentenceTransform|
                                                  +------------------+
```

---

## 2. Recommendation Algorithm

### 2.1 Hybrid Approach

The system uses a 7-factor weighted algorithm:

**Skill-Difficulty Alignment (22%)**
- Maps user education level to course difficulty
- Education levels: high_school, bachelor, master, phd
- Perfect match = 1.0, partial match = 0.7, mismatch = 0.3

**Category Interest (18%)**
- Analyzes user's historical engagement by category
- Calculates category affinity scores from interactions

**Collaborative Filtering (18%)**
- Finds similar users based on interaction patterns
- Recommends courses liked by similar users

**Accessibility Match (13%)**
- Prioritizes courses with appropriate accessibility features
- Considers user's disability type (visual, hearing, motor, cognitive)

**Quality Signals (13%)**
- Course ratings: 60% of quality score
- Completion rates: 40% of quality score

**Semantic Similarity (10%)**
- ML embeddings using SentenceTransformers (all-MiniLM-L6-v2)
- 384-dimensional vectors with cosine similarity

**Engagement Prediction (6%)**
- Predicts likelihood of course completion
- Based on user behavior patterns

### 2.2 Score Calculation

```python
FINAL_SCORE = (
    skill_match * 0.22 +
    category_interest * 0.18 +
    collaborative * 0.18 +
    accessibility * 0.13 +
    quality * 0.13 +
    semantic * 0.10 +
    engagement * 0.06
)
```

---

## 3. API Design

### 3.1 Endpoints

**GET /api/recommendations/{user_id}**

Returns personalized recommendations.

Response:
```json
{
  "user_id": "user_0",
  "recommendations": [
    {
      "course_id": "course_42",
      "rank": 1,
      "score": 0.87,
      "title": "Introduction to Python",
      "category": "programming",
      "why_recommended": "Matches your skill level"
    }
  ],
  "total_count": 15
}
```

**POST /api/recommendations/{user_id}/dismiss**

Dismisses a recommendation.

**POST /api/recommendations/{user_id}/refresh**

Forces recommendation refresh.

**GET /api/recommendations/{user_id}/stats**

Returns recommendation statistics.

---

## 4. Data Models

### 4.1 User Profile

```python
class User:
    user_id: str
    education_level: str  # high_school, bachelor, master, phd
    disability_type: Optional[str]  # visual, hearing, motor, cognitive
    interests: List[str]
```

### 4.2 Course

```python
class Course:
    course_id: str
    title: str
    category: str
    difficulty: str  # beginner, intermediate, advanced
    accessibility_features: List[str]
```

### 4.3 Recommendation

```python
class Recommendation:
    course_id: str
    rank: int
    score: float
    title: str
    why_recommended: str
    is_dismissed: bool
```

---

## 5. ML Embeddings

### 5.1 Model Details

- **Model:** all-MiniLM-L6-v2
- **Framework:** SentenceTransformers
- **Dimensions:** 384
- **Input:** Course title + category + description

### 5.2 Storage

- **Vectors:** NumPy array (.npy)
- **Index:** JSON mapping course_id to array index
- **Metadata:** JSON with generation timestamp

---

## 6. Frontend Component

### 6.1 RecommendationsDashboard.tsx

React component features:
- Fetches recommendations from API
- Displays course cards with scores
- Dismiss button per card
- Refresh button
- Loading and error states
- Responsive grid layout

### 6.2 Props

```typescript
interface Props {
  userId: string;
  apiBaseUrl: string;
}
```

---

## 7. Testing

Run tests:
```bash
pytest tests/ -v
```

Test coverage:
- Engine recommendation generation
- Score computation ranges
- API endpoint responses
- Embedding dimension validation

---

**Status:** Complete
