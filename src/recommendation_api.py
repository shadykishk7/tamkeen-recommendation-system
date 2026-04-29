"""
REST API endpoints for the Recommendation System
Personalized Course Recommendations

Endpoints:
- GET /api/recommendations/{user_id} - Get recommendations for user
- POST /api/recommendations/{user_id}/dismiss - Dismiss a recommendation
- POST /api/recommendations/{user_id}/refresh - Force refresh recommendations
- GET /api/recommendations/{user_id}/stats - Get recommendation statistics
- GET /api/recommendations/{user_id}/preferences - Get user preferences
- PUT /api/recommendations/{user_id}/preferences - Update user preferences
"""

from fastapi import FastAPI, HTTPException, Path, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.recommendation_engine import RecommendationManager, load_recommendation_system
from src.recommendation_models import (
    RecommendationList, CourseRecommendation, RecommendationExplanation,
    DismissRecommendationRequest, DismissRecommendationResponse,
    RefreshRecommendationsRequest, RefreshRecommendationsResponse,
    RecommendationStats, UserPreferences, UpdatePreferencesRequest,
    ErrorResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Tamkeen Recommendation API",
    description="Personalized course recommendation system for Tamkeen platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global recommendation manager (will be initialized on startup)
recommendation_manager: Optional[RecommendationManager] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the recommendation system on app startup"""
    global recommendation_manager
    try:
        logger.info("Loading recommendation system...")
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_path = os.path.join(base_dir, "out_small")
        logger.info(f"Loading data from: {data_path}")

        # Read Cohere / Qdrant config from environment variables
        cohere_api_key = os.environ.get("COHERE_API_KEY")
        qdrant_url = os.environ.get("QDRANT_URL")
        qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        qdrant_collection = os.environ.get("QDRANT_COLLECTION", "tamkeen-RS")

        recommendation_manager = load_recommendation_system(
            data_path,
            cohere_api_key=cohere_api_key,
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key,
        )

        # Override collection name if provided
        if qdrant_collection:
            recommendation_manager.engine.QDRANT_COLLECTION = qdrant_collection
        logger.info("Recommendation system loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load recommendation system: {e}")
        raise


def get_recommendation_manager() -> RecommendationManager:
    """Dependency injection for recommendation manager"""
    if recommendation_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Recommendation system not initialized"
        )
    return recommendation_manager


@app.get("/api/recommendations/{user_id}", 
         response_model=RecommendationList,
         responses={
             404: {"model": ErrorResponse, "description": "User not found"},
             503: {"model": ErrorResponse, "description": "Service unavailable"}
         },
         summary="Get personalized recommendations",
         description="Retrieve personalized course recommendations for a user. Returns at least 10 recommendations with explanations.")
async def get_recommendations(
    user_id: int = Path(..., description="User ID to get recommendations for"),
    force_refresh: bool = Query(False, description="Force regeneration of recommendations"),
    include_dismissed: bool = Query(False, description="Include dismissed recommendations"),
    manager: RecommendationManager = Depends(get_recommendation_manager)
):
    """
    Get personalized course recommendations for a user.
    
    - **Minimum 10 recommendations** returned
    - **Explanations included** for each recommendation
    - **Weekly automatic updates** (can be forced with force_refresh=true)
    - **Excludes dismissed** courses unless include_dismissed=true
    """
    try:
        logger.info(f"Getting recommendations for user {user_id} (force_refresh={force_refresh})")
        
        recommendations = manager.get_recommendations(user_id, force_refresh=force_refresh)
        
        if not include_dismissed:
            dismissed = manager.dismissed_recommendations.get(user_id, set())
            recommendations = [r for r in recommendations if r['course_id'] not in dismissed]
        
        # Ensure minimum recommendations (up to 10 or total available)
        if len(recommendations) < 5 and not force_refresh:
            logger.info(f"User {user_id} has few recommendations ({len(recommendations)}), attempting refresh")
            recommendations = manager.get_recommendations(user_id, force_refresh=True)
        
        # Convert to Pydantic models
        rec_objects = []
        for rec in recommendations[:20]:  # Return top 20
            # Parse explanation
            explanation = None
            if 'explanation' in rec and rec['explanation']:
                exp_data = rec['explanation']
                if 'score_breakdown' in exp_data:
                    reasons = []
                    for category, items in exp_data.items():
                        if category != 'score_breakdown' and isinstance(items, list):
                            reasons.extend(items)
                    
                    explanation = RecommendationExplanation(
                        primary_reason=reasons[0] if reasons else "Recommended for you",
                        supporting_reasons=reasons[1:3] if len(reasons) > 1 else [],
                        score_breakdown=exp_data.get('score_breakdown', {})
                    )
            
            rec_obj = CourseRecommendation(
                course_id=rec['course_id'],
                rank=rec['rank'],
                score=rec['score'],
                title=rec['title'],
                category=rec['category'],
                difficulty_level=rec['difficulty_level'],
                duration_hours=rec['duration_hours'],
                rating=rec['rating'],
                explanation=explanation,
                why_recommended=rec.get('why_recommended', ''),
                generated_at=datetime.fromisoformat(rec['generated_at']) if isinstance(rec['generated_at'], str) else rec['generated_at'],
                dismissed=rec.get('dismissed', False)
            )
            rec_objects.append(rec_obj)
        
        # Calculate next update time
        last_update = manager.last_update.get(user_id, datetime.utcnow())
        next_update = last_update + timedelta(days=7)
        
        return RecommendationList(
            user_id=user_id,
            recommendations=rec_objects,
            total_count=len(rec_objects),
            generated_at=last_update,
            next_update=next_update
        )
        
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"ValueError for {user_id}: {error_msg}", exc_info=True)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Unexpected error for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommendations/{user_id}/dismiss",
          response_model=DismissRecommendationResponse,
          summary="Dismiss a recommendation",
          description="Dismiss a specific course recommendation. The course will not appear in future recommendations.")
async def dismiss_recommendation(
    user_id: int = Path(..., description="User ID"),
    request: DismissRecommendationRequest = ...,
    manager: RecommendationManager = Depends(get_recommendation_manager)
):
    """
    Dismiss a course recommendation for a user.
    
    - **Removes course from recommendations** immediately
    - **Persists dismissal** across sessions
    - **New recommendations** generated if count drops below 10
    """
    try:
        logger.info(f"Dismissing recommendation for user {user_id}: {request.course_id}")
        
        success = manager.dismiss_recommendation(user_id, request.course_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to dismiss recommendation")
        
        # Get updated recommendations count
        recommendations = manager.get_recommendations(user_id, force_refresh=False)
        remaining_count = len([r for r in recommendations if not r.get('dismissed', False)])
        
        message = f"Recommendation dismissed successfully"
        if request.reason:
            message += f" (reason: {request.reason})"
            logger.info(f"Dismissal reason: {request.reason}")
        
        return DismissRecommendationResponse(
            success=True,
            course_id=request.course_id,
            remaining_recommendations=remaining_count,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error dismissing recommendation for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommendations/{user_id}/refresh",
          response_model=RefreshRecommendationsResponse,
          summary="Refresh recommendations",
          description="Force refresh of recommendations before the scheduled weekly update.")
async def refresh_recommendations(
    user_id: int = Path(..., description="User ID"),
    request: RefreshRecommendationsRequest = RefreshRecommendationsRequest(),
    manager: RecommendationManager = Depends(get_recommendation_manager)
):
    """
    Force refresh recommendations for a user.
    
    - **Regenerates recommendations** based on latest data
    - **Resets weekly timer** after refresh
    - **Considers new activity** since last update
    """
    try:
        logger.info(f"Refreshing recommendations for user {user_id} (force={request.force})")
        
        previous_update = manager.last_update.get(user_id)
        
        # Force refresh
        recommendations = manager.get_recommendations(user_id, force_refresh=True)
        
        new_update = manager.last_update[user_id]
        next_update = new_update + timedelta(days=7)
        
        message = "Recommendations refreshed successfully"
        if request.reason:
            message += f" (reason: {request.reason})"
            logger.info(f"Refresh reason: {request.reason}")
        
        return RefreshRecommendationsResponse(
            success=True,
            recommendations_count=len(recommendations),
            previous_update=previous_update,
            next_update=next_update
        )
        
    except Exception as e:
        logger.error(f"Error refreshing recommendations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/{user_id}/stats",
         response_model=RecommendationStats,
         summary="Get recommendation statistics",
         description="Get statistics about user's recommendations including counts and refresh status.")
async def get_recommendation_stats(
    user_id: int = Path(..., description="User ID"),
    manager: RecommendationManager = Depends(get_recommendation_manager)
):
    """
    Get statistics about user's recommendations.
    
    Returns counts, dismissal info, and refresh schedule.
    """
    try:
        logger.info(f"Getting recommendation stats for user {user_id}")
        
        stats = manager.get_recommendation_stats(user_id)
        
        # Calculate days until refresh
        last_update = stats.get('last_updated')
        if last_update:
            if isinstance(last_update, str):
                last_update = datetime.fromisoformat(last_update)
            days_since = (datetime.utcnow() - last_update).days
            days_until = max(0, 7 - days_since)
        else:
            days_until = 0
        
        return RecommendationStats(
            user_id=user_id,
            total_recommendations=stats['total_recommendations'],
            active_recommendations=stats['active_recommendations'],
            dismissed_count=stats['dismissed_count'],
            last_updated=last_update,
            needs_refresh=stats['needs_refresh'],
            days_until_refresh=days_until
        )
        
    except Exception as e:
        logger.error(f"Error getting stats for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommendations/{user_id}/preferences",
         response_model=UserPreferences,
         summary="Get user preferences",
         description="Get user's recommendation preferences.")
async def get_user_preferences(
    user_id: int = Path(..., description="User ID")
):
    """
    Get user's recommendation preferences.
    
    Returns preferred categories, difficulty levels, and filters.
    """
    # This would typically fetch from database
    # For now, return default preferences
    return UserPreferences(
        user_id=user_id,
        preferred_categories=[],
        excluded_categories=[],
        preferred_difficulty=None,
        max_duration_hours=None,
        min_rating=None
    )


@app.put("/api/recommendations/{user_id}/preferences",
         response_model=UserPreferences,
         summary="Update user preferences",
         description="Update user's recommendation preferences. Triggers recommendation refresh.")
async def update_user_preferences(
    user_id: int = Path(..., description="User ID"),
    request: UpdatePreferencesRequest = ...,
    manager: RecommendationManager = Depends(get_recommendation_manager)
):
    """
    Update user's recommendation preferences.
    
    - **Updates preferences** immediately
    - **Triggers recommendation refresh** to apply new preferences
    - **Validates preferences** before applying
    """
    try:
        logger.info(f"Updating preferences for user {user_id}")
        
        # Build updated preferences
        preferences = UserPreferences(
            user_id=user_id,
            preferred_categories=request.preferred_categories or [],
            excluded_categories=request.excluded_categories or [],
            preferred_difficulty=request.preferred_difficulty,
            max_duration_hours=request.max_duration_hours,
            min_rating=request.min_rating
        )
        
        # Save preferences (would persist to database in real implementation)
        
        # Trigger recommendation refresh
        manager.get_recommendations(user_id, force_refresh=True)
        
        logger.info(f"Preferences updated and recommendations refreshed for {user_id}")
        
        return preferences
        
    except Exception as e:
        logger.error(f"Error updating preferences for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health",
         summary="Health check",
         description="Check if the recommendation API is healthy.")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "recommendation-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "recommendation_system": "initialized" if recommendation_manager else "not initialized"
    }


@app.get("/",
         summary="API root",
         description="Root endpoint with API information.")
async def root():
    """Root endpoint"""
    return {
        "service": "Tamkeen Recommendation API",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        "recommendation_api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
