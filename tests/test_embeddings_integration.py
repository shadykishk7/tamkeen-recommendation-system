"""
Test script to verify real ML embeddings are working in the recommendation engine.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from recommendation_engine import load_recommendation_system

def main():
    print("=" * 60)
    print("Testing Recommendation Engine with Real ML Embeddings")
    print("=" * 60)
    
    # Load the system
    print("\nLoading recommendation system...")
    manager = load_recommendation_system('../out_small')
    print("System loaded successfully!")
    
    # Check if embeddings are loaded
    engine = manager.engine
    if engine.embeddings is not None:
        print(f"\nEmbeddings loaded: {engine.embeddings.shape}")
        print(f"  - {engine.embeddings.shape[0]} courses")
        print(f"  - {engine.embeddings.shape[1]} dimensions (SentenceTransformer)")
    else:
        print("\nWARNING: No embeddings loaded!")
    
    # Get recommendations for user_0
    print("\n" + "-" * 60)
    print("Generating recommendations for user_0...")
    print("-" * 60)
    
    recs = manager.get_recommendations('user_0')
    
    print(f"\nTop 10 Recommendations:")
    print("-" * 60)
    
    for rec in recs[:10]:
        print(f"\n{rec['rank']}. {rec['title']}")
        print(f"   Category: {rec['category']} | Difficulty: {rec['difficulty_level']}/5")
        print(f"   Rating: {rec['rating']}/5.0 | Duration: {rec['duration_hours']}h")
        print(f"   Total Score: {rec['score']:.4f}")
        
        # Show score breakdown
        breakdown = rec['explanation'].get('score_breakdown', {})
        print("   Score Breakdown:")
        for factor, score in breakdown.items():
            print(f"     - {factor}: {score:.4f}")
        
        # Show explanation
        print(f"   Why: {rec['why_recommended']}")
    
    # Show comparison of semantic scores
    print("\n" + "=" * 60)
    print("Semantic Similarity Analysis")
    print("=" * 60)
    
    # Get all semantic scores
    semantic_scores = []
    for rec in recs:
        breakdown = rec['explanation'].get('score_breakdown', {})
        sem_score = breakdown.get('semantic_similarity', 0)
        semantic_scores.append((rec['course_id'], rec['title'], sem_score))
    
    # Sort by semantic score
    semantic_scores.sort(key=lambda x: x[2], reverse=True)
    
    print("\nCourses by Semantic Similarity to User's Interests:")
    for cid, title, score in semantic_scores[:5]:
        print(f"  {title}: {score:.4f}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
