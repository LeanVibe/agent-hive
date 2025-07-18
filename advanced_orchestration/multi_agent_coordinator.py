"""
Multi-Agent Coordinator for managing multiple agents in a distributed system.

This module provides the core coordination capabilities for managing multiple
agents, including registration, task distribution, load balancing, and fault tolerance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import uuid

from .models import (
    AgentInfo, AgentStatus, AgentRegistration, TaskAssignment, TaskStatus,
    CoordinatorConfig, CoordinatorState, LoadBalancingStrategy, AgentRegistrationException, TaskDistributionException, ResourceUsage, LoadBalancingMetrics, ScalingMetrics
)
from .resource_manager import ResourceManager
from .scaling_manager import ScalingManager


class MultiAgentCoordinator:
    """
    Multi-Agent Coordinator for managing agent lifecycle and task distribution.

    This class provides the core coordination capabilities including:
    - Agent registration and discovery
    - Task distribution and load balancing
    - Health monitoring and fault tolerance
    - Resource management and optimization
    - Auto-scaling based on demand
    """

    def __init__(self, config: CoordinatorConfig):
        """
        Initialize the MultiAgentCoordinator.

        Args:
            config: Configuration for the coordinator
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Core state
        self.agents: Dict[str, AgentInfo] = {}
        self.pending_tasks: List[TaskAssignment] = []
        self.assigned_tasks: Dict[str, TaskAssignment] = {}
        self.task_history: List[TaskAssignment] = []

        # Load balancing
        self.current_round_robin_index = 0
        self.agent_weights: Dict[str, float] = {}
        self.load_metrics: Dict[str, List[float]] = defaultdict(list)

        # Monitoring
        self.running = False
        self.startup_time = datetime.now()
        self.last_health_check = datetime.now()
        self.last_load_balance = datetime.now()

        # Components
        self.resource_manager = ResourceManager(config.resource_limits)
        self.scaling_manager = ScalingManager(config.resource_limits)

        # Metrics
        self.performance_metrics: Dict[str, Any] = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'agent_failures': 0,
            'scaling_events': 0,
            'load_balancing_events': 0
        }

        self.logger.info(f"MultiAgentCoordinator initialized with config: {config}")

    async def start(self) -> None:
        """Start the coordinator and begin monitoring."""
        self.running = True
        self.logger.info("MultiAgentCoordinator started")

        # Start background tasks
        asyncio.create_task(self._health_monitor())
        asyncio.create_task(self._load_balancer())
        asyncio.create_task(self._scaling_monitor())

    async def stop(self) -> None:
        """Stop the coordinator and cleanup resources."""
        self.running = False
        self.logger.info("MultiAgentCoordinator stopped")

    async def register_agent(self, registration: AgentRegistration) -> bool:
        """
        Register a new agent with the coordinator.

        Args:
            registration: Agent registration data

        Returns:
            bool: True if registration successful

        Raises:
            AgentRegistrationException: If registration fails
        """
        try:
            agent_id = registration.agent_id

            # Check if agent already exists
            if agent_id in self.agents:
                raise AgentRegistrationException(f"Agent {agent_id} already registered")

            # Check if we've reached the maximum number of agents
            if len(self.agents) >= self.config.max_agents:
                raise AgentRegistrationException(f"Maximum number of agents ({self.config.max_agents}) reached")

            # Allocate resources
            allocation = await self.resource_manager.allocate_resources(
                agent_id, registration.resource_requirements
            )

            # Create agent info
            agent_info = AgentInfo(
                agent_id=agent_id,
                status=AgentStatus.HEALTHY,
                registration=registration,
                resource_allocation=allocation,
                active_tasks=0,
                error_count=0,
                last_heartbeat=datetime.now()
            )

            # Register agent
            self.agents[agent_id] = agent_info
            self.agent_weights[agent_id] = 1.0

            self.logger.info(f"Agent {agent_id} registered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register agent {registration.agent_id}: {e}")
            raise AgentRegistrationException(f"Registration failed: {e}")

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the coordinator.

        Args:
            agent_id: ID of the agent to unregister

        Returns:
            bool: True if unregistration successful
        """
        try:
            if agent_id not in self.agents:
                self.logger.warning(f"Agent {agent_id} not found for unregistration")
                return False

            agent_info = self.agents[agent_id]

            # Reassign active tasks
            await self._reassign_agent_tasks(agent_id)

            # Deallocate resources
            await self.resource_manager.deallocate_resources(agent_id)

            # Remove agent
            del self.agents[agent_id]
            if agent_id in self.agent_weights:
                del self.agent_weights[agent_id]

            self.logger.info(f"Agent {agent_id} unregistered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def distribute_task(self, task_data: Dict[str, Any], priority: int = 5) -> Optional[TaskAssignment]:
        """
        Distribute a task to the most suitable agent.

        Args:
            task_data: Task data to be processed
            priority: Task priority (1-10, higher is more important)

        Returns:
            TaskAssignment: Assignment details if successful, None otherwise

        Raises:
            TaskDistributionException: If task distribution fails
        """
        try:
            # Find suitable agent
            agent_id = await self._select_agent_for_task(task_data, priority)
            if not agent_id:
                # Add to pending tasks if no agent available
                task_assignment = TaskAssignment(
                    task_id=str(uuid.uuid4()),
                    agent_id="",
                    task_data=task_data,
                    priority=priority,
                    status=TaskStatus.PENDING
                )
                self.pending_tasks.append(task_assignment)
                self.logger.info(f"Task {task_assignment.task_id} added to pending queue")
                return task_assignment

            # Create task assignment
            task_assignment = TaskAssignment(
                task_id=str(uuid.uuid4()),
                agent_id=agent_id,
                task_data=task_data,
                priority=priority,
                status=TaskStatus.ASSIGNED
            )

            # Update agent info
            self.agents[agent_id].active_tasks += 1
            self.assigned_tasks[task_assignment.task_id] = task_assignment

            self.logger.info(f"Task {task_assignment.task_id} assigned to agent {agent_id}")
            return task_assignment

        except Exception as e:
            self.logger.error(f"Failed to distribute task: {e}")
            raise TaskDistributionException(f"Task distribution failed: {e}")

    async def complete_task(self, task_id: str, success: bool = True) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: ID of the completed task
            success: Whether task completed successfully

        Returns:
            bool: True if task completion processed successfully
        """
        try:
            if task_id not in self.assigned_tasks:
                self.logger.warning(f"Task {task_id} not found in assigned tasks")
                return False

            task_assignment = self.assigned_tasks[task_id]
            agent_id = task_assignment.agent_id

            # Update task status
            task_assignment.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

            # Update agent info
            if agent_id in self.agents:
                self.agents[agent_id].active_tasks -= 1
                if not success:
                    self.agents[agent_id].error_count += 1

            # Move to history
            self.task_history.append(task_assignment)
            del self.assigned_tasks[task_id]

            # Update metrics
            if success:
                self.performance_metrics['tasks_completed'] += 1
            else:
                self.performance_metrics['tasks_failed'] += 1

            self.logger.info(f"Task {task_id} completed {'successfully' if success else 'with failure'}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    async def get_agent_status(self, agent_id: str) -> Optional[AgentInfo]:
        """
        Get the current status of an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            AgentInfo: Agent information if found, None otherwise
        """
        return self.agents.get(agent_id)

    async def get_coordinator_state(self) -> CoordinatorState:
        """
        Get the current state of the coordinator.

        Returns:
            CoordinatorState: Current coordinator state
        """
        # Calculate resource usage
        resource_usage = await self.resource_manager.get_resource_usage()

        # Calculate scaling metrics
        scaling_metrics = await self._calculate_scaling_metrics()

        # Calculate load balancing metrics
        load_balancing_metrics = await self._calculate_load_balancing_metrics()

        return CoordinatorState(
            active_agents=self.agents.copy(),
            pending_tasks=self.pending_tasks.copy(),
            assigned_tasks=self.assigned_tasks.copy(),
            resource_usage=resource_usage,
            scaling_metrics=scaling_metrics,
            load_balancing_metrics=load_balancing_metrics
        )

    async def rebalance_load(self) -> None:
        """Rebalance load across agents."""
        try:
            self.logger.info("Starting load rebalancing")

            # Process pending tasks
            await self._process_pending_tasks()

            # Update load balancing metrics
            await self._update_load_metrics()

            # Adjust agent weights based on performance
            await self._adjust_agent_weights()

            self.performance_metrics['load_balancing_events'] += 1
            self.last_load_balance = datetime.now()

            self.logger.info("Load rebalancing completed")

        except Exception as e:
            self.logger.error(f"Load rebalancing failed: {e}")

    async def handle_agent_failure(self, agent_id: str) -> None:
        """
        Handle agent failure and recovery.

        Args:
            agent_id: ID of the failed agent
        """
        try:
            if agent_id not in self.agents:
                return

            agent_info = self.agents[agent_id]
            agent_info.status = AgentStatus.UNHEALTHY
            agent_info.error_count += 1

            # Reassign active tasks
            await self._reassign_agent_tasks(agent_id)

            # Check if agent should be removed
            if agent_info.error_count >= self.config.failure_threshold:
                self.logger.warning(f"Agent {agent_id} exceeded failure threshold, removing")
                await self.unregister_agent(agent_id)

            self.performance_metrics['agent_failures'] += 1

        except Exception as e:
            self.logger.error(f"Failed to handle agent failure for {agent_id}: {e}")

    async def _select_agent_for_task(self, task_data: Dict[str, Any], priority: int) -> Optional[str]:
        """
        Select the best agent for a task based on the load balancing strategy.

        Args:
            task_data: Task data
            priority: Task priority

        Returns:
            str: Selected agent ID or None if no suitable agent
        """
        healthy_agents = [
            agent_id for agent_id, agent in self.agents.items()
            if agent.status == AgentStatus.HEALTHY
        ]

        if not healthy_agents:
            return None

        strategy = self.config.load_balancing_strategy

        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._select_round_robin(healthy_agents)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._select_least_connections(healthy_agents)
        elif strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return await self._select_resource_based(healthy_agents)
        elif strategy == LoadBalancingStrategy.WEIGHTED:
            return self._select_weighted(healthy_agents)
        else:
            return healthy_agents[0]

    def _select_round_robin(self, agents: List[str]) -> Optional[str]:
        """Select agent using round-robin strategy."""
        if not agents:
            return None

        selected = agents[self.current_round_robin_index % len(agents)]
        self.current_round_robin_index += 1
        return selected

    def _select_least_connections(self, agents: List[str]) -> Optional[str]:
        """Select agent with least active tasks."""
        if not agents:
            return None

        return min(agents, key=lambda a: self.agents[a].active_tasks)

    async def _select_resource_based(self, agents: List[str]) -> Optional[str]:
        """Select agent based on resource utilization."""
        if not agents:
            return None

        # Get resource usage for each agent
        agent_scores = []
        for agent_id in agents:
            agent_info = self.agents[agent_id]
            if agent_info.current_usage:
                # Calculate resource score (lower is better)
                score = (
                    agent_info.current_usage.cpu_percent * 0.4 +
                    agent_info.current_usage.memory_percent * 0.3 +
                    agent_info.current_usage.disk_percent * 0.2 +
                    agent_info.current_usage.network_percent * 0.1
                )
                agent_scores.append((agent_id, score))

        if not agent_scores:
            return agents[0]

        # Return agent with lowest resource utilization
        return min(agent_scores, key=lambda x: x[1])[0]

    def _select_weighted(self, agents: List[str]) -> Optional[str]:
        """Select agent based on weights."""
        if not agents:
            return None

        # Select agent with highest weight
        return max(agents, key=lambda a: self.agent_weights.get(a, 1.0))

    async def _reassign_agent_tasks(self, agent_id: str) -> None:
        """Reassign tasks from a failed agent."""
        tasks_to_reassign = [
            task for task in self.assigned_tasks.values()
            if task.agent_id == agent_id
        ]

        for task in tasks_to_reassign:
            # Remove from assigned tasks
            del self.assigned_tasks[task.task_id]

            # Reset task status
            task.status = TaskStatus.PENDING
            task.agent_id = ""

            # Add back to pending tasks
            self.pending_tasks.append(task)

            self.logger.info(f"Task {task.task_id} reassigned from failed agent {agent_id}")

    async def _process_pending_tasks(self) -> None:
        """Process pending tasks and assign them to available agents."""
        if not self.pending_tasks:
            return

        # Sort pending tasks by priority
        self.pending_tasks.sort(key=lambda t: t.priority, reverse=True)

        processed_tasks = []
        for task in self.pending_tasks:
            agent_id = await self._select_agent_for_task(task.task_data, task.priority)
            if agent_id:
                task.agent_id = agent_id
                task.status = TaskStatus.ASSIGNED
                task.assignment_time = datetime.now()

                # Update agent info
                self.agents[agent_id].active_tasks += 1
                self.assigned_tasks[task.task_id] = task
                processed_tasks.append(task)

        # Remove processed tasks from pending
        for task in processed_tasks:
            self.pending_tasks.remove(task)

    async def _update_load_metrics(self) -> None:
        """Update load balancing metrics."""
        for agent_id, agent_info in self.agents.items():
            if len(self.load_metrics[agent_id]) >= 100:
                self.load_metrics[agent_id].pop(0)
            self.load_metrics[agent_id].append(agent_info.active_tasks)

    async def _adjust_agent_weights(self) -> None:
        """Adjust agent weights based on performance."""
        for agent_id, agent_info in self.agents.items():
            # Calculate performance score
            if agent_info.error_count > 0:
                error_rate = agent_info.error_count / max(1, len(self.task_history))
                weight = max(0.1, 1.0 - error_rate)
            else:
                weight = 1.0

            self.agent_weights[agent_id] = weight

    async def _calculate_scaling_metrics(self) -> ScalingMetrics:
        """Calculate scaling metrics."""
        current_agents = len([a for a in self.agents.values() if a.status == AgentStatus.HEALTHY])
        queue_depth = len(self.pending_tasks)

        # Calculate average response time
        recent_tasks = self.task_history[-100:] if self.task_history else []
        avg_response_time = 0.0
        if recent_tasks:
            response_times = [
                (task.assignment_time - task.assignment_time).total_seconds()
                for task in recent_tasks
            ]
            avg_response_time = sum(response_times) / len(response_times)

        # Calculate resource utilization
        resource_usage = await self.resource_manager.get_resource_usage()
        resource_utilization = (
            resource_usage.cpu_percent + resource_usage.memory_percent
        ) / 2.0

        # Calculate throughput
        throughput = len([
            task for task in self.task_history
            if task.status == TaskStatus.COMPLETED and
            task.assignment_time > datetime.now() - timedelta(minutes=1)
        ])

        # Calculate error rate
        error_rate = len([
            task for task in self.task_history
            if task.status == TaskStatus.FAILED and
            task.assignment_time > datetime.now() - timedelta(minutes=1)
        ]) / max(1, len(self.task_history))

        return ScalingMetrics(
            current_agents=current_agents,
            target_agents=current_agents,
            queue_depth=queue_depth,
            avg_response_time=avg_response_time,
            resource_utilization=resource_utilization,
            throughput=throughput,
            error_rate=error_rate
        )

    async def _calculate_load_balancing_metrics(self) -> LoadBalancingMetrics:
        """Calculate load balancing metrics."""
        if not self.agents:
            return LoadBalancingMetrics(
                distribution_variance=0.0,
                agent_utilization={},
                task_completion_rate=0.0,
                average_wait_time=0.0,
                balancing_effectiveness=0.0
            )

        # Calculate distribution variance
        task_counts = [agent.active_tasks for agent in self.agents.values()]
        if task_counts:
            mean_tasks = sum(task_counts) / len(task_counts)
            variance = sum((count - mean_tasks) ** 2 for count in task_counts) / len(task_counts)
        else:
            variance = 0.0

        # Calculate agent utilization
        agent_utilization = {}
        for agent_id, agent_info in self.agents.items():
            if agent_info.resource_allocation:
                allocation = agent_info.resource_allocation
                if agent_info.current_usage:
                    usage = agent_info.current_usage
                    utilization = (usage.cpu_percent + usage.memory_percent) / 2.0
                else:
                    utilization = 0.0
                agent_utilization[agent_id] = utilization

        # Calculate task completion rate
        completed_tasks = len([t for t in self.task_history if t.status == TaskStatus.COMPLETED])
        total_tasks = len(self.task_history)
        completion_rate = completed_tasks / max(1, total_tasks)

        # Calculate average wait time
        pending_wait_times = [
            (datetime.now() - task.assignment_time).total_seconds()
            for task in self.pending_tasks
        ]
        avg_wait_time = sum(pending_wait_times) / max(1, len(pending_wait_times))

        # Calculate balancing effectiveness (inverse of variance)
        effectiveness = 1.0 / (1.0 + variance)

        return LoadBalancingMetrics(
            distribution_variance=variance,
            agent_utilization=agent_utilization,
            task_completion_rate=completion_rate,
            average_wait_time=avg_wait_time,
            balancing_effectiveness=effectiveness
        )

    async def _health_monitor(self) -> None:
        """Background health monitoring task."""
        while self.running:
            try:
                await asyncio.sleep(self.config.health_check_interval)

                # Check agent health
                for agent_id, agent_info in self.agents.items():
                    if agent_info.status == AgentStatus.HEALTHY:
                        # Check if agent is responsive
                        time_since_heartbeat = datetime.now() - agent_info.last_heartbeat
                        if time_since_heartbeat.total_seconds() > self.config.health_check_interval * 2:
                            agent_info.status = AgentStatus.UNHEALTHY
                            await self.handle_agent_failure(agent_id)

                self.last_health_check = datetime.now()

            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")

    async def _load_balancer(self) -> None:
        """Background load balancing task."""
        while self.running:
            try:
                await asyncio.sleep(self.config.load_balance_interval)
                await self.rebalance_load()

            except Exception as e:
                self.logger.error(f"Load balancing error: {e}")

    async def _scaling_monitor(self) -> None:
        """Background scaling monitoring task."""
        while self.running:
            try:
                await asyncio.sleep(self.config.scaling_check_interval)

                if self.config.enable_auto_scaling:
                    await self.scaling_manager.check_scaling_needs(self)

            except Exception as e:
                self.logger.error(f"Scaling monitoring error: {e}")

    async def update_agent_heartbeat(self, agent_id: str, usage: Optional[ResourceUsage] = None) -> bool:
        """
        Update agent heartbeat and resource usage.

        Args:
            agent_id: ID of the agent
            usage: Current resource usage

        Returns:
            bool: True if update successful
        """
        if agent_id not in self.agents:
            return False

        agent_info = self.agents[agent_id]
        agent_info.last_heartbeat = datetime.now()

        if usage:
            agent_info.current_usage = usage

        return True

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.

        Returns:
            Dict[str, Any]: Performance metrics
        """
        uptime = (datetime.now() - self.startup_time).total_seconds()

        metrics = self.performance_metrics.copy()
        metrics.update({
            'uptime_seconds': uptime,
            'active_agents': len([a for a in self.agents.values() if a.status == AgentStatus.HEALTHY]),
            'total_agents': len(self.agents),
            'pending_tasks': len(self.pending_tasks),
            'assigned_tasks': len(self.assigned_tasks),
            'completed_tasks': len([t for t in self.task_history if t.status == TaskStatus.COMPLETED]),
            'failed_tasks': len([t for t in self.task_history if t.status == TaskStatus.FAILED]),
            'last_health_check': self.last_health_check.isoformat(),
            'last_load_balance': self.last_load_balance.isoformat()
        })

        return metrics
