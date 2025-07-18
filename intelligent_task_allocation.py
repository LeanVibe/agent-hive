"""
Intelligent Task Allocation and Prioritization System

This module provides advanced task allocation and prioritization capabilities
using machine learning and intelligent decision-making algorithms.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import sqlite3
import numpy as np
from collections import defaultdict
import uuid

from advanced_orchestration.models import (
    AgentInfo, ResourceRequirements
)


logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    VERY_COMPLEX = 4


class AllocationStrategy(Enum):
    """Task allocation strategies."""
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    CAPABILITY_BASED = "capability_based"
    PERFORMANCE_OPTIMIZED = "performance_optimized"
    INTELLIGENT_HYBRID = "intelligent_hybrid"


@dataclass
class TaskMetrics:
    """Metrics for task performance tracking."""

    task_id: str
    allocated_agent: str
    allocation_time: datetime
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    execution_duration: Optional[float] = None
    resource_utilization: Dict[str, float] = field(default_factory=dict)
    quality_score: float = 0.0
    error_count: int = 0
    retry_count: int = 0
    success: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'allocated_agent': self.allocated_agent,
            'allocation_time': self.allocation_time.isoformat(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'completion_time': self.completion_time.isoformat() if self.completion_time else None,
            'execution_duration': self.execution_duration,
            'resource_utilization': self.resource_utilization,
            'quality_score': self.quality_score,
            'error_count': self.error_count,
            'retry_count': self.retry_count,
            'success': self.success
        }


@dataclass
class IntelligentTask:
    """Enhanced task with intelligence and learning capabilities."""

    task_id: str
    task_type: str
    priority: TaskPriority
    complexity: TaskComplexity
    requirements: ResourceRequirements
    dependencies: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: float = 0.0
    deadline: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Learning and adaptation
    historical_performance: List[float] = field(default_factory=list)
    preferred_agents: List[str] = field(default_factory=list)
    blacklisted_agents: List[str] = field(default_factory=list)

    # Runtime state
    created_at: datetime = field(default_factory=datetime.now)
    allocation_attempts: int = 0
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'priority': self.priority.value,
            'complexity': self.complexity.value,
            'requirements': {
                'cpu_cores': self.requirements.cpu_cores,
                'memory_mb': self.requirements.memory_mb,
                'disk_mb': self.requirements.disk_mb,
                'network_mbps': self.requirements.network_mbps
            },
            'dependencies': self.dependencies,
            'constraints': self.constraints,
            'estimated_duration': self.estimated_duration,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'context': self.context,
            'metadata': self.metadata,
            'historical_performance': self.historical_performance,
            'preferred_agents': self.preferred_agents,
            'blacklisted_agents': self.blacklisted_agents,
            'created_at': self.created_at.isoformat(),
            'allocation_attempts': self.allocation_attempts,
            'retry_count': self.retry_count
        }


@dataclass
class AgentPerformanceProfile:
    """Performance profile for an agent."""

    agent_id: str
    task_types: Dict[str, float]  # task_type -> performance_score
    complexity_handling: Dict[TaskComplexity, float]
    resource_efficiency: Dict[str, float]  # resource_type -> efficiency
    reliability_score: float
    throughput_score: float
    quality_score: float
    learning_rate: float
    specializations: List[str]

    # Performance history
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time: float = 0.0
    average_quality: float = 0.0

    # Adaptive metrics
    recent_performance: List[float] = field(default_factory=list)
    performance_trend: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

    def update_performance(self, task_metrics: TaskMetrics) -> None:
        """Update performance profile with new task metrics."""
        self.completed_tasks += 1
        self.total_execution_time += task_metrics.execution_duration or 0

        # Update quality score
        self.average_quality = (
            (self.average_quality * (self.completed_tasks - 1) + task_metrics.quality_score) /
            self.completed_tasks
        )

        # Update recent performance
        performance_score = 1.0 if task_metrics.success else 0.0
        self.recent_performance.append(performance_score)

        # Keep only last 20 performance samples
        if len(self.recent_performance) > 20:
            self.recent_performance = self.recent_performance[-20:]

        # Calculate performance trend
        if len(self.recent_performance) >= 5:
            recent_avg = np.mean(self.recent_performance[-5:])
            older_avg = np.mean(self.recent_performance[:-5]) if len(self.recent_performance) > 5 else recent_avg
            self.performance_trend = recent_avg - older_avg

        self.last_updated = datetime.now()

    def get_performance_score(self, task_type: str, complexity: TaskComplexity) -> float:
        """Get performance score for a specific task type and complexity."""
        base_score = self.task_types.get(task_type, 0.5)
        complexity_factor = self.complexity_handling.get(complexity, 0.5)

        # Combine base score with complexity handling
        combined_score = (base_score * 0.7) + (complexity_factor * 0.3)

        # Adjust for recent performance trend
        adjusted_score = combined_score + (self.performance_trend * 0.1)

        return max(0.0, min(1.0, adjusted_score))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'agent_id': self.agent_id,
            'task_types': self.task_types,
            'complexity_handling': {k.value: v for k, v in self.complexity_handling.items()},
            'resource_efficiency': self.resource_efficiency,
            'reliability_score': self.reliability_score,
            'throughput_score': self.throughput_score,
            'quality_score': self.quality_score,
            'learning_rate': self.learning_rate,
            'specializations': self.specializations,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'total_execution_time': self.total_execution_time,
            'average_quality': self.average_quality,
            'recent_performance': self.recent_performance,
            'performance_trend': self.performance_trend,
            'last_updated': self.last_updated.isoformat()
        }


class IntelligentTaskAllocator:
    """
    Intelligent task allocation and prioritization system.

    This class provides advanced task allocation using machine learning,
    performance prediction, and intelligent optimization strategies.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the intelligent task allocator."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Task management
        self.task_queue: List[IntelligentTask] = []
        self.active_tasks: Dict[str, IntelligentTask] = {}
        self.completed_tasks: Dict[str, TaskMetrics] = {}
        self.failed_tasks: Dict[str, TaskMetrics] = {}

        # Agent management
        self.agent_profiles: Dict[str, AgentPerformanceProfile] = {}
        self.agent_workloads: Dict[str, int] = defaultdict(int)

        # Learning and optimization
        self.task_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.allocation_history: List[Dict[str, Any]] = []

        # Performance tracking
        self.allocation_metrics = {
            'total_allocations': 0,
            'successful_allocations': 0,
            'failed_allocations': 0,
            'average_allocation_time': 0.0,
            'average_execution_time': 0.0,
            'resource_utilization': 0.0,
            'agent_satisfaction': 0.0
        }

        # Configuration
        self.max_task_queue_size = self.config.get('max_task_queue_size', 1000)
        self.allocation_timeout = self.config.get('allocation_timeout', 30.0)
        self.performance_window = self.config.get('performance_window', 100)

        # Initialize database
        self._init_database()

        self.logger.info("Intelligent Task Allocator initialized")

    def _init_database(self) -> None:
        """Initialize SQLite database for task allocation data."""
        db_path = self.config.get('db_path', 'task_allocation.db')

        with sqlite3.connect(db_path) as conn:
            # Task allocation history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_allocations (
                    allocation_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    allocation_time TIMESTAMP NOT NULL,
                    completion_time TIMESTAMP,
                    success BOOLEAN,
                    execution_duration REAL,
                    quality_score REAL,
                    resource_utilization TEXT,
                    metadata TEXT
                )
            """)

            # Agent performance history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_performance (
                    performance_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    complexity INTEGER NOT NULL,
                    performance_score REAL NOT NULL,
                    execution_time REAL NOT NULL,
                    quality_score REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            # Task patterns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    frequency INTEGER NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            # Allocation strategies performance
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    strategy_id TEXT PRIMARY KEY,
                    strategy_name TEXT NOT NULL,
                    success_rate REAL NOT NULL,
                    average_allocation_time REAL NOT NULL,
                    average_execution_time REAL NOT NULL,
                    resource_efficiency REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_allocations_agent_time
                ON task_allocations(agent_id, allocation_time)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_agent_task
                ON agent_performance(agent_id, task_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_type
                ON task_patterns(task_type)
            """)

            conn.commit()

    async def submit_task(
        self,
        task_type: str,
        priority: TaskPriority,
        complexity: TaskComplexity,
        requirements: ResourceRequirements,
        dependencies: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        deadline: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IntelligentTask:
        """
        Submit a new task for intelligent allocation.

        Args:
            task_type: Type of task
            priority: Task priority level
            complexity: Task complexity level
            requirements: Resource requirements
            dependencies: Task dependencies
            constraints: Task constraints
            deadline: Task deadline
            context: Task context
            metadata: Additional metadata

        Returns:
            IntelligentTask: The created task
        """
        task_id = str(uuid.uuid4())

        # Estimate duration based on historical data
        estimated_duration = await self._estimate_task_duration(task_type, complexity)

        # Create intelligent task
        task = IntelligentTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            complexity=complexity,
            requirements=requirements,
            dependencies=dependencies or [],
            constraints=constraints or {},
            estimated_duration=estimated_duration,
            deadline=deadline,
            context=context or {},
            metadata=metadata or {}
        )

        # Add to queue
        await self._add_to_queue(task)

        # Learn from task submission pattern
        await self._learn_task_pattern(task)

        self.logger.info(f"Task {task_id} submitted with priority {priority.name}")
        return task

    async def allocate_task(
        self,
        task: IntelligentTask,
        available_agents: List[AgentInfo],
        strategy: AllocationStrategy = AllocationStrategy.INTELLIGENT_HYBRID
    ) -> Optional[str]:
        """
        Allocate a task to the best available agent.

        Args:
            task: Task to allocate
            available_agents: List of available agents
            strategy: Allocation strategy to use

        Returns:
            str: ID of the allocated agent, or None if allocation failed
        """
        start_time = datetime.now()

        try:
            # Check dependencies
            if not await self._check_dependencies(task):
                self.logger.debug(f"Task {task.task_id} dependencies not satisfied")
                return None

            # Filter suitable agents
            suitable_agents = await self._filter_suitable_agents(task, available_agents)

            if not suitable_agents:
                self.logger.warning(f"No suitable agents found for task {task.task_id}")
                return None

            # Select best agent using strategy
            selected_agent = await self._select_best_agent(task, suitable_agents, strategy)

            if not selected_agent:
                self.logger.warning(f"No agent selected for task {task.task_id}")
                return None

            # Perform allocation
            success = await self._perform_allocation(task, selected_agent)

            if success:
                # Update metrics
                allocation_time = (datetime.now() - start_time).total_seconds()
                await self._update_allocation_metrics(task, selected_agent.agent_id, allocation_time, True)

                self.logger.info(f"Task {task.task_id} allocated to agent {selected_agent.agent_id}")
                return selected_agent.agent_id
            else:
                await self._update_allocation_metrics(task, selected_agent.agent_id, 0, False)
                return None

        except Exception as e:
            self.logger.error(f"Task allocation failed for {task.task_id}: {e}")
            await self._update_allocation_metrics(task, "", 0, False)
            return None

    async def complete_task(
        self,
        task_id: str,
        agent_id: str,
        success: bool,
        execution_duration: float,
        quality_score: float,
        resource_utilization: Dict[str, float],
        error_count: int = 0
    ) -> None:
        """
        Mark a task as completed and update performance metrics.

        Args:
            task_id: ID of the completed task
            agent_id: ID of the agent that completed the task
            success: Whether the task was successful
            execution_duration: Time taken to execute the task
            quality_score: Quality score of the task output
            resource_utilization: Resource utilization during execution
            error_count: Number of errors encountered
        """
        if task_id not in self.active_tasks:
            self.logger.warning(f"Task {task_id} not found in active tasks")
            return

        task = self.active_tasks.pop(task_id)

        # Create task metrics
        task_metrics = TaskMetrics(
            task_id=task_id,
            allocated_agent=agent_id,
            allocation_time=task.created_at,
            completion_time=datetime.now(),
            execution_duration=execution_duration,
            resource_utilization=resource_utilization,
            quality_score=quality_score,
            error_count=error_count,
            success=success
        )

        # Store metrics
        if success:
            self.completed_tasks[task_id] = task_metrics
        else:
            self.failed_tasks[task_id] = task_metrics

        # Update agent performance profile
        await self._update_agent_performance(agent_id, task, task_metrics)

        # Learn from task completion
        await self._learn_from_completion(task, task_metrics)

        # Update workload
        self.agent_workloads[agent_id] = max(0, self.agent_workloads[agent_id] - 1)

        # Store in database
        await self._store_task_completion(task_metrics)

        self.logger.info(f"Task {task_id} completed by agent {agent_id} (success: {success})")

    async def get_task_recommendations(
        self,
        agent_id: str,
        max_recommendations: int = 5
    ) -> List[Tuple[IntelligentTask, float]]:
        """
        Get task recommendations for an agent based on their performance profile.

        Args:
            agent_id: ID of the agent
            max_recommendations: Maximum number of recommendations

        Returns:
            List of (task, score) tuples sorted by recommendation score
        """
        if agent_id not in self.agent_profiles:
            return []

        agent_profile = self.agent_profiles[agent_id]
        recommendations = []

        for task in self.task_queue:
            # Skip if agent is blacklisted for this task
            if agent_id in task.blacklisted_agents:
                continue

            # Calculate recommendation score
            score = await self._calculate_recommendation_score(agent_profile, task)

            if score > 0.5:  # Threshold for recommendations
                recommendations.append((task, score))

        # Sort by score (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return recommendations[:max_recommendations]

    async def optimize_allocation_strategy(self) -> AllocationStrategy:
        """
        Optimize allocation strategy based on historical performance.

        Returns:
            AllocationStrategy: The optimal strategy
        """
        # Analyze performance of different strategies
        strategy_performance = {}

        for strategy in AllocationStrategy:
            performance = await self._analyze_strategy_performance(strategy)
            strategy_performance[strategy] = performance

        # Select best performing strategy
        best_strategy = max(strategy_performance, key=lambda s: strategy_performance[s]['overall_score'])

        self.logger.info(f"Optimal allocation strategy: {best_strategy.name}")
        return best_strategy

    async def rebalance_workloads(self, agents: List[AgentInfo]) -> Dict[str, List[str]]:
        """
        Rebalance workloads across agents for optimal performance.

        Args:
            agents: List of available agents

        Returns:
            Dict mapping agent IDs to lists of tasks to be reassigned
        """
        rebalancing_plan = {}

        # Calculate current load distribution
        agent_loads = {}
        for agent in agents:
            agent_loads[agent.agent_id] = self.agent_workloads[agent.agent_id]

        # Identify overloaded and underloaded agents
        avg_load = sum(agent_loads.values()) / len(agent_loads)
        overloaded_agents = [aid for aid, load in agent_loads.items() if load > avg_load * 1.5]
        underloaded_agents = [aid for aid, load in agent_loads.items() if load < avg_load * 0.5]

        # Plan task reassignments
        for overloaded_agent in overloaded_agents:
            tasks_to_reassign = await self._identify_reassignable_tasks(overloaded_agent)

            for task_id in tasks_to_reassign:
                # Find best underloaded agent for this task
                best_agent = await self._find_best_reassignment_agent(
                    task_id, underloaded_agents
                )

                if best_agent:
                    if best_agent not in rebalancing_plan:
                        rebalancing_plan[best_agent] = []
                    rebalancing_plan[best_agent].append(task_id)

        return rebalancing_plan

    async def predict_task_completion(
        self,
        task_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Predict task completion metrics for a given task-agent pair.

        Args:
            task_id: ID of the task
            agent_id: ID of the agent

        Returns:
            Dict containing prediction metrics
        """
        if task_id not in self.active_tasks:
            return {'error': 'Task not found'}

        task = self.active_tasks[task_id]

        if agent_id not in self.agent_profiles:
            return {'error': 'Agent profile not found'}

        agent_profile = self.agent_profiles[agent_id]

        # Predict completion time
        predicted_duration = await self._predict_execution_duration(task, agent_profile)

        # Predict success probability
        success_probability = await self._predict_success_probability(task, agent_profile)

        # Predict quality score
        predicted_quality = await self._predict_quality_score(task, agent_profile)

        # Predict resource utilization
        predicted_resources = await self._predict_resource_utilization(task, agent_profile)

        return {
            'task_id': task_id,
            'agent_id': agent_id,
            'predicted_duration': predicted_duration,
            'success_probability': success_probability,
            'predicted_quality': predicted_quality,
            'predicted_resources': predicted_resources,
            'confidence': self._calculate_prediction_confidence(task, agent_profile)
        }

    async def _add_to_queue(self, task: IntelligentTask) -> None:
        """Add task to the priority queue."""
        # Insert task in priority order
        inserted = False
        for i, queued_task in enumerate(self.task_queue):
            if self._compare_task_priority(task, queued_task):
                self.task_queue.insert(i, task)
                inserted = True
                break

        if not inserted:
            self.task_queue.append(task)

        # Maintain queue size limit
        if len(self.task_queue) > self.max_task_queue_size:
            # Remove lowest priority tasks
            self.task_queue = self.task_queue[:self.max_task_queue_size]

    async def _check_dependencies(self, task: IntelligentTask) -> bool:
        """Check if task dependencies are satisfied."""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True

    async def _filter_suitable_agents(
        self,
        task: IntelligentTask,
        available_agents: List[AgentInfo]
    ) -> List[AgentInfo]:
        """Filter agents that are suitable for the task."""
        suitable_agents = []

        for agent in available_agents:
            # Check if agent is blacklisted
            if agent.agent_id in task.blacklisted_agents:
                continue

            # Check resource requirements
            if not self._check_resource_compatibility(task.requirements, agent):
                continue

            # Check agent capabilities
            if not self._check_capability_match(task, agent):
                continue

            # Check workload
            if self.agent_workloads[agent.agent_id] >= 10:  # Max concurrent tasks
                continue

            suitable_agents.append(agent)

        return suitable_agents

    async def _select_best_agent(
        self,
        task: IntelligentTask,
        suitable_agents: List[AgentInfo],
        strategy: AllocationStrategy
    ) -> Optional[AgentInfo]:
        """Select the best agent for the task using the specified strategy."""

        if strategy == AllocationStrategy.ROUND_ROBIN:
            return await self._select_round_robin(suitable_agents)

        elif strategy == AllocationStrategy.LOAD_BALANCED:
            return await self._select_load_balanced(suitable_agents)

        elif strategy == AllocationStrategy.CAPABILITY_BASED:
            return await self._select_capability_based(task, suitable_agents)

        elif strategy == AllocationStrategy.PERFORMANCE_OPTIMIZED:
            return await self._select_performance_optimized(task, suitable_agents)

        elif strategy == AllocationStrategy.INTELLIGENT_HYBRID:
            return await self._select_intelligent_hybrid(task, suitable_agents)

        else:
            return suitable_agents[0] if suitable_agents else None

    async def _select_round_robin(self, suitable_agents: List[AgentInfo]) -> Optional[AgentInfo]:
        """Select agent using round-robin strategy."""
        if not suitable_agents:
            return None

        # Simple round-robin based on allocation count
        agent_allocations = {agent.agent_id: self.agent_workloads[agent.agent_id] for agent in suitable_agents}
        min_allocations = min(agent_allocations.values())

        # Find agents with minimum allocations
        candidates = [agent for agent in suitable_agents
                     if agent_allocations[agent.agent_id] == min_allocations]

        return candidates[0]

    async def _select_load_balanced(self, suitable_agents: List[AgentInfo]) -> Optional[AgentInfo]:
        """Select agent using load balancing strategy."""
        if not suitable_agents:
            return None

        # Select agent with lowest current workload
        return min(suitable_agents, key=lambda a: self.agent_workloads[a.agent_id])

    async def _select_capability_based(
        self,
        task: IntelligentTask,
        suitable_agents: List[AgentInfo]
    ) -> Optional[AgentInfo]:
        """Select agent based on capability matching."""
        if not suitable_agents:
            return None

        # Score agents based on capability match
        agent_scores = []

        for agent in suitable_agents:
            score = await self._calculate_capability_score(task, agent)
            agent_scores.append((agent, score))

        # Sort by score (descending)
        agent_scores.sort(key=lambda x: x[1], reverse=True)

        return agent_scores[0][0]

    async def _select_performance_optimized(
        self,
        task: IntelligentTask,
        suitable_agents: List[AgentInfo]
    ) -> Optional[AgentInfo]:
        """Select agent based on performance optimization."""
        if not suitable_agents:
            return None

        # Score agents based on historical performance
        agent_scores = []

        for agent in suitable_agents:
            if agent.agent_id in self.agent_profiles:
                profile = self.agent_profiles[agent.agent_id]
                score = profile.get_performance_score(task.task_type, task.complexity)
                agent_scores.append((agent, score))

        if not agent_scores:
            return suitable_agents[0]

        # Sort by score (descending)
        agent_scores.sort(key=lambda x: x[1], reverse=True)

        return agent_scores[0][0]

    async def _select_intelligent_hybrid(
        self,
        task: IntelligentTask,
        suitable_agents: List[AgentInfo]
    ) -> Optional[AgentInfo]:
        """Select agent using intelligent hybrid strategy."""
        if not suitable_agents:
            return None

        # Calculate comprehensive score for each agent
        agent_scores = []

        for agent in suitable_agents:
            score_components = {
                'performance': 0.0,
                'capability': 0.0,
                'load': 0.0,
                'preference': 0.0
            }

            # Performance score
            if agent.agent_id in self.agent_profiles:
                profile = self.agent_profiles[agent.agent_id]
                score_components['performance'] = profile.get_performance_score(task.task_type, task.complexity)

            # Capability score
            score_components['capability'] = await self._calculate_capability_score(task, agent)

            # Load score (inverse of current workload)
            max_load = max(self.agent_workloads.values()) if self.agent_workloads else 1
            max_load = max(max_load, 1)  # Ensure max_load is at least 1 to avoid division by zero
            current_load = self.agent_workloads.get(agent.agent_id, 0)
            score_components['load'] = 1.0 - (current_load / max_load)

            # Preference score (if agent is preferred for this task)
            if agent.agent_id in task.preferred_agents:
                score_components['preference'] = 1.0

            # Weighted combination
            total_score = (
                score_components['performance'] * 0.4 +
                score_components['capability'] * 0.3 +
                score_components['load'] * 0.2 +
                score_components['preference'] * 0.1
            )

            agent_scores.append((agent, total_score, score_components))

        # Sort by total score (descending)
        agent_scores.sort(key=lambda x: x[1], reverse=True)

        return agent_scores[0][0]

    async def _perform_allocation(self, task: IntelligentTask, agent: AgentInfo) -> bool:
        """Perform the actual task allocation."""
        try:
            # Move task to active tasks
            self.active_tasks[task.task_id] = task

            # Update agent workload
            self.agent_workloads[agent.agent_id] += 1

            # Update task allocation attempts
            task.allocation_attempts += 1

            # Record allocation
            self.allocation_history.append({
                'task_id': task.task_id,
                'agent_id': agent.agent_id,
                'allocation_time': datetime.now(),
                'task_type': task.task_type,
                'priority': task.priority.value,
                'complexity': task.complexity.value
            })

            return True

        except Exception as e:
            self.logger.error(f"Allocation failed for task {task.task_id} to agent {agent.agent_id}: {e}")
            return False

    async def _estimate_task_duration(self, task_type: str, complexity: TaskComplexity) -> float:
        """Estimate task duration based on historical data."""
        # Get historical data for similar tasks
        similar_tasks = [
            metrics for metrics in self.completed_tasks.values()
            if metrics.task_id in [t.task_id for t in self.task_queue + list(self.active_tasks.values())
                                  if t.task_type == task_type and t.complexity == complexity]
        ]

        if similar_tasks:
            durations = [t.execution_duration for t in similar_tasks if t.execution_duration]
            if durations:
                return np.mean(durations)

        # Default estimates based on complexity
        complexity_estimates = {
            TaskComplexity.SIMPLE: 60.0,      # 1 minute
            TaskComplexity.MODERATE: 300.0,   # 5 minutes
            TaskComplexity.COMPLEX: 900.0,    # 15 minutes
            TaskComplexity.VERY_COMPLEX: 1800.0  # 30 minutes
        }

        return complexity_estimates.get(complexity, 300.0)

    async def _learn_task_pattern(self, task: IntelligentTask) -> None:
        """Learn from task submission patterns."""
        pattern_key = f"{task.task_type}_{task.complexity.value}_{task.priority.value}"

        pattern_data = {
            'task_type': task.task_type,
            'complexity': task.complexity.value,
            'priority': task.priority.value,
            'submission_time': task.created_at.isoformat(),
            'resource_requirements': task.requirements.__dict__,
            'dependencies_count': len(task.dependencies)
        }

        self.task_patterns[pattern_key].append(pattern_data)

        # Keep only recent patterns
        if len(self.task_patterns[pattern_key]) > 100:
            self.task_patterns[pattern_key] = self.task_patterns[pattern_key][-100:]

    async def _update_agent_performance(
        self,
        agent_id: str,
        task: IntelligentTask,
        task_metrics: TaskMetrics
    ) -> None:
        """Update agent performance profile."""
        if agent_id not in self.agent_profiles:
            # Create new profile
            self.agent_profiles[agent_id] = AgentPerformanceProfile(
                agent_id=agent_id,
                task_types={},
                complexity_handling={},
                resource_efficiency={},
                reliability_score=0.8,
                throughput_score=0.8,
                quality_score=0.8,
                learning_rate=0.1,
                specializations=[]
            )

        profile = self.agent_profiles[agent_id]

        # Update performance metrics
        profile.update_performance(task_metrics)

        # Update task type performance
        current_score = profile.task_types.get(task.task_type, 0.5)
        task_score = 1.0 if task_metrics.success else 0.0
        learning_rate = profile.learning_rate

        profile.task_types[task.task_type] = (
            current_score * (1 - learning_rate) + task_score * learning_rate
        )

        # Update complexity handling
        complexity_score = profile.complexity_handling.get(task.complexity, 0.5)
        profile.complexity_handling[task.complexity] = (
            complexity_score * (1 - learning_rate) + task_score * learning_rate
        )

        # Update resource efficiency
        for resource, utilization in task_metrics.resource_utilization.items():
            current_efficiency = profile.resource_efficiency.get(resource, 0.5)
            # Lower utilization with success = higher efficiency
            efficiency_score = (1.0 - utilization) * task_score if task_score > 0 else 0.0
            profile.resource_efficiency[resource] = (
                current_efficiency * (1 - learning_rate) + efficiency_score * learning_rate
            )

        # Update quality score
        profile.quality_score = (
            profile.quality_score * (1 - learning_rate) +
            task_metrics.quality_score * learning_rate
        )

    async def _learn_from_completion(self, task: IntelligentTask, task_metrics: TaskMetrics) -> None:
        """Learn from task completion."""
        # Update task preferences
        if task_metrics.success and task_metrics.quality_score > 0.8:
            if task_metrics.allocated_agent not in task.preferred_agents:
                # Add to preferred agents for similar tasks
                similar_tasks = [
                    t for t in self.task_queue
                    if t.task_type == task.task_type and t.complexity == task.complexity
                ]

                for similar_task in similar_tasks[:5]:  # Limit to 5 similar tasks
                    if task_metrics.allocated_agent not in similar_task.preferred_agents:
                        similar_task.preferred_agents.append(task_metrics.allocated_agent)

        elif not task_metrics.success or task_metrics.quality_score < 0.3:
            # Add to blacklisted agents for similar tasks
            similar_tasks = [
                t for t in self.task_queue
                if t.task_type == task.task_type and t.complexity == task.complexity
            ]

            for similar_task in similar_tasks[:5]:
                if task_metrics.allocated_agent not in similar_task.blacklisted_agents:
                    similar_task.blacklisted_agents.append(task_metrics.allocated_agent)

    async def _update_allocation_metrics(
        self,
        task: IntelligentTask,
        agent_id: str,
        allocation_time: float,
        success: bool
    ) -> None:
        """Update allocation metrics."""
        self.allocation_metrics['total_allocations'] += 1

        if success:
            self.allocation_metrics['successful_allocations'] += 1
        else:
            self.allocation_metrics['failed_allocations'] += 1

        # Update average allocation time
        total_allocations = self.allocation_metrics['total_allocations']
        current_avg = self.allocation_metrics['average_allocation_time']
        if total_allocations > 0:
            self.allocation_metrics['average_allocation_time'] = (
                (current_avg * (total_allocations - 1) + allocation_time) / total_allocations
            )

    async def _store_task_completion(self, task_metrics: TaskMetrics) -> None:
        """Store task completion in database."""
        db_path = self.config.get('db_path', 'task_allocation.db')

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT INTO task_allocations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                task_metrics.task_id,
                task_metrics.allocated_agent,
                task_metrics.allocation_time,
                task_metrics.completion_time,
                task_metrics.success,
                task_metrics.execution_duration,
                task_metrics.quality_score,
                json.dumps(task_metrics.resource_utilization),
                json.dumps({})
            ))
            conn.commit()

    def _compare_task_priority(self, task1: IntelligentTask, task2: IntelligentTask) -> bool:
        """Compare task priorities for queue ordering."""
        # Higher priority comes first
        if task1.priority.value != task2.priority.value:
            return task1.priority.value > task2.priority.value

        # If same priority, check deadline
        if task1.deadline and task2.deadline:
            return task1.deadline < task2.deadline
        elif task1.deadline:
            return True
        elif task2.deadline:
            return False

        # If no deadline, FIFO
        return task1.created_at < task2.created_at

    def _check_resource_compatibility(
        self,
        requirements: ResourceRequirements,
        agent: AgentInfo
    ) -> bool:
        """Check if agent can meet resource requirements."""
        if not agent.resource_allocation:
            return True  # Assume compatible if no allocation info

        allocation = agent.resource_allocation

        return (
            allocation.allocated_cpu >= requirements.cpu_cores and
            allocation.allocated_memory >= requirements.memory_mb and
            allocation.allocated_disk >= requirements.disk_mb and
            allocation.allocated_network >= requirements.network_mbps
        )

    def _check_capability_match(self, task: IntelligentTask, agent: AgentInfo) -> bool:
        """Check if agent capabilities match task requirements."""
        if not agent.registration.capabilities:
            return True  # Assume compatible if no capability info

        # Check if agent has any matching capabilities
        task_capabilities = task.context.get('required_capabilities', [])
        if not task_capabilities:
            return True

        return any(cap in agent.registration.capabilities for cap in task_capabilities)

    async def _calculate_capability_score(self, task: IntelligentTask, agent: AgentInfo) -> float:
        """Calculate capability match score."""
        if not agent.registration.capabilities:
            return 0.5  # Default score

        task_capabilities = task.context.get('required_capabilities', [])
        if not task_capabilities:
            return 0.8  # High score if no specific requirements

        # Calculate overlap
        agent_caps = set(agent.registration.capabilities)
        task_caps = set(task_capabilities)

        if not task_caps:
            return 0.8

        overlap = len(agent_caps & task_caps)
        return overlap / len(task_caps)

    async def _calculate_recommendation_score(
        self,
        agent_profile: AgentPerformanceProfile,
        task: IntelligentTask
    ) -> float:
        """Calculate recommendation score for a task-agent pair."""
        # Base performance score
        performance_score = agent_profile.get_performance_score(task.task_type, task.complexity)

        # Adjust for agent preference
        preference_bonus = 0.2 if agent_profile.agent_id in task.preferred_agents else 0.0

        # Adjust for workload
        workload_penalty = self.agent_workloads[agent_profile.agent_id] * 0.1

        # Adjust for deadline urgency
        deadline_bonus = 0.0
        if task.deadline:
            time_to_deadline = (task.deadline - datetime.now()).total_seconds()
            if time_to_deadline < 3600:  # Less than 1 hour
                deadline_bonus = 0.3
            elif time_to_deadline < 7200:  # Less than 2 hours
                deadline_bonus = 0.1

        total_score = performance_score + preference_bonus - workload_penalty + deadline_bonus
        return max(0.0, min(1.0, total_score))

    async def _analyze_strategy_performance(self, strategy: AllocationStrategy) -> Dict[str, float]:
        """Analyze performance of an allocation strategy."""
        # This would analyze historical allocation data
        # For now, return default scores
        return {
            'success_rate': 0.85,
            'average_allocation_time': 1.5,
            'resource_efficiency': 0.75,
            'agent_satisfaction': 0.80,
            'overall_score': 0.75
        }

    async def _identify_reassignable_tasks(self, agent_id: str) -> List[str]:
        """Identify tasks that can be reassigned from an overloaded agent."""
        # Find active tasks for this agent
        agent_tasks = [
            task_id for task_id, task in self.active_tasks.items()
            if task_id in [t.task_id for t in self.task_queue if hasattr(t, 'allocated_agent') and t.allocated_agent == agent_id]
        ]

        # Return tasks that can be reassigned (e.g., not started yet)
        return agent_tasks[:min(2, len(agent_tasks))]  # Limit reassignments

    async def _find_best_reassignment_agent(
        self,
        task_id: str,
        candidate_agents: List[str]
    ) -> Optional[str]:
        """Find the best agent to reassign a task to."""
        if not candidate_agents or task_id not in self.active_tasks:
            return None

        task = self.active_tasks[task_id]

        # Score candidate agents
        best_agent = None
        best_score = 0.0

        for agent_id in candidate_agents:
            if agent_id in self.agent_profiles:
                profile = self.agent_profiles[agent_id]
                score = profile.get_performance_score(task.task_type, task.complexity)

                if score > best_score:
                    best_score = score
                    best_agent = agent_id

        return best_agent

    async def _predict_execution_duration(
        self,
        task: IntelligentTask,
        agent_profile: AgentPerformanceProfile
    ) -> float:
        """Predict task execution duration for an agent."""
        # Base prediction from task estimation
        base_duration = task.estimated_duration

        # Adjust based on agent performance
        performance_factor = agent_profile.get_performance_score(task.task_type, task.complexity)

        # Better performance = faster execution
        adjusted_duration = base_duration * (2.0 - performance_factor)

        return max(30.0, adjusted_duration)  # Minimum 30 seconds

    async def _predict_success_probability(
        self,
        task: IntelligentTask,
        agent_profile: AgentPerformanceProfile
    ) -> float:
        """Predict probability of task success."""
        # Base probability from agent performance
        base_probability = agent_profile.get_performance_score(task.task_type, task.complexity)

        # Adjust based on agent reliability
        reliability_factor = agent_profile.reliability_score

        # Adjust based on task complexity
        complexity_penalty = (task.complexity.value - 1) * 0.1

        probability = base_probability * reliability_factor - complexity_penalty

        return max(0.1, min(0.95, probability))

    async def _predict_quality_score(
        self,
        task: IntelligentTask,
        agent_profile: AgentPerformanceProfile
    ) -> float:
        """Predict task quality score."""
        # Base quality from agent profile
        base_quality = agent_profile.quality_score

        # Adjust based on task complexity
        complexity_factor = 1.0 - (task.complexity.value - 1) * 0.15

        predicted_quality = base_quality * complexity_factor

        return max(0.1, min(1.0, predicted_quality))

    async def _predict_resource_utilization(
        self,
        task: IntelligentTask,
        agent_profile: AgentPerformanceProfile
    ) -> Dict[str, float]:
        """Predict resource utilization."""
        # Base utilization from task requirements
        base_utilization = {
            'cpu': min(1.0, task.requirements.cpu_cores * 0.4),
            'memory': min(1.0, task.requirements.memory_mb / 1024.0),
            'disk': min(1.0, task.requirements.disk_mb / 10240.0),
            'network': min(1.0, task.requirements.network_mbps / 100.0)
        }

        # Adjust based on agent efficiency
        predicted_utilization = {}
        for resource, base_util in base_utilization.items():
            efficiency = agent_profile.resource_efficiency.get(resource, 0.5)
            # Higher efficiency = lower utilization
            predicted_utilization[resource] = base_util * (1.0 - efficiency * 0.3)

        return predicted_utilization

    def _calculate_prediction_confidence(
        self,
        task: IntelligentTask,
        agent_profile: AgentPerformanceProfile
    ) -> float:
        """Calculate confidence in predictions."""
        # Base confidence from agent data quality
        base_confidence = 0.7

        # Adjust based on historical data availability
        if agent_profile.completed_tasks > 10:
            base_confidence += 0.1

        if len(agent_profile.recent_performance) > 5:
            base_confidence += 0.1

        # Adjust based on task type familiarity
        if task.task_type in agent_profile.task_types:
            base_confidence += 0.1

        return max(0.5, min(0.95, base_confidence))

    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get comprehensive allocation system summary."""
        return {
            'queue_size': len(self.task_queue),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'agent_profiles': len(self.agent_profiles),
            'allocation_metrics': self.allocation_metrics,
            'agent_workloads': dict(self.agent_workloads),
            'task_patterns': {k: len(v) for k, v in self.task_patterns.items()},
            'allocation_history_count': len(self.allocation_history)
        }
