#!/usr/bin/env python3
"""
Tests for the Persona Manager System

Comprehensive test suite for the persona management components including
context compression, quality validation, and performance optimization.
"""

import pytest
import tempfile
from pathlib import Path

from personas.persona_manager import (
    PersonaManager,
    PersonaType,
    PersonaConfig,
    PersonaContext,
    PersonaPerformanceMetrics,
    ContextCompressor,
    QualityValidator,
    CompressionLevel,
    PersonaCapability,
    persona_manager,
    activate_persona,
    switch_persona,
    find_optimal_persona,
    get_persona_capabilities,
    get_system_metrics
)


class TestPersonaCapability:
    """Test PersonaCapability class functionality."""

    def test_persona_capability_creation(self):
        """Test basic persona capability creation."""
        capability = PersonaCapability(
            name="architecture_design",
            description="Design and review software architecture",
            proficiency=0.9,
            keywords=["architecture", "design", "patterns"],
            dependencies=["system_design", "scalability"]
        )

        assert capability.name == "architecture_design"
        assert capability.description == "Design and review software architecture"
        assert capability.proficiency == 0.9
        assert "architecture" in capability.keywords
        assert "system_design" in capability.dependencies


class TestPersonaConfig:
    """Test PersonaConfig class functionality."""

    def test_persona_config_creation(self):
        """Test persona configuration creation."""
        config = PersonaConfig(
            name="architect",
            persona_type=PersonaType.ARCHITECT,
            title="Senior Software Architect",
            experience="10+ years",
            capabilities=[],
            expertise_areas=["architecture", "design", "patterns"],
            personality_traits=["strategic", "methodical"],
            context_optimization={"focus": "architecture"},
            prompt_template="You are an architecture expert...",
            compression_level=CompressionLevel.MEDIUM,
            token_reduction_target=0.7
        )

        assert config.name == "architect"
        assert config.persona_type == PersonaType.ARCHITECT
        assert config.title == "Senior Software Architect"
        assert config.compression_level == CompressionLevel.MEDIUM
        assert config.token_reduction_target == 0.7
        assert config.enabled is True


class TestPersonaContext:
    """Test PersonaContext class functionality."""

    def test_persona_context_creation(self):
        """Test persona context creation."""
        original_context = {"task": "design system", "requirements": ["scalability"]}
        compressed_context = {"task": "design system"}
        compression_stats = {"token_reduction": 0.3, "compression_time": 0.1}

        context = PersonaContext(
            persona_name="architect",
            original_context=original_context,
            compressed_context=compressed_context,
            compression_stats=compression_stats,
            quality_score=0.95,
            session_id="test_session",
            token_count=100,
            compressed_token_count=70
        )

        assert context.persona_name == "architect"
        assert context.original_context == original_context
        assert context.compressed_context == compressed_context
        assert context.quality_score == 0.95
        assert context.session_id == "test_session"
        assert context.token_count == 100
        assert context.compressed_token_count == 70


class TestContextCompressor:
    """Test ContextCompressor class functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.compressor = ContextCompressor()
        self.test_config = PersonaConfig(
            name="architect",
            persona_type=PersonaType.ARCHITECT,
            title="Test Architect",
            experience="Test",
            capabilities=[],
            expertise_areas=["architecture", "design"],
            personality_traits=[],
            context_optimization={},
            prompt_template="",
            compression_level=CompressionLevel.MEDIUM
        )

    def test_token_estimation(self):
        """Test token count estimation."""
        context = {"description": "This is a test description", "code": "print('hello')"}
        token_count = self.compressor._estimate_tokens(context)

        assert token_count > 0
        assert isinstance(token_count, int)

    def test_compress_context(self):
        """Test context compression."""
        context = {
            "description": "Design a scalable system",
            "code": "class Service:\n    def __init__(self):\n        pass",
            "requirements": ["scalability", "performance"],
            "system_design": "microservices architecture"
        }

        compressed_context, compression_stats = self.compressor.compress_context(context, self.test_config)

        assert isinstance(compressed_context, dict)
        assert isinstance(compression_stats, dict)
        assert "token_reduction" in compression_stats
        assert "compression_time" in compression_stats
        assert compression_stats["token_reduction"] >= 0
        assert compression_stats["compression_time"] > 0

    def test_architecture_context_compression(self):
        """Test architecture-specific context compression."""
        context = {
            "system_design": "microservices with API gateway",
            "architecture_patterns": ["repository", "factory"],
            "scalability_requirements": ["horizontal scaling"],
            "irrelevant_data": "some random information"
        }

        compressed = self.compressor._compress_architecture_context(context, self.test_config)

        assert "system_design" in compressed
        assert "architecture_patterns" in compressed
        assert "scalability_requirements" in compressed
        # Should prioritize architecture-related content

    def test_security_context_compression(self):
        """Test security-specific context compression."""
        security_config = PersonaConfig(
            name="security",
            persona_type=PersonaType.SECURITY,
            title="Security Expert",
            experience="Test",
            capabilities=[],
            expertise_areas=["security", "compliance"],
            personality_traits=[],
            context_optimization={},
            prompt_template="",
            compression_level=CompressionLevel.HEAVY
        )

        context = {
            "security_requirements": ["authentication", "authorization"],
            "threat_model": "OWASP Top 10",
            "code": "def authenticate(user, password):\n    return check_credentials(user, password)",
            "random_data": "irrelevant information"
        }

        compressed = self.compressor._compress_security_context(context, security_config)

        assert "security_requirements" in compressed
        assert "threat_model" in compressed
        # Should focus on security-relevant content

    def test_code_compression_for_architecture(self):
        """Test code compression for architecture focus."""
        code = """
import os
from typing import List

class UserService:
    def __init__(self):
        self.users = []

    def add_user(self, user):
        self.users.append(user)
        return user

    def get_user(self, user_id):
        for user in self.users:
            if user.id == user_id:
                return user
        return None

@decorator
def helper_function():
    pass
"""

        compressed = self.compressor._compress_code_for_architecture(code)

        assert "import os" in compressed
        assert "from typing import List" in compressed
        assert "class UserService:" in compressed
        assert "def __init__(self):" in compressed
        assert "def add_user(self, user):" in compressed
        assert "@decorator" in compressed
        # Should preserve structure while removing implementation details

    def test_text_summarization(self):
        """Test text summarization functionality."""
        long_text = "This is a very long text. " * 50
        summarized = self.compressor._summarize_text(long_text, max_length=100)

        assert len(summarized) <= 100
        assert summarized.endswith(".")
        assert "This is a very long text" in summarized


class TestQualityValidator:
    """Test QualityValidator class functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.validator = QualityValidator()

    def test_quality_validation_perfect_match(self):
        """Test quality validation with perfect match."""
        original = {"key1": "value1", "key2": "value2"}
        compressed = {"key1": "value1", "key2": "value2"}

        quality_score = self.validator.validate_compression_quality(original, compressed)

        assert quality_score == 1.0

    def test_quality_validation_partial_match(self):
        """Test quality validation with partial match."""
        original = {"key1": "value1", "key2": "value2", "key3": "value3"}
        compressed = {"key1": "value1", "key2": "modified_value2"}

        quality_score = self.validator.validate_compression_quality(original, compressed)

        assert 0.0 < quality_score < 1.0

    def test_quality_validation_no_match(self):
        """Test quality validation with no match."""
        original = {"key1": "value1", "key2": "value2"}
        compressed = {"key3": "value3", "key4": "value4"}

        quality_score = self.validator.validate_compression_quality(original, compressed)

        assert quality_score >= 0.0

    def test_content_preservation_calculation(self):
        """Test content preservation calculation."""
        original = {"key1": "value1", "key2": "value2"}
        compressed = {"key1": "value1", "key2": "different_value"}

        preservation = self.validator._calculate_content_preservation(original, compressed)

        assert 0.0 < preservation < 1.0

    def test_essential_info_score(self):
        """Test essential information scoring."""
        original = {"description": "test", "code": "print('hello')", "other": "data"}
        compressed = {"description": "test", "code": "print('hello')"}

        score = self.validator._calculate_essential_info_score(original, compressed)

        assert score == 1.0  # Both essential keys preserved


class TestPersonaManager:
    """Test PersonaManager class functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = PersonaManager(personas_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_persona_manager_initialization(self):
        """Test persona manager initialization."""
        assert isinstance(self.manager.personas, dict)
        assert isinstance(self.manager.active_contexts, dict)
        assert isinstance(self.manager.performance_metrics, dict)
        assert len(self.manager.personas) > 0  # Should have default personas

    def test_load_default_personas(self):
        """Test loading of default personas."""
        self.manager._load_default_personas()

        assert "architect" in self.manager.personas
        assert "security" in self.manager.personas
        assert "frontend" in self.manager.personas
        assert "backend" in self.manager.personas
        assert "performance" in self.manager.personas

        # Check persona configuration
        architect = self.manager.personas["architect"]
        assert architect.persona_type == PersonaType.ARCHITECT
        assert "architecture" in architect.expertise_areas

    def test_activate_persona_success(self):
        """Test successful persona activation."""
        context = {
            "description": "Design a scalable architecture",
            "requirements": ["performance", "scalability"],
            "code": "class Service:\n    pass"
        }

        persona_context = self.manager.activate_persona("architect", context)

        assert persona_context.persona_name == "architect"
        assert persona_context.original_context == context
        assert isinstance(persona_context.compressed_context, dict)
        assert persona_context.quality_score > 0.0
        assert persona_context.session_id is not None

    def test_activate_persona_not_found(self):
        """Test persona activation with non-existent persona."""
        context = {"description": "test"}

        with pytest.raises(ValueError, match="Persona 'nonexistent' not found"):
            self.manager.activate_persona("nonexistent", context)

    def test_activate_persona_disabled(self):
        """Test persona activation with disabled persona."""
        # Disable architect persona
        self.manager.personas["architect"].enabled = False

        context = {"description": "test"}

        with pytest.raises(ValueError, match="Persona 'architect' is disabled"):
            self.manager.activate_persona("architect", context)

    def test_switch_persona(self):
        """Test persona switching functionality."""
        context1 = {"description": "Architecture design"}
        context2 = {"description": "Security analysis"}

        # Activate first persona
        persona_context1 = self.manager.activate_persona("architect", context1, "session1")

        # Switch to second persona
        persona_context2 = self.manager.switch_persona("architect", "security", context2, "session1")

        assert persona_context2.persona_name == "security"
        assert persona_context2.session_id == "session1"
        assert persona_context2.original_context == context2

    def test_get_persona_capabilities(self):
        """Test getting persona capabilities."""
        capabilities = self.manager.get_persona_capabilities("architect")

        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert "architecture" in capabilities

    def test_get_persona_capabilities_not_found(self):
        """Test getting capabilities for non-existent persona."""
        capabilities = self.manager.get_persona_capabilities("nonexistent")

        assert capabilities == []

    def test_find_optimal_persona(self):
        """Test finding optimal persona for capabilities."""
        required_capabilities = ["architecture", "design", "scalability"]

        optimal_persona = self.manager.find_optimal_persona(required_capabilities)

        assert optimal_persona is not None
        assert optimal_persona in self.manager.personas
        # Should likely return "architect" for architecture-related capabilities

    def test_find_optimal_persona_no_requirements(self):
        """Test finding optimal persona with no requirements."""
        optimal_persona = self.manager.find_optimal_persona([])

        assert optimal_persona == "analyst"  # Default fallback

    def test_capability_score_calculation(self):
        """Test capability score calculation."""
        required = ["architecture", "design"]
        available = ["architecture", "design", "patterns", "scalability"]

        score = self.manager._calculate_capability_score(required, available)

        assert score == 1.0  # Perfect match

    def test_capability_score_partial_match(self):
        """Test capability score with partial match."""
        required = ["architecture", "security"]
        available = ["architecture", "design", "patterns"]

        score = self.manager._calculate_capability_score(required, available)

        assert 0.0 < score < 1.0

    def test_get_persona_performance(self):
        """Test getting persona performance metrics."""
        performance = self.manager.get_persona_performance("architect")

        assert isinstance(performance, PersonaPerformanceMetrics)
        assert performance.persona_name == "architect"

    def test_get_system_metrics(self):
        """Test getting system metrics."""
        metrics = self.manager.get_system_metrics()

        assert "total_personas" in metrics
        assert "active_contexts" in metrics
        assert "enabled_personas" in metrics
        assert "avg_token_reduction" in metrics
        assert "avg_quality_score" in metrics
        assert "persona_performance" in metrics

        assert metrics["total_personas"] > 0
        assert metrics["enabled_personas"] > 0

    def test_update_performance_metrics(self):
        """Test updating performance metrics."""
        initial_metrics = self.manager.performance_metrics["architect"]
        initial_tasks = initial_metrics.total_tasks

        compression_stats = {
            "token_reduction": 0.6,
            "compression_time": 0.1
        }

        self.manager._update_performance_metrics("architect", 0.95, compression_stats)

        updated_metrics = self.manager.performance_metrics["architect"]
        assert updated_metrics.total_tasks == initial_tasks + 1
        assert updated_metrics.successful_tasks == initial_tasks + 1
        assert updated_metrics.avg_quality_score > 0
        assert updated_metrics.avg_token_reduction > 0

    def test_session_id_generation(self):
        """Test session ID generation."""
        context = {"description": "test"}
        session_id = self.manager._generate_session_id("architect", context)

        assert isinstance(session_id, str)
        assert "architect" in session_id
        assert len(session_id) > 20  # Should include timestamp and hash

    def test_effectiveness_score_calculation(self):
        """Test effectiveness score calculation."""
        metrics = PersonaPerformanceMetrics(
            persona_name="test",
            total_tasks=10,
            successful_tasks=9,
            avg_quality_score=0.95,
            avg_token_reduction=0.7
        )

        effectiveness = self.manager._calculate_effectiveness_score(metrics)

        assert 0.0 <= effectiveness <= 1.0
        assert effectiveness > 0.8  # Should be high for good metrics

    def test_update_average(self):
        """Test running average update."""
        current_avg = 0.8
        new_value = 0.6
        count = 5

        new_avg = self.manager._update_average(current_avg, new_value, count)

        expected = (0.8 * 4 + 0.6) / 5
        assert abs(new_avg - expected) < 0.001


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_activate_persona_function(self):
        """Test global activate_persona function."""
        context = {"description": "Architecture design task"}

        persona_context = activate_persona("architect", context)

        assert persona_context.persona_name == "architect"
        assert persona_context.original_context == context

    def test_switch_persona_function(self):
        """Test global switch_persona function."""
        context1 = {"description": "Architecture design"}
        context2 = {"description": "Security analysis"}

        # Activate first persona
        persona_context1 = activate_persona("architect", context1, "global_session")

        # Switch to second persona
        persona_context2 = switch_persona("architect", "security", context2, "global_session")

        assert persona_context2.persona_name == "security"
        assert persona_context2.session_id == "global_session"

    def test_find_optimal_persona_function(self):
        """Test global find_optimal_persona function."""
        optimal_persona = find_optimal_persona(["architecture", "design"])

        assert optimal_persona is not None
        assert optimal_persona in persona_manager.personas

    def test_get_persona_capabilities_function(self):
        """Test global get_persona_capabilities function."""
        capabilities = get_persona_capabilities("architect")

        assert isinstance(capabilities, list)
        assert len(capabilities) > 0

    def test_get_system_metrics_function(self):
        """Test global get_system_metrics function."""
        metrics = get_system_metrics()

        assert "total_personas" in metrics
        assert "active_contexts" in metrics
        assert "persona_performance" in metrics


class TestIntegration:
    """Integration tests for the complete persona system."""

    def test_complete_persona_workflow(self):
        """Test complete persona workflow."""
        # Define test context
        context = {
            "description": "Design a scalable microservices architecture",
            "requirements": ["high availability", "performance", "fault tolerance"],
            "code": """
class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register_service(self, service_name, service_info):
        self.services[service_name] = service_info

    def discover_service(self, service_name):
        return self.services.get(service_name)
""",
            "constraints": ["budget limitations", "timeline constraints"]
        }

        # Find optimal persona
        optimal_persona = find_optimal_persona(["architecture", "microservices", "scalability"])
        assert optimal_persona is not None

        # Activate persona
        persona_context = activate_persona(optimal_persona, context)

        # Verify persona context
        assert persona_context.persona_name == optimal_persona
        assert persona_context.original_context == context
        assert persona_context.quality_score >= 0.0
        assert persona_context.compression_stats["token_reduction"] >= 0.0

        # Verify compression effectiveness
        original_tokens = persona_context.compression_stats["original_tokens"]
        compressed_tokens = persona_context.compression_stats["compressed_tokens"]
        assert compressed_tokens <= original_tokens

        # Switch to different persona
        security_context = {
            "description": "Analyze security vulnerabilities in the architecture",
            "threat_model": "OWASP Top 10",
            "security_requirements": ["authentication", "authorization", "encryption"]
        }

        security_persona_context = switch_persona(
            optimal_persona, "security", security_context, persona_context.session_id
        )

        assert security_persona_context.persona_name == "security"
        assert security_persona_context.session_id == persona_context.session_id

        # Verify system metrics
        metrics = get_system_metrics()
        assert metrics["total_personas"] > 0
        assert metrics["active_contexts"] > 0

        # Verify persona performance tracking
        performance = persona_manager.get_persona_performance(optimal_persona)
        assert performance.total_tasks > 0
        assert performance.successful_tasks > 0


class TestPersonaYAMLConfiguration:
    """Test persona configuration from YAML files."""

    def test_yaml_persona_loading(self):
        """Test loading persona from YAML configuration."""
        # Create temporary YAML file
        yaml_content = """
name: test_persona
persona_type: architect
title: Test Architect
experience: 5+ years
expertise_areas:
  - architecture
  - design
  - testing
personality_traits:
  - analytical
  - methodical
compression_level: medium
token_reduction_target: 0.65
"""

        temp_dir = tempfile.mkdtemp()
        yaml_file = Path(temp_dir) / "test_persona.yaml"

        try:
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)

            # Load persona manager with custom directory
            manager = PersonaManager(personas_dir=temp_dir)

            # Verify persona was loaded (along with defaults)
            assert "test_persona" in manager.personas

            persona = manager.personas["test_persona"]
            assert persona.name == "test_persona"
            assert persona.title == "Test Architect"
            assert "architecture" in persona.expertise_areas
            assert "analytical" in persona.personality_traits

        finally:
            import shutil
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
