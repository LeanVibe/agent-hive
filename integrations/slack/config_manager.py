#!/usr/bin/env python3
"""
Configuration Manager for Slack Integration

Handles loading, validation, and management of Slack configuration settings.
Provides secure configuration management with environment variable support.
"""

import json
import os
from datetime import time
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging


@dataclass
class NotificationSettings:
    """Notification configuration settings."""
    priority_changes_enabled: bool = True
    completions_enabled: bool = True
    sprint_updates_enabled: bool = True
    min_priority_changes: str = "P2"
    min_priority_completions: str = "P1"
    milestone_threshold: float = 25.0


@dataclass
class DeliverySettings:
    """Message delivery configuration."""
    max_retries: int = 3
    timeout_seconds: int = 10
    enable_threading: bool = True
    rate_limit_per_minute: int = 30


@dataclass
class FilterSettings:
    """Message filtering settings."""
    exclude_bots: bool = True
    exclude_automated: bool = False
    quiet_hours_enabled: bool = False
    quiet_start_time: Optional[time] = None
    quiet_end_time: Optional[time] = None
    timezone: str = "UTC"


@dataclass
class FormattingSettings:
    """Message formatting settings."""
    include_context: bool = True
    include_links: bool = True
    max_message_length: int = 4000
    truncate_long_titles: bool = True


class SlackConfigManager:
    """
    Configuration manager for Slack integration.
    
    Handles loading from files and environment variables with security considerations.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[Dict[str, Any]] = None

    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Look for config in current directory, then in config directory
        current_dir = Path.cwd()
        config_paths = [
            current_dir / "config" / "slack_config.json",
            current_dir / "slack_config.json",
            Path.home() / ".leanvibe" / "slack_config.json"
        ]
        
        for path in config_paths:
            if path.exists():
                return str(path)
                
        # Return the default location if none found
        return str(config_paths[0])

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file and environment variables.
        
        Returns:
            Dict: Complete configuration
        """
        try:
            # Load from file if exists
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    self.logger.info(f"Loaded Slack config from {self.config_path}")
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
                file_config = {}

            # Override with environment variables
            config = self._apply_env_overrides(file_config)
            
            # Validate configuration
            self._validate_config(config)
            
            self._config = config
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load Slack configuration: {e}")
            # Return minimal default config
            return self._get_default_config()

    def get_webhook_url(self) -> Optional[str]:
        """Get Slack webhook URL from configuration."""
        config = self._config or self.load_config()
        
        # Check environment variable first
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if webhook_url:
            return webhook_url
            
        # Check configuration file
        return config.get("webhook_url")

    def get_notification_settings(self) -> NotificationSettings:
        """Get notification settings."""
        config = self._config or self.load_config()
        notifications = config.get("notifications", {})
        
        return NotificationSettings(
            priority_changes_enabled=notifications.get("priority_changes", {}).get("enabled", True),
            completions_enabled=notifications.get("completions", {}).get("enabled", True),
            sprint_updates_enabled=notifications.get("sprint_updates", {}).get("enabled", True),
            min_priority_changes=notifications.get("priority_changes", {}).get("min_priority", "P2"),
            min_priority_completions=notifications.get("completions", {}).get("min_priority", "P1"),
            milestone_threshold=notifications.get("sprint_updates", {}).get("milestone_threshold", 25.0)
        )

    def get_delivery_settings(self) -> DeliverySettings:
        """Get delivery settings."""
        config = self._config or self.load_config()
        delivery = config.get("delivery_settings", {})
        
        return DeliverySettings(
            max_retries=delivery.get("max_retries", 3),
            timeout_seconds=delivery.get("timeout_seconds", 10),
            enable_threading=delivery.get("enable_threading", True),
            rate_limit_per_minute=delivery.get("rate_limit_per_minute", 30)
        )

    def get_filter_settings(self) -> FilterSettings:
        """Get filter settings."""
        config = self._config or self.load_config()
        filters = config.get("filters", {})
        quiet_hours = filters.get("quiet_hours", {})
        
        # Parse quiet hours if enabled
        quiet_start = None
        quiet_end = None
        if quiet_hours.get("enabled", False):
            try:
                start_str = quiet_hours.get("start_time", "22:00")
                end_str = quiet_hours.get("end_time", "08:00")
                quiet_start = time.fromisoformat(start_str)
                quiet_end = time.fromisoformat(end_str)
            except ValueError as e:
                self.logger.warning(f"Invalid quiet hours format: {e}")
        
        return FilterSettings(
            exclude_bots=filters.get("exclude_bots", True),
            exclude_automated=filters.get("exclude_automated", False),
            quiet_hours_enabled=quiet_hours.get("enabled", False),
            quiet_start_time=quiet_start,
            quiet_end_time=quiet_end,
            timezone=quiet_hours.get("timezone", "UTC")
        )

    def get_formatting_settings(self) -> FormattingSettings:
        """Get formatting settings."""
        config = self._config or self.load_config()
        formatting = config.get("formatting", {})
        
        return FormattingSettings(
            include_context=formatting.get("include_context", True),
            include_links=formatting.get("include_links", True),
            max_message_length=formatting.get("max_message_length", 4000),
            truncate_long_titles=formatting.get("truncate_long_titles", True)
        )

    def get_basic_config(self) -> Dict[str, Any]:
        """Get basic Slack configuration (webhook, channel, etc.)."""
        config = self._config or self.load_config()
        
        return {
            "webhook_url": self.get_webhook_url(),
            "channel": config.get("channel", "#agent-hive-notifications"),
            "username": config.get("username", "LeanVibe Agent Hive"),
            "icon_emoji": config.get("icon_emoji", ":robot_face:")
        }

    def is_configured(self) -> bool:
        """Check if Slack integration is properly configured."""
        webhook_url = self.get_webhook_url()
        return bool(webhook_url and webhook_url.startswith("https://hooks.slack.com/"))

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Remove sensitive data before saving
            safe_config = config.copy()
            if "webhook_url" in safe_config:
                # Don't save webhook URL to file - use environment variable
                safe_config["webhook_url"] = ""
                
            with open(self.config_path, 'w') as f:
                json.dump(safe_config, f, indent=2)
                
            self.logger.info(f"Slack configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save Slack configuration: {e}")
            return False

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        env_overrides = {
            "SLACK_WEBHOOK_URL": ("webhook_url",),
            "SLACK_CHANNEL": ("channel",),
            "SLACK_USERNAME": ("username",),
            "SLACK_ICON_EMOJI": ("icon_emoji",),
            "SLACK_MAX_RETRIES": ("delivery_settings", "max_retries"),
            "SLACK_TIMEOUT": ("delivery_settings", "timeout_seconds"),
        }
        
        for env_var, config_path in env_overrides.items():
            value = os.getenv(env_var)
            if value:
                # Navigate to the correct config section
                current = config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert value to appropriate type
                final_key = config_path[-1]
                if env_var in ["SLACK_MAX_RETRIES", "SLACK_TIMEOUT"]:
                    try:
                        current[final_key] = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {env_var}: {value}")
                else:
                    current[final_key] = value
                    
        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration values."""
        # Check webhook URL format
        webhook_url = config.get("webhook_url")
        if webhook_url and not webhook_url.startswith("https://hooks.slack.com/"):
            if webhook_url:  # Only warn if URL is provided
                self.logger.warning("Webhook URL does not appear to be a valid Slack webhook")

        # Validate delivery settings
        delivery = config.get("delivery_settings", {})
        if delivery.get("max_retries", 3) > 10:
            self.logger.warning("max_retries > 10 may cause delays")
        if delivery.get("timeout_seconds", 10) > 60:
            self.logger.warning("timeout_seconds > 60 may cause blocking")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get minimal default configuration."""
        return {
            "webhook_url": "",
            "channel": "#agent-hive-notifications",
            "username": "LeanVibe Agent Hive",
            "icon_emoji": ":robot_face:",
            "notifications": {
                "priority_changes": {"enabled": True, "min_priority": "P2"},
                "completions": {"enabled": True, "min_priority": "P1"},
                "sprint_updates": {"enabled": True, "milestone_threshold": 25.0}
            },
            "delivery_settings": {
                "max_retries": 3,
                "timeout_seconds": 10,
                "enable_threading": True,
                "rate_limit_per_minute": 30
            },
            "filters": {
                "exclude_bots": True,
                "exclude_automated": False,
                "quiet_hours": {"enabled": False}
            },
            "formatting": {
                "include_context": True,
                "include_links": True,
                "max_message_length": 4000,
                "truncate_long_titles": True
            }
        }