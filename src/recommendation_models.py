"""
Data models and schemas for the recommendation system.
Includes Pydantic models for API validation and database schemas.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class DifficultyLevel(int, Enum):
    """Course difficulty levels (3 levels)"""
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3


class EducationLevel(str, Enum):
    """Education levels (aligned with Prisma EducationLevel enum)"""
    NO_FORMAL = "NO_FORMAL"
    PRIMARY = "PRIMARY"
    LOWER_SECONDARY = "LOWER_SECONDARY"
    UPPER_SECONDARY = "UPPER_SECONDARY"
    SHORT_CYCLE_TERTIARY = "SHORT_CYCLE_TERTIARY"
    BACHELOR = "BACHELOR"
    MASTER = "MASTER"
    DOCTORATE = "DOCTORATE"


class CourseCategory(str, Enum):
    """Available course categories"""
    PROGRAMMING = "programming"
    SOFT_SKILLS = "soft_skills"
    BUSINESS = "business"
    ACCESSIBILITY = "accessibility"
    DESIGN = "design"
    DATA = "data"
    LANGUAGE = "language"
    # Tamkeen-specific categories (real courses)
    PYTHON = "python"
    DIGITAL_MARKETING = "digital_marketing"
    EMBEDDED = "embedded"
    FREELANCING = "freelancing_khamsat"
    IOT = "iot"
    TESTING = "testing"
    UX = "ux"
    # Mock course categories
    QA = "qa"
    HARDWARE = "hardware"
    MARKETING = "marketing"


class DisabilityType(str, Enum):
    """Disability types (aligned with Prisma DisabilityTypes enum)"""
    DYSLEXIA = "Dyslexia"
    ADHD = "ADHD"


class ActivityTier(str, Enum):
    """User activity levels"""
    DORMANT = "dormant"
    CASUAL = "casual"
    REGULAR = "regular"
    POWER = "power"


class ExplanationComponent(BaseModel):
    """Component of recommendation explanation"""
    category: str = Field(..., description="Explanation category (skill_match, collaborative, etc.)")
    reason: str = Field(..., description="Human-readable reason")
    weight: float = Field(..., ge=0.0, le=1.0, description="Contribution to total score")


class RecommendationExplanation(BaseModel):
    """Detailed explanation of why a course was recommended"""
    primary_reason: str = Field(..., description="Main reason for recommendation")
    supporting_reasons: List[str] = Field(default_factory=list, description="Additional supporting reasons")
    score_breakdown: Dict[str, float] = Field(..., description="Component scores")
    
    class Config:
        json_schema_extra = {
            "example": {
                "primary_reason": "Matches your bachelor education level",
                "supporting_reasons": [
                    "You've shown interest in programming courses",
                    "Users with similar interests enjoyed this course"
                ],
                "score_breakdown": {
                    "skill_match": 0.25,
                    "category_interest": 0.18,
                    "collaborative": 0.15,
                    "accessibility": 0.12,
                    "quality": 0.14
                }
            }
        }


class CourseRecommendation(BaseModel):
    """Single course recommendation"""
    course_id: int = Field(..., description="Unique course identifier")
    rank: int = Field(..., ge=1, description="Recommendation rank (1 is best)")
    score: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence score")
    title: str = Field(..., description="Course title")
    category: CourseCategory = Field(..., description="Course category")
    difficulty_level: DifficultyLevel = Field(..., description="Course difficulty")
    duration_hours: float = Field(..., gt=0, description="Course duration in hours")
    rating: float = Field(..., ge=0.0, le=5.0, description="Course rating out of 5")
    explanation: Optional[RecommendationExplanation] = Field(None, description="Why this was recommended")
    why_recommended: str = Field(..., description="Short explanation text")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When recommendation was generated")
    dismissed: bool = Field(default=False, description="Whether user dismissed this recommendation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "course_id": "course_42",
                "rank": 1,
                "score": 0.8756,
                "title": "Advanced Python Programming",
                "category": "programming",
                "difficulty_level": 3,
                "duration_hours": 12.5,
                "rating": 4.7,
                "why_recommended": "Matches your bachelor education level • You've shown interest in programming courses • Highly rated (4.7/5.0) by learners",
                "generated_at": "2025-12-07T10:30:00",
                "dismissed": False
            }
        }


class RecommendationList(BaseModel):
    """List of recommendations for a user"""
    user_id: int = Field(..., description="User identifier")
    recommendations: List[CourseRecommendation] = Field(..., min_length=0, description="List of course recommendations")
    total_count: int = Field(..., ge=0, description="Total number of recommendations")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When recommendations were generated")
    next_update: datetime = Field(..., description="When recommendations will be refreshed")
    
    @validator('recommendations')
    def validate_min_recommendations(cls, v):
        # Relaxed for Tamkeen's 7-course catalog
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "recommendations": [],
                "total_count": 15,
                "generated_at": "2025-12-07T10:30:00",
                "next_update": "2025-12-14T10:30:00"
            }
        }


class DismissRecommendationRequest(BaseModel):
    """Request to dismiss a recommendation"""
    course_id: int = Field(..., description="Course ID to dismiss")
    reason: Optional[str] = Field(None, description="Optional reason for dismissal")
    
    class Config:
        json_schema_extra = {
            "example": {
                "course_id": "course_42",
                "reason": "Already completed elsewhere"
            }
        }


class DismissRecommendationResponse(BaseModel):
    """Response after dismissing a recommendation"""
    success: bool = Field(..., description="Whether dismissal was successful")
    course_id: int = Field(..., description="Course ID that was dismissed")
    remaining_recommendations: int = Field(..., description="Number of active recommendations remaining")
    message: str = Field(..., description="Status message")


class RefreshRecommendationsRequest(BaseModel):
    """Request to refresh recommendations"""
    force: bool = Field(default=False, description="Force refresh even if not due")
    reason: Optional[str] = Field(None, description="Reason for refresh")


class RefreshRecommendationsResponse(BaseModel):
    """Response after refreshing recommendations"""
    success: bool = Field(..., description="Whether refresh was successful")
    recommendations_count: int = Field(..., description="Number of new recommendations")
    previous_update: Optional[datetime] = Field(None, description="When previous update occurred")
    next_update: datetime = Field(..., description="When next update will occur")


class RecommendationStats(BaseModel):
    """Statistics about user's recommendations"""
    user_id: int = Field(..., description="User identifier")
    total_recommendations: int = Field(..., ge=0, description="Total recommendations generated")
    active_recommendations: int = Field(..., ge=0, description="Non-dismissed recommendations")
    dismissed_count: int = Field(..., ge=0, description="Number of dismissed recommendations")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    needs_refresh: bool = Field(..., description="Whether recommendations need refresh")
    days_until_refresh: int = Field(..., ge=0, description="Days until next scheduled refresh")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "total_recommendations": 20,
                "active_recommendations": 15,
                "dismissed_count": 5,
                "last_updated": "2025-12-01T10:30:00",
                "needs_refresh": False,
                "days_until_refresh": 4
            }
        }


class UserPreferences(BaseModel):
    """User preferences for recommendations"""
    user_id: int = Field(..., description="User identifier")
    preferred_categories: List[CourseCategory] = Field(default_factory=list, description="Preferred course categories")
    excluded_categories: List[CourseCategory] = Field(default_factory=list, description="Categories to exclude")
    preferred_difficulty: Optional[DifficultyLevel] = Field(None, description="Preferred difficulty level")
    max_duration_hours: Optional[float] = Field(None, gt=0, description="Maximum course duration")
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Minimum acceptable rating")
    
    @validator('excluded_categories')
    def validate_no_overlap(cls, v, values):
        if 'preferred_categories' in values:
            overlap = set(v) & set(values['preferred_categories'])
            if overlap:
                raise ValueError(f'Categories cannot be both preferred and excluded: {overlap}')
        return v


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences"""
    preferred_categories: Optional[List[CourseCategory]] = None
    excluded_categories: Optional[List[CourseCategory]] = None
    preferred_difficulty: Optional[DifficultyLevel] = None
    max_duration_hours: Optional[float] = Field(None, gt=0)
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0)


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "UserNotFound",
                "message": "User with ID user_999 not found",
                "details": {"user_id": "user_999"}
            }
        }


# Database table schemas (for SQLAlchemy or similar ORM)

class RecommendationRecord:
    """Database schema for storing recommendations"""
    __tablename__ = 'recommendations'
    
    id: int  # Primary key
    user_id: int  # Foreign key to users table
    course_id: int  # Foreign key to courses table
    rank: int
    score: float
    explanation: str  # JSON string
    generated_at: datetime
    dismissed: bool
    dismissed_at: Optional[datetime]
    dismissal_reason: Optional[str]
    
    # Indexes
    # INDEX on (user_id, generated_at)
    # INDEX on (user_id, dismissed)
    # INDEX on (course_id)


class UserPreferencesRecord:
    """Database schema for user preferences"""
    __tablename__ = 'user_preferences'
    
    user_id: int  # Primary key, foreign key to users
    preferred_categories: str  # JSON array
    excluded_categories: str  # JSON array
    preferred_difficulty: Optional[int]
    max_duration_hours: Optional[float]
    min_rating: Optional[float]
    updated_at: datetime
    
    # INDEX on user_id


class RecommendationUpdateLog:
    """Log of recommendation updates"""
    __tablename__ = 'recommendation_update_log'
    
    id: int  # Primary key
    user_id: int  # Foreign key to users
    update_type: str  # 'scheduled', 'manual', 'forced'
    recommendations_generated: int
    triggered_at: datetime
    completed_at: datetime
    success: bool
    error_message: Optional[str]
    
    # INDEX on (user_id, triggered_at)
    # INDEX on update_type
