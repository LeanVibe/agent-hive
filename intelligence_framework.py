"""
Intelligence Framework - Core Intelligence Layer for Agent Hive

This module provides the central intelligence coordination layer that unifies
all ML components, decision-making, and agent intelligence capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import sqlite3
from pathlib import Path
import numpy as np

from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import (
    CoordinatorConfig, AgentInfo, TaskAssignment, CoordinatorState
)
from ml_enhancements.adaptive_learning import AdaptiveLearning
from ml_enhancements.predictive_analytics import PredictiveAnalytics
from ml_enhancements.pattern_optimizer import PatternOptimizer
from ml_enhancements.models import MLConfig, LearningMetrics, AnalyticsResult


logger = logging.getLogger(__name__)


class IntelligenceLevel(Enum):
    """Intelligence capability levels for agents."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class DecisionType(Enum):
    """Types of decisions the intelligence framework makes."""
    TASK_ALLOCATION = "task_allocation"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    SCALING_DECISION = "scaling_decision"
    AGENT_COORDINATION = "agent_coordination"
    PERFORMANCE_TUNING = "performance_tuning"
    QUALITY_ASSESSMENT = "quality_assessment"


@dataclass
class IntelligenceConfig:
    """Configuration for the Intelligence Framework."""
    
    # Core intelligence settings
    intelligence_level: IntelligenceLevel = IntelligenceLevel.ADVANCED
    decision_confidence_threshold: float = 0.8
    learning_update_interval: int = 300  # 5 minutes
    analytics_update_interval: int = 600  # 10 minutes
    
    # ML component configurations
    ml_config: MLConfig = field(default_factory=MLConfig)
    coordinator_config: CoordinatorConfig = field(default_factory=CoordinatorConfig)
    
    # Database settings
    db_path: str = "intelligence_framework.db"
    enable_persistent_learning: bool = True
    
    # Performance settings
    max_concurrent_decisions: int = 10
    decision_timeout: float = 30.0
    
    # Quality thresholds
    min_task_success_rate: float = 0.9
    max_error_rate: float = 0.1
    target_response_time: float = 2.0


@dataclass
class IntelligenceDecision:
    """Represents an intelligence decision made by the framework."""
    
    decision_id: str
    decision_type: DecisionType
    confidence: float
    recommendation: Dict[str, Any]
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'decision_id': self.decision_id,
            'decision_type': self.decision_type.value,
            'confidence': self.confidence,
            'recommendation': self.recommendation,
            'reasoning': self.reasoning,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class AgentIntelligence:
    """Intelligence profile for an agent."""
    
    agent_id: str
    intelligence_level: IntelligenceLevel
    specializations: List[str]
    performance_score: float
    learning_progress: float
    decision_accuracy: float
    last_assessment: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'agent_id': self.agent_id,
            'intelligence_level': self.intelligence_level.value,
            'specializations': self.specializations,
            'performance_score': self.performance_score,
            'learning_progress': self.learning_progress,
            'decision_accuracy': self.decision_accuracy,
            'last_assessment': self.last_assessment.isoformat()
        }


class IntelligenceFramework:
    """
    Core Intelligence Framework for Agent Hive.
    
    This class coordinates all intelligence components and provides
    unified decision-making capabilities across the system.
    """
    
    def __init__(self, config: Optional[IntelligenceConfig] = None):
        """Initialize the Intelligence Framework."""
        self.config = config or IntelligenceConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.coordinator = MultiAgentCoordinator(self.config.coordinator_config)
        self.adaptive_learning = AdaptiveLearning(self.config.ml_config)
        self.predictive_analytics = PredictiveAnalytics(self.config.ml_config)
        self.pattern_optimizer = PatternOptimizer(self.config.ml_config)
        
        # Intelligence state
        self.agent_intelligence: Dict[str, AgentIntelligence] = {}
        self.decision_history: List[IntelligenceDecision] = []
        self.active_learning_sessions: Dict[str, str] = {}
        
        # Performance tracking
        self.performance_metrics = {
            'total_decisions': 0,
            'successful_decisions': 0,
            'decision_accuracy': 0.0,
            'avg_decision_time': 0.0,
            'learning_sessions': 0,
            'optimization_improvements': 0
        }
        
        # Initialize database
        self._init_database()
        
        # Background tasks
        self.running = False
        self.background_tasks = []
        
        self.logger.info(f"Intelligence Framework initialized with level: {self.config.intelligence_level}")
    
    def _init_database(self) -> None:
        """Initialize SQLite database for intelligence data."""
        with sqlite3.connect(self.config.db_path, 
                           detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            # Intelligence decisions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_decisions (
                    decision_id TEXT PRIMARY KEY,
                    decision_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    recommendation TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    success BOOLEAN,
                    execution_time REAL,
                    metadata TEXT
                )
            """)
            
            # Agent intelligence profiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_intelligence (
                    agent_id TEXT PRIMARY KEY,
                    intelligence_level TEXT NOT NULL,
                    specializations TEXT NOT NULL,
                    performance_score REAL NOT NULL,
                    learning_progress REAL NOT NULL,
                    decision_accuracy REAL NOT NULL,
                    last_assessment TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Learning sessions tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    improvement_score REAL,
                    lessons_learned TEXT,
                    metadata TEXT
                )
            """)
            
            # Performance history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_history (
                    history_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    context TEXT,
                    metadata TEXT
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp 
                ON intelligence_decisions(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_type 
                ON intelligence_decisions(decision_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_type_time 
                ON performance_history(metric_type, timestamp)
            """)
            
            conn.commit()
    
    async def start(self) -> None:
        """Start the Intelligence Framework."""
        self.running = True
        
        # Start coordinator
        await self.coordinator.start()
        
        # Start background intelligence tasks
        self.background_tasks = [
            asyncio.create_task(self._intelligence_monitor()),
            asyncio.create_task(self._learning_coordinator()),
            asyncio.create_task(self._performance_optimizer()),
            asyncio.create_task(self._decision_evaluator())
        ]
        
        self.logger.info("Intelligence Framework started")
    
    async def stop(self) -> None:
        """Stop the Intelligence Framework."""
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Stop coordinator
        await self.coordinator.stop()
        
        self.logger.info("Intelligence Framework stopped")
    
    async def make_decision(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        options: Optional[List[Dict[str, Any]]] = None
    ) -> IntelligenceDecision:
        """
        Make an intelligent decision based on context and available options.
        
        Args:
            decision_type: Type of decision to make
            context: Decision context and parameters
            options: Available options to choose from
            
        Returns:
            IntelligenceDecision: The decision with reasoning and confidence
        """
        decision_id = f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        try:
            # Analyze context using ML components
            analysis = await self._analyze_decision_context(decision_type, context)
            
            # Generate recommendation
            recommendation = await self._generate_recommendation(
                decision_type, context, options, analysis
            )
            
            # Calculate confidence
            confidence = await self._calculate_decision_confidence(
                decision_type, context, recommendation, analysis
            )
            
            # Generate reasoning
            reasoning = await self._generate_reasoning(
                decision_type, context, recommendation, analysis
            )
            
            # Create decision
            decision = IntelligenceDecision(
                decision_id=decision_id,
                decision_type=decision_type,
                confidence=confidence,
                recommendation=recommendation,
                reasoning=reasoning,
                metadata={
                    'context': context,
                    'options': options or [],
                    'analysis': analysis
                }
            )
            
            # Store decision
            await self._store_decision(decision)
            
            # Update metrics
            self.performance_metrics['total_decisions'] += 1
            
            self.logger.info(f"Decision made: {decision_type.value} with confidence {confidence:.3f}")
            return decision
            
        except Exception as e:
            self.logger.error(f"Decision making failed for {decision_type.value}: {e}")
            
            # Return fallback decision
            return IntelligenceDecision(
                decision_id=decision_id,
                decision_type=decision_type,
                confidence=0.5,
                recommendation={'action': 'fallback', 'reason': str(e)},
                reasoning=f"Decision making failed: {e}",
                metadata={'error': str(e)}
            )
    
    async def assess_agent_intelligence(self, agent_id: str) -> AgentIntelligence:
        """
        Assess and update an agent's intelligence profile.
        
        Args:
            agent_id: ID of the agent to assess
            
        Returns:
            AgentIntelligence: Updated intelligence profile
        """
        try:
            # Get agent info
            agent_info = await self.coordinator.get_agent_status(agent_id)
            if not agent_info:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Calculate performance metrics
            performance_score = await self._calculate_agent_performance(agent_id)
            learning_progress = await self._calculate_learning_progress(agent_id)
            decision_accuracy = await self._calculate_decision_accuracy(agent_id)
            
            # Determine intelligence level
            intelligence_level = self._determine_intelligence_level(
                performance_score, learning_progress, decision_accuracy
            )
            
            # Extract specializations
            specializations = self._extract_specializations(agent_info)
            
            # Create or update intelligence profile
            intelligence = AgentIntelligence(
                agent_id=agent_id,
                intelligence_level=intelligence_level,
                specializations=specializations,
                performance_score=performance_score,
                learning_progress=learning_progress,
                decision_accuracy=decision_accuracy
            )
            
            # Store in memory and database
            self.agent_intelligence[agent_id] = intelligence
            await self._store_agent_intelligence(intelligence)
            
            self.logger.info(f"Agent {agent_id} intelligence assessed: {intelligence_level.value}")
            return intelligence
            
        except Exception as e:
            self.logger.error(f"Intelligence assessment failed for agent {agent_id}: {e}")
            
            # Return default intelligence profile
            return AgentIntelligence(
                agent_id=agent_id,
                intelligence_level=IntelligenceLevel.BASIC,
                specializations=[],
                performance_score=0.5,
                learning_progress=0.0,
                decision_accuracy=0.5
            )
    
    async def optimize_system_performance(self) -> Dict[str, Any]:
        """
        Optimize overall system performance using intelligence insights.
        
        Returns:
            Dict[str, Any]: Optimization results and recommendations
        """
        try:
            # Get current system state
            coordinator_state = await self.coordinator.get_coordinator_state()
            
            # Analyze performance patterns
            patterns = await self.pattern_optimizer.analyze_patterns()
            
            # Generate predictions
            performance_prediction = await self.predictive_analytics.predict_performance(
                features=self._extract_system_features(coordinator_state)
            )
            
            # Generate optimization recommendations
            recommendations = []
            
            # Resource optimization
            if performance_prediction.predicted_value < 0.8:
                recommendations.append({
                    'type': 'resource_optimization',
                    'priority': 'high',
                    'action': 'Scale up resources based on predicted performance decline',
                    'confidence': performance_prediction.accuracy_score
                })
            
            # Agent rebalancing
            if coordinator_state.load_balancing_metrics.distribution_variance > 0.3:
                recommendations.append({
                    'type': 'load_balancing',
                    'priority': 'medium',
                    'action': 'Rebalance agent workloads to improve distribution',
                    'confidence': 0.85
                })
            
            # Learning optimization
            if len(self.active_learning_sessions) < len(coordinator_state.active_agents) * 0.5:
                recommendations.append({
                    'type': 'learning_optimization',
                    'priority': 'medium',
                    'action': 'Increase learning sessions for underperforming agents',
                    'confidence': 0.9
                })
            
            optimization_results = {
                'timestamp': datetime.now().isoformat(),
                'current_performance': performance_prediction.predicted_value,
                'performance_trend': self._calculate_performance_trend(),
                'recommendations': recommendations,
                'system_health': self._assess_system_health(coordinator_state),
                'optimization_priority': self._prioritize_optimizations(recommendations)
            }
            
            # Update metrics
            self.performance_metrics['optimization_improvements'] += len(recommendations)
            
            self.logger.info(f"System optimization completed with {len(recommendations)} recommendations")
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"System optimization failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'recommendations': []
            }
    
    async def _analyze_decision_context(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze decision context using ML components."""
        analysis = {
            'context_complexity': self._calculate_context_complexity(context),
            'historical_patterns': [],
            'predictive_insights': {},
            'resource_implications': {}
        }
        
        try:
            # Get historical patterns
            if decision_type == DecisionType.TASK_ALLOCATION:
                analysis['historical_patterns'] = await self.pattern_optimizer.get_task_patterns()
            
            # Get predictive insights
            if 'features' in context:
                prediction = await self.predictive_analytics.predict_performance(
                    features=context['features']
                )
                analysis['predictive_insights'] = prediction.to_dict()
            
            # Analyze resource implications
            if 'resource_requirements' in context:
                analysis['resource_implications'] = await self._analyze_resource_impact(
                    context['resource_requirements']
                )
            
        except Exception as e:
            self.logger.warning(f"Context analysis failed: {e}")
        
        return analysis
    
    async def _generate_recommendation(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        options: Optional[List[Dict[str, Any]]],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate recommendation based on decision type and analysis."""
        
        if decision_type == DecisionType.TASK_ALLOCATION:
            return await self._recommend_task_allocation(context, options, analysis)
        
        elif decision_type == DecisionType.RESOURCE_OPTIMIZATION:
            return await self._recommend_resource_optimization(context, analysis)
        
        elif decision_type == DecisionType.SCALING_DECISION:
            return await self._recommend_scaling_decision(context, analysis)
        
        elif decision_type == DecisionType.AGENT_COORDINATION:
            return await self._recommend_agent_coordination(context, options, analysis)
        
        elif decision_type == DecisionType.PERFORMANCE_TUNING:
            return await self._recommend_performance_tuning(context, analysis)
        
        elif decision_type == DecisionType.QUALITY_ASSESSMENT:
            return await self._recommend_quality_assessment(context, analysis)
        
        else:
            return {
                'action': 'default',
                'reason': f'No specific recommendation for {decision_type.value}',
                'confidence': 0.5
            }
    
    async def _recommend_task_allocation(
        self,
        context: Dict[str, Any],
        options: Optional[List[Dict[str, Any]]],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend task allocation strategy."""
        
        # Get available agents
        coordinator_state = await self.coordinator.get_coordinator_state()
        available_agents = [
            agent for agent in coordinator_state.active_agents.values()
            if agent.active_tasks < 5  # Threshold for availability
        ]
        
        if not available_agents:
            return {
                'action': 'queue_task',
                'reason': 'No available agents for task allocation',
                'agent_id': None
            }
        
        # Score agents based on intelligence and current load
        best_agent = None
        best_score = 0
        
        for agent in available_agents:
            intelligence = self.agent_intelligence.get(agent.agent_id)
            if intelligence:
                # Calculate score based on performance and availability
                load_factor = 1.0 - (agent.active_tasks / 5.0)
                performance_factor = intelligence.performance_score
                
                score = (load_factor * 0.6) + (performance_factor * 0.4)
                
                if score > best_score:
                    best_score = score
                    best_agent = agent
        
        if best_agent:
            return {
                'action': 'assign_task',
                'agent_id': best_agent.agent_id,
                'reason': f'Selected agent with best performance/availability score: {best_score:.3f}',
                'allocation_strategy': 'intelligent_selection'
            }
        
        # Fallback to least loaded agent
        least_loaded = min(available_agents, key=lambda a: a.active_tasks)
        return {
            'action': 'assign_task',
            'agent_id': least_loaded.agent_id,
            'reason': 'Fallback to least loaded agent',
            'allocation_strategy': 'least_loaded'
        }
    
    async def _recommend_resource_optimization(
        self,
        context: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend resource optimization actions."""
        
        # Get current resource usage
        coordinator_state = await self.coordinator.get_coordinator_state()
        resource_usage = coordinator_state.resource_usage
        
        recommendations = []
        
        # CPU optimization
        if resource_usage.cpu_percent > 0.8:
            recommendations.append({
                'resource': 'cpu',
                'action': 'scale_up',
                'priority': 'high',
                'current_usage': resource_usage.cpu_percent
            })
        
        # Memory optimization
        if resource_usage.memory_percent > 0.85:
            recommendations.append({
                'resource': 'memory',
                'action': 'scale_up',
                'priority': 'high',
                'current_usage': resource_usage.memory_percent
            })
        
        # Network optimization
        if resource_usage.network_percent > 0.9:
            recommendations.append({
                'resource': 'network',
                'action': 'optimize_traffic',
                'priority': 'medium',
                'current_usage': resource_usage.network_percent
            })
        
        return {
            'action': 'optimize_resources',
            'recommendations': recommendations,
            'priority': 'high' if any(r['priority'] == 'high' for r in recommendations) else 'medium'
        }
    
    async def _recommend_scaling_decision(
        self,
        context: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend scaling decisions."""
        
        coordinator_state = await self.coordinator.get_coordinator_state()
        current_agents = len(coordinator_state.active_agents)
        queue_depth = len(coordinator_state.pending_tasks)
        
        # Scale up conditions
        if queue_depth > 10 and current_agents < self.config.coordinator_config.max_agents:
            return {
                'action': 'scale_up',
                'target_agents': min(current_agents + 2, self.config.coordinator_config.max_agents),
                'reason': f'High queue depth ({queue_depth}) requires more agents',
                'priority': 'high'
            }
        
        # Scale down conditions
        if queue_depth == 0 and current_agents > self.config.coordinator_config.min_agents:
            avg_utilization = sum(
                agent.active_tasks for agent in coordinator_state.active_agents.values()
            ) / len(coordinator_state.active_agents)
            
            if avg_utilization < 1.0:
                return {
                    'action': 'scale_down',
                    'target_agents': max(current_agents - 1, self.config.coordinator_config.min_agents),
                    'reason': f'Low utilization ({avg_utilization:.1f}) allows scaling down',
                    'priority': 'low'
                }
        
        return {
            'action': 'maintain',
            'reason': 'Current agent count is optimal',
            'priority': 'low'
        }
    
    async def _recommend_agent_coordination(
        self,
        context: Dict[str, Any],
        options: Optional[List[Dict[str, Any]]],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend agent coordination strategies."""
        
        return {
            'action': 'coordinate_agents',
            'strategy': 'intelligent_collaboration',
            'coordination_type': 'dynamic',
            'reason': 'Enable intelligent agent collaboration based on capabilities'
        }
    
    async def _recommend_performance_tuning(
        self,
        context: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend performance tuning actions."""
        
        return {
            'action': 'tune_performance',
            'optimizations': [
                'adaptive_learning_rate',
                'resource_allocation',
                'task_scheduling'
            ],
            'reason': 'Optimize system performance based on current patterns'
        }
    
    async def _recommend_quality_assessment(
        self,
        context: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend quality assessment actions."""
        
        return {
            'action': 'assess_quality',
            'assessment_type': 'comprehensive',
            'focus_areas': ['performance', 'reliability', 'efficiency'],
            'reason': 'Continuous quality monitoring and improvement'
        }
    
    async def _calculate_decision_confidence(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        recommendation: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> float:
        """Calculate ML-based confidence in a decision using multiple algorithms."""
        
        try:
            # Multi-factor confidence calculation using ML insights
            confidence_factors = []
            
            # 1. Historical pattern similarity confidence
            patterns = analysis.get('historical_patterns', [])
            if patterns:
                pattern_confidence = await self._calculate_pattern_similarity_confidence(
                    decision_type, context, patterns
                )
                confidence_factors.append(('pattern_similarity', pattern_confidence, 0.25))
            
            # 2. Predictive model confidence
            insights = analysis.get('predictive_insights', {})
            if insights:
                model_confidence = self._calculate_model_prediction_confidence(insights)
                confidence_factors.append(('model_prediction', model_confidence, 0.3))
            
            # 3. Context completeness confidence
            context_confidence = self._calculate_context_completeness_confidence(context, decision_type)
            confidence_factors.append(('context_completeness', context_confidence, 0.2))
            
            # 4. Historical decision accuracy confidence
            historical_confidence = await self._calculate_historical_decision_confidence(decision_type)
            confidence_factors.append(('historical_accuracy', historical_confidence, 0.15))
            
            # 5. Resource availability confidence
            resource_confidence = await self._calculate_resource_availability_confidence(context)
            confidence_factors.append(('resource_availability', resource_confidence, 0.1))
            
            # Weighted confidence calculation
            if confidence_factors:
                weighted_confidence = sum(
                    factor_value * weight 
                    for _, factor_value, weight in confidence_factors
                )
                total_weight = sum(weight for _, _, weight in confidence_factors)
                final_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5
            else:
                # Fallback to complexity-based confidence
                complexity = analysis.get('context_complexity', 0.5)
                final_confidence = 0.7 * (1.0 - complexity * 0.3)
            
            # Apply confidence bounds and return
            return max(0.1, min(0.95, final_confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculating decision confidence: {e}")
            return 0.5  # Safe fallback confidence
    
    async def _generate_reasoning(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        recommendation: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> str:
        """Generate reasoning for a decision."""
        
        reasoning_parts = []
        
        # Base reasoning
        reasoning_parts.append(f"Decision type: {decision_type.value}")
        reasoning_parts.append(f"Recommended action: {recommendation.get('action', 'unknown')}")
        
        # Context-based reasoning
        if 'reason' in recommendation:
            reasoning_parts.append(f"Rationale: {recommendation['reason']}")
        
        # Analysis-based reasoning
        if analysis.get('predictive_insights'):
            reasoning_parts.append("Incorporates predictive analytics insights")
        
        if analysis.get('historical_patterns'):
            reasoning_parts.append("Based on historical pattern analysis")
        
        return "; ".join(reasoning_parts)
    
    async def _store_decision(self, decision: IntelligenceDecision) -> None:
        """Store decision in database."""
        
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute("""
                INSERT INTO intelligence_decisions 
                (decision_id, decision_type, confidence, recommendation, reasoning, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.decision_id,
                decision.decision_type.value,
                decision.confidence,
                json.dumps(decision.recommendation),
                decision.reasoning,
                decision.timestamp,
                json.dumps(decision.metadata)
            ))
            conn.commit()
    
    async def _store_agent_intelligence(self, intelligence: AgentIntelligence) -> None:
        """Store agent intelligence in database."""
        
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_intelligence 
                (agent_id, intelligence_level, specializations, performance_score, 
                 learning_progress, decision_accuracy, last_assessment, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                intelligence.agent_id,
                intelligence.intelligence_level.value,
                json.dumps(intelligence.specializations),
                intelligence.performance_score,
                intelligence.learning_progress,
                intelligence.decision_accuracy,
                intelligence.last_assessment,
                json.dumps({})
            ))
            conn.commit()
    
    async def _intelligence_monitor(self) -> None:
        """Background task for intelligence monitoring."""
        while self.running:
            try:
                await asyncio.sleep(self.config.learning_update_interval)
                
                # Update agent intelligence profiles
                coordinator_state = await self.coordinator.get_coordinator_state()
                for agent_id in coordinator_state.active_agents.keys():
                    await self.assess_agent_intelligence(agent_id)
                
            except Exception as e:
                self.logger.error(f"Intelligence monitoring error: {e}")
    
    async def _learning_coordinator(self) -> None:
        """Enhanced background task for coordinating adaptive learning sessions."""
        while self.running:
            try:
                await asyncio.sleep(self.config.learning_update_interval)
                
                # 1. Start learning sessions for underperforming agents
                await self._manage_adaptive_learning_sessions()
                
                # 2. Process feedback from recent decisions
                await self._process_decision_feedback()
                
                # 3. Update learning patterns based on system performance
                await self._update_learning_patterns()
                
                # 4. Optimize learning parameters based on results
                await self._optimize_learning_parameters()
                
            except Exception as e:
                self.logger.error(f"Learning coordination error: {e}")
    
    async def _manage_adaptive_learning_sessions(self) -> None:
        """Manage adaptive learning sessions for agents."""
        try:
            for agent_id, intelligence in self.agent_intelligence.items():
                # Start new sessions for underperforming agents
                if (intelligence.performance_score < 0.7 and 
                    agent_id not in self.active_learning_sessions):
                    
                    # Determine optimal learning strategy based on agent characteristics
                    learning_strategy = self._determine_learning_strategy(intelligence)
                    
                    session_context = {
                        'agent_id': agent_id,
                        'target_improvement': 0.8,
                        'current_performance': intelligence.performance_score,
                        'learning_strategy': learning_strategy,
                        'specializations': intelligence.specializations,
                        'decision_accuracy': intelligence.decision_accuracy
                    }
                    
                    session_id = self.adaptive_learning.start_learning_session(
                        learning_strategy, session_context
                    )
                    self.active_learning_sessions[agent_id] = session_id
                    
                    self.logger.info(f"Started {learning_strategy} learning session for agent {agent_id}")
                
                # Monitor and update existing sessions
                elif agent_id in self.active_learning_sessions:
                    session_id = self.active_learning_sessions[agent_id]
                    await self._monitor_learning_session(agent_id, session_id, intelligence)
                
            # Clean up completed sessions
            await self._cleanup_completed_sessions()
            
        except Exception as e:
            self.logger.error(f"Error managing learning sessions: {e}")
    
    def _determine_learning_strategy(self, intelligence: AgentIntelligence) -> str:
        """Determine optimal learning strategy based on agent intelligence profile."""
        
        # Analyze agent characteristics to choose best learning approach
        if intelligence.performance_score < 0.4:
            # Very low performance - use basic optimization
            return 'performance_optimizer'
        elif intelligence.decision_accuracy < 0.6:
            # Poor decision making - focus on decision improvement
            return 'decision_optimizer'
        elif len(intelligence.specializations) == 0:
            # No specializations - general capability building
            return 'capability_builder'
        elif intelligence.learning_progress < 0.3:
            # Slow learning - adaptive rate adjustment
            return 'adaptive_rate_optimizer'
        else:
            # Good baseline - advanced optimization
            return 'advanced_optimizer'
    
    async def _monitor_learning_session(
        self, 
        agent_id: str, 
        session_id: str, 
        intelligence: AgentIntelligence
    ) -> None:
        """Monitor ongoing learning session and provide adaptive feedback."""
        try:
            # Get session progress
            session_progress = await self._get_active_session_progress(session_id)
            
            # Provide contextual feedback based on agent performance
            if session_progress > 0.8:
                # High progress - provide positive reinforcement
                self.adaptive_learning.provide_feedback(
                    session_id, 'positive', 0.9,
                    {
                        'agent_id': agent_id,
                        'progress_type': 'excellent',
                        'performance_improvement': session_progress - 0.5
                    }
                )
            elif session_progress < 0.3:
                # Low progress - provide corrective feedback
                corrective_context = await self._generate_corrective_feedback(agent_id, intelligence)
                self.adaptive_learning.provide_feedback(
                    session_id, 'negative', 0.7,
                    corrective_context
                )
            
            # Provide performance-based feedback
            current_performance = intelligence.performance_score
            performance_context = {
                'agent_id': agent_id,
                'current_performance': current_performance,
                'target_performance': 0.8,
                'specializations': intelligence.specializations,
                'decision_accuracy': intelligence.decision_accuracy
            }
            
            self.adaptive_learning.provide_feedback(
                session_id, 'performance', current_performance,
                performance_context, source_agent=agent_id
            )
            
        except Exception as e:
            self.logger.error(f"Error monitoring learning session for {agent_id}: {e}")
    
    async def _generate_corrective_feedback(
        self, 
        agent_id: str, 
        intelligence: AgentIntelligence
    ) -> Dict[str, Any]:
        """Generate corrective feedback based on agent performance issues."""
        
        corrective_context = {
            'agent_id': agent_id,
            'feedback_type': 'corrective',
            'performance_score': intelligence.performance_score,
            'areas_for_improvement': []
        }
        
        # Identify specific areas needing improvement
        if intelligence.decision_accuracy < 0.6:
            corrective_context['areas_for_improvement'].append('decision_making')
        
        if intelligence.performance_score < 0.5:
            corrective_context['areas_for_improvement'].append('task_execution')
        
        if intelligence.learning_progress < 0.3:
            corrective_context['areas_for_improvement'].append('learning_adaptation')
        
        # Add specific recommendations
        corrective_context['recommendations'] = await self._get_improvement_recommendations(intelligence)
        
        return corrective_context
    
    async def _get_improvement_recommendations(self, intelligence: AgentIntelligence) -> List[str]:
        """Get specific improvement recommendations for an agent."""
        recommendations = []
        
        if intelligence.decision_accuracy < 0.6:
            recommendations.append("Focus on decision pattern analysis and context evaluation")
        
        if intelligence.performance_score < 0.5:
            recommendations.append("Optimize task execution efficiency and error handling")
        
        if len(intelligence.specializations) < 2:
            recommendations.append("Develop additional specialization areas")
        
        if intelligence.learning_progress < 0.5:
            recommendations.append("Increase feedback processing and adaptation speed")
        
        return recommendations
    
    async def _cleanup_completed_sessions(self) -> None:
        """Clean up completed learning sessions."""
        try:
            completed_sessions = []
            
            for agent_id, session_id in self.active_learning_sessions.items():
                # Check if session has converged or completed
                convergence_info = self.adaptive_learning.convergence_tracking.get(session_id)
                if convergence_info and convergence_info.get('converged', False):
                    completed_sessions.append(agent_id)
                    
                    # End the session and get summary
                    session_summary = self.adaptive_learning.end_learning_session(session_id)
                    
                    self.logger.info(f"Completed learning session for agent {agent_id}: {session_summary}")
            
            # Remove completed sessions
            for agent_id in completed_sessions:
                del self.active_learning_sessions[agent_id]
                
        except Exception as e:
            self.logger.error(f"Error cleaning up learning sessions: {e}")
    
    async def _process_decision_feedback(self) -> None:
        """Process feedback from recent decisions to improve learning."""
        try:
            # Get recent decisions for feedback analysis
            cutoff_time = datetime.now() - timedelta(hours=2)
            
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT decision_id, decision_type, confidence, success, 
                           recommendation, metadata, timestamp
                    FROM intelligence_decisions 
                    WHERE timestamp > ? AND success IS NOT NULL
                    ORDER BY timestamp DESC LIMIT 50
                """, (cutoff_time,))
                
                recent_decisions = cursor.fetchall()
            
            if not recent_decisions:
                return
            
            # Process decisions and generate learning feedback
            for decision_data in recent_decisions:
                await self._process_single_decision_feedback(decision_data)
                
        except Exception as e:
            self.logger.error(f"Error processing decision feedback: {e}")
    
    async def _process_single_decision_feedback(self, decision_data: Tuple) -> None:
        """Process feedback from a single decision."""
        try:
            (decision_id, decision_type, confidence, success, 
             recommendation_json, metadata_json, timestamp) = decision_data
            
            recommendation = json.loads(recommendation_json)
            metadata = json.loads(metadata_json or '{}')
            
            # Extract context for learning
            feedback_context = {
                'decision_id': decision_id,
                'decision_type': decision_type,
                'confidence': confidence,
                'success': success,
                'recommendation': recommendation,
                'timestamp': timestamp
            }
            
            # Determine feedback type and value
            if success:
                feedback_type = 'positive'
                feedback_value = confidence * 1.0  # Successful decisions reinforce confidence
            else:
                feedback_type = 'negative'
                feedback_value = (1.0 - confidence) * 0.7  # Failed decisions reduce confidence
            
            # Provide feedback to relevant learning sessions
            for agent_id, session_id in self.active_learning_sessions.items():
                if agent_id in metadata_json:
                    self.adaptive_learning.provide_feedback(
                        session_id, feedback_type, feedback_value,
                        feedback_context, source_agent=agent_id
                    )
                    
        except Exception as e:
            self.logger.error(f"Error processing single decision feedback: {e}")
    
    async def _update_learning_patterns(self) -> None:
        """Update learning patterns based on system performance."""
        try:
            # Get current system performance metrics
            overall_performance = await self._calculate_system_performance()
            
            # Update pattern optimizer with recent performance data
            if overall_performance < 0.7:
                # System underperforming - increase learning frequency
                self.config.learning_update_interval = max(60, self.config.learning_update_interval * 0.8)
                self.logger.info("Increased learning frequency due to low system performance")
            elif overall_performance > 0.9:
                # System performing well - can reduce learning frequency
                self.config.learning_update_interval = min(600, self.config.learning_update_interval * 1.2)
                self.logger.info("Reduced learning frequency due to high system performance")
            
            # Record performance patterns for future optimization
            performance_features = {
                'overall_performance': overall_performance,
                'active_agents': len(self.agent_intelligence),
                'learning_sessions': len(self.active_learning_sessions),
                'avg_agent_performance': sum(ai.performance_score for ai in self.agent_intelligence.values()) / max(1, len(self.agent_intelligence))
            }
            
            # Record in pattern optimizer for future analysis
            self.pattern_optimizer.record_workflow_execution(
                f"system_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'system_optimization',
                performance_features,
                {'overall_performance': overall_performance},
                0.0,  # No specific execution time
                overall_performance > 0.8,  # Success if performance > 80%
                'intelligence_framework'
            )
            
        except Exception as e:
            self.logger.error(f"Error updating learning patterns: {e}")
    
    async def _calculate_system_performance(self) -> float:
        """Calculate overall system performance score."""
        try:
            if not self.agent_intelligence:
                return 0.5
            
            # Calculate weighted system performance
            performance_factors = []
            
            # Agent performance average
            avg_agent_performance = sum(ai.performance_score for ai in self.agent_intelligence.values()) / len(self.agent_intelligence)
            performance_factors.append(('agent_performance', avg_agent_performance, 0.4))
            
            # Decision accuracy average
            avg_decision_accuracy = sum(ai.decision_accuracy for ai in self.agent_intelligence.values()) / len(self.agent_intelligence)
            performance_factors.append(('decision_accuracy', avg_decision_accuracy, 0.3))
            
            # Learning progress average
            avg_learning_progress = sum(ai.learning_progress for ai in self.agent_intelligence.values()) / len(self.agent_intelligence)
            performance_factors.append(('learning_progress', avg_learning_progress, 0.2))
            
            # System health from recent decisions
            recent_success_rate = await self._get_recent_decision_success_rate()
            performance_factors.append(('recent_success', recent_success_rate, 0.1))
            
            # Calculate weighted average
            weighted_performance = sum(score * weight for _, score, weight in performance_factors)
            total_weight = sum(weight for _, _, weight in performance_factors)
            
            return weighted_performance / total_weight if total_weight > 0 else 0.5
            
        except Exception as e:
            self.logger.error(f"Error calculating system performance: {e}")
            return 0.5
    
    async def _get_recent_decision_success_rate(self) -> float:
        """Get success rate of recent decisions."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=6)
            
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) as total, 
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                    FROM intelligence_decisions 
                    WHERE timestamp > ? AND success IS NOT NULL
                """, (cutoff_time,))
                
                result = cursor.fetchone()
                total, successful = result if result else (0, 0)
            
            return successful / max(1, total)
            
        except Exception as e:
            self.logger.error(f"Error getting recent decision success rate: {e}")
            return 0.7
    
    async def _optimize_learning_parameters(self) -> None:
        """Optimize learning parameters based on performance analysis."""
        try:
            # Get learning insights from adaptive learning component
            learning_insights = self.adaptive_learning.get_learning_insights()
            
            session_stats = learning_insights.get('session_statistics', {})
            avg_improvement_rate = session_stats.get('avg_improvement_rate', 0)
            avg_convergence_time = session_stats.get('avg_convergence_time', 300)
            
            # Optimize learning rate based on improvement patterns
            if avg_improvement_rate < 0.1:
                # Slow improvement - increase learning rate
                new_learning_rate = min(0.05, self.adaptive_learning.config.learning_rate * 1.2)
                self.adaptive_learning.config.learning_rate = new_learning_rate
                self.logger.info(f"Increased learning rate to {new_learning_rate}")
                
            elif avg_improvement_rate > 0.5:
                # Fast improvement - can reduce learning rate for stability
                new_learning_rate = max(0.001, self.adaptive_learning.config.learning_rate * 0.9)
                self.adaptive_learning.config.learning_rate = new_learning_rate
                self.logger.info(f"Reduced learning rate to {new_learning_rate}")
            
            # Optimize update frequency based on convergence time
            if avg_convergence_time > 600:  # 10 minutes
                # Slow convergence - increase update frequency
                new_frequency = max(50, self.adaptive_learning.config.update_frequency * 0.8)
                self.adaptive_learning.config.update_frequency = int(new_frequency)
                self.logger.info(f"Increased update frequency to {new_frequency}")
                
        except Exception as e:
            self.logger.error(f"Error optimizing learning parameters: {e}")
    
    async def _performance_optimizer(self) -> None:
        """Background task for performance optimization."""
        while self.running:
            try:
                await asyncio.sleep(self.config.analytics_update_interval)
                
                # Optimize system performance
                await self.optimize_system_performance()
                
            except Exception as e:
                self.logger.error(f"Performance optimization error: {e}")
    
    async def _decision_evaluator(self) -> None:
        """Background task for evaluating decision outcomes."""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                # Evaluate recent decisions
                await self._evaluate_recent_decisions()
                
            except Exception as e:
                self.logger.error(f"Decision evaluation error: {e}")
    
    async def _evaluate_recent_decisions(self) -> None:
        """Evaluate outcomes of recent decisions."""
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        # Get recent decisions from database
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute("""
                SELECT decision_id, decision_type, confidence, recommendation, success 
                FROM intelligence_decisions 
                WHERE timestamp > ? AND success IS NOT NULL
            """, (cutoff_time,))
            
            decisions = cursor.fetchall()
        
        if decisions:
            successful_decisions = sum(1 for d in decisions if d[4])
            accuracy = successful_decisions / len(decisions)
            
            # Update performance metrics
            self.performance_metrics['decision_accuracy'] = accuracy
            self.performance_metrics['successful_decisions'] = successful_decisions
            
            self.logger.info(f"Decision accuracy: {accuracy:.3f} ({successful_decisions}/{len(decisions)})")
    
    def _calculate_context_complexity(self, context: Dict[str, Any]) -> float:
        """Calculate complexity of decision context."""
        complexity = 0.0
        
        # Base complexity from number of context keys
        complexity += len(context) * 0.1
        
        # Complexity from nested structures
        for value in context.values():
            if isinstance(value, dict):
                complexity += 0.2
            elif isinstance(value, list):
                complexity += 0.1
        
        return min(1.0, complexity)
    
    async def _calculate_agent_performance(self, agent_id: str) -> float:
        """Calculate agent performance score using ML-based multi-factor analysis."""
        try:
            # Get agent info
            agent_info = await self.coordinator.get_agent_status(agent_id)
            if not agent_info:
                return 0.5
            
            # Multi-factor performance calculation
            performance_factors = []
            
            # 1. Task completion effectiveness
            total_tasks = agent_info.active_tasks + agent_info.error_count
            if total_tasks > 0:
                completion_rate = 1.0 - (agent_info.error_count / total_tasks)
                performance_factors.append(('completion_rate', completion_rate, 0.3))
            
            # 2. Resource efficiency score
            if agent_info.current_usage:
                cpu_efficiency = self._calculate_resource_efficiency(
                    agent_info.current_usage.cpu_percent, optimal_range=(0.4, 0.8)
                )
                memory_efficiency = self._calculate_resource_efficiency(
                    agent_info.current_usage.memory_percent, optimal_range=(0.3, 0.7)
                )
                resource_efficiency = (cpu_efficiency + memory_efficiency) / 2.0
                performance_factors.append(('resource_efficiency', resource_efficiency, 0.25))
            
            # 3. Response time performance
            if hasattr(agent_info, 'avg_response_time') and agent_info.avg_response_time:
                # Lower response time is better
                response_performance = max(0.1, min(1.0, 5.0 / max(0.1, agent_info.avg_response_time)))
                performance_factors.append(('response_time', response_performance, 0.2))
            
            # 4. Historical performance trend
            historical_performance = await self._get_agent_historical_performance(agent_id)
            if historical_performance is not None:
                performance_factors.append(('historical_trend', historical_performance, 0.15))
            
            # 5. Workload balance score
            if hasattr(agent_info, 'max_concurrent_tasks'):
                workload_balance = 1.0 - (agent_info.active_tasks / max(1, agent_info.max_concurrent_tasks))
                performance_factors.append(('workload_balance', workload_balance, 0.1))
            
            # Calculate weighted performance score
            if performance_factors:
                weighted_score = sum(score * weight for _, score, weight in performance_factors)
                total_weight = sum(weight for _, _, weight in performance_factors)
                final_performance = weighted_score / total_weight if total_weight > 0 else 0.5
            else:
                # Fallback calculation
                error_rate = agent_info.error_count / max(1, total_tasks)
                final_performance = 1.0 - error_rate
            
            # Apply performance bounds
            return max(0.1, min(1.0, final_performance))
            
        except Exception as e:
            self.logger.error(f"Error calculating agent performance for {agent_id}: {e}")
            return 0.5
    
    def _calculate_resource_efficiency(self, usage: float, optimal_range: Tuple[float, float]) -> float:
        """Calculate resource efficiency score based on optimal usage range."""
        optimal_min, optimal_max = optimal_range
        
        if optimal_min <= usage <= optimal_max:
            # Within optimal range - high efficiency
            return 1.0
        elif usage < optimal_min:
            # Under-utilization - efficiency decreases
            return max(0.1, usage / optimal_min)
        else:
            # Over-utilization - efficiency decreases
            return max(0.1, (1.0 - usage) / (1.0 - optimal_max))
    
    async def _get_agent_historical_performance(self, agent_id: str) -> Optional[float]:
        """Get agent's historical performance trend using ML analysis."""
        try:
            # Get recent performance data from database
            cutoff_time = datetime.now() - timedelta(days=7)
            
            # This would typically query agent-specific performance history
            # For now, we'll use decision history where this agent was involved
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, confidence, success 
                    FROM intelligence_decisions 
                    WHERE timestamp > ? AND success IS NOT NULL
                    AND metadata LIKE ?
                    ORDER BY timestamp ASC
                """, (cutoff_time, f'%{agent_id}%'))
                
                performance_data = cursor.fetchall()
            
            if len(performance_data) < 2:
                return None
            
            # Calculate performance trend
            scores = []
            for _, confidence, success in performance_data:
                performance_score = confidence * (1.0 if success else 0.2)
                scores.append(performance_score)
            
            # Calculate trend using moving average and slope
            if len(scores) >= 3:
                # Recent average vs early average
                mid_point = len(scores) // 2
                early_avg = sum(scores[:mid_point]) / mid_point
                recent_avg = sum(scores[mid_point:]) / (len(scores) - mid_point)
                
                # Performance trend factor
                trend_factor = recent_avg / max(0.1, early_avg)
                return max(0.1, min(1.0, trend_factor))
            
            return sum(scores) / len(scores)
            
        except Exception as e:
            self.logger.error(f"Error getting historical performance for {agent_id}: {e}")
            return None
    
    async def _calculate_learning_progress(self, agent_id: str) -> float:
        """Calculate agent learning progress using ML-based adaptive learning metrics."""
        try:
            learning_factors = []
            
            # 1. Active learning session progress
            if agent_id in self.active_learning_sessions:
                session_id = self.active_learning_sessions[agent_id]
                session_progress = await self._get_active_session_progress(session_id)
                learning_factors.append(('active_session', session_progress, 0.4))
            
            # 2. Historical learning improvement rates
            historical_improvement = await self._get_historical_learning_improvement(agent_id)
            if historical_improvement is not None:
                learning_factors.append(('historical_improvement', historical_improvement, 0.3))
            
            # 3. Adaptation speed (how quickly agent improves)
            adaptation_speed = await self._calculate_adaptation_speed(agent_id)
            if adaptation_speed is not None:
                learning_factors.append(('adaptation_speed', adaptation_speed, 0.2))
            
            # 4. Knowledge retention (performance consistency)
            knowledge_retention = await self._calculate_knowledge_retention(agent_id)
            if knowledge_retention is not None:
                learning_factors.append(('knowledge_retention', knowledge_retention, 0.1))
            
            # Calculate weighted learning progress
            if learning_factors:
                weighted_progress = sum(score * weight for _, score, weight in learning_factors)
                total_weight = sum(weight for _, _, weight in learning_factors)
                final_progress = weighted_progress / total_weight if total_weight > 0 else 0.5
            else:
                # Fallback to basic calculation
                final_progress = 0.8 if agent_id in self.active_learning_sessions else 0.5
            
            return max(0.0, min(1.0, final_progress))
            
        except Exception as e:
            self.logger.error(f"Error calculating learning progress for {agent_id}: {e}")
            return 0.5
    
    async def _get_active_session_progress(self, session_id: str) -> float:
        """Get progress of active learning session."""
        try:
            # Get session performance history
            performance_history = self.model_performance.get(session_id, [])
            
            if len(performance_history) < 2:
                return 0.7  # Early in session
            
            # Calculate improvement rate
            initial_performance = performance_history[0]
            current_performance = performance_history[-1]
            
            if initial_performance > 0:
                improvement_rate = (current_performance - initial_performance) / initial_performance
                # Normalize improvement to 0-1 scale
                progress = max(0.1, min(1.0, 0.5 + improvement_rate))
                return progress
            
            return 0.7
            
        except Exception as e:
            self.logger.error(f"Error getting active session progress: {e}")
            return 0.7
    
    async def _get_historical_learning_improvement(self, agent_id: str) -> Optional[float]:
        """Get historical learning improvement rates for agent."""
        try:
            # Query adaptive learning database for this agent's sessions
            adaptive_learning_db = self.adaptive_learning.db_path
            
            with sqlite3.connect(adaptive_learning_db) as conn:
                cursor = conn.execute("""
                    SELECT improvement_rate FROM learning_sessions 
                    WHERE metadata LIKE ? AND end_time IS NOT NULL 
                    AND improvement_rate IS NOT NULL
                    ORDER BY end_time DESC LIMIT 10
                """, (f'%{agent_id}%',))
                
                improvement_rates = [row[0] for row in cursor.fetchall()]
            
            if improvement_rates:
                # Calculate weighted average (recent sessions weighted more heavily)
                weights = [1.0 / (i + 1) for i in range(len(improvement_rates))]
                weighted_avg = sum(rate * weight for rate, weight in zip(improvement_rates, weights))
                total_weight = sum(weights)
                
                if total_weight > 0:
                    normalized_improvement = weighted_avg / total_weight
                    return max(0.0, min(1.0, normalized_improvement + 0.5))  # Shift to 0.5-1.5 range then clamp
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting historical learning improvement: {e}")
            return None
    
    async def _calculate_adaptation_speed(self, agent_id: str) -> Optional[float]:
        """Calculate how quickly agent adapts to new patterns."""
        try:
            # Get recent decision accuracy improvements
            cutoff_time = datetime.now() - timedelta(days=14)
            
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, confidence, success 
                    FROM intelligence_decisions 
                    WHERE timestamp > ? AND metadata LIKE ?
                    AND success IS NOT NULL
                    ORDER BY timestamp ASC
                """, (cutoff_time, f'%{agent_id}%'))
                
                decisions = cursor.fetchall()
            
            if len(decisions) < 5:
                return None
            
            # Calculate success rate improvement over time
            # Split into early and recent periods
            mid_point = len(decisions) // 2
            early_decisions = decisions[:mid_point]
            recent_decisions = decisions[mid_point:]
            
            early_success_rate = sum(1 for _, _, success in early_decisions if success) / len(early_decisions)
            recent_success_rate = sum(1 for _, _, success in recent_decisions if success) / len(recent_decisions)
            
            # Adaptation speed based on improvement rate
            if early_success_rate > 0:
                adaptation_speed = recent_success_rate / early_success_rate
                return max(0.1, min(1.0, adaptation_speed))
            
            return recent_success_rate
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptation speed: {e}")
            return None
    
    async def _calculate_knowledge_retention(self, agent_id: str) -> Optional[float]:
        """Calculate consistency of agent performance over time."""
        try:
            # Get performance data over longer period
            cutoff_time = datetime.now() - timedelta(days=30)
            
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT confidence, success 
                    FROM intelligence_decisions 
                    WHERE timestamp > ? AND metadata LIKE ?
                    AND success IS NOT NULL
                """, (cutoff_time, f'%{agent_id}%'))
                
                decisions = cursor.fetchall()
            
            if len(decisions) < 5:
                return None
            
            # Calculate performance scores
            performance_scores = [
                confidence * (1.0 if success else 0.3) 
                for confidence, success in decisions
            ]
            
            # Knowledge retention is inverse of variance (more consistent = better retention)
            if len(performance_scores) > 1:
                mean_performance = sum(performance_scores) / len(performance_scores)
                variance = sum((score - mean_performance) ** 2 for score in performance_scores) / len(performance_scores)
                
                # Convert variance to retention score (lower variance = higher retention)
                retention_score = max(0.1, 1.0 - variance)
                return min(1.0, retention_score)
            
            return performance_scores[0] if performance_scores else None
            
        except Exception as e:
            self.logger.error(f"Error calculating knowledge retention: {e}")
            return None
    
    async def _calculate_decision_accuracy(self, agent_id: str) -> float:
        """Calculate agent decision accuracy using ML-based analysis."""
        try:
            # Get recent decisions involving this agent
            cutoff_time = datetime.now() - timedelta(days=14)
            
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT decision_type, confidence, success, execution_time
                    FROM intelligence_decisions 
                    WHERE timestamp > ? AND metadata LIKE ?
                    AND success IS NOT NULL
                    ORDER BY timestamp DESC
                """, (cutoff_time, f'%{agent_id}%'))
                
                decisions = cursor.fetchall()
            
            if not decisions:
                return 0.7  # Default accuracy when no history
            
            # Calculate multi-factor accuracy
            accuracy_factors = []
            
            # 1. Success rate accuracy
            successful_decisions = [d for d in decisions if d[2]]  # d[2] is success
            success_rate = len(successful_decisions) / len(decisions)
            accuracy_factors.append(('success_rate', success_rate, 0.4))
            
            # 2. Confidence calibration (how well confidence predicts success)
            if len(decisions) > 5:
                confidence_accuracy = self._calculate_confidence_calibration(decisions)
                accuracy_factors.append(('confidence_calibration', confidence_accuracy, 0.3))
            
            # 3. Decision type consistency
            decision_consistency = self._calculate_decision_type_consistency(decisions)
            accuracy_factors.append(('decision_consistency', decision_consistency, 0.2))
            
            # 4. Execution efficiency (successful decisions with reasonable execution time)
            execution_efficiency = self._calculate_execution_efficiency(decisions)
            accuracy_factors.append(('execution_efficiency', execution_efficiency, 0.1))
            
            # Calculate weighted accuracy
            weighted_accuracy = sum(score * weight for _, score, weight in accuracy_factors)
            total_weight = sum(weight for _, _, weight in accuracy_factors)
            
            final_accuracy = weighted_accuracy / total_weight if total_weight > 0 else success_rate
            return max(0.1, min(1.0, final_accuracy))
            
        except Exception as e:
            self.logger.error(f"Error calculating decision accuracy for {agent_id}: {e}")
            return 0.7
    
    def _calculate_confidence_calibration(self, decisions: List[Tuple[str, float, bool, float]]) -> float:
        """Calculate how well confidence scores predict actual success."""
        try:
            # Group decisions by confidence ranges
            confidence_bins = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.0)]
            calibration_errors = []
            
            for low, high in confidence_bins:
                bin_decisions = [d for d in decisions if low <= d[1] < high]
                if not bin_decisions:
                    continue
                
                predicted_confidence = sum(d[1] for d in bin_decisions) / len(bin_decisions)
                actual_success_rate = sum(1 for d in bin_decisions if d[2]) / len(bin_decisions)
                
                calibration_error = abs(predicted_confidence - actual_success_rate)
                calibration_errors.append(calibration_error)
            
            if calibration_errors:
                avg_calibration_error = sum(calibration_errors) / len(calibration_errors)
                return max(0.1, 1.0 - avg_calibration_error)  # Lower error = better calibration
            
            return 0.7
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence calibration: {e}")
            return 0.7
    
    def _calculate_decision_type_consistency(self, decisions: List[Tuple[str, float, bool, float]]) -> float:
        """Calculate consistency of decisions across different types."""
        try:
            # Group by decision type
            type_performance = {}
            
            for decision_type, confidence, success, _ in decisions:
                if decision_type not in type_performance:
                    type_performance[decision_type] = []
                
                performance_score = confidence * (1.0 if success else 0.3)
                type_performance[decision_type].append(performance_score)
            
            if not type_performance:
                return 0.7
            
            # Calculate variance across decision types
            type_averages = [
                sum(scores) / len(scores) 
                for scores in type_performance.values()
            ]
            
            if len(type_averages) > 1:
                overall_avg = sum(type_averages) / len(type_averages)
                variance = sum((avg - overall_avg) ** 2 for avg in type_averages) / len(type_averages)
                consistency = max(0.1, 1.0 - variance)  # Lower variance = higher consistency
                return min(1.0, consistency)
            
            return type_averages[0] if type_averages else 0.7
            
        except Exception as e:
            self.logger.error(f"Error calculating decision type consistency: {e}")
            return 0.7
    
    def _calculate_execution_efficiency(self, decisions: List[Tuple[str, float, bool, float]]) -> float:
        """Calculate efficiency of decision execution times."""
        try:
            successful_decisions = [d for d in decisions if d[2]]  # Only successful decisions
            if not successful_decisions:
                return 0.5
            
            execution_times = [d[3] for d in successful_decisions if d[3] is not None]
            if not execution_times:
                return 0.7
            
            # Calculate efficiency based on execution time distribution
            avg_time = sum(execution_times) / len(execution_times)
            
            # Efficiency is inversely related to execution time
            # Assuming optimal execution time is around 2-5 seconds
            optimal_time = 3.0
            
            if avg_time <= optimal_time:
                efficiency = 1.0
            else:
                # Diminishing efficiency for longer execution times
                efficiency = max(0.1, optimal_time / avg_time)
            
            return min(1.0, efficiency)
            
        except Exception as e:
            self.logger.error(f"Error calculating execution efficiency: {e}")
            return 0.7
    
    def _determine_intelligence_level(
        self,
        performance_score: float,
        learning_progress: float,
        decision_accuracy: float
    ) -> IntelligenceLevel:
        """Determine intelligence level based on scores."""
        
        overall_score = (performance_score + learning_progress + decision_accuracy) / 3.0
        
        if overall_score >= 0.9:
            return IntelligenceLevel.EXPERT
        elif overall_score >= 0.8:
            return IntelligenceLevel.ADVANCED
        elif overall_score >= 0.6:
            return IntelligenceLevel.INTERMEDIATE
        else:
            return IntelligenceLevel.BASIC
    
    def _extract_specializations(self, agent_info: AgentInfo) -> List[str]:
        """Extract agent specializations from agent info."""
        specializations = []
        
        if agent_info.registration.capabilities:
            specializations.extend(agent_info.registration.capabilities)
        
        # Add specializations based on performance metrics
        if agent_info.performance_metrics:
            if agent_info.performance_metrics.get('task_completion_rate', 0) > 0.9:
                specializations.append('high_throughput')
            if agent_info.performance_metrics.get('error_rate', 1) < 0.1:
                specializations.append('high_reliability')
        
        return list(set(specializations))  # Remove duplicates
    
    def _extract_system_features(self, coordinator_state: CoordinatorState) -> Dict[str, float]:
        """Extract system features for analysis."""
        return {
            'active_agents': len(coordinator_state.active_agents),
            'pending_tasks': len(coordinator_state.pending_tasks),
            'assigned_tasks': len(coordinator_state.assigned_tasks),
            'cpu_usage': coordinator_state.resource_usage.cpu_percent,
            'memory_usage': coordinator_state.resource_usage.memory_percent,
            'network_usage': coordinator_state.resource_usage.network_percent,
            'queue_depth': len(coordinator_state.pending_tasks),
            'response_time': coordinator_state.scaling_metrics.avg_response_time,
            'throughput': coordinator_state.scaling_metrics.throughput,
            'error_rate': coordinator_state.scaling_metrics.error_rate
        }
    
    def _calculate_performance_trend(self) -> str:
        """Calculate overall performance trend using ML-based analysis."""
        try:
            # Get recent performance metrics from database
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, confidence, success 
                    FROM intelligence_decisions 
                    WHERE timestamp > ? AND success IS NOT NULL
                    ORDER BY timestamp ASC
                """, (cutoff_time,))
                
                performance_data = cursor.fetchall()
            
            if len(performance_data) < 3:
                return "insufficient_data"
            
            # Extract performance scores over time
            timestamps = []
            scores = []
            
            for timestamp_str, confidence, success in performance_data:
                timestamps.append(datetime.fromisoformat(timestamp_str))
                # Combine confidence and success into performance score
                performance_score = confidence * (1.0 if success else 0.3)
                scores.append(performance_score)
            
            # Calculate trend using linear regression
            if len(scores) >= 2:
                # Convert timestamps to hours since start
                start_time = timestamps[0]
                x = [(ts - start_time).total_seconds() / 3600 for ts in timestamps]
                y = scores
                
                # Simple linear regression
                n = len(x)
                if n > 1:
                    sum_x = sum(x)
                    sum_y = sum(y)
                    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
                    sum_x2 = sum(xi * xi for xi in x)
                    
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                    
                    # Determine trend based on slope
                    if slope > 0.02:  # Significant positive trend
                        return "improving"
                    elif slope < -0.02:  # Significant negative trend
                        return "declining"
                    else:
                        return "stable"
                        
                return "stable"
            
        except Exception as e:
            self.logger.error(f"Error calculating performance trend: {e}")
            return "unknown"
    
    def _assess_system_health(self, coordinator_state: CoordinatorState) -> Dict[str, Any]:
        """Assess overall system health."""
        return {
            'status': 'healthy',
            'active_agents': len(coordinator_state.active_agents),
            'resource_utilization': {
                'cpu': coordinator_state.resource_usage.cpu_percent,
                'memory': coordinator_state.resource_usage.memory_percent,
                'network': coordinator_state.resource_usage.network_percent
            },
            'queue_status': 'normal' if len(coordinator_state.pending_tasks) < 10 else 'high',
            'error_rate': coordinator_state.scaling_metrics.error_rate
        }
    
    def _prioritize_optimizations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize optimization recommendations."""
        # Sort by priority (high -> medium -> low)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        return sorted(recommendations, key=lambda x: priority_order.get(x.get('priority', 'medium'), 1))
    
    async def _calculate_pattern_similarity_confidence(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        patterns: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence based on pattern similarity using ML algorithms."""
        try:
            if not patterns:
                return 0.3
            
            # Extract features from current context
            current_features = self._extract_context_features(context)
            
            # Calculate similarity scores with historical patterns
            similarity_scores = []
            for pattern in patterns:
                pattern_features = pattern.get('features', {})
                similarity = self._calculate_feature_similarity(current_features, pattern_features)
                pattern_performance = pattern.get('performance_score', 0.5)
                
                # Weight similarity by pattern performance and sample count
                weighted_similarity = similarity * pattern_performance * min(1.0, pattern.get('sample_count', 1) / 10)
                similarity_scores.append(weighted_similarity)
            
            if similarity_scores:
                # Use weighted average of top 3 similar patterns
                top_similarities = sorted(similarity_scores, reverse=True)[:3]
                confidence = sum(top_similarities) / len(top_similarities)
                return max(0.1, min(0.95, confidence))
            
            return 0.3
            
        except Exception as e:
            self.logger.error(f"Error calculating pattern similarity confidence: {e}")
            return 0.3
    
    def _calculate_model_prediction_confidence(self, insights: Dict[str, Any]) -> float:
        """Calculate confidence based on ML model prediction accuracy."""
        try:
            # Extract model confidence metrics
            accuracy_score = insights.get('accuracy_score', 0.5)
            prediction_variance = insights.get('prediction_variance', 0.5)
            feature_importance = insights.get('feature_importance', {})
            
            # Base confidence from model accuracy
            base_confidence = accuracy_score
            
            # Adjust for prediction variance (lower variance = higher confidence)
            variance_factor = max(0.1, 1.0 - prediction_variance)
            
            # Adjust for feature importance distribution
            if feature_importance:
                # More balanced feature importance = higher confidence
                importance_values = list(feature_importance.values())
                importance_std = np.std(importance_values) if importance_values else 0.5
                importance_factor = max(0.5, 1.0 - importance_std)
            else:
                importance_factor = 0.7
            
            # Combined confidence calculation
            confidence = base_confidence * variance_factor * importance_factor
            return max(0.1, min(0.95, confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculating model prediction confidence: {e}")
            return 0.5
    
    def _calculate_context_completeness_confidence(
        self,
        context: Dict[str, Any],
        decision_type: DecisionType
    ) -> float:
        """Calculate confidence based on context completeness for decision type."""
        try:
            # Define required context features for each decision type
            required_features = {
                DecisionType.TASK_ALLOCATION: ['agent_count', 'queue_size', 'task_complexity'],
                DecisionType.RESOURCE_OPTIMIZATION: ['resource_usage', 'current_load', 'historical_usage'],
                DecisionType.SCALING_DECISION: ['queue_depth', 'agent_count', 'response_time'],
                DecisionType.AGENT_COORDINATION: ['agent_capabilities', 'task_requirements'],
                DecisionType.PERFORMANCE_TUNING: ['performance_metrics', 'resource_usage'],
                DecisionType.QUALITY_ASSESSMENT: ['error_rates', 'completion_rates', 'performance_history']
            }
            
            expected_features = required_features.get(decision_type, [])
            if not expected_features:
                return 0.7  # Default confidence for unknown decision types
            
            # Calculate feature availability
            available_features = set(context.keys())
            required_features_set = set(expected_features)
            
            # Basic completeness
            completeness = len(available_features & required_features_set) / len(required_features_set)
            
            # Bonus for additional relevant features
            additional_valuable_features = {
                'historical_performance', 'agent_specializations', 'resource_constraints',
                'time_constraints', 'priority_level', 'success_rate_history'
            }
            
            bonus_features = available_features & additional_valuable_features
            bonus_factor = min(0.2, len(bonus_features) * 0.05)
            
            # Final confidence with bonus
            confidence = completeness + bonus_factor
            return max(0.1, min(0.95, confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculating context completeness confidence: {e}")
            return 0.5
    
    async def _calculate_historical_decision_confidence(self, decision_type: DecisionType) -> float:
        """Calculate confidence based on historical decision accuracy for this type."""
        try:
            # Query recent decisions of this type from database
            cutoff_time = datetime.now() - timedelta(days=7)
            
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute("""
                    SELECT confidence, success, execution_time
                    FROM intelligence_decisions 
                    WHERE decision_type = ? AND timestamp > ? AND success IS NOT NULL
                    ORDER BY timestamp DESC 
                    LIMIT 50
                """, (decision_type.value, cutoff_time))
                
                decisions = cursor.fetchall()
            
            if not decisions:
                return 0.6  # Default confidence when no history
            
            # Calculate success rate and average confidence
            successful_decisions = [d for d in decisions if d[1]]  # d[1] is success
            success_rate = len(successful_decisions) / len(decisions)
            
            # Weight by historical confidence levels
            if successful_decisions:
                avg_confidence = sum(d[0] for d in successful_decisions) / len(successful_decisions)
                confidence_variance = np.var([d[0] for d in successful_decisions])
            else:
                avg_confidence = 0.3
                confidence_variance = 0.5
            
            # Combine success rate with confidence consistency
            consistency_factor = max(0.5, 1.0 - confidence_variance)
            historical_confidence = success_rate * avg_confidence * consistency_factor
            
            return max(0.1, min(0.95, historical_confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculating historical decision confidence: {e}")
            return 0.6
    
    async def _calculate_resource_availability_confidence(self, context: Dict[str, Any]) -> float:
        """Calculate confidence based on resource availability for decision execution."""
        try:
            # Get current system state
            coordinator_state = await self.coordinator.get_coordinator_state()
            resource_usage = coordinator_state.resource_usage
            
            # Calculate resource health scores
            cpu_health = 1.0 - min(1.0, resource_usage.cpu_percent)
            memory_health = 1.0 - min(1.0, resource_usage.memory_percent)
            network_health = 1.0 - min(1.0, resource_usage.network_percent)
            
            # Agent availability factor
            available_agents = len([
                agent for agent in coordinator_state.active_agents.values()
                if agent.active_tasks < 5
            ])
            total_agents = len(coordinator_state.active_agents)
            agent_availability = available_agents / max(1, total_agents)
            
            # Queue health factor
            queue_size = len(coordinator_state.pending_tasks)
            queue_health = max(0.1, 1.0 - min(1.0, queue_size / 20))  # 20 tasks = poor health
            
            # Weighted resource confidence
            resource_confidence = (
                cpu_health * 0.25 +
                memory_health * 0.25 +
                network_health * 0.15 +
                agent_availability * 0.25 +
                queue_health * 0.1
            )
            
            return max(0.1, min(0.95, resource_confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculating resource availability confidence: {e}")
            return 0.5
    
    def _extract_context_features(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Extract numerical features from context for similarity calculation."""
        features = {}
        
        # Numerical features
        numerical_keys = [
            'agent_count', 'queue_size', 'task_complexity', 'resource_usage',
            'response_time', 'error_rate', 'success_rate', 'load_factor'
        ]
        
        for key in numerical_keys:
            if key in context:
                try:
                    features[key] = float(context[key])
                except (ValueError, TypeError):
                    features[key] = 0.0
        
        # Categorical features (convert to numerical)
        if 'priority' in context:
            priority_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
            features['priority_score'] = priority_map.get(context['priority'], 0.5)
        
        if 'urgency' in context:
            urgency_map = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'immediate': 1.0}
            features['urgency_score'] = urgency_map.get(context['urgency'], 0.5)
        
        return features
    
    def _calculate_feature_similarity(
        self,
        features1: Dict[str, float],
        features2: Dict[str, float]
    ) -> float:
        """Calculate cosine similarity between feature vectors."""
        try:
            # Get common features
            common_features = set(features1.keys()) & set(features2.keys())
            if not common_features:
                return 0.0
            
            # Create vectors for common features
            vec1 = [features1[feat] for feat in common_features]
            vec2 = [features2[feat] for feat in common_features]
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            return max(0.0, similarity)
            
        except Exception as e:
            self.logger.error(f"Error calculating feature similarity: {e}")
            return 0.0
    
    async def _analyze_resource_impact(self, resource_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resource impact of a decision using ML-based predictive models."""
        try:
            # Get current system state for baseline comparison
            coordinator_state = await self.coordinator.get_coordinator_state()
            current_usage = coordinator_state.resource_usage
            
            # Extract resource requirements
            cpu_cores = resource_requirements.get('cpu_cores', 0)
            memory_mb = resource_requirements.get('memory_mb', 0)
            network_mbps = resource_requirements.get('network_mbps', 0)
            duration_minutes = resource_requirements.get('duration_minutes', 5)
            
            # Calculate detailed impact analysis
            impact_analysis = {
                'cpu_impact': await self._calculate_cpu_impact(cpu_cores, current_usage.cpu_percent, duration_minutes),
                'memory_impact': await self._calculate_memory_impact(memory_mb, current_usage.memory_percent),
                'network_impact': await self._calculate_network_impact(network_mbps, current_usage.network_percent),
                'agent_capacity_impact': await self._calculate_agent_capacity_impact(resource_requirements),
                'predicted_bottlenecks': await self._predict_resource_bottlenecks(resource_requirements, current_usage),
                'optimization_opportunities': await self._identify_optimization_opportunities(resource_requirements),
                'risk_assessment': self._calculate_resource_risk_score(resource_requirements, current_usage),
                'overall_impact': 'pending'  # Will be calculated below
            }
            
            # Calculate overall impact classification
            impact_scores = [
                impact_analysis['cpu_impact'].get('impact_score', 0.3),
                impact_analysis['memory_impact'].get('impact_score', 0.3),
                impact_analysis['network_impact'].get('impact_score', 0.3),
                impact_analysis['risk_assessment']
            ]
            
            avg_impact = sum(impact_scores) / len(impact_scores)
            
            if avg_impact < 0.3:
                impact_analysis['overall_impact'] = 'low'
            elif avg_impact < 0.6:
                impact_analysis['overall_impact'] = 'medium'
            elif avg_impact < 0.8:
                impact_analysis['overall_impact'] = 'high'
            else:
                impact_analysis['overall_impact'] = 'critical'
            
            return impact_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing resource impact: {e}")
            return {
                'cpu_impact': {'impact_score': 0.3, 'details': 'analysis_failed'},
                'memory_impact': {'impact_score': 0.3, 'details': 'analysis_failed'},
                'network_impact': {'impact_score': 0.3, 'details': 'analysis_failed'},
                'overall_impact': 'unknown',
                'error': str(e)
            }
    
    async def _calculate_cpu_impact(self, cpu_cores: float, current_cpu: float, duration: float) -> Dict[str, Any]:
        """Calculate detailed CPU impact using predictive analysis."""
        try:
            # Predict CPU usage increase
            estimated_cpu_increase = cpu_cores * 0.15  # Estimated 15% per core
            predicted_cpu = current_cpu + estimated_cpu_increase
            
            # Use predictive analytics if available
            if hasattr(self.predictive_analytics, 'predict_resource_usage'):
                try:
                    features = {
                        'current_cpu': current_cpu,
                        'additional_cores': cpu_cores,
                        'duration': duration,
                        'time_of_day': datetime.now().hour
                    }
                    prediction = await self.predictive_analytics.predict_resource_usage(
                        'cpu_usage', current_cpu, features, int(duration)
                    )
                    predicted_cpu = prediction.predicted_usage
                except Exception as e:
                    self.logger.warning(f"CPU prediction model failed: {e}")
            
            # Calculate impact score
            if predicted_cpu < 0.6:
                impact_score = 0.2
                impact_level = 'low'
            elif predicted_cpu < 0.8:
                impact_score = 0.5
                impact_level = 'medium'
            elif predicted_cpu < 0.9:
                impact_score = 0.8
                impact_level = 'high'
            else:
                impact_score = 1.0
                impact_level = 'critical'
            
            return {
                'impact_score': impact_score,
                'impact_level': impact_level,
                'predicted_usage': predicted_cpu,
                'current_usage': current_cpu,
                'estimated_increase': estimated_cpu_increase,
                'recommendation': self._get_cpu_recommendation(predicted_cpu, impact_level)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating CPU impact: {e}")
            return {'impact_score': 0.5, 'error': str(e)}
    
    async def _calculate_memory_impact(self, memory_mb: float, current_memory: float) -> Dict[str, Any]:
        """Calculate detailed memory impact using predictive analysis."""
        try:
            # Estimate memory usage increase (convert MB to percentage)
            # Assuming system has approximately 8GB total memory
            system_memory_gb = 8.0
            memory_increase_percent = (memory_mb / 1024) / system_memory_gb
            predicted_memory = current_memory + memory_increase_percent
            
            # Use predictive analytics if available
            if hasattr(self.predictive_analytics, 'predict_resource_usage'):
                try:
                    features = {
                        'current_memory': current_memory,
                        'additional_memory_mb': memory_mb,
                        'active_agents': len(getattr(self.coordinator, 'active_agents', {}))
                    }
                    prediction = await self.predictive_analytics.predict_resource_usage(
                        'memory_usage', current_memory, features, 10
                    )
                    predicted_memory = prediction.predicted_usage
                except Exception as e:
                    self.logger.warning(f"Memory prediction model failed: {e}")
            
            # Calculate impact score
            if predicted_memory < 0.7:
                impact_score = 0.2
                impact_level = 'low'
            elif predicted_memory < 0.85:
                impact_score = 0.5
                impact_level = 'medium'
            elif predicted_memory < 0.95:
                impact_score = 0.8
                impact_level = 'high'
            else:
                impact_score = 1.0
                impact_level = 'critical'
            
            return {
                'impact_score': impact_score,
                'impact_level': impact_level,
                'predicted_usage': predicted_memory,
                'current_usage': current_memory,
                'estimated_increase': memory_increase_percent,
                'recommendation': self._get_memory_recommendation(predicted_memory, impact_level)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating memory impact: {e}")
            return {'impact_score': 0.5, 'error': str(e)}
    
    async def _calculate_network_impact(self, network_mbps: float, current_network: float) -> Dict[str, Any]:
        """Calculate detailed network impact using predictive analysis."""
        try:
            # Estimate network usage increase
            # Assuming system has 100 Mbps capacity
            system_network_capacity = 100.0
            network_increase_percent = network_mbps / system_network_capacity
            predicted_network = current_network + network_increase_percent
            
            # Calculate impact score
            if predicted_network < 0.6:
                impact_score = 0.1
                impact_level = 'low'
            elif predicted_network < 0.8:
                impact_score = 0.4
                impact_level = 'medium'
            elif predicted_network < 0.9:
                impact_score = 0.7
                impact_level = 'high'
            else:
                impact_score = 1.0
                impact_level = 'critical'
            
            return {
                'impact_score': impact_score,
                'impact_level': impact_level,
                'predicted_usage': predicted_network,
                'current_usage': current_network,
                'estimated_increase': network_increase_percent,
                'recommendation': self._get_network_recommendation(predicted_network, impact_level)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating network impact: {e}")
            return {'impact_score': 0.3, 'error': str(e)}
    
    async def _calculate_agent_capacity_impact(self, resource_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate impact on agent capacity and availability."""
        try:
            coordinator_state = await self.coordinator.get_coordinator_state()
            
            # Calculate current agent utilization
            total_agents = len(coordinator_state.active_agents)
            busy_agents = len([
                agent for agent in coordinator_state.active_agents.values()
                if agent.active_tasks >= 4
            ])
            
            current_utilization = busy_agents / max(1, total_agents)
            
            # Estimate additional agents needed
            task_complexity = resource_requirements.get('task_complexity', 1.0)
            estimated_agents_needed = max(1, int(task_complexity))
            
            # Predict capacity impact
            if total_agents - busy_agents >= estimated_agents_needed:
                capacity_impact = 'low'
                impact_score = 0.2
            elif total_agents - busy_agents > 0:
                capacity_impact = 'medium'
                impact_score = 0.5
            else:
                capacity_impact = 'high'
                impact_score = 0.9
            
            return {
                'impact_score': impact_score,
                'capacity_impact': capacity_impact,
                'current_utilization': current_utilization,
                'estimated_agents_needed': estimated_agents_needed,
                'available_agents': total_agents - busy_agents,
                'recommendation': self._get_capacity_recommendation(capacity_impact, total_agents, busy_agents)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating agent capacity impact: {e}")
            return {'impact_score': 0.5, 'error': str(e)}
    
    async def _predict_resource_bottlenecks(
        self,
        resource_requirements: Dict[str, Any],
        current_usage: Any
    ) -> List[Dict[str, str]]:
        """Predict potential resource bottlenecks using ML analysis."""
        bottlenecks = []
        
        try:
            # Check for CPU bottleneck
            cpu_cores = resource_requirements.get('cpu_cores', 0)
            if current_usage.cpu_percent + (cpu_cores * 0.15) > 0.85:
                bottlenecks.append({
                    'resource': 'cpu',
                    'severity': 'high' if current_usage.cpu_percent > 0.8 else 'medium',
                    'prediction': f'CPU usage may exceed 85% (current: {current_usage.cpu_percent:.1%})'
                })
            
            # Check for memory bottleneck
            memory_mb = resource_requirements.get('memory_mb', 0)
            memory_increase = (memory_mb / 1024) / 8.0  # Assuming 8GB system
            if current_usage.memory_percent + memory_increase > 0.9:
                bottlenecks.append({
                    'resource': 'memory',
                    'severity': 'critical' if current_usage.memory_percent > 0.85 else 'high',
                    'prediction': f'Memory usage may exceed 90% (current: {current_usage.memory_percent:.1%})'
                })
            
            # Check for network bottleneck
            network_mbps = resource_requirements.get('network_mbps', 0)
            if current_usage.network_percent + (network_mbps / 100) > 0.8:
                bottlenecks.append({
                    'resource': 'network',
                    'severity': 'medium',
                    'prediction': f'Network usage may exceed 80% (current: {current_usage.network_percent:.1%})'
                })
            
        except Exception as e:
            self.logger.error(f"Error predicting bottlenecks: {e}")
            bottlenecks.append({
                'resource': 'analysis',
                'severity': 'unknown',
                'prediction': f'Bottleneck analysis failed: {e}'
            })
        
        return bottlenecks
    
    async def _identify_optimization_opportunities(self, resource_requirements: Dict[str, Any]) -> List[str]:
        """Identify optimization opportunities based on resource analysis."""
        opportunities = []
        
        # Check for resource optimization opportunities
        cpu_cores = resource_requirements.get('cpu_cores', 0)
        memory_mb = resource_requirements.get('memory_mb', 0)
        duration = resource_requirements.get('duration_minutes', 5)
        
        if cpu_cores > 2:
            opportunities.append("Consider task parallelization to reduce CPU core requirements")
        
        if memory_mb > 2048:  # > 2GB
            opportunities.append("Evaluate memory usage patterns for potential optimization")
        
        if duration > 30:
            opportunities.append("Consider breaking long-running tasks into smaller chunks")
        
        # Add intelligent recommendations based on patterns
        try:
            patterns = await self.pattern_optimizer.get_task_patterns()
            if patterns:
                high_perf_patterns = [p for p in patterns if p.get('performance_score', 0) > 0.8]
                if high_perf_patterns:
                    opportunities.append("Apply high-performance patterns from similar successful tasks")
        except Exception as e:
            self.logger.warning(f"Could not get optimization patterns: {e}")
        
        return opportunities
    
    def _calculate_resource_risk_score(
        self,
        resource_requirements: Dict[str, Any],
        current_usage: Any
    ) -> float:
        """Calculate overall resource risk score."""
        try:
            risk_factors = []
            
            # CPU risk
            cpu_risk = min(1.0, current_usage.cpu_percent + resource_requirements.get('cpu_cores', 0) * 0.15)
            risk_factors.append(cpu_risk)
            
            # Memory risk
            memory_increase = (resource_requirements.get('memory_mb', 0) / 1024) / 8.0
            memory_risk = min(1.0, current_usage.memory_percent + memory_increase)
            risk_factors.append(memory_risk)
            
            # Network risk
            network_increase = resource_requirements.get('network_mbps', 0) / 100
            network_risk = min(1.0, current_usage.network_percent + network_increase)
            risk_factors.append(network_risk)
            
            # Duration risk (longer tasks have higher risk)
            duration = resource_requirements.get('duration_minutes', 5)
            duration_risk = min(1.0, duration / 60)  # Normalize to 1 hour
            risk_factors.append(duration_risk)
            
            # Calculate weighted average
            weights = [0.3, 0.3, 0.2, 0.2]
            weighted_risk = sum(risk * weight for risk, weight in zip(risk_factors, weights))
            
            return max(0.0, min(1.0, weighted_risk))
            
        except Exception as e:
            self.logger.error(f"Error calculating resource risk score: {e}")
            return 0.5
    
    def _get_cpu_recommendation(self, predicted_usage: float, impact_level: str) -> str:
        """Get CPU optimization recommendation."""
        if impact_level == 'critical':
            return "Critical: Scale up CPU resources or defer task execution"
        elif impact_level == 'high':
            return "High: Consider CPU optimization or load balancing"
        elif impact_level == 'medium':
            return "Medium: Monitor CPU usage during execution"
        else:
            return "Low: No immediate CPU concerns"
    
    def _get_memory_recommendation(self, predicted_usage: float, impact_level: str) -> str:
        """Get memory optimization recommendation."""
        if impact_level == 'critical':
            return "Critical: Increase memory allocation or optimize memory usage"
        elif impact_level == 'high':
            return "High: Monitor memory usage and consider garbage collection"
        elif impact_level == 'medium':
            return "Medium: Watch for memory leaks during execution"
        else:
            return "Low: Memory usage within acceptable limits"
    
    def _get_network_recommendation(self, predicted_usage: float, impact_level: str) -> str:
        """Get network optimization recommendation."""
        if impact_level == 'critical':
            return "Critical: Optimize network usage or increase bandwidth"
        elif impact_level == 'high':
            return "High: Consider data compression or caching"
        elif impact_level == 'medium':
            return "Medium: Monitor network latency"
        else:
            return "Low: Network impact minimal"
    
    def _get_capacity_recommendation(self, impact: str, total_agents: int, busy_agents: int) -> str:
        """Get agent capacity recommendation."""
        if impact == 'high':
            return f"High: Scale up agents (current: {total_agents}, busy: {busy_agents})"
        elif impact == 'medium':
            return f"Medium: Consider agent optimization (available: {total_agents - busy_agents})"
        else:
            return f"Low: Sufficient agent capacity (available: {total_agents - busy_agents})"
    
    def get_intelligence_summary(self) -> Dict[str, Any]:
        """Get summary of intelligence framework status."""
        return {
            'framework_status': 'active' if self.running else 'inactive',
            'intelligence_level': self.config.intelligence_level.value,
            'total_agents': len(self.agent_intelligence),
            'active_learning_sessions': len(self.active_learning_sessions),
            'performance_metrics': self.performance_metrics,
            'decision_history_count': len(self.decision_history),
            'agent_intelligence_levels': {
                level.value: sum(1 for ai in self.agent_intelligence.values() 
                               if ai.intelligence_level == level)
                for level in IntelligenceLevel
            }
        }