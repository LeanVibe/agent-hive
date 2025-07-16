"""
Comprehensive test suite for ML intelligence components.

Tests the intelligence framework's ML-based algorithms for confidence scoring,
decision making, performance analysis, and learning integration.
"""

import asyncio
import pytest
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

from intelligence_framework import (
    IntelligenceFramework, IntelligenceConfig, DecisionType, 
    IntelligenceDecision, AgentIntelligence, IntelligenceLevel
)
from advanced_orchestration.models import CoordinatorConfig, AgentInfo, CoordinatorState, ResourceUsage
from ml_enhancements.models import MLConfig


class TestIntelligenceMLComponents:
    """Test suite for ML-based intelligence components."""
    
    @pytest.fixture
    async def intelligence_framework(self):
        """Create intelligence framework for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            config = IntelligenceConfig(
                db_path=tmp_db.name,
                decision_confidence_threshold=0.8,
                learning_update_interval=10,
                analytics_update_interval=20
            )
            
            framework = IntelligenceFramework(config)
            
            # Mock the coordinator and ML components
            framework.coordinator = AsyncMock()
            framework.adaptive_learning = MagicMock()
            framework.predictive_analytics = MagicMock()
            framework.pattern_optimizer = MagicMock()
            
            await framework.start()
            yield framework
            await framework.stop()
    
    @pytest.fixture
    def mock_coordinator_state(self):
        """Create mock coordinator state for testing."""
        resource_usage = ResourceUsage(
            cpu_percent=0.5,
            memory_percent=0.6,
            disk_percent=0.3,
            network_percent=0.4
        )
        
        mock_agent = MagicMock()
        mock_agent.agent_id = "test_agent_1"
        mock_agent.active_tasks = 2
        mock_agent.error_count = 0
        mock_agent.current_usage = resource_usage
        
        state = MagicMock()
        state.resource_usage = resource_usage
        state.active_agents = {"test_agent_1": mock_agent}
        state.pending_tasks = []
        state.assigned_tasks = []
        
        return state
    
    @pytest.mark.asyncio
    async def test_ml_confidence_calculation_multi_factor(self, intelligence_framework):
        """Test ML-based confidence calculation with multiple factors."""
        
        # Setup test data
        decision_type = DecisionType.TASK_ALLOCATION
        context = {
            'agent_count': 3,
            'queue_size': 5,
            'task_complexity': 1.5,
            'resource_usage': 0.6,
            'historical_performance': [0.8, 0.85, 0.9]
        }
        recommendation = {
            'action': 'assign_task',
            'agent_id': 'test_agent_1',
            'confidence': 0.85
        }
        analysis = {
            'context_complexity': 0.4,
            'historical_patterns': [
                {'performance_score': 0.9, 'sample_count': 10, 'features': context}
            ],
            'predictive_insights': {
                'accuracy_score': 0.88,
                'prediction_variance': 0.15,
                'feature_importance': {'agent_count': 0.3, 'queue_size': 0.4}
            }
        }
        
        # Mock database responses for historical data
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (0.85, True, 2.5),  # confidence, success, execution_time
                (0.90, True, 1.8),
                (0.75, False, 3.2)
            ]
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            # Calculate confidence
            confidence = await intelligence_framework._calculate_decision_confidence(
                decision_type, context, recommendation, analysis
            )
        
        # Verify confidence is calculated using ML algorithms
        assert 0.1 <= confidence <= 0.95
        assert isinstance(confidence, float)
        
        # Verify the confidence accounts for multiple factors
        # Should be higher than base confidence due to good historical patterns and insights
        assert confidence > 0.6
    
    @pytest.mark.asyncio
    async def test_pattern_similarity_confidence(self, intelligence_framework):
        """Test pattern similarity confidence calculation."""
        
        decision_type = DecisionType.RESOURCE_OPTIMIZATION
        context = {'resource_usage': 0.7, 'agent_count': 4, 'priority': 'high'}
        patterns = [
            {
                'features': {'resource_usage': 0.75, 'agent_count': 4, 'priority_score': 0.8},
                'performance_score': 0.9,
                'sample_count': 15
            },
            {
                'features': {'resource_usage': 0.6, 'agent_count': 3, 'priority_score': 0.8},
                'performance_score': 0.7,
                'sample_count': 8
            }
        ]
        
        # Test pattern similarity calculation
        confidence = await intelligence_framework._calculate_pattern_similarity_confidence(
            decision_type, context, patterns
        )
        
        assert 0.1 <= confidence <= 0.95
        assert isinstance(confidence, float)
        
        # Test with no patterns
        empty_confidence = await intelligence_framework._calculate_pattern_similarity_confidence(
            decision_type, context, []
        )
        assert empty_confidence == 0.3
    
    @pytest.mark.asyncio
    async def test_context_completeness_confidence(self, intelligence_framework):
        """Test context completeness confidence calculation."""
        
        # Test with complete context for task allocation
        complete_context = {
            'agent_count': 3,
            'queue_size': 5,
            'task_complexity': 1.5,
            'historical_performance': [0.8, 0.9],
            'agent_specializations': ['optimization', 'analysis']
        }
        
        confidence = intelligence_framework._calculate_context_completeness_confidence(
            complete_context, DecisionType.TASK_ALLOCATION
        )
        
        assert confidence > 0.8  # Should have high confidence with complete context
        
        # Test with minimal context
        minimal_context = {'agent_count': 2}
        
        minimal_confidence = intelligence_framework._calculate_context_completeness_confidence(
            minimal_context, DecisionType.TASK_ALLOCATION
        )
        
        assert minimal_confidence < confidence  # Should have lower confidence
        assert minimal_confidence > 0.1
    
    @pytest.mark.asyncio
    async def test_historical_decision_confidence(self, intelligence_framework):
        """Test historical decision confidence calculation."""
        
        decision_type = DecisionType.PERFORMANCE_TUNING
        
        # Mock database with successful historical decisions
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (0.85, True, 2.5),   # confidence, success, execution_time
                (0.90, True, 1.8),
                (0.80, True, 2.1),
                (0.75, True, 2.8),
                (0.88, True, 1.9)
            ]
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            confidence = await intelligence_framework._calculate_historical_decision_confidence(decision_type)
        
        assert confidence > 0.7  # Should have high confidence with successful history
        assert confidence <= 0.95
        
        # Test with mixed success history
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (0.85, True, 2.5),
                (0.70, False, 4.0),
                (0.80, True, 2.1),
                (0.60, False, 5.0)
            ]
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            mixed_confidence = await intelligence_framework._calculate_historical_decision_confidence(decision_type)
        
        assert mixed_confidence < confidence  # Should be lower with mixed results
        assert mixed_confidence > 0.3
    
    @pytest.mark.asyncio
    async def test_resource_availability_confidence(self, intelligence_framework, mock_coordinator_state):
        """Test resource availability confidence calculation."""
        
        intelligence_framework.coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        context = {'estimated_resource_usage': 0.3}
        
        confidence = await intelligence_framework._calculate_resource_availability_confidence(context)
        
        assert 0.1 <= confidence <= 0.95
        assert isinstance(confidence, float)
        
        # Should have reasonable confidence with moderate resource usage
        assert confidence > 0.4
    
    @pytest.mark.asyncio
    async def test_agent_performance_calculation_ml_based(self, intelligence_framework):
        """Test ML-based agent performance calculation."""
        
        # Mock agent info
        mock_agent_info = MagicMock()
        mock_agent_info.active_tasks = 3
        mock_agent_info.error_count = 1
        mock_agent_info.avg_response_time = 2.5
        mock_agent_info.current_usage = MagicMock()
        mock_agent_info.current_usage.cpu_percent = 0.6
        mock_agent_info.current_usage.memory_percent = 0.5
        mock_agent_info.max_concurrent_tasks = 5
        
        intelligence_framework.coordinator.get_agent_status.return_value = mock_agent_info
        
        # Mock historical performance data
        with patch.object(intelligence_framework, '_get_agent_historical_performance', return_value=0.8):
            performance = await intelligence_framework._calculate_agent_performance("test_agent_1")
        
        assert 0.1 <= performance <= 1.0
        assert isinstance(performance, float)
        
        # Should calculate performance using multiple factors
        # With the given metrics, should have reasonable performance
        assert performance > 0.5
    
    @pytest.mark.asyncio
    async def test_learning_progress_calculation_adaptive(self, intelligence_framework):
        """Test adaptive learning progress calculation."""
        
        agent_id = "test_agent_1"
        
        # Mock active learning session
        intelligence_framework.active_learning_sessions = {agent_id: "session_123"}
        intelligence_framework.model_performance = {"session_123": [0.6, 0.7, 0.8, 0.85]}
        
        # Mock historical learning data
        mock_db_responses = [
            [(0.15, 0.12, 0.18, 0.20)],  # improvement_rates
            [(0.85, True, 2.5), (0.90, True, 1.8)],  # adaptation_speed data
            [(0.8, True), (0.85, True), (0.9, True)]  # knowledge_retention data
        ]
        
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.side_effect = mock_db_responses
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            progress = await intelligence_framework._calculate_learning_progress(agent_id)
        
        assert 0.0 <= progress <= 1.0
        assert isinstance(progress, float)
        
        # Should have good progress with active session and historical data
        assert progress > 0.6
    
    @pytest.mark.asyncio
    async def test_decision_accuracy_ml_analysis(self, intelligence_framework):
        """Test ML-based decision accuracy calculation."""
        
        agent_id = "test_agent_1"
        
        # Mock decision history with various outcomes
        mock_decisions = [
            ("task_allocation", 0.85, True, 2.5),   # decision_type, confidence, success, exec_time
            ("resource_optimization", 0.70, False, 4.0),
            ("task_allocation", 0.90, True, 1.8),
            ("scaling_decision", 0.80, True, 2.1),
            ("performance_tuning", 0.75, True, 2.8)
        ]
        
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = mock_decisions
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            accuracy = await intelligence_framework._calculate_decision_accuracy(agent_id)
        
        assert 0.1 <= accuracy <= 1.0
        assert isinstance(accuracy, float)
        
        # Should calculate accuracy using multiple factors including calibration
        assert accuracy > 0.5  # Should be decent with mostly successful decisions
    
    @pytest.mark.asyncio
    async def test_performance_trend_analysis_ml(self, intelligence_framework):
        """Test ML-based performance trend analysis."""
        
        # Mock performance data showing improving trend
        improving_data = [
            ("2024-01-01T10:00:00", 0.7, True),
            ("2024-01-01T11:00:00", 0.75, True),
            ("2024-01-01T12:00:00", 0.8, True),
            ("2024-01-01T13:00:00", 0.85, True),
            ("2024-01-01T14:00:00", 0.9, True)
        ]
        
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = improving_data
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            trend = intelligence_framework._calculate_performance_trend()
        
        assert trend in ["improving", "declining", "stable", "insufficient_data", "unknown"]
        
        # With improving data, should detect improvement
        assert trend == "improving"
        
        # Test with declining trend
        declining_data = [
            ("2024-01-01T10:00:00", 0.9, True),
            ("2024-01-01T11:00:00", 0.85, True),
            ("2024-01-01T12:00:00", 0.8, False),
            ("2024-01-01T13:00:00", 0.75, False),
            ("2024-01-01T14:00:00", 0.7, False)
        ]
        
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = declining_data
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            trend = intelligence_framework._calculate_performance_trend()
        
        assert trend == "declining"
    
    @pytest.mark.asyncio
    async def test_resource_impact_analysis_ml_predictions(self, intelligence_framework, mock_coordinator_state):
        """Test ML-based resource impact analysis."""
        
        intelligence_framework.coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        # Mock predictive analytics
        mock_prediction = MagicMock()
        mock_prediction.predicted_usage = 0.75
        intelligence_framework.predictive_analytics.predict_resource_usage.return_value = mock_prediction
        
        # Mock pattern optimizer
        intelligence_framework.pattern_optimizer.get_task_patterns.return_value = [
            {'performance_score': 0.9, 'workflow_type': 'optimization'}
        ]
        
        resource_requirements = {
            'cpu_cores': 2,
            'memory_mb': 1024,
            'network_mbps': 10,
            'duration_minutes': 15,
            'task_complexity': 2.0
        }
        
        impact_analysis = await intelligence_framework._analyze_resource_impact(resource_requirements)
        
        # Verify comprehensive analysis structure
        assert 'cpu_impact' in impact_analysis
        assert 'memory_impact' in impact_analysis
        assert 'network_impact' in impact_analysis
        assert 'agent_capacity_impact' in impact_analysis
        assert 'predicted_bottlenecks' in impact_analysis
        assert 'optimization_opportunities' in impact_analysis
        assert 'risk_assessment' in impact_analysis
        assert 'overall_impact' in impact_analysis
        
        # Verify impact scores are calculated
        cpu_impact = impact_analysis['cpu_impact']
        assert 'impact_score' in cpu_impact
        assert 'impact_level' in cpu_impact
        assert 'predicted_usage' in cpu_impact
        assert 'recommendation' in cpu_impact
        
        # Verify overall impact classification
        assert impact_analysis['overall_impact'] in ['low', 'medium', 'high', 'critical']
    
    @pytest.mark.asyncio
    async def test_learning_system_integration(self, intelligence_framework):
        """Test integration between intelligence framework and learning system."""
        
        # Setup agent intelligence
        agent_intelligence = AgentIntelligence(
            agent_id="test_agent_1",
            intelligence_level=IntelligenceLevel.INTERMEDIATE,
            specializations=["optimization"],
            performance_score=0.6,  # Below threshold for learning
            learning_progress=0.4,
            decision_accuracy=0.65
        )
        
        intelligence_framework.agent_intelligence = {"test_agent_1": agent_intelligence}
        intelligence_framework.adaptive_learning.start_learning_session.return_value = "session_123"
        intelligence_framework.adaptive_learning.convergence_tracking = {}
        
        # Test learning session management
        await intelligence_framework._manage_adaptive_learning_sessions()
        
        # Verify learning session was started for underperforming agent
        intelligence_framework.adaptive_learning.start_learning_session.assert_called_once()
        call_args = intelligence_framework.adaptive_learning.start_learning_session.call_args
        assert call_args[0][0] == 'performance_optimizer'  # Strategy for low performance
        assert 'agent_id' in call_args[0][1]
        assert call_args[0][1]['agent_id'] == "test_agent_1"
    
    @pytest.mark.asyncio
    async def test_feedback_processing_loop(self, intelligence_framework):
        """Test decision feedback processing for learning improvement."""
        
        # Mock recent decisions
        mock_decisions = [
            ("dec_1", "task_allocation", 0.85, True, '{"action": "assign"}', '{"agent_id": "test_agent_1"}', "2024-01-01T10:00:00"),
            ("dec_2", "resource_optimization", 0.70, False, '{"action": "scale"}', '{"agent_id": "test_agent_2"}', "2024-01-01T10:30:00")
        ]
        
        # Setup active learning sessions
        intelligence_framework.active_learning_sessions = {
            "test_agent_1": "session_123",
            "test_agent_2": "session_456"
        }
        
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = mock_decisions
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            await intelligence_framework._process_decision_feedback()
        
        # Verify feedback was provided to learning sessions
        intelligence_framework.adaptive_learning.provide_feedback.assert_called()
        
        # Check that feedback was provided for both agents
        call_count = intelligence_framework.adaptive_learning.provide_feedback.call_count
        assert call_count >= 2  # At least one call per agent
    
    @pytest.mark.asyncio
    async def test_system_performance_calculation(self, intelligence_framework):
        """Test comprehensive system performance calculation."""
        
        # Setup multiple agent intelligences
        agent_intelligences = {
            "agent_1": AgentIntelligence(
                agent_id="agent_1",
                intelligence_level=IntelligenceLevel.ADVANCED,
                specializations=["optimization", "analysis"],
                performance_score=0.85,
                learning_progress=0.7,
                decision_accuracy=0.8
            ),
            "agent_2": AgentIntelligence(
                agent_id="agent_2", 
                intelligence_level=IntelligenceLevel.INTERMEDIATE,
                specializations=["coordination"],
                performance_score=0.75,
                learning_progress=0.6,
                decision_accuracy=0.7
            )
        }
        
        intelligence_framework.agent_intelligence = agent_intelligences
        
        # Mock recent decision success rate
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (10, 8)  # total, successful
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            performance = await intelligence_framework._calculate_system_performance()
        
        assert 0.0 <= performance <= 1.0
        assert isinstance(performance, float)
        
        # Should calculate weighted performance from multiple factors
        # With good agent metrics, should have decent system performance
        assert performance > 0.6
    
    def test_feature_similarity_calculation(self, intelligence_framework):
        """Test cosine similarity calculation for feature vectors."""
        
        features1 = {'agent_count': 3, 'queue_size': 5, 'task_complexity': 1.5}
        features2 = {'agent_count': 3, 'queue_size': 4, 'task_complexity': 1.6}
        
        similarity = intelligence_framework._calculate_feature_similarity(features1, features2)
        
        assert 0.0 <= similarity <= 1.0
        assert isinstance(similarity, float)
        
        # Similar features should have high similarity
        assert similarity > 0.8
        
        # Test with very different features
        features3 = {'agent_count': 10, 'queue_size': 1, 'task_complexity': 0.1}
        
        low_similarity = intelligence_framework._calculate_feature_similarity(features1, features3)
        assert low_similarity < similarity
        
        # Test with no common features
        features4 = {'different_metric': 1.0}
        
        no_similarity = intelligence_framework._calculate_feature_similarity(features1, features4)
        assert no_similarity == 0.0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self, intelligence_framework):
        """Test error handling and fallback behaviors in ML components."""
        
        # Test confidence calculation with database error
        with patch('sqlite3.connect', side_effect=Exception("Database error")):
            confidence = await intelligence_framework._calculate_decision_confidence(
                DecisionType.TASK_ALLOCATION, {}, {}, {}
            )
            
            assert confidence == 0.5  # Should return fallback confidence
        
        # Test performance calculation with missing agent
        intelligence_framework.coordinator.get_agent_status.return_value = None
        
        performance = await intelligence_framework._calculate_agent_performance("missing_agent")
        assert performance == 0.5  # Should return fallback performance
        
        # Test learning progress with no data
        progress = await intelligence_framework._calculate_learning_progress("new_agent")
        assert 0.0 <= progress <= 1.0  # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_ml_algorithm_integration_end_to_end(self, intelligence_framework, mock_coordinator_state):
        """Test end-to-end ML algorithm integration in decision making."""
        
        intelligence_framework.coordinator.get_coordinator_state.return_value = mock_coordinator_state
        
        # Setup ML components
        intelligence_framework.pattern_optimizer.get_task_patterns.return_value = [
            {'performance_score': 0.9, 'workflow_type': 'task_allocation', 'recommended_strategy': 'intelligent_selection'}
        ]
        
        mock_prediction = MagicMock()
        mock_prediction.predicted_value = 0.85
        mock_prediction.accuracy_score = 0.9
        mock_prediction.to_dict.return_value = {'predicted_value': 0.85, 'accuracy_score': 0.9}
        intelligence_framework.predictive_analytics.predict_performance.return_value = mock_prediction
        
        # Mock database for historical decisions
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                (0.85, True, 2.5),  # Historical decisions
                (0.90, True, 1.8)
            ]
            mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
            
            # Make a decision using ML algorithms
            decision = await intelligence_framework.make_decision(
                DecisionType.TASK_ALLOCATION,
                {
                    'agent_count': 3,
                    'queue_size': 5,
                    'task_complexity': 1.5,
                    'features': {'active_agents': 3, 'queue_size': 5}
                },
                [
                    {'agent_id': 'agent_1', 'capabilities': ['optimization']},
                    {'agent_id': 'agent_2', 'capabilities': ['analysis']}
                ]
            )
        
        # Verify decision uses ML algorithms
        assert isinstance(decision, IntelligenceDecision)
        assert decision.decision_type == DecisionType.TASK_ALLOCATION
        assert 0.1 <= decision.confidence <= 0.95
        assert 'action' in decision.recommendation
        
        # Verify ML components were utilized
        intelligence_framework.predictive_analytics.predict_performance.assert_called()
        intelligence_framework.pattern_optimizer.get_task_patterns.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])