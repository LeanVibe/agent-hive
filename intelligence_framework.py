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
        """Calculate confidence in a decision."""
        
        base_confidence = 0.7
        
        # Adjust based on context complexity
        complexity = analysis.get('context_complexity', 0.5)
        confidence = base_confidence * (1.0 - complexity * 0.3)
        
        # Adjust based on historical patterns
        patterns = analysis.get('historical_patterns', [])
        if patterns:
            confidence += 0.1
        
        # Adjust based on predictive insights
        insights = analysis.get('predictive_insights', {})
        if insights and insights.get('accuracy_score', 0) > 0.8:
            confidence += 0.1
        
        return max(0.1, min(0.95, confidence))
    
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
        """Background task for coordinating learning sessions."""
        while self.running:
            try:
                await asyncio.sleep(self.config.learning_update_interval)
                
                # Start learning sessions for underperforming agents
                for agent_id, intelligence in self.agent_intelligence.items():
                    if intelligence.performance_score < 0.7 and agent_id not in self.active_learning_sessions:
                        session_id = self.adaptive_learning.start_learning_session(
                            'performance_optimizer',
                            {'agent_id': agent_id, 'target_improvement': 0.8}
                        )
                        self.active_learning_sessions[agent_id] = session_id
                        
                        self.logger.info(f"Started learning session for agent {agent_id}")
                
            except Exception as e:
                self.logger.error(f"Learning coordination error: {e}")
    
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
        """Calculate agent performance score."""
        # Get agent info
        agent_info = await self.coordinator.get_agent_status(agent_id)
        if not agent_info:
            return 0.5
        
        # Calculate performance based on error rate and task completion
        error_rate = agent_info.error_count / max(1, agent_info.active_tasks + agent_info.error_count)
        performance = 1.0 - error_rate
        
        # Adjust based on resource utilization
        if agent_info.current_usage:
            utilization = (agent_info.current_usage.cpu_percent + 
                          agent_info.current_usage.memory_percent) / 2.0
            # Optimal utilization is around 60-70%
            utilization_factor = 1.0 - abs(utilization - 0.65) * 2
            performance *= max(0.5, utilization_factor)
        
        return max(0.1, min(1.0, performance))
    
    async def _calculate_learning_progress(self, agent_id: str) -> float:
        """Calculate agent learning progress."""
        # Check if agent has active learning sessions
        if agent_id in self.active_learning_sessions:
            return 0.8  # Active learning
        
        # Get historical learning data
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute("""
                SELECT improvement_score FROM learning_sessions 
                WHERE agent_id = ? AND end_time IS NOT NULL
                ORDER BY end_time DESC LIMIT 5
            """, (agent_id,))
            
            scores = [row[0] for row in cursor.fetchall() if row[0] is not None]
        
        if scores:
            return min(1.0, sum(scores) / len(scores))
        
        return 0.5  # Default learning progress
    
    async def _calculate_decision_accuracy(self, agent_id: str) -> float:
        """Calculate agent decision accuracy."""
        # This would typically track agent's decision outcomes
        # For now, return a default value
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
        """Calculate overall performance trend."""
        # This would analyze historical performance data
        return "stable"  # Default trend
    
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
    
    async def _analyze_resource_impact(self, resource_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resource impact of a decision."""
        return {
            'cpu_impact': resource_requirements.get('cpu_cores', 0) * 0.1,
            'memory_impact': resource_requirements.get('memory_mb', 0) * 0.001,
            'network_impact': resource_requirements.get('network_mbps', 0) * 0.01,
            'overall_impact': 'low'
        }
    
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