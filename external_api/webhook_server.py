"""
Webhook Server for External API Integration

Handles incoming webhooks from external systems and routes them to
appropriate handlers within the LeanVibe Agent Hive system.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .models import (
    EventPriority,
    WebhookConfig,
    WebhookDelivery,
    WebhookEvent,
    WebhookEventType,
)

logger = logging.getLogger(__name__)


class WebhookServer:
    """
    HTTP server for handling incoming webhooks.

    Provides endpoint registration, event validation, rate limiting,
    and delivery status tracking.
    """

    def __init__(self, config: WebhookConfig):
        """
        Initialize webhook server.

        Args:
            config: Webhook server configuration
        """
        self.config = config
        self.handlers: Dict[str, Callable] = {}
        self.rate_limiter: Dict[str, List[float]] = {}
        self.server_started = False
        self.delivery_status: Dict[str, WebhookDelivery] = {}
        self._server_task: Optional[asyncio.Task] = None

        logger.info(
            f"WebhookServer initialized on {config.host}:{config.port}")

    async def start_server(self) -> None:
        """Start the webhook server."""
        if self.server_started:
            logger.warning("Server already started")
            return

        try:
            # Simulate server startup
            logger.info(
                f"Starting webhook server on {
                    self.config.host}:{
                    self.config.port}")
            await asyncio.sleep(0.1)  # Simulate startup time

            self.server_started = True
            logger.info("Webhook server started successfully")

        except Exception as e:
            logger.error(f"Failed to start webhook server: {e}")
            raise

    async def stop_server(self) -> None:
        """Stop the webhook server."""
        if not self.server_started:
            logger.warning("Server not running")
            return

        try:
            logger.info("Stopping webhook server...")

            if self._server_task:
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass

            self.server_started = False
            logger.info("Webhook server stopped")

        except Exception as e:
            logger.error(f"Error stopping webhook server: {e}")
            raise

    def register_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler for specific webhook event type.

        Args:
            event_type: Type of webhook event to handle
            handler: Async function to handle the event
        """
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError("Handler must be an async function")

        self.handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    def unregister_handler(self, event_type: str) -> bool:
        """
        Unregister a handler for specific webhook event type.

        Args:
            event_type: Type of webhook event to unregister

        Returns:
            True if handler was removed, False if not found
        """
        if event_type in self.handlers:
            del self.handlers[event_type]
            logger.info(f"Unregistered handler for event type: {event_type}")
            return True
        return False

    async def handle_webhook(
            self, payload: Dict[str, Any], source_ip: str = "unknown") -> Dict[str, Any]:
        """
        Handle incoming webhook request.

        Args:
            payload: Webhook payload data
            source_ip: Source IP address of the request

        Returns:
            Response data
        """
        try:
            # Rate limiting check
            if not self._check_rate_limit(source_ip):
                logger.warning(f"Rate limit exceeded for {source_ip}")
                return {
                    "status": "error",
                    "message": "Rate limit exceeded",
                    "code": 429
                }

            # Validate payload size
            payload_size = len(json.dumps(payload).encode())
            if payload_size > self.config.max_payload_size:
                logger.warning(f"Payload too large: {payload_size} bytes")
                return {
                    "status": "error",
                    "message": "Payload too large",
                    "code": 413
                }

            # Extract event information
            event_type = payload.get("type")
            if not event_type:
                return {
                    "status": "error",
                    "message": "Missing event type",
                    "code": 400
                }

            # Create webhook event
            webhook_event = WebhookEvent(
                event_type=WebhookEventType(event_type) if event_type in [
                    e.value for e in WebhookEventType] else WebhookEventType.SYSTEM_ALERT,
                event_id=str(
                    uuid.uuid4()),
                timestamp=datetime.now(),
                source=source_ip,
                payload=payload,
                priority=EventPriority(
                    payload.get(
                        "priority",
                        "medium")))

            # Process the event
            response = await self._process_event(webhook_event)

            # Track delivery status
            delivery = WebhookDelivery(
                webhook_id=str(uuid.uuid4()),
                event_id=webhook_event.event_id,
                endpoint_url=f"{self.config.endpoint_prefix}/{event_type}",
                attempt_count=1,
                last_attempt=datetime.now(),
                status="success" if response.get(
                    "status") == "success" else "failed",
                response_code=response.get("code", 200)
            )
            self.delivery_status[delivery.webhook_id] = delivery

            logger.info(
                f"Processed webhook event {
                    webhook_event.event_id} from {source_ip}")
            return response

        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {
                "status": "error",
                "message": "Internal server error",
                "code": 500
            }

    async def _process_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Process webhook event using registered handlers.

        Args:
            event: Webhook event to process

        Returns:
            Processing result
        """
        handler = self.handlers.get(event.event_type.value)

        if not handler:
            logger.warning(
                f"No handler registered for event type: {
                    event.event_type.value}")
            return {
                "status": "error",
                "message": f"No handler for event type: {
                    event.event_type.value}",
                "code": 404}

        try:
            # Execute handler with timeout
            result = await asyncio.wait_for(
                handler(event),
                timeout=self.config.timeout_seconds
            )

            return {
                "status": "success",
                "message": "Event processed successfully",
                "code": 200,
                "result": result
            }

        except asyncio.TimeoutError:
            logger.error(f"Handler timeout for event {event.event_id}")
            return {
                "status": "error",
                "message": "Handler timeout",
                "code": 504
            }
        except Exception as e:
            logger.error(f"Handler error for event {event.event_id}: {e}")
            return {
                "status": "error",
                "message": f"Handler error: {str(e)}",
                "code": 500
            }

    def _check_rate_limit(self, source_ip: str) -> bool:
        """
        Check if request is within rate limits.

        Args:
            source_ip: Source IP address

        Returns:
            True if within limits, False otherwise
        """
        current_time = time.time()
        window_start = current_time - self.config.rate_limit_window

        # Clean old entries
        if source_ip in self.rate_limiter:
            self.rate_limiter[source_ip] = [
                timestamp for timestamp in self.rate_limiter[source_ip]
                if timestamp > window_start
            ]
        else:
            self.rate_limiter[source_ip] = []

        # Check current count
        current_count = len(self.rate_limiter[source_ip])
        if current_count >= self.config.rate_limit_requests:
            return False

        # Add current request
        self.rate_limiter[source_ip].append(current_time)
        return True

    def get_delivery_status(
            self,
            webhook_id: str) -> Optional[WebhookDelivery]:
        """
        Get delivery status for a webhook.

        Args:
            webhook_id: Webhook delivery ID

        Returns:
            Delivery status or None if not found
        """
        return self.delivery_status.get(webhook_id)

    def get_handler_info(self) -> Dict[str, Any]:
        """
        Get information about registered handlers.

        Returns:
            Handler information
        """
        return {
            "registered_handlers": list(self.handlers.keys()),
            "handler_count": len(self.handlers),
            "server_status": "running" if self.server_started else "stopped",
            "config": asdict(self.config)
        }

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limiting status.

        Returns:
            Rate limit information
        """
        current_time = time.time()
        window_start = current_time - self.config.rate_limit_window

        active_ips = {}
        for ip, timestamps in self.rate_limiter.items():
            active_requests = [t for t in timestamps if t > window_start]
            if active_requests:
                active_ips[ip] = len(active_requests)

        return {
            "rate_limit_config": {
                "requests_per_window": self.config.rate_limit_requests,
                "window_seconds": self.config.rate_limit_window
            },
            "active_clients": active_ips,
            "total_active_clients": len(active_ips)
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on webhook server.

        Returns:
            Health status information
        """
        return {
            "status": "healthy" if self.server_started else "unhealthy",
            "server_running": self.server_started,
            "registered_handlers": len(self.handlers),
            "active_deliveries": len(self.delivery_status),
            "config_valid": True,  # Could add actual validation
            "timestamp": datetime.now().isoformat()
        }
