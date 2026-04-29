"""
Personalized Course Recommendation Engine for Tamkeen Platform

Features:
- Hybrid recommendation (collaborative + content-based + accessibility-aware)
- Explainable recommendations with clear reasoning
- User skill level matching
- Learning history consideration
- Accessibility preference matching
- Cohere embedding generation (384-D via embed-english-v3.0)
- Qdrant vector search for semantic similarity
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json
from collections import defaultdict

# Configure module-level logger
logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Core recommendation engine that generates personalized course suggestions
    considering user profile, learning history, and accessibility needs.
    """
    
    # Event weight mapping used across embedding & interaction logic
    EVENT_WEIGHTS: Dict[str, float] = {
        'complete_course': 10.0,
        'enroll_course': 5.0,
        'rate_course': 4.0,
        'complete_lesson': 3.0,
        'video_play': 2.0,
        'click_course': 1.5,
        'view_course': 1.0,
    }

    # Qdrant collection that stores Cohere course embeddings
    QDRANT_COLLECTION: str = "tamkeen-RS"

    def __init__(
        self,
        users_df: pd.DataFrame,
        courses_df: pd.DataFrame,
        interactions_df: pd.DataFrame,
        embeddings: Optional[np.ndarray] = None,
        cohere_api_key: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
    ):
        """
        Initialize the recommendation engine with data.

        Args:
            users_df: User profiles with disability types, education, preferences
            courses_df: Course catalog with difficulty, category, ratings
            interactions_df: User interaction history (views, enrolls, completions)
            embeddings: Optional course embeddings for content-based filtering
                        (numpy fallback when Qdrant is unavailable)
            cohere_api_key: Cohere API key. Falls back to ``COHERE_API_KEY`` env var.
            qdrant_url: Full Qdrant Cloud URL (e.g. ``https://…cloud.qdrant.io:6333``).
                        Falls back to ``QDRANT_URL`` env var.
            qdrant_api_key: Qdrant API key for cloud auth.
                           Falls back to ``QDRANT_API_KEY`` env var.
        """
        self.users_df = users_df.set_index('user_id')
        self.courses_df = courses_df.set_index('course_id')
        self.interactions_df = interactions_df
        
        # Mapping for Qdrant (int ID -> original string ID)
        self.course_id_map = {}
        if 'original_course_id' in courses_df.columns:
            self.course_id_map = dict(zip(courses_df['course_id'], courses_df['original_course_id']))
        self.embeddings = embeddings  # numpy fallback

        # --- Cohere client ---
        resolved_cohere_key = cohere_api_key or os.environ.get("COHERE_API_KEY")
        if resolved_cohere_key:
            try:
                import cohere
                self.cohere_client = cohere.ClientV2(api_key=resolved_cohere_key)
                logger.info("Cohere client initialized successfully.")
            except Exception as exc:
                logger.warning("Cohere client initialization failed: %s", exc)
                self.cohere_client = None
        else:
            logger.info("No Cohere API key provided – semantic features will use numpy fallback.")
            self.cohere_client = None

        # --- Qdrant client (supports Cloud URL + API key) ---
        resolved_qdrant_url = qdrant_url or os.environ.get("QDRANT_URL")
        resolved_qdrant_key = qdrant_api_key or os.environ.get("QDRANT_API_KEY")
        try:
            from qdrant_client import QdrantClient
            if resolved_qdrant_url:
                # Cloud / remote mode
                self.qdrant_client = QdrantClient(
                    url=resolved_qdrant_url,
                    api_key=resolved_qdrant_key,
                    timeout=60,
                )
            else:
                # Local mode fallback (localhost:6333)
                self.qdrant_client = QdrantClient(
                    host="localhost",
                    port=6333,
                    prefer_grpc=True,
                )
            # Quick health-check
            self.qdrant_client.get_collections()
            logger.info("Qdrant client connected at %s.", resolved_qdrant_url or "localhost:6333")
        except Exception as exc:
            logger.warning("Qdrant connection failed (%s): %s", resolved_qdrant_url or "localhost:6333", exc)
            self.qdrant_client = None

        # Precompute user-course interaction matrix
        self._build_interaction_matrix()

        # Compute course statistics
        self._compute_course_stats()
        
    def _build_interaction_matrix(self):
        """Build user-course interaction matrix with weighted events."""
        # Weight different event types
        event_weights = {
            'view_course': 1.0,
            'click_course': 1.5,
            'enroll_course': 5.0,
            'video_play': 2.0,
            'complete_lesson': 3.0,
            'complete_course': 10.0,
            'rate_course': 4.0
        }
        
        # Calculate interaction scores
        interactions = self.interactions_df.copy()
        interactions['score'] = interactions['event_type'].map(event_weights).fillna(1.0)
        
        # Aggregate by user-course
        self.user_course_scores = interactions.groupby(['user_id', 'course_id'])['score'].sum()
        
        # Get completed courses per user
        completed = interactions[interactions['event_type'] == 'complete_course']
        self.user_completed_courses = completed.groupby('user_id')['course_id'].apply(set).to_dict()
        
        # Get enrolled courses per user
        enrolled = interactions[interactions['event_type'] == 'enroll_course']
        self.user_enrolled_courses = enrolled.groupby('user_id')['course_id'].apply(set).to_dict()
        
    def _compute_course_stats(self):
        """Compute popularity and engagement statistics for courses."""
        # Course popularity (number of unique users who interacted)
        course_users = self.interactions_df.groupby('course_id')['user_id'].nunique()
        self.course_popularity = course_users / course_users.max()
        
        # Course completion rate (if available in course data)
        if 'completion_rate' in self.courses_df.columns:
            self.course_completion_rate = self.courses_df['completion_rate']
        else:
            # Calculate from interactions
            enrolls = self.interactions_df[self.interactions_df['event_type'] == 'enroll_course']
            completes = self.interactions_df[self.interactions_df['event_type'] == 'complete_course']
            enroll_counts = enrolls.groupby('course_id').size()
            complete_counts = completes.groupby('course_id').size()
            self.course_completion_rate = (complete_counts / enroll_counts).fillna(0)
    
    def generate_recommendations(self, user_id: int, n: int = 10, 
                                include_explanations: bool = True) -> List[Dict]:
        """
        Generate personalized course recommendations for a user.
        
        Args:
            user_id: User identifier
            n: Number of recommendations to generate (minimum 10)
            include_explanations: Whether to include explanation for each recommendation
            
        Returns:
            List of recommendation dictionaries with scores and explanations
        """
        n = max(n, 10)  # Ensure minimum 10 recommendations
        
        if user_id not in self.users_df.index:
            raise ValueError(f"User {user_id} not found")
        
        user_profile = self.users_df.loc[user_id]
        
        # Get courses already completed or enrolled (exclude from recommendations)
        completed = self.user_completed_courses.get(user_id, set())
        enrolled = self.user_enrolled_courses.get(user_id, set())
        exclude_courses = completed | enrolled
        
        # Compute recommendation scores using hybrid approach
        scores = {}
        explanations = {}
        
        for course_id in self.courses_df.index:
            if course_id in exclude_courses:
                continue
                
            score, explanation = self._compute_course_score(
                user_id, user_profile, course_id, include_explanations
            )
            scores[course_id] = score
            if include_explanations:
                explanations[course_id] = explanation
        
        # Sort by score and get top N
        top_courses = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]
        
        # Format recommendations
        recommendations = []
        for rank, (course_id, score) in enumerate(top_courses, 1):
            course = self.courses_df.loc[course_id]
            rec = {
                'course_id': course_id,
                'rank': rank,
                'score': round(float(score), 4),
                'title': course['title'],
                'category': course['category'],
                'difficulty_level': min(int(course['difficulty_level']), 3),
                'duration_hours': float(course['duration_hours']),
                'rating': float(course['rating']),
            }
            
            if include_explanations:
                rec['explanation'] = explanations[course_id]
                rec['why_recommended'] = self._format_explanation(explanations[course_id])
            
            recommendations.append(rec)
        
        return recommendations
    
    def _compute_course_score(self, user_id: int, user_profile: pd.Series, 
                             course_id: int, include_explanation: bool = False) -> Tuple[float, Dict]:
        """
        Compute recommendation score for a course using hybrid approach.
        
        Components:
        1. Skill level matching (22%)
        2. Category interest (18%)
        3. Collaborative filtering (18%)
        4. Accessibility alignment (13%)
        5. Quality & popularity signals (13%)
        6. Semantic similarity via embeddings (10%) - NEW
        7. Engagement prediction (6%)
        """
        course = self.courses_df.loc[course_id]
        explanation = defaultdict(list)
        score_components = {}
        
        # 1. Skill Level Matching (22% weight)
        skill_score = self._compute_skill_match(user_profile, course)
        score_components['skill_match'] = skill_score * 0.22
        if skill_score > 0.7:
            explanation['skill_match'].append(
                f"Matches your {user_profile['education_level']} education level"
            )
        
        # 2. Category Interest (18% weight)
        category_score = self._compute_category_interest(user_id, course['category'])
        score_components['category_interest'] = category_score * 0.18
        if category_score > 0.5:
            explanation['category_interest'].append(
                f"You've shown interest in {course['category']} courses"
            )
        
        # 3. Collaborative Filtering (18% weight)
        collab_score = self._compute_collaborative_score(user_id, course_id)
        score_components['collaborative'] = collab_score * 0.18
        if collab_score > 0.6:
            explanation['collaborative'].append(
                "Users with similar interests enjoyed this course"
            )
        
        # 4. Accessibility Match (13% weight)
        accessibility_score = self._compute_accessibility_match(user_profile, course)
        score_components['accessibility'] = accessibility_score * 0.13
        if accessibility_score > 0.8:
            explanation['accessibility'].append(
                f"Optimized for {user_profile['disability_type']} accessibility needs"
            )
        
        # 5. Quality & Popularity Signals (13% weight)
        quality_score = self._compute_quality_score(course_id, course)
        score_components['quality'] = quality_score * 0.13
        if course['rating'] >= 4.5:
            explanation['quality'].append(
                f"Highly rated ({course['rating']:.1f}/5.0) by learners"
            )
        if self.course_popularity.get(course_id, 0) > 0.7:
            explanation['quality'].append("Popular course in our platform")
        
        # 6. Semantic Similarity via Embeddings (10% weight) - NEW!
        semantic_score = self._compute_semantic_similarity(user_id, course_id)
        score_components['semantic_similarity'] = semantic_score * 0.10
        if semantic_score > 0.7:
            explanation['semantic_similarity'].append(
                "Similar to courses you've engaged with"
            )
        
        # 7. Engagement Prediction (6% weight)
        engagement_score = self._compute_engagement_prediction(user_profile, course)
        score_components['engagement'] = engagement_score * 0.06
        
        # Total score
        total_score = sum(score_components.values())
        
        # Add bonus for trending or new courses
        total_score += self._compute_trend_bonus(course_id) * 0.05
        
        explanation_dict = dict(explanation) if include_explanation else {}
        explanation_dict['score_breakdown'] = score_components
        
        return total_score, explanation_dict
    
    def _compute_skill_match(self, user_profile: pd.Series, course: pd.Series) -> float:
        """Match course difficulty to user education level."""
        education_to_skill = {
            'NO_FORMAL': 1,
            'PRIMARY': 1,
            'LOWER_SECONDARY': 1,
            'UPPER_SECONDARY': 2,
            'SHORT_CYCLE_TERTIARY': 2,
            'BACHELOR': 2,
            'MASTER': 3,
            'DOCTORATE': 3,
            # Legacy CSV support
            'secondary': 2,
            'diploma': 2,
            'bachelor': 2,
            'postgraduate': 3
        }
        
        user_skill = education_to_skill.get(user_profile['education_level'], 2)
        course_difficulty = min(int(course['difficulty_level']), 3)
        
        # Prefer courses at user's level or slightly above
        diff = abs(user_skill - course_difficulty)
        
        if diff == 0:
            return 1.0  # Perfect match
        elif diff == 1 and course_difficulty > user_skill:
            return 0.85  # Slight challenge (good)
        elif diff == 1:
            return 0.7  # Slightly below (okay)
        elif diff == 2:
            return 0.4  # Too different
        else:
            return 0.2  # Very mismatched
    
    def _compute_category_interest(self, user_id: int, category: str) -> float:
        """Compute user's interest in a course category based on history."""
        user_interactions = self.interactions_df[self.interactions_df['user_id'] == user_id]
        
        if len(user_interactions) == 0:
            return 0.5  # Neutral for new users
        
        # Get courses user interacted with
        user_courses = user_interactions['course_id'].unique()
        
        # Count interactions in this category
        category_interactions = 0
        total_interactions = len(user_courses)
        
        for course_id in user_courses:
            if course_id in self.courses_df.index:
                if self.courses_df.loc[course_id]['category'] == category:
                    category_interactions += 1
        
        if total_interactions == 0:
            return 0.5
        
        return min(1.0, category_interactions / total_interactions + 0.3)
    
    def _compute_collaborative_score(self, user_id: int, course_id: int) -> float:
        """Collaborative filtering: find similar users and their preferences."""
        # Get user's interaction vector
        user_interactions = self.user_course_scores.xs(user_id, level='user_id') if user_id in self.user_course_scores.index.get_level_values('user_id') else pd.Series()
        
        if len(user_interactions) == 0:
            return 0.5  # Neutral for new users
        
        # Find users who took courses this user also took
        similar_users = set()
        for interacted_course in user_interactions.index:
            if interacted_course in self.user_course_scores.index.get_level_values('course_id'):
                users_who_took = self.user_course_scores.xs(interacted_course, level='course_id').index
                similar_users.update(users_who_took)
        
        similar_users.discard(user_id)
        
        if not similar_users:
            return 0.5
        
        # Check how many similar users interacted with target course
        if course_id not in self.user_course_scores.index.get_level_values('course_id'):
            return 0.4
        
        users_who_took_target = set(self.user_course_scores.xs(course_id, level='course_id').index)
        overlap = len(similar_users & users_who_took_target)
        
        return min(1.0, overlap / len(similar_users) * 2)
    
    # ------------------------------------------------------------------
    # Issue 3 – User interest embedding from Qdrant
    # ------------------------------------------------------------------
    def get_user_interest_embedding(self, user_id: int) -> Optional[List[float]]:
        """
        Build the user's interest embedding as a *weighted average* of Cohere
        embeddings for courses they engaged with, retrieved from Qdrant.

        Returns:
            A list of floats (384-D for Cohere embed-english-v3.0) or ``None``
            when no valid embedding could be computed.
        """
        if self.qdrant_client is None:
            logger.debug("get_user_interest_embedding: Qdrant unavailable for user %s.", user_id)
            return None

        # We now expect User embeddings to be stored directly in Qdrant with item_type="user"
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            results = self.qdrant_client.scroll(
                collection_name=self.QDRANT_COLLECTION,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="item_type",
                            match=MatchValue(value="user"),
                        ),
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id),
                        )
                    ]
                ),
                with_vectors=True,
                limit=1,
            )

            points = results[0] if results else []
            if not points:
                logger.debug("Qdrant returned no pre-computed embedding for user %s.", user_id)
                return None

            user_embedding = points[0].vector
            logger.debug("Found pre-computed interest embedding for user %s.", user_id)
            return user_embedding

        except Exception as exc:
            logger.error("Error computing user interest embedding for %s: %s", user_id, exc)
            return None

    # ------------------------------------------------------------------
    # Issue 4 – Semantic similarity via Cohere + Qdrant (with fallback)
    # ------------------------------------------------------------------
    def _compute_semantic_similarity(self, user_id: int, course_id: int) -> float:
        """
        Compute semantic similarity between a user's interest profile and a
        target course.

        Strategy:
        1. **Primary** – Use Qdrant vector search with the user's weighted
           interest embedding (built from Cohere 384-D vectors stored in
           Qdrant).  Returns the Qdrant cosine similarity score (0-1).
        2. **Fallback** – If Qdrant is unavailable, fall back to the legacy
           numpy-based cosine similarity using the local ``self.embeddings``
           matrix.
        3. **Neutral** – Return 0.5 when neither source is available.
        """

        # ----- Primary path: Qdrant -----
        if self.qdrant_client is not None:
            user_embedding = self.get_user_interest_embedding(user_id)
            if user_embedding is not None:
                try:
                    from qdrant_client.models import Filter, FieldCondition, MatchValue

                    results = self.qdrant_client.search(
                        collection_name=self.QDRANT_COLLECTION,
                        query_vector=user_embedding,
                        query_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="item_type",
                                    match=MatchValue(value="course"),
                                ),
                                FieldCondition(
                                    key="course_id",
                                    match=MatchValue(value=self.course_id_map.get(course_id, str(course_id))),
                                )
                            ]
                        ),
                        limit=1,
                    )

                    if results and len(results) > 0:
                        score = float(results[0].score)
                        # Qdrant cosine similarity can be in [-1, 1]; normalise
                        # to [0, 1] for consistency with the rest of the engine.
                        normalised = (score + 1.0) / 2.0
                        return max(0.0, min(1.0, normalised))
                    else:
                        logger.debug(
                            "Qdrant returned no results for course %s.", course_id
                        )
                        return 0.5

                except Exception as exc:
                    logger.error("Qdrant search error for course %s: %s", course_id, exc)
                    # Fall through to numpy fallback

        # ----- Fallback path: numpy embeddings from file -----
        if self.embeddings is not None:
            return self._compute_semantic_similarity_numpy(user_id, course_id)

        # ----- No embedding source available -----
        return 0.5

    # ------------------------------------------------------------------
    # Legacy numpy-based semantic similarity (kept for backward compat)
    # ------------------------------------------------------------------
    def _compute_semantic_similarity_numpy(
        self, user_id: int, course_id: int
    ) -> float:
        """
        Fallback: compute cosine similarity using the local numpy embedding
        matrix.  This is the original algorithm, preserved so the engine
        continues to work without Cohere / Qdrant.
        """
        course_list = list(self.courses_df.index)
        if course_id not in course_list:
            return 0.5

        course_idx = course_list.index(course_id)

        # Get user's interaction history
        user_interactions = self.interactions_df[
            self.interactions_df['user_id'] == user_id
        ]
        if user_interactions.empty:
            return 0.5  # Neutral for new users

        # Weighted course engagement
        user_course_weights: Dict[str, float] = {}
        for _, interaction in user_interactions.iterrows():
            cid = interaction['course_id']
            event = interaction['event_type']
            weight = self.EVENT_WEIGHTS.get(event, 1.0)
            user_course_weights[cid] = user_course_weights.get(cid, 0) + weight

        # Build user interest embedding (weighted average)
        interest_embedding = np.zeros(self.embeddings.shape[1])
        total_weight = 0.0

        for cid, weight in user_course_weights.items():
            if cid in course_list and cid != course_id:
                idx = course_list.index(cid)
                interest_embedding += self.embeddings[idx] * weight
                total_weight += weight

        if total_weight == 0:
            return 0.5

        interest_embedding /= total_weight

        # Cosine similarity
        course_embedding = self.embeddings[course_idx]
        norm_interest = np.linalg.norm(interest_embedding)
        norm_course = np.linalg.norm(course_embedding)

        if norm_interest == 0 or norm_course == 0:
            return 0.5

        similarity = np.dot(interest_embedding, course_embedding) / (
            norm_interest * norm_course
        )

        # Convert from [-1, 1] to [0, 1] range
        return float((similarity + 1) / 2)
    
    def _compute_accessibility_match(self, user_profile: pd.Series, course: pd.Series) -> float:
        """Score based on accessibility feature alignment."""
        disability_type = user_profile['disability_type']
        
        # Baseline score
        score = 0.7
        
        # Check user preferences (if available)
        if 'pref_high_contrast' in user_profile and user_profile['pref_high_contrast']:
            score += 0.1
        if 'pref_screen_reader' in user_profile and user_profile['pref_screen_reader']:
            score += 0.1
        if 'pref_sign_language' in user_profile and user_profile['pref_sign_language']:
            score += 0.05
        
        return min(1.0, score)
    
    def _compute_quality_score(self, course_id: str, course: pd.Series) -> float:
        """Compute quality score from ratings and completion rates."""
        # Normalize rating (0-5 scale to 0-1)
        rating_score = course['rating'] / 5.0
        
        # Get completion rate
        completion_score = self.course_completion_rate.get(course_id, 0.5)
        
        # Get popularity
        popularity_score = self.course_popularity.get(course_id, 0.3)
        
        # Weighted combination
        quality = (rating_score * 0.5 + completion_score * 0.3 + popularity_score * 0.2)
        
        return quality
    
    def _compute_engagement_prediction(self, user_profile: pd.Series, course: pd.Series) -> float:
        """Predict likelihood of user engaging with course."""
        # Activity tier influences engagement
        tier_engagement = {
            'dormant': 0.3,
            'casual': 0.6,
            'regular': 0.8,
            'power': 1.0
        }
        
        base_engagement = tier_engagement.get(user_profile['activity_tier'], 0.6)
        
        # Adjust for course duration (shorter courses more likely for casual users)
        if course['duration_hours'] < 5 and user_profile['activity_tier'] in ['dormant', 'casual']:
            base_engagement += 0.1
        elif course['duration_hours'] > 20 and user_profile['activity_tier'] == 'power':
            base_engagement += 0.1
        
        return min(1.0, base_engagement)
    
    def _compute_trend_bonus(self, course_id: int) -> float:
        """Add small bonus for trending courses (recent popularity spike)."""
        # Check recent interactions (last 7 days)
        recent_date = datetime.utcnow() - timedelta(days=7)
        
        try:
            recent_interactions = self.interactions_df[
                pd.to_datetime(self.interactions_df['event_ts']) > recent_date
            ]
            
            if course_id in recent_interactions['course_id'].values:
                recent_count = len(recent_interactions[recent_interactions['course_id'] == course_id])
                if recent_count > 10:  # Arbitrary threshold
                    return 0.2
        except:
            pass
        
        return 0.0
    
    def _format_explanation(self, explanation_dict: Dict) -> str:
        """Format explanation dictionary into human-readable text."""
        reasons = []
        
        for category, items in explanation_dict.items():
            if category == 'score_breakdown':
                continue
            if items:
                reasons.extend(items)
        
        if not reasons:
            reasons.append("Recommended based on your profile and learning preferences")
        
        return " • ".join(reasons[:3])  # Show top 3 reasons


class RecommendationManager:
    """
    Manages recommendation lifecycle: generation, storage, dismissal, and updates.
    """
    
    def __init__(self, engine: RecommendationEngine):
        self.engine = engine
        self.user_recommendations = {}  # Cache: user_id -> recommendations
        self.dismissed_recommendations = defaultdict(set)  # user_id -> set of course_ids
        self.last_update = {}  # user_id -> timestamp
    
    def get_recommendations(self, user_id: int, force_refresh: bool = False) -> List[Dict]:
        """
        Get recommendations for a user. Uses cache if available and not stale.
        
        Args:
            user_id: User identifier
            force_refresh: Force regeneration even if cache is fresh
            
        Returns:
            List of recommendations with explanations
        """
        # Check if we need to refresh
        needs_refresh = force_refresh or self._should_refresh(user_id)
        
        if needs_refresh:
            recommendations = self._generate_fresh_recommendations(user_id)
            self.user_recommendations[user_id] = recommendations
            self.last_update[user_id] = datetime.utcnow()
        else:
            recommendations = self.user_recommendations.get(user_id, [])
        
        # Filter out dismissed recommendations
        dismissed = self.dismissed_recommendations[user_id]
        filtered = [r for r in recommendations if r['course_id'] not in dismissed]
        
        # Ensure we still have enough (at least 5 or all available)
        if len(filtered) < 5 and needs_refresh is False:
            # Force refresh if we don't have enough after filtering
            return self.get_recommendations(user_id, force_refresh=True)
        
        return filtered
    
    def _should_refresh(self, user_id: int) -> bool:
        """Check if recommendations should be refreshed (weekly update)."""
        if user_id not in self.last_update:
            return True
        
        last_update = self.last_update[user_id]
        days_since_update = (datetime.utcnow() - last_update).days
        
        return days_since_update >= 7  # Weekly update
    
    def _generate_fresh_recommendations(self, user_id: int) -> List[Dict]:
        """Generate fresh recommendations using the engine."""
        # Generate extra recommendations to account for dismissals
        recommendations = self.engine.generate_recommendations(
            user_id, 
            n=20,  # Generate 20 to have buffer
            include_explanations=True
        )
        
        # Add metadata
        for rec in recommendations:
            rec['generated_at'] = datetime.utcnow().isoformat()
            rec['dismissed'] = False
        
        return recommendations
    
    def dismiss_recommendation(self, user_id: int, course_id: int) -> bool:
        """
        Dismiss a recommendation for a user.
        
        Args:
            user_id: User identifier
            course_id: Course to dismiss
            
        Returns:
            True if successfully dismissed
        """
        self.dismissed_recommendations[user_id].add(course_id)
        
        # Update the recommendation list if cached
        if user_id in self.user_recommendations:
            for rec in self.user_recommendations[user_id]:
                if rec['course_id'] == course_id:
                    rec['dismissed'] = True
        
        return True
    
    def force_update_all_users(self, user_ids: List[str]):
        """Force update recommendations for multiple users (batch processing)."""
        for user_id in user_ids:
            try:
                self.get_recommendations(user_id, force_refresh=True)
            except Exception as e:
                print(f"Error updating recommendations for {user_id}: {e}")
    
    def get_recommendation_stats(self, user_id: int) -> Dict:
        """Get statistics about user's recommendations."""
        recommendations = self.user_recommendations.get(user_id, [])
        dismissed = self.dismissed_recommendations[user_id]
        last_update = self.last_update.get(user_id)
        
        return {
            'total_recommendations': len(recommendations),
            'active_recommendations': len([r for r in recommendations if r['course_id'] not in dismissed]),
            'dismissed_count': len(dismissed),
            'last_updated': last_update.isoformat() if last_update else None,
            'needs_refresh': self._should_refresh(user_id)
        }


def load_recommendation_system(
    data_path: str,
    cohere_api_key: Optional[str] = None,
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
) -> RecommendationManager:
    """
    Load the recommendation system from generated data.

    Args:
        data_path: Path to the output directory with generated data
        cohere_api_key: Optional Cohere API key (falls back to env var)
        qdrant_url: Qdrant Cloud URL (falls back to QDRANT_URL env var)
        qdrant_api_key: Qdrant API key (falls back to QDRANT_API_KEY env var)

    Returns:
        Initialized RecommendationManager
    """
    def sanitize_id(id_val):
        if isinstance(id_val, str):
            import re
            # 1. Try to extract number (e.g., 'user_123' -> 123)
            match = re.search(r'\d+', id_val)
            if match:
                return int(match.group())
            
            # 2. For non-numeric strings (e.g., 'digital_marketing'), 
            # generate a stable integer hash to satisfy the 'int' schema requirement
            import hashlib
            return int(hashlib.md5(id_val.encode()).hexdigest(), 16) % 1000000
            
        try:
            return int(id_val)
        except:
            # Fallback to a hash if it's somehow not an int or str
            import hashlib
            return int(hashlib.md5(str(id_val).encode()).hexdigest(), 16) % 1000000

    # Load data
    users_df = pd.read_csv(os.path.join(data_path, 'users.csv'))
    users_df['user_id'] = users_df['user_id'].apply(sanitize_id)
    
    courses_df = pd.read_csv(os.path.join(data_path, 'courses.csv'))
    courses_df['original_course_id'] = courses_df['course_id']
    courses_df['course_id'] = courses_df['course_id'].apply(sanitize_id)

    # Load interactions from partitioned files
    interactions_parts = []
    interactions_dir = os.path.join(data_path, 'interactions')
    if os.path.exists(interactions_dir):
        for file in os.listdir(interactions_dir):
            if file.endswith('.csv'):
                part = pd.read_csv(os.path.join(interactions_dir, file))
                part['user_id'] = part['user_id'].apply(sanitize_id)
                part['course_id'] = part['course_id'].apply(sanitize_id)
                interactions_parts.append(part)

    interactions_df = (
        pd.concat(interactions_parts, ignore_index=True)
        if interactions_parts
        else pd.DataFrame()
    )

    # Load numpy embeddings as fallback (legacy)
    embeddings_path = os.path.join(data_path, 'embeddings', 'course_text.npy')
    embeddings = np.load(embeddings_path) if os.path.exists(embeddings_path) else None

    # Initialize engine with Cohere + Qdrant Cloud support
    engine = RecommendationEngine(
        users_df,
        courses_df,
        interactions_df,
        embeddings=embeddings,
        cohere_api_key=cohere_api_key,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
    )
    manager = RecommendationManager(engine)

    return manager


if __name__ == "__main__":
    # Example usage
    print("Loading recommendation system...")
    manager = load_recommendation_system("./out_small")
    
    # Get recommendations for first user
    user_id = "user_0"
    print(f"\nGenerating recommendations for {user_id}...")
    recommendations = manager.get_recommendations(user_id)
    
    print(f"\nTop 10 Recommendations for {user_id}:")
    print("=" * 80)
    for rec in recommendations[:10]:
        print(f"\n{rec['rank']}. {rec['title']}")
        print(f"   Category: {rec['category']} | Difficulty: {rec['difficulty_level']}/5")
        print(f"   Duration: {rec['duration_hours']}h | Rating: {rec['rating']}/5.0")
        print(f"   Score: {rec['score']:.4f}")
        print(f"   Why: {rec['why_recommended']}")
    
    print("\n" + "=" * 80)
    print(f"\nStats: {manager.get_recommendation_stats(user_id)}")
