"""
Integration Agent Examples

This file contains practical examples of how to use the Integration Agent
components for various integration scenarios.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from external_api.integration_manager import IntegrationManager, IntegrationConfig
from external_api.github_client import GitHubClient, GitHubConfig, GitHubEventType
from external_api.slack_client import SlackClient, SlackConfig, SlackEventType
from external_api.api_gateway import ApiGateway
from external_api.service_discovery import ServiceDiscovery, ServiceInfo, ServiceStatus
from external_api.models import ApiGatewayConfig, ApiRequest
from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationExamples:
    """Examples of integration patterns and use cases."""
    
    def __init__(self):
        self.github_client = None
        self.slack_client = None
        self.api_gateway = None
        self.service_discovery = None
        self.integration_manager = None
        self.coordinator = None
    
    async def example_1_basic_github_integration(self):
        """Example 1: Basic GitHub integration with repository management."""
        logger.info("🚀 Example 1: Basic GitHub Integration")
        
        # Configure GitHub client
        github_config = GitHubConfig(
            token="your_github_token",  # Replace with actual token
            webhook_secret="your_webhook_secret",
            default_owner="your_org",
            default_repo="your_repo"
        )
        
        async with GitHubClient(github_config) as github_client:
            try:
                # Get repository information
                repo = await github_client.get_repository("octocat", "Hello-World")
                logger.info(f"Repository: {repo['full_name']}")
                logger.info(f"Description: {repo['description']}")
                logger.info(f"Stars: {repo['stargazers_count']}")
                
                # List open issues
                issues = await github_client.list_issues("octocat", "Hello-World", state="open")
                logger.info(f"Found {len(issues)} open issues")
                
                # Create a new issue (commented out to avoid spam)
                # new_issue = await github_client.create_issue(
                #     owner="your_org",
                #     repo="your_repo",
                #     title="Test Issue from Integration Agent",
                #     body="This is a test issue created by the Integration Agent example.",
                #     labels=["test", "integration"]
                # )
                # logger.info(f"Created issue #{new_issue['number']}")
                
            except Exception as e:
                logger.error(f"GitHub integration error: {e}")
    
    async def example_2_slack_bot_integration(self):
        """Example 2: Slack bot integration with message handling."""
        logger.info("🚀 Example 2: Slack Bot Integration")
        
        # Configure Slack client
        slack_config = SlackConfig(
            bot_token="xoxb-your-bot-token",  # Replace with actual token
            webhook_url="https://hooks.slack.com/services/...",
            signing_secret="your_signing_secret",
            default_channel="#general"
        )
        
        async with SlackClient(slack_config) as slack_client:
            try:
                # Test connection
                connection_test = await slack_client.test_connection()
                logger.info(f"Slack connection: {connection_test['status']}")
                
                # Send a simple message
                # message = await slack_client.send_message(
                #     channel="#test",
                #     text="Hello from the Integration Agent! 🤖"
                # )
                # logger.info(f"Sent message: {message['ts']}")
                
                # Send a formatted notification
                # await slack_client.send_notification(
                #     message="Integration Agent is now online and ready to assist!",
                #     level="success"
                # )
                
                # Register event handlers
                async def handle_message(event):
                    event_data = event.event_data
                    user = event_data.get("user")
                    text = event_data.get("text", "")
                    
                    if "hello" in text.lower():
                        await slack_client.send_message(
                            event_data.get("channel"),
                            f"Hello <@{user}>! How can I help you today?"
                        )
                
                slack_client.register_event_handler(SlackEventType.MESSAGE, handle_message)
                
            except Exception as e:
                logger.error(f"Slack integration error: {e}")
    
    async def example_3_api_gateway_setup(self):
        """Example 3: API Gateway setup with authentication and rate limiting."""
        logger.info("🚀 Example 3: API Gateway Setup")
        
        # Configure API Gateway
        # Note: Using "0.0.0.0" for examples only. Use "127.0.0.1" in production for security
        config = ApiGatewayConfig(
            host="0.0.0.0",
            port=8080,
            api_prefix="/api/v1",
            auth_required=True,
            enable_cors=True,
            cors_origins=["*"],
            rate_limit_requests=100,
            rate_limit_window=60
        )
        
        # Initialize API Gateway
        gateway = ApiGateway(config)
        
        # Create API key for testing
        api_key = gateway.auth_middleware.create_api_key(
            user_id="test_user",
            permissions=["read", "write"],
            expires_in_hours=24
        )
        logger.info(f"Created API key: {api_key}")
        
        # Define route handlers
        async def health_check(request):
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        
        async def get_integrations(request):
            return {
                "integrations": [
                    {"name": "github", "status": "connected"},
                    {"name": "slack", "status": "connected"},
                    {"name": "service_discovery", "status": "running"}
                ]
            }
        
        async def create_integration(request):
            return {
                "message": "Integration created successfully",
                "integration_id": "int_123456",
                "status": "pending"
            }
        
        # Register routes
        gateway.register_route("/health", "GET", health_check)
        gateway.register_route("/integrations", "GET", get_integrations)
        gateway.register_route("/integrations", "POST", create_integration)
        
        # Register versioned routes
        async def get_integrations_v2(request):
            return {
                "integrations": [
                    {
                        "name": "github",
                        "status": "connected",
                        "version": "v4",
                        "last_sync": "2023-07-15T10:30:00Z"
                    },
                    {
                        "name": "slack",
                        "status": "connected",
                        "version": "v1",
                        "last_sync": "2023-07-15T10:29:00Z"
                    }
                ]
            }
        
        gateway.register_route("/integrations", "GET", get_integrations_v2, version="v2")
        
        # Start server
        await gateway.start_server()
        logger.info("API Gateway started on http://0.0.0.0:8080 (example only - use 127.0.0.1 in production)")
        
        # Test API call
        test_request = ApiRequest(
            method="GET",
            path="/api/v1/health",
            headers={"X-API-Key": api_key},
            body=None,
            client_ip="127.0.0.1",
            request_id="test_001"
        )
        
        response = await gateway.handle_request(test_request)
        logger.info(f"Test response: {response.body}")
        
        # Stop server
        await gateway.stop_server()
    
    async def example_4_service_discovery(self):
        """Example 4: Service discovery with health monitoring."""
        logger.info("🚀 Example 4: Service Discovery")
        
        # Configure service discovery
        discovery_config = {
            "strategy": "dynamic",
            "cleanup_enabled": True,
            "cleanup_interval": 60,
            "service_ttl": 300
        }
        
        discovery = ServiceDiscovery(discovery_config)
        await discovery.start()
        
        # Register multiple services
        services = [
            ServiceInfo(
                service_id="user_service_1",
                service_name="user_service",
                service_type="api",
                host="user-service.internal",
                port=8080,
                endpoints=["/users", "/profiles"],
                metadata={"version": "1.2.3", "region": "us-east-1"},
                tags=["user", "profile", "api"],
                status=ServiceStatus.HEALTHY
            ),
            ServiceInfo(
                service_id="payment_service_1",
                service_name="payment_service",
                service_type="api",
                host="payment-service.internal",
                port=8080,
                endpoints=["/payments", "/refunds"],
                metadata={"version": "2.1.0", "region": "us-east-1"},
                tags=["payment", "financial", "critical"],
                status=ServiceStatus.HEALTHY
            ),
            ServiceInfo(
                service_id="notification_service_1",
                service_name="notification_service",
                service_type="worker",
                host="notification-worker.internal",
                port=8080,
                endpoints=["/notify", "/templates"],
                metadata={"version": "1.0.5", "region": "us-west-2"},
                tags=["notification", "email", "sms"],
                status=ServiceStatus.HEALTHY
            )
        ]
        
        # Register services
        for service in services:
            await discovery.register_service(service)
            logger.info(f"Registered service: {service.service_name}")
        
        # Discover services
        user_services = await discovery.discover_services(
            service_name="user_service",
            status=ServiceStatus.HEALTHY
        )
        logger.info(f"Found {len(user_services)} user services")
        
        api_services = await discovery.discover_services(
            service_type="api",
            status=ServiceStatus.HEALTHY
        )
        logger.info(f"Found {len(api_services)} API services")
        
        critical_services = await discovery.discover_services(
            tags=["critical"],
            status=ServiceStatus.HEALTHY
        )
        logger.info(f"Found {len(critical_services)} critical services")
        
        # Get service health
        for service in services:
            health = await discovery.get_service_health(service.service_id)
            logger.info(f"Service {service.service_name} health: {health['status']}")
        
        # Stop discovery
        await discovery.stop()
    
    async def example_5_full_integration_manager(self):
        """Example 5: Full integration manager with all components."""
        logger.info("🚀 Example 5: Full Integration Manager")
        
        # Configure all integrations
        github_config = GitHubConfig(
            token="your_github_token",
            webhook_secret="your_webhook_secret",
            default_owner="your_org",
            default_repo="your_repo"
        )
        
        slack_config = SlackConfig(
            bot_token="xoxb-your-bot-token",
            webhook_url="https://hooks.slack.com/services/...",
            signing_secret="your_signing_secret",
            default_channel="#general"
        )
        
        integration_config = IntegrationConfig(
            github=github_config,
            slack=slack_config,
            notification_channels=["slack:#alerts", "email:admin@example.com"],
            auto_sync_interval=300,
            health_check_interval=60
        )
        
        # Initialize coordinator
        coordinator_config = CoordinatorConfig(
            max_agents=10,
            failure_threshold=3,
            resource_limits={"cpu": 100, "memory": 1000}
        )
        
        coordinator = MultiAgentCoordinator(coordinator_config)
        await coordinator.start()
        
        # Initialize integration manager
        manager = IntegrationManager(
            integration_config,
            coordinator=coordinator
        )
        
        # Register event handlers
        async def handle_github_pr(event):
            pr_data = event.payload.get("pull_request", {})
            pr_number = pr_data.get("number")
            pr_title = pr_data.get("title")
            
            await manager.send_notification(
                f"🔄 New PR #{pr_number}: {pr_title}",
                level="info"
            )
        
        async def handle_github_issue(event):
            issue_data = event.payload.get("issue", {})
            issue_number = issue_data.get("number")
            issue_title = issue_data.get("title")
            action = event.payload.get("action")
            
            if action == "opened":
                await manager.send_notification(
                    f"🐛 New issue #{issue_number}: {issue_title}",
                    level="warning"
                )
        
        async def handle_slack_mention(event):
            event_data = event.event_data
            user = event_data.get("user")
            text = event_data.get("text", "")
            
            if "status" in text.lower():
                status = manager.get_integration_status()
                healthy_count = sum(1 for integration in status["integrations"].values() 
                                  if integration["status"] == "connected")
                
                await manager.send_notification(
                    f"🤖 Integration Status: {healthy_count} integrations healthy",
                    level="success"
                )
        
        # Register handlers
        manager.register_event_handler("github_pull_request", handle_github_pr)
        manager.register_event_handler("github_issue", handle_github_issue)
        manager.register_event_handler("slack_mention", handle_slack_mention)
        
        # Start integration manager
        await manager.start()
        
        # Send startup notification
        await manager.send_notification(
            "🚀 Integration Manager started successfully!",
            level="success"
        )
        
        # Get and display status
        status = manager.get_integration_status()
        logger.info(f"Integration status: {status}")
        
        # Simulate running for a while
        await asyncio.sleep(5)
        
        # Stop integration manager
        await manager.stop()
        await coordinator.stop()
    
    async def example_6_webhook_server(self):
        """Example 6: Webhook server for GitHub and Slack events."""
        logger.info("🚀 Example 6: Webhook Server")
        
        from aiohttp import web
        import json
        
        # Configure GitHub client
        github_config = GitHubConfig(
            token="your_github_token",
            webhook_secret="your_webhook_secret"
        )
        
        github_client = GitHubClient(github_config)
        
        # Configure Slack client
        slack_config = SlackConfig(
            signing_secret="your_signing_secret",
            default_channel="#webhooks"
        )
        
        slack_client = SlackClient(slack_config)
        
        # GitHub webhook handler
        async def github_webhook(request):
            try:
                headers = dict(request.headers)
                payload = await request.read()
                
                # Process GitHub webhook
                event = await github_client.process_webhook_event(headers, payload)
                
                logger.info(f"GitHub webhook: {event.event_type.value}")
                logger.info(f"Repository: {event.repository}")
                logger.info(f"Sender: {event.sender}")
                
                return web.Response(text="OK", status=200)
                
            except Exception as e:
                logger.error(f"GitHub webhook error: {e}")
                return web.Response(text="Error", status=400)
        
        # Slack webhook handler
        async def slack_webhook(request):
            try:
                headers = dict(request.headers)
                body = await request.read()
                
                # Verify signature
                timestamp = headers.get("X-Slack-Request-Timestamp")
                signature = headers.get("X-Slack-Signature")
                
                if not slack_client.verify_webhook_signature(body, timestamp, signature):
                    return web.Response(text="Invalid signature", status=401)
                
                # Parse event
                data = json.loads(body.decode())
                
                # Handle URL verification
                if data.get("type") == "url_verification":
                    return web.Response(text=data["challenge"], status=200)
                
                # Process event
                if data.get("type") == "event_callback":
                    event_data = data.get("event", {})
                    await slack_client.process_event(event_data)
                
                return web.Response(text="OK", status=200)
                
            except Exception as e:
                logger.error(f"Slack webhook error: {e}")
                return web.Response(text="Error", status=400)
        
        # Create webhook server
        app = web.Application()
        app.router.add_post("/webhook/github", github_webhook)
        app.router.add_post("/webhook/slack", slack_webhook)
        
        logger.info("Webhook server configured")
        logger.info("GitHub webhook URL: http://localhost:8000/webhook/github")
        logger.info("Slack webhook URL: http://localhost:8000/webhook/slack")
        
        # Note: In a real application, you would run this server
        # web.run_app(app, host="0.0.0.0", port=8000)  # Use "127.0.0.1" in production
    
    async def example_7_monitoring_dashboard(self):
        """Example 7: Monitoring dashboard with health checks and metrics."""
        logger.info("🚀 Example 7: Monitoring Dashboard")
        
        # Configure components
        github_config = GitHubConfig(token="your_github_token")
        slack_config = SlackConfig(bot_token="xoxb-your-bot-token")
        
        github_client = GitHubClient(github_config)
        slack_client = SlackClient(slack_config)
        
        # Perform health checks
        logger.info("Performing health checks...")
        
        try:
            github_health = await github_client.health_check()
            logger.info(f"GitHub health: {github_health['status']}")
        except Exception as e:
            logger.error(f"GitHub health check failed: {e}")
        
        try:
            slack_health = await slack_client.health_check()
            logger.info(f"Slack health: {slack_health['status']}")
        except Exception as e:
            logger.error(f"Slack health check failed: {e}")
        
        # Collect metrics
        logger.info("Collecting metrics...")
        
        try:
            github_stats = github_client.get_client_stats()
            logger.info(f"GitHub stats: {github_stats}")
        except Exception as e:
            logger.error(f"GitHub stats collection failed: {e}")
        
        try:
            slack_stats = slack_client.get_client_stats()
            logger.info(f"Slack stats: {slack_stats}")
        except Exception as e:
            logger.error(f"Slack stats collection failed: {e}")
        
        # Create monitoring report
        monitoring_report = {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "github": {
                    "status": "healthy",
                    "response_time": "120ms",
                    "requests_today": 1250,
                    "rate_limit_remaining": 4750
                },
                "slack": {
                    "status": "healthy",
                    "response_time": "85ms",
                    "messages_sent_today": 342,
                    "channels_active": 15
                }
            },
            "system": {
                "cpu_usage": "45%",
                "memory_usage": "67%",
                "disk_usage": "23%",
                "network_io": "1.2MB/s"
            }
        }
        
        logger.info("Monitoring report generated:")
        logger.info(json.dumps(monitoring_report, indent=2))
        
        # Disconnect clients
        await github_client.disconnect()
        await slack_client.disconnect()


async def main():
    """Run all examples."""
    examples = IntegrationExamples()
    
    logger.info("=" * 60)
    logger.info("🤖 Integration Agent Examples")
    logger.info("=" * 60)
    
    try:
        # Run examples (comment out examples that require real API credentials)
        # await examples.example_1_basic_github_integration()
        # await examples.example_2_slack_bot_integration()
        await examples.example_3_api_gateway_setup()
        await examples.example_4_service_discovery()
        # await examples.example_5_full_integration_manager()
        # await examples.example_6_webhook_server()
        await examples.example_7_monitoring_dashboard()
        
        logger.info("✅ All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Example execution failed: {e}")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())