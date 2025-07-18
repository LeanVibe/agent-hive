"""
PatternOptimizer - ML-based workflow optimization and pattern recognition

Analyzes historical workflow data to identify patterns and optimize task distribution
and execution strategies within the multi-agent coordination system.
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score

from .models import MLConfig, PatternData, WorkflowOptimization


logger = logging.getLogger(__name__)


class PatternOptimizer:
    """
    Advanced pattern recognition and workflow optimization using machine learning.

    This component analyzes historical workflow data to:
    - Identify recurring patterns in task execution
    - Optimize task distribution strategies
    - Predict optimal resource allocation
    - Recommend workflow improvements
    """

    def __init__(self, config: Optional[MLConfig] = None, db_path: Optional[str] = None):
        """Initialize PatternOptimizer with configuration and database."""
        self.config = config or MLConfig()
        self.db_path = db_path or "pattern_optimizer.db"
        self.scaler = StandardScaler()
        self.cluster_model: Optional[KMeans] = None
        self.performance_model: Optional[RandomForestRegressor] = None
        self.model_version = "1.0.0"

        # Initialize database
        self._init_database()

        # Feature columns for ML models
        self.feature_columns = [
            'task_complexity', 'agent_count', 'resource_usage',
            'queue_size', 'time_of_day', 'day_of_week',
            'historical_success_rate', 'avg_completion_time'
        ]

        logger.info(f"PatternOptimizer initialized with config: {self.config}")

    def _init_database(self) -> None:
        """Initialize SQLite database for pattern storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    workflow_type TEXT NOT NULL,
                    feature_hash TEXT NOT NULL,
                    performance_score REAL NOT NULL,
                    optimization_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    execution_id TEXT PRIMARY KEY,
                    workflow_type TEXT NOT NULL,
                    features TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    success BOOLEAN NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    agent_id TEXT,
                    resource_usage TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_type
                ON workflow_patterns(workflow_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_type_time
                ON workflow_executions(workflow_type, timestamp)
            """)

            conn.commit()

    def record_workflow_execution(
        self,
        execution_id: str,
        workflow_type: str,
        features: Dict[str, float],
        performance_metrics: Dict[str, float],
        execution_time: float,
        success: bool,
        agent_id: Optional[str] = None,
        resource_usage: Optional[Dict[str, float]] = None
    ) -> None:
        """Record a workflow execution for pattern analysis."""

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflow_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                workflow_type,
                json.dumps(features),
                json.dumps(performance_metrics),
                execution_time,
                success,
                datetime.now(),
                agent_id,
                json.dumps(resource_usage or {})
            ))
            conn.commit()

        # Update patterns after recording
        if success:  # Only learn from successful executions
            self._update_patterns(workflow_type, features, performance_metrics)

        logger.debug(f"Recorded workflow execution: {execution_id}")

    def _update_patterns(
        self,
        workflow_type: str,
        features: Dict[str, float],
        performance_metrics: Dict[str, float]
    ) -> None:
        """Update pattern data based on new execution."""

        feature_hash = self._hash_features(features)
        performance_score = self._calculate_performance_score(performance_metrics)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if pattern exists
            cursor.execute("""
                SELECT sample_count, performance_score, confidence
                FROM workflow_patterns
                WHERE workflow_type = ? AND feature_hash = ?
            """, (workflow_type, feature_hash))

            result = cursor.fetchone()

            if result:
                # Update existing pattern
                sample_count, old_score, old_confidence = result
                new_sample_count = sample_count + 1

                # Weighted average of performance scores
                alpha = 1.0 / new_sample_count
                new_score = (1 - alpha) * old_score + alpha * performance_score

                # Update confidence based on sample count
                new_confidence = min(0.95, 0.5 + 0.45 * (new_sample_count / 100))

                optimization_score = self._calculate_optimization_score(
                    new_score, new_confidence, new_sample_count
                )

                cursor.execute("""
                    UPDATE workflow_patterns
                    SET performance_score = ?, optimization_score = ?,
                        confidence = ?, sample_count = ?, last_updated = ?
                    WHERE workflow_type = ? AND feature_hash = ?
                """, (
                    new_score, optimization_score, new_confidence,
                    new_sample_count, datetime.now(), workflow_type, feature_hash
                ))
            else:
                # Create new pattern
                pattern_id = f"{workflow_type}_{feature_hash[:8]}"
                optimization_score = self._calculate_optimization_score(
                    performance_score, 0.5, 1
                )

                cursor.execute("""
                    INSERT INTO workflow_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_id, workflow_type, feature_hash, performance_score,
                    optimization_score, 0.5, 1, datetime.now(), datetime.now(),
                    json.dumps({})
                ))

            conn.commit()

    def _hash_features(self, features: Dict[str, float]) -> str:
        """Create hash of feature values for pattern matching."""
        # Normalize feature values to create consistent patterns
        normalized_features: Dict[str, Any] = {}
        for key, value in features.items():
            if key in ['task_complexity', 'agent_count', 'queue_size']:
                # Bin into categories for better pattern matching
                normalized_features[key] = int(value // 1)
            elif key in ['resource_usage', 'historical_success_rate']:
                # Bin into 10% increments
                normalized_features[key] = round(float(value), 1)
            else:
<<<<<<< HEAD
                normalized_features[key] = value

||||||| 48e9100
                normalized_features[key] = value
        
=======
                normalized_features[key] = float(value)

>>>>>>> new-work/performance-Jul-17-0823
        feature_str = json.dumps(normalized_features, sort_keys=True)
        return hashlib.sha256(feature_str.encode()).hexdigest()[:16]

    def _calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall performance score from metrics."""
        weights = {
            'completion_time': 0.3,  # Lower is better (inverted later)
            'resource_efficiency': 0.3,  # Higher is better
            'success_rate': 0.4,  # Higher is better
            'error_count': 0.2,  # Lower is better (inverted later)
            'agent_utilization': 0.2  # Higher is better
        }

        score = 0.0
        total_weight = 0.0

        for metric, value in metrics.items():
            if metric in weights:
                weight = weights[metric]
                # Invert metrics where lower is better
                if metric in ['completion_time', 'error_count']:
                    # Convert to "goodness" scale: 1 - value
                    adjusted_value = 1.0 - value
                else:
                    adjusted_value = value

                score += weight * adjusted_value
                total_weight += weight

        if total_weight > 0:
            score = score / total_weight

        # Already normalized to 0-1 range due to input constraints
        return max(0.0, min(1.0, score))

    def _calculate_optimization_score(
        self,
        performance_score: float,
        confidence: float,
        sample_count: int
    ) -> float:
        """Calculate optimization potential score."""
        # Higher performance and confidence mean lower optimization potential
        base_score = (1.0 - performance_score) * confidence

        # Scale by sample count (more samples = more reliable)
        sample_factor = min(1.0, sample_count / 50)

        return base_score * sample_factor

    def analyze_patterns(self, workflow_type: Optional[str] = None) -> List[PatternData]:
        """Analyze workflow patterns and return optimization opportunities."""

        with sqlite3.connect(self.db_path) as conn:
            if workflow_type:
                query = """
                    SELECT * FROM workflow_patterns
                    WHERE workflow_type = ? AND sample_count >= ?
                    ORDER BY optimization_score DESC
                """
                cursor = conn.execute(query, (workflow_type, self.config.min_data_points))
            else:
                query = """
                    SELECT * FROM workflow_patterns
                    WHERE sample_count >= ?
                    ORDER BY optimization_score DESC
                """
                cursor = conn.execute(query, (self.config.min_data_points,))

            patterns = []
            for row in cursor.fetchall():
                (pattern_id, wf_type, feature_hash, perf_score, opt_score,
                 confidence, sample_count, created_at, last_updated, metadata) = row

                pattern = PatternData(
                    pattern_id=pattern_id,
                    workflow_type=wf_type,
                    performance_metrics={'performance_score': perf_score},
                    optimization_score=opt_score,
                    confidence=confidence,
                    sample_count=sample_count,
                    last_updated=datetime.fromisoformat(last_updated),
                    metadata=json.loads(metadata or '{}')
                )
                patterns.append(pattern)

        logger.info(f"Analyzed {len(patterns)} patterns for workflow: {workflow_type}")
        return patterns

    def get_optimization_recommendations(
        self,
        workflow_type: str,
        current_features: Dict[str, float]
    ) -> List[WorkflowOptimization]:
        """Get optimization recommendations for a specific workflow."""

        patterns = self.analyze_patterns(workflow_type)
        if not patterns:
            return []

        recommendations = []
        current_score = self._get_current_performance(workflow_type, current_features)

        for pattern in patterns[:5]:  # Top 5 patterns
            if pattern.confidence < self.config.confidence_threshold:
                continue

            predicted_improvement = pattern.performance_metrics['performance_score'] - current_score
            if predicted_improvement <= 0:
                continue

            # Generate recommendations based on pattern analysis
            changes = self._generate_optimization_changes(pattern, current_features)

            recommendation = WorkflowOptimization(
                workflow_id=f"{workflow_type}_{pattern.pattern_id}",
                optimization_type="pattern_based",
                current_performance=current_score,
                predicted_improvement=predicted_improvement,
                confidence=pattern.confidence,
                recommended_changes=changes,
                effort_estimate=self._estimate_effort(changes),
                impact_score=predicted_improvement * pattern.confidence
            )

            recommendations.append(recommendation)

        # Sort by impact score
        recommendations.sort(key=lambda x: x.impact_score, reverse=True)

        logger.info(f"Generated {len(recommendations)} optimization recommendations")
        return recommendations

    def _get_current_performance(
        self,
        workflow_type: str,
        features: Dict[str, float]
    ) -> float:
        """Get current performance score for workflow with given features."""

        # Look for similar patterns
        feature_hash = self._hash_features(features)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT performance_score FROM workflow_patterns
                WHERE workflow_type = ? AND feature_hash = ?
            """, (workflow_type, feature_hash))

            result = cursor.fetchone()
            if result:
                return float(result[0])

        # Fallback to average performance for workflow type
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT AVG(performance_score) FROM workflow_patterns
                WHERE workflow_type = ?
            """, (workflow_type,))

            result = cursor.fetchone()
            return float(result[0]) if result and result[0] is not None else 0.5

    def _generate_optimization_changes(
        self,
        pattern: PatternData,
        current_features: Dict[str, float]
    ) -> List[str]:
        """Generate specific optimization recommendations."""
        changes = []

        # This is a simplified heuristic approach
        # In production, this could be more sophisticated

        if pattern.performance_metrics.get('performance_score', 0) > 0.8:
            if current_features.get('agent_count', 1) < 3:
                changes.append("Consider increasing agent count to 3-5 for better parallel processing")

            if current_features.get('resource_usage', 0) < 0.6:
                changes.append("Increase resource allocation to improve execution speed")

            if current_features.get('queue_size', 0) > 10:
                changes.append("Implement queue optimization to reduce task backlog")

        if not changes:
            changes.append("Optimize based on high-performing pattern analysis")

        return changes

    async def get_task_patterns(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get task execution patterns for intelligent decision making."""

        try:
            with sqlite3.connect(self.db_path) as conn:
                if task_type:
                    query = """
                        SELECT workflow_type, performance_score, optimization_score, confidence, sample_count, metadata
                        FROM workflow_patterns
                        WHERE workflow_type LIKE ? AND sample_count >= ?
                        ORDER BY performance_score DESC
                    """
                    cursor = conn.execute(query, (f"%{task_type}%", self.config.min_data_points))
                else:
                    query = """
                        SELECT workflow_type, performance_score, optimization_score, confidence, sample_count, metadata
                        FROM workflow_patterns
                        WHERE sample_count >= ?
                        ORDER BY performance_score DESC
                    """
                    cursor = conn.execute(query, (self.config.min_data_points,))

                patterns = []
                for row in cursor.fetchall():
                    workflow_type, perf_score, opt_score, confidence, sample_count, metadata = row

                    pattern = {
                        'workflow_type': workflow_type,
                        'performance_score': perf_score,
                        'optimization_score': opt_score,
                        'confidence': confidence,
                        'sample_count': sample_count,
                        'metadata': json.loads(metadata or '{}'),
                        'recommended_strategy': self._get_recommended_strategy(perf_score, opt_score)
                    }
                    patterns.append(pattern)

                logger.info(f"Retrieved {len(patterns)} task patterns for type: {task_type}")
                return patterns

        except Exception as e:
            logger.error(f"Error retrieving task patterns: {e}")
            return []

    def _get_recommended_strategy(self, performance_score: float, optimization_score: float) -> str:
        """Get recommended allocation strategy based on pattern analysis."""

        if performance_score > 0.8 and optimization_score < 0.3:
            return "maintain_current"
        elif performance_score > 0.6 and optimization_score < 0.5:
            return "minor_optimization"
        elif performance_score < 0.5 or optimization_score > 0.7:
            return "major_restructure"
        else:
            return "gradual_improvement"

    def _estimate_effort(self, changes: List[str]) -> str:
        """Estimate implementation effort for optimization changes."""
        if not changes:
            return "low"

        effort_keywords = {
            'high': ['architecture', 'redesign', 'refactor'],
            'medium': ['increase', 'optimize', 'implement'],
            'low': ['adjust', 'tune', 'modify']
        }

        for change in changes:
            change_lower = change.lower()
            for effort, keywords in effort_keywords.items():
                if any(keyword in change_lower for keyword in keywords):
                    return effort

        return "medium"  # Default

    def train_models(self) -> Dict[str, Any]:
        """Train ML models for pattern recognition and optimization."""

        try:
            # Get training data
            training_data = self._prepare_training_data()
            if len(training_data) < self.config.min_data_points:
                logger.warning(f"Insufficient training data: {len(training_data)} samples")
                return {'error': 'insufficient_data'}

            X = training_data[self.feature_columns].values
            y = training_data['performance_score'].values

            # Train clustering model for pattern grouping
            try:
                self.cluster_model = KMeans(n_clusters=min(5, len(training_data) // 10), random_state=42)
                X_scaled = self.scaler.fit_transform(X)
                self.cluster_model.fit(X_scaled)
            except (ValueError, MemoryError) as e:
                logger.error(f"Clustering model training failed: {e}")
                return {'error': 'clustering_failed', 'details': str(e)}

            # Train performance prediction model
            try:
                self.performance_model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
                self.performance_model.fit(X, y)
            except (ValueError, MemoryError) as e:
                logger.error(f"Performance model training failed: {e}")
                return {'error': 'performance_model_failed', 'details': str(e)}

            # Calculate model performance
            try:
                y_pred = self.performance_model.predict(X)
                mse = mean_squared_error(y, y_pred)
                r2 = r2_score(y, y_pred)
            except Exception as e:
                logger.error(f"Model evaluation failed: {e}")
                mse, r2 = float('inf'), 0.0

            metrics = {
                'model_version': self.model_version,
                'training_samples': float(len(training_data)),
                'mse': float(mse),
                'r2_score': float(r2),
                'clusters': float(self.cluster_model.n_clusters if self.cluster_model else 0)
            }

            logger.info(f"Model training completed: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Unexpected error during model training: {e}")
            return {'error': 'training_failed', 'details': str(e)}

    def _prepare_training_data(self) -> pd.DataFrame:
        """Prepare training data from workflow executions."""

        with sqlite3.connect(self.db_path) as conn:
            # Get recent successful executions
            cutoff_date = datetime.now() - timedelta(days=self.config.max_model_age_days)

            query = """
                SELECT workflow_type, features, performance_metrics, execution_time,
                       timestamp, agent_id, resource_usage
                FROM workflow_executions
                WHERE success = 1 AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """

            cursor = conn.execute(query, (cutoff_date, self.config.pattern_analysis_window))

            data = []
            for row in cursor.fetchall():
                (wf_type, features_json, metrics_json, exec_time,
                 timestamp, agent_id, resource_json) = row

                features = json.loads(features_json)
                metrics = json.loads(metrics_json)
                resource_usage = json.loads(resource_json or '{}')

                # Extract required features with defaults
                record = {
                    'workflow_type': wf_type,
                    'task_complexity': features.get('task_complexity', 1.0),
                    'agent_count': features.get('agent_count', 1),
                    'resource_usage': resource_usage.get('cpu', 0.5),
                    'queue_size': features.get('queue_size', 0),
                    'time_of_day': datetime.fromisoformat(timestamp).hour,
                    'day_of_week': datetime.fromisoformat(timestamp).weekday(),
                    'historical_success_rate': features.get('historical_success_rate', 0.8),
                    'avg_completion_time': exec_time,
                    'performance_score': self._calculate_performance_score(metrics)
                }
                data.append(record)

        return pd.DataFrame(data)

    def predict_performance(self, features: Dict[str, float]) -> Tuple[float, float]:
        """Predict performance for given feature set."""

        if not self.performance_model:
            logger.warning("Performance model not trained")
            return 0.5, 0.1  # Default prediction with low confidence

        # Prepare feature vector
        feature_vector = []
        for col in self.feature_columns:
            feature_vector.append(features.get(col, 0.0))

        # Make prediction
        prediction = self.performance_model.predict([feature_vector])[0]

        # Estimate confidence based on feature similarity to training data
        confidence = self._estimate_prediction_confidence(features)

        return prediction, confidence

    def _estimate_prediction_confidence(self, features: Dict[str, float]) -> float:
        """Estimate confidence in prediction based on training data similarity."""

        if not self.cluster_model:
            return 0.5

        # Transform features and find nearest cluster
        feature_vector = [features.get(col, 0.0) for col in self.feature_columns]
        feature_scaled = self.scaler.transform([feature_vector])

        # Distance to nearest cluster center
        distances = self.cluster_model.transform(feature_scaled)[0]
        min_distance = float(min(distances))

        # Convert distance to confidence (lower distance = higher confidence)
        confidence = max(0.1, 1.0 - min_distance / 10.0)

        return float(min(confidence, 0.95))

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored patterns and performance."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Pattern counts by workflow type
            cursor.execute("""
                SELECT workflow_type, COUNT(*), AVG(performance_score),
                       AVG(optimization_score), AVG(confidence)
                FROM workflow_patterns
                GROUP BY workflow_type
            """)

            workflow_stats = {}
            for row in cursor.fetchall():
                wf_type, count, avg_perf, avg_opt, avg_conf = row
                workflow_stats[wf_type] = {
                    'pattern_count': count,
                    'avg_performance': avg_perf,
                    'avg_optimization_potential': avg_opt,
                    'avg_confidence': avg_conf
                }

            # Overall statistics
            cursor.execute("""
                SELECT COUNT(*), AVG(performance_score), AVG(sample_count),
                       MAX(last_updated), COUNT(DISTINCT workflow_type)
                FROM workflow_patterns
            """)

            total_patterns, avg_performance, avg_samples, last_update, workflow_types = cursor.fetchone()

            # Recent execution statistics
            cursor.execute("""
                SELECT COUNT(*), AVG(execution_time),
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
                FROM workflow_executions
                WHERE timestamp > datetime('now', '-7 days')
            """)

            recent_executions, avg_exec_time, success_rate = cursor.fetchone()

            return {
                'total_patterns': total_patterns,
                'workflow_types': workflow_types,
                'avg_performance': avg_performance,
                'avg_sample_count': avg_samples,
                'last_pattern_update': last_update,
                'recent_executions_7days': recent_executions,
                'avg_execution_time': avg_exec_time,
                'success_rate_7days': success_rate,
                'workflow_statistics': workflow_stats,
                'model_status': {
                    'cluster_model_trained': self.cluster_model is not None,
                    'performance_model_trained': self.performance_model is not None,
                    'model_version': self.model_version
                }
            }

    def cleanup_old_patterns(self, days_to_keep: int = 90) -> int:
        """Clean up old pattern data."""

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM workflow_patterns
                WHERE last_updated < ? AND sample_count < ?
            """, (cutoff_date, self.config.min_data_points))

            patterns_deleted = cursor.rowcount

            cursor = conn.execute("""
                DELETE FROM workflow_executions
                WHERE timestamp < ?
            """, (cutoff_date,))

            executions_deleted = cursor.rowcount
            conn.commit()

        logger.info(f"Cleaned up {patterns_deleted} patterns and {executions_deleted} executions")
        return patterns_deleted + executions_deleted
