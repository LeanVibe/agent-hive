"""
Real-Time Coordination Feedback Loops for Multi-Agent Orchestration.

This module implements sophisticated real-time feedback mechanisms that continuously
monitor, analyze, and optimize multi-agent coordination based on live performance
data and coordination patterns.
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .continuous_improvement import (
    ContinuousImprovementEngine,
    ImprovementOpportunity,
)
from .performance_monitor import (
    PerformanceMetric,
    PerformanceMetricType,
    PerformanceMonitor,
)


class FeedbackType(Enum):
    """Types of feedback mechanisms."""
    PERFORMANCE_FEEDBACK = "performance_feedback"
    COORDINATION_FEEDBACK = "coordination_feedback"
    RESOURCE_FEEDBACK = "resource_feedback"
    QUALITY_FEEDBACK = "quality_feedback"
    AGENT_FEEDBACK = "agent_feedback"
    WORKFLOW_FEEDBACK = "workflow_feedback"
    PREDICTIVE_FEEDBACK = "predictive_feedback"
    ADAPTIVE_FEEDBACK = "adaptive_feedback"


class FeedbackPriority(Enum):
    """Priority levels for feedback processing."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class FeedbackAction(Enum):
    """Types of feedback actions."""
    IMMEDIATE_ADJUSTMENT = "immediate_adjustment"
    GRADUAL_OPTIMIZATION = "gradual_optimization"
    PREDICTIVE_SCALING = "predictive_scaling"
    COORDINATION_REBALANCING = "coordination_rebalancing"
    RESOURCE_REALLOCATION = "resource_reallocation"
    QUALITY_ENHANCEMENT = "quality_enhancement"
    LEARNING_UPDATE = "learning_update"
    ALERT_GENERATION = "alert_generation"


@dataclass
class FeedbackSignal:
    """Individual feedback signal."""
    id: str
    type: FeedbackType
    priority: FeedbackPriority
    source: str  # Agent ID, workflow ID, or system component
    timestamp: datetime
    data: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    expiry_time: Optional[datetime] = None
    processed: bool = False
    processing_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class FeedbackRule:
    """Rule for processing feedback signals."""
    id: str
    name: str
    type: FeedbackType
    condition: Callable[[FeedbackSignal], bool]
    action: FeedbackAction
    handler: Callable[[FeedbackSignal], Any]
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    enabled: bool = True
    min_confidence: float = 0.7
    cooldown_period: timedelta = timedelta(minutes=5)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    success_count: int = 0


@dataclass
class FeedbackResponse:
    """Response to feedback processing."""
    signal_id: str
    action_taken: FeedbackAction
    success: bool
    result: Dict[str, Any]
    processing_time: float
    confidence: float
    side_effects: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class AdaptiveFeedbackController:
    """Adaptive controller for dynamic feedback adjustment."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.adaptation_history: deque = deque(maxlen=1000)
        self.control_parameters: Dict[str, float] = {
            "response_sensitivity": 0.7,
            "adaptation_rate": 0.1,
            "stability_threshold": 0.8,
            "prediction_horizon": 300.0,  # 5 minutes
            "damping_factor": 0.9
        }
        self.system_state: Dict[str, Any] = {}
        self.target_metrics: Dict[str, float] = {
            "coordination_efficiency": 0.85,
            "response_time": 2.0,
            "throughput": 20.0,
            "error_rate": 0.02
        }

    def calculate_control_signal(self,
                                 current_metrics: Dict[str,
                                                       float],
                                 target_metrics: Dict[str,
                                                      float] = None) -> Dict[str,
                                                                             float]:
        """Calculate control signals for adaptive feedback."""
        if target_metrics is None:
            target_metrics = self.target_metrics

        control_signals = {}

        for metric_name, current_value in current_metrics.items():
            target_value = target_metrics.get(metric_name)
            if target_value is None:
                continue

            # Calculate error
            error = target_value - current_value

            # Calculate control signal using PID-like approach
            proportional = error * \
                self.control_parameters["response_sensitivity"]

            # Get derivative from history
            derivative = self._calculate_derivative(metric_name, current_value)

            # Get integral from history
            integral = self._calculate_integral(metric_name, error)

            # Combine signals
            control_signal = proportional + derivative + integral

            # Apply damping
            control_signal *= self.control_parameters["damping_factor"]

            control_signals[metric_name] = control_signal

        # Record adaptation
        self.adaptation_history.append({
            "timestamp": datetime.now(),
            "current_metrics": current_metrics,
            "target_metrics": target_metrics,
            "control_signals": control_signals
        })

        return control_signals

    def _calculate_derivative(
            self,
            metric_name: str,
            current_value: float) -> float:
        """Calculate derivative component for control signal."""
        if len(self.adaptation_history) < 2:
            return 0.0

        # Get last value for this metric
        for entry in reversed(self.adaptation_history):
            if metric_name in entry.get("current_metrics", {}):
                last_value = entry["current_metrics"][metric_name]
                time_diff = (datetime.now() -
                             entry["timestamp"]).total_seconds()
                if time_diff > 0:
                    return (current_value - last_value) / time_diff

        return 0.0

    def _calculate_integral(self, metric_name: str, error: float) -> float:
        """Calculate integral component for control signal."""
        if len(self.adaptation_history) < 3:
            return 0.0

        # Sum recent errors
        error_sum = 0.0
        count = 0

        for entry in list(self.adaptation_history)[-10:]:  # Last 10 entries
            if metric_name in entry.get("current_metrics", {}):
                target = self.target_metrics.get(metric_name, 0)
                current = entry["current_metrics"][metric_name]
                error_sum += (target - current)
                count += 1

        if count > 0:
            return error_sum / count * \
                self.control_parameters["adaptation_rate"]

        return 0.0

    def update_targets(self, new_targets: Dict[str, float]) -> None:
        """Update target metrics."""
        self.target_metrics.update(new_targets)
        self.logger.info(f"Updated target metrics: {new_targets}")

    def get_adaptation_status(self) -> Dict[str, Any]:
        """Get current adaptation status."""
        return {
            "control_parameters": self.control_parameters,
            "target_metrics": self.target_metrics,
            "adaptation_history_size": len(self.adaptation_history),
            "system_state": self.system_state
        }


class RealTimeFeedbackEngine:
    """Real-time feedback engine for multi-agent coordination."""

    def __init__(self, performance_monitor: PerformanceMonitor,
                 improvement_engine: ContinuousImprovementEngine):
        self.logger = logging.getLogger(__name__)
        self.performance_monitor = performance_monitor
        self.improvement_engine = improvement_engine
        self.adaptive_controller = AdaptiveFeedbackController()

        # Feedback processing
        self.feedback_queue: asyncio.Queue = asyncio.Queue()
        self.feedback_history: deque = deque(maxlen=5000)
        self.feedback_rules: Dict[str, FeedbackRule] = {}
        self.active_feedbacks: Dict[str, FeedbackSignal] = {}

        # Processing state
        self.running = False
        self.feedback_tasks: Set[asyncio.Task] = set()
        self.processing_stats: Dict[str, int] = defaultdict(int)
        self.response_times: deque = deque(maxlen=100)

        # Real-time metrics
        self.current_metrics: Dict[str, float] = {}
        self.metric_trends: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=50))
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}

        # Configuration
        self.max_concurrent_feedback = 10
        self.feedback_timeout = 30.0  # seconds
        self.metric_update_interval = 1.0  # seconds

        # Initialize feedback rules
        self._initialize_feedback_rules()

        self.logger.info("RealTimeFeedbackEngine initialized")

    async def start(self) -> None:
        """Start the real-time feedback engine."""
        self.running = True

        # Start feedback processing tasks
        self.feedback_tasks.add(asyncio.create_task(
            self._feedback_processing_loop()))
        self.feedback_tasks.add(asyncio.create_task(
            self._metrics_collection_loop()))
        self.feedback_tasks.add(asyncio.create_task(
            self._correlation_analysis_loop()))
        self.feedback_tasks.add(asyncio.create_task(
            self._adaptive_control_loop()))

        self.logger.info("Real-time feedback engine started")

    async def stop(self) -> None:
        """Stop the real-time feedback engine."""
        self.running = False

        # Cancel all feedback tasks
        for task in self.feedback_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.feedback_tasks, return_exceptions=True)

        self.logger.info("Real-time feedback engine stopped")

    def _initialize_feedback_rules(self) -> None:
        """Initialize feedback processing rules."""

        # Performance feedback rules
        self.feedback_rules["performance_degradation"] = FeedbackRule(
            id="performance_degradation",
            name="Performance Degradation Detection",
            type=FeedbackType.PERFORMANCE_FEEDBACK,
            condition=lambda signal: signal.data.get(
                "performance_delta", 0) < -0.1,
            action=FeedbackAction.IMMEDIATE_ADJUSTMENT,
            handler=self._handle_performance_degradation,
            priority=FeedbackPriority.HIGH
        )

        self.feedback_rules["coordination_inefficiency"] = FeedbackRule(
            id="coordination_inefficiency",
            name="Coordination Inefficiency Detection",
            type=FeedbackType.COORDINATION_FEEDBACK,
            condition=lambda signal: signal.data.get(
                "coordination_efficiency", 1.0) < 0.6,
            action=FeedbackAction.COORDINATION_REBALANCING,
            handler=self._handle_coordination_inefficiency,
            priority=FeedbackPriority.HIGH
        )

        self.feedback_rules["resource_saturation"] = FeedbackRule(
            id="resource_saturation",
            name="Resource Saturation Detection",
            type=FeedbackType.RESOURCE_FEEDBACK,
            condition=lambda signal: signal.data.get(
                "resource_utilization", 0) > 0.85,
            action=FeedbackAction.RESOURCE_REALLOCATION,
            handler=self._handle_resource_saturation,
            priority=FeedbackPriority.CRITICAL
        )

        self.feedback_rules["quality_decline"] = FeedbackRule(
            id="quality_decline",
            name="Quality Decline Detection",
            type=FeedbackType.QUALITY_FEEDBACK,
            condition=lambda signal: signal.data.get(
                "quality_score", 1.0) < 0.7,
            action=FeedbackAction.QUALITY_ENHANCEMENT,
            handler=self._handle_quality_decline,
            priority=FeedbackPriority.MEDIUM
        )

        self.feedback_rules["agent_overload"] = FeedbackRule(
            id="agent_overload",
            name="Agent Overload Detection",
            type=FeedbackType.AGENT_FEEDBACK,
            condition=lambda signal: signal.data.get("agent_load", 0) > 0.9,
            action=FeedbackAction.PREDICTIVE_SCALING,
            handler=self._handle_agent_overload,
            priority=FeedbackPriority.HIGH
        )

        self.feedback_rules["workflow_bottleneck"] = FeedbackRule(
            id="workflow_bottleneck",
            name="Workflow Bottleneck Detection",
            type=FeedbackType.WORKFLOW_FEEDBACK,
            condition=lambda signal: signal.data.get(
                "bottleneck_detected", False),
            action=FeedbackAction.GRADUAL_OPTIMIZATION,
            handler=self._handle_workflow_bottleneck,
            priority=FeedbackPriority.MEDIUM
        )

        self.feedback_rules["predictive_alert"] = FeedbackRule(
            id="predictive_alert",
            name="Predictive Issue Detection",
            type=FeedbackType.PREDICTIVE_FEEDBACK,
            condition=lambda signal: signal.data.get(
                "prediction_confidence", 0) > 0.8,
            action=FeedbackAction.ALERT_GENERATION,
            handler=self._handle_predictive_alert,
            priority=FeedbackPriority.MEDIUM
        )

        self.feedback_rules["adaptive_learning"] = FeedbackRule(
            id="adaptive_learning",
            name="Adaptive Learning Update",
            type=FeedbackType.ADAPTIVE_FEEDBACK,
            condition=lambda signal: signal.data.get(
                "learning_opportunity", False),
            action=FeedbackAction.LEARNING_UPDATE,
            handler=self._handle_adaptive_learning,
            priority=FeedbackPriority.LOW
        )

    async def submit_feedback(self, signal: FeedbackSignal) -> None:
        """Submit feedback signal for processing."""
        await self.feedback_queue.put(signal)
        self.active_feedbacks[signal.id] = signal

    async def _feedback_processing_loop(self) -> None:
        """Main feedback processing loop."""
        while self.running:
            try:
                # Get feedback signal with timeout
                signal = await asyncio.wait_for(
                    self.feedback_queue.get(),
                    timeout=1.0
                )

                # Process feedback signal
                await self._process_feedback_signal(signal)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in feedback processing loop: {e}")
                await asyncio.sleep(1)

    async def _process_feedback_signal(self, signal: FeedbackSignal) -> None:
        """Process individual feedback signal."""
        try:
            start_time = time.time()

            # Check if signal is expired
            if signal.expiry_time and datetime.now() > signal.expiry_time:
                self.logger.debug(f"Feedback signal expired: {signal.id}")
                return

            # Find matching rules
            matching_rules = self._find_matching_rules(signal)

            if not matching_rules:
                self.logger.debug(
                    f"No matching rules for feedback signal: {signal.id}")
                return

            # Sort rules by priority
            matching_rules.sort(key=lambda r: r.priority.value)

            # Process with highest priority rule
            rule = matching_rules[0]

            # Check cooldown
            if not self._check_cooldown(rule):
                self.logger.debug(f"Rule {rule.id} is in cooldown period")
                return

            # Execute rule handler
            response = await self._execute_rule_handler(rule, signal)

            # Update rule statistics
            rule.last_triggered = datetime.now()
            rule.trigger_count += 1
            if response and response.success:
                rule.success_count += 1

            # Record processing time
            processing_time = time.time() - start_time
            self.response_times.append(processing_time)

            # Update signal
            signal.processed = True
            signal.processing_time = datetime.now()
            signal.result = response.result if response else None

            # Store in history
            self.feedback_history.append({
                "signal": signal,
                "rule": rule.id,
                "response": response,
                "processing_time": processing_time
            })

            # Update processing stats
            self.processing_stats[signal.type.value] += 1

            self.logger.debug(
                f"Processed feedback signal: {signal.id} with rule: {rule.id}")

        except Exception as e:
            self.logger.error(
                f"Error processing feedback signal {signal.id}: {e}")
            signal.processed = True
            signal.result = {"error": str(e)}

        finally:
            # Remove from active feedbacks
            self.active_feedbacks.pop(signal.id, None)

    def _find_matching_rules(
            self,
            signal: FeedbackSignal) -> List[FeedbackRule]:
        """Find rules that match the feedback signal."""
        matching_rules = []

        for rule in self.feedback_rules.values():
            if not rule.enabled:
                continue

            # Check type match
            if rule.type != signal.type:
                continue

            # Check condition
            try:
                if rule.condition(signal):
                    matching_rules.append(rule)
            except Exception as e:
                self.logger.warning(
                    f"Error evaluating rule condition {rule.id}: {e}")

        return matching_rules

    def _check_cooldown(self, rule: FeedbackRule) -> bool:
        """Check if rule is in cooldown period."""
        if not rule.last_triggered:
            return True

        time_since_last = datetime.now() - rule.last_triggered
        return time_since_last >= rule.cooldown_period

    async def _execute_rule_handler(
            self,
            rule: FeedbackRule,
            signal: FeedbackSignal) -> Optional[FeedbackResponse]:
        """Execute rule handler with timeout."""
        try:
            # Create timeout task
            handler_task = asyncio.create_task(rule.handler(signal))

            # Wait for handler with timeout
            result = await asyncio.wait_for(handler_task, timeout=self.feedback_timeout)

            if isinstance(result, FeedbackResponse):
                return result
            else:
                # Create response from handler result
                return FeedbackResponse(
                    signal_id=signal.id,
                    action_taken=rule.action,
                    success=True,
                    result=result or {},
                    processing_time=time.time(),
                    confidence=0.8
                )

        except asyncio.TimeoutError:
            self.logger.warning(f"Rule handler {rule.id} timed out")
            return FeedbackResponse(
                signal_id=signal.id,
                action_taken=rule.action,
                success=False,
                result={"error": "timeout"},
                processing_time=self.feedback_timeout,
                confidence=0.0
            )

        except Exception as e:
            self.logger.error(f"Error executing rule handler {rule.id}: {e}")
            return FeedbackResponse(
                signal_id=signal.id,
                action_taken=rule.action,
                success=False,
                result={"error": str(e)},
                processing_time=time.time(),
                confidence=0.0
            )

    async def _metrics_collection_loop(self) -> None:
        """Collect real-time metrics for feedback analysis."""
        while self.running:
            try:
                # Get current metrics from performance monitor
                real_time_metrics = self.performance_monitor.get_real_time_metrics()

                # Update current metrics
                for metric_name, metric_data in real_time_metrics.get(
                        "metrics", {}).items():
                    current_value = metric_data.get("current", 0.0)
                    self.current_metrics[metric_name] = current_value
                    self.metric_trends[metric_name].append(current_value)

                # Generate feedback signals based on metrics
                await self._generate_metric_feedback_signals()

                await asyncio.sleep(self.metric_update_interval)

            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)

    async def _generate_metric_feedback_signals(self) -> None:
        """Generate feedback signals based on current metrics."""
        for metric_name, current_value in self.current_metrics.items():
            # Check for performance degradation
            if len(self.metric_trends[metric_name]) >= 5:
                recent_values = list(self.metric_trends[metric_name])[-5:]
                trend = self._calculate_trend(recent_values)

                if trend < -0.2:  # Significant negative trend
                    signal = FeedbackSignal(
                        id=f"perf_degradation_{metric_name}_{
                            int(
                                time.time())}",
                        type=FeedbackType.PERFORMANCE_FEEDBACK,
                        priority=FeedbackPriority.HIGH,
                        source="metrics_collector",
                        timestamp=datetime.now(),
                        data={
                            "metric_name": metric_name,
                            "current_value": current_value,
                            "trend": trend,
                            "performance_delta": trend
                        }
                    )
                    await self.submit_feedback(signal)

            # Check for resource saturation
            if metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
                if current_value > 0.85:
                    signal = FeedbackSignal(
                        id=f"resource_saturation_{metric_name}_{
                            int(
                                time.time())}",
                        type=FeedbackType.RESOURCE_FEEDBACK,
                        priority=FeedbackPriority.CRITICAL,
                        source="metrics_collector",
                        timestamp=datetime.now(),
                        data={
                            "metric_name": metric_name,
                            "resource_utilization": current_value
                        }
                    )
                    await self.submit_feedback(signal)

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend from values."""
        if len(values) < 2:
            return 0.0

        # Simple linear regression slope
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * values[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))

        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope

    async def _correlation_analysis_loop(self) -> None:
        """Analyze correlations between metrics."""
        while self.running:
            try:
                # Wait for sufficient data
                await asyncio.sleep(60)  # Analyze every minute

                # Calculate correlations
                self._calculate_metric_correlations()

                # Generate predictive feedback signals
                await self._generate_predictive_signals()

            except Exception as e:
                self.logger.error(f"Error in correlation analysis loop: {e}")
                await asyncio.sleep(30)

    def _calculate_metric_correlations(self) -> None:
        """Calculate correlations between metrics."""
        metric_names = list(self.metric_trends.keys())

        for i, metric1 in enumerate(metric_names):
            for j, metric2 in enumerate(metric_names[i + 1:], i + 1):
                values1 = list(self.metric_trends[metric1])
                values2 = list(self.metric_trends[metric2])

                if len(values1) >= 10 and len(values2) >= 10:
                    # Take common length
                    min_len = min(len(values1), len(values2))
                    values1 = values1[-min_len:]
                    values2 = values2[-min_len:]

                    # Calculate correlation
                    correlation = self._calculate_correlation(values1, values2)
                    self.correlation_matrix[(metric1, metric2)] = correlation

    def _calculate_correlation(
            self,
            x_values: List[float],
            y_values: List[float]) -> float:
        """Calculate correlation coefficient."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x * sum_x) *
                       (n * sum_y2 - sum_y * sum_y)) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    async def _generate_predictive_signals(self) -> None:
        """Generate predictive feedback signals."""
        # Look for strong correlations that might predict issues
        for (metric1, metric2), correlation in self.correlation_matrix.items():
            if abs(correlation) > 0.8:  # Strong correlation
                # Check if one metric is trending towards problem
                trend1 = self._calculate_trend(
                    list(self.metric_trends[metric1])[-10:])
                trend2 = self._calculate_trend(
                    list(self.metric_trends[metric2])[-10:])

                # If one is trending bad and correlation is positive, predict
                # the other will too
                if correlation > 0.8 and (trend1 < -0.1 or trend2 < -0.1):
                    signal = FeedbackSignal(
                        id=f"predictive_correlation_{metric1}_{metric2}_{
                            int(
                                time.time())}",
                        type=FeedbackType.PREDICTIVE_FEEDBACK,
                        priority=FeedbackPriority.MEDIUM,
                        source="correlation_analyzer",
                        timestamp=datetime.now(),
                        data={
                            "metric1": metric1,
                            "metric2": metric2,
                            "correlation": correlation,
                            "trend1": trend1,
                            "trend2": trend2,
                            "prediction_confidence": abs(correlation)
                        }
                    )
                    await self.submit_feedback(signal)

    async def _adaptive_control_loop(self) -> None:
        """Adaptive control loop for dynamic adjustment."""
        while self.running:
            try:
                # Calculate control signals
                control_signals = self.adaptive_controller.calculate_control_signal(
                    self.current_metrics)

                # Apply control signals
                await self._apply_control_signals(control_signals)

                await asyncio.sleep(5)  # Control loop every 5 seconds

            except Exception as e:
                self.logger.error(f"Error in adaptive control loop: {e}")
                await asyncio.sleep(10)

    async def _apply_control_signals(
            self, control_signals: Dict[str, float]) -> None:
        """Apply control signals to adjust system behavior."""
        for metric_name, signal_value in control_signals.items():
            if abs(signal_value) > 0.1:  # Significant control signal
                # Generate adaptive feedback
                feedback_signal = FeedbackSignal(
                    id=f"adaptive_control_{metric_name}_{int(time.time())}",
                    type=FeedbackType.ADAPTIVE_FEEDBACK,
                    priority=FeedbackPriority.LOW,
                    source="adaptive_controller",
                    timestamp=datetime.now(),
                    data={
                        "metric_name": metric_name,
                        "control_signal": signal_value,
                        "learning_opportunity": True
                    }
                )
                await self.submit_feedback(feedback_signal)

    # Feedback handlers
    async def _handle_performance_degradation(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle performance degradation feedback."""
        metric_name = signal.data.get("metric_name")
        performance_delta = signal.data.get("performance_delta", 0)

        self.logger.warning(
            f"Performance degradation detected in {metric_name}: {performance_delta}")

        # Record performance metric
        self.performance_monitor.record_metric(
            PerformanceMetric(
                metric_type=PerformanceMetricType.LATENCY,
                value=abs(performance_delta),
                timestamp=datetime.now(),
                additional_context={
                    "feedback_signal": signal.id,
                    "metric_name": metric_name
                }
            )
        )

        # Generate improvement opportunity
        opportunity = ImprovementOpportunity(
            id=f"perf_degradation_{metric_name}_{int(time.time())}",
            type=self.improvement_engine.ImprovementType.PERFORMANCE_OPTIMIZATION,
            priority=self.improvement_engine.ImprovementPriority.HIGH,
            title=f"Address performance degradation in {metric_name}",
            description=f"Performance degradation detected: {performance_delta}",
            current_state={"performance_delta": performance_delta},
            target_state={"performance_delta": 0.0},
            expected_impact=0.8,
            implementation_effort=0.6,
            success_metrics=[metric_name],
            implementation_steps=[
                f"Analyze {metric_name} performance degradation",
                "Implement performance optimization",
                "Monitor improvement results"
            ],
            confidence_score=0.85
        )

        # Submit to improvement engine
        self.improvement_engine.improvement_opportunities[opportunity.id] = opportunity

        return {
            "action": "performance_optimization_initiated",
            "metric": metric_name,
            "degradation": performance_delta,
            "improvement_opportunity": opportunity.id
        }

    async def _handle_coordination_inefficiency(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle coordination inefficiency feedback."""
        efficiency = signal.data.get("coordination_efficiency", 0.0)

        self.logger.warning(
            f"Coordination inefficiency detected: {efficiency}")

        # Trigger coordination rebalancing
        rebalancing_actions = [
            "Analyze agent interaction patterns",
            "Optimize communication protocols",
            "Rebalance task distribution"
        ]

        return {
            "action": "coordination_rebalancing_initiated",
            "efficiency": efficiency,
            "rebalancing_actions": rebalancing_actions
        }

    async def _handle_resource_saturation(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle resource saturation feedback."""
        utilization = signal.data.get("resource_utilization", 0.0)
        metric_name = signal.data.get("metric_name", "unknown")

        self.logger.critical(
            f"Resource saturation detected: {metric_name} at {
                utilization:.1%}")

        # Immediate resource reallocation
        reallocation_actions = [
            "Scale up resources",
            "Redistribute load",
            "Optimize resource usage"
        ]

        return {
            "action": "resource_reallocation_initiated",
            "resource": metric_name,
            "utilization": utilization,
            "reallocation_actions": reallocation_actions
        }

    async def _handle_quality_decline(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle quality decline feedback."""
        quality_score = signal.data.get("quality_score", 0.0)

        self.logger.warning(f"Quality decline detected: {quality_score}")

        # Quality enhancement actions
        enhancement_actions = [
            "Review quality metrics",
            "Implement quality improvements",
            "Enhance validation processes"
        ]

        return {
            "action": "quality_enhancement_initiated",
            "quality_score": quality_score,
            "enhancement_actions": enhancement_actions
        }

    async def _handle_agent_overload(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle agent overload feedback."""
        agent_load = signal.data.get("agent_load", 0.0)
        agent_id = signal.source

        self.logger.warning(
            f"Agent overload detected: {agent_id} at {agent_load:.1%}")

        # Predictive scaling actions
        scaling_actions = [
            "Assess agent capacity",
            "Redistribute tasks",
            "Scale agent resources"
        ]

        return {
            "action": "predictive_scaling_initiated",
            "agent_id": agent_id,
            "load": agent_load,
            "scaling_actions": scaling_actions
        }

    async def _handle_workflow_bottleneck(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle workflow bottleneck feedback."""
        bottleneck_info = signal.data.get("bottleneck_info", {})

        self.logger.warning(f"Workflow bottleneck detected: {bottleneck_info}")

        # Gradual optimization actions
        optimization_actions = [
            "Analyze bottleneck root cause",
            "Optimize workflow structure",
            "Implement parallel processing"
        ]

        return {
            "action": "workflow_optimization_initiated",
            "bottleneck_info": bottleneck_info,
            "optimization_actions": optimization_actions
        }

    async def _handle_predictive_alert(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle predictive alert feedback."""
        prediction_confidence = signal.data.get("prediction_confidence", 0.0)
        metric1 = signal.data.get("metric1")
        metric2 = signal.data.get("metric2")

        self.logger.info(
            f"Predictive alert: {metric1} -> {metric2} correlation (confidence: {prediction_confidence:.2f})")

        # Generate alert
        alert_info = {
            "type": "predictive_correlation",
            "metrics": [metric1, metric2],
            "confidence": prediction_confidence,
            "recommendation": f"Monitor {metric2} closely due to correlation with {metric1}"
        }

        return {
            "action": "alert_generated",
            "alert_info": alert_info
        }

    async def _handle_adaptive_learning(
            self, signal: FeedbackSignal) -> Dict[str, Any]:
        """Handle adaptive learning feedback."""
        metric_name = signal.data.get("metric_name")
        control_signal = signal.data.get("control_signal", 0.0)

        self.logger.debug(
            f"Adaptive learning update: {metric_name} control signal: {control_signal}")

        # Update learning parameters
        learning_updates = {
            "metric": metric_name,
            "control_signal": control_signal,
            "timestamp": datetime.now().isoformat()
        }

        return {
            "action": "learning_update_applied",
            "learning_updates": learning_updates
        }

    def get_feedback_status(self) -> Dict[str, Any]:
        """Get current feedback system status."""
        return {
            "running": self.running,
            "active_feedbacks": len(self.active_feedbacks),
            "feedback_queue_size": self.feedback_queue.qsize(),
            "processing_stats": dict(self.processing_stats),
            "average_response_time": statistics.mean(self.response_times) if self.response_times else 0.0,
            "rules_count": len(self.feedback_rules),
            "enabled_rules": len([r for r in self.feedback_rules.values() if r.enabled]),
            "current_metrics": self.current_metrics,
            "correlation_matrix_size": len(self.correlation_matrix),
            "adaptation_status": self.adaptive_controller.get_adaptation_status()
        }

    def get_feedback_analytics(self) -> Dict[str, Any]:
        """Get feedback system analytics."""
        # Calculate rule success rates
        rule_analytics = {}
        for rule_id, rule in self.feedback_rules.items():
            success_rate = rule.success_count / \
                rule.trigger_count if rule.trigger_count > 0 else 0.0
            rule_analytics[rule_id] = {
                "trigger_count": rule.trigger_count,
                "success_count": rule.success_count,
                "success_rate": success_rate,
                "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None}

        # Calculate feedback type distribution
        type_distribution = defaultdict(int)
        for entry in self.feedback_history:
            type_distribution[entry["signal"].type.value] += 1

        return {
            "rule_analytics": rule_analytics,
            "type_distribution": dict(type_distribution),
            "total_processed": len(self.feedback_history),
            "average_processing_time": statistics.mean(
                [entry["processing_time"] for entry in self.feedback_history]
            ) if self.feedback_history else 0.0
        }
