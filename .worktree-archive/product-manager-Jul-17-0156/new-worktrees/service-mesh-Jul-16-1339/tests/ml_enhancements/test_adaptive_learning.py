"""
Comprehensive tests for AdaptiveLearning ML component.
"""

import pytest
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ml_enhancements.adaptive_learning import AdaptiveLearning
from ml_enhancements.models import MLConfig, LearningMetrics


class TestAdaptiveLearning:
    """Test suite for AdaptiveLearning functionality."""

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
            learning_rate=0.05,
            update_frequency=50,
            min_data_points=3,
            confidence_threshold=0.6
        )

    @pytest.fixture
    def learning(self, config, temp_db):
        """Create AdaptiveLearning with test configuration."""
        return AdaptiveLearning(config=config, db_path=temp_db)

    def test_init_creates_database_schema(self, temp_db, config):
        """Test that initialization creates proper database schema."""
        learning = AdaptiveLearning(config=config, db_path=temp_db)

        # Verify database file exists
        assert Path(temp_db).exists()

        # Verify schema
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Check learning_sessions table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_sessions'")
            assert cursor.fetchone() is not None

            # Check feedback_data table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedback_data'")
            assert cursor.fetchone() is not None

            # Check model_adaptations table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='model_adaptations'")
            assert cursor.fetchone() is not None

            # Check performance_history table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_history'")
            assert cursor.fetchone() is not None

    def test_start_learning_session(self, learning):
        """Test starting a learning session."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'},
            hyperparameters={'learning_rate': 0.01}
        )

        assert session_id.startswith('session_performance_optimizer_')
        assert learning.learning_state['current_session'] == session_id

        # Verify session was stored in database
        with sqlite3.connect(learning.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM learning_sessions WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()

            assert result is not None
            assert result[1] == 'performance_optimizer'  # model_type

    def test_provide_feedback(self, learning):
        """Test providing feedback for learning."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        learning.provide_feedback(
            session_id=session_id,
            feedback_type='positive',
            feedback_value=0.8,
            context={'success': True, 'performance': 0.85},
            source_agent='test_agent'
        )

        # Check feedback buffer
        assert len(learning.feedback_buffer['positive_feedback']) == 1

        # Verify feedback was stored in database
        with sqlite3.connect(learning.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feedback_data WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()

            assert result is not None
            assert result[2] == 'positive'  # feedback_type
            assert result[3] == 0.8  # feedback_value

    def test_adapt_model_no_data(self, learning):
        """Test model adaptation with no training data."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        metrics = learning.adapt_model(
            session_id=session_id,
            model_type='performance_optimizer',
            training_data=[],
            target_values=[]
        )

        assert isinstance(metrics, LearningMetrics)
        assert metrics.learning_session_id == session_id
        assert metrics.improvement_rate == 0.0
        assert metrics.samples_processed == 0

    def test_adapt_model_with_data(self, learning):
        """Test model adaptation with training data."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        training_data = [
            {'feature1': 1.0, 'feature2': 2.0},
            {'feature1': 1.5, 'feature2': 2.5},
            {'feature1': 2.0, 'feature2': 3.0}
        ]
        target_values = [0.7, 0.8, 0.9]

        metrics = learning.adapt_model(
            session_id=session_id,
            model_type='performance_optimizer',
            training_data=training_data,
            target_values=target_values
        )

        assert isinstance(metrics, LearningMetrics)
        assert metrics.learning_session_id == session_id
        assert metrics.samples_processed == 3
        assert len(metrics.performance_history) > 0

    def test_invalid_model_type(self, learning):
        """Test handling of invalid model type."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        with pytest.raises(ValueError, match="Unknown model type"):
            learning.adapt_model(
                session_id=session_id,
                model_type='invalid_model',
                training_data=[],
                target_values=[]
            )

    def test_prepare_training_data(self, learning):
        """Test training data preparation."""
        training_data = [
            {'feature1': 1.0, 'feature2': 2.0},
            {'feature1': 1.5, 'feature2': 2.5}
        ]
        target_values = [0.7, 0.8]

        X, y = learning._prepare_training_data(training_data, target_values)

        assert X.shape == (2, 2)  # 2 samples, 2 features
        assert y.shape == (2,)
        assert list(y) == [0.7, 0.8]

    def test_measure_model_performance(self, learning):
        """Test model performance measurement."""
        # Test with untrained model
        performance = learning._measure_model_performance(
            'performance_optimizer',
            [{'feature1': 1.0}],
            [0.8]
        )

        assert performance == 0.5  # Default performance for untrained model

    def test_estimate_model_complexity(self, learning):
        """Test model complexity estimation."""
        # Test with different model types
        rf_model = learning.adaptive_models['task_scheduler']  # RandomForest
        sgd_model = learning.adaptive_models['performance_optimizer']  # SGD

        rf_complexity = learning._estimate_model_complexity(rf_model)
        sgd_complexity = learning._estimate_model_complexity(sgd_model)

        assert rf_complexity >= 1  # Should have n_estimators
        assert sgd_complexity >= 1

    def test_calculate_convergence_time(self, learning):
        """Test convergence time calculation."""
        session_id = 'test_session'

        # Test with no performance history
        convergence_time = learning._calculate_convergence_time(session_id)
        assert convergence_time == 0.0

        # Test with stable performance
        learning.learning_state['model_performance'][session_id] = [0.8, 0.81, 0.805, 0.802, 0.801]
        convergence_time = learning._calculate_convergence_time(session_id)
        assert convergence_time > 0

    def test_extract_features_from_context(self, learning):
        """Test feature extraction from feedback context."""
        context = {
            'agent_count': 3,
            'task_complexity': 2.0,
            'resource_usage': 0.7,
            'queue_size': 5,
            'success_rate': 0.9,
            'response_time': 1.2
        }

        features = learning._extract_features_from_context(context)

        assert 'agent_count' in features
        assert 'efficiency_score' in features  # Derived feature
        assert 'load_factor' in features  # Derived feature
        assert features['efficiency_score'] == 0.9 / 1.2
        assert features['load_factor'] == 5 / 3

    def test_check_convergence(self, learning):
        """Test convergence checking."""
        session_id = 'test_session'

        # Test with insufficient history
        converged = learning._check_convergence(session_id, 'performance_optimizer')
        assert not converged

        # Test with stable performance (converged)
        learning.learning_state['model_performance'][session_id] = [0.8, 0.801, 0.802, 0.8015, 0.8018]
        converged = learning._check_convergence(session_id, 'performance_optimizer')
        assert converged

        # Check convergence was recorded
        assert session_id in learning.learning_state['convergence_tracking']
        assert learning.learning_state['convergence_tracking'][session_id]['converged']

    def test_end_learning_session(self, learning):
        """Test ending a learning session."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        # Add some performance history
        learning.learning_state['model_performance'][session_id] = [0.7, 0.8, 0.85]

        summary = learning.end_learning_session(session_id)

        assert summary['session_id'] == session_id
        assert summary['final_performance'] == 0.85
        assert summary['total_adaptations'] == 3
        assert 'end_time' in summary

        # Verify session was updated in database
        with sqlite3.connect(learning.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT final_performance FROM learning_sessions WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()

            assert result is not None
            assert result[0] == 0.85

    def test_calculate_improvement_trend(self, learning):
        """Test improvement trend calculation."""
        # Test increasing trend
        increasing_history = [0.6, 0.7, 0.8, 0.9]
        trend = learning._calculate_improvement_trend(increasing_history)
        assert trend > 0  # Positive slope

        # Test decreasing trend
        decreasing_history = [0.9, 0.8, 0.7, 0.6]
        trend = learning._calculate_improvement_trend(decreasing_history)
        assert trend < 0  # Negative slope

        # Test insufficient data
        short_history = [0.8]
        trend = learning._calculate_improvement_trend(short_history)
        assert trend == 0.0

    def test_calculate_session_improvement_rate(self, learning):
        """Test session improvement rate calculation."""
        # Test improvement
        improving_history = [0.6, 0.8]
        rate = learning._calculate_session_improvement_rate(improving_history)
        assert rate > 0
        assert abs(rate - (0.8 - 0.6) / 0.6) < 0.001

        # Test no improvement
        stable_history = [0.8, 0.8]
        rate = learning._calculate_session_improvement_rate(stable_history)
        assert rate == 0.0

    def test_get_learning_insights(self, learning):
        """Test learning insights generation."""
        # Create some test session data
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        learning.end_learning_session(session_id)

        insights = learning.get_learning_insights()

        assert 'session_statistics' in insights
        assert 'adaptation_statistics' in insights
        assert 'recent_performance_7days' in insights
        assert 'model_status' in insights
        assert 'config' in insights

    def test_predict_with_adaptation_untrained(self, learning):
        """Test prediction with untrained model."""
        features = {'feature1': 1.0, 'feature2': 2.0}

        prediction, confidence, needs_adaptation = learning.predict_with_adaptation(
            'performance_optimizer', features
        )

        assert prediction == 0.5  # Default prediction
        assert confidence == 0.1   # Low confidence
        assert needs_adaptation     # Should need adaptation

    def test_predict_with_adaptation_trained(self, learning):
        """Test prediction with trained model."""
        # First train the model with some data
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        training_data = [{'feature1': 1.0, 'feature2': 2.0}]
        target_values = [0.8]

        learning.adapt_model(session_id, 'performance_optimizer', training_data, target_values)

        # Now test prediction
        features = {'feature1': 1.0, 'feature2': 2.0}
        prediction, confidence, needs_adaptation = learning.predict_with_adaptation(
            'performance_optimizer', features, confidence_threshold=0.5
        )

        assert 0.0 <= prediction <= 1.0
        assert 0.0 <= confidence <= 1.0

    def test_estimate_prediction_confidence(self, learning):
        """Test prediction confidence estimation."""
        # Test with no current session
        confidence = learning._estimate_prediction_confidence(
            'performance_optimizer',
            {'feature1': 1.0}
        )
        assert confidence == 0.5  # Base confidence

        # Test with current session
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )
        learning.learning_state['model_performance'][session_id] = [0.9]

        confidence = learning._estimate_prediction_confidence(
            'performance_optimizer',
            {'feature1': 1.0, 'feature2': 2.0}
        )
        assert confidence > 0.5  # Should be higher with good performance

    def test_get_adaptation_recommendations(self, learning):
        """Test adaptation recommendations generation."""
        recommendations = learning.get_adaptation_recommendations()

        assert isinstance(recommendations, list)

        # Should recommend initialization for new system
        init_rec = next((r for r in recommendations if r['type'] == 'initialization'), None)
        assert init_rec is not None
        assert init_rec['priority'] == 'high'

    def test_get_recent_sessions(self, learning):
        """Test recent sessions retrieval."""
        # Create a completed session
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )
        learning.end_learning_session(session_id)

        recent_sessions = learning._get_recent_sessions(days=7)

        assert len(recent_sessions) == 1
        assert recent_sessions[0]['session_id'] == session_id

    def test_cleanup_old_learning_data(self, learning):
        """Test cleanup of old learning data."""
        # Create old session data
        old_time = datetime.now() - timedelta(days=70)
        recent_time = datetime.now() - timedelta(days=10)

        with sqlite3.connect(learning.db_path) as conn:
            # Insert old session
            conn.execute("""
                INSERT INTO learning_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "old_session", "test_model", old_time, None, 0.5, None, 0.0, 10, 0.0, "{}", "{}"
            ))

            # Insert recent session
            conn.execute("""
                INSERT INTO learning_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "recent_session", "test_model", recent_time, None, 0.8, None, 0.1, 20, 0.0, "{}", "{}"
            ))

            conn.commit()

        deleted_count = learning.cleanup_old_learning_data(days_to_keep=60)

        # Should have deleted old data
        assert deleted_count >= 1

        # Verify recent session still exists
        with sqlite3.connect(learning.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM learning_sessions WHERE session_id = 'recent_session'")
            assert cursor.fetchone()[0] == 1

    def test_learning_metrics_serialization(self, learning):
        """Test LearningMetrics serialization."""
        metrics = LearningMetrics(
            learning_session_id='test_session',
            improvement_rate=0.15,
            accuracy_change=0.05,
            convergence_time=120.0,
            samples_processed=50,
            model_complexity=10,
            timestamp=datetime.now(),
            performance_history=[0.7, 0.8, 0.85]
        )

        metrics_dict = metrics.to_dict()

        assert isinstance(metrics_dict, dict)
        assert metrics_dict['learning_session_id'] == 'test_session'
        assert metrics_dict['improvement_rate'] == 0.15
        assert 'improvement_trend' in metrics_dict
        assert 'timestamp' in metrics_dict

    def test_learning_metrics_performance_tracking(self, learning):
        """Test LearningMetrics performance sample tracking."""
        metrics = LearningMetrics(
            learning_session_id='test_session',
            improvement_rate=0.0,
            accuracy_change=0.0,
            convergence_time=0.0,
            samples_processed=0,
            model_complexity=1,
            timestamp=datetime.now()
        )

        # Add performance samples
        for i in range(105):  # More than 100 to test truncation
            metrics.add_performance_sample(0.5 + i * 0.001)

        assert len(metrics.performance_history) == 100  # Should be truncated

        # Test trend calculation
        trend = metrics.get_improvement_trend()
        assert trend > 0  # Should be positive trend

    def test_concurrent_feedback_processing(self, learning):
        """Test thread safety of feedback processing."""
        import threading
        import time

        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        def provide_feedback_thread(thread_id):
            for i in range(3):
                learning.provide_feedback(
                    session_id=session_id,
                    feedback_type='positive' if i % 2 == 0 else 'negative',
                    feedback_value=0.7 + thread_id * 0.1,
                    context={'thread': thread_id, 'iteration': i}
                )
                time.sleep(0.01)

        # Run multiple threads
        threads = []
        for t in range(3):
            thread = threading.Thread(target=provide_feedback_thread, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all feedback was recorded
        with sqlite3.connect(learning.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM feedback_data WHERE session_id = ?", (session_id,))
            count = cursor.fetchone()[0]
            assert count == 9  # 3 threads * 3 feedback each

    @patch('ml_enhancements.adaptive_learning.logger')
    def test_logging_integration(self, mock_logger, learning):
        """Test that logging is properly integrated."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        # Verify logging was called
        mock_logger.info.assert_called()

    def test_error_handling_invalid_data(self, learning):
        """Test error handling with invalid data."""
        session_id = learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'workflow': 'test'}
        )

        # Test with mismatched data lengths
        try:
            learning.adapt_model(
                session_id=session_id,
                model_type='performance_optimizer',
                training_data=[{'feature1': 1.0}],
                target_values=[0.8, 0.9]  # Mismatched length
            )
        except Exception:
            pass  # Should handle gracefully

        # Test with empty context
        learning.provide_feedback(
            session_id=session_id,
            feedback_type='positive',
            feedback_value=0.8,
            context={}  # Empty context
        )

        # Should not crash
