"""
Agent-Level Business Metrics Monitor.

Tracks critical business metrics for multi-agent coordination including:
- Task throughput per agent
- Conflict resolution rates
- Agent collaboration efficiency
- Cross-agent dependency resolution times
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
import threading
from collections import defaultdict, deque

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter


class BusinessMetricType(Enum):
    """Types of business metrics to track."""
    TASK_THROUGHPUT = "task_throughput"
    CONFLICT_RESOLUTION_RATE = "conflict_resolution_rate" 
    AGENT_COLLABORATION_EFFICIENCY = "agent_collaboration_efficiency"
    DEPENDENCY_RESOLUTION_TIME = "dependency_resolution_time"
    WORKFLOW_SUCCESS_RATE = "workflow_success_rate"
    AGENT_UTILIZATION = "agent_utilization"
    TASK_COMPLETION_QUALITY = "task_completion_quality"
    INTER_AGENT_COMMUNICATION_LATENCY = "inter_agent_communication_latency"


@dataclass
class BusinessMetric:
    """Individual business metric data point."""
    metric_type: BusinessMetricType
    value: float
    timestamp: datetime
    agent_id: str
    task_id: Optional[str] = None
    workflow_id: Optional[str] = None
    conflict_id: Optional[str] = None
    collaboration_context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None


@dataclass
class TaskThroughputMetric:
    """Task throughput measurement."""
    agent_id: str
    tasks_completed: int
    time_window: timedelta
    task_types: List[str]
    avg_completion_time: float
    timestamp: datetime


@dataclass
class ConflictResolutionMetric:
    """Conflict resolution measurement."""
    conflict_id: str
    participating_agents: List[str]
    resolution_time: float
    resolution_method: str
    success: bool
    complexity_score: float
    timestamp: datetime


@dataclass
class CollaborationEfficiencyMetric:
    """Agent collaboration efficiency measurement."""
    primary_agent: str
    collaborating_agents: List[str]
    task_id: str
    coordination_overhead: float
    communication_rounds: int
    parallel_efficiency: float
    success_rate: float
    timestamp: datetime


class BusinessMetricsMonitor:
    """Monitor and track agent-level business metrics."""
    
    def __init__(self, enable_tracing: bool = True):
        self.logger = logging.getLogger(__name__)
        self.enable_tracing = enable_tracing
        
        # Initialize OpenTelemetry tracing
        if enable_tracing:
            self._setup_tracing()
        
        # Metrics storage
        self.business_metrics: deque = deque(maxlen=50000)
        self.agent_task_counts: Dict[str, int] = defaultdict(int)
        self.agent_task_completion_times: Dict[str, List[float]] = defaultdict(list)
        self.conflict_resolution_history: List[ConflictResolutionMetric] = []
        self.collaboration_sessions: Dict[str, CollaborationEfficiencyMetric] = {}
        
        # Real-time tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.active_conflicts: Dict[str, Dict[str, Any]] = {}
        self.agent_states: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Performance thresholds
        self.throughput_thresholds = {
            "warning": 5.0,  # tasks per hour
            "critical": 2.0,
            "target": 10.0
        }
        
        self.conflict_resolution_thresholds = {
            "warning": 0.7,  # 70% success rate
            "critical": 0.5,
            "target": 0.9
        }
        
        # Monitoring thread
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        self.logger.info("BusinessMetricsMonitor initialized")
    
    def _setup_tracing(self) -> None:
        """Setup OpenTelemetry distributed tracing."""
        try:
            # Configure Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
                collector_endpoint="http://localhost:14268/api/traces",
            )
            
            # Setup tracer provider
            trace.set_tracer_provider(TracerProvider())
            tracer_provider = trace.get_tracer_provider()
            
            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            self.tracer = trace.get_tracer(__name__)
            self.logger.info("OpenTelemetry tracing configured with Jaeger")
            
        except Exception as e:
            self.logger.warning(f"Failed to setup tracing: {e}")
            self.enable_tracing = False
            self.tracer = None
    
    def start_monitoring(self) -> None:
        """Start business metrics monitoring."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Business metrics monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop business metrics monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Business metrics monitoring stopped")
    
    def start_task(self, agent_id: str, task_id: str, task_type: str, 
                   workflow_id: Optional[str] = None) -> Optional[str]:
        """Start tracking a new task."""
        trace_id = None
        
        if self.enable_tracing and self.tracer:
            with self.tracer.start_as_current_span(f"task_{task_type}") as span:
                span.set_attribute("agent.id", agent_id)
                span.set_attribute("task.id", task_id)
                span.set_attribute("task.type", task_type)
                if workflow_id:
                    span.set_attribute("workflow.id", workflow_id)
                trace_id = span.get_span_context().trace_id
        
        with self.lock:
            self.active_tasks[task_id] = {
                "agent_id": agent_id,
                "task_type": task_type,
                "workflow_id": workflow_id,
                "start_time": datetime.now(),
                "trace_id": trace_id
            }
        
        self.logger.debug(f"Task {task_id} started for agent {agent_id}")
        return str(trace_id) if trace_id else None
    
    def complete_task(self, task_id: str, success: bool = True, 
                     quality_score: Optional[float] = None) -> None:
        """Mark task as completed and record metrics."""
        with self.lock:
            if task_id not in self.active_tasks:
                self.logger.warning(f"Task {task_id} not found in active tasks")
                return
            
            task_info = self.active_tasks.pop(task_id)
            completion_time = datetime.now()
            duration = (completion_time - task_info["start_time"]).total_seconds()
            
            agent_id = task_info["agent_id"]
            
            # Record task completion
            self.agent_task_counts[agent_id] += 1
            self.agent_task_completion_times[agent_id].append(duration)
            
            # Keep only last 100 completion times per agent
            if len(self.agent_task_completion_times[agent_id]) > 100:
                self.agent_task_completion_times[agent_id] = \
                    self.agent_task_completion_times[agent_id][-100:]
            
            # Record business metrics
            self._record_task_completion_metrics(
                agent_id, task_id, duration, success, quality_score, completion_time
            )
        
        self.logger.debug(f"Task {task_id} completed by agent {agent_id} in {duration:.2f}s")
    
    def start_conflict_resolution(self, conflict_id: str, participating_agents: List[str],
                                 conflict_type: str, complexity_score: float = 1.0) -> None:
        """Start tracking conflict resolution."""
        with self.lock:
            self.active_conflicts[conflict_id] = {
                "participating_agents": participating_agents,
                "conflict_type": conflict_type,
                "complexity_score": complexity_score,
                "start_time": datetime.now(),
                "communication_rounds": 0
            }
        
        if self.enable_tracing and self.tracer:
            with self.tracer.start_as_current_span(f"conflict_resolution_{conflict_type}") as span:
                span.set_attribute("conflict.id", conflict_id)
                span.set_attribute("conflict.type", conflict_type)
                span.set_attribute("agents.count", len(participating_agents))
                span.set_attribute("conflict.complexity", complexity_score)
        
        self.logger.info(f"Conflict resolution {conflict_id} started with agents: {participating_agents}")
    
    def resolve_conflict(self, conflict_id: str, resolution_method: str, 
                        success: bool = True) -> None:
        """Mark conflict as resolved and record metrics."""
        with self.lock:
            if conflict_id not in self.active_conflicts:
                self.logger.warning(f"Conflict {conflict_id} not found in active conflicts")
                return
            
            conflict_info = self.active_conflicts.pop(conflict_id)
            resolution_time = (datetime.now() - conflict_info["start_time"]).total_seconds()
            
            metric = ConflictResolutionMetric(
                conflict_id=conflict_id,
                participating_agents=conflict_info["participating_agents"],
                resolution_time=resolution_time,
                resolution_method=resolution_method,
                success=success,
                complexity_score=conflict_info["complexity_score"],
                timestamp=datetime.now()
            )
            
            self.conflict_resolution_history.append(metric)
            
            # Keep only last 1000 conflict resolutions
            if len(self.conflict_resolution_history) > 1000:
                self.conflict_resolution_history = self.conflict_resolution_history[-1000:]
            
            # Record business metric
            self.record_business_metric(BusinessMetric(
                metric_type=BusinessMetricType.CONFLICT_RESOLUTION_RATE,
                value=1.0 if success else 0.0,
                timestamp=datetime.now(),
                agent_id=conflict_info["participating_agents"][0],  # Primary agent
                conflict_id=conflict_id,
                collaboration_context={
                    "resolution_time": resolution_time,
                    "participating_agents": conflict_info["participating_agents"],
                    "resolution_method": resolution_method,
                    "complexity_score": conflict_info["complexity_score"]
                }
            ))
        
        self.logger.info(f"Conflict {conflict_id} resolved in {resolution_time:.2f}s: {success}")
    
    def start_collaboration(self, primary_agent: str, collaborating_agents: List[str],
                           task_id: str) -> None:
        """Start tracking agent collaboration."""
        collaboration_key = f"{primary_agent}_{task_id}"
        
        with self.lock:
            self.collaboration_sessions[collaboration_key] = CollaborationEfficiencyMetric(
                primary_agent=primary_agent,
                collaborating_agents=collaborating_agents,
                task_id=task_id,
                coordination_overhead=0.0,
                communication_rounds=0,
                parallel_efficiency=0.0,
                success_rate=0.0,
                timestamp=datetime.now()
            )
        
        self.logger.debug(f"Collaboration started: {primary_agent} with {collaborating_agents}")
    
    def end_collaboration(self, primary_agent: str, task_id: str, success: bool = True) -> None:
        """End collaboration tracking and record efficiency metrics."""
        collaboration_key = f"{primary_agent}_{task_id}"
        
        with self.lock:
            if collaboration_key not in self.collaboration_sessions:
                return
            
            collaboration = self.collaboration_sessions.pop(collaboration_key)
            collaboration.success_rate = 1.0 if success else 0.0
            
            # Record collaboration efficiency metric
            efficiency = self._calculate_collaboration_efficiency(collaboration)
            
            self.record_business_metric(BusinessMetric(
                metric_type=BusinessMetricType.AGENT_COLLABORATION_EFFICIENCY,
                value=efficiency,
                timestamp=datetime.now(),
                agent_id=primary_agent,
                task_id=task_id,
                collaboration_context={
                    "collaborating_agents": collaboration.collaborating_agents,
                    "communication_rounds": collaboration.communication_rounds,
                    "coordination_overhead": collaboration.coordination_overhead,
                    "parallel_efficiency": collaboration.parallel_efficiency
                }
            ))
    
    def record_business_metric(self, metric: BusinessMetric) -> None:
        """Record a business metric."""
        with self.lock:
            self.business_metrics.append(metric)
        
        self.logger.debug(f"Business metric recorded: {metric.metric_type.value} = {metric.value}")
    
    def _record_task_completion_metrics(self, agent_id: str, task_id: str, 
                                      duration: float, success: bool,
                                      quality_score: Optional[float],
                                      timestamp: datetime) -> None:
        """Record task completion business metrics."""
        # Task throughput metric
        self.record_business_metric(BusinessMetric(
            metric_type=BusinessMetricType.TASK_THROUGHPUT,
            value=1.0,  # 1 task completed
            timestamp=timestamp,
            agent_id=agent_id,
            task_id=task_id
        ))
        
        # Task completion quality
        if quality_score is not None:
            self.record_business_metric(BusinessMetric(
                metric_type=BusinessMetricType.TASK_COMPLETION_QUALITY,
                value=quality_score,
                timestamp=timestamp,
                agent_id=agent_id,
                task_id=task_id
            ))
        
        # Agent utilization (inverse of completion time)
        utilization = min(1.0, 1.0 / max(0.1, duration))  # Cap at 1.0
        self.record_business_metric(BusinessMetric(
            metric_type=BusinessMetricType.AGENT_UTILIZATION,
            value=utilization,
            timestamp=timestamp,
            agent_id=agent_id,
            task_id=task_id
        ))
    
    def _calculate_collaboration_efficiency(self, collaboration: CollaborationEfficiencyMetric) -> float:
        """Calculate collaboration efficiency score."""
        # Base efficiency from success rate
        efficiency = collaboration.success_rate
        
        # Adjust for communication efficiency
        if collaboration.communication_rounds > 0:
            communication_efficiency = 1.0 / (1.0 + collaboration.communication_rounds * 0.1)
            efficiency *= communication_efficiency
        
        # Adjust for coordination overhead
        overhead_penalty = max(0.0, 1.0 - collaboration.coordination_overhead)
        efficiency *= overhead_penalty
        
        return min(1.0, max(0.0, efficiency))
    
    def _monitoring_loop(self) -> None:
        """Main business metrics monitoring loop."""
        while self.running:
            try:
                # Calculate and record throughput metrics
                self._calculate_throughput_metrics()
                
                # Calculate conflict resolution rates
                self._calculate_conflict_resolution_rates()
                
                # Analyze agent performance trends
                self._analyze_agent_performance_trends()
                
                # Clean up old data
                self._cleanup_old_data()
                
                time.sleep(60)  # Monitor every minute
                
            except Exception as e:
                self.logger.error(f"Error in business metrics monitoring loop: {e}")
                time.sleep(10)
    
    def _calculate_throughput_metrics(self) -> None:
        """Calculate and record throughput metrics for all agents."""
        current_time = datetime.now()
        one_hour_ago = current_time - timedelta(hours=1)
        
        for agent_id in self.agent_task_completion_times.keys():
            # Get tasks completed in last hour
            recent_completions = [
                t for t in self.agent_task_completion_times[agent_id]
                if t <= 3600  # Completed within last hour (duration <= 1 hour)
            ]
            
            if recent_completions:
                throughput = len(recent_completions)  # tasks per hour
                
                self.record_business_metric(BusinessMetric(
                    metric_type=BusinessMetricType.TASK_THROUGHPUT,
                    value=throughput,
                    timestamp=current_time,
                    agent_id=agent_id
                ))
    
    def _calculate_conflict_resolution_rates(self) -> None:
        """Calculate conflict resolution success rates."""
        current_time = datetime.now()
        one_hour_ago = current_time - timedelta(hours=1)
        
        # Get recent conflict resolutions
        recent_conflicts = [
            c for c in self.conflict_resolution_history
            if c.timestamp >= one_hour_ago
        ]
        
        if recent_conflicts:
            # Calculate overall success rate
            successful_resolutions = sum(1 for c in recent_conflicts if c.success)
            total_resolutions = len(recent_conflicts)
            success_rate = successful_resolutions / total_resolutions
            
            # Record for primary agents involved
            participating_agents = set()
            for conflict in recent_conflicts:
                participating_agents.update(conflict.participating_agents)
            
            for agent_id in participating_agents:
                self.record_business_metric(BusinessMetric(
                    metric_type=BusinessMetricType.CONFLICT_RESOLUTION_RATE,
                    value=success_rate,
                    timestamp=current_time,
                    agent_id=agent_id
                ))
    
    def _analyze_agent_performance_trends(self) -> None:
        """Analyze agent performance trends and log insights."""
        for agent_id in self.agent_task_completion_times.keys():
            completion_times = self.agent_task_completion_times[agent_id]
            
            if len(completion_times) >= 10:
                recent_avg = statistics.mean(completion_times[-10:])
                overall_avg = statistics.mean(completion_times)
                
                if recent_avg > overall_avg * 1.5:
                    self.logger.warning(f"Agent {agent_id} showing performance degradation")
                elif recent_avg < overall_avg * 0.7:
                    self.logger.info(f"Agent {agent_id} showing performance improvement")
    
    def _cleanup_old_data(self) -> None:
        """Clean up old metrics data."""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        # Clean up conflict resolution history
        self.conflict_resolution_history = [
            c for c in self.conflict_resolution_history
            if c.timestamp > cutoff_time
        ]
    
    def get_agent_throughput_report(self, agent_id: str, 
                                   time_period: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """Get throughput report for specific agent."""
        current_time = datetime.now()
        start_time = current_time - time_period
        
        # Filter metrics for this agent and time period
        agent_metrics = [
            m for m in self.business_metrics
            if (m.agent_id == agent_id and 
                m.metric_type == BusinessMetricType.TASK_THROUGHPUT and
                m.timestamp >= start_time)
        ]
        
        if not agent_metrics:
            return {"agent_id": agent_id, "throughput": 0, "status": "no_data"}
        
        total_tasks = sum(m.value for m in agent_metrics)
        hours = time_period.total_seconds() / 3600
        throughput_per_hour = total_tasks / hours if hours > 0 else 0
        
        # Determine status based on thresholds
        if throughput_per_hour >= self.throughput_thresholds["target"]:
            status = "excellent"
        elif throughput_per_hour >= self.throughput_thresholds["warning"]:
            status = "good"
        elif throughput_per_hour >= self.throughput_thresholds["critical"]:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "agent_id": agent_id,
            "time_period_hours": hours,
            "total_tasks": int(total_tasks),
            "throughput_per_hour": round(throughput_per_hour, 2),
            "status": status,
            "thresholds": self.throughput_thresholds
        }
    
    def get_conflict_resolution_report(self, time_period: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """Get conflict resolution report."""
        current_time = datetime.now()
        start_time = current_time - time_period
        
        recent_conflicts = [
            c for c in self.conflict_resolution_history
            if c.timestamp >= start_time
        ]
        
        if not recent_conflicts:
            return {"total_conflicts": 0, "success_rate": 0.0, "status": "no_data"}
        
        successful = sum(1 for c in recent_conflicts if c.success)
        total = len(recent_conflicts)
        success_rate = successful / total
        
        avg_resolution_time = statistics.mean([c.resolution_time for c in recent_conflicts])
        
        # Determine status
        if success_rate >= self.conflict_resolution_thresholds["target"]:
            status = "excellent"
        elif success_rate >= self.conflict_resolution_thresholds["warning"]:
            status = "good"
        elif success_rate >= self.conflict_resolution_thresholds["critical"]:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "time_period_hours": time_period.total_seconds() / 3600,
            "total_conflicts": total,
            "successful_resolutions": successful,
            "success_rate": round(success_rate, 3),
            "avg_resolution_time": round(avg_resolution_time, 2),
            "status": status,
            "thresholds": self.conflict_resolution_thresholds
        }
    
    def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Get real-time business metrics dashboard."""
        current_time = datetime.now()
        
        # Active tasks and conflicts
        active_task_count = len(self.active_tasks)
        active_conflict_count = len(self.active_conflicts)
        
        # Recent throughput (last hour)
        one_hour_ago = current_time - timedelta(hours=1)
        recent_throughput_metrics = [
            m for m in self.business_metrics
            if (m.metric_type == BusinessMetricType.TASK_THROUGHPUT and
                m.timestamp >= one_hour_ago)
        ]
        
        total_hourly_throughput = sum(m.value for m in recent_throughput_metrics)
        
        # Agent status summary
        agent_status = {}
        for agent_id in self.agent_task_completion_times.keys():
            throughput_report = self.get_agent_throughput_report(agent_id, timedelta(hours=1))
            agent_status[agent_id] = {
                "throughput_status": throughput_report["status"],
                "active_tasks": len([t for t in self.active_tasks.values() 
                                   if t["agent_id"] == agent_id])
            }
        
        return {
            "timestamp": current_time.isoformat(),
            "active_tasks": active_task_count,
            "active_conflicts": active_conflict_count,
            "total_hourly_throughput": int(total_hourly_throughput),
            "agent_status": agent_status,
            "system_health": "healthy" if active_conflict_count == 0 else "conflicts_active"
        }