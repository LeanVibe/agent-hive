# .claude/config/config_loader.py
"""Configuration loader for LeanVibe orchestration system."""

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
            self.config_path = Path(__file__).parent / "config.yaml"
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
        """Get configuration value by dot-notation key.

        Args:
            key: Configuration key in dot notation (e.g., 'agents.claude.timeout')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._config is None:
            return default

        # Check for environment variable override
        env_key = f"LEANVIBE_{key.upper().replace('.', '_')}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return self._convert_env_value(env_value)

        # Navigate through nested dictionary
        current = self._config
        for part in key.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass

        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration dictionary
        """
        return self.get(f'agents.{agent_name}', {})

    def get_system_config(self) -> Dict[str, Any]:
        """Get system-wide configuration.

        Returns:
            System configuration dictionary
        """
        return self.get('system', {})

    def get_task_queue_config(self) -> Dict[str, Any]:
        """Get task queue configuration.

        Returns:
            Task queue configuration dictionary
        """
        return self.get('task_queue', {})

    def get_state_management_config(self) -> Dict[str, Any]:
        """Get state management configuration.

        Returns:
            State management configuration dictionary
        """
        return self.get('state_management', {})

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration.

        Returns:
            Monitoring configuration dictionary
        """
        return self.get('monitoring', {})

    def is_development_mode(self) -> bool:
        """Check if running in development mode.

        Returns:
            True if in development mode
        """
        return self.get('development.debug_mode', False)

    def should_use_mock_cli(self) -> bool:
        """Check if should use mock CLI for testing.

        Returns:
            True if should use mock CLI
        """
        return self.get('development.use_mock_cli', False)

    def get_cli_path(self, agent_name: str) -> str:
        """Get CLI path for agent (production or mock).

        Args:
            agent_name: Name of the agent

        Returns:
            CLI path
        """
        agent_config = self.get_agent_config(agent_name)

        if self.should_use_mock_cli():
            path = agent_config.get('test_cli_path', agent_config.get('cli_path', ''))
        else:
            path = agent_config.get('cli_path', '')

        # Make relative paths absolute
        if path and not Path(path).is_absolute():
            # Resolve relative to project root
            project_root = Path(__file__).parent.parent.parent
            path = str(project_root / path)

        return path

    def reload(self):
        """Reload configuration from file."""
        self._load_config()

    def validate(self) -> bool:
        """Validate configuration completeness.

        Returns:
            True if configuration is valid
        """
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
_config_loader = None


def get_config() -> ConfigLoader:
    """Get global configuration loader instance.

    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def reload_config():
    """Reload global configuration."""
    global _config_loader
    if _config_loader is not None:
        _config_loader.reload()
