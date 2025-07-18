"""
Unit tests for ConfigLoader component.

Tests configuration loading with environment variable overrides.
"""

import pytest
import os
import yaml
from unittest.mock import patch
from pathlib import Path

# Import the component under test
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

from config.config_loader import ConfigLoader, get_config


class TestConfigLoader:
    """Test cases for ConfigLoader functionality."""

    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data for testing."""
        return {
            "system": {
                "log_level": "INFO",
                "debug_mode": False
            },
            "agents": {
                "claude": {
                    "cli_path": "/usr/local/bin/claude",
                    "test_cli_path": "/mock/claude",
                    "timeout": 300,
                    "max_retries": 3
                },
                "gemini": {
                    "cli_path": "/usr/local/bin/gemini",
                    "test_cli_path": "/mock/gemini",
                    "timeout": 180
                }
            },
            "task_queue": {
                "max_queue_size": 1000,
                "default_priority": 5
            },
            "development": {
                "debug_mode": True,
                "use_mock_cli": True
            }
        }

    @pytest.mark.unit
    def test_config_loader_initialization_with_file(self, sample_config_data, temp_directory):
        """Test ConfigLoader initializes with existing config file."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        assert loader.get("system.log_level") == "INFO"
        assert loader.get("agents.claude.timeout") == 300

    @pytest.mark.unit
    def test_config_loader_initialization_missing_file(self, temp_directory):
        """Test ConfigLoader handles missing config file gracefully."""
        non_existent_file = temp_directory / "missing.yaml"

        loader = ConfigLoader(str(non_existent_file))

        # Should return defaults for missing keys
        assert loader.get("system.log_level", "DEFAULT") == "DEFAULT"
        assert loader.get("nonexistent.key", "default") == "default"

    @pytest.mark.unit
    def test_config_loader_invalid_yaml(self, temp_directory):
        """Test ConfigLoader handles invalid YAML gracefully."""
        config_file = temp_directory / "invalid.yaml"
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [")

        loader = ConfigLoader(str(config_file))

        # Should fall back to empty config
        assert loader.get("any.key", "default") == "default"

    @pytest.mark.unit
    def test_dot_notation_access(self, sample_config_data, temp_directory):
        """Test configuration access using dot notation."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        # Test various levels of nesting
        assert loader.get("system") == sample_config_data["system"]
        assert loader.get("system.log_level") == "INFO"
        assert loader.get("agents.claude.timeout") == 300
        assert loader.get("task_queue.max_queue_size") == 1000

    @pytest.mark.unit
    def test_environment_variable_overrides(self, sample_config_data, temp_directory):
        """Test environment variable overrides for config values."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        # Test string override
        with patch.dict(os.environ, {"LEANVIBE_SYSTEM_LOG_LEVEL": "DEBUG"}):
            assert loader.get("system.log_level") == "DEBUG"

        # Test integer override
        with patch.dict(os.environ, {"LEANVIBE_AGENTS_CLAUDE_TIMEOUT": "600"}):
            assert loader.get("agents.claude.timeout") == 600

        # Test boolean override
        with patch.dict(os.environ, {"LEANVIBE_SYSTEM_DEBUG_MODE": "true"}):
            assert loader.get("system.debug_mode") is True

        with patch.dict(os.environ, {"LEANVIBE_SYSTEM_DEBUG_MODE": "false"}):
            assert loader.get("system.debug_mode") is False

    @pytest.mark.unit
    def test_environment_variable_type_conversion(self, sample_config_data, temp_directory):
        """Test environment variable type conversion."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        # Test float conversion
        with patch.dict(os.environ, {"LEANVIBE_TEST_FLOAT": "3.14"}):
            assert loader.get("test.float") == 3.14

        # Test integer conversion
        with patch.dict(os.environ, {"LEANVIBE_TEST_INT": "42"}):
            assert loader.get("test.int") == 42

        # Test boolean conversion
        with patch.dict(os.environ, {"LEANVIBE_TEST_BOOL_TRUE": "True"}):
            assert loader.get("test.bool.true") is True

        with patch.dict(os.environ, {"LEANVIBE_TEST_BOOL_FALSE": "False"}):
            assert loader.get("test.bool.false") is False

        # Test string fallback
        with patch.dict(os.environ, {"LEANVIBE_TEST_STRING": "hello world"}):
            assert loader.get("test.string") == "hello world"

    @pytest.mark.unit
    def test_agent_config_helper(self, sample_config_data, temp_directory):
        """Test agent-specific configuration helper."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        claude_config = loader.get_agent_config("claude")
        assert claude_config["timeout"] == 300
        assert claude_config["max_retries"] == 3

        gemini_config = loader.get_agent_config("gemini")
        assert gemini_config["timeout"] == 180

        # Non-existent agent should return empty dict
        unknown_config = loader.get_agent_config("unknown")
        assert unknown_config == {}

    @pytest.mark.unit
    def test_system_config_helper(self, sample_config_data, temp_directory):
        """Test system configuration helper."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        system_config = loader.get_system_config()
        assert system_config["log_level"] == "INFO"
        assert system_config["debug_mode"] is False

    @pytest.mark.unit
    def test_development_mode_detection(self, sample_config_data, temp_directory):
        """Test development mode detection."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        assert loader.is_development_mode() is True
        assert loader.should_use_mock_cli() is True

    @pytest.mark.unit
    def test_cli_path_resolution(self, sample_config_data, temp_directory):
        """Test CLI path resolution for production vs mock."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        # In development mode, should return test CLI path
        claude_path = loader.get_cli_path("claude")
        assert "/mock/claude" in claude_path

        # Test relative path resolution
        sample_config_data["agents"]["test_agent"] = {
            "cli_path": "relative/path/cli",
            "test_cli_path": "relative/test/cli"
        }

        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader.reload()
        test_path = loader.get_cli_path("test_agent")
        assert Path(test_path).is_absolute()

    @pytest.mark.unit
    def test_config_validation(self, sample_config_data, temp_directory):
        """Test configuration validation."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        # Valid config should pass validation
        assert loader.validate() is True

        # Missing required key should fail validation
        incomplete_config = {"system": {"log_level": "INFO"}}
        with open(config_file, 'w') as f:
            yaml.dump(incomplete_config, f)

        loader.reload()
        assert loader.validate() is False

    @pytest.mark.unit
    def test_config_reload(self, sample_config_data, temp_directory):
        """Test configuration reload functionality."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))
        assert loader.get("system.log_level") == "INFO"

        # Update config file
        sample_config_data["system"]["log_level"] = "DEBUG"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        # Reload and verify change
        loader.reload()
        assert loader.get("system.log_level") == "DEBUG"

    @pytest.mark.unit
    def test_global_config_instance(self, sample_config_data, temp_directory):
        """Test global configuration instance management."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        # Mock the default config path
        with patch('claude.config.config_loader.ConfigLoader.__init__') as mock_init:
            mock_init.return_value = None

            # Get global config instances
            config1 = get_config()
            config2 = get_config()

            # Should be the same instance
            assert config1 is config2

    @pytest.mark.unit
    def test_missing_nested_keys(self, sample_config_data, temp_directory):
        """Test behavior with missing nested keys."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        # Non-existent nested keys should return default
        assert loader.get("nonexistent.nested.key", "default") == "default"
        assert loader.get("system.nonexistent", "default") == "default"
        assert loader.get("agents.nonexistent.key", "default") == "default"

    @pytest.mark.unit
    @pytest.mark.performance
    def test_config_access_performance(self, sample_config_data, temp_directory, performance_thresholds):
        """Test configuration access performance."""
        config_file = temp_directory / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)

        loader = ConfigLoader(str(config_file))

        # Time multiple config accesses
        import time
        start_time = time.time()

        iterations = 1000
        for _ in range(iterations):
            loader.get("system.log_level")
            loader.get("agents.claude.timeout")
            loader.get("task_queue.max_queue_size")

        total_time = time.time() - start_time
        avg_time = total_time / (iterations * 3)  # 3 calls per iteration

        # Config access should be fast
        assert avg_time < performance_thresholds["config_load_max_time"], f"Config access too slow: {avg_time}s per call"

    @pytest.mark.unit
    def test_config_edge_cases(self, temp_directory):
        """Test configuration edge cases and error conditions."""
        # Test with completely empty file
        empty_file = temp_directory / "empty.yaml"
        empty_file.touch()

        loader = ConfigLoader(str(empty_file))
        assert loader.get("any.key", "default") == "default"

        # Test with None config content
        none_config_file = temp_directory / "none.yaml"
        with open(none_config_file, 'w') as f:
            f.write("")  # Empty content that parses to None

        loader = ConfigLoader(str(none_config_file))
        assert loader.get("any.key", "default") == "default"
