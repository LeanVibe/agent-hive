#!/usr/bin/env python3
"""
Start the API Gateway and Webhook server for testing
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from external_api.fastapi_server import create_server
from external_api.models import ApiGatewayConfig, WebhookConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_webhook_handlers(server):
    """Setup webhook handlers for agent coordination."""

    async def handle_task_created(event):
        """Handle task creation webhook."""
        task_data = event.payload.get("data", {})
        logger.info(f"📋 Task created: {task_data.get('task_id')} - {task_data.get('description', '')[:50]}...")

        # Simulate task processing
        return {
            "status": "assigned",
            "agent": "integration-specialist",
            "confidence": 0.85
        }

    async def handle_agent_status(event):
        """Handle agent status change webhook."""
        status_data = event.payload.get("data", {})
        agent_name = status_data.get("agent_name")
        status = status_data.get("status")

        logger.info(f"📡 Agent {agent_name} status: {status}")

        return {"acknowledged": True}

    async def handle_system_alert(event):
        """Handle system alert webhook."""
        alert_data = event.payload.get("data", {})
        logger.info(f"🚨 System alert: {alert_data}")

        return {"handled": True}

    # Register handlers
    server.register_webhook_handler("task_created", handle_task_created)
    server.register_webhook_handler("agent_status", handle_agent_status)
    server.register_webhook_handler("system_alert", handle_system_alert)

    logger.info("✅ Webhook handlers registered")


async def setup_api_routes(server):
    """Setup API routes for agent coordination."""

    async def get_tasks(request):
        """Get tasks endpoint."""
        return {
            "status_code": 200,
            "body": {
                "tasks": [
                    {"id": "task_1", "status": "active", "agent": "integration-specialist"},
                    {"id": "task_2", "status": "pending", "agent": None}
                ]
            }
        }

    async def get_pm_workload(request):
        """Get PM workload analytics."""
        return {
            "status_code": 200,
            "body": {
                "workload_reduction": 0.75,  # 75% automation
                "total_tasks": 100,
                "automated_tasks": 75,
                "manual_tasks": 25
            }
        }

    # Register API routes
    server.register_api_route("/tasks", "GET", get_tasks)
    server.register_api_route("/analytics/pm_workload", "GET", get_pm_workload)

    logger.info("✅ API routes registered")


async def main():
    """Main server startup."""
    # Create server configurations
    gateway_config = ApiGatewayConfig(
        host="0.0.0.0",
        port=8000,
        api_prefix="/api",
        enable_cors=True,
        cors_origins=["*"],
        auth_required=False
    )

    webhook_config = WebhookConfig(
        host="0.0.0.0",
        port=8001,
        endpoint_prefix="/webhooks",
        max_payload_size=1048576,  # 1MB
        rate_limit_requests=1000,
        rate_limit_window=60
    )

    # Create and configure server
    logger.info("🚀 Starting API Gateway and Webhook server...")
    server = await create_server(gateway_config, webhook_config)

    # Setup handlers and routes
    await setup_webhook_handlers(server)
    await setup_api_routes(server)

    # Start server
    await server.start_server()

    logger.info("✅ Server started successfully!")
    logger.info(f"API Gateway: http://localhost:{gateway_config.port}")
    logger.info(f"Webhooks: http://localhost:{webhook_config.port}")
    logger.info("Press Ctrl+C to stop")

    # Handle shutdown gracefully
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info("🛑 Shutdown signal received")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Wait for shutdown signal
    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
    finally:
        logger.info("🔄 Stopping server...")
        await server.stop_server()
        logger.info("✅ Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
