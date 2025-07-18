"""
Scaling Manager for automatic agent scaling based on demand and performance metrics.

This module provides auto-scaling capabilities for the multi-agent system.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from .models import (
    ResourceLimits, ScalingConfig, ScalingReason, ScalingMetrics,
    ScalingException, AgentStatus
)

if TYPE_CHECKING:
    from .multi_agent_coordinator import MultiAgentCoordinator


class ScalingDecision(Enum):
    """Scaling decision enumeration."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_CHANGE = "no_change"


@dataclass
class ScalingEvent:
    """Scaling event record."""
    timestamp: datetime
    decision: ScalingDecision
    reason: ScalingReason
    agents_before: int
    agents_after: int
    success: bool
    error: Optional[str] = None


class ScalingManager:
    """
    Scaling Manager for automatic agent scaling.

    This class provides:
    - Auto-scaling based on demand metrics
    - Scale-up/scale-down decision making
    - Scaling event tracking and metrics
    - Cooldown period management
    - Performance-based scaling optimization
    """

    def __init__(self, resource_limits: ResourceLimits):
        """
        Initialize the ScalingManager.

        Args:
            resource_limits: System resource limits
        """
        self.resource_limits = resource_limits
        self.logger = logging.getLogger(__name__)

        # Scaling configuration
        self.config = ScalingConfig(
            max_agents=resource_limits.max_agents
        )

        # Scaling state
        self.last_scaling_event: Optional[datetime] = None
        self.scaling_history: List[ScalingEvent] = []
        self.scaling_metrics_history: List[ScalingMetrics] = []

        # Metrics tracking
        self.metrics_window_size = 10
        self.scaling_enabled = True

        self.logger.info(f"ScalingManager initialized with config: {self.config}")

    async def check_scaling_needs(self, coordinator: 'MultiAgentCoordinator') -> Optional[ScalingDecision]:
        """
        Check if scaling is needed and execute if appropriate.

        Args:
            coordinator: MultiAgentCoordinator instance

        Returns:
            ScalingDecision: Decision made or None if no action taken
        """
        try:
            if not self.scaling_enabled:
                return None

            # Check cooldown period
            if self._in_cooldown_period():
                return None

            # Get current metrics
            current_metrics = await coordinator._calculate_scaling_metrics()
            self._update_metrics_history(current_metrics)

            # Make scaling decision
            decision, reason = await self._make_scaling_decision(current_metrics)

            if decision == ScalingDecision.NO_CHANGE:
                return decision

            # Execute scaling decision
            success = await self._execute_scaling_decision(coordinator, decision, reason)

            if success:
                self.logger.info(f"Scaling decision executed: {decision.value}, reason: {reason.reason}")
                return decision

            return None

        except Exception as e:
            self.logger.error(f"Error checking scaling needs: {e}")
            return None

    async def should_scale_up(self, coordinator: 'MultiAgentCoordinator') -> Tuple[bool, Optional[ScalingReason]]:
        """
        Check if the system should scale up.

        Args:
            coordinator: MultiAgentCoordinator instance

        Returns:
            Tuple[bool, Optional[ScalingReason]]: Should scale up and reason
        """
        try:
            current_metrics = await coordinator._calculate_scaling_metrics()

            # Check if we're at maximum capacity
            if current_metrics.current_agents >= self.config.max_agents:
                return False, None

            # Check queue depth
            if current_metrics.queue_depth >= self.config.queue_depth_threshold:
                return True, ScalingReason(
                    reason="High queue depth",
                    metric_name="queue_depth",
                    current_value=current_metrics.queue_depth,
                    threshold=self.config.queue_depth_threshold
                )

            # Check response time
            if current_metrics.avg_response_time > self.config.response_time_threshold:
                return True, ScalingReason(
                    reason="High response time",
                    metric_name="avg_response_time",
                    current_value=current_metrics.avg_response_time,
                    threshold=self.config.response_time_threshold
                )

            # Check resource utilization
            if current_metrics.resource_utilization > self.config.scale_up_threshold:
                return True, ScalingReason(
                    reason="High resource utilization",
                    metric_name="resource_utilization",
                    current_value=current_metrics.resource_utilization,
                    threshold=self.config.scale_up_threshold
                )

            # Check throughput decline
            if len(self.scaling_metrics_history) >= 2:
                previous_metrics = self.scaling_metrics_history[-2]
                throughput_decline = (previous_metrics.throughput - current_metrics.throughput) / max(1, previous_metrics.throughput)

                if throughput_decline > 0.2:  # 20% decline
                    return True, ScalingReason(
                        reason="Throughput decline",
                        metric_name="throughput",
                        current_value=current_metrics.throughput,
                        threshold=previous_metrics.throughput * 0.8
                    )

            return False, None

        except Exception as e:
            self.logger.error(f"Error checking scale up conditions: {e}")
            return False, None

    async def should_scale_down(self, coordinator: 'MultiAgentCoordinator') -> Tuple[bool, Optional[ScalingReason]]:
        """
        Check if the system should scale down.

        Args:
            coordinator: MultiAgentCoordinator instance

        Returns:
            Tuple[bool, Optional[ScalingReason]]: Should scale down and reason
        """
        try:
            current_metrics = await coordinator._calculate_scaling_metrics()

            # Check if we're at minimum capacity
            if current_metrics.current_agents <= self.config.min_agents:
                return False, None

            # Only scale down if conditions are stable
            if not self._are_conditions_stable():
                return False, None

            # Check resource utilization
            if current_metrics.resource_utilization < self.config.scale_down_threshold:
                # Additional checks to ensure it's safe to scale down
                if (current_metrics.queue_depth < self.config.queue_depth_threshold * 0.3 and
                    current_metrics.avg_response_time < self.config.response_time_threshold * 0.5):

                    return True, ScalingReason(
                        reason="Low resource utilization",
                        metric_name="resource_utilization",
                        current_value=current_metrics.resource_utilization,
                        threshold=self.config.scale_down_threshold
                    )

            # Check for sustained low queue depth
            if len(self.scaling_metrics_history) >= 5:
                recent_queue_depths = [m.queue_depth for m in self.scaling_metrics_history[-5:]]
                avg_queue_depth = sum(recent_queue_depths) / len(recent_queue_depths)

                if avg_queue_depth < self.config.queue_depth_threshold * 0.2:
                    return True, ScalingReason(
                        reason="Sustained low queue depth",
                        metric_name="queue_depth",
                        current_value=avg_queue_depth,
                        threshold=self.config.queue_depth_threshold * 0.2
                    )

            return False, None

        except Exception as e:
            self.logger.error(f"Error checking scale down conditions: {e}")
            return False, None

    async def scale_up(self, coordinator: 'MultiAgentCoordinator', count: Optional[int] = None) -> List[str]:
        """
        Scale up the number of agents.

        Args:
            coordinator: MultiAgentCoordinator instance
            count: Number of agents to add (default: config.scale_up_step)

        Returns:
            List[str]: List of new agent IDs

        Raises:
            ScalingException: If scaling fails
        """
        try:
            if count is None:
                count = self.config.scale_up_step

            current_agents = len([a for a in coordinator.agents.values() if a.status == AgentStatus.HEALTHY])

            # Check limits
            if current_agents + count > self.config.max_agents:
                count = self.config.max_agents - current_agents

            if count <= 0:
                raise ScalingException("Cannot scale up: at maximum capacity")

            # TODO: Implement actual agent spawning
            # For now, return placeholder agent IDs
            new_agent_ids = []
            for i in range(count):
                agent_id = f"auto-agent-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{i}"
                new_agent_ids.append(agent_id)

            self.logger.info(f"Scaled up by {count} agents: {new_agent_ids}")
            return new_agent_ids

        except Exception as e:
            self.logger.error(f"Failed to scale up: {e}")
            raise ScalingException(f"Scale up failed: {e}")

    async def scale_down(self, coordinator: 'MultiAgentCoordinator', count: Optional[int] = None) -> List[str]:
        """
        Scale down the number of agents.

        Args:
            coordinator: MultiAgentCoordinator instance
            count: Number of agents to remove (default: config.scale_down_step)

        Returns:
            List[str]: List of removed agent IDs

        Raises:
            ScalingException: If scaling fails
        """
        try:
            if count is None:
                count = self.config.scale_down_step

            healthy_agents = [
                agent_id for agent_id, agent in coordinator.agents.items()
                if agent.status == AgentStatus.HEALTHY
            ]

            # Check limits
            if len(healthy_agents) - count < self.config.min_agents:
                count = len(healthy_agents) - self.config.min_agents

            if count <= 0:
                raise ScalingException("Cannot scale down: at minimum capacity")

            # Select agents to remove (prefer agents with least active tasks)
            agents_to_remove = sorted(
                healthy_agents,
                key=lambda agent_id: coordinator.agents[agent_id].active_tasks
            )[:count]

            # Remove agents
            removed_agents = []
            for agent_id in agents_to_remove:
                if await coordinator.unregister_agent(agent_id):
                    removed_agents.append(agent_id)

            self.logger.info(f"Scaled down by {len(removed_agents)} agents: {removed_agents}")
            return removed_agents

        except Exception as e:
            self.logger.error(f"Failed to scale down: {e}")
            raise ScalingException(f"Scale down failed: {e}")

    async def get_scaling_metrics(self, coordinator: 'MultiAgentCoordinator') -> ScalingMetrics:
        """
        Get current scaling metrics.

        Args:
            coordinator: MultiAgentCoordinator instance

        Returns:
            ScalingMetrics: Current scaling metrics
        """
        return await coordinator._calculate_scaling_metrics()

    def get_scaling_history(self, limit: int = 50) -> List[ScalingEvent]:
        """
        Get scaling event history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List[ScalingEvent]: Recent scaling events
        """
        return self.scaling_history[-limit:]

    def get_scaling_statistics(self) -> Dict[str, Any]:
        """
        Get scaling statistics.

        Returns:
            Dict[str, any]: Scaling statistics
        """
        total_events = len(self.scaling_history)
        successful_events = len([e for e in self.scaling_history if e.success])
        scale_up_events = len([e for e in self.scaling_history if e.decision == ScalingDecision.SCALE_UP])
        scale_down_events = len([e for e in self.scaling_history if e.decision == ScalingDecision.SCALE_DOWN])

        # Calculate average scaling effectiveness
        effectiveness = 0.0
        if total_events > 0:
            effectiveness = successful_events / total_events

        return {
            'total_events': total_events,
            'successful_events': successful_events,
            'scale_up_events': scale_up_events,
            'scale_down_events': scale_down_events,
            'success_rate': effectiveness,
            'last_scaling_event': self.last_scaling_event.isoformat() if self.last_scaling_event else None,
            'scaling_enabled': self.scaling_enabled,
            'config': {
                'min_agents': self.config.min_agents,
                'max_agents': self.config.max_agents,
                'scale_up_threshold': self.config.scale_up_threshold,
                'scale_down_threshold': self.config.scale_down_threshold,
                'cooldown_period': self.config.cooldown_period
            }
        }

    def enable_scaling(self) -> None:
        """Enable automatic scaling."""
        self.scaling_enabled = True
        self.logger.info("Automatic scaling enabled")

    def disable_scaling(self) -> None:
        """Disable automatic scaling."""
        self.scaling_enabled = False
        self.logger.info("Automatic scaling disabled")

    def update_config(self, config: ScalingConfig) -> None:
        """
        Update scaling configuration.

        Args:
            config: New scaling configuration
        """
        self.config = config
        self.logger.info(f"Scaling configuration updated: {config}")

    async def _make_scaling_decision(self, current_metrics: ScalingMetrics) -> Tuple[ScalingDecision, Optional[ScalingReason]]:
        """
        Make scaling decision based on current metrics.

        Args:
            current_metrics: Current scaling metrics

        Returns:
            Tuple[ScalingDecision, Optional[ScalingReason]]: Decision and reason
        """
        # Check scale up conditions first (higher priority)
        should_scale_up, scale_up_reason = await self._check_scale_up_conditions(current_metrics)
        if should_scale_up:
            return ScalingDecision.SCALE_UP, scale_up_reason

        # Check scale down conditions
        should_scale_down, scale_down_reason = await self._check_scale_down_conditions(current_metrics)
        if should_scale_down:
            return ScalingDecision.SCALE_DOWN, scale_down_reason

        return ScalingDecision.NO_CHANGE, None

    async def _check_scale_up_conditions(self, metrics: ScalingMetrics) -> Tuple[bool, Optional[ScalingReason]]:
        """Check if scale up conditions are met."""
        # Check maximum capacity
        if metrics.current_agents >= self.config.max_agents:
            return False, None

        # Check queue depth
        if metrics.queue_depth >= self.config.queue_depth_threshold:
            return True, ScalingReason(
                reason="High queue depth",
                metric_name="queue_depth",
                current_value=metrics.queue_depth,
                threshold=self.config.queue_depth_threshold
            )

        # Check response time
        if metrics.avg_response_time > self.config.response_time_threshold:
            return True, ScalingReason(
                reason="High response time",
                metric_name="avg_response_time",
                current_value=metrics.avg_response_time,
                threshold=self.config.response_time_threshold
            )

        # Check resource utilization
        if metrics.resource_utilization > self.config.scale_up_threshold:
            return True, ScalingReason(
                reason="High resource utilization",
                metric_name="resource_utilization",
                current_value=metrics.resource_utilization,
                threshold=self.config.scale_up_threshold
            )

        return False, None

    async def _check_scale_down_conditions(self, metrics: ScalingMetrics) -> Tuple[bool, Optional[ScalingReason]]:
        """Check if scale down conditions are met."""
        # Check minimum capacity
        if metrics.current_agents <= self.config.min_agents:
            return False, None

        # Only scale down if conditions are stable
        if not self._are_conditions_stable():
            return False, None

        # Check resource utilization
        if metrics.resource_utilization < self.config.scale_down_threshold:
            # Additional safety checks
            if (metrics.queue_depth < self.config.queue_depth_threshold * 0.3 and
                metrics.avg_response_time < self.config.response_time_threshold * 0.5):

                return True, ScalingReason(
                    reason="Low resource utilization",
                    metric_name="resource_utilization",
                    current_value=metrics.resource_utilization,
                    threshold=self.config.scale_down_threshold
                )

        return False, None

    async def _execute_scaling_decision(self, coordinator: 'MultiAgentCoordinator',
                                       decision: ScalingDecision, reason: ScalingReason) -> bool:
        """
        Execute scaling decision.

        Args:
            coordinator: MultiAgentCoordinator instance
            decision: Scaling decision
            reason: Scaling reason

        Returns:
            bool: True if scaling was successful
        """
        try:
            agents_before = len([a for a in coordinator.agents.values() if a.status == AgentStatus.HEALTHY])

            if decision == ScalingDecision.SCALE_UP:
                new_agents = await self.scale_up(coordinator)
                agents_after = agents_before + len(new_agents)
                success = len(new_agents) > 0

            elif decision == ScalingDecision.SCALE_DOWN:
                removed_agents = await self.scale_down(coordinator)
                agents_after = agents_before - len(removed_agents)
                success = len(removed_agents) > 0

            else:
                return False

            # Record scaling event
            event = ScalingEvent(
                timestamp=datetime.now(),
                decision=decision,
                reason=reason,
                agents_before=agents_before,
                agents_after=agents_after,
                success=success
            )

            self.scaling_history.append(event)
            self.last_scaling_event = event.timestamp

            # Keep history limited
            if len(self.scaling_history) > 1000:
                self.scaling_history = self.scaling_history[-500:]

            return success

        except Exception as e:
            # Record failed scaling event
            event = ScalingEvent(
                timestamp=datetime.now(),
                decision=decision,
                reason=reason,
                agents_before=len([a for a in coordinator.agents.values() if a.status == AgentStatus.HEALTHY]),
                agents_after=0,
                success=False,
                error=str(e)
            )

            self.scaling_history.append(event)
            self.logger.error(f"Scaling execution failed: {e}")
            return False

    def _in_cooldown_period(self) -> bool:
        """Check if we're in cooldown period after last scaling event."""
        if not self.last_scaling_event:
            return False

        time_since_last = datetime.now() - self.last_scaling_event
        return time_since_last.total_seconds() < self.config.cooldown_period

    def _are_conditions_stable(self) -> bool:
        """Check if system conditions are stable for scaling down."""
        if len(self.scaling_metrics_history) < 3:
            return False

        # Check last 3 metrics for stability
        recent_metrics = self.scaling_metrics_history[-3:]

        # Check queue depth stability
        queue_depths = [m.queue_depth for m in recent_metrics]
        queue_variance = self._calculate_variance(queue_depths)

        # Check response time stability
        response_times = [m.avg_response_time for m in recent_metrics]
        response_variance = self._calculate_variance(response_times)

        # Consider stable if variance is low
        return queue_variance < 100 and response_variance < 1.0

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    def _update_metrics_history(self, metrics: ScalingMetrics) -> None:
        """Update metrics history."""
        self.scaling_metrics_history.append(metrics)

        # Keep history limited
        if len(self.scaling_metrics_history) > self.metrics_window_size * 10:
            self.scaling_metrics_history = self.scaling_metrics_history[-self.metrics_window_size * 5:]
