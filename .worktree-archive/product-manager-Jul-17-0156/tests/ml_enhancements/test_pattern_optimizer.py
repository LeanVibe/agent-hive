"""
Comprehensive tests for PatternOptimizer ML component.
"""

import pytest
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ml_enhancements.pattern_optimizer import PatternOptimizer
from ml_enhancements.models import MLConfig, PatternData, WorkflowOptimization


class TestPatternOptimizer:
    """Test suite for PatternOptimizer functionality."""

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
            pattern_analysis_window=100,
            pattern_optimization_threshold=0.1,
            min_data_points=5,
            confidence_threshold=0.7
        )

    @pytest.fixture
    def optimizer(self, config, temp_db):
        """Create PatternOptimizer with test configuration."""
        return PatternOptimizer(config=config, db_path=temp_db)

    def test_init_creates_database_schema(self, temp_db, config):
        """Test that initialization creates proper database schema."""
        optimizer = PatternOptimizer(config=config, db_path=temp_db)

        # Verify database file exists
        assert Path(temp_db).exists()

        # Verify schema
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Check workflow_patterns table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_patterns'")
            assert cursor.fetchone() is not None

            # Check workflow_executions table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_executions'")
            assert cursor.fetchone() is not None

            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_patterns_type'")
            assert cursor.fetchone() is not None

    def test_record_workflow_execution(self, optimizer):
        """Test recording workflow execution data."""
        features = {
            'task_complexity': 2.0,
            'agent_count': 3,
            'resource_usage': 0.7,
            'queue_size': 5
        }

        performance_metrics = {
            'completion_time': 1.5,
            'resource_efficiency': 0.8,
            'success_rate': 0.9,
            'error_count': 0
        }

        optimizer.record_workflow_execution(
            execution_id="test_exec_1",
            workflow_type="feature_development",
            features=features,
            performance_metrics=performance_metrics,
            execution_time=1.5,
            success=True,
            agent_id="agent_1"
        )

        # Verify execution was recorded
        with sqlite3.connect(optimizer.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM workflow_executions WHERE execution_id = ?", ("test_exec_1",))
            result = cursor.fetchone()

            assert result is not None
            assert result[1] == "feature_development"  # workflow_type
            assert result[4] == 1.5  # execution_time
            assert result[5] == 1  # success (True)

    def test_hash_features_consistency(self, optimizer):
        """Test that feature hashing is consistent and deterministic."""
        features1 = {
            'task_complexity': 2.0,
            'agent_count': 3,
            'resource_usage': 0.7
        }

        features2 = {
            'resource_usage': 0.7,
            'task_complexity': 2.0,
            'agent_count': 3
        }

        hash1 = optimizer._hash_features(features1)
        hash2 = optimizer._hash_features(features2)

        assert hash1 == hash2
        assert len(hash1) == 16  # MD5 hash truncated to 16 chars

    def test_calculate_performance_score(self, optimizer):
        """Test performance score calculation."""
        # High performance metrics
        high_perf_metrics = {
            'completion_time': 0.5,  # Low completion time is good
            'resource_efficiency': 0.9,
            'success_rate': 0.95,
            'error_count': 0.05,  # Low error count is good
            'agent_utilization': 0.85
        }

        high_score = optimizer._calculate_performance_score(high_perf_metrics)
        assert 0.8 <= high_score <= 1.0

        # Low performance metrics
        low_perf_metrics = {
            'completion_time': 5.0,  # High completion time is bad
            'resource_efficiency': 0.3,
            'success_rate': 0.5,
            'error_count': 0.8,  # High error count is bad
            'agent_utilization': 0.2
        }

        low_score = optimizer._calculate_performance_score(low_perf_metrics)
        assert 0.0 <= low_score <= 0.5

    def test_calculate_optimization_score(self, optimizer):
        """Test optimization score calculation."""
        # Low performance, high confidence = high optimization potential
        high_opt_score = optimizer._calculate_optimization_score(0.3, 0.9, 50)

        # High performance, high confidence = low optimization potential
        low_opt_score = optimizer._calculate_optimization_score(0.9, 0.9, 50)

        assert high_opt_score > low_opt_score
        assert 0.0 <= high_opt_score <= 1.0
        assert 0.0 <= low_opt_score <= 1.0

    def test_analyze_patterns_empty_data(self, optimizer):
        """Test pattern analysis with no data."""
        patterns = optimizer.analyze_patterns("nonexistent_workflow")
        assert patterns == []

    def test_analyze_patterns_with_data(self, optimizer):
        """Test pattern analysis with recorded data."""
        # Record multiple executions to create patterns
        for i in range(10):
            features = {
                'task_complexity': 1.5 + i * 0.1,
                'agent_count': 2 + (i % 3),
                'resource_usage': 0.5 + i * 0.05,
                'queue_size': i % 5
            }

            performance_metrics = {
                'completion_time': 1.0 + i * 0.1,
                'resource_efficiency': 0.8 - i * 0.02,
                'success_rate': 0.9,
                'error_count': 0.1
            }

            optimizer.record_workflow_execution(
                execution_id=f"test_exec_{i}",
                workflow_type="test_workflow",
                features=features,
                performance_metrics=performance_metrics,
                execution_time=1.0 + i * 0.1,
                success=True
            )

        patterns = optimizer.analyze_patterns("test_workflow")
        assert len(patterns) >= 1

        for pattern in patterns:
            assert isinstance(pattern, PatternData)
            assert pattern.workflow_type == "test_workflow"
            assert pattern.sample_count >= 1
            assert 0.0 <= pattern.confidence <= 1.0

    def test_get_optimization_recommendations(self, optimizer):
        """Test optimization recommendation generation."""
        # Create some pattern data first
        for i in range(8):  # Enough to exceed min_data_points
            features = {
                'task_complexity': 2.0,
                'agent_count': 3,
                'resource_usage': 0.8,
                'queue_size': 2
            }

            performance_metrics = {
                'completion_time': 1.0,
                'resource_efficiency': 0.9,
                'success_rate': 0.95,
                'error_count': 0.05
            }

            optimizer.record_workflow_execution(
                execution_id=f"rec_test_{i}",
                workflow_type="recommendation_test",
                features=features,
                performance_metrics=performance_metrics,
                execution_time=1.0,
                success=True
            )

        current_features = {
            'task_complexity': 1.5,
            'agent_count': 2,
            'resource_usage': 0.6,
            'queue_size': 3
        }

        recommendations = optimizer.get_optimization_recommendations(
            "recommendation_test", current_features
        )

        # Should return recommendations if patterns exist
        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert isinstance(rec, WorkflowOptimization)
            assert rec.workflow_id.startswith("recommendation_test")
            assert 0.0 <= rec.confidence <= 1.0
            assert rec.effort_estimate in ['low', 'medium', 'high']

    def test_train_models_insufficient_data(self, optimizer):
        """Test model training with insufficient data."""
        result = optimizer.train_models()
        assert 'error' in result
        assert result['error'] == 'insufficient_data'

    def test_train_models_with_data(self, optimizer):
        """Test model training with sufficient data."""
        # Create sufficient training data
        for i in range(50):  # Well above min_data_points
            features = {
                'task_complexity': 1.0 + i * 0.1,
                'agent_count': 1 + (i % 5),
                'resource_usage': 0.3 + (i % 7) * 0.1,
                'queue_size': i % 10,
                'historical_success_rate': 0.8 + (i % 3) * 0.05
            }

            performance_metrics = {
                'completion_time': 1.0 + (i % 5) * 0.2,
                'resource_efficiency': 0.7 + (i % 4) * 0.1,
                'success_rate': 0.85 + (i % 3) * 0.05,
                'error_count': 0.1 - (i % 3) * 0.03
            }

            optimizer.record_workflow_execution(
                execution_id=f"train_test_{i}",
                workflow_type="training_workflow",
                features=features,
                performance_metrics=performance_metrics,
                execution_time=1.0 + (i % 5) * 0.2,
                success=True
            )

        result = optimizer.train_models()

        assert 'model_version' in result
        assert 'training_samples' in result
        assert result['training_samples'] >= 10  # Should have sufficient data
        assert 'mse' in result
        assert 'r2_score' in result

    def test_predict_performance(self, optimizer):
        """Test performance prediction."""
        features = {
            'task_complexity': 2.0,
            'agent_count': 3,
            'resource_usage': 0.7,
            'queue_size': 5,
            'time_of_day': 14,
            'day_of_week': 2,
            'historical_success_rate': 0.8,
            'avg_completion_time': 1.5
        }

        # Test prediction without trained model (should return defaults)
        prediction, confidence = optimizer.predict_performance(features)
        assert 0.0 <= prediction <= 1.0
        assert 0.0 <= confidence <= 1.0

    def test_get_pattern_statistics(self, optimizer):
        """Test pattern statistics retrieval."""
        # Add some test data
        for i in range(5):
            optimizer.record_workflow_execution(
                execution_id=f"stats_test_{i}",
                workflow_type="stats_workflow",
                features={'task_complexity': 1.0, 'agent_count': 2},
                performance_metrics={'completion_time': 1.0, 'success_rate': 0.9},
                execution_time=1.0,
                success=True
            )

        stats = optimizer.get_pattern_statistics()

        assert 'total_patterns' in stats
        assert 'workflow_types' in stats
        assert 'avg_performance' in stats
        assert 'workflow_statistics' in stats
        assert 'model_status' in stats

    def test_cleanup_old_patterns(self, optimizer):
        """Test cleanup of old pattern data."""
        # Create old pattern data
        old_time = datetime.now() - timedelta(days=100)
        recent_time = datetime.now() - timedelta(days=10)

        with sqlite3.connect(optimizer.db_path) as conn:
            # Insert old pattern
            conn.execute("""
                INSERT INTO workflow_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "old_pattern", "old_workflow", "hash1", 0.5, 0.3, 0.6, 3,
                old_time, old_time, "{}"
            ))

            # Insert recent pattern with sufficient samples
            conn.execute("""
                INSERT INTO workflow_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "recent_pattern", "recent_workflow", "hash2", 0.8, 0.2, 0.9, 20,
                recent_time, recent_time, "{}"
            ))

            # Insert old execution
            conn.execute("""
                INSERT INTO workflow_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "old_exec", "old_workflow", "{}", "{}", 1.0, 1, old_time, "agent1", "{}"
            ))

            conn.commit()

        deleted_count = optimizer.cleanup_old_patterns(days_to_keep=90)

        # Should have deleted old data
        assert deleted_count >= 1

        # Verify recent pattern still exists
        with sqlite3.connect(optimizer.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM workflow_patterns WHERE pattern_id = 'recent_pattern'")
            assert cursor.fetchone()[0] == 1

    def test_workflow_optimization_creation(self, optimizer):
        """Test creation of WorkflowOptimization objects."""
        optimization = WorkflowOptimization(
            workflow_id="test_workflow_123",
            optimization_type="pattern_based",
            current_performance=0.7,
            predicted_improvement=0.15,
            confidence=0.85,
            recommended_changes=["Increase agent count", "Optimize resource allocation"],
            effort_estimate="medium",
            impact_score=0.85 * 0.15
        )

        assert optimization.workflow_id == "test_workflow_123"
        assert optimization.optimization_type == "pattern_based"
        assert optimization.current_performance == 0.7
        assert optimization.predicted_improvement == 0.15
        assert optimization.confidence == 0.85
        assert len(optimization.recommended_changes) == 2
        assert optimization.effort_estimate == "medium"
        assert optimization.impact_score == 0.85 * 0.15

        # Test serialization
        opt_dict = optimization.to_dict()
        assert isinstance(opt_dict, dict)
        assert 'timestamp' in opt_dict

    def test_pattern_data_creation(self, optimizer):
        """Test creation of PatternData objects."""
        pattern = PatternData(
            pattern_id="test_pattern_1",
            workflow_type="test_workflow",
            performance_metrics={'score': 0.85, 'efficiency': 0.9},
            optimization_score=0.3,
            confidence=0.8,
            sample_count=25,
            last_updated=datetime.now(),
            metadata={'source': 'test'}
        )

        assert pattern.pattern_id == "test_pattern_1"
        assert pattern.workflow_type == "test_workflow"
        assert pattern.performance_metrics['score'] == 0.85
        assert pattern.optimization_score == 0.3
        assert pattern.confidence == 0.8
        assert pattern.sample_count == 25
        assert pattern.metadata['source'] == 'test'

        # Test serialization
        pattern_dict = pattern.to_dict()
        assert isinstance(pattern_dict, dict)
        assert pattern_dict['pattern_id'] == "test_pattern_1"

    def test_feature_extraction_and_normalization(self, optimizer):
        """Test feature extraction and normalization for pattern matching."""
        features1 = {
            'task_complexity': 2.3,  # Should be binned to 2
            'agent_count': 3.7,      # Should be binned to 3
            'resource_usage': 0.83,  # Should be rounded to 0.8
            'queue_size': 5.2        # Should be binned to 5
        }

        features2 = {
            'task_complexity': 2.1,  # Should be binned to 2
            'agent_count': 3.9,      # Should be binned to 3
            'resource_usage': 0.84,  # Should be rounded to 0.8
            'queue_size': 5.8        # Should be binned to 5
        }

        # These should produce the same hash due to normalization
        hash1 = optimizer._hash_features(features1)
        hash2 = optimizer._hash_features(features2)

        assert hash1 == hash2

    def test_estimate_effort_calculation(self, optimizer):
        """Test effort estimation for optimization changes."""
        high_effort_changes = [
            "Redesign the entire architecture",
            "Refactor core algorithms"
        ]

        medium_effort_changes = [
            "Increase agent count to 5",
            "Implement new optimization strategy"
        ]

        low_effort_changes = [
            "Adjust queue size parameter",
            "Tune resource allocation"
        ]

        assert optimizer._estimate_effort(high_effort_changes) == "high"
        assert optimizer._estimate_effort(medium_effort_changes) == "medium"
        assert optimizer._estimate_effort(low_effort_changes) == "medium"  # Default for implement

    def test_concurrent_pattern_updates(self, optimizer):
        """Test thread safety of pattern updates."""
        import threading
        import time

        def record_executions(thread_id):
            for i in range(5):
                features = {
                    'task_complexity': 1.0 + thread_id * 0.1,
                    'agent_count': 2 + thread_id,
                    'resource_usage': 0.5 + i * 0.1
                }

                performance_metrics = {
                    'completion_time': 1.0,
                    'success_rate': 0.9
                }

                optimizer.record_workflow_execution(
                    execution_id=f"thread_{thread_id}_exec_{i}",
                    workflow_type="concurrent_test",
                    features=features,
                    performance_metrics=performance_metrics,
                    execution_time=1.0,
                    success=True
                )
                time.sleep(0.01)  # Small delay to test concurrency

        # Run multiple threads
        threads = []
        for t in range(3):
            thread = threading.Thread(target=record_executions, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all executions were recorded
        with sqlite3.connect(optimizer.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM workflow_executions
                WHERE workflow_type = 'concurrent_test'
            """)
            count = cursor.fetchone()[0]
            assert count == 15  # 3 threads * 5 executions each

    def test_error_handling_invalid_data(self, optimizer):
        """Test error handling with invalid data."""
        # Test with missing required features
        try:
            optimizer.record_workflow_execution(
                execution_id="invalid_test",
                workflow_type="test",
                features={},  # Empty features
                performance_metrics={},  # Empty metrics
                execution_time=1.0,
                success=True
            )
            # Should not raise exception but handle gracefully
        except Exception as e:
            pytest.fail(f"Should handle empty data gracefully: {e}")

        # Test performance score calculation with missing metrics
        score = optimizer._calculate_performance_score({})
        assert score == 0.0  # Should return 0 for no data

    @patch('ml_enhancements.pattern_optimizer.logger')
    def test_logging_integration(self, mock_logger, optimizer):
        """Test that logging is properly integrated."""
        optimizer.record_workflow_execution(
            execution_id="log_test",
            workflow_type="logging_test",
            features={'task_complexity': 1.0},
            performance_metrics={'success_rate': 0.9},
            execution_time=1.0,
            success=True
        )

        # Verify debug logging was called
        mock_logger.debug.assert_called_with("Recorded workflow execution: log_test")
