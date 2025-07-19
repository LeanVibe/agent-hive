#!/usr/bin/env python3
"""
CLI Commands for Slack Notifications

Provides command-line interface for managing and testing Slack notifications.
Integrates with the main LeanVibe CLI system.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import argparse
import logging

from .slack_notifier import (
    SlackNotifier, 
    SlackNotificationConfig,
    PriorityChangeEvent,
    CompletionEvent,
    SprintEvent,
    NotificationPriority
)
from .config_manager import SlackConfigManager
from .event_detector import EventDetector


class SlackCLI:
    """CLI interface for Slack notification management."""

    def __init__(self):
        """Initialize Slack CLI."""
        self.config_manager = SlackConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # Configure logging for CLI
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    async def test_connection(self) -> None:
        """Test Slack webhook connection."""
        print("🧪 Testing Slack connection...")
        
        # Check configuration
        if not self.config_manager.is_configured():
            print("❌ Slack not configured. Set SLACK_WEBHOOK_URL environment variable.")
            print("💡 Example: export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'")
            return
            
        try:
            # Create notifier
            notifier = self._create_notifier()
            
            # Test connection
            success = await notifier.test_connection()
            
            if success:
                print("✅ Slack connection successful!")
                print("📱 Check your Slack channel for the test message.")
            else:
                print("❌ Slack connection failed.")
                print("💡 Check your webhook URL and network connection.")
                
        except Exception as e:
            print(f"❌ Error testing connection: {e}")

    async def send_test_notification(self, notification_type: str = "priority") -> None:
        """Send test notification."""
        print(f"📤 Sending test {notification_type} notification...")
        
        if not self.config_manager.is_configured():
            print("❌ Slack not configured.")
            return
            
        try:
            notifier = self._create_notifier()
            
            if notification_type == "priority":
                event = PriorityChangeEvent(
                    item_id="TEST-001",
                    item_title="Test Priority Change Notification",
                    old_priority="P2",
                    new_priority="P1",
                    changed_by="CLI Test",
                    timestamp=datetime.now(timezone.utc),
                    context={"source": "cli_test", "test": True}
                )
                success = await notifier.notify_priority_change(event)
                
            elif notification_type == "completion":
                event = CompletionEvent(
                    item_id="TEST-002",
                    item_title="Test Task Completion Notification",
                    priority="P1",
                    completed_by="CLI Test",
                    timestamp=datetime.now(timezone.utc),
                    context={"source": "cli_test", "test": True}
                )
                success = await notifier.notify_completion(event)
                
            elif notification_type == "sprint":
                event = SprintEvent(
                    milestone="75% Complete",
                    progress=75.0,
                    completed_items=["Task A", "Task B", "Task C"],
                    timestamp=datetime.now(timezone.utc),
                    context={"source": "cli_test", "test": True}
                )
                success = await notifier.notify_sprint_update(event)
                
            else:
                print(f"❌ Unknown notification type: {notification_type}")
                return
                
            if success:
                print("✅ Test notification sent successfully!")
            else:
                print("❌ Failed to send test notification.")
                
        except Exception as e:
            print(f"❌ Error sending test notification: {e}")

    async def send_custom_message(self, title: str, message: str, 
                                priority: str = "medium") -> None:
        """Send custom notification message."""
        print(f"📤 Sending custom notification: {title}")
        
        if not self.config_manager.is_configured():
            print("❌ Slack not configured.")
            return
            
        try:
            notifier = self._create_notifier()
            
            # Map priority string to enum
            priority_map = {
                "urgent": NotificationPriority.URGENT,
                "high": NotificationPriority.HIGH,
                "medium": NotificationPriority.MEDIUM,
                "low": NotificationPriority.LOW
            }
            notification_priority = priority_map.get(priority.lower(), NotificationPriority.MEDIUM)
            
            success = await notifier.send_custom_notification(
                title=title,
                message=message,
                priority=notification_priority,
                context={"source": "cli_custom"}
            )
            
            if success:
                print("✅ Custom notification sent successfully!")
            else:
                print("❌ Failed to send custom notification.")
                
        except Exception as e:
            print(f"❌ Error sending custom notification: {e}")

    async def check_events(self) -> None:
        """Check for events and send notifications."""
        print("🔍 Checking for events...")
        
        if not self.config_manager.is_configured():
            print("❌ Slack not configured.")
            return
            
        try:
            notifier = self._create_notifier()
            detector = EventDetector(notifier)
            
            events = await detector.check_for_changes()
            
            if events:
                print(f"✅ Detected and processed {len(events)} events:")
                for event in events:
                    if hasattr(event, 'item_title'):
                        print(f"  • {event.item_title}")
            else:
                print("ℹ️  No events detected.")
                
        except Exception as e:
            print(f"❌ Error checking events: {e}")

    def show_config(self) -> None:
        """Show current configuration."""
        print("📋 Slack Configuration:")
        print("=" * 30)
        
        try:
            # Basic config
            basic_config = self.config_manager.get_basic_config()
            webhook_configured = bool(basic_config.get("webhook_url"))
            
            print(f"Webhook URL: {'✅ Configured' if webhook_configured else '❌ Not configured'}")
            print(f"Channel: {basic_config.get('channel', 'Not set')}")
            print(f"Username: {basic_config.get('username', 'Not set')}")
            print(f"Icon: {basic_config.get('icon_emoji', 'Not set')}")
            print()
            
            # Notification settings
            notifications = self.config_manager.get_notification_settings()
            print("Notification Settings:")
            print(f"  Priority Changes: {'✅' if notifications.priority_changes_enabled else '❌'}")
            print(f"  Completions: {'✅' if notifications.completions_enabled else '❌'}")
            print(f"  Sprint Updates: {'✅' if notifications.sprint_updates_enabled else '❌'}")
            print(f"  Min Priority (Changes): {notifications.min_priority_changes}")
            print(f"  Min Priority (Completions): {notifications.min_priority_completions}")
            print()
            
            # Delivery settings
            delivery = self.config_manager.get_delivery_settings()
            print("Delivery Settings:")
            print(f"  Max Retries: {delivery.max_retries}")
            print(f"  Timeout: {delivery.timeout_seconds}s")
            print(f"  Threading: {'✅' if delivery.enable_threading else '❌'}")
            print(f"  Rate Limit: {delivery.rate_limit_per_minute}/min")
            
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")

    def setup_config(self, webhook_url: Optional[str] = None,
                    channel: Optional[str] = None) -> None:
        """Set up basic configuration."""
        print("⚙️  Setting up Slack configuration...")
        
        try:
            config = self.config_manager.load_config()
            
            if webhook_url:
                print(f"🔗 Setting webhook URL")
                # Don't save webhook URL to file, use environment variable
                import os
                os.environ['SLACK_WEBHOOK_URL'] = webhook_url
                
            if channel:
                print(f"📢 Setting channel to {channel}")
                config['channel'] = channel
                
            # Save configuration
            success = self.config_manager.save_config(config)
            
            if success:
                print("✅ Configuration saved successfully!")
                print("💡 Webhook URL stored in environment variable for security.")
            else:
                print("❌ Failed to save configuration.")
                
        except Exception as e:
            print(f"❌ Error setting up configuration: {e}")

    async def manually_notify_priority_change(self, item_id: str, title: str,
                                            old_priority: str, new_priority: str) -> None:
        """Manually trigger priority change notification."""
        print(f"📢 Sending priority change notification: {title}")
        
        if not self.config_manager.is_configured():
            print("❌ Slack not configured.")
            return
            
        try:
            notifier = self._create_notifier()
            detector = EventDetector(notifier)
            
            success = await detector.manually_trigger_priority_change(
                item_id=item_id,
                item_title=title,
                old_priority=old_priority,
                new_priority=new_priority,
                changed_by="CLI Manual"
            )
            
            if success:
                print("✅ Priority change notification sent!")
            else:
                print("❌ Failed to send notification.")
                
        except Exception as e:
            print(f"❌ Error sending notification: {e}")

    async def manually_notify_completion(self, item_id: str, title: str,
                                       priority: str) -> None:
        """Manually trigger completion notification."""
        print(f"📢 Sending completion notification: {title}")
        
        if not self.config_manager.is_configured():
            print("❌ Slack not configured.")
            return
            
        try:
            notifier = self._create_notifier()
            detector = EventDetector(notifier)
            
            success = await detector.manually_trigger_completion(
                item_id=item_id,
                item_title=title,
                priority=priority,
                completed_by="CLI Manual"
            )
            
            if success:
                print("✅ Completion notification sent!")
            else:
                print("❌ Failed to send notification.")
                
        except Exception as e:
            print(f"❌ Error sending notification: {e}")

    def _create_notifier(self) -> SlackNotifier:
        """Create configured Slack notifier."""
        basic_config = self.config_manager.get_basic_config()
        delivery_settings = self.config_manager.get_delivery_settings()
        
        config = SlackNotificationConfig(
            webhook_url=basic_config["webhook_url"],
            channel=basic_config["channel"],
            username=basic_config["username"],
            icon_emoji=basic_config["icon_emoji"],
            enable_threading=delivery_settings.enable_threading,
            max_retries=delivery_settings.max_retries,
            timeout_seconds=delivery_settings.timeout_seconds
        )
        
        return SlackNotifier(config)


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="slack-notify",
        description="LeanVibe Agent Hive - Slack Notifications Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slack-notify test-connection
  slack-notify test-notification --type priority
  slack-notify send-custom --title "Deploy Ready" --message "Version 1.0 ready for production"
  slack-notify check-events
  slack-notify config --show
  slack-notify setup --webhook-url "https://hooks.slack.com/..." --channel "#notifications"
  slack-notify notify-priority --id "TASK-123" --title "Fix critical bug" --old-priority "P2" --new-priority "P0"
  slack-notify notify-completion --id "TASK-456" --title "Implement user auth" --priority "P1"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Test connection
    subparsers.add_parser("test-connection", help="Test Slack webhook connection")

    # Test notification
    test_parser = subparsers.add_parser("test-notification", help="Send test notification")
    test_parser.add_argument("--type", choices=["priority", "completion", "sprint"], 
                           default="priority", help="Type of test notification")

    # Send custom message
    custom_parser = subparsers.add_parser("send-custom", help="Send custom notification")
    custom_parser.add_argument("--title", required=True, help="Notification title")
    custom_parser.add_argument("--message", required=True, help="Notification message")
    custom_parser.add_argument("--priority", choices=["urgent", "high", "medium", "low"],
                             default="medium", help="Notification priority")

    # Check events
    subparsers.add_parser("check-events", help="Check for events and send notifications")

    # Configuration
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current configuration")

    # Setup
    setup_parser = subparsers.add_parser("setup", help="Set up Slack configuration")
    setup_parser.add_argument("--webhook-url", help="Slack webhook URL")
    setup_parser.add_argument("--channel", help="Slack channel")

    # Manual notifications
    priority_parser = subparsers.add_parser("notify-priority", help="Send priority change notification")
    priority_parser.add_argument("--id", required=True, help="Item ID")
    priority_parser.add_argument("--title", required=True, help="Item title")
    priority_parser.add_argument("--old-priority", required=True, help="Old priority (P0-P3)")
    priority_parser.add_argument("--new-priority", required=True, help="New priority (P0-P3)")

    completion_parser = subparsers.add_parser("notify-completion", help="Send completion notification")
    completion_parser.add_argument("--id", required=True, help="Item ID")
    completion_parser.add_argument("--title", required=True, help="Item title")
    completion_parser.add_argument("--priority", required=True, help="Item priority (P0-P3)")

    return parser


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = SlackCLI()

    try:
        if args.command == "test-connection":
            await cli.test_connection()
        elif args.command == "test-notification":
            await cli.send_test_notification(args.type)
        elif args.command == "send-custom":
            await cli.send_custom_message(args.title, args.message, args.priority)
        elif args.command == "check-events":
            await cli.check_events()
        elif args.command == "config":
            cli.show_config()
        elif args.command == "setup":
            cli.setup_config(args.webhook_url, args.channel)
        elif args.command == "notify-priority":
            await cli.manually_notify_priority_change(
                args.id, args.title, args.old_priority, args.new_priority
            )
        elif args.command == "notify-completion":
            await cli.manually_notify_completion(args.id, args.title, args.priority)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n👋 Slack CLI interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())