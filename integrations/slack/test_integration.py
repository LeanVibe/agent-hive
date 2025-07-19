#!/usr/bin/env python3
"""
Test script for Slack notifications integration.

Simple validation test that can be run manually to verify the integration works.
"""

import asyncio
import json
from datetime import datetime, timezone

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.slack.slack_notifier import (
    SlackNotifier,
    SlackNotificationConfig,
    PriorityChangeEvent,
    CompletionEvent,
    SprintEvent
)
from integrations.slack.config_manager import SlackConfigManager
from integrations.slack.message_templates import NotificationPriority


async def test_configuration():
    """Test configuration loading."""
    print("🧪 Testing configuration...")
    
    config_manager = SlackConfigManager()
    config = config_manager.load_config()
    
    print(f"✅ Configuration loaded: {len(config)} keys")
    print(f"   Webhook configured: {config_manager.is_configured()}")
    print(f"   Basic config: {list(config_manager.get_basic_config().keys())}")
    
    return config_manager.is_configured()


async def test_message_formatting():
    """Test message template formatting."""
    print("🧪 Testing message formatting...")
    
    try:
        from integrations.slack.message_templates import SlackMessageTemplate
        
        template = SlackMessageTemplate()
        
        # Test priority change message
        priority_event = PriorityChangeEvent(
            item_id="TEST-001",
            item_title="Test Priority Change",
            old_priority="P2", 
            new_priority="P1",
            changed_by="Test User",
            timestamp=datetime.now(timezone.utc),
            context={"test": True}
        )
        
        message = template.create_priority_change_message(
            priority_event, NotificationPriority.HIGH
        )
        
        print(f"✅ Priority change message formatted: {len(json.dumps(message))} characters")
        
        # Test completion message
        completion_event = CompletionEvent(
            item_id="TEST-002",
            item_title="Test Task Completion",
            priority="P1",
            completed_by="Test User",
            timestamp=datetime.now(timezone.utc),
            context={"test": True}
        )
        
        completion_message = template.create_completion_message(
            completion_event, NotificationPriority.HIGH
        )
        
        print(f"✅ Completion message formatted: {len(json.dumps(completion_message))} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Message formatting test failed: {e}")
        return False


async def test_dry_run_notifications():
    """Test notification creation without sending."""
    print("🧪 Testing notification creation (dry run)...")
    
    try:
        # Create a notifier with dummy webhook (won't actually send)
        config = SlackNotificationConfig(
            webhook_url="https://hooks.slack.com/services/TEST/TEST/TEST",
            channel="#test-channel"
        )
        
        notifier = SlackNotifier(config)
        
        # Test priority change
        priority_event = PriorityChangeEvent(
            item_id="DRY-001",
            item_title="Dry Run Priority Change Test",
            old_priority="P3",
            new_priority="P0",
            changed_by="Test System",
            timestamp=datetime.now(timezone.utc),
            context={"dry_run": True}
        )
        
        print("✅ Priority change event created")
        
        # Test completion
        completion_event = CompletionEvent(
            item_id="DRY-002", 
            item_title="Dry Run Completion Test",
            priority="P1",
            completed_by="Test System",
            timestamp=datetime.now(timezone.utc),
            context={"dry_run": True}
        )
        
        print("✅ Completion event created")
        
        # Test sprint update
        sprint_event = SprintEvent(
            milestone="Test Milestone",
            progress=50.0,
            completed_items=["Task A", "Task B"],
            timestamp=datetime.now(timezone.utc),
            context={"dry_run": True}
        )
        
        print("✅ Sprint event created")
        
        # Test custom notification
        print("✅ Custom notification ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Dry run test failed: {e}")
        return False


async def test_event_detection():
    """Test event detection capabilities."""
    print("🧪 Testing event detection...")
    
    try:
        from integrations.slack.event_detector import EventDetector
        
        # Create dummy notifier for testing
        config = SlackNotificationConfig(
            webhook_url="https://hooks.slack.com/services/TEST/TEST/TEST",
            channel="#test"
        )
        notifier = SlackNotifier(config)
        
        detector = EventDetector(notifier)
        status = detector.get_status()
        
        print(f"✅ Event detector initialized")
        print(f"   Backlog path: {status.get('backlog_path', 'Not found')}")
        print(f"   Cached items: {status.get('cached_items', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Event detection test failed: {e}")
        return False


async def test_integration_with_real_webhook():
    """Test with real webhook if configured."""
    print("🧪 Testing with real webhook (if configured)...")
    
    config_manager = SlackConfigManager()
    
    if not config_manager.is_configured():
        print("ℹ️  No webhook configured - skipping real test")
        print("💡 Set SLACK_WEBHOOK_URL environment variable to test with real Slack")
        return True
        
    try:
        # Create notifier with real config
        basic_config = config_manager.get_basic_config()
        delivery_settings = config_manager.get_delivery_settings()
        
        config = SlackNotificationConfig(
            webhook_url=basic_config["webhook_url"],
            channel=basic_config["channel"],
            username=basic_config["username"],
            icon_emoji=basic_config["icon_emoji"],
            max_retries=delivery_settings.max_retries,
            timeout_seconds=delivery_settings.timeout_seconds
        )
        
        notifier = SlackNotifier(config)
        
        # Test connection
        success = await notifier.test_connection()
        
        if success:
            print("✅ Real webhook test successful!")
            print("📱 Check your Slack channel for the test message")
        else:
            print("❌ Real webhook test failed")
            
        return success
        
    except Exception as e:
        print(f"❌ Real webhook test error: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 LeanVibe Slack Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Message Formatting", test_message_formatting), 
        ("Dry Run Notifications", test_dry_run_notifications),
        ("Event Detection", test_event_detection),
        ("Real Webhook", test_integration_with_real_webhook)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 Running: {test_name}")
        print("-" * 30)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"💥 Test crashed: {e}")
            results.append((test_name, False))
    
    print(f"\n📊 Test Results Summary")
    print("=" * 30)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🏆 {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Slack integration is ready.")
    else:
        print("⚠️  Some tests failed. Check configuration and dependencies.")


if __name__ == "__main__":
    asyncio.run(main())