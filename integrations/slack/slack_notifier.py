#!/usr/bin/env python3
"""
Slack Notifier for LeanVibe Agent Hive Priority Changes

Lightweight Slack webhook integration for real-time notifications of:
- Priority changes (P0/P1/P2 adjustments)
- Task completions (P0/P1 items)
- Sprint milestone updates
- Critical coordination updates

Focus: Simple, reliable, immediate notifications without complexity.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp

from .message_templates import SlackMessageTemplate, MessageType, NotificationPriority


@dataclass
class SlackNotificationConfig:
    """Configuration for Slack notifications."""
    webhook_url: str
    channel: Optional[str] = None
    username: str = "LeanVibe Agent Hive"
    icon_emoji: str = ":robot_face:"
    enable_threading: bool = True
    max_retries: int = 3
    timeout_seconds: int = 10


@dataclass
class PriorityChangeEvent:
    """Represents a priority change event."""
    item_id: str
    item_title: str
    old_priority: str
    new_priority: str
    changed_by: str
    timestamp: datetime
    context: Dict[str, Any]


@dataclass
class CompletionEvent:
    """Represents a task completion event."""
    item_id: str
    item_title: str
    priority: str
    completed_by: str
    timestamp: datetime
    context: Dict[str, Any]


@dataclass
class SprintEvent:
    """Represents a sprint milestone event."""
    milestone: str
    progress: float
    completed_items: List[str]
    timestamp: datetime
    context: Dict[str, Any]


class SlackNotifier:
    """
    Slack notification system for priority changes and completions.
    
    Lightweight implementation focused on immediate delivery of high-value updates.
    """

    def __init__(self, config: SlackNotificationConfig):
        """Initialize Slack notifier with configuration."""
        self.config = config
        self.message_template = SlackMessageTemplate()
        self.logger = logging.getLogger(__name__)
        
        # Configure logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    async def notify_priority_change(self, event: PriorityChangeEvent) -> bool:
        """
        Send notification for priority change.
        
        Args:
            event: Priority change event data
            
        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Determine notification priority
            notification_priority = self._get_notification_priority(event.new_priority)
            
            # Generate message
            message = self.message_template.create_priority_change_message(
                event, notification_priority
            )
            
            # Send notification
            success = await self._send_slack_message(message)
            
            if success:
                self.logger.info(
                    f"Priority change notification sent: {event.item_id} "
                    f"{event.old_priority} -> {event.new_priority}"
                )
            else:
                self.logger.error(
                    f"Failed to send priority change notification: {event.item_id}"
                )
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending priority change notification: {e}")
            return False

    async def notify_completion(self, event: CompletionEvent) -> bool:
        """
        Send notification for task completion.
        
        Args:
            event: Completion event data
            
        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Only notify for P0/P1 completions
            if event.priority not in ["P0", "P1"]:
                self.logger.debug(f"Skipping completion notification for {event.priority} item")
                return True
                
            # Determine notification priority
            notification_priority = self._get_notification_priority(event.priority)
            
            # Generate message
            message = self.message_template.create_completion_message(
                event, notification_priority
            )
            
            # Send notification
            success = await self._send_slack_message(message)
            
            if success:
                self.logger.info(f"Completion notification sent: {event.item_id}")
            else:
                self.logger.error(f"Failed to send completion notification: {event.item_id}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending completion notification: {e}")
            return False

    async def notify_sprint_update(self, event: SprintEvent) -> bool:
        """
        Send notification for sprint milestone.
        
        Args:
            event: Sprint event data
            
        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Generate message
            message = self.message_template.create_sprint_message(event)
            
            # Send notification
            success = await self._send_slack_message(message)
            
            if success:
                self.logger.info(f"Sprint update notification sent: {event.milestone}")
            else:
                self.logger.error(f"Failed to send sprint update: {event.milestone}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending sprint update notification: {e}")
            return False

    async def send_custom_notification(self, title: str, message: str, 
                                     priority: NotificationPriority = NotificationPriority.MEDIUM,
                                     context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send custom notification message.
        
        Args:
            title: Notification title
            message: Message content
            priority: Notification priority
            context: Additional context data
            
        Returns:
            bool: True if notification sent successfully
        """
        try:
            # Generate custom message
            slack_message = self.message_template.create_custom_message(
                title, message, priority, context or {}
            )
            
            # Send notification
            success = await self._send_slack_message(slack_message)
            
            if success:
                self.logger.info(f"Custom notification sent: {title}")
            else:
                self.logger.error(f"Failed to send custom notification: {title}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending custom notification: {e}")
            return False

    async def test_connection(self) -> bool:
        """
        Test Slack webhook connection.
        
        Returns:
            bool: True if connection successful
        """
        try:
            test_message = {
                "text": f"🧪 LeanVibe Agent Hive - Connection Test",
                "username": self.config.username,
                "icon_emoji": self.config.icon_emoji,
                "attachments": [{
                    "color": "good",
                    "fields": [{
                        "title": "Status",
                        "value": "✅ Slack integration operational",
                        "short": True
                    }, {
                        "title": "Timestamp",
                        "value": datetime.now(timezone.utc).isoformat(),
                        "short": True
                    }]
                }]
            }
            
            if self.config.channel:
                test_message["channel"] = self.config.channel
                
            success = await self._send_slack_message(test_message)
            
            if success:
                self.logger.info("Slack connection test successful")
            else:
                self.logger.error("Slack connection test failed")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error testing Slack connection: {e}")
            return False

    def _get_notification_priority(self, priority: str) -> NotificationPriority:
        """Map item priority to notification priority."""
        priority_mapping = {
            "P0": NotificationPriority.URGENT,
            "P1": NotificationPriority.HIGH,
            "P2": NotificationPriority.MEDIUM,
            "P3": NotificationPriority.LOW
        }
        return priority_mapping.get(priority, NotificationPriority.MEDIUM)

    async def _send_slack_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message to Slack webhook.
        
        Args:
            message: Slack message payload
            
        Returns:
            bool: True if message sent successfully
        """
        retries = 0
        
        while retries < self.config.max_retries:
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        self.config.webhook_url,
                        json=message,
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        
                        if response.status == 200:
                            return True
                        else:
                            self.logger.warning(
                                f"Slack webhook returned status {response.status}: "
                                f"{await response.text()}"
                            )
                            
            except asyncio.TimeoutError:
                self.logger.warning(f"Slack webhook timeout on attempt {retries + 1}")
            except aiohttp.ClientError as e:
                self.logger.warning(f"Slack webhook client error on attempt {retries + 1}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error sending Slack message: {e}")
                break
                
            retries += 1
            if retries < self.config.max_retries:
                await asyncio.sleep(1)  # Brief delay before retry
                
        self.logger.error(f"Failed to send Slack message after {self.config.max_retries} attempts")
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        return {
            "webhook_url_configured": bool(self.config.webhook_url),
            "channel": self.config.channel,
            "username": self.config.username,
            "max_retries": self.config.max_retries,
            "timeout_seconds": self.config.timeout_seconds
        }


# Factory function for easy initialization
def create_slack_notifier(webhook_url: str, channel: Optional[str] = None) -> SlackNotifier:
    """
    Create configured Slack notifier.
    
    Args:
        webhook_url: Slack webhook URL
        channel: Optional channel override
        
    Returns:
        SlackNotifier: Configured notifier instance
    """
    config = SlackNotificationConfig(
        webhook_url=webhook_url,
        channel=channel
    )
    return SlackNotifier(config)