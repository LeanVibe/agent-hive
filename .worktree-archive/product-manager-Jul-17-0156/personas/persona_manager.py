#!/usr/bin/env python3
"""
Persona Manager for LeanVibe Agent Hive SuperClaude Integration

Provides comprehensive persona management including dynamic switching,
context compression, and performance optimization for specialized agent capabilities.
"""

import json
import logging
import yaml
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import hashlib
import re
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PersonaType(Enum):
    """Types of personas available in the system."""
    ARCHITECT = "architect"
    SECURITY = "security"
    FRONTEND = "frontend"
    BACKEND = "backend"
    PERFORMANCE = "performance"
    QA = "qa"
    DEVOPS = "devops"
    ANALYST = "analyst"
    MENTOR = "mentor"
    REVIEWER = "reviewer"


class CompressionLevel(Enum):
    """Context compression levels."""
    LIGHT = 0.3    # 30% reduction
    MEDIUM = 0.5   # 50% reduction
    HEAVY = 0.7    # 70% reduction
    ULTRA = 0.8    # 80% reduction


@dataclass
class PersonaCapability:
    """Represents a specific capability of a persona."""
    name: str
    description: str
    proficiency: float  # 0.0 to 1.0
    keywords: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class PersonaConfig:
    """Configuration for a specific persona."""
    name: str
    persona_type: PersonaType
    title: str
    experience: str
    capabilities: List[PersonaCapability]
    expertise_areas: List[str]
    personality_traits: List[str]
    context_optimization: Dict[str, Any]
    prompt_template: str
    compression_level: CompressionLevel = CompressionLevel.MEDIUM
    token_reduction_target: float = 0.7
    quality_threshold: float = 0.95
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PersonaContext:
    """Context for a persona including compressed state and metadata."""
    persona_name: str
    original_context: Dict[str, Any]
    compressed_context: Dict[str, Any]
    compression_stats: Dict[str, float]
    quality_score: float
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    token_count: int = 0
    compressed_token_count: int = 0


@dataclass
class PersonaPerformanceMetrics:
    """Performance metrics for a persona."""
    persona_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_response_time: float = 0.0
    avg_quality_score: float = 0.0
    avg_token_reduction: float = 0.0
    avg_compression_time: float = 0.0
    effectiveness_score: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class ContextCompressor:
    """Handles context compression and optimization."""

    def __init__(self):
        self.compression_cache = {}
        self.quality_validator = QualityValidator()

    def compress_context(self, context: Dict[str, Any], persona_config: PersonaConfig) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Compress context based on persona configuration.

        Args:
            context: Original context to compress
            persona_config: Persona configuration with compression settings

        Returns:
            Tuple of (compressed_context, compression_stats)
        """
        start_time = time.time()

        # Calculate original token count
        original_tokens = self._estimate_tokens(context)

        # Apply compression based on persona type
        if persona_config.persona_type == PersonaType.ARCHITECT:
            compressed_context = self._compress_architecture_context(context, persona_config)
        elif persona_config.persona_type == PersonaType.SECURITY:
            compressed_context = self._compress_security_context(context, persona_config)
        elif persona_config.persona_type == PersonaType.FRONTEND:
            compressed_context = self._compress_frontend_context(context, persona_config)
        elif persona_config.persona_type == PersonaType.BACKEND:
            compressed_context = self._compress_backend_context(context, persona_config)
        elif persona_config.persona_type == PersonaType.PERFORMANCE:
            compressed_context = self._compress_performance_context(context, persona_config)
        else:
            compressed_context = self._compress_general_context(context, persona_config)

        # Calculate compressed token count
        compressed_tokens = self._estimate_tokens(compressed_context)

        # Calculate compression statistics
        compression_time = time.time() - start_time
        token_reduction = 1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0.0

        compression_stats = {
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            'token_reduction': token_reduction,
            'compression_time': compression_time,
            'compression_ratio': compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        }

        return compressed_context, compression_stats

    def _estimate_tokens(self, context: Dict[str, Any]) -> int:
        """Estimate token count for context."""
        text = json.dumps(context, separators=(',', ':'))
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4

    def _compress_architecture_context(self, context: Dict[str, Any], config: PersonaConfig) -> Dict[str, Any]:
        """Compress context for architecture persona."""
        compressed = {}

        # Keep essential architecture information
        if 'system_design' in context:
            compressed['system_design'] = context['system_design']
        if 'architecture_patterns' in context:
            compressed['architecture_patterns'] = context['architecture_patterns']
        if 'scalability_requirements' in context:
            compressed['scalability_requirements'] = context['scalability_requirements']

        # Compress code snippets to focus on structure
        if 'code' in context:
            compressed['code'] = self._compress_code_for_architecture(context['code'])

        # Summarize non-architecture content
        if 'description' in context:
            compressed['description'] = self._summarize_text(context['description'], max_length=200)

        return compressed

    def _compress_security_context(self, context: Dict[str, Any], config: PersonaConfig) -> Dict[str, Any]:
        """Compress context for security persona."""
        compressed = {}

        # Keep security-relevant information
        security_keys = ['security_requirements', 'threat_model', 'vulnerabilities', 'compliance']
        for key in security_keys:
            if key in context:
                compressed[key] = context[key]

        # Focus on security-relevant code
        if 'code' in context:
            compressed['code'] = self._extract_security_relevant_code(context['code'])

        return compressed

    def _compress_frontend_context(self, context: Dict[str, Any], config: PersonaConfig) -> Dict[str, Any]:
        """Compress context for frontend persona."""
        compressed = {}

        # Keep UI/UX relevant information
        frontend_keys = ['ui_requirements', 'user_experience', 'accessibility', 'performance']
        for key in frontend_keys:
            if key in context:
                compressed[key] = context[key]

        # Focus on frontend code
        if 'code' in context:
            compressed['code'] = self._extract_frontend_code(context['code'])

        return compressed

    def _compress_backend_context(self, context: Dict[str, Any], config: PersonaConfig) -> Dict[str, Any]:
        """Compress context for backend persona."""
        compressed = {}

        # Keep backend-relevant information
        backend_keys = ['api_design', 'database_schema', 'business_logic', 'integrations']
        for key in backend_keys:
            if key in context:
                compressed[key] = context[key]

        # Focus on backend code
        if 'code' in context:
            compressed['code'] = self._extract_backend_code(context['code'])

        return compressed

    def _compress_performance_context(self, context: Dict[str, Any], config: PersonaConfig) -> Dict[str, Any]:
        """Compress context for performance persona."""
        compressed = {}

        # Keep performance-relevant information
        performance_keys = ['performance_requirements', 'benchmarks', 'bottlenecks', 'optimization']
        for key in performance_keys:
            if key in context:
                compressed[key] = context[key]

        # Focus on performance-critical code
        if 'code' in context:
            compressed['code'] = self._extract_performance_critical_code(context['code'])

        return compressed

    def _compress_general_context(self, context: Dict[str, Any], config: PersonaConfig) -> Dict[str, Any]:
        """General context compression."""
        compressed = {}

        # Keep essential information based on compression level
        compression_ratio = config.compression_level.value

        # Prioritize based on persona expertise areas
        for key, value in context.items():
            if any(area.lower() in key.lower() for area in config.expertise_areas):
                compressed[key] = value
            elif len(compressed) < len(context) * (1 - compression_ratio):
                compressed[key] = value

        return compressed

    def _compress_code_for_architecture(self, code: str) -> str:
        """Compress code to focus on architectural elements."""
        # Extract class definitions, function signatures, imports
        lines = code.split('\n')
        important_lines = []

        for line in lines:
            stripped = line.strip()
            if (stripped.startswith('class ') or
                stripped.startswith('def ') or
                stripped.startswith('import ') or
                stripped.startswith('from ') or
                stripped.startswith('@')):
                important_lines.append(line)

        return '\n'.join(important_lines)

    def _extract_security_relevant_code(self, code: str) -> str:
        """Extract security-relevant code sections."""
        # Look for security-related patterns
        security_patterns = [
            r'auth', r'token', r'password', r'encrypt', r'decrypt',
            r'security', r'vulnerability', r'validate', r'sanitize'
        ]

        lines = code.split('\n')
        relevant_lines = []

        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in security_patterns):
                relevant_lines.append(line)

        return '\n'.join(relevant_lines)

    def _extract_frontend_code(self, code: str) -> str:
        """Extract frontend-relevant code sections."""
        # Look for UI/frontend patterns
        frontend_patterns = [
            r'render', r'component', r'props', r'state', r'event',
            r'css', r'style', r'html', r'dom', r'ui', r'ux'
        ]

        lines = code.split('\n')
        relevant_lines = []

        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in frontend_patterns):
                relevant_lines.append(line)

        return '\n'.join(relevant_lines)

    def _extract_backend_code(self, code: str) -> str:
        """Extract backend-relevant code sections."""
        # Look for backend patterns
        backend_patterns = [
            r'api', r'endpoint', r'route', r'handler', r'service',
            r'database', r'db', r'query', r'model', r'schema'
        ]

        lines = code.split('\n')
        relevant_lines = []

        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in backend_patterns):
                relevant_lines.append(line)

        return '\n'.join(relevant_lines)

    def _extract_performance_critical_code(self, code: str) -> str:
        """Extract performance-critical code sections."""
        # Look for performance patterns
        performance_patterns = [
            r'loop', r'for', r'while', r'async', r'await',
            r'cache', r'optimize', r'performance', r'benchmark'
        ]

        lines = code.split('\n')
        relevant_lines = []

        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in performance_patterns):
                relevant_lines.append(line)

        return '\n'.join(relevant_lines)

    def _summarize_text(self, text: str, max_length: int = 500) -> str:
        """Summarize text to maximum length."""
        if len(text) <= max_length:
            return text

        # Simple summarization - take first sentences up to max_length
        sentences = text.split('. ')
        summary = ""

        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + ". "
            else:
                break

        return summary.strip()


class QualityValidator:
    """Validates quality of compressed contexts."""

    def validate_compression_quality(self, original: Dict[str, Any], compressed: Dict[str, Any]) -> float:
        """
        Validate quality of compression.

        Args:
            original: Original context
            compressed: Compressed context

        Returns:
            Quality score (0.0 to 1.0)
        """
        # Simple quality scoring based on information retention
        original_keys = set(original.keys())
        compressed_keys = set(compressed.keys())

        # Key retention score
        key_retention = len(compressed_keys) / len(original_keys) if original_keys else 1.0

        # Content preservation score
        content_preservation = self._calculate_content_preservation(original, compressed)

        # Essential information score
        essential_info_score = self._calculate_essential_info_score(original, compressed)

        # Weighted average
        quality_score = (key_retention * 0.3 + content_preservation * 0.4 + essential_info_score * 0.3)

        return min(1.0, quality_score)

    def _calculate_content_preservation(self, original: Dict[str, Any], compressed: Dict[str, Any]) -> float:
        """Calculate how well content is preserved."""
        preservation_score = 0.0
        total_items = 0

        for key in compressed.keys():
            if key in original:
                total_items += 1
                if original[key] == compressed[key]:
                    preservation_score += 1.0
                else:
                    # Partial preservation for modified content
                    preservation_score += 0.5

        return preservation_score / total_items if total_items > 0 else 0.0

    def _calculate_essential_info_score(self, original: Dict[str, Any], compressed: Dict[str, Any]) -> float:
        """Calculate preservation of essential information."""
        essential_keys = ['description', 'requirements', 'code', 'context']
        essential_score = 0.0
        total_essential = 0

        for key in essential_keys:
            if key in original:
                total_essential += 1
                if key in compressed:
                    essential_score += 1.0

        return essential_score / total_essential if total_essential > 0 else 1.0


class PersonaManager:
    """Main persona management system."""

    def __init__(self, personas_dir: str = "personas"):
        """
        Initialize PersonaManager.

        Args:
            personas_dir: Directory containing persona configurations
        """
        self.personas_dir = Path(personas_dir)
        self.personas: Dict[str, PersonaConfig] = {}
        self.active_contexts: Dict[str, PersonaContext] = {}
        self.performance_metrics: Dict[str, PersonaPerformanceMetrics] = {}
        self.context_compressor = ContextCompressor()
        self.quality_validator = QualityValidator()

        # Load personas from configuration
        self._load_personas()

        # Initialize performance metrics
        self._initialize_performance_metrics()

    def _load_personas(self):
        """Load persona configurations from YAML files."""
        try:
            # Load default SuperClaude personas
            self._load_default_personas()

            # Load custom personas from directory
            if self.personas_dir.exists():
                for persona_file in self.personas_dir.glob("*.yaml"):
                    try:
                        with open(persona_file, 'r') as f:
                            persona_data = yaml.safe_load(f)
                            persona_config = self._create_persona_config(persona_data)
                            self.personas[persona_config.name] = persona_config
                    except Exception as e:
                        logger.error(f"Failed to load persona from {persona_file}: {e}")

            logger.info(f"Loaded {len(self.personas)} personas")
        except Exception as e:
            logger.error(f"Failed to load personas: {e}")

    def _load_default_personas(self):
        """Load default SuperClaude personas."""
        default_personas = {
            "architect": {
                "name": "architect",
                "persona_type": PersonaType.ARCHITECT,
                "title": "Senior Software Architect",
                "experience": "12+ years in software design and architecture",
                "expertise_areas": ["architecture", "design", "scalability", "patterns"],
                "personality_traits": ["strategic", "methodical", "quality-focused"],
                "compression_level": CompressionLevel.MEDIUM,
                "token_reduction_target": 0.65
            },
            "security": {
                "name": "security",
                "persona_type": PersonaType.SECURITY,
                "title": "Security Architect",
                "experience": "10+ years in cybersecurity and threat analysis",
                "expertise_areas": ["security", "compliance", "threats", "vulnerabilities"],
                "personality_traits": ["vigilant", "thorough", "risk-aware"],
                "compression_level": CompressionLevel.HEAVY,
                "token_reduction_target": 0.70
            },
            "frontend": {
                "name": "frontend",
                "persona_type": PersonaType.FRONTEND,
                "title": "Frontend Architect",
                "experience": "8+ years in UI/UX and frontend development",
                "expertise_areas": ["ui", "ux", "frontend", "performance", "accessibility"],
                "personality_traits": ["user-focused", "creative", "detail-oriented"],
                "compression_level": CompressionLevel.MEDIUM,
                "token_reduction_target": 0.68
            },
            "backend": {
                "name": "backend",
                "persona_type": PersonaType.BACKEND,
                "title": "Backend Architect",
                "experience": "10+ years in backend systems and API design",
                "expertise_areas": ["api", "database", "services", "integration"],
                "personality_traits": ["systematic", "reliable", "performance-focused"],
                "compression_level": CompressionLevel.MEDIUM,
                "token_reduction_target": 0.68
            },
            "performance": {
                "name": "performance",
                "persona_type": PersonaType.PERFORMANCE,
                "title": "Performance Engineer",
                "experience": "8+ years in performance optimization",
                "expertise_areas": ["performance", "optimization", "benchmarking", "profiling"],
                "personality_traits": ["analytical", "precise", "optimization-focused"],
                "compression_level": CompressionLevel.HEAVY,
                "token_reduction_target": 0.75
            }
        }

        for persona_name, persona_data in default_personas.items():
            persona_config = self._create_persona_config(persona_data)
            self.personas[persona_name] = persona_config

    def _create_persona_config(self, persona_data: Dict[str, Any]) -> PersonaConfig:
        """Create PersonaConfig from dictionary data."""
        return PersonaConfig(
            name=persona_data["name"],
            persona_type=persona_data.get("persona_type", PersonaType.ANALYST),
            title=persona_data.get("title", "Specialist"),
            experience=persona_data.get("experience", "5+ years"),
            capabilities=[],  # Will be populated from expertise_areas
            expertise_areas=persona_data.get("expertise_areas", []),
            personality_traits=persona_data.get("personality_traits", []),
            context_optimization=persona_data.get("context_optimization", {}),
            prompt_template=persona_data.get("prompt_template", ""),
            compression_level=persona_data.get("compression_level", CompressionLevel.MEDIUM),
            token_reduction_target=persona_data.get("token_reduction_target", 0.7)
        )

    def _initialize_performance_metrics(self):
        """Initialize performance metrics for all personas."""
        for persona_name in self.personas:
            self.performance_metrics[persona_name] = PersonaPerformanceMetrics(
                persona_name=persona_name
            )

    def activate_persona(self, persona_name: str, context: Dict[str, Any], session_id: str = None) -> PersonaContext:
        """
        Activate a persona with given context.

        Args:
            persona_name: Name of persona to activate
            context: Context to optimize for persona
            session_id: Optional session identifier

        Returns:
            PersonaContext with optimized context
        """
        if persona_name not in self.personas:
            raise ValueError(f"Persona '{persona_name}' not found")

        persona_config = self.personas[persona_name]

        if not persona_config.enabled:
            raise ValueError(f"Persona '{persona_name}' is disabled")

        # Generate session ID if not provided
        if session_id is None:
            session_id = self._generate_session_id(persona_name, context)

        # Compress context for persona
        compressed_context, compression_stats = self.context_compressor.compress_context(
            context, persona_config
        )

        # Validate compression quality
        quality_score = self.quality_validator.validate_compression_quality(
            context, compressed_context
        )

        # Create persona context
        persona_context = PersonaContext(
            persona_name=persona_name,
            original_context=context,
            compressed_context=compressed_context,
            compression_stats=compression_stats,
            quality_score=quality_score,
            session_id=session_id,
            token_count=compression_stats['original_tokens'],
            compressed_token_count=compression_stats['compressed_tokens']
        )

        # Store active context
        self.active_contexts[session_id] = persona_context

        # Update performance metrics
        self._update_performance_metrics(persona_name, quality_score, compression_stats)

        logger.info(f"Activated persona '{persona_name}' with {compression_stats['token_reduction']:.1%} token reduction")

        return persona_context

    def switch_persona(self, from_persona: str, to_persona: str, context: Dict[str, Any], session_id: str = None) -> PersonaContext:
        """
        Switch from one persona to another.

        Args:
            from_persona: Current persona name
            to_persona: Target persona name
            context: Context for new persona
            session_id: Session identifier

        Returns:
            PersonaContext for new persona
        """
        # Deactivate current persona if active
        if session_id and session_id in self.active_contexts:
            current_context = self.active_contexts[session_id]
            current_context.last_used = datetime.now()
            current_context.usage_count += 1

        # Activate new persona
        return self.activate_persona(to_persona, context, session_id)

    def get_persona_capabilities(self, persona_name: str) -> List[str]:
        """
        Get capabilities of a specific persona.

        Args:
            persona_name: Name of persona

        Returns:
            List of capability names
        """
        if persona_name not in self.personas:
            return []

        persona_config = self.personas[persona_name]
        return persona_config.expertise_areas

    def find_optimal_persona(self, required_capabilities: List[str]) -> str:
        """
        Find the optimal persona for given capabilities.

        Args:
            required_capabilities: List of required capabilities

        Returns:
            Name of optimal persona
        """
        best_persona = None
        best_score = 0.0

        for persona_name, persona_config in self.personas.items():
            if not persona_config.enabled:
                continue

            # Calculate capability match score
            capability_score = self._calculate_capability_score(
                required_capabilities, persona_config.expertise_areas
            )

            # Factor in performance metrics
            performance_score = self.performance_metrics[persona_name].effectiveness_score

            # Combined score
            combined_score = capability_score * 0.7 + performance_score * 0.3

            if combined_score > best_score:
                best_score = combined_score
                best_persona = persona_name

        return best_persona or "analyst"  # Default fallback

    def _calculate_capability_score(self, required: List[str], available: List[str]) -> float:
        """Calculate capability match score."""
        if not required:
            return 0.0

        matches = 0
        for req_cap in required:
            for avail_cap in available:
                if req_cap.lower() in avail_cap.lower() or avail_cap.lower() in req_cap.lower():
                    matches += 1
                    break

        return matches / len(required)

    def get_persona_performance(self, persona_name: str) -> PersonaPerformanceMetrics:
        """
        Get performance metrics for a persona.

        Args:
            persona_name: Name of persona

        Returns:
            PersonaPerformanceMetrics
        """
        return self.performance_metrics.get(persona_name, PersonaPerformanceMetrics(persona_name))

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        return {
            "total_personas": len(self.personas),
            "active_contexts": len(self.active_contexts),
            "enabled_personas": len([p for p in self.personas.values() if p.enabled]),
            "avg_token_reduction": self._calculate_avg_token_reduction(),
            "avg_quality_score": self._calculate_avg_quality_score(),
            "persona_performance": {
                name: asdict(metrics) for name, metrics in self.performance_metrics.items()
            }
        }

    def _calculate_avg_token_reduction(self) -> float:
        """Calculate average token reduction across all personas."""
        total_reduction = 0.0
        count = 0

        for metrics in self.performance_metrics.values():
            if metrics.total_tasks > 0:
                total_reduction += metrics.avg_token_reduction
                count += 1

        return total_reduction / count if count > 0 else 0.0

    def _calculate_avg_quality_score(self) -> float:
        """Calculate average quality score across all personas."""
        total_quality = 0.0
        count = 0

        for metrics in self.performance_metrics.values():
            if metrics.total_tasks > 0:
                total_quality += metrics.avg_quality_score
                count += 1

        return total_quality / count if count > 0 else 0.0

    def _update_performance_metrics(self, persona_name: str, quality_score: float, compression_stats: Dict[str, float]):
        """Update performance metrics for a persona."""
        if persona_name not in self.performance_metrics:
            self.performance_metrics[persona_name] = PersonaPerformanceMetrics(persona_name)

        metrics = self.performance_metrics[persona_name]

        # Update counters
        metrics.total_tasks += 1
        metrics.successful_tasks += 1

        # Update averages
        metrics.avg_quality_score = self._update_average(
            metrics.avg_quality_score, quality_score, metrics.total_tasks
        )

        metrics.avg_token_reduction = self._update_average(
            metrics.avg_token_reduction, compression_stats['token_reduction'], metrics.total_tasks
        )

        metrics.avg_compression_time = self._update_average(
            metrics.avg_compression_time, compression_stats['compression_time'], metrics.total_tasks
        )

        # Calculate effectiveness score
        metrics.effectiveness_score = self._calculate_effectiveness_score(metrics)

        metrics.last_updated = datetime.now()

    def _update_average(self, current_avg: float, new_value: float, count: int) -> float:
        """Update running average."""
        return (current_avg * (count - 1) + new_value) / count

    def _calculate_effectiveness_score(self, metrics: PersonaPerformanceMetrics) -> float:
        """Calculate effectiveness score for a persona."""
        if metrics.total_tasks == 0:
            return 0.0

        # Factors: success rate, quality, token reduction efficiency
        success_rate = metrics.successful_tasks / metrics.total_tasks
        quality_factor = metrics.avg_quality_score
        efficiency_factor = metrics.avg_token_reduction

        # Weighted score
        effectiveness = (success_rate * 0.4 + quality_factor * 0.4 + efficiency_factor * 0.2)

        return min(1.0, effectiveness)

    def _generate_session_id(self, persona_name: str, context: Dict[str, Any]) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().isoformat()
        context_hash = hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()[:8]
        return f"{persona_name}_{timestamp}_{context_hash}"


# Global persona manager instance
persona_manager = PersonaManager()


# Convenience functions
def activate_persona(persona_name: str, context: Dict[str, Any], session_id: str = None) -> PersonaContext:
    """Activate a persona with given context."""
    return persona_manager.activate_persona(persona_name, context, session_id)


def switch_persona(from_persona: str, to_persona: str, context: Dict[str, Any], session_id: str = None) -> PersonaContext:
    """Switch from one persona to another."""
    return persona_manager.switch_persona(from_persona, to_persona, context, session_id)


def find_optimal_persona(required_capabilities: List[str]) -> str:
    """Find the optimal persona for given capabilities."""
    return persona_manager.find_optimal_persona(required_capabilities)


def get_persona_capabilities(persona_name: str) -> List[str]:
    """Get capabilities of a specific persona."""
    return persona_manager.get_persona_capabilities(persona_name)


def get_system_metrics() -> Dict[str, Any]:
    """Get comprehensive system metrics."""
    return persona_manager.get_system_metrics()


if __name__ == "__main__":
    # Example usage and demonstration
    print("LeanVibe SuperClaude Persona Manager")
    print("=" * 40)

    # Test persona activation
    test_context = {
        "description": "Design a scalable microservices architecture",
        "requirements": ["high availability", "fault tolerance", "performance"],
        "code": "class ServiceRegistry:\n    def register_service(self, service):\n        pass",
        "constraints": ["budget", "timeline"]
    }

    # Find optimal persona
    optimal_persona = find_optimal_persona(["architecture", "scalability", "microservices"])
    print(f"Optimal persona: {optimal_persona}")

    # Activate persona
    persona_context = activate_persona(optimal_persona, test_context)
    print(f"Activated persona: {persona_context.persona_name}")
    print(f"Token reduction: {persona_context.compression_stats['token_reduction']:.1%}")
    print(f"Quality score: {persona_context.quality_score:.2f}")

    # Get system metrics
    metrics = get_system_metrics()
    print(f"System metrics: {json.dumps(metrics, indent=2, default=str)}")

    print("\nPersona Manager demonstration complete!")
