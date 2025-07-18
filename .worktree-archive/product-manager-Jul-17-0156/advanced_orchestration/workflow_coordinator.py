"""
Enhanced Workflow Coordinator for multi-agent orchestration.

This module provides advanced workflow coordination capabilities including:
- Intelligent task routing based on agent specialization
- Dynamic dependency resolution and parallel execution
- Quality gate validation and integration points
- Adaptive performance optimization
- Real-time coordination metrics and monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict
import uuid
import json

from .models import (
    WorkflowDefinition, EnhancedTaskAssignment, AgentCapabilities,
    CoordinationMetrics, IntelligentRouting, QualityGate, WorkflowState,
    TaskDependency, TaskStatus, TaskPriority, AgentSpecialization,
    WorkflowType, DependencyType, AgentInfo, CoordinatorConfig,
    TaskDistributionException, CoordinatorException
)
from .multi_agent_coordinator import MultiAgentCoordinator


class WorkflowCoordinator:
    """
    Enhanced workflow coordinator for multi-agent orchestration.

    Provides advanced coordination capabilities including:
    - Intelligent task routing and load balancing
    - Dynamic dependency resolution and parallel execution
    - Quality gate validation and integration management
    - Adaptive performance optimization and learning
    - Real-time monitoring and metrics collection
    """

    def __init__(self, config: CoordinatorConfig):
        """
        Initialize the WorkflowCoordinator.

        Args:
            config: Configuration for the coordinator
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Core coordinator
        self.multi_agent_coordinator = MultiAgentCoordinator(config)

        # Workflow state
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.enhanced_tasks: Dict[str, EnhancedTaskAssignment] = {}
        self.agent_capabilities: Dict[str, AgentCapabilities] = {}
        self.quality_gates: Dict[str, QualityGate] = {}

        # Coordination
        self.task_dependencies: Dict[str, List[TaskDependency]] = defaultdict(list)
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.parallel_execution_groups: Dict[str, List[str]] = defaultdict(list)

        # Intelligence
        self.intelligent_routing = IntelligentRouting()
        self.performance_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.coordination_metrics: Dict[str, CoordinationMetrics] = {}

        # Monitoring
        self.running = False
        self.coordination_stats = {
            'workflows_executed': 0,
            'parallel_tasks_executed': 0,
            'quality_gates_passed': 0,
            'quality_gates_failed': 0,
            'dependency_violations': 0,
            'coordination_efficiency': 0.0
        }

        self.logger.info("WorkflowCoordinator initialized with intelligent routing")

    async def start(self) -> None:
        """Start the workflow coordinator."""
        self.running = True
        await self.multi_agent_coordinator.start()

        # Start background tasks
        asyncio.create_task(self._coordination_monitor())
        asyncio.create_task(self._quality_gate_monitor())
        asyncio.create_task(self._performance_optimizer())

        self.logger.info("WorkflowCoordinator started")

    async def stop(self) -> None:
        """Stop the workflow coordinator."""
        self.running = False
        await self.multi_agent_coordinator.stop()
        self.logger.info("WorkflowCoordinator stopped")

    async def register_workflow(self, workflow_def: WorkflowDefinition) -> bool:
        """
        Register a new workflow definition.

        Args:
            workflow_def: Workflow definition to register

        Returns:
            bool: True if registration successful
        """
        try:
            # Validate workflow definition
            if not await self._validate_workflow_definition(workflow_def):
                return False

            # Build dependency graph
            await self._build_dependency_graph(workflow_def)

            # Register workflow
            self.workflow_definitions[workflow_def.workflow_id] = workflow_def

            self.logger.info(f"Workflow {workflow_def.workflow_id} registered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register workflow {workflow_def.workflow_id}: {e}")
            return False

    async def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None) -> WorkflowState:
        """
        Execute a registered workflow.

        Args:
            workflow_id: ID of the workflow to execute
            context: Additional context for workflow execution

        Returns:
            WorkflowState: Current workflow state

        Raises:
            CoordinatorException: If workflow execution fails
        """
        try:
            if workflow_id not in self.workflow_definitions:
                raise CoordinatorException(f"Workflow {workflow_id} not found")

            workflow_def = self.workflow_definitions[workflow_id]

            # Initialize workflow state
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                status="initializing",
                progress_percentage=0.0,
                active_tasks=[],
                completed_tasks=[],
                failed_tasks=[],
                blocked_tasks=[],
                quality_gates=[],
                coordination_metrics=CoordinationMetrics(
                    workflow_completion_rate=0.0,
                    parallel_efficiency=0.0,
                    task_distribution_balance=0.0,
                    quality_consistency=0.0,
                    dependency_resolution_time=0.0,
                    agent_utilization={},
                    coordination_overhead=0.0
                ),
                estimated_completion=datetime.now() + timedelta(minutes=workflow_def.estimated_duration)
            )

            self.active_workflows[workflow_id] = workflow_state

            # Create enhanced task assignments
            await self._create_enhanced_task_assignments(workflow_def, context or {})

            # Execute workflow
            await self._execute_workflow_phases(workflow_id)

            # Update statistics
            self.coordination_stats['workflows_executed'] += 1

            self.logger.info(f"Workflow {workflow_id} execution initiated")
            return workflow_state

        except Exception as e:
            self.logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            raise CoordinatorException(f"Workflow execution failed: {e}")

    async def register_agent_capabilities(self, agent_id: str, capabilities: AgentCapabilities) -> bool:
        """
        Register agent capabilities for intelligent routing.

        Args:
            agent_id: Agent ID
            capabilities: Agent capabilities

        Returns:
            bool: True if registration successful
        """
        try:
            self.agent_capabilities[agent_id] = capabilities
            self.logger.info(f"Agent {agent_id} capabilities registered: {capabilities.specialization}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register agent capabilities for {agent_id}: {e}")
            return False

    async def update_task_progress(self, task_id: str, progress: float, quality_score: float = 0.0) -> bool:
        """
        Update task progress and quality metrics.

        Args:
            task_id: Task ID
            progress: Progress percentage (0.0 to 1.0)
            quality_score: Quality score (0.0 to 1.0)

        Returns:
            bool: True if update successful
        """
        try:
            if task_id not in self.enhanced_tasks:
                return False

            task = self.enhanced_tasks[task_id]
            task.progress_percentage = progress * 100
            task.quality_score = quality_score

            # Update workflow state
            workflow_state = self.active_workflows.get(task.workflow_id)
            if workflow_state:
                await self._update_workflow_progress(workflow_state)

            self.logger.debug(f"Task {task_id} progress updated: {progress:.1%}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update task progress for {task_id}: {e}")
            return False

    async def validate_quality_gate(self, gate_id: str) -> bool:
        """
        Validate a quality gate.

        Args:
            gate_id: Quality gate ID

        Returns:
            bool: True if quality gate passed
        """
        try:
            if gate_id not in self.quality_gates:
                return False

            gate = self.quality_gates[gate_id]

            # Check required tasks completion
            required_tasks_completed = all(
                task_id in self.enhanced_tasks and
                self.enhanced_tasks[task_id].status == TaskStatus.COMPLETED
                for task_id in gate.required_tasks
            )

            if not required_tasks_completed:
                return False

            # Check quality threshold
            if gate.quality_threshold > 0:
                avg_quality = sum(
                    self.enhanced_tasks[task_id].quality_score
                    for task_id in gate.required_tasks
                ) / len(gate.required_tasks)

                if avg_quality < gate.quality_threshold:
                    self.coordination_stats['quality_gates_failed'] += 1
                    return False

            self.coordination_stats['quality_gates_passed'] += 1
            self.logger.info(f"Quality gate {gate_id} passed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to validate quality gate {gate_id}: {e}")
            return False

    async def get_coordination_metrics(self, workflow_id: str) -> Optional[CoordinationMetrics]:
        """
        Get coordination metrics for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            CoordinationMetrics: Coordination metrics or None if not found
        """
        return self.coordination_metrics.get(workflow_id)

    async def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        Get current workflow state.

        Args:
            workflow_id: Workflow ID

        Returns:
            WorkflowState: Current workflow state or None if not found
        """
        return self.active_workflows.get(workflow_id)

    async def _validate_workflow_definition(self, workflow_def: WorkflowDefinition) -> bool:
        """Validate workflow definition."""
        try:
            # Check tasks exist
            if not workflow_def.tasks:
                self.logger.error(f"Workflow {workflow_def.workflow_id} has no tasks")
                return False

            # Check dependencies are valid
            task_set = set(workflow_def.tasks)
            for dep in workflow_def.dependencies:
                if dep.task_id not in task_set or dep.depends_on not in task_set:
                    self.logger.error(f"Invalid dependency in workflow {workflow_def.workflow_id}")
                    return False

            # Check for circular dependencies
            if await self._has_circular_dependencies(workflow_def):
                self.logger.error(f"Circular dependencies detected in workflow {workflow_def.workflow_id}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Workflow validation failed: {e}")
            return False

    async def _has_circular_dependencies(self, workflow_def: WorkflowDefinition) -> bool:
        """Check for circular dependencies in workflow."""
        graph = defaultdict(set)

        for dep in workflow_def.dependencies:
            graph[dep.task_id].add(dep.depends_on)

        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for task in workflow_def.tasks:
            if task not in visited:
                if has_cycle(task):
                    return True

        return False

    async def _build_dependency_graph(self, workflow_def: WorkflowDefinition) -> None:
        """Build dependency graph for workflow."""
        workflow_id = workflow_def.workflow_id

        # Clear existing dependencies
        self.task_dependencies[workflow_id] = []
        self.dependency_graph[workflow_id] = defaultdict(set)

        # Build dependency mappings
        for dep in workflow_def.dependencies:
            self.task_dependencies[workflow_id].append(dep)
            self.dependency_graph[workflow_id][dep.task_id].add(dep.depends_on)

        # Identify parallel execution groups
        await self._identify_parallel_groups(workflow_def)

    async def _identify_parallel_groups(self, workflow_def: WorkflowDefinition) -> None:
        """Identify tasks that can be executed in parallel."""
        workflow_id = workflow_def.workflow_id
        self.parallel_execution_groups[workflow_id] = []

        if not workflow_def.parallel_execution:
            return

        # Group tasks by dependency level
        dependency_levels = defaultdict(list)
        task_levels = {}

        # Calculate dependency levels
        for task in workflow_def.tasks:
            level = await self._calculate_task_level(task, workflow_id)
            dependency_levels[level].append(task)
            task_levels[task] = level

        # Create parallel groups
        for level, tasks in dependency_levels.items():
            if len(tasks) > 1:
                self.parallel_execution_groups[workflow_id].append(tasks)

    async def _calculate_task_level(self, task_id: str, workflow_id: str) -> int:
        """Calculate dependency level for a task."""
        dependencies = self.dependency_graph[workflow_id].get(task_id, set())

        if not dependencies:
            return 0

        max_level = 0
        for dep in dependencies:
            dep_level = await self._calculate_task_level(dep, workflow_id)
            max_level = max(max_level, dep_level + 1)

        return max_level

    async def _create_enhanced_task_assignments(self, workflow_def: WorkflowDefinition, context: Dict[str, Any]) -> None:
        """Create enhanced task assignments for workflow."""
        workflow_id = workflow_def.workflow_id

        for task_id in workflow_def.tasks:
            # Get task dependencies
            task_deps = [dep for dep in workflow_def.dependencies if dep.task_id == task_id]

            # Determine agent specialization
            agent_spec = workflow_def.agent_assignments.get(task_id, AgentSpecialization.GENERAL)

            # Create enhanced task assignment
            enhanced_task = EnhancedTaskAssignment(
                task_id=task_id,
                workflow_id=workflow_id,
                agent_id="",  # Will be assigned during execution
                agent_specialization=agent_spec,
                task_data=context.get(task_id, {}),
                priority=TaskPriority.MEDIUM,
                dependencies=task_deps,
                estimated_duration=60,  # Default 1 hour
                status=TaskStatus.PENDING if not task_deps else TaskStatus.WAITING_DEPENDENCY
            )

            self.enhanced_tasks[task_id] = enhanced_task

    async def _execute_workflow_phases(self, workflow_id: str) -> None:
        """Execute workflow phases with intelligent coordination."""
        workflow_state = self.active_workflows[workflow_id]
        workflow_state.status = "executing"

        # Execute parallel groups
        for group in self.parallel_execution_groups[workflow_id]:
            await self._execute_parallel_group(workflow_id, group)

        # Execute remaining tasks
        await self._execute_remaining_tasks(workflow_id)

        # Validate final quality gates
        await self._validate_workflow_quality_gates(workflow_id)

        # Update final state
        workflow_state.status = "completed"
        workflow_state.progress_percentage = 100.0

    async def _execute_parallel_group(self, workflow_id: str, task_group: List[str]) -> None:
        """Execute a group of tasks in parallel."""
        workflow_state = self.active_workflows[workflow_id]

        # Check if tasks are ready
        ready_tasks = []
        for task_id in task_group:
            if await self._is_task_ready(task_id):
                ready_tasks.append(task_id)

        if not ready_tasks:
            return

        # Execute tasks in parallel
        tasks = []
        for task_id in ready_tasks:
            task = asyncio.create_task(self._execute_single_task(task_id))
            tasks.append(task)

        # Wait for completion
        await asyncio.gather(*tasks)

        # Update workflow state
        workflow_state.active_tasks = [t for t in workflow_state.active_tasks if t not in ready_tasks]
        workflow_state.completed_tasks.extend(ready_tasks)

        self.coordination_stats['parallel_tasks_executed'] += len(ready_tasks)

    async def _execute_remaining_tasks(self, workflow_id: str) -> None:
        """Execute remaining tasks that weren't in parallel groups."""
        workflow_def = self.workflow_definitions[workflow_id]

        for task_id in workflow_def.tasks:
            if task_id not in self.active_workflows[workflow_id].completed_tasks:
                if await self._is_task_ready(task_id):
                    await self._execute_single_task(task_id)

    async def _execute_single_task(self, task_id: str) -> None:
        """Execute a single task with intelligent agent selection."""
        try:
            enhanced_task = self.enhanced_tasks[task_id]

            # Select best agent for task
            agent_id = await self._select_agent_for_task(enhanced_task)
            if not agent_id:
                enhanced_task.status = TaskStatus.BLOCKED
                return

            # Assign task to agent
            enhanced_task.agent_id = agent_id
            enhanced_task.status = TaskStatus.ASSIGNED

            # Execute task through multi-agent coordinator
            task_assignment = await self.multi_agent_coordinator.distribute_task(
                enhanced_task.task_data,
                enhanced_task.priority.value
            )

            if task_assignment:
                enhanced_task.status = TaskStatus.IN_PROGRESS

                # Monitor task completion
                await self._monitor_task_completion(task_id, task_assignment.task_id)

        except Exception as e:
            self.logger.error(f"Failed to execute task {task_id}: {e}")
            self.enhanced_tasks[task_id].status = TaskStatus.FAILED

    async def _select_agent_for_task(self, task: EnhancedTaskAssignment) -> Optional[str]:
        """Select best agent for task using intelligent routing."""
        try:
            # Get available agents
            coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()
            available_agents = [
                agent_id for agent_id, agent_info in coordinator_state.active_agents.items()
                if agent_info.status.value == "healthy"
            ]

            if not available_agents:
                return None

            # Filter by specialization
            specialized_agents = []
            for agent_id in available_agents:
                if agent_id in self.agent_capabilities:
                    capabilities = self.agent_capabilities[agent_id]
                    if capabilities.specialization == task.agent_specialization:
                        specialized_agents.append(agent_id)

            # Use specialized agents if available
            candidates = specialized_agents if specialized_agents else available_agents

            if not candidates:
                return None

            # Intelligent selection based on performance history
            if self.intelligent_routing.use_ml_prediction:
                return await self._ml_agent_selection(task, candidates)
            else:
                return await self._heuristic_agent_selection(task, candidates)

        except Exception as e:
            self.logger.error(f"Failed to select agent for task {task.task_id}: {e}")
            return None

    async def _ml_agent_selection(self, task: EnhancedTaskAssignment, candidates: List[str]) -> str:
        """Machine learning based agent selection."""
        # Simplified ML selection - in production, this would use actual ML models
        best_agent = None
        best_score = 0.0

        for agent_id in candidates:
            score = 0.0

            # Consider agent capabilities
            if agent_id in self.agent_capabilities:
                capabilities = self.agent_capabilities[agent_id]
                score += capabilities.skill_level * 0.4
                score += capabilities.adaptation_score * 0.3

            # Consider performance history
            if agent_id in self.performance_history:
                history = self.performance_history[agent_id]
                if history:
                    avg_performance = sum(h.get('performance', 0.5) for h in history) / len(history)
                    score += avg_performance * 0.3

            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent or candidates[0]

    async def _heuristic_agent_selection(self, task: EnhancedTaskAssignment, candidates: List[str]) -> str:
        """Heuristic-based agent selection."""
        # Select agent with least active tasks
        coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()

        return min(candidates, key=lambda agent_id:
                  coordinator_state.active_agents[agent_id].active_tasks)

    async def _is_task_ready(self, task_id: str) -> bool:
        """Check if task is ready for execution."""
        if task_id not in self.enhanced_tasks:
            return False

        task = self.enhanced_tasks[task_id]

        # Check dependencies
        for dep in task.dependencies:
            if dep.depends_on not in self.enhanced_tasks:
                return False

            dep_task = self.enhanced_tasks[dep.depends_on]
            if dep_task.status != dep.required_status:
                return False

        return True

    async def _monitor_task_completion(self, enhanced_task_id: str, coordinator_task_id: str) -> None:
        """Monitor task completion and update state."""
        # This would be integrated with the multi-agent coordinator's task completion
        # For now, we'll simulate completion
        await asyncio.sleep(1)  # Simulate task execution time

        # Update task status
        if enhanced_task_id in self.enhanced_tasks:
            self.enhanced_tasks[enhanced_task_id].status = TaskStatus.COMPLETED
            self.enhanced_tasks[enhanced_task_id].progress_percentage = 100.0

    async def _update_workflow_progress(self, workflow_state: WorkflowState) -> None:
        """Update workflow progress based on task completion."""
        workflow_id = workflow_state.workflow_id
        workflow_def = self.workflow_definitions[workflow_id]

        total_tasks = len(workflow_def.tasks)
        completed_tasks = len(workflow_state.completed_tasks)

        workflow_state.progress_percentage = (completed_tasks / total_tasks) * 100
        workflow_state.last_updated = datetime.now()

    async def _validate_workflow_quality_gates(self, workflow_id: str) -> None:
        """Validate all quality gates for workflow."""
        workflow_gates = [gate for gate in self.quality_gates.values()
                         if gate.workflow_id == workflow_id]

        for gate in workflow_gates:
            await self.validate_quality_gate(gate.gate_id)

    async def _coordination_monitor(self) -> None:
        """Background coordination monitoring."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Update coordination metrics
                for workflow_id in self.active_workflows:
                    await self._calculate_coordination_metrics(workflow_id)

            except Exception as e:
                self.logger.error(f"Coordination monitoring error: {e}")

    async def _quality_gate_monitor(self) -> None:
        """Background quality gate monitoring."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Check quality gates
                for gate_id in self.quality_gates:
                    await self.validate_quality_gate(gate_id)

            except Exception as e:
                self.logger.error(f"Quality gate monitoring error: {e}")

    async def _performance_optimizer(self) -> None:
        """Background performance optimization."""
        while self.running:
            try:
                await asyncio.sleep(120)  # Optimize every 2 minutes

                # Optimize agent capabilities and routing
                await self._optimize_agent_routing()

            except Exception as e:
                self.logger.error(f"Performance optimization error: {e}")

    async def _calculate_coordination_metrics(self, workflow_id: str) -> None:
        """Calculate coordination metrics for workflow."""
        try:
            workflow_state = self.active_workflows[workflow_id]

            # Calculate metrics
            metrics = CoordinationMetrics(
                workflow_completion_rate=workflow_state.progress_percentage / 100,
                parallel_efficiency=self._calculate_parallel_efficiency(workflow_id),
                task_distribution_balance=self._calculate_distribution_balance(workflow_id),
                quality_consistency=self._calculate_quality_consistency(workflow_id),
                dependency_resolution_time=self._calculate_dependency_resolution_time(workflow_id),
                agent_utilization=await self._calculate_agent_utilization(workflow_id),
                coordination_overhead=self._calculate_coordination_overhead(workflow_id)
            )

            self.coordination_metrics[workflow_id] = metrics
            workflow_state.coordination_metrics = metrics

        except Exception as e:
            self.logger.error(f"Failed to calculate coordination metrics for {workflow_id}: {e}")

    def _calculate_parallel_efficiency(self, workflow_id: str) -> float:
        """Calculate parallel execution efficiency."""
        # Simplified calculation - in production, this would be more sophisticated
        return min(1.0, self.coordination_stats['parallel_tasks_executed'] / max(1, len(self.parallel_execution_groups[workflow_id])))

    def _calculate_distribution_balance(self, workflow_id: str) -> float:
        """Calculate task distribution balance."""
        # Simplified calculation
        return 0.8  # Placeholder

    def _calculate_quality_consistency(self, workflow_id: str) -> float:
        """Calculate quality consistency across tasks."""
        workflow_tasks = [task for task in self.enhanced_tasks.values()
                         if task.workflow_id == workflow_id]

        if not workflow_tasks:
            return 0.0

        quality_scores = [task.quality_score for task in workflow_tasks if task.quality_score > 0]
        if not quality_scores:
            return 0.0

        return sum(quality_scores) / len(quality_scores)

    def _calculate_dependency_resolution_time(self, workflow_id: str) -> float:
        """Calculate average dependency resolution time."""
        # Simplified calculation
        return 30.0  # Placeholder

    async def _calculate_agent_utilization(self, workflow_id: str) -> Dict[str, float]:
        """Calculate agent utilization for workflow."""
        coordinator_state = await self.multi_agent_coordinator.get_coordinator_state()

        utilization = {}
        for agent_id, agent_info in coordinator_state.active_agents.items():
            if agent_info.resource_allocation and agent_info.current_usage:
                utilization[agent_id] = (
                    agent_info.current_usage.cpu_percent +
                    agent_info.current_usage.memory_percent
                ) / 2.0

        return utilization

    def _calculate_coordination_overhead(self, workflow_id: str) -> float:
        """Calculate coordination overhead."""
        # Simplified calculation
        return 0.1  # Placeholder

    async def _optimize_agent_routing(self) -> None:
        """Optimize agent routing based on performance history."""
        try:
            # Update agent capabilities based on performance
            for agent_id, capabilities in self.agent_capabilities.items():
                if agent_id in self.performance_history:
                    history = self.performance_history[agent_id]
                    if history:
                        avg_performance = sum(h.get('performance', 0.5) for h in history) / len(history)

                        # Adapt skill level based on performance
                        if self.intelligent_routing.learning_enabled:
                            adaptation = (avg_performance - 0.5) * capabilities.learning_rate
                            capabilities.skill_level = max(0.0, min(1.0, capabilities.skill_level + adaptation))
                            capabilities.adaptation_score = avg_performance

            self.logger.debug("Agent routing optimization completed")

        except Exception as e:
            self.logger.error(f"Agent routing optimization failed: {e}")

    def get_coordination_statistics(self) -> Dict[str, Any]:
        """Get current coordination statistics."""
        return {
            **self.coordination_stats,
            'active_workflows': len(self.active_workflows),
            'total_tasks': len(self.enhanced_tasks),
            'registered_agents': len(self.agent_capabilities),
            'quality_gates': len(self.quality_gates)
        }
