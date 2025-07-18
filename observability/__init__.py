"""
LeanVibe Agent Hive Observability System

This module provides comprehensive real-time observability for the LeanVibe Agent Hive
system, including hook management, event streaming, agent monitoring, and baseline metrics.
"""

from .baseline_metrics import (
    BaselineAnalyzer,
    BaselineMetric,
    MetricsCollector,
    PerformanceBaseline,
    baseline_analyzer,
    export_baseline_metrics,
    get_baseline_report,
    metrics_collector,
    start_baseline_monitoring,
    stop_baseline_monitoring,
)
from .hook_manager import (
    AgentMonitor,
    EventPriority,
    EventStream,
    HookEvent,
    HookManager,
    HookType,
    hook_manager,
    register_notification_hook,
    register_post_tool_use_hook,
    register_pre_tool_use_hook,
    start_observability_system,
    stop_observability_system,
    track_agent_error,
    track_performance_metrics,
    track_tool_use,
)

__version__ = "1.0.0"
__all__ = [
    # Hook Management
    "HookManager",
    "HookType",
    "EventPriority",
    "HookEvent",
    "EventStream",
    "AgentMonitor",
    "hook_manager",
    "start_observability_system",
    "stop_observability_system",
    "register_pre_tool_use_hook",
    "register_post_tool_use_hook",
    "register_notification_hook",
    "track_tool_use",
    "track_agent_error",
    "track_performance_metrics",

    # Baseline Metrics
    "BaselineMetric",
    "PerformanceBaseline",
    "MetricsCollector",
    "BaselineAnalyzer",
    "metrics_collector",
    "baseline_analyzer",
    "start_baseline_monitoring",
    "stop_baseline_monitoring",
    "get_baseline_report",
    "export_baseline_metrics"
]
