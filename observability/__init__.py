"""
LeanVibe Agent Hive Observability System

This module provides comprehensive real-time observability for the LeanVibe Agent Hive
system, including hook management, event streaming, and agent monitoring.
"""

from .hook_manager import (
    HookManager,
    HookType,
    EventPriority,
    HookEvent,
    EventStream,
    AgentMonitor,
    hook_manager,
    start_observability_system,
    stop_observability_system,
    register_pre_tool_use_hook,
    register_post_tool_use_hook,
    register_notification_hook,
    track_tool_use,
    track_agent_error,
    track_performance_metrics
)

__version__ = "1.0.0"
__all__ = [
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
    "track_performance_metrics"
]