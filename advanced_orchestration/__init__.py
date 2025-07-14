"""
Advanced orchestration package for multi-agent coordination.

This package provides components for:
- Multi-agent coordination and communication
- Resource management and allocation
- Auto-scaling and load balancing
- Fault tolerance and recovery
"""

from .multi_agent_coordinator import MultiAgentCoordinator
from .resource_manager import ResourceManager
from .scaling_manager import ScalingManager

__all__ = [
    'MultiAgentCoordinator',
    'ResourceManager', 
    'ScalingManager'
]