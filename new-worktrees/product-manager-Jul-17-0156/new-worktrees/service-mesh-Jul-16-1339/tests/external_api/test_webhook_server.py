"""
Tests for WebhookServer component.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

from external_api.webhook_server import WebhookServer
from external_api.models import (
    WebhookConfig,
    WebhookEvent,
    WebhookEventType,
    EventPriority
)


class TestWebhookServer:
    """Test suite for WebhookServer class."""

    @pytest.fixture
    def webhook_config(self):
        """Create test webhook configuration."""
        return WebhookConfig(
            host="localhost",
            port=8080,
            endpoint_prefix="/webhooks",
            timeout_seconds=30,
            max_payload_size=1024,  # 1KB for testing
            rate_limit_requests=10,
            rate_limit_window=60
        )

    @pytest.fixture
    def webhook_server(self, webhook_config):
        """Create WebhookServer instance."""
        return WebhookServer(webhook_config)

    @pytest.fixture
    def sample_payload(self):
        """Create sample webhook payload."""
        return {
            "type": "task_created",
            "priority": "medium",
            "data": {
                "task_id": "test-123",
                "description": "Test task"
            }
        }

    @pytest.mark.asyncio
    async def test_server_initialization(self, webhook_server, webhook_config):
        """Test webhook server initialization."""
        assert webhook_server.config == webhook_config
        assert webhook_server.handlers == {}
        assert webhook_server.rate_limiter == {}
        assert not webhook_server.server_started
        assert webhook_server.delivery_status == {}

    async def test_start_stop_server(self, webhook_server):
        """Test server start and stop functionality."""
        # Test start
        await webhook_server.start_server()
        assert webhook_server.server_started

        # Test start when already started
        await webhook_server.start_server()  # Should not raise error
        assert webhook_server.server_started

        # Test stop
        await webhook_server.stop_server()
        assert not webhook_server.server_started

        # Test stop when not running
        await webhook_server.stop_server()  # Should not raise error
        assert not webhook_server.server_started

    async def test_register_handler(self, webhook_server):
        """Test handler registration."""
        async def test_handler(event):
            return {"result": "success"}

        # Test successful registration
        webhook_server.register_handler("test_event", test_handler)
        assert "test_event" in webhook_server.handlers
        assert webhook_server.handlers["test_event"] == test_handler

        # Test non-async handler rejection
        def sync_handler(event):
            return {"result": "success"}

        with pytest.raises(ValueError, match="Handler must be an async function"):
            webhook_server.register_handler("sync_event", sync_handler)

    async def test_unregister_handler(self, webhook_server):
        """Test handler unregistration."""
        async def test_handler(event):
            return {"result": "success"}

        # Register handler first
        webhook_server.register_handler("test_event", test_handler)

        # Test successful unregistration
        result = webhook_server.unregister_handler("test_event")
        assert result is True
        assert "test_event" not in webhook_server.handlers

        # Test unregistration of non-existent handler
        result = webhook_server.unregister_handler("non_existent")
        assert result is False

    async def test_handle_webhook_success(self, webhook_server, sample_payload):
        """Test successful webhook handling."""
        async def test_handler(event):
            return {"processed": True, "event_id": event.event_id}

        webhook_server.register_handler("task_created", test_handler)

        result = await webhook_server.handle_webhook(sample_payload, "127.0.0.1")

        assert result["status"] == "success"
        assert result["code"] == 200
        assert "result" in result

    async def test_handle_webhook_rate_limit(self, webhook_server, sample_payload):
        """Test webhook rate limiting."""
        # Fill up rate limit
        for _ in range(10):  # config.rate_limit_requests = 10
            await webhook_server.handle_webhook(sample_payload, "127.0.0.1")

        # Next request should be rate limited
        result = await webhook_server.handle_webhook(sample_payload, "127.0.0.1")
        assert result["status"] == "error"
        assert result["code"] == 429
        assert "Rate limit exceeded" in result["message"]

    async def test_handle_webhook_payload_too_large(self, webhook_server):
        """Test handling of oversized payloads."""
        large_payload = {
            "type": "task_created",
            "data": "x" * 2000  # Larger than config.max_payload_size (1024)
        }

        result = await webhook_server.handle_webhook(large_payload, "127.0.0.1")
        assert result["status"] == "error"
        assert result["code"] == 413
        assert "Payload too large" in result["message"]

    async def test_handle_webhook_missing_event_type(self, webhook_server):
        """Test handling of payload without event type."""
        invalid_payload = {"data": {"test": "value"}}

        result = await webhook_server.handle_webhook(invalid_payload, "127.0.0.1")
        assert result["status"] == "error"
        assert result["code"] == 400
        assert "Missing event type" in result["message"]

    async def test_handle_webhook_no_handler(self, webhook_server, sample_payload):
        """Test handling when no handler is registered."""
        result = await webhook_server.handle_webhook(sample_payload, "127.0.0.1")
        assert result["status"] == "error"
        assert result["code"] == 404
        assert "No handler for event type" in result["message"]

    async def test_handle_webhook_handler_timeout(self, webhook_server, sample_payload):
        """Test handler timeout handling."""
        async def slow_handler(event):
            await asyncio.sleep(35)  # Longer than config.timeout_seconds (30)
            return {"result": "done"}

        webhook_server.register_handler("task_created", slow_handler)

        result = await webhook_server.handle_webhook(sample_payload, "127.0.0.1")
        assert result["status"] == "error"
        assert result["code"] == 504
        assert "Handler timeout" in result["message"]

    async def test_handle_webhook_handler_error(self, webhook_server, sample_payload):
        """Test handler error handling."""
        async def error_handler(event):
            raise ValueError("Test error")

        webhook_server.register_handler("task_created", error_handler)

        result = await webhook_server.handle_webhook(sample_payload, "127.0.0.1")
        assert result["status"] == "error"
        assert result["code"] == 500
        assert "Handler error" in result["message"]

    async def test_rate_limit_check(self, webhook_server):
        """Test rate limiting logic."""
        source_ip = "192.168.1.1"

        # Should allow requests within limit
        for i in range(10):  # config.rate_limit_requests = 10
            assert webhook_server._check_rate_limit(source_ip) is True

        # Should deny request exceeding limit
        assert webhook_server._check_rate_limit(source_ip) is False

    async def test_get_delivery_status(self, webhook_server, sample_payload):
        """Test delivery status tracking."""
        async def test_handler(event):
            return {"processed": True}

        webhook_server.register_handler("task_created", test_handler)

        # Process webhook to create delivery status
        await webhook_server.handle_webhook(sample_payload, "127.0.0.1")

        # Should have one delivery status entry
        assert len(webhook_server.delivery_status) == 1

        webhook_id = list(webhook_server.delivery_status.keys())[0]
        delivery = webhook_server.get_delivery_status(webhook_id)

        assert delivery is not None
        assert delivery.status == "success"
        assert delivery.response_code == 200

    async def test_get_handler_info(self, webhook_server):
        """Test handler information retrieval."""
        async def handler1(event):
            return {}

        async def handler2(event):
            return {}

        webhook_server.register_handler("event1", handler1)
        webhook_server.register_handler("event2", handler2)

        info = webhook_server.get_handler_info()

        assert info["handler_count"] == 2
        assert set(info["registered_handlers"]) == {"event1", "event2"}
        assert info["server_status"] == "stopped"
        assert "config" in info

    async def test_get_rate_limit_status(self, webhook_server):
        """Test rate limit status retrieval."""
        # Generate some rate limit activity
        webhook_server._check_rate_limit("192.168.1.1")
        webhook_server._check_rate_limit("192.168.1.2")

        status = webhook_server.get_rate_limit_status()

        assert "rate_limit_config" in status
        assert "active_clients" in status
        assert "total_active_clients" in status
        assert status["rate_limit_config"]["requests_per_window"] == 10
        assert status["total_active_clients"] == 2

    async def test_health_check(self, webhook_server):
        """Test health check functionality."""
        # Health check when stopped
        health = await webhook_server.health_check()
        assert health["status"] == "unhealthy"
        assert health["server_running"] is False

        # Start server and check again
        await webhook_server.start_server()
        health = await webhook_server.health_check()
        assert health["status"] == "healthy"
        assert health["server_running"] is True
        assert "timestamp" in health

    async def test_webhook_config_validation(self):
        """Test webhook configuration validation."""
        # Test invalid port
        with pytest.raises(ValueError, match="Port must be between 1-65535"):
            WebhookConfig(port=0)

        with pytest.raises(ValueError, match="Port must be between 1-65535"):
            WebhookConfig(port=70000)

        # Test invalid timeout
        with pytest.raises(ValueError, match="Timeout must be positive"):
            WebhookConfig(timeout_seconds=0)

        # Test invalid payload size
        with pytest.raises(ValueError, match="Max payload size must be positive"):
            WebhookConfig(max_payload_size=0)

    async def test_webhook_event_validation(self):
        """Test webhook event validation."""
        # Test valid event
        event = WebhookEvent(
            event_type=WebhookEventType.TASK_CREATED,
            event_id="test-123",
            timestamp=datetime.now(),
            source="test-source",
            payload={"data": "test"}
        )
        assert event.event_id == "test-123"

        # Test empty event ID
        with pytest.raises(ValueError, match="Event ID cannot be empty"):
            WebhookEvent(
                event_type=WebhookEventType.TASK_CREATED,
                event_id="",
                timestamp=datetime.now(),
                source="test-source",
                payload={"data": "test"}
            )

        # Test empty source
        with pytest.raises(ValueError, match="Event source cannot be empty"):
            WebhookEvent(
                event_type=WebhookEventType.TASK_CREATED,
                event_id="test-123",
                timestamp=datetime.now(),
                source="",
                payload={"data": "test"}
            )
