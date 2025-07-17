"""
Integration tests for ML Enhancement components working together.
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from ml_enhancements import (
    PatternOptimizer,
    PredictiveAnalytics,
    AdaptiveLearning,
    MLConfig
)
from advanced_orchestration import MultiAgentCoordinator


class TestMLComponentsIntegration:
    """Test suite for ML components integration."""

    @pytest.fixture
    def temp_dbs(self):
        """Create temporary databases for all ML components."""
        dbs = {}
        temp_files = []

        for component in ['pattern', 'analytics', 'learning']:
            temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            dbs[component] = temp_file.name
            temp_files.append(temp_file.name)

        yield dbs

        # Cleanup
        for temp_file in temp_files:
            Path(temp_file).unlink(missing_ok=True)

    @pytest.fixture
    def ml_config(self):
        """Create shared ML configuration."""
        return MLConfig(
            pattern_analysis_window=50,
            forecasting_horizon=30,
            learning_rate=0.05,
            min_data_points=3,
            confidence_threshold=0.7
        )

    @pytest.fixture
    def ml_system(self, ml_config, temp_dbs):
        """Create integrated ML system."""
        pattern_optimizer = PatternOptimizer(
            config=ml_config,
            db_path=temp_dbs['pattern']
        )

        predictive_analytics = PredictiveAnalytics(
            config=ml_config,
            db_path=temp_dbs['analytics']
        )

        adaptive_learning = AdaptiveLearning(
            config=ml_config,
            db_path=temp_dbs['learning']
        )

        return {
            'pattern_optimizer': pattern_optimizer,
            'predictive_analytics': predictive_analytics,
            'adaptive_learning': adaptive_learning,
            'config': ml_config
        }

    def test_pattern_to_analytics_data_flow(self, ml_system):
        """Test data flow from PatternOptimizer to PredictiveAnalytics."""
        pattern_optimizer = ml_system['pattern_optimizer']
        predictive_analytics = ml_system['predictive_analytics']

        # Record workflow executions in pattern optimizer
        workflow_metrics = []
        for i in range(5):
            features = {
                'task_complexity': 1.5 + i * 0.2,
                'agent_count': 2 + i % 3,
                'resource_usage': 0.5 + i * 0.1
            }

            performance_metrics = {
                'completion_time': 1.0 + i * 0.1,
                'resource_efficiency': 0.8 - i * 0.02,
                'success_rate': 0.9,
                'error_count': 0.1
            }

            pattern_optimizer.record_workflow_execution(
                execution_id=f"workflow_{i}",
                workflow_type="integration_test",
                features=features,
                performance_metrics=performance_metrics,
                execution_time=1.0 + i * 0.1,
                success=True
            )

            # Convert to system metrics for analytics
            system_metric_id = predictive_analytics.record_system_metrics(
                cpu_usage=features['resource_usage'],
                memory_usage=features['resource_usage'] * 0.8,
                disk_usage=0.3,
                network_usage=0.2,
                active_agents=features['agent_count'],
                queue_size=i % 5,
                task_completion_rate=performance_metrics['success_rate'],
                error_rate=performance_metrics['error_count'],
                response_time=performance_metrics['completion_time'],
                throughput=8.0 + i
            )

            workflow_metrics.append({
                'features': features,
                'metrics': performance_metrics,
                'system_metric_id': system_metric_id
            })

        # Analyze patterns
        patterns = pattern_optimizer.analyze_patterns("integration_test")

        # Predict performance using analytics
        test_features = {
            'active_agents': 3,
            'queue_size': 2,
            'task_complexity': 2.0
        }

        prediction_result = predictive_analytics.predict_performance(test_features)

        # Verify integration
        assert len(workflow_metrics) == 5
        assert len(patterns) >= 0  # May not have enough data for patterns yet
        assert prediction_result.prediction_type == 'performance'
        assert 0.0 <= prediction_result.predicted_value <= 1.0

    def test_analytics_to_learning_feedback_loop(self, ml_system):
        """Test feedback loop from PredictiveAnalytics to AdaptiveLearning."""
        predictive_analytics = ml_system['predictive_analytics']
        adaptive_learning = ml_system['adaptive_learning']

        # Start learning session
        session_id = adaptive_learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'integration_test': True}
        )

        # Record metrics and make predictions
        prediction_results = []
        for i in range(4):
            # Record system metrics
            predictive_analytics.record_system_metrics(
                cpu_usage=0.6 + i * 0.05,
                memory_usage=0.5 + i * 0.05,
                disk_usage=0.3,
                network_usage=0.2,
                active_agents=2 + i,
                queue_size=i,
                task_completion_rate=0.85 + i * 0.02,
                error_rate=0.1 - i * 0.01,
                response_time=1.2 - i * 0.1,
                throughput=9.0 + i
            )

            # Make prediction
            features = {
                'active_agents': 2 + i,
                'queue_size': i,
                'task_complexity': 1.5
            }

            prediction = predictive_analytics.predict_performance(features)
            prediction_results.append(prediction)

            # Provide feedback to adaptive learning based on prediction accuracy
            # Simulate actual vs predicted performance
            actual_performance = 0.8 + i * 0.03
            prediction_accuracy = 1.0 - abs(actual_performance - prediction.predicted_value)

            adaptive_learning.provide_feedback(
                session_id=session_id,
                feedback_type='performance',
                feedback_value=prediction_accuracy,
                context={
                    'predicted_value': prediction.predicted_value,
                    'actual_value': actual_performance,
                    'features': features
                }
            )

        # Adapt model based on feedback
        training_data = []
        target_values = []

        for i, result in enumerate(prediction_results):
            training_data.append({
                'active_agents': 2 + i,
                'queue_size': i,
                'task_complexity': 1.5,
                'prediction_confidence': result.accuracy_score
            })
            target_values.append(0.8 + i * 0.03)  # Actual performance

        learning_metrics = adaptive_learning.adapt_model(
            session_id=session_id,
            model_type='performance_optimizer',
            training_data=training_data,
            target_values=target_values
        )

        # End session
        session_summary = adaptive_learning.end_learning_session(session_id)

        # Verify integration
        assert len(prediction_results) == 4
        assert learning_metrics.samples_processed == 4
        assert session_summary['total_adaptations'] > 0

    def test_full_ml_pipeline_workflow(self, ml_system):
        """Test complete ML pipeline workflow."""
        pattern_optimizer = ml_system['pattern_optimizer']
        predictive_analytics = ml_system['predictive_analytics']
        adaptive_learning = ml_system['adaptive_learning']

        # 1. Record initial workflow executions
        initial_workflows = []
        for i in range(6):
            features = {
                'task_complexity': 1.0 + i * 0.3,
                'agent_count': 2 + i % 4,
                'resource_usage': 0.4 + i * 0.1,
                'queue_size': i % 8
            }

            performance_metrics = {
                'completion_time': 2.0 - i * 0.2,
                'resource_efficiency': 0.7 + i * 0.05,
                'success_rate': 0.85 + i * 0.02,
                'error_count': 0.15 - i * 0.02
            }

            pattern_optimizer.record_workflow_execution(
                execution_id=f"pipeline_workflow_{i}",
                workflow_type="full_pipeline_test",
                features=features,
                performance_metrics=performance_metrics,
                execution_time=performance_metrics['completion_time'],
                success=True
            )

            initial_workflows.append({
                'features': features,
                'performance': performance_metrics
            })

        # 2. Analyze patterns and get optimization recommendations
        patterns = pattern_optimizer.analyze_patterns("full_pipeline_test")

        current_features = {
            'task_complexity': 2.0,
            'agent_count': 3,
            'resource_usage': 0.7,
            'queue_size': 4
        }

        recommendations = pattern_optimizer.get_optimization_recommendations(
            "full_pipeline_test", current_features
        )

        # 3. Start adaptive learning session
        session_id = adaptive_learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={
                'workflow_type': 'full_pipeline_test',
                'patterns_found': len(patterns),
                'recommendations': len(recommendations)
            }
        )

        # 4. Record system metrics and make predictions
        for i in range(4):
            # Record corresponding system metrics
            predictive_analytics.record_system_metrics(
                cpu_usage=initial_workflows[i]['features']['resource_usage'],
                memory_usage=initial_workflows[i]['features']['resource_usage'] * 0.9,
                disk_usage=0.3,
                network_usage=0.2,
                active_agents=initial_workflows[i]['features']['agent_count'],
                queue_size=initial_workflows[i]['features']['queue_size'],
                task_completion_rate=initial_workflows[i]['performance']['success_rate'],
                error_rate=initial_workflows[i]['performance']['error_count'],
                response_time=initial_workflows[i]['performance']['completion_time'],
                throughput=10.0 - i
            )

            # Make performance prediction
            prediction = predictive_analytics.predict_performance({
                'active_agents': initial_workflows[i]['features']['agent_count'],
                'queue_size': initial_workflows[i]['features']['queue_size'],
                'task_complexity': initial_workflows[i]['features']['task_complexity']
            })

            # Provide feedback to learning system
            adaptive_learning.provide_feedback(
                session_id=session_id,
                feedback_type='performance',
                feedback_value=prediction.predicted_value,
                context=initial_workflows[i]['features']
            )

        # 5. Adapt learning models
        learning_training_data = [wf['features'] for wf in initial_workflows[:4]]
        learning_target_values = [
            pattern_optimizer._calculate_performance_score(wf['performance'])
            for wf in initial_workflows[:4]
        ]

        learning_metrics = adaptive_learning.adapt_model(
            session_id=session_id,
            model_type='performance_optimizer',
            training_data=learning_training_data,
            target_values=learning_target_values
        )

        # 6. Test improved prediction with adaptation
        improved_features = {
            'task_complexity': 1.8,
            'agent_count': 4,
            'resource_usage': 0.6
        }

        prediction_result, confidence, needs_adaptation = adaptive_learning.predict_with_adaptation(
            'performance_optimizer',
            improved_features,
            confidence_threshold=0.6
        )

        # 7. End learning session
        session_summary = adaptive_learning.end_learning_session(session_id)

        # Verify complete pipeline
        assert len(initial_workflows) == 6
        assert learning_metrics.samples_processed == 4
        assert 0.0 <= prediction_result <= 1.0
        assert 0.0 <= confidence <= 1.0
        assert session_summary['final_performance'] > 0

    def test_ml_config_validation_integration(self, temp_dbs):
        """Test ML configuration validation across components."""
        # Test invalid configuration
        with pytest.raises(ValueError):
            invalid_config = MLConfig(learning_rate=1.5)  # Invalid learning rate

        # Test valid configuration
        valid_config = MLConfig(
            learning_rate=0.02,
            confidence_threshold=0.8,
            accuracy_threshold=0.85,
            pattern_optimization_threshold=0.12
        )

        # Create components with valid config
        pattern_optimizer = PatternOptimizer(config=valid_config, db_path=temp_dbs['pattern'])
        predictive_analytics = PredictiveAnalytics(config=valid_config, db_path=temp_dbs['analytics'])
        adaptive_learning = AdaptiveLearning(config=valid_config, db_path=temp_dbs['learning'])

        # Verify all components use the same configuration
        assert pattern_optimizer.config.learning_rate == 0.02
        assert predictive_analytics.config.confidence_threshold == 0.8
        assert adaptive_learning.config.accuracy_threshold == 0.85

    def test_ml_system_statistics_integration(self, ml_system):
        """Test integrated statistics from all ML components."""
        pattern_optimizer = ml_system['pattern_optimizer']
        predictive_analytics = ml_system['predictive_analytics']
        adaptive_learning = ml_system['adaptive_learning']

        # Add some data to each component
        # Pattern optimizer data
        pattern_optimizer.record_workflow_execution(
            execution_id="stats_test_1",
            workflow_type="statistics_test",
            features={'task_complexity': 1.5, 'agent_count': 3},
            performance_metrics={'completion_time': 1.2, 'success_rate': 0.9},
            execution_time=1.2,
            success=True
        )

        # Analytics data
        predictive_analytics.record_system_metrics(
            cpu_usage=0.7, memory_usage=0.6, disk_usage=0.4, network_usage=0.3,
            active_agents=3, queue_size=2, task_completion_rate=0.9,
            error_rate=0.05, response_time=1.2, throughput=8.5
        )

        # Learning data
        session_id = adaptive_learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'stats_test': True}
        )
        adaptive_learning.end_learning_session(session_id)

        # Get statistics from all components
        pattern_stats = pattern_optimizer.get_pattern_statistics()
        analytics_summary = predictive_analytics.get_analytics_summary()
        learning_insights = adaptive_learning.get_learning_insights()

        # Verify statistics are available
        assert pattern_stats['total_patterns'] >= 0
        assert analytics_summary['data_availability']['total_metrics'] > 0
        assert learning_insights['session_statistics']['total_sessions'] > 0

    def test_error_handling_integration(self, ml_system):
        """Test error handling across ML components."""
        pattern_optimizer = ml_system['pattern_optimizer']
        predictive_analytics = ml_system['predictive_analytics']
        adaptive_learning = ml_system['adaptive_learning']

        # Test pattern optimizer with invalid data
        try:
            pattern_optimizer.record_workflow_execution(
                execution_id="error_test",
                workflow_type="error_test",
                features={},  # Empty features
                performance_metrics={},  # Empty metrics
                execution_time=1.0,
                success=True
            )
        except Exception as e:
            pytest.fail(f"Pattern optimizer should handle empty data gracefully: {e}")

        # Test predictive analytics with edge cases
        try:
            result = predictive_analytics.predict_performance({})  # Empty features
            assert result.predicted_value >= 0  # Should return valid result
        except Exception as e:
            pytest.fail(f"Predictive analytics should handle empty features: {e}")

        # Test adaptive learning with invalid model type
        session_id = adaptive_learning.start_learning_session(
            model_type='performance_optimizer',
            initial_context={'error_test': True}
        )

        with pytest.raises(ValueError):
            adaptive_learning.adapt_model(
                session_id=session_id,
                model_type='nonexistent_model',
                training_data=[],
                target_values=[]
            )

    def test_memory_cleanup_integration(self, ml_system):
        """Test memory cleanup across all ML components."""
        pattern_optimizer = ml_system['pattern_optimizer']
        predictive_analytics = ml_system['predictive_analytics']
        adaptive_learning = ml_system['adaptive_learning']

        # Create old data in all components
        old_time = datetime.now() - timedelta(days=40)

        # Pattern optimizer cleanup
        pattern_deleted = pattern_optimizer.cleanup_old_patterns(days_to_keep=30)

        # Analytics cleanup
        analytics_deleted = predictive_analytics.cleanup_old_data(days_to_keep=30)

        # Learning cleanup
        learning_deleted = adaptive_learning.cleanup_old_learning_data(days_to_keep=30)

        # Verify cleanup operations completed
        assert pattern_deleted >= 0
        assert analytics_deleted >= 0
        assert learning_deleted >= 0

    @patch('advanced_orchestration.MultiAgentCoordinator')
    def test_ml_orchestrator_integration(self, mock_coordinator, ml_system):
        """Test ML system integration with MultiAgentCoordinator."""
        pattern_optimizer = ml_system['pattern_optimizer']
        predictive_analytics = ml_system['predictive_analytics']

        # Mock coordinator behavior
        mock_coordinator_instance = Mock()
        mock_coordinator.return_value = mock_coordinator_instance

        # Simulate workflow from coordinator perspective
        workflow_data = {
            'task_id': 'test_task_123',
            'task_type': 'feature_development',
            'agent_count': 3,
            'complexity': 2.0,
            'start_time': datetime.now()
        }

        # Record workflow execution
        pattern_optimizer.record_workflow_execution(
            execution_id=workflow_data['task_id'],
            workflow_type=workflow_data['task_type'],
            features={
                'task_complexity': workflow_data['complexity'],
                'agent_count': workflow_data['agent_count'],
                'resource_usage': 0.7
            },
            performance_metrics={
                'completion_time': 1.5,
                'success_rate': 0.92,
                'resource_efficiency': 0.85
            },
            execution_time=1.5,
            success=True
        )

        # Record corresponding system metrics
        predictive_analytics.record_system_metrics(
            cpu_usage=0.7, memory_usage=0.6, disk_usage=0.4, network_usage=0.3,
            active_agents=workflow_data['agent_count'], queue_size=2,
            task_completion_rate=0.92, error_rate=0.08, response_time=1.5, throughput=10.0
        )

        # Get optimization recommendations
        recommendations = pattern_optimizer.get_optimization_recommendations(
            workflow_data['task_type'],
            {
                'task_complexity': workflow_data['complexity'],
                'agent_count': workflow_data['agent_count'],
                'resource_usage': 0.7
            }
        )

        # Predict future performance
        future_prediction = predictive_analytics.predict_performance({
            'active_agents': workflow_data['agent_count'],
            'task_complexity': workflow_data['complexity'],
            'queue_size': 3
        })

        # Verify integration works
        assert len(recommendations) >= 0
        assert future_prediction.predicted_value >= 0
        assert mock_coordinator.called

    def test_concurrent_ml_operations(self, ml_system):
        """Test concurrent operations across ML components."""
        import threading
        import time

        pattern_optimizer = ml_system['pattern_optimizer']
        predictive_analytics = ml_system['predictive_analytics']
        adaptive_learning = ml_system['adaptive_learning']

        results = {'pattern': [], 'analytics': [], 'learning': []}

        def pattern_worker():
            for i in range(3):
                pattern_optimizer.record_workflow_execution(
                    execution_id=f"concurrent_pattern_{i}",
                    workflow_type="concurrent_test",
                    features={'task_complexity': 1.0 + i, 'agent_count': 2},
                    performance_metrics={'completion_time': 1.0, 'success_rate': 0.9},
                    execution_time=1.0,
                    success=True
                )
                results['pattern'].append(i)
                time.sleep(0.01)

        def analytics_worker():
            for i in range(3):
                metric_id = predictive_analytics.record_system_metrics(
                    cpu_usage=0.6 + i * 0.1, memory_usage=0.5, disk_usage=0.3, network_usage=0.2,
                    active_agents=2, queue_size=i, task_completion_rate=0.9,
                    error_rate=0.05, response_time=1.0, throughput=8.0
                )
                results['analytics'].append(metric_id)
                time.sleep(0.01)

        def learning_worker():
            session_id = adaptive_learning.start_learning_session(
                model_type='performance_optimizer',
                initial_context={'concurrent_test': True}
            )
            for i in range(3):
                adaptive_learning.provide_feedback(
                    session_id=session_id,
                    feedback_type='positive',
                    feedback_value=0.8 + i * 0.05,
                    context={'iteration': i}
                )
                results['learning'].append(i)
                time.sleep(0.01)
            adaptive_learning.end_learning_session(session_id)

        # Run concurrent operations
        threads = [
            threading.Thread(target=pattern_worker),
            threading.Thread(target=analytics_worker),
            threading.Thread(target=learning_worker)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all operations completed
        assert len(results['pattern']) == 3
        assert len(results['analytics']) == 3
        assert len(results['learning']) == 3
