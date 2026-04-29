# Recommendation System Integration Plan

This document outlines the strategy for integrating the Tamkeen Recommendation System with the main backend team.

## 1. API Communication Architecture

The Recommendation System (RS) is built as a standalone microservice using **FastAPI**. It should be deployed alongside the main backend.

### Key Endpoints for Backend Integration
*   `GET /api/recommendations/{user_id}`: Fetch personalized courses.
*   `POST /api/recommendations/{user_id}/dismiss`: Report that a user dismissed a suggestion.
*   `POST /api/recommendations/{user_id}/refresh`: Force a re-calculation (e.g., after a major profile change).
*   `GET /api/health`: Monitor service status.

### Frontend Integration
The backend can either:
1.  **Proxy the request**: Backend receives request from Frontend → Backend calls RS → Backend returns response to Frontend. (Recommended for security)
2.  **Direct access**: Frontend calls RS directly. (Requires CORS configuration and public RS endpoint).

## 2. Data Synchronization Strategies

The RS needs up-to-date information on Users, Courses, and Interactions.

### Strategy A: Periodic Sync (Current/Phase 1)
*   **Method**: Backend exports `users.csv`, `courses.csv`, and `interactions.csv` to a shared volume.
*   **Trigger**: A cron job or a webhook call to `/api/recommendations/refresh-data`.
*   **Pros**: Simplest to implement, low impact on main DB.
*   **Cons**: Recommendations aren't real-time.

### Strategy B: Direct Database Access (Phase 2)
*   **Method**: The RS connects directly to a Read-Replica of the main database.
*   **Implementation**: Update `load_recommendation_system` to use SQLAlchemy/Pandas `read_sql` instead of `read_csv`.
*   **Pros**: More accurate data, no manual exports.
*   **Cons**: Requires DB access management.

### Strategy C: Event-Driven / Real-time (Phase 3)
*   **Method**: Every time a user interacts (completes a lesson, enrolls), the Backend sends a small POST request to the RS.
*   **Endpoint**: `POST /api/events` (to be implemented).
*   **Pros**: Real-time personalization.
*   **Cons**: Higher complexity.

## 3. Security & Authentication

Currently, the RS API is open. Before production, we must implement:

*   **API Key Validation**: The backend must include an `X-API-KEY` header in every request.
*   **JWT Verification**: If the RS is exposed to the frontend, it should verify the user's JWT.
*   **Network Isolation**: Run the RS in a private network (VPC) where only the main backend can reach it.

## 4. Deployment Workflow

### Dockerization
The project already contains a `Dockerfile`. The backend team can include it in their `docker-compose.yml`:

```yaml
services:
  recommendation-system:
    build: .
    ports:
      - "8000:8000"
    environment:
      - COHERE_API_KEY=${COHERE_API_KEY}
      - QDRANT_URL=${QDRANT_URL}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
    volumes:
      - ./data:/app/data
```

### CI/CD
*   Every push to `main` should trigger a Docker build.
*   The image is pushed to a Registry (GCR, ECR, Docker Hub).
*   Automatic deployment to the staging environment.

## 5. Next Steps for Integration

1.  **Standardize User IDs**: Ensure the `user_id` format in the RS matches the main DB (UUID vs Integer).
2.  **Implement API Auth**: Add a simple API key check in `recommendation_api.py`.
3.  **Setup Shared Storage**: Decide where the RS will read course data from.
4.  **Swagger Handover**: Provide the backend team with the link to `/api/docs` once deployed.
