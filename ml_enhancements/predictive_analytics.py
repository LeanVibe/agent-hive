"""
PredictiveAnalytics - Performance prediction and resource forecasting

Provides machine learning-based predictions for system performance, resource usage,
and capacity planning within the multi-agent orchestration system.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from .models import MLConfig, AnalyticsResult, ResourcePrediction


logger = logging.getLogger(__name__)


class PredictiveAnalytics:
    """
    Advanced predictive analytics for performance forecasting and resource optimization.
    
    This component provides:
    - Performance prediction for system configurations
    - Resource usage forecasting
    - Capacity planning recommendations
    - Real-time analytics and monitoring
    """
    
    def __init__(self, config: Optional[MLConfig] = None, db_path: Optional[str] = None):
        """Initialize PredictiveAnalytics with configuration and database."""
        self.config = config or MLConfig()
        self.db_path = db_path or "predictive_analytics.db"
        self.model_version = "1.0.0"
        
        # ML models for different prediction types
        self.models = {
            'performance': RandomForestRegressor(n_estimators=100, random_state=42),
            'cpu_usage': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'memory_usage': RandomForestRegressor(n_estimators=100, random_state=42),
            'network_usage': LinearRegression(),
            'task_completion_time': RandomForestRegressor(n_estimators=100, random_state=42)
        }
        
        self.scalers = {
            model_name: StandardScaler() for model_name in self.models.keys()
        }
        
        self.model_metrics: Dict[str, Dict[str, float]] = {}
        
        # Initialize database
        self._init_database()
        
        logger.info(f"PredictiveAnalytics initialized with config: {self.config}")
    
    def _init_database(self) -> None:
        """Initialize SQLite database for analytics data storage."""
        with sqlite3.connect(self.db_path) as conn:
            # Historical metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    metric_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    cpu_usage REAL NOT NULL,
                    memory_usage REAL NOT NULL,
                    disk_usage REAL NOT NULL,
                    network_usage REAL NOT NULL,
                    active_agents INTEGER NOT NULL,
                    queue_size INTEGER NOT NULL,
                    task_completion_rate REAL NOT NULL,
                    error_rate REAL NOT NULL,
                    response_time REAL NOT NULL,
                    throughput REAL NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Predictions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id TEXT PRIMARY KEY,
                    prediction_type TEXT NOT NULL,
                    predicted_value REAL NOT NULL,
                    actual_value REAL,
                    confidence_lower REAL NOT NULL,
                    confidence_upper REAL NOT NULL,
                    accuracy_score REAL,
                    features_used TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    prediction_time TIMESTAMP NOT NULL,
                    target_time TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Resource forecasts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    current_usage REAL NOT NULL,
                    predicted_usage REAL NOT NULL,
                    prediction_horizon INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    trend_direction TEXT NOT NULL,
                    forecast_time TIMESTAMP NOT NULL,
                    target_time TIMESTAMP NOT NULL,
                    recommended_action TEXT,
                    metadata TEXT
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON system_metrics(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_predictions_type_time 
                ON predictions(prediction_type, prediction_time)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_forecasts_resource_time 
                ON resource_forecasts(resource_type, forecast_time)
            """)
            
            conn.commit()
    
    def record_system_metrics(
        self,
        cpu_usage: float,
        memory_usage: float,
        disk_usage: float,
        network_usage: float,
        active_agents: int,
        queue_size: int,
        task_completion_rate: float,
        error_rate: float,
        response_time: float,
        throughput: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record system metrics for analysis and prediction."""
        
        metric_id = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO system_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric_id, timestamp, cpu_usage, memory_usage, disk_usage,
                network_usage, active_agents, queue_size, task_completion_rate,
                error_rate, response_time, throughput, json.dumps(metadata or {})
            ))
            conn.commit()
        
        logger.debug(f"Recorded system metrics: {metric_id}")
        return metric_id
    
    def predict_performance(
        self,
        features: Dict[str, float],
        prediction_horizon: int = 60
    ) -> AnalyticsResult:
        """Predict system performance based on current features."""
        
        if 'performance' not in self.model_metrics:
            logger.warning("Performance model not trained")
            return self._create_default_result('performance', 0.8, features)
        
        # Prepare feature vector
        feature_vector = self._prepare_feature_vector(features, 'performance')
        
        # Make prediction
        prediction = self.models['performance'].predict([feature_vector])[0]
        
        # Calculate confidence interval (simplified approach)
        confidence_interval = self._calculate_confidence_interval(
            prediction, 'performance', features
        )
        
        # Create result
        result = AnalyticsResult(
            prediction_type='performance',
            predicted_value=prediction,
            confidence_interval=confidence_interval,
            accuracy_score=self.model_metrics['performance'].get('r2_score', 0.8),
            timestamp=datetime.now(),
            features_used=list(features.keys()),
            model_version=self.model_version
        )
        
        # Store prediction
        self._store_prediction(result, prediction_horizon)
        
        logger.info(f"Performance prediction: {prediction:.3f} with confidence {confidence_interval}")
        return result
    
    def predict_resource_usage(
        self,
        resource_type: str,
        current_usage: float,
        features: Dict[str, float],
        prediction_horizon: int = 60
    ) -> ResourcePrediction:
        """Predict resource usage for specified resource type."""
        
        valid_resources = ['cpu_usage', 'memory_usage', 'network_usage']
        if resource_type not in valid_resources:
            raise ValueError(f"Invalid resource type: {resource_type}")
        
        if resource_type not in self.model_metrics:
            logger.warning(f"{resource_type} model not trained")
            return self._create_default_resource_prediction(
                resource_type, current_usage, prediction_horizon
            )
        
        # Prepare feature vector
        feature_vector = self._prepare_feature_vector(features, resource_type)
        
        # Make prediction
        predicted_usage = self.models[resource_type].predict([feature_vector])[0]
        
        # Calculate confidence
        confidence = self._calculate_prediction_confidence(resource_type, features)
        
        # Determine trend
        trend_direction = self._determine_trend(current_usage, predicted_usage)
        
        # Generate recommendation
        recommended_action = self._generate_resource_recommendation(
            resource_type, current_usage, predicted_usage, trend_direction
        )
        
        # Create prediction
        prediction = ResourcePrediction(
            resource_type=resource_type,
            current_usage=current_usage,
            predicted_usage=predicted_usage,
            prediction_horizon=prediction_horizon,
            confidence=confidence,
            trend_direction=trend_direction,
            recommended_action=recommended_action
        )
        
        # Store forecast
        self._store_resource_forecast(prediction)
        
        logger.info(f"Resource prediction for {resource_type}: {predicted_usage:.3f}")
        return prediction
    
    def train_models(self) -> Dict[str, Any]:
        """Train all prediction models using historical data."""
        
        # Get training data
        training_data = self._prepare_training_data()
        if len(training_data) < self.config.min_data_points:
            logger.warning(f"Insufficient training data: {len(training_data)} samples")
            return {'error': 'insufficient_data'}
        
        results: Dict[str, Any] = {}
        
        # Train each model
        for model_name, model in self.models.items():
            try:
                # Prepare target variable based on model type
                if model_name == 'performance':
                    # Performance is calculated from multiple metrics
                    y = self._calculate_performance_score(training_data)
                else:
                    # Direct metric prediction
                    y = np.array(training_data[model_name].values)
                
                # Prepare features
                X = self._prepare_feature_matrix(training_data, model_name)
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
                
                # Scale features
                X_train_scaled = self.scalers[model_name].fit_transform(X_train)
                X_test_scaled = self.scalers[model_name].transform(X_test)
                
                # Train model
                model.fit(X_train_scaled, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test_scaled)
                
                mae = mean_absolute_error(y_test, y_pred)
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                # Store metrics
                self.model_metrics[model_name] = {
                    'mae': mae,
                    'mse': mse,
                    'r2_score': r2,
                    'training_samples': len(X_train),
                    'test_samples': len(X_test),
                    'features': X.shape[1]
                }
                
                results[model_name] = self.model_metrics[model_name]
                
                logger.info(f"Trained {model_name} model: MAE={mae:.4f}, R2={r2:.4f}")
                
            except Exception as e:
                logger.error(f"Failed to train {model_name} model: {e}")
                results[model_name] = {'error': str(e)}
        
        results['model_version'] = self.model_version
        results['training_data_size'] = len(training_data)
        results['training_timestamp'] = datetime.now().isoformat()
        
        return results
    
    def _prepare_training_data(self) -> pd.DataFrame:
        """Prepare training data from historical metrics."""
        
        with sqlite3.connect(self.db_path) as conn:
            # Get recent metrics
            cutoff_date = datetime.now() - timedelta(days=self.config.max_model_age_days)
            
            query = """
                SELECT * FROM system_metrics 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            
            cursor = conn.execute(query, (cutoff_date, self.config.forecasting_horizon * 24))
            
            columns = [desc[0] for desc in cursor.description]
            data = []
            
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                # Parse timestamp
                record['timestamp'] = datetime.fromisoformat(record['timestamp'])
                # Parse metadata
                record['metadata'] = json.loads(record['metadata'] or '{}')
                data.append(record)
        
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Add time-based features
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['minute_of_hour'] = df['timestamp'].dt.minute
            
            # Add rolling averages and trends
            df = df.sort_values('timestamp')
            
            for col in ['cpu_usage', 'memory_usage', 'network_usage', 'response_time']:
                if col in df.columns:
                    df[f'{col}_ma5'] = df[col].rolling(window=5, min_periods=1).mean()
                    df[f'{col}_trend'] = df[col].diff()
        
        return df
    
    def _prepare_feature_vector(self, features: Dict[str, float], model_type: str) -> np.ndarray:
        """Prepare feature vector for prediction."""
        
        # Base features
        base_features = [
            features.get('active_agents', 1),
            features.get('queue_size', 0),
            features.get('hour', datetime.now().hour),
            features.get('day_of_week', datetime.now().weekday()),
        ]
        
        # Model-specific features
        if model_type in ['cpu_usage', 'performance']:
            base_features.extend([
                features.get('task_complexity', 1.0),
                features.get('concurrent_tasks', 1),
            ])
        
        if model_type in ['memory_usage', 'performance']:
            base_features.extend([
                features.get('data_size', 1.0),
                features.get('cache_usage', 0.5),
            ])
        
        if model_type in ['network_usage', 'performance']:
            base_features.extend([
                features.get('api_calls', 0),
                features.get('data_transfer', 0),
            ])
        
        # Pad or truncate to consistent size
        target_size = 8
        if len(base_features) < target_size:
            base_features.extend([0.0] * (target_size - len(base_features)))
        else:
            base_features = base_features[:target_size]
        
        return np.array(base_features)
    
    def _prepare_feature_matrix(self, df: pd.DataFrame, model_type: str) -> np.ndarray[Any, np.dtype[Any]]:
        """Prepare feature matrix for training."""
        
        base_cols = ['active_agents', 'queue_size', 'hour', 'day_of_week']
        
        # Model-specific columns
        if model_type in ['cpu_usage', 'performance']:
            base_cols.extend(['task_completion_rate', 'throughput'])
        
        if model_type in ['memory_usage', 'performance']:
            base_cols.extend(['error_rate', 'response_time'])
        
        if model_type in ['network_usage', 'performance']:
            base_cols.extend(['throughput', 'response_time'])
        
        # Use available columns
        available_cols = [col for col in base_cols if col in df.columns]
        
        if not available_cols:
            # Fallback to basic columns
            available_cols = ['active_agents', 'queue_size']
        
        # Fill missing values
        feature_matrix = df[available_cols].fillna(0).values
        
        return np.array(feature_matrix, dtype=np.float64)
    
    def _calculate_performance_score(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate overall performance score from metrics."""
        
        # Normalize metrics to 0-1 scale
        weights = {
            'task_completion_rate': 0.3,
            'response_time': -0.25,  # Lower is better
            'error_rate': -0.2,      # Lower is better
            'throughput': 0.25       # Higher is better
        }
        
        scores = []
        for _, row in df.iterrows():
            score = 0.0
            total_weight = 0.0
            
            for metric, weight in weights.items():
                if metric in row:
                    value = row[metric]
                    if metric == 'response_time':
                        # Invert and normalize response time
                        normalized_value = max(0, 1 - value / 5.0)  # Assuming 5s is poor
                    elif metric == 'error_rate':
                        # Invert error rate
                        normalized_value = max(0, 1 - value)
                    else:
                        # Direct metrics (already 0-1 or normalized)
                        normalized_value = min(1.0, max(0.0, value))
                    
                    score += weight * normalized_value
                    total_weight += abs(weight)
            
            if total_weight > 0:
                score = score / total_weight
            
            scores.append(max(0.0, min(1.0, score)))
        
        return np.array(scores)
    
    def _calculate_confidence_interval(
        self,
        prediction: float,
        model_type: str,
        features: Dict[str, float]
    ) -> Tuple[float, float]:
        """Calculate confidence interval for prediction."""
        
        # Use model metrics if available
        if model_type in self.model_metrics:
            mse = self.model_metrics[model_type].get('mse', 0.1)
            std = np.sqrt(mse)
        else:
            std = 0.1  # Default uncertainty
        
        # Adjust based on feature confidence
        feature_confidence = self._calculate_prediction_confidence(model_type, features)
        adjusted_std = std / feature_confidence
        
        # 95% confidence interval
        margin = 1.96 * adjusted_std
        
        lower = max(0.0, prediction - margin)
        upper = min(1.0, prediction + margin)
        
        return (lower, upper)
    
    def _calculate_prediction_confidence(
        self,
        model_type: str,
        features: Dict[str, float]
    ) -> float:
        """Calculate confidence in prediction based on feature quality."""
        
        # Base confidence from model performance
        if model_type in self.model_metrics:
            base_confidence = max(0.1, float(self.model_metrics[model_type].get('r2_score', 0.8)))
        else:
            base_confidence = 0.5
        
        # Adjust based on feature completeness
        expected_features = {
            'performance': ['active_agents', 'queue_size', 'task_complexity'],
            'cpu_usage': ['active_agents', 'task_complexity', 'concurrent_tasks'],
            'memory_usage': ['active_agents', 'data_size', 'cache_usage'],
            'network_usage': ['api_calls', 'data_transfer', 'active_agents']
        }
        
        if model_type in expected_features:
            expected = set(expected_features[model_type])
            provided = set(features.keys())
            completeness = len(expected & provided) / len(expected)
            base_confidence *= completeness
        
        return max(0.1, min(0.95, base_confidence))
    
    def _determine_trend(self, current: float, predicted: float) -> str:
        """Determine trend direction from current to predicted value."""
        
        difference = predicted - current
        threshold = 0.05  # 5% threshold
        
        if difference > threshold:
            return 'increasing'
        elif difference < -threshold:
            return 'decreasing'
        else:
            return 'stable'
    
    def _generate_resource_recommendation(
        self,
        resource_type: str,
        current: float,
        predicted: float,
        trend: str
    ) -> Optional[str]:
        """Generate resource optimization recommendation."""
        
        # High usage thresholds
        high_thresholds = {
            'cpu_usage': 0.8,
            'memory_usage': 0.85,
            'network_usage': 0.9
        }
        
        threshold = high_thresholds.get(resource_type, 0.8)
        
        if predicted > threshold:
            if trend == 'increasing':
                return f"Scale up {resource_type.replace('_', ' ')} - predicted high usage with increasing trend"
            else:
                return f"Monitor {resource_type.replace('_', ' ')} - predicted high usage"
        
        elif current > threshold and trend == 'decreasing':
            return f"Consider scaling down {resource_type.replace('_', ' ')} - usage decreasing"
        
        elif trend == 'increasing' and predicted > 0.6:
            return f"Prepare to scale {resource_type.replace('_', ' ')} - usage trending up"
        
        return None
    
    def _create_default_result(
        self,
        prediction_type: str,
        default_value: float,
        features: Dict[str, float]
    ) -> AnalyticsResult:
        """Create default analytics result when model unavailable."""
        
        return AnalyticsResult(
            prediction_type=prediction_type,
            predicted_value=default_value,
            confidence_interval=(default_value - 0.1, default_value + 0.1),
            accuracy_score=0.5,
            timestamp=datetime.now(),
            features_used=list(features.keys()),
            model_version="default",
            metadata={'model_unavailable': True}
        )
    
    def _create_default_resource_prediction(
        self,
        resource_type: str,
        current_usage: float,
        horizon: int
    ) -> ResourcePrediction:
        """Create default resource prediction when model unavailable."""
        
        # Simple heuristic: assume 10% increase over time
        predicted_usage = min(1.0, current_usage * 1.1)
        
        return ResourcePrediction(
            resource_type=resource_type,
            current_usage=current_usage,
            predicted_usage=predicted_usage,
            prediction_horizon=horizon,
            confidence=0.5,
            trend_direction='stable',
            recommended_action=None
        )
    
    def _store_prediction(self, result: AnalyticsResult, horizon: int) -> None:
        """Store prediction in database."""
        
        prediction_id = f"pred_{result.prediction_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        target_time = datetime.now() + timedelta(minutes=horizon)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction_id, result.prediction_type, result.predicted_value, None,
                result.confidence_interval[0], result.confidence_interval[1],
                result.accuracy_score, json.dumps(result.features_used),
                result.model_version, result.timestamp, target_time,
                json.dumps(result.metadata)
            ))
            conn.commit()
    
    def _store_resource_forecast(self, prediction: ResourcePrediction) -> None:
        """Store resource forecast in database."""
        
        forecast_id = f"forecast_{prediction.resource_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        target_time = datetime.now() + timedelta(minutes=prediction.prediction_horizon)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO resource_forecasts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                forecast_id, prediction.resource_type, prediction.current_usage,
                prediction.predicted_usage, prediction.prediction_horizon,
                prediction.confidence, prediction.trend_direction,
                prediction.timestamp, target_time, prediction.recommended_action,
                json.dumps({})
            ))
            conn.commit()
    
    def get_prediction_accuracy(self, prediction_type: Optional[str] = None) -> Dict[str, Any]:
        """Get accuracy metrics for predictions."""
        
        with sqlite3.connect(self.db_path) as conn:
            if prediction_type:
                query = """
                    SELECT prediction_type, predicted_value, actual_value, 
                           accuracy_score, prediction_time
                    FROM predictions 
                    WHERE actual_value IS NOT NULL AND prediction_type = ?
                """
                cursor = conn.execute(query, (prediction_type,))
            else:
                query = """
                    SELECT prediction_type, predicted_value, actual_value, 
                           accuracy_score, prediction_time
                    FROM predictions 
                    WHERE actual_value IS NOT NULL
                """
                cursor = conn.execute(query)
            
            predictions = cursor.fetchall()
        
        if not predictions:
            return {'error': 'no_validated_predictions'}
        
        # Calculate accuracy metrics
        by_type: Dict[str, Dict[str, List[float]]] = {}
        overall_metrics: Dict[str, List[float]] = {'mae': [], 'mse': [], 'r2': []}
        
        for pred_type, predicted, actual, accuracy, pred_time in predictions:
            if pred_type not in by_type:
                by_type[pred_type] = {'predicted': [], 'actual': [], 'accuracies': []}
            
            by_type[pred_type]['predicted'].append(predicted)
            by_type[pred_type]['actual'].append(actual)
            by_type[pred_type]['accuracies'].append(accuracy or 0)
            
            overall_metrics['mae'].append(abs(predicted - actual))
            overall_metrics['mse'].append((predicted - actual) ** 2)
        
        # Calculate overall metrics
        results = {
            'overall': {
                'mae': np.mean(overall_metrics['mae']),
                'mse': np.mean(overall_metrics['mse']),
                'rmse': np.sqrt(np.mean(overall_metrics['mse'])),
                'total_predictions': len(predictions)
            },
            'by_type': {}
        }
        
        # Calculate per-type metrics
        for pred_type, data in by_type.items():
            predicted = np.array(data['predicted'])
            actual = np.array(data['actual'])
            
            mae = mean_absolute_error(actual, predicted)
            mse = mean_squared_error(actual, predicted)
            r2 = r2_score(actual, predicted) if len(actual) > 1 else 0
            
            results['by_type'][pred_type] = {
                'mae': mae,
                'mse': mse,
                'rmse': np.sqrt(mse),
                'r2_score': r2,
                'avg_accuracy': np.mean(data['accuracies']),
                'prediction_count': len(data['predicted'])
            }
        
        return results
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Model training status
            model_status = {}
            for model_name in self.models.keys():
                model_status[model_name] = {
                    'trained': model_name in self.model_metrics,
                    'metrics': self.model_metrics.get(model_name, {})
                }
            
            # Recent predictions count
            cursor.execute("""
                SELECT prediction_type, COUNT(*) 
                FROM predictions 
                WHERE prediction_time > datetime('now', '-24 hours')
                GROUP BY prediction_type
            """)
            recent_predictions = dict(cursor.fetchall())
            
            # Recent forecasts count
            cursor.execute("""
                SELECT resource_type, COUNT(*) 
                FROM resource_forecasts 
                WHERE forecast_time > datetime('now', '-24 hours')
                GROUP BY resource_type
            """)
            recent_forecasts = dict(cursor.fetchall())
            
            # Data availability
            cursor.execute("""
                SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM system_metrics
            """)
            total_metrics, min_time, max_time = cursor.fetchone()
            
            return {
                'model_status': model_status,
                'model_version': self.model_version,
                'data_availability': {
                    'total_metrics': total_metrics,
                    'earliest_data': min_time,
                    'latest_data': max_time
                },
                'recent_activity_24h': {
                    'predictions': recent_predictions,
                    'resource_forecasts': recent_forecasts
                },
                'prediction_accuracy': self.get_prediction_accuracy(),
                'config': {
                    'forecasting_horizon': self.config.forecasting_horizon,
                    'accuracy_threshold': self.config.accuracy_threshold,
                    'analytics_enabled': self.config.analytics_enabled
                }
            }
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old analytics data."""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM system_metrics WHERE timestamp < ?
            """, (cutoff_date,))
            metrics_deleted = cursor.rowcount
            
            cursor = conn.execute("""
                DELETE FROM predictions WHERE prediction_time < ?
            """, (cutoff_date,))
            predictions_deleted = cursor.rowcount
            
            cursor = conn.execute("""
                DELETE FROM resource_forecasts WHERE forecast_time < ?
            """, (cutoff_date,))
            forecasts_deleted = cursor.rowcount
            
            conn.commit()
        
        total_deleted = metrics_deleted + predictions_deleted + forecasts_deleted
        logger.info(f"Cleaned up {total_deleted} analytics records")
        return total_deleted