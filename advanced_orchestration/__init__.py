"""
Advanced orchestration package for multi-agent coordination with ML enhancements.

This package provides components for:
- Multi-agent coordination and communication
- Resource management and allocation
- Auto-scaling and load balancing
- Fault tolerance and recovery
- Advanced ML pattern recognition and optimization
- Predictive analytics and resource forecasting
- Adaptive learning and continuous improvement
"""

from .cli_integration import EnhancedOrchestrationCLI
from .enhanced_coordination import EnhancedCoordinationProtocol
from .multi_agent_coordinator import MultiAgentCoordinator
from .resource_manager import ResourceManager
from .scaling_manager import ScalingManager
from .workflow_coordinator import WorkflowCoordinator

# ML Enhancement imports
try:
    pass

    ML_AVAILABLE = True

    __all__ = [
        'MultiAgentCoordinator',
        'ResourceManager',
        'ScalingManager',
        'WorkflowCoordinator',
        'EnhancedCoordinationProtocol',
        'EnhancedOrchestrationCLI',
        # ML components
        'PatternOptimizer',
        'PredictiveAnalytics',
        'AdaptiveLearning',
        'MLConfig',
        'PatternData',
        'AnalyticsResult',
        'LearningMetrics'
    ]

except ImportError:
    ML_AVAILABLE = False

    __all__ = [
        'MultiAgentCoordinator',
        'ResourceManager',
        'ScalingManager',
        'WorkflowCoordinator',
        'EnhancedCoordinationProtocol',
        'EnhancedOrchestrationCLI'
    ]

__version__ = '2.2.0'  # Updated for ML enhancements
