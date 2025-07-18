"""
Coordination Protocols module for LeanVibe Agent Hive.

This module provides advanced coordination and communication protocols
for multi-agent systems.
"""

from .automated_coordination_orchestrator import AutomatedCoordinationOrchestrator
from .cross_agent_protocols import CrossAgentCoordinator, CoordinationMessage
from .component_workflow import ComponentWorkflowManager

__all__ = [
    'AutomatedCoordinationOrchestrator',
    'CrossAgentCoordinator',
    'CoordinationMessage',
    'ComponentWorkflowManager'
]