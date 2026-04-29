# Tamkeen - Personalized Course Recommendation System

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![React](https://img.shields.io/badge/React-18+-blue)
![Tests](https://img.shields.io/badge/Tests-11%20Passing-success)

**AI-Powered Personalized Course Recommendations for Inclusive Learning**

*Part of the Tamkeen Graduation Project - January 2026*

---

## About

Personalized Course Recommendation System for the Tamkeen inclusive e-learning platform. The system provides intelligent, accessibility-aware course suggestions based on user profiles, learning history, and individual needs.

---

## Features

- **7-Factor Hybrid Algorithm** - Combines collaborative filtering, content-based, and accessibility-aware scoring
- **Real ML Embeddings** - SentenceTransformers (all-MiniLM-L6-v2) with 384-dimensional vectors
- **Explainable AI** - Each recommendation includes reasoning for transparency
- **Accessibility-First Design** - Prioritizes courses matching user disability needs
- **RESTful API** - FastAPI with automatic documentation
- **React Dashboard** - Ready-to-integrate frontend component

---

## Project Structure

```
Recommendation System/
├── src/                    # Source code
│   ├── recommendation_engine.py    # Core algorithm
│   ├── recommendation_api.py       # FastAPI server
│   ├── recommendation_models.py    # Data models
│   ├── embedding_service.py        # ML embeddings
│   └── data_generators_*.py        # Synthetic data generation
├── tests/                  # Unit and integration tests
├── frontend/               # React dashboard component
├── config/                 # Configuration files
├── scripts/                # Utility scripts
├── docs/                   # Documentation
└── out_small/              # Generated synthetic data
```

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Generate embeddings (first time only)
python scripts/generate_embeddings.py --data out_small --output out_small/embeddings
```

### Run API Server

```bash
uvicorn src.recommendation_api:app --reload --port 8000
```

### Test the API

```bash
# Get recommendations
curl http://localhost:8000/api/recommendations/user_0

# View interactive docs
# Open http://localhost:8000/api/docs in browser
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/recommendations/{user_id}` | Get personalized recommendations |
| POST | `/api/recommendations/{user_id}/dismiss` | Dismiss a course |
| POST | `/api/recommendations/{user_id}/refresh` | Force refresh recommendations |
| GET | `/api/recommendations/{user_id}/stats` | Get recommendation statistics |
| GET | `/api/docs` | Interactive API documentation |

---

## Algorithm

The recommendation engine uses a 7-factor weighted hybrid approach:

| Factor | Weight | Description |
|--------|--------|-------------|
| Skill Match | 22% | Course difficulty aligns with user education |
| Category Interest | 18% | Based on historical engagement |
| Collaborative | 18% | Similar users' preferences |
| Accessibility | 13% | Matches user disability needs |
| Quality | 13% | Course ratings and completion rates |
| Semantic | 10% | ML embedding similarity |
| Engagement | 6% | Predicted completion likelihood |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Expected: 11/11 passing
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [SUMMARY.md](docs/SUMMARY.md) | Implementation overview |
| [IMPLEMENTATION_DOCS.md](docs/IMPLEMENTATION_DOCS.md) | Technical documentation |
| [API_TESTING_GUIDE.md](docs/API_TESTING_GUIDE.md) | API testing guide |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.9+, FastAPI |
| ML | SentenceTransformers, NumPy |
| Data | Pandas, Parquet |
| Frontend | React 18, TypeScript |
| Testing | Pytest |

---

## 👤 Author

**Shady Kishk**

- GitHub: [@ShadyKishk77](https://github.com/ShadyKishk77)
- LinkedIn: [Shady Kishk](https://linkedin.com/in/shady-kishk)
- Email: shadykishk77@gmail.com

---

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

*Tamkeen Graduation Project - January 2026*
