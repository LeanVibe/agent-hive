"""Unified configuration loader accessible as `config.config_loader`.

This module provides the same API as `.claude/config/config_loader.py` so that
imports like `from config.config_loader import ConfigLoader, get_config` work
consistently across the test suite.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader with environment variable support."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Default to the repo's `.claude/config/config.yaml` to preserve behavior
            self.config_path = Path(__file__).resolve().parent.parent / ".claude" / "config" / "config.yaml"
        else:
            self.config_path = Path(config_path)

        self._config: Optional[Dict[str, Any]] = None
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            self._config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        if self._config is None:
            return default

        # Environment variable override
        env_key = f"LEANVIBE_{key.upper().replace('.', '_')}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return self._convert_env_value(env_value)

        current = self._config
        for part in key.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def _convert_env_value(self, value: str) -> Any:
        # Boolean
        lower = value.lower()
        if lower in ('true', 'false'):
            return lower == 'true'
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        # String fallback
        return value

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        return self.get(f'agents.{agent_name}', {})

    def get_system_config(self) -> Dict[str, Any]:
        return self.get('system', {})

    def get_task_queue_config(self) -> Dict[str, Any]:
        return self.get('task_queue', {})

    def get_state_management_config(self) -> Dict[str, Any]:
        return self.get('state_management', {})

    def get_monitoring_config(self) -> Dict[str, Any]:
        return self.get('monitoring', {})

    def is_development_mode(self) -> bool:
        return self.get('development.debug_mode', False)

    def should_use_mock_cli(self) -> bool:
        return self.get('development.use_mock_cli', False)

    def get_cli_path(self, agent_name: str) -> str:
        agent_config = self.get_agent_config(agent_name)
        if self.should_use_mock_cli():
            path = agent_config.get('test_cli_path', agent_config.get('cli_path', ''))
        else:
            path = agent_config.get('cli_path', '')

        if path and not Path(path).is_absolute():
            # Resolve relative to repo root
            project_root = Path(__file__).resolve().parent.parent
            path = str(project_root / path)
        return path

    def reload(self):
        self._load_config()

    def validate(self) -> bool:
        required_keys = [
            'system.log_level',
            'agents.claude.cli_path',
            'agents.gemini.cli_path',
            'task_queue.max_queue_size'
        ]
        for key in required_keys:
            if self.get(key) is None:
                logger.error(f"Missing required configuration: {key}")
                return False
        return True


# Global configuration instance
__global_config: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    global __global_config
    if __global_config is None:
        __global_config = ConfigLoader()
    return __global_config


def reload_config():
    global __global_config
    if __global_config is not None:
        __global_config.reload()
