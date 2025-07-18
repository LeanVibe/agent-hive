"""
ML Enhancement Data Models

Data structures and type definitions for the ML enhancement components.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import numpy as np


@dataclass
class MLConfig:
    """Configuration for ML enhancement components."""

    # PatternOptimizer settings
    pattern_analysis_window: int = 1000
    pattern_optimization_threshold: float = 0.15
    pattern_enabled: bool = True

    # PredictiveAnalytics settings
    forecasting_horizon: int = 60
    accuracy_threshold: float = 0.9
    analytics_enabled: bool = True

    # AdaptiveLearning settings
    learning_rate: float = 0.01
    update_frequency: int = 100
    learning_enabled: bool = True

    # General ML settings
    min_data_points: int = 10
    confidence_threshold: float = 0.75
    max_model_age_days: int = 30

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if not 0 < self.learning_rate < 1:
            raise ValueError(f"Learning rate must be between 0 and 1, got {self.learning_rate}")

        if not 0 < self.confidence_threshold <= 1:
            raise ValueError(f"Confidence threshold must be between 0 and 1, got {self.confidence_threshold}")

        if not 0 < self.accuracy_threshold <= 1:
            raise ValueError(f"Accuracy threshold must be between 0 and 1, got {self.accuracy_threshold}")

        if not 0 < self.pattern_optimization_threshold < 1:
            raise ValueError(f"Pattern optimization threshold must be between 0 and 1, got {self.pattern_optimization_threshold}")

        if self.pattern_analysis_window <= 0:
            raise ValueError(f"Pattern analysis window must be positive, got {self.pattern_analysis_window}")

        if self.forecasting_horizon <= 0:
            raise ValueError(f"Forecasting horizon must be positive, got {self.forecasting_horizon}")

        if self.update_frequency <= 0:
            raise ValueError(f"Update frequency must be positive, got {self.update_frequency}")

        if self.min_data_points <= 0:
            raise ValueError(f"Min data points must be positive, got {self.min_data_points}")

        if self.max_model_age_days <= 0:
            raise ValueError(f"Max model age days must be positive, got {self.max_model_age_days}")


@dataclass
class PatternData:
    """Data structure for workflow patterns and optimization results."""

    pattern_id: str
    workflow_type: str
    performance_metrics: Dict[str, float]
    optimization_score: float
    confidence: float
    sample_count: int
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'pattern_id': self.pattern_id,
            'workflow_type': self.workflow_type,
            'performance_metrics': self.performance_metrics,
            'optimization_score': self.optimization_score,
            'confidence': self.confidence,
            'sample_count': self.sample_count,
            'last_updated': self.last_updated.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class AnalyticsResult:
    """Results from predictive analytics operations."""

    prediction_type: str
    predicted_value: float
    confidence_interval: tuple[float, float]
    accuracy_score: float
    timestamp: datetime
    features_used: List[str]
    model_version: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'prediction_type': self.prediction_type,
            'predicted_value': self.predicted_value,
            'confidence_interval': self.confidence_interval,
            'accuracy_score': self.accuracy_score,
            'timestamp': self.timestamp.isoformat(),
            'features_used': self.features_used,
            'model_version': self.model_version,
            'metadata': self.metadata
        }


@dataclass
class LearningMetrics:
    """Metrics for adaptive learning performance."""

    learning_session_id: str
    improvement_rate: float
    accuracy_change: float
    convergence_time: float
    samples_processed: int
    model_complexity: int
    timestamp: datetime
    performance_history: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_performance_sample(self, performance: float) -> None:
        """Add new performance sample to history."""
        self.performance_history.append(performance)
        # Keep only last 100 samples for memory efficiency
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

    def get_improvement_trend(self) -> float:
        """Calculate improvement trend from performance history."""
        if len(self.performance_history) < 2:
            return 0.0

        # Simple linear trend calculation
        x = np.arange(len(self.performance_history))
        y = np.array(self.performance_history)

        if len(x) < 2:
            return 0.0

        # Calculate slope using least squares
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        return float(slope)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'learning_session_id': self.learning_session_id,
            'improvement_rate': self.improvement_rate,
            'accuracy_change': self.accuracy_change,
            'convergence_time': self.convergence_time,
            'samples_processed': self.samples_processed,
            'model_complexity': self.model_complexity,
            'timestamp': self.timestamp.isoformat(),
            'performance_history': self.performance_history,
            'improvement_trend': self.get_improvement_trend(),
            'metadata': self.metadata
        }


@dataclass
class ModelMetadata:
    """Metadata for ML models and their performance."""

    model_id: str
    model_type: str
    version: str
    training_data_size: int
    validation_score: float
    feature_importance: Dict[str, float]
    hyperparameters: Dict[str, Any]
    created_at: datetime
    last_updated: datetime
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'model_id': self.model_id,
            'model_type': self.model_type,
            'version': self.version,
            'training_data_size': self.training_data_size,
            'validation_score': self.validation_score,
            'feature_importance': self.feature_importance,
            'hyperparameters': self.hyperparameters,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'is_active': self.is_active
        }


@dataclass
class ResourcePrediction:
    """Resource usage predictions and forecasts."""

    resource_type: str  # 'cpu', 'memory', 'disk', 'network'
    current_usage: float
    predicted_usage: float
    prediction_horizon: int  # minutes into future
    confidence: float
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    recommended_action: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'resource_type': self.resource_type,
            'current_usage': self.current_usage,
            'predicted_usage': self.predicted_usage,
            'prediction_horizon': self.prediction_horizon,
            'confidence': self.confidence,
            'trend_direction': self.trend_direction,
            'recommended_action': self.recommended_action,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class WorkflowOptimization:
    """Optimization recommendations for workflows."""

    workflow_id: str
    optimization_type: str
    current_performance: float
    predicted_improvement: float
    confidence: float
    recommended_changes: List[str]
    effort_estimate: str  # 'low', 'medium', 'high'
    impact_score: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'workflow_id': self.workflow_id,
            'optimization_type': self.optimization_type,
            'current_performance': self.current_performance,
            'predicted_improvement': self.predicted_improvement,
            'confidence': self.confidence,
            'recommended_changes': self.recommended_changes,
            'effort_estimate': self.effort_estimate,
            'impact_score': self.impact_score,
            'timestamp': self.timestamp.isoformat()
        }
