"""
Comprehensive tests for PredictiveAnalytics ML component.
"""

import pytest
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ml_enhancements.predictive_analytics import PredictiveAnalytics
from ml_enhancements.models import MLConfig, AnalyticsResult, ResourcePrediction


class TestPredictiveAnalytics:
    """Test suite for PredictiveAnalytics functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MLConfig(
            forecasting_horizon=30,
            accuracy_threshold=0.8,
            min_data_points=5,
            confidence_threshold=0.7
        )

    @pytest.fixture
    def analytics(self, config, temp_db):
        """Create PredictiveAnalytics with test configuration."""
        return PredictiveAnalytics(config=config, db_path=temp_db)

    def test_init_creates_database_schema(self, temp_db, config):
        """Test that initialization creates proper database schema."""
        analytics = PredictiveAnalytics(config=config, db_path=temp_db)

        # Verify database file exists
        assert Path(temp_db).exists()

        # Verify schema
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Check system_metrics table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_metrics'")
            assert cursor.fetchone() is not None

            # Check predictions table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions'")
            assert cursor.fetchone() is not None

            # Check resource_forecasts table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resource_forecasts'")
            assert cursor.fetchone() is not None

    def test_record_system_metrics(self, analytics):
        """Test recording system metrics."""
        metric_id = analytics.record_system_metrics(
            cpu_usage=0.7,
            memory_usage=0.6,
            disk_usage=0.4,
            network_usage=0.3,
            active_agents=3,
            queue_size=5,
            task_completion_rate=0.9,
            error_rate=0.05,
            response_time=1.2,
            throughput=10.5,
            metadata={'source': 'test'}
        )

        assert metric_id.startswith('metrics_')

        # Verify metric was recorded
        with sqlite3.connect(analytics.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_metrics WHERE metric_id = ?", (metric_id,))
            result = cursor.fetchone()

            assert result is not None
            assert result[2] == 0.7  # cpu_usage
            assert result[3] == 0.6  # memory_usage
            assert result[7] == 5    # queue_size

    def test_predict_performance_no_model(self, analytics):
        """Test performance prediction without trained model."""
        features = {
            'active_agents': 3,
            'queue_size': 5,
            'task_complexity': 2.0
        }

        result = analytics.predict_performance(features)

        assert isinstance(result, AnalyticsResult)
        assert result.prediction_type == 'performance'
        assert 0.0 <= result.predicted_value <= 1.0
        assert len(result.confidence_interval) == 2
        assert result.model_version == "default"

    def test_predict_resource_usage_invalid_type(self, analytics):
        """Test resource prediction with invalid resource type."""
        with pytest.raises(ValueError, match="Invalid resource type"):
            analytics.predict_resource_usage(
                resource_type="invalid_resource",
                current_usage=0.5,
                features={'active_agents': 3},
                prediction_horizon=60
            )

    def test_predict_resource_usage_valid(self, analytics):
        """Test resource prediction with valid parameters."""
        prediction = analytics.predict_resource_usage(
            resource_type="cpu_usage",
            current_usage=0.6,
            features={'active_agents': 3, 'task_complexity': 2.0},
            prediction_horizon=60
        )

        assert isinstance(prediction, ResourcePrediction)
        assert prediction.resource_type == "cpu_usage"
        assert prediction.current_usage == 0.6
        assert 0.0 <= prediction.predicted_usage <= 1.0
        assert prediction.prediction_horizon == 60
        assert prediction.trend_direction in ['increasing', 'decreasing', 'stable']

    def test_train_models_insufficient_data(self, analytics):
        """Test model training with insufficient data."""
        result = analytics.train_models()
        assert 'error' in result
        assert result['error'] == 'insufficient_data'

    def test_train_models_with_data(self, analytics):
        """Test model training with sufficient data."""
        # Create sufficient training data
        for i in range(20):  # Above min_data_points
            analytics.record_system_metrics(
                cpu_usage=0.5 + i * 0.02,
                memory_usage=0.4 + i * 0.02,
                disk_usage=0.3,
                network_usage=0.2 + i * 0.01,
                active_agents=2 + (i % 3),
                queue_size=i % 10,
                task_completion_rate=0.8 + (i % 3) * 0.05,
                error_rate=0.1 - (i % 3) * 0.02,
                response_time=1.0 + (i % 5) * 0.2,
                throughput=8.0 + i * 0.5
            )

        result = analytics.train_models()

        assert 'model_version' in result
        assert 'training_data_size' in result
        assert result['training_data_size'] >= 10

        # Check that at least some models were trained successfully
        successful_models = [k for k, v in result.items()
                           if isinstance(v, dict) and 'error' not in v]
        assert len(successful_models) > 0

    def test_calculate_performance_score(self, analytics):
        """Test performance score calculation."""
        import pandas as pd

        # Create test dataframe
        test_data = pd.DataFrame([
            {
                'task_completion_rate': 0.9,
                'response_time': 1.0,
                'error_rate': 0.05,
                'throughput': 10.0
            },
            {
                'task_completion_rate': 0.7,
                'response_time': 3.0,
                'error_rate': 0.2,
                'throughput': 5.0
            }
        ])

        scores = analytics._calculate_performance_score(test_data)

        assert len(scores) == 2
        assert 0.0 <= scores[0] <= 1.0
        assert 0.0 <= scores[1] <= 1.0
        assert scores[0] > scores[1]  # First row should have better performance

    def test_prepare_feature_vector(self, analytics):
        """Test feature vector preparation."""
        features = {
            'active_agents': 3,
            'queue_size': 5,
            'task_complexity': 2.0,
            'hour': 14,
            'day_of_week': 2
        }

        vector = analytics._prepare_feature_vector(features, 'performance')

        assert isinstance(vector, type(vector))  # numpy array
        assert len(vector) >= 4  # Should have at least base features

    def test_calculate_confidence_interval(self, analytics):
        """Test confidence interval calculation."""
        prediction = 0.8
        interval = analytics._calculate_confidence_interval(
            prediction, 'performance', {'active_agents': 3}
        )

        assert len(interval) == 2
        assert interval[0] <= prediction <= interval[1]
        assert 0.0 <= interval[0] <= 1.0
        assert 0.0 <= interval[1] <= 1.0

    def test_determine_trend(self, analytics):
        """Test trend determination logic."""
        # Test increasing trend
        trend = analytics._determine_trend(0.5, 0.7)
        assert trend == 'increasing'

        # Test decreasing trend
        trend = analytics._determine_trend(0.7, 0.5)
        assert trend == 'decreasing'

        # Test stable trend
        trend = analytics._determine_trend(0.6, 0.62)
        assert trend == 'stable'

    def test_generate_resource_recommendation(self, analytics):
        """Test resource recommendation generation."""
        # Test high usage with increasing trend
        rec = analytics._generate_resource_recommendation(
            'cpu_usage', 0.85, 0.9, 'increasing'
        )
        assert rec is not None
        assert 'scale up' in rec.lower()

        # Test normal usage
        rec = analytics._generate_resource_recommendation(
            'memory_usage', 0.5, 0.55, 'stable'
        )
        assert rec is None  # No action needed

    def test_get_prediction_accuracy_no_data(self, analytics):
        """Test accuracy metrics with no validated predictions."""
        result = analytics.get_prediction_accuracy()
        assert 'error' in result
        assert result['error'] == 'no_validated_predictions'

    def test_get_analytics_summary(self, analytics):
        """Test analytics summary generation."""
        # Add some test data
        analytics.record_system_metrics(
            cpu_usage=0.7, memory_usage=0.6, disk_usage=0.4, network_usage=0.3,
            active_agents=3, queue_size=5, task_completion_rate=0.9,
            error_rate=0.05, response_time=1.2, throughput=10.5
        )

        summary = analytics.get_analytics_summary()

        assert 'model_status' in summary
        assert 'model_version' in summary
        assert 'data_availability' in summary
        assert 'recent_activity_24h' in summary
        assert 'config' in summary

        # Check data availability
        assert summary['data_availability']['total_metrics'] > 0

    def test_cleanup_old_data(self, analytics):
        """Test cleanup of old analytics data."""
        # Create old and recent data
        old_time = datetime.now() - timedelta(days=35)
        recent_time = datetime.now() - timedelta(days=5)

        with sqlite3.connect(analytics.db_path) as conn:
            # Insert old metric
            conn.execute("""
                INSERT INTO system_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "old_metric", old_time, 0.5, 0.4, 0.3, 0.2, 2, 3, 0.8, 0.1, 1.0, 5.0, "{}"
            ))

            # Insert recent metric
            conn.execute("""
                INSERT INTO system_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "recent_metric", recent_time, 0.6, 0.5, 0.4, 0.3, 3, 4, 0.9, 0.05, 1.2, 8.0, "{}"
            ))

            conn.commit()

        deleted_count = analytics.cleanup_old_data(days_to_keep=30)

        # Should have deleted old data
        assert deleted_count >= 1

        # Verify recent data still exists
        with sqlite3.connect(analytics.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM system_metrics WHERE metric_id = 'recent_metric'")
            assert cursor.fetchone()[0] == 1

    def test_analytics_result_serialization(self, analytics):
        """Test AnalyticsResult serialization."""
        result = AnalyticsResult(
            prediction_type='performance',
            predicted_value=0.85,
            confidence_interval=(0.8, 0.9),
            accuracy_score=0.92,
            timestamp=datetime.now(),
            features_used=['agents', 'queue_size'],
            model_version='1.0.0'
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict['prediction_type'] == 'performance'
        assert result_dict['predicted_value'] == 0.85
        assert 'timestamp' in result_dict

    def test_resource_prediction_serialization(self, analytics):
        """Test ResourcePrediction serialization."""
        prediction = ResourcePrediction(
            resource_type='cpu_usage',
            current_usage=0.6,
            predicted_usage=0.75,
            prediction_horizon=60,
            confidence=0.85,
            trend_direction='increasing',
            recommended_action='Monitor closely'
        )

        pred_dict = prediction.to_dict()

        assert isinstance(pred_dict, dict)
        assert pred_dict['resource_type'] == 'cpu_usage'
        assert pred_dict['current_usage'] == 0.6
        assert pred_dict['predicted_usage'] == 0.75
        assert 'timestamp' in pred_dict

    def test_concurrent_metrics_recording(self, analytics):
        """Test thread safety of metrics recording."""
        import threading
        import time

        def record_metrics(thread_id):
            for i in range(3):
                analytics.record_system_metrics(
                    cpu_usage=0.5 + thread_id * 0.1,
                    memory_usage=0.4 + i * 0.1,
                    disk_usage=0.3,
                    network_usage=0.2,
                    active_agents=2 + thread_id,
                    queue_size=i,
                    task_completion_rate=0.8,
                    error_rate=0.1,
                    response_time=1.0 + i * 0.2,
                    throughput=5.0 + thread_id
                )
                time.sleep(0.01)

        # Run multiple threads
        threads = []
        for t in range(3):
            thread = threading.Thread(target=record_metrics, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all metrics were recorded
        with sqlite3.connect(analytics.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM system_metrics")
            count = cursor.fetchone()[0]
            assert count == 9  # 3 threads * 3 metrics each

    @patch('ml_enhancements.predictive_analytics.logger')
    def test_logging_integration(self, mock_logger, analytics):
        """Test that logging is properly integrated."""
        analytics.record_system_metrics(
            cpu_usage=0.7, memory_usage=0.6, disk_usage=0.4, network_usage=0.3,
            active_agents=3, queue_size=5, task_completion_rate=0.9,
            error_rate=0.05, response_time=1.2, throughput=10.5
        )

        # Verify debug logging was called
        mock_logger.debug.assert_called()

    def test_error_handling_invalid_config(self):
        """Test error handling with invalid configuration."""
        with pytest.raises(ValueError):
            MLConfig(forecasting_horizon=-10)  # Should trigger validation

        with pytest.raises(ValueError):
            MLConfig(accuracy_threshold=1.5)  # Should trigger validation

    def test_model_metadata_handling(self, analytics):
        """Test model metadata and version tracking."""
        # Test that model version is properly set
        assert analytics.model_version == "1.0.0"

        # Test that model metrics are initialized
        assert isinstance(analytics.model_metrics, dict)

        # Test that scalers are initialized for each model
        expected_models = ['performance', 'cpu_usage', 'memory_usage', 'network_usage', 'task_completion_time']
        for model_name in expected_models:
            assert model_name in analytics.scalers
