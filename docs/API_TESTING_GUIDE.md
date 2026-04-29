# API Testing Guide

## Server Setup

Start the API server:
```powershell
uvicorn src.recommendation_api:app --reload --port 8000
```

**Base URL:** `http://127.0.0.1:8000`

---

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/recommendations/{user_id}` | Get recommendations |
| POST | `/api/recommendations/{user_id}/dismiss` | Dismiss a course |
| POST | `/api/recommendations/{user_id}/refresh` | Force refresh |
| GET | `/api/recommendations/{user_id}/stats` | Get statistics |
| GET | `/api/docs` | Interactive Swagger UI |

---

## Browser Tests

**Health Check:**
```
http://127.0.0.1:8000/api/health
```

**Get Recommendations:**
```
http://127.0.0.1:8000/api/recommendations/user_0
```

**Interactive Docs:**
```
http://127.0.0.1:8000/api/docs
```

---

## PowerShell Commands

### Using Invoke-RestMethod

```powershell
# Health check
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"

# Get recommendations
$recs = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/recommendations/user_0"
$recs.recommendations | Select-Object rank, title, score, why_recommended

# Dismiss a course
$body = @{ course_id = "course_0" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/recommendations/user_0/dismiss" -Method POST -Body $body -ContentType "application/json"

# Force refresh
$body = @{ force = $true } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/recommendations/user_0/refresh" -Method POST -Body $body -ContentType "application/json"

# Get statistics
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/recommendations/user_0/stats"
```

### Using curl

```powershell
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/recommendations/user_0
curl http://127.0.0.1:8000/api/recommendations/user_0/stats
```

---

## ID Formats

**User IDs:** `user_0`, `user_1`, ... `user_99`  
**Course IDs:** `course_0`, `course_1`, ... `course_49`

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 404 Not Found | Missing `/api/` prefix or wrong ID format | Use `/api/` prefix and correct IDs |
| 422 Validation Error | Invalid request body | Check JSON format |
| Connection Refused | Server not running | Start server with uvicorn |

---

## Response Example

```json
{
  "user_id": "user_0",
  "recommendations": [
    {
      "course_id": "course_42",
      "rank": 1,
      "score": 0.85,
      "title": "Introduction to Python",
      "why_recommended": "Matches your skill level"
    }
  ],
  "total_count": 10
}
```
