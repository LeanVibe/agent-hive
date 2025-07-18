"""
LeanVibe Agent Hive Persona Management System

This module provides comprehensive persona management including dynamic switching,
context compression, and performance optimization for specialized agent capabilities.
"""

from .persona_manager import (
    CompressionLevel,
    ContextCompressor,
    PersonaCapability,
    PersonaConfig,
    PersonaContext,
    PersonaManager,
    PersonaPerformanceMetrics,
    PersonaType,
    QualityValidator,
    activate_persona,
    find_optimal_persona,
    get_persona_capabilities,
    get_system_metrics,
    persona_manager,
    switch_persona,
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
