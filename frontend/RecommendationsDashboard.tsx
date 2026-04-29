/**
 * Course Recommendations Dashboard Component
 * Displays personalized course recommendations with explanations
 * 
 * Features:
 * - Shows minimum 10 recommendations
 * - Displays explanation for each recommendation
 * - Allows dismissing recommendations
 * - Shows refresh status and next update time
 */

import React, { useState, useEffect, useCallback } from 'react';
import './RecommendationsDashboard.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

interface Recommendation {
    course_id: string;
    rank: number;
    score: number;
    title: string;
    category: string;
    difficulty_level: number;
    duration_hours: number;
    rating: number;
    why_recommended: string;
    explanation?: {
        primary_reason: string;
        supporting_reasons: string[];
        score_breakdown: Record<string, number>;
    };
    generated_at: string;
    dismissed: boolean;
}

interface RecommendationListResponse {
    user_id: string;
    recommendations: Recommendation[];
    total_count: number;
    generated_at: string;
    next_update: string;
}

interface RecommendationsDashboardProps {
    userId: string;
}

export const RecommendationsDashboard: React.FC<RecommendationsDashboardProps> = ({ userId }) => {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [nextUpdate, setNextUpdate] = useState<string>('');
    const [generatedAt, setGeneratedAt] = useState<string>('');
    const [showExplanation, setShowExplanation] = useState<Record<string, boolean>>({});

    const fetchRecommendations = useCallback(async (forceRefresh: boolean = false) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE_URL}/recommendations/${userId}?force_refresh=${forceRefresh}`
            );

            if (!response.ok) {
                throw new Error(`Failed to fetch recommendations: ${response.statusText}`);
            }

            const data: RecommendationListResponse = await response.json();
            setRecommendations(data.recommendations);
            setNextUpdate(data.next_update);
            setGeneratedAt(data.generated_at);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    }, [userId]);

    useEffect(() => {
        fetchRecommendations();
    }, [fetchRecommendations]);

    const dismissRecommendation = async (courseId: string) => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/recommendations/${userId}/dismiss`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        course_id: courseId,
                        reason: 'User dismissed from dashboard',
                    }),
                }
            );

            if (!response.ok) {
                throw new Error('Failed to dismiss recommendation');
            }

            // Remove from UI
            setRecommendations(prev => prev.filter(rec => rec.course_id !== courseId));
        } catch (err) {
            console.error('Error dismissing recommendation:', err);
            alert('Failed to dismiss recommendation');
        }
    };

    const handleRefresh = () => {
        fetchRecommendations(true);
    };

    const toggleExplanation = (courseId: string) => {
        setShowExplanation(prev => ({
            ...prev,
            [courseId]: !prev[courseId],
        }));
    };

    const getDifficultyLabel = (level: number): string => {
        const labels = ['', 'Beginner', 'Elementary', 'Intermediate', 'Advanced', 'Expert'];
        return labels[level] || 'Unknown';
    };

    const getCategoryIcon = (category: string): string => {
        const icons: Record<string, string> = {
            programming: '💻',
            soft_skills: '🤝',
            business: '💼',
            accessibility: '♿',
            design: '🎨',
            data: '📊',
            language: '🌍',
        };
        return icons[category] || '📚';
    };

    const formatDate = (dateString: string): string => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    };

    const getDaysUntilUpdate = (): number => {
        if (!nextUpdate) return 0;
        const next = new Date(nextUpdate);
        const now = new Date();
        const diff = next.getTime() - now.getTime();
        return Math.ceil(diff / (1000 * 60 * 60 * 24));
    };

    if (loading) {
        return (
            <div className="recommendations-dashboard loading">
                <div className="spinner"></div>
                <p>Loading your personalized recommendations...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="recommendations-dashboard error">
                <h3>Error Loading Recommendations</h3>
                <p>{error}</p>
                <button onClick={() => fetchRecommendations()}>Try Again</button>
            </div>
        );
    }

    return (
        <div className="recommendations-dashboard">
            <div className="dashboard-header">
                <div className="header-content">
                    <h2>📚 Recommended for You</h2>
                    <p className="subtitle">
                        Personalized course suggestions based on your profile, interests, and learning history
                    </p>
                </div>
                <div className="header-actions">
                    <button
                        className="refresh-button"
                        onClick={handleRefresh}
                        title="Refresh recommendations"
                    >
                        🔄 Refresh
                    </button>
                </div>
            </div>

            <div className="update-info">
                <span className="info-badge">
                    Last updated: {formatDate(generatedAt)}
                </span>
                <span className="info-badge">
                    Next update in {getDaysUntilUpdate()} days
                </span>
                <span className="info-badge">
                    {recommendations.length} recommendations
                </span>
            </div>

            {recommendations.length < 10 && (
                <div className="warning-banner">
                    ⚠️ Fewer than 10 recommendations available. Try refreshing or adjusting your preferences.
                </div>
            )}

            <div className="recommendations-grid">
                {recommendations.map((rec) => (
                    <div key={rec.course_id} className="recommendation-card">
                        <div className="card-header">
                            <div className="card-rank">#{rec.rank}</div>
                            <button
                                className="dismiss-button"
                                onClick={() => dismissRecommendation(rec.course_id)}
                                title="Dismiss this recommendation"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="card-content">
                            <div className="course-icon">
                                {getCategoryIcon(rec.category)}
                            </div>

                            <h3 className="course-title">{rec.title}</h3>

                            <div className="course-meta">
                                <span className="meta-badge category">
                                    {rec.category.replace('_', ' ')}
                                </span>
                                <span className="meta-badge difficulty">
                                    {getDifficultyLabel(rec.difficulty_level)}
                                </span>
                            </div>

                            <div className="course-stats">
                                <div className="stat">
                                    <span className="stat-icon">⏱️</span>
                                    <span>{rec.duration_hours}h</span>
                                </div>
                                <div className="stat">
                                    <span className="stat-icon">⭐</span>
                                    <span>{rec.rating.toFixed(1)}/5.0</span>
                                </div>
                                <div className="stat">
                                    <span className="stat-icon">🎯</span>
                                    <span>{(rec.score * 100).toFixed(0)}% match</span>
                                </div>
                            </div>

                            <div className="explanation-section">
                                <p className="why-recommended">
                                    <strong>Why recommended:</strong> {rec.why_recommended}
                                </p>

                                {rec.explanation && (
                                    <>
                                        <button
                                            className="show-details-button"
                                            onClick={() => toggleExplanation(rec.course_id)}
                                        >
                                            {showExplanation[rec.course_id] ? '▼' : '▶'} More details
                                        </button>

                                        {showExplanation[rec.course_id] && (
                                            <div className="explanation-details">
                                                <div className="primary-reason">
                                                    <strong>Primary Reason:</strong>
                                                    <p>{rec.explanation.primary_reason}</p>
                                                </div>

                                                {rec.explanation.supporting_reasons.length > 0 && (
                                                    <div className="supporting-reasons">
                                                        <strong>Also:</strong>
                                                        <ul>
                                                            {rec.explanation.supporting_reasons.map((reason, idx) => (
                                                                <li key={idx}>{reason}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}

                                                <div className="score-breakdown">
                                                    <strong>Score Breakdown:</strong>
                                                    <div className="breakdown-bars">
                                                        {Object.entries(rec.explanation.score_breakdown).map(([key, value]) => (
                                                            <div key={key} className="breakdown-item">
                                                                <span className="breakdown-label">
                                                                    {key.replace('_', ' ')}
                                                                </span>
                                                                <div className="breakdown-bar-container">
                                                                    <div
                                                                        className="breakdown-bar"
                                                                        style={{ width: `${value * 100}%` }}
                                                                    ></div>
                                                                </div>
                                                                <span className="breakdown-value">
                                                                    {(value * 100).toFixed(0)}%
                                                                </span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>

                        <div className="card-actions">
                            <button className="action-button primary">
                                View Course
                            </button>
                            <button className="action-button secondary">
                                Save for Later
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {recommendations.length === 0 && (
                <div className="empty-state">
                    <div className="empty-icon">📭</div>
                    <h3>No Recommendations Available</h3>
                    <p>We're working on finding the perfect courses for you.</p>
                    <button onClick={handleRefresh}>Refresh Now</button>
                </div>
            )}
        </div>
    );
};

export default RecommendationsDashboard;
