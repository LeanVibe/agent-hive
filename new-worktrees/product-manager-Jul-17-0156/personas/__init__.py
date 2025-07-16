"""
LeanVibe Agent Hive Persona Management System

This module provides comprehensive persona management including dynamic switching,
context compression, and performance optimization for specialized agent capabilities.
"""

from .persona_manager import (
    PersonaManager,
    PersonaType,
    PersonaConfig,
    PersonaContext,
    PersonaPerformanceMetrics,
    PersonaCapability,
    ContextCompressor,
    QualityValidator,
    CompressionLevel,
    persona_manager,
    activate_persona,
    switch_persona,
    find_optimal_persona,
    get_persona_capabilities,
    get_system_metrics
)

__version__ = "1.0.0"
__all__ = [
    # Core Classes
    "PersonaManager",
    "PersonaType",
    "PersonaConfig",
    "PersonaContext",
    "PersonaPerformanceMetrics",
    "PersonaCapability",
    "ContextCompressor",
    "QualityValidator",
    "CompressionLevel",
    
    # Global Instance
    "persona_manager",
    
    # Convenience Functions
    "activate_persona",
    "switch_persona",
    "find_optimal_persona",
    "get_persona_capabilities",
    "get_system_metrics"
]