"""
LeanVibe Agent Hive ML Enhancements

Advanced machine learning components for intelligent pattern recognition,
predictive analytics, and adaptive learning within the multi-agent orchestration system.

Components:
- PatternOptimizer: ML-based workflow optimization and pattern recognition
- PredictiveAnalytics: Performance prediction and resource forecasting  
- AdaptiveLearning: Self-improving learning system with continuous optimization
"""

from .pattern_optimizer import PatternOptimizer
from .predictive_analytics import PredictiveAnalytics
from .adaptive_learning import AdaptiveLearning
from .models import (
    MLConfig,
    PatternData, 
    AnalyticsResult,
    LearningMetrics
)

__all__ = [
    'PatternOptimizer',
    'PredictiveAnalytics', 
    'AdaptiveLearning',
    'MLConfig',
    'PatternData',
    'AnalyticsResult',
    'LearningMetrics'
]

__version__ = '1.0.0'