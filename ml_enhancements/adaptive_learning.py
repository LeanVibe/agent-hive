"""
AdaptiveLearning - Self-improving learning system with continuous optimization

Implements adaptive learning algorithms that continuously improve system performance
based on feedback and historical patterns within the multi-agent coordination system.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

from .models import MLConfig, LearningMetrics


logger = logging.getLogger(__name__)


class AdaptiveLearning:
    """
    Self-improving learning system with continuous optimization and feedback integration.

    This component provides:
    - Self-improving learning algorithms
    - Feedback integration mechanisms
    - Model update and evaluation systems
    - Continuous optimization based on historical data
    """

    def __init__(self, config: Optional[MLConfig] = None, db_path: Optional[str] = None):
        """Initialize AdaptiveLearning with configuration and database."""
        self.config = config or MLConfig()
        self.db_path = db_path or "adaptive_learning.db"
        self.model_version = "1.0.0"

        # Adaptive models with online learning capability
        self.adaptive_models = {
            'performance_optimizer': SGDRegressor(
                learning_rate='adaptive',
                eta0=self.config.learning_rate,
                random_state=42
            ),
            'resource_optimizer': SGDRegressor(
                learning_rate='adaptive',
                eta0=self.config.learning_rate,
                random_state=42
            ),
            'task_scheduler': RandomForestRegressor(
                n_estimators=50,
                max_depth=8,
                random_state=42
            )
        }

        self.scalers = {
            model_name: StandardScaler() for model_name in self.adaptive_models.keys()
        }

        # Learning state tracking - properly typed
        self.learning_state: Dict[str, Any] = {
            'current_session': None,
            'adaptation_history': [],
            'last_update': {},
        }

        # Type-safe accessors
        self.model_performance: Dict[str, List[float]] = {}
        self.convergence_tracking: Dict[str, Dict[str, Any]] = {}

        # Feedback integration - properly typed
        self.feedback_buffer: Dict[str, List[Dict[str, Any]]] = {
            'positive_feedback': [],
            'negative_feedback': [],
            'performance_feedback': []
        }

        # Initialize database
        self._init_database()

        logger.info(f"AdaptiveLearning initialized with config: {self.config}")

    def _init_database(self) -> None:
        """Initialize SQLite database for adaptive learning data."""
        with sqlite3.connect(self.db_path) as conn:
            # Learning sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    session_id TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    initial_performance REAL NOT NULL,
                    final_performance REAL,
                    improvement_rate REAL,
                    samples_processed INTEGER NOT NULL,
                    convergence_time REAL,
                    hyperparameters TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # Feedback table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_data (
                    feedback_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    feedback_value REAL NOT NULL,
                    context TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    source_agent TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
                )
            """)

            # Model adaptations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_adaptations (
                    adaptation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    adaptation_type TEXT NOT NULL,
                    before_performance REAL NOT NULL,
                    after_performance REAL NOT NULL,
                    adaptation_details TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    success BOOLEAN NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
                )
            """)

            # Performance history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_history (
                    history_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    performance_metric REAL NOT NULL,
                    measurement_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    context TEXT,
                    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_model_time
                ON learning_sessions(model_type, start_time)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_session_type
                ON feedback_data(session_id, feedback_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_adaptations_session_time
                ON model_adaptations(session_id, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_session_time
                ON performance_history(session_id, timestamp)
            """)

            conn.commit()

    def start_learning_session(
        self,
        model_type: str,
        initial_context: Dict[str, Any],
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new adaptive learning session."""

        session_id = f"session_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Initialize session state
        self.learning_state['current_session'] = session_id
        self.model_performance[session_id] = []
        self.learning_state['adaptation_history'].append({
            'session_id': session_id,
            'start_time': datetime.now(),
            'model_type': model_type
        })

        # Reset feedback buffer for new session
        for buffer in self.feedback_buffer.values():
            buffer.clear()

        # Store session in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO learning_sessions
                (session_id, model_type, start_time, initial_performance,
                 samples_processed, hyperparameters, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, model_type, datetime.now(), 0.5,  # Default initial performance
                0, json.dumps(hyperparameters or {}), json.dumps(initial_context)
            ))
            conn.commit()

        logger.info(f"Started learning session: {session_id} for model: {model_type}")
        return session_id

    def provide_feedback(
        self,
        session_id: str,
        feedback_type: str,
        feedback_value: float,
        context: Dict[str, Any],
        source_agent: Optional[str] = None
    ) -> None:
        """Provide feedback for adaptive learning."""

        feedback_id = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Store in buffer for immediate use
        feedback_data = {
            'feedback_id': feedback_id,
            'type': feedback_type,
            'value': feedback_value,
            'context': context,
            'timestamp': datetime.now(),
            'source': source_agent
        }

        if feedback_type == 'positive':
            self.feedback_buffer['positive_feedback'].append(feedback_data)
        elif feedback_type == 'negative':
            self.feedback_buffer['negative_feedback'].append(feedback_data)
        else:
            self.feedback_buffer['performance_feedback'].append(feedback_data)

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO feedback_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id, session_id, feedback_type, feedback_value,
                json.dumps(context), datetime.now(), source_agent, json.dumps({})
            ))
            conn.commit()

        # Trigger immediate adaptation if enough feedback
        self._process_feedback_adaptation(session_id)

        logger.debug(f"Received {feedback_type} feedback: {feedback_value}")

    def adapt_model(
        self,
        session_id: str,
        model_type: str,
        training_data: List[Dict[str, Any]],
        target_values: List[float]
    ) -> LearningMetrics:
        """Adapt model based on new training data and feedback."""

        if model_type not in self.adaptive_models:
            raise ValueError(f"Unknown model type: {model_type}")

        model = self.adaptive_models[model_type]
        scaler = self.scalers[model_type]

        # Measure performance before adaptation
        before_performance = self._measure_model_performance(model_type, training_data, target_values)

        # Prepare training data
        X, y = self._prepare_training_data(training_data, target_values)

        if len(X) == 0:
            logger.warning(f"No training data available for {model_type}")
            return self._create_default_metrics(session_id)

        # Scale features
        if hasattr(model, 'partial_fit'):
            # Online learning for SGD models
            X_scaled = scaler.partial_fit(X).transform(X) if not hasattr(scaler, 'mean_') else scaler.transform(X)
            model.partial_fit(X_scaled, y)
        else:
            # Batch learning for tree models
            X_scaled = scaler.fit_transform(X)
            model.fit(X_scaled, y)

        # Measure performance after adaptation
        after_performance = self._measure_model_performance(model_type, training_data, target_values)

        # Calculate improvement metrics
        improvement_rate = (after_performance - before_performance) / max(before_performance, 0.001)
        accuracy_change = after_performance - before_performance

        # Update learning state
        session_performance = self.model_performance.get(session_id, [])
        session_performance.append(after_performance)
        self.model_performance[session_id] = session_performance

        # Create learning metrics
        metrics = LearningMetrics(
            learning_session_id=session_id,
            improvement_rate=improvement_rate,
            accuracy_change=accuracy_change,
            convergence_time=self._calculate_convergence_time(session_id),
            samples_processed=len(training_data),
            model_complexity=self._estimate_model_complexity(model),
            timestamp=datetime.now(),
            performance_history=session_performance.copy()
        )

        # Store adaptation in database
        self._store_adaptation(session_id, model_type, before_performance, after_performance, metrics)

        # Check for convergence
        self._check_convergence(session_id, model_type)

        logger.info(f"Adapted {model_type}: improvement={improvement_rate:.3f}")
        return metrics

    def _prepare_training_data(
        self,
        training_data: List[Dict[str, Any]],
        target_values: List[float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for model adaptation."""

        if not training_data or not target_values:
            return np.array([]), np.array([])

        # Extract features from training data
        feature_keys_set: set[str] = set()
        for data_point in training_data:
            feature_keys_set.update(data_point.keys())

        feature_keys: List[str] = sorted(list(feature_keys_set))

        # Create feature matrix
        X = []
        for data_point in training_data:
            feature_vector = [data_point.get(key, 0.0) for key in feature_keys]
            X.append(feature_vector)

        return np.array(X), np.array(target_values)

    def _measure_model_performance(
        self,
        model_type: str,
        test_data: List[Dict[str, Any]],
        target_values: List[float]
    ) -> float:
        """Measure current model performance."""

        model = self.adaptive_models[model_type]
        scaler = self.scalers[model_type]

        if not hasattr(scaler, 'mean_') or len(test_data) == 0:
            return 0.5  # Default performance

        try:
            X, y = self._prepare_training_data(test_data, target_values)
            if len(X) == 0:
                return 0.5

            X_scaled = scaler.transform(X)
            y_pred = model.predict(X_scaled)

            # Calculate R² score as performance metric
            if len(y) > 1:
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r2_score = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                return max(0.0, min(1.0, r2_score))
            else:
                # Single sample - use absolute error
                mae = abs(float(y[0]) - float(y_pred[0]))
                return max(0.0, 1.0 - mae)

        except Exception as e:
            logger.error(f"Error measuring performance for {model_type}: {e}")
            return 0.5

    def _estimate_model_complexity(self, model: Any) -> int:
        """Estimate model complexity score."""

        if hasattr(model, 'n_estimators'):
            # Tree-based models
            return int(model.n_estimators)
        elif hasattr(model, 'coef_'):
            # Linear models
            return len(model.coef_) if hasattr(model.coef_, '__len__') else 1
        else:
            return 1  # Default complexity

    def _calculate_convergence_time(self, session_id: str) -> float:
        """Calculate time to convergence for learning session."""
        performance_history = self.model_performance.get(session_id, [])
        if len(performance_history) < 3:
            return 0.0

        # Find when performance stabilized (variance < threshold for last 3 measurements)
        for i in range(2, len(performance_history)):
            recent_performance = performance_history[i-2:i+1]
            variance = np.var(recent_performance)

            if variance < 0.01:  # Convergence threshold
                return i * self.config.update_frequency  # Approximate time

        return len(performance_history) * self.config.update_frequency

    def _process_feedback_adaptation(self, session_id: str) -> None:
        """Process accumulated feedback for immediate adaptation."""

        # Check if enough feedback accumulated
        total_feedback = (
            len(self.feedback_buffer['positive_feedback']) +
            len(self.feedback_buffer['negative_feedback']) +
            len(self.feedback_buffer['performance_feedback'])
        )

        if total_feedback < 5:  # Minimum feedback threshold
            return

        # Extract learning signals from feedback
        adaptation_data = []
        target_values = []

        for feedback_list, weight in [
            (self.feedback_buffer['positive_feedback'], 1.0),
            (self.feedback_buffer['negative_feedback'], -0.5),
            (self.feedback_buffer['performance_feedback'], 0.0)
        ]:
            for feedback in feedback_list:
                # Convert feedback context to feature vector
                context_features = self._extract_features_from_context(feedback['context'])
                adaptation_data.append(context_features)

                if feedback['type'] == 'performance':
                    target_values.append(feedback['value'])
                else:
                    # Convert positive/negative feedback to performance score
                    base_performance = 0.7
                    target_values.append(base_performance + weight * 0.2)

        # Trigger adaptation if we have data
        if adaptation_data and target_values:
            try:
                # Determine which model to adapt based on feedback context
                model_type = self._determine_model_from_feedback(session_id)
                self.adapt_model(session_id, model_type, adaptation_data, target_values)

                # Clear processed feedback
                for buffer in self.feedback_buffer.values():
                    buffer.clear()

            except Exception as e:
                logger.error(f"Error processing feedback adaptation: {e}")

    def _extract_features_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant features from feedback context."""

        # Standard feature extraction
        features = {
            'agent_count': context.get('agent_count', 1),
            'task_complexity': context.get('task_complexity', 1.0),
            'resource_usage': context.get('resource_usage', 0.5),
            'queue_size': context.get('queue_size', 0),
            'success_rate': context.get('success_rate', 0.8),
            'response_time': context.get('response_time', 1.0)
        }

        # Add derived features
        features['efficiency_score'] = features['success_rate'] / max(features['response_time'], 0.1)
        features['load_factor'] = features['queue_size'] / max(features['agent_count'], 1)

        return features

    def _determine_model_from_feedback(self, session_id: str) -> str:
        """Determine which model to adapt based on feedback characteristics."""

        # Get session info to determine model type
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT model_type FROM learning_sessions WHERE session_id = ?
            """, (session_id,))
            result = cursor.fetchone()

            if result:
                return str(result[0])

        # Default to performance optimizer
        return 'performance_optimizer'

    def _check_convergence(self, session_id: str, model_type: str) -> bool:
        """Check if model has converged and should stop learning."""
        performance_history = self.model_performance.get(session_id, [])
        if len(performance_history) < 5:
            return False

        # Check recent performance variance
        recent_performance = performance_history[-5:]
        variance = np.var(recent_performance)

        convergence_threshold = 0.005  # 0.5% variance threshold
        converged = bool(variance < convergence_threshold)

        if converged:
            self.convergence_tracking[session_id] = {
                'converged': True,
                'convergence_time': self._calculate_convergence_time(session_id),
                'final_performance': recent_performance[-1],
                'convergence_variance': variance
            }

            logger.info(f"Model {model_type} converged in session {session_id}")

        return converged

    def _store_adaptation(
        self,
        session_id: str,
        model_type: str,
        before_performance: float,
        after_performance: float,
        metrics: LearningMetrics
    ) -> None:
        """Store adaptation details in database."""

        adaptation_id = f"adapt_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        adaptation_details = {
            'improvement_rate': metrics.improvement_rate,
            'accuracy_change': metrics.accuracy_change,
            'samples_processed': metrics.samples_processed,
            'model_complexity': metrics.model_complexity
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO model_adaptations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                adaptation_id, session_id, model_type, 'feedback_adaptation',
                before_performance, after_performance, json.dumps(adaptation_details),
                datetime.now(), after_performance > before_performance
            ))

            # Also store performance history point
            history_id = f"perf_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            conn.execute("""
                INSERT INTO performance_history VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                history_id, session_id, model_type, after_performance,
                'post_adaptation', datetime.now(), json.dumps({})
            ))

            conn.commit()

    def _create_default_metrics(self, session_id: str) -> LearningMetrics:
        """Create default learning metrics when adaptation fails."""

        return LearningMetrics(
            learning_session_id=session_id,
            improvement_rate=0.0,
            accuracy_change=0.0,
            convergence_time=0.0,
            samples_processed=0,
            model_complexity=1,
            timestamp=datetime.now(),
            metadata={'status': 'no_data'}
        )

    def end_learning_session(self, session_id: str) -> Dict[str, Any]:
        """End learning session and return summary metrics."""

        # Get final performance
        performance_history = self.model_performance.get(session_id, [])
        final_performance = performance_history[-1] if performance_history else 0.5

        # Calculate session metrics
        convergence_info = self.convergence_tracking.get(session_id, {})

        session_summary = {
            'session_id': session_id,
            'final_performance': final_performance,
            'total_adaptations': len(performance_history),
            'converged': convergence_info.get('converged', False),
            'convergence_time': convergence_info.get('convergence_time', 0),
            'improvement_trend': self._calculate_improvement_trend(performance_history),
            'end_time': datetime.now()
        }

        # Update database
        with sqlite3.connect(self.db_path) as conn:
            improvement_rate = self._calculate_session_improvement_rate(performance_history)
            conn.execute("""
                UPDATE learning_sessions
                SET end_time = ?, final_performance = ?, improvement_rate = ?,
                    convergence_time = ?
                WHERE session_id = ?
            """, (
                datetime.now(), final_performance, improvement_rate,
                convergence_info.get('convergence_time', 0), session_id
            ))
            conn.commit()

        # Clean up session state
        if session_id in self.learning_state['model_performance']:
            del self.learning_state['model_performance'][session_id]

        if self.learning_state['current_session'] == session_id:
            self.learning_state['current_session'] = None

        logger.info(f"Ended learning session {session_id}: {session_summary}")
        return session_summary

    def _calculate_improvement_trend(self, performance_history: List[float]) -> float:
        """Calculate overall improvement trend for session."""

        if len(performance_history) < 2:
            return 0.0

        # Simple linear trend
        x = np.arange(len(performance_history))
        y = np.array(performance_history)

        # Calculate slope
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)

        return float(slope)

    def _calculate_session_improvement_rate(self, performance_history: List[float]) -> float:
        """Calculate overall improvement rate for session."""

        if len(performance_history) < 2:
            return 0.0

        initial_performance = performance_history[0]
        final_performance = performance_history[-1]

        if initial_performance <= 0:
            return 0.0

        return (final_performance - initial_performance) / initial_performance

    def get_learning_insights(self, model_type: Optional[str] = None) -> Dict[str, Any]:
        """Get insights from adaptive learning patterns."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Session statistics
            if model_type:
                cursor.execute("""
                    SELECT COUNT(*), AVG(improvement_rate), AVG(final_performance),
                           AVG(convergence_time), AVG(samples_processed)
                    FROM learning_sessions
                    WHERE model_type = ? AND final_performance IS NOT NULL
                """, (model_type,))
            else:
                cursor.execute("""
                    SELECT COUNT(*), AVG(improvement_rate), AVG(final_performance),
                           AVG(convergence_time), AVG(samples_processed)
                    FROM learning_sessions
                    WHERE final_performance IS NOT NULL
                """)

            session_stats = cursor.fetchone()

            # Adaptation success rates
            cursor.execute("""
                SELECT model_type, COUNT(*),
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
                FROM model_adaptations
                GROUP BY model_type
            """)

            adaptation_stats = {}
            for model, total_adaptations, success_rate in cursor.fetchall():
                adaptation_stats[model] = {
                    'total_adaptations': total_adaptations,
                    'success_rate': success_rate
                }

            # Recent performance trends
            cursor.execute("""
                SELECT model_type, AVG(performance_metric)
                FROM performance_history
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY model_type
            """)

            recent_performance = dict(cursor.fetchall())

            return {
                'session_statistics': {
                    'total_sessions': session_stats[0] if session_stats else 0,
                    'avg_improvement_rate': session_stats[1] if session_stats else 0,
                    'avg_final_performance': session_stats[2] if session_stats else 0,
                    'avg_convergence_time': session_stats[3] if session_stats else 0,
                    'avg_samples_processed': session_stats[4] if session_stats else 0
                },
                'adaptation_statistics': adaptation_stats,
                'recent_performance_7days': recent_performance,
                'model_status': {
                    'current_session': self.learning_state['current_session'],
                    'active_models': list(self.adaptive_models.keys()),
                    'convergence_tracking': len(self.convergence_tracking)
                },
                'config': {
                    'learning_rate': self.config.learning_rate,
                    'update_frequency': self.config.update_frequency,
                    'learning_enabled': self.config.learning_enabled
                }
            }

    def predict_with_adaptation(
        self,
        model_type: str,
        features: Dict[str, float],
        confidence_threshold: float = 0.7
    ) -> Tuple[float, float, bool]:
        """Make prediction with adaptive model and indicate if adaptation needed."""

        if model_type not in self.adaptive_models:
            raise ValueError(f"Unknown model type: {model_type}")

        model = self.adaptive_models[model_type]
        scaler = self.scalers[model_type]

        # Prepare feature vector
        feature_vector = [features.get(key, 0.0) for key in sorted(features.keys())]

        try:
            if hasattr(scaler, 'mean_'):
                X_scaled = scaler.transform([feature_vector])
                prediction = model.predict(X_scaled)[0]

                # Estimate prediction confidence
                confidence = self._estimate_prediction_confidence(model_type, features)

                # Determine if adaptation needed
                needs_adaptation = confidence < confidence_threshold

                return prediction, confidence, needs_adaptation
            else:
                # Model not trained yet
                return 0.5, 0.1, True

        except Exception as e:
            logger.error(f"Error in prediction with {model_type}: {e}")
            return 0.5, 0.1, True

    def _estimate_prediction_confidence(
        self,
        model_type: str,
        features: Dict[str, float]
    ) -> float:
        """Estimate confidence in prediction based on model state."""

        # Base confidence from recent performance
        session_id = self.learning_state['current_session']
        if session_id and session_id in self.learning_state['model_performance']:
            recent_performance = self.learning_state['model_performance'][session_id]
            if recent_performance:
                base_confidence = float(recent_performance[-1])
                # Adjust based on feature quality for active sessions
                feature_completeness = min(1.0, len(features) / 3.0)  # Assuming 3 key features minimum
                confidence = base_confidence * max(0.7, feature_completeness)  # Don't penalize too much
            else:
                confidence = 0.5
        else:
            # No active session, return base confidence
            confidence = 0.5

        return max(0.1, min(0.95, confidence))

    def get_adaptation_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for improving adaptive learning performance."""

        recommendations = []

        # Check recent session performance
        recent_sessions = self._get_recent_sessions(days=7)

        if not recent_sessions:
            recommendations.append({
                'type': 'initialization',
                'priority': 'high',
                'description': 'Start adaptive learning sessions to begin optimization',
                'action': 'Initialize learning sessions for key models'
            })

        # Analyze convergence issues
        slow_convergence = [s for s in recent_sessions if s.get('convergence_time', 0) > 1000]
        if slow_convergence:
            recommendations.append({
                'type': 'convergence',
                'priority': 'medium',
                'description': f'Slow convergence detected in {len(slow_convergence)} sessions',
                'action': 'Consider adjusting learning rate or model complexity'
            })

        # Check for low improvement rates
        low_improvement = [s for s in recent_sessions if s.get('improvement_rate', 0) < 0.1]
        if low_improvement:
            recommendations.append({
                'type': 'improvement',
                'priority': 'medium',
                'description': f'Low improvement rates in {len(low_improvement)} sessions',
                'action': 'Increase feedback frequency or review training data quality'
            })

        # Check feedback utilization
        total_feedback = sum(len(buffer) for buffer in self.feedback_buffer.values())
        if total_feedback > 20:
            recommendations.append({
                'type': 'feedback',
                'priority': 'high',
                'description': f'Large feedback buffer ({total_feedback} items)',
                'action': 'Process accumulated feedback to improve model performance'
            })

        return recommendations

    def _get_recent_sessions(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent learning sessions data."""

        cutoff_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT session_id, model_type, improvement_rate, final_performance,
                       convergence_time, samples_processed
                FROM learning_sessions
                WHERE start_time > ? AND final_performance IS NOT NULL
            """, (cutoff_date,))

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'model_type': row[1],
                    'improvement_rate': row[2],
                    'final_performance': row[3],
                    'convergence_time': row[4],
                    'samples_processed': row[5]
                })

            return sessions

    def cleanup_old_learning_data(self, days_to_keep: int = 60) -> int:
        """Clean up old learning data."""

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with sqlite3.connect(self.db_path) as conn:
            # Clean up old sessions
            cursor = conn.execute("""
                DELETE FROM learning_sessions WHERE start_time < ?
            """, (cutoff_date,))
            sessions_deleted = cursor.rowcount

            # Clean up orphaned feedback
            cursor = conn.execute("""
                DELETE FROM feedback_data
                WHERE session_id NOT IN (SELECT session_id FROM learning_sessions)
            """)
            feedback_deleted = cursor.rowcount

            # Clean up orphaned adaptations
            cursor = conn.execute("""
                DELETE FROM model_adaptations
                WHERE session_id NOT IN (SELECT session_id FROM learning_sessions)
            """)
            adaptations_deleted = cursor.rowcount

            # Clean up orphaned performance history
            cursor = conn.execute("""
                DELETE FROM performance_history
                WHERE session_id NOT IN (SELECT session_id FROM learning_sessions)
            """)
            history_deleted = cursor.rowcount

            conn.commit()

        total_deleted = sessions_deleted + feedback_deleted + adaptations_deleted + history_deleted
        logger.info(f"Cleaned up {total_deleted} learning records")
        return total_deleted
