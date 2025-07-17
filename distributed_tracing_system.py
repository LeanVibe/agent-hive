"""
OpenTelemetry Distributed Tracing System for Multi-Agent Workflows.

Provides end-to-end visibility into agent coordination, task execution,
and cross-service interactions with comprehensive trace correlation.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from collections import defaultdict
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import extract, inject
from opentelemetry.baggage import get_baggage, set_baggage
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class WorkflowType(Enum):
    """Types of workflows to trace."""
    TASK_EXECUTION = "task_execution"
    AGENT_COORDINATION = "agent_coordination"
    CONFLICT_RESOLUTION = "conflict_resolution"
    DEPENDENCY_RESOLUTION = "dependency_resolution"
    BUSINESS_PROCESS = "business_process"
    SYSTEM_MAINTENANCE = "system_maintenance"


class SpanType(Enum):
    """Types of spans for categorization."""
    ROOT = "root"
    AGENT_OPERATION = "agent_operation"
    TASK = "task"
    COMMUNICATION = "communication"
    DEPENDENCY = "dependency"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    COORDINATION = "coordination"


@dataclass
class TraceContext:
    """Trace context for propagation between services."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    trace_flags: int
    baggage: Dict[str, str] = field(default_factory=dict)

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers for propagation."""
        headers = {}

        # Use OpenTelemetry propagator
        propagator = TraceContextTextMapPropagator()
        carrier = {}

        # Create a temporary span for propagation
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("temp_span") as span:
            propagator.inject(carrier)

        return carrier

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional['TraceContext']:
        """Create trace context from HTTP headers."""
        try:
            propagator = TraceContextTextMapPropagator()
            context = propagator.extract(headers)

            span = trace.get_current_span(context)
            if span == trace.INVALID_SPAN:
                return None

            span_context = span.get_span_context()

            return cls(
                trace_id=format(span_context.trace_id, '032x'),
                span_id=format(span_context.span_id, '016x'),
                parent_span_id=None,
                trace_flags=span_context.trace_flags
            )
        except Exception:
            return None


@dataclass
class WorkflowTrace:
    """Complete workflow trace information."""
    workflow_id: str
    workflow_type: WorkflowType
    root_trace_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    status: str
    participating_agents: List[str]
    total_spans: int
    error_spans: int
    tags: Dict[str, str] = field(default_factory=dict)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


class DistributedTracingSystem:
    """OpenTelemetry-based distributed tracing for multi-agent systems."""

    def __init__(self, service_name: str = "agent-hive",
                 jaeger_endpoint: str = "http://localhost:14268/api/traces",
                 enable_console_export: bool = False):
        self.logger = logging.getLogger(__name__)
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint

        # Tracing components
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None

        # Workflow tracking
        self.active_workflows: Dict[str, WorkflowTrace] = {}
        self.completed_workflows: List[WorkflowTrace] = []
        self.workflow_spans: Dict[str, List[str]] = defaultdict(list)  # workflow_id -> span_ids

        # Span tracking
        self.span_metadata: Dict[str, Dict[str, Any]] = {}
        self.agent_spans: Dict[str, List[str]] = defaultdict(list)  # agent_id -> span_ids

        # Configuration
        self.enable_console_export = enable_console_export
        self.max_completed_workflows = 1000

        # Thread safety
        self.lock = threading.Lock()

        # Initialize tracing
        self._setup_tracing()

        self.logger.info(f"DistributedTracingSystem initialized for service: {service_name}")

    def _setup_tracing(self) -> None:
        """Setup OpenTelemetry tracing configuration."""
        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "deployment.environment": "production"
            })

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)

            # Setup exporters
            exporters = []

            # Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
                collector_endpoint=self.jaeger_endpoint,
            )
            exporters.append(jaeger_exporter)

            # Console exporter for debugging
            if self.enable_console_export:
                console_exporter = ConsoleSpanExporter()
                exporters.append(console_exporter)

            # Add span processors
            for exporter in exporters:
                span_processor = BatchSpanProcessor(exporter)
                self.tracer_provider.add_span_processor(span_processor)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            self.logger.info("OpenTelemetry tracing configured successfully")

        except Exception as e:
            self.logger.error(f"Failed to setup tracing: {e}")
            # Fallback to no-op tracer
            self.tracer = trace.NoOpTracer()

    def start_workflow_trace(self, workflow_id: str, workflow_type: WorkflowType,
                           participating_agents: List[str],
                           tags: Optional[Dict[str, str]] = None) -> str:
        """Start tracing a new workflow."""
        if not self.tracer:
            return ""

        with self.lock:
            start_time = datetime.now()

            # Create root span for workflow
            span = self.tracer.start_span(
                name=f"workflow_{workflow_type.value}",
                attributes={
                    "workflow.id": workflow_id,
                    "workflow.type": workflow_type.value,
                    "workflow.agents": ",".join(participating_agents),
                    "workflow.start_time": start_time.isoformat(),
                    **(tags or {})
                }
            )

            trace_id = format(span.get_span_context().trace_id, '032x')

            # Create workflow trace record
            workflow_trace = WorkflowTrace(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                root_trace_id=trace_id,
                start_time=start_time,
                end_time=None,
                duration=None,
                status="active",
                participating_agents=participating_agents,
                total_spans=1,
                error_spans=0,
                tags=tags or {},
                custom_attributes={}
            )

            self.active_workflows[workflow_id] = workflow_trace

            # Store span metadata
            span_id = format(span.get_span_context().span_id, '016x')
            self.span_metadata[span_id] = {
                "workflow_id": workflow_id,
                "span_type": SpanType.ROOT.value,
                "agent_id": None,
                "start_time": start_time,
                "span_object": span
            }

            self.workflow_spans[workflow_id].append(span_id)

            self.logger.info(f"Started workflow trace: {workflow_id} (trace_id: {trace_id})")

            return trace_id

    @contextmanager
    def trace_agent_operation(self, agent_id: str, operation_name: str,
                            workflow_id: Optional[str] = None,
                            attributes: Optional[Dict[str, Any]] = None):
        """Context manager for tracing agent operations."""
        if not self.tracer:
            yield None
            return

        span_name = f"agent_{agent_id}_{operation_name}"

        with self.tracer.start_as_current_span(span_name) as span:
            # Set standard attributes
            span.set_attribute("agent.id", agent_id)
            span.set_attribute("operation.name", operation_name)
            span.set_attribute("span.type", SpanType.AGENT_OPERATION.value)

            if workflow_id:
                span.set_attribute("workflow.id", workflow_id)

            # Set custom attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            # Track span
            span_id = format(span.get_span_context().span_id, '016x')
            trace_id = format(span.get_span_context().trace_id, '032x')

            with self.lock:
                self.span_metadata[span_id] = {
                    "workflow_id": workflow_id,
                    "span_type": SpanType.AGENT_OPERATION.value,
                    "agent_id": agent_id,
                    "operation_name": operation_name,
                    "start_time": datetime.now(),
                    "span_object": span
                }

                self.agent_spans[agent_id].append(span_id)

                if workflow_id:
                    self.workflow_spans[workflow_id].append(span_id)
                    if workflow_id in self.active_workflows:
                        self.active_workflows[workflow_id].total_spans += 1

            try:
                yield span
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)

                with self.lock:
                    if workflow_id and workflow_id in self.active_workflows:
                        self.active_workflows[workflow_id].error_spans += 1

                raise

            finally:
                # Update span metadata
                with self.lock:
                    if span_id in self.span_metadata:
                        self.span_metadata[span_id]["end_time"] = datetime.now()

    @contextmanager
    def trace_task_execution(self, task_id: str, task_type: str, agent_id: str,
                           workflow_id: Optional[str] = None,
                           attributes: Optional[Dict[str, Any]] = None):
        """Context manager for tracing task execution."""
        if not self.tracer:
            yield None
            return

        span_name = f"task_{task_type}"

        with self.tracer.start_as_current_span(span_name) as span:
            # Set standard attributes
            span.set_attribute("task.id", task_id)
            span.set_attribute("task.type", task_type)
            span.set_attribute("agent.id", agent_id)
            span.set_attribute("span.type", SpanType.TASK.value)

            if workflow_id:
                span.set_attribute("workflow.id", workflow_id)

            # Set custom attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            # Track task progress
            span_id = format(span.get_span_context().span_id, '016x')

            with self.lock:
                self.span_metadata[span_id] = {
                    "workflow_id": workflow_id,
                    "span_type": SpanType.TASK.value,
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "task_type": task_type,
                    "start_time": datetime.now(),
                    "span_object": span
                }

                self.agent_spans[agent_id].append(span_id)

                if workflow_id:
                    self.workflow_spans[workflow_id].append(span_id)
                    if workflow_id in self.active_workflows:
                        self.active_workflows[workflow_id].total_spans += 1

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
                span.add_event("task_completed")

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.add_event("task_failed", {"error": str(e)})

                with self.lock:
                    if workflow_id and workflow_id in self.active_workflows:
                        self.active_workflows[workflow_id].error_spans += 1

                raise

            finally:
                with self.lock:
                    if span_id in self.span_metadata:
                        self.span_metadata[span_id]["end_time"] = datetime.now()

    @contextmanager
    def trace_agent_communication(self, sender_agent: str, receiver_agent: str,
                                message_type: str, workflow_id: Optional[str] = None,
                                attributes: Optional[Dict[str, Any]] = None):
        """Context manager for tracing inter-agent communication."""
        if not self.tracer:
            yield None
            return

        span_name = f"comm_{message_type}_{sender_agent}_to_{receiver_agent}"

        with self.tracer.start_as_current_span(span_name) as span:
            # Set communication attributes
            span.set_attribute("communication.sender", sender_agent)
            span.set_attribute("communication.receiver", receiver_agent)
            span.set_attribute("communication.type", message_type)
            span.set_attribute("span.type", SpanType.COMMUNICATION.value)

            if workflow_id:
                span.set_attribute("workflow.id", workflow_id)

            # Set custom attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            span_id = format(span.get_span_context().span_id, '016x')

            with self.lock:
                self.span_metadata[span_id] = {
                    "workflow_id": workflow_id,
                    "span_type": SpanType.COMMUNICATION.value,
                    "sender_agent": sender_agent,
                    "receiver_agent": receiver_agent,
                    "message_type": message_type,
                    "start_time": datetime.now(),
                    "span_object": span
                }

                # Add to both agents' span lists
                self.agent_spans[sender_agent].append(span_id)
                self.agent_spans[receiver_agent].append(span_id)

                if workflow_id:
                    self.workflow_spans[workflow_id].append(span_id)
                    if workflow_id in self.active_workflows:
                        self.active_workflows[workflow_id].total_spans += 1

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
                span.add_event("communication_successful")

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                span.add_event("communication_failed", {"error": str(e)})

                with self.lock:
                    if workflow_id and workflow_id in self.active_workflows:
                        self.active_workflows[workflow_id].error_spans += 1

                raise

            finally:
                with self.lock:
                    if span_id in self.span_metadata:
                        self.span_metadata[span_id]["end_time"] = datetime.now()

    def complete_workflow_trace(self, workflow_id: str, status: str = "completed",
                              final_attributes: Optional[Dict[str, Any]] = None) -> None:
        """Complete a workflow trace."""
        with self.lock:
            if workflow_id not in self.active_workflows:
                self.logger.warning(f"Workflow {workflow_id} not found in active workflows")
                return

            workflow_trace = self.active_workflows.pop(workflow_id)
            end_time = datetime.now()
            duration = (end_time - workflow_trace.start_time).total_seconds()

            # Update workflow trace
            workflow_trace.end_time = end_time
            workflow_trace.duration = duration
            workflow_trace.status = status

            if final_attributes:
                workflow_trace.custom_attributes.update(final_attributes)

            # Find and close root span
            root_spans = [
                span_id for span_id in self.workflow_spans[workflow_id]
                if (span_id in self.span_metadata and
                    self.span_metadata[span_id]["span_type"] == SpanType.ROOT.value)
            ]

            for span_id in root_spans:
                span_meta = self.span_metadata.get(span_id)
                if span_meta and "span_object" in span_meta:
                    span = span_meta["span_object"]
                    span.set_attribute("workflow.status", status)
                    span.set_attribute("workflow.duration", duration)
                    span.set_attribute("workflow.total_spans", workflow_trace.total_spans)
                    span.set_attribute("workflow.error_spans", workflow_trace.error_spans)

                    if final_attributes:
                        for key, value in final_attributes.items():
                            span.set_attribute(key, str(value))

                    if status == "failed":
                        span.set_status(Status(StatusCode.ERROR, "Workflow failed"))
                    else:
                        span.set_status(Status(StatusCode.OK))

                    span.end()

            # Move to completed workflows
            self.completed_workflows.append(workflow_trace)

            # Cleanup old completed workflows
            if len(self.completed_workflows) > self.max_completed_workflows:
                self.completed_workflows = self.completed_workflows[-self.max_completed_workflows:]

            self.logger.info(f"Completed workflow trace: {workflow_id} (duration: {duration:.2f}s, status: {status})")

    def get_trace_context(self) -> Optional[TraceContext]:
        """Get current trace context for propagation."""
        current_span = trace.get_current_span()
        if current_span == trace.INVALID_SPAN:
            return None

        span_context = current_span.get_span_context()

        return TraceContext(
            trace_id=format(span_context.trace_id, '032x'),
            span_id=format(span_context.span_id, '016x'),
            parent_span_id=None,
            trace_flags=span_context.trace_flags,
            baggage=dict(get_baggage())
        )

    def inject_trace_context(self, carrier: Dict[str, str]) -> None:
        """Inject trace context into carrier (e.g., HTTP headers)."""
        propagator = TraceContextTextMapPropagator()
        propagator.inject(carrier)

    def extract_trace_context(self, carrier: Dict[str, str]) -> Any:
        """Extract trace context from carrier and set as current."""
        propagator = TraceContextTextMapPropagator()
        return propagator.extract(carrier)

    def add_span_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to current span."""
        current_span = trace.get_current_span()
        if current_span != trace.INVALID_SPAN:
            current_span.add_event(event_name, attributes or {})

    def set_span_attribute(self, key: str, value: Any) -> None:
        """Set attribute on current span."""
        current_span = trace.get_current_span()
        if current_span != trace.INVALID_SPAN:
            current_span.set_attribute(key, str(value))

    def get_workflow_trace_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of workflow trace."""
        with self.lock:
            # Check active workflows
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                return self._format_workflow_summary(workflow, "active")

            # Check completed workflows
            for workflow in self.completed_workflows:
                if workflow.workflow_id == workflow_id:
                    return self._format_workflow_summary(workflow, "completed")

            return None

    def _format_workflow_summary(self, workflow: WorkflowTrace, state: str) -> Dict[str, Any]:
        """Format workflow summary for API response."""
        return {
            "workflow_id": workflow.workflow_id,
            "workflow_type": workflow.workflow_type.value,
            "trace_id": workflow.root_trace_id,
            "state": state,
            "start_time": workflow.start_time.isoformat(),
            "end_time": workflow.end_time.isoformat() if workflow.end_time else None,
            "duration": workflow.duration,
            "status": workflow.status,
            "participating_agents": workflow.participating_agents,
            "total_spans": workflow.total_spans,
            "error_spans": workflow.error_spans,
            "success_rate": (workflow.total_spans - workflow.error_spans) / max(1, workflow.total_spans),
            "tags": workflow.tags,
            "custom_attributes": workflow.custom_attributes
        }

    def get_agent_trace_summary(self, agent_id: str, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get trace summary for specific agent."""
        current_time = datetime.now()
        start_time = current_time - time_window

        with self.lock:
            agent_span_ids = self.agent_spans.get(agent_id, [])

            # Filter spans by time window
            recent_spans = []
            for span_id in agent_span_ids:
                span_meta = self.span_metadata.get(span_id)
                if span_meta and span_meta["start_time"] >= start_time:
                    recent_spans.append(span_meta)

            # Calculate metrics
            total_spans = len(recent_spans)
            error_spans = sum(1 for span in recent_spans if span.get("error", False))
            task_spans = [s for s in recent_spans if s["span_type"] == SpanType.TASK.value]
            comm_spans = [s for s in recent_spans if s["span_type"] == SpanType.COMMUNICATION.value]

            # Calculate durations for completed spans
            completed_spans = [s for s in recent_spans if "end_time" in s]
            avg_duration = 0.0
            if completed_spans:
                durations = [(s["end_time"] - s["start_time"]).total_seconds() for s in completed_spans]
                avg_duration = sum(durations) / len(durations)

            return {
                "agent_id": agent_id,
                "time_window_hours": time_window.total_seconds() / 3600,
                "total_spans": total_spans,
                "error_spans": error_spans,
                "success_rate": (total_spans - error_spans) / max(1, total_spans),
                "task_spans": len(task_spans),
                "communication_spans": len(comm_spans),
                "avg_span_duration": avg_duration,
                "active_workflows": len(set(
                    span["workflow_id"] for span in recent_spans
                    if span["workflow_id"] and span["workflow_id"] in self.active_workflows
                ))
            }

    def get_system_trace_overview(self) -> Dict[str, Any]:
        """Get system-wide tracing overview."""
        current_time = datetime.now()

        with self.lock:
            # Active workflows stats
            active_count = len(self.active_workflows)
            active_agents = set()
            total_active_spans = 0

            for workflow in self.active_workflows.values():
                active_agents.update(workflow.participating_agents)
                total_active_spans += workflow.total_spans

            # Recent completed workflows (last hour)
            one_hour_ago = current_time - timedelta(hours=1)
            recent_completed = [
                w for w in self.completed_workflows
                if w.end_time and w.end_time >= one_hour_ago
            ]

            # Calculate success rate
            total_recent = len(recent_completed)
            successful_recent = len([w for w in recent_completed if w.status == "completed"])
            success_rate = successful_recent / max(1, total_recent)

            # Average workflow duration
            avg_duration = 0.0
            if recent_completed:
                durations = [w.duration for w in recent_completed if w.duration]
                avg_duration = sum(durations) / len(durations) if durations else 0.0

            return {
                "timestamp": current_time.isoformat(),
                "active_workflows": active_count,
                "active_agents": len(active_agents),
                "total_active_spans": total_active_spans,
                "completed_workflows_1h": total_recent,
                "workflow_success_rate": success_rate,
                "avg_workflow_duration": avg_duration,
                "total_agents_tracked": len(self.agent_spans),
                "total_spans_tracked": len(self.span_metadata),
                "tracing_enabled": self.tracer is not None and not isinstance(self.tracer, trace.NoOpTracer)
            }

    def cleanup_old_data(self, retention_hours: int = 24) -> None:
        """Clean up old span metadata and completed workflows."""
        cutoff_time = datetime.now() - timedelta(hours=retention_hours)

        with self.lock:
            # Clean up old span metadata
            old_span_ids = [
                span_id for span_id, meta in self.span_metadata.items()
                if meta["start_time"] < cutoff_time
            ]

            for span_id in old_span_ids:
                del self.span_metadata[span_id]

                # Remove from agent spans
                for agent_spans in self.agent_spans.values():
                    if span_id in agent_spans:
                        agent_spans.remove(span_id)

                # Remove from workflow spans
                for workflow_spans in self.workflow_spans.values():
                    if span_id in workflow_spans:
                        workflow_spans.remove(span_id)

            # Clean up old completed workflows
            self.completed_workflows = [
                w for w in self.completed_workflows
                if w.end_time is None or w.end_time >= cutoff_time
            ]

            self.logger.info(f"Cleaned up {len(old_span_ids)} old spans and old workflows")

    def shutdown(self) -> None:
        """Shutdown tracing system gracefully."""
        if self.tracer_provider:
            # Complete any active workflows
            with self.lock:
                for workflow_id in list(self.active_workflows.keys()):
                    self.complete_workflow_trace(workflow_id, "shutdown")

            # Force flush and shutdown
            self.tracer_provider.force_flush(timeout_millis=5000)
            self.tracer_provider.shutdown()

            self.logger.info("Distributed tracing system shutdown completed")
