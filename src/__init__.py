"""
Tamkeen Recommendation System

A comprehensive course recommendation system with hybrid algorithm,
RESTful API, and React frontend components.

Modules:
    - recommendation_engine: Core hybrid recommendation algorithm
    - recommendation_api: FastAPI REST endpoints
    - recommendation_models: Pydantic data models
    - recommendation_scheduler: Background task scheduler
    - data_generators_*: Synthetic data generation utilities
"""

__version__ = "1.0.0"
__author__ = "Tamkeen Team"
__all__ = [
    "recommendation_engine",
    "recommendation_api",
    "recommendation_models",
    "recommendation_scheduler",
]
