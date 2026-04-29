"""
Integration tests for the Recommendation System
Personalized Course Recommendations

Tests cover:
- Recommendation generation with minimum 10 results
- Explanation generation
- Dismissal functionality
- Weekly update scheduling
- API endpoints
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent and src directories to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from recommendation_engine import RecommendationEngine, RecommendationManager, load_recommendation_system
from recommendation_models import RecommendationList, CourseRecommendation


class TestRecommendationEngine:
    """Test core recommendation engine functionality"""
    
    @pytest.fixture
    def manager(self):
        """Load recommendation system for testing"""
        return load_recommendation_system("./out_small")
    
    def test_minimum_recommendations(self, manager):
        """Test that at least 10 recommendations are generated"""
        user_id = "user_0"
        recommendations = manager.get_recommendations(user_id)
        
        assert len(recommendations) >= 10, "Must generate at least 10 recommendations"
    
    def test_recommendation_structure(self, manager):
        """Test that recommendations have required fields"""
        user_id = "user_0"
        recommendations = manager.get_recommendations(user_id)
        
        assert len(recommendations) > 0, "Should have recommendations"
        
        rec = recommendations[0]
        required_fields = [
            'course_id', 'rank', 'score', 'title', 'category',
            'difficulty_level', 'duration_hours', 'rating',
            'why_recommended', 'generated_at'
        ]
        
        for field in required_fields:
            assert field in rec, f"Missing required field: {field}"
    
    def test_explanation_included(self, manager):
        """Test that explanations are included in recommendations"""
        user_id = "user_0"
        recommendations = manager.get_recommendations(user_id)
        
        assert len(recommendations) > 0
        
        rec = recommendations[0]
        assert 'why_recommended' in rec, "Should have explanation"
        assert len(rec['why_recommended']) > 0, "Explanation should not be empty"
        
        if 'explanation' in rec and rec['explanation']:
            assert 'score_breakdown' in rec['explanation'], "Should have score breakdown"
    
    def test_score_range(self, manager):
        """Test that scores are in valid range [0, 1]"""
        user_id = "user_0"
        recommendations = manager.get_recommendations(user_id)
        
        for rec in recommendations:
            assert 0 <= rec['score'] <= 1, f"Score {rec['score']} out of range"
    
    def test_unique_recommendations(self, manager):
        """Test that recommendations don't contain duplicates"""
        user_id = "user_0"
        recommendations = manager.get_recommendations(user_id)
        
        course_ids = [rec['course_id'] for rec in recommendations]
        assert len(course_ids) == len(set(course_ids)), "Should not have duplicate courses"
    
    def test_dismissal_functionality(self, manager):
        """Test dismissing a recommendation"""
        user_id = "user_0"
        recommendations = manager.get_recommendations(user_id)
        
        assert len(recommendations) > 0
        
        course_to_dismiss = recommendations[0]['course_id']
        success = manager.dismiss_recommendation(user_id, course_to_dismiss)
        
        assert success, "Dismissal should succeed"
        
        # Get updated recommendations
        updated_recommendations = manager.get_recommendations(user_id)
        updated_course_ids = [rec['course_id'] for rec in updated_recommendations]
        
        assert course_to_dismiss not in updated_course_ids, "Dismissed course should not appear"
    
    def test_dismissal_maintains_minimum(self, manager):
        """Test that dismissing maintains minimum 10 recommendations"""
        user_id = "user_0"
        
        # Dismiss multiple recommendations
        recommendations = manager.get_recommendations(user_id)
        for i in range(5):
            if i < len(recommendations):
                manager.dismiss_recommendation(user_id, recommendations[i]['course_id'])
        
        # Get updated recommendations
        updated_recommendations = manager.get_recommendations(user_id)
        
        assert len(updated_recommendations) >= 10, "Should maintain at least 10 recommendations"
    
    def test_weekly_update_check(self, manager):
        """Test weekly update scheduling"""
        user_id = "user_0"
        
        # Get initial recommendations
        manager.get_recommendations(user_id)
        
        # Should not need refresh immediately
        assert not manager._should_refresh(user_id), "Should not need immediate refresh"
        
        # Simulate 7 days passing
        manager.last_update[user_id] = datetime.utcnow() - timedelta(days=8)
        
        # Should need refresh now
        assert manager._should_refresh(user_id), "Should need refresh after 7 days"
    
    def test_force_refresh(self, manager):
        """Test forced refresh of recommendations"""
        user_id = "user_0"
        
        # Get initial recommendations
        recommendations1 = manager.get_recommendations(user_id, force_refresh=True)
        first_update = manager.last_update[user_id]
        
        # Force refresh
        recommendations2 = manager.get_recommendations(user_id, force_refresh=True)
        second_update = manager.last_update[user_id]
        
        assert second_update > first_update, "Update time should be newer after refresh"
    
    def test_different_users_different_recommendations(self, manager):
        """Test that different users get different recommendations"""
        user_id_1 = "user_0"
        user_id_2 = "user_1"
        
        recs1 = manager.get_recommendations(user_id_1)
        recs2 = manager.get_recommendations(user_id_2)
        
        courses1 = set(rec['course_id'] for rec in recs1[:5])
        courses2 = set(rec['course_id'] for rec in recs2[:5])
        
        # Top 5 recommendations should have some differences (not identical)
        assert courses1 != courses2, "Different users should get personalized recommendations"
    
    def test_stats_functionality(self, manager):
        """Test recommendation statistics"""
        user_id = "user_0"
        
        # Generate recommendations
        manager.get_recommendations(user_id)
        
        # Dismiss one
        recs = manager.get_recommendations(user_id)
        manager.dismiss_recommendation(user_id, recs[0]['course_id'])
        
        # Get stats
        stats = manager.get_recommendation_stats(user_id)
        
        assert 'total_recommendations' in stats
        assert 'active_recommendations' in stats
        assert 'dismissed_count' in stats
        assert stats['dismissed_count'] >= 1, "Should have at least 1 dismissal"
        assert stats['active_recommendations'] < stats['total_recommendations'], \
            "Active should be less than total after dismissal"


class TestRecommendationAPI:
    """Test API endpoints (requires running API server)"""
    
    @pytest.fixture
    def api_base_url(self):
        """API base URL for testing"""
        return "http://localhost:8000/api"
    
    @pytest.mark.skip(reason="Requires running API server")
    def test_get_recommendations_endpoint(self, api_base_url):
        """Test GET /api/recommendations/{user_id}"""
        import requests
        
        response = requests.get(f"{api_base_url}/recommendations/user_0")
        assert response.status_code == 200
        
        data = response.json()
        assert 'recommendations' in data
        assert len(data['recommendations']) >= 10
    
    @pytest.mark.skip(reason="Requires running API server")
    def test_dismiss_endpoint(self, api_base_url):
        """Test POST /api/recommendations/{user_id}/dismiss"""
        import requests
        
        # Get recommendations first
        response = requests.get(f"{api_base_url}/recommendations/user_0")
        data = response.json()
        course_id = data['recommendations'][0]['course_id']
        
        # Dismiss
        response = requests.post(
            f"{api_base_url}/recommendations/user_0/dismiss",
            json={"course_id": course_id}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
    
    @pytest.mark.skip(reason="Requires running API server")
    def test_refresh_endpoint(self, api_base_url):
        """Test POST /api/recommendations/{user_id}/refresh"""
        import requests
        
        response = requests.post(
            f"{api_base_url}/recommendations/user_0/refresh",
            json={"force": True}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert result['recommendations_count'] >= 10


def run_manual_tests():
    """Run manual verification tests"""
    print("=" * 80)
    print("MANUAL TEST: Recommendation System")
    print("=" * 80)
    
    print("\n1. Loading recommendation system...")
    manager = load_recommendation_system("./out_small")
    print("✓ System loaded")
    
    print("\n2. Testing recommendation generation...")
    user_id = "user_0"
    recommendations = manager.get_recommendations(user_id)
    print(f"✓ Generated {len(recommendations)} recommendations")
    assert len(recommendations) >= 10, "FAIL: Less than 10 recommendations"
    print("✓ Minimum 10 recommendations requirement met")
    
    print("\n3. Testing explanation generation...")
    rec = recommendations[0]
    print(f"   Course: {rec['title']}")
    print(f"   Reason: {rec['why_recommended']}")
    assert 'why_recommended' in rec and len(rec['why_recommended']) > 0
    print("✓ Explanations present")
    
    print("\n4. Testing dismissal...")
    course_to_dismiss = recommendations[0]['course_id']
    manager.dismiss_recommendation(user_id, course_to_dismiss)
    updated_recs = manager.get_recommendations(user_id)
    assert course_to_dismiss not in [r['course_id'] for r in updated_recs]
    print("✓ Dismissal working")
    assert len(updated_recs) >= 10
    print("✓ Still have minimum 10 recommendations")
    
    print("\n5. Testing weekly update check...")
    assert not manager._should_refresh(user_id)
    print("✓ No immediate refresh needed")
    
    manager.last_update[user_id] = datetime.utcnow() - timedelta(days=8)
    assert manager._should_refresh(user_id)
    print("✓ Refresh triggered after 7 days")
    
    print("\n6. Testing statistics...")
    stats = manager.get_recommendation_stats(user_id)
    print(f"   Total: {stats['total_recommendations']}")
    print(f"   Active: {stats['active_recommendations']}")
    print(f"   Dismissed: {stats['dismissed_count']}")
    print("✓ Statistics working")
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)


if __name__ == "__main__":
    # Run manual tests
    run_manual_tests()
    
    # Run pytest if available
    print("\n\nRunning pytest...")
    pytest.main([__file__, "-v", "--tb=short"])
