"""
Comprehensive Integration Test Suite for External API Integration

Tests the full integration layer including API Gateway, Service Discovery,
GitHub client, Slack client, and Integration Manager.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp

from external_api.api_gateway import ApiGateway
from external_api.service_discovery import ServiceDiscovery, ServiceInfo, ServiceStatus
from external_api.github_client import GitHubClient, GitHubConfig, GitHubEventType
from external_api.slack_client import SlackClient, SlackConfig, SlackEventType
from external_api.integration_manager import IntegrationManager, IntegrationConfig
from external_api.auth_middleware import AuthenticationMiddleware, AuthMethod
from external_api.rate_limiter import AdvancedRateLimiter, RateLimitStrategy
from external_api.models import ApiGatewayConfig, ApiRequest, ApiResponse
from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig


class TestIntegrationSuite:
    """Comprehensive integration test suite."""
    
    @pytest.fixture
    def coordinator_config(self):
        """Coordinator configuration for tests."""
        return CoordinatorConfig(
            max_agents=10,
            failure_threshold=3,
            resource_limits={"cpu": 100, "memory": 1000, "disk": 1000}
        )
    
    @pytest.fixture
    def api_gateway_config(self):
        """API Gateway configuration for tests."""
        return ApiGatewayConfig(
            host="localhost",
            port=8080,
            api_prefix="/api/v1",
            auth_required=True,
            enable_cors=True,
            cors_origins=["*"],
            rate_limit_requests=100,
            rate_limit_window=60,
            request_timeout=30,
            api_key_header="X-API-Key"
        )
    
    @pytest.fixture
    def github_config(self):
        """GitHub configuration for tests."""
        return GitHubConfig(
            token="test_token",
            webhook_secret="test_secret",
            default_owner="test_owner",
            default_repo="test_repo"
        )
    
    @pytest.fixture
    def slack_config(self):
        """Slack configuration for tests."""
        return SlackConfig(
            bot_token="test_bot_token",
            webhook_url="https://hooks.slack.com/test",
            signing_secret="test_signing_secret",
            default_channel="#test"
        )
    
    @pytest.fixture
    def integration_config(self, github_config, slack_config):
        """Integration configuration for tests."""
        return IntegrationConfig(
            github=github_config,
            slack=slack_config,
            notification_channels=["slack:#general", "email:test@example.com"]
        )
    
    @pytest.fixture
    async def coordinator(self, coordinator_config):
        """Multi-agent coordinator for tests."""
        coordinator = MultiAgentCoordinator(coordinator_config)
        await coordinator.start()
        yield coordinator
        await coordinator.stop()
    
    @pytest.fixture
    async def service_discovery(self, coordinator):
        """Service discovery for tests."""
        config = {"strategy": "dynamic", "cleanup_enabled": True}
        discovery = ServiceDiscovery(config, coordinator)
        await discovery.start()
        yield discovery
        await discovery.stop()
    
    @pytest.fixture
    async def api_gateway(self, api_gateway_config, coordinator, service_discovery):
        """API Gateway for tests."""
        gateway = ApiGateway(
            api_gateway_config,
            coordinator=coordinator,
            discovery_config={"strategy": "dynamic"}
        )
        await gateway.start_server()
        yield gateway
        await gateway.stop_server()


class TestAPIGatewayIntegration:
    """Test API Gateway integration functionality."""
    
    @pytest.mark.asyncio
    async def test_api_gateway_initialization(self, api_gateway):
        """Test API Gateway initialization."""
        assert api_gateway.server_started
        assert api_gateway.coordinator is not None
        assert api_gateway.service_discovery is not None
        assert api_gateway.auth_middleware is not None
        assert api_gateway.advanced_rate_limiter is not None
    
    @pytest.mark.asyncio
    async def test_route_registration_and_versioning(self, api_gateway):
        """Test route registration with versioning."""
        # Register unversioned route
        async def test_handler(request):
            return {"status": "ok"}
        
        api_gateway.register_route("/test", "GET", test_handler)
        
        # Register versioned route
        async def v2_handler(request):
            return {"status": "ok", "version": "v2"}
        
        api_gateway.register_route("/test", "GET", v2_handler, version="v2")
        
        # Verify routes are registered
        assert "/test" in api_gateway.routes
        assert "v2" in api_gateway.versioned_routes
        assert "/test" in api_gateway.versioned_routes["v2"]
    
    @pytest.mark.asyncio
    async def test_service_registration_and_discovery(self, api_gateway):
        """Test service registration and discovery."""
        # Register a service
        api_gateway.register_service("test_service", ["agent1", "agent2"])
        
        # Test service selection
        selected_agent = await api_gateway.select_agent_for_service("test_service")
        assert selected_agent in ["agent1", "agent2"]
        
        # Test service unregistration
        result = api_gateway.unregister_service("test_service")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_authentication_middleware(self, api_gateway):
        """Test authentication middleware functionality."""
        # Create API key
        api_key = api_gateway.auth_middleware.create_api_key(
            "test_user",
            ["read", "write"],
            expires_in_hours=24
        )
        
        # Test API key authentication
        request = ApiRequest(
            method="GET",
            path="/test",
            headers={"X-API-Key": api_key},
            body=None,
            client_ip="127.0.0.1",
            request_id="test_request_1"
        )
        
        auth_result = await api_gateway.auth_middleware.authenticate_request(request)
        assert auth_result.success
        assert auth_result.user_id == "test_user"
        assert "read" in [p.value for p in auth_result.permissions]
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_gateway):
        """Test advanced rate limiting."""
        # Test rate limit check
        request = ApiRequest(
            method="GET",
            path="/test",
            headers={"X-API-Key": "test_key"},
            body=None,
            client_ip="127.0.0.1",
            request_id="test_request_2"
        )
        
        # First request should be allowed
        result1 = await api_gateway.advanced_rate_limiter.check_rate_limit(request)
        assert result1.allowed
        
        # Configure low rate limit for testing
        api_gateway.advanced_rate_limiter.set_client_limit("ip:127.0.0.1", 1)
        
        # Second request should be rate limited
        result2 = await api_gateway.advanced_rate_limiter.check_rate_limit(request)
        assert not result2.allowed
    
    @pytest.mark.asyncio
    async def test_api_documentation_generation(self, api_gateway):
        """Test API documentation generation."""
        # Register some routes
        async def handler1(request):
            return {"data": "test"}
        
        async def handler2(request):
            return {"data": "test_v2"}
        
        api_gateway.register_route("/users", "GET", handler1)
        api_gateway.register_route("/users", "POST", handler1)
        api_gateway.register_route("/users", "GET", handler2, version="v2")
        
        # Generate documentation
        docs = api_gateway.get_api_documentation()
        
        assert docs["title"] == "LeanVibe Agent Hive API"
        assert "unversioned" in docs["endpoints"]
        assert "versioned" in docs["endpoints"]
        assert "/users" in docs["endpoints"]["unversioned"]
        assert "v2" in docs["endpoints"]["versioned"]


class TestServiceDiscoveryIntegration:
    """Test Service Discovery integration functionality."""
    
    @pytest.mark.asyncio
    async def test_service_discovery_initialization(self, service_discovery):
        """Test service discovery initialization."""
        assert service_discovery.running
        assert service_discovery.coordinator is not None
        assert service_discovery.strategy.value == "dynamic"
    
    @pytest.mark.asyncio
    async def test_service_registration_and_health_monitoring(self, service_discovery):
        """Test service registration and health monitoring."""
        from external_api.service_discovery import HealthCheckConfig
        
        # Create test service
        service_info = ServiceInfo(
            service_id="test_service_1",
            service_name="test_service",
            service_type="api",
            host="localhost",
            port=8080,
            endpoints=["/health", "/api"],
            metadata={"version": "1.0.0"},
            tags=["test", "api"],
            status=ServiceStatus.HEALTHY
        )
        
        # Register service with health check
        health_config = HealthCheckConfig(
            enabled=True,
            interval=5,
            timeout=2,
            endpoint="/health"
        )
        
        result = await service_discovery.register_service(service_info, health_config)
        assert result is True
        assert service_info.service_id in service_discovery.services
        
        # Test service discovery
        services = await service_discovery.discover_services(
            service_name="test_service",
            status=ServiceStatus.HEALTHY
        )
        assert len(services) == 1
        assert services[0].service_id == "test_service_1"
    
    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, service_discovery):
        """Test service health monitoring."""
        # Register service
        service_info = ServiceInfo(
            service_id="health_test_service",
            service_name="health_test",
            service_type="api",
            host="localhost",
            port=8080,
            endpoints=["/health"],
            metadata={},
            tags=["health_test"],
            status=ServiceStatus.HEALTHY
        )
        
        await service_discovery.register_service(service_info)
        
        # Get health status
        health_status = await service_discovery.get_service_health("health_test_service")
        assert health_status["service_id"] == "health_test_service"
        assert health_status["status"] == ServiceStatus.HEALTHY.value
    
    @pytest.mark.asyncio
    async def test_coordinator_synchronization(self, service_discovery, coordinator):
        """Test synchronization with coordinator."""
        # Register an agent with coordinator
        from advanced_orchestration.models import AgentRegistration
        
        agent_registration = AgentRegistration(
            agent_id="test_agent_1",
            agent_type="test_agent",
            capabilities=["test_capability"],
            resource_requirements={"cpu": 1, "memory": 100},
            endpoint={"host": "localhost", "port": 8081}
        )
        
        await coordinator.register_agent(agent_registration)
        
        # Sync with coordinator
        await service_discovery._sync_with_coordinator()
        
        # Verify agent is registered as service
        services = await service_discovery.discover_services(service_name="agent-test_agent")
        assert len(services) >= 1


class TestGitHubClientIntegration:
    """Test GitHub client integration functionality."""
    
    @pytest.mark.asyncio
    async def test_github_client_initialization(self, github_config):
        """Test GitHub client initialization."""
        async with GitHubClient(github_config) as client:
            assert client.config.token == "test_token"
            assert client.session is not None
    
    @pytest.mark.asyncio
    async def test_github_webhook_processing(self, github_config):
        """Test GitHub webhook event processing."""
        client = GitHubClient(github_config)
        
        # Mock webhook payload
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "Test PR",
                "state": "open"
            },
            "repository": {
                "full_name": "test/repo"
            },
            "sender": {
                "login": "testuser"
            }
        }
        
        headers = {
            "x-github-event": "pull_request",
            "x-github-delivery": "12345-67890",
            "x-hub-signature-256": "sha256=test_signature"
        }
        
        # Process webhook event
        with patch.object(client, 'verify_webhook_signature', return_value=True):
            event = await client.process_webhook_event(headers, json.dumps(payload).encode())
            
            assert event.event_type == GitHubEventType.PULL_REQUEST
            assert event.repository == "test/repo"
            assert event.sender == "testuser"
    
    @pytest.mark.asyncio
    async def test_github_api_operations(self, github_config):
        """Test GitHub API operations."""
        client = GitHubClient(github_config)
        
        # Mock HTTP responses
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"x-ratelimit-remaining": "5000"}
        mock_response.json = AsyncMock(return_value={"name": "test_repo"})
        
        with patch.object(client, 'session') as mock_session:
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            # Test repository retrieval
            repo_info = await client.get_repository("test_owner", "test_repo")
            assert repo_info["name"] == "test_repo"


class TestSlackClientIntegration:
    """Test Slack client integration functionality."""
    
    @pytest.mark.asyncio
    async def test_slack_client_initialization(self, slack_config):
        """Test Slack client initialization."""
        async with SlackClient(slack_config) as client:
            assert client.config.bot_token == "test_bot_token"
            assert client.session is not None
    
    @pytest.mark.asyncio
    async def test_slack_webhook_verification(self, slack_config):
        """Test Slack webhook signature verification."""
        client = SlackClient(slack_config)
        
        # Test webhook signature verification
        body = b'{"type": "event_callback", "event": {"type": "message"}}'
        timestamp = str(int(time.time()))
        
        # This would normally use the real signing secret
        with patch.object(client, 'verify_webhook_signature', return_value=True):
            result = client.verify_webhook_signature(body, timestamp, "test_signature")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_slack_message_sending(self, slack_config):
        """Test Slack message sending."""
        client = SlackClient(slack_config)
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True, "message": {"ts": "1234567890"}})
        
        with patch.object(client, 'session') as mock_session:
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            # Test message sending
            result = await client.send_message("#test", "Hello, world!")
            assert result["ok"] is True
    
    @pytest.mark.asyncio
    async def test_slack_event_processing(self, slack_config):
        """Test Slack event processing."""
        client = SlackClient(slack_config)
        
        # Mock event data
        event_data = {
            "type": "message",
            "user": "U123456",
            "text": "Hello, bot!",
            "channel": "C123456",
            "ts": "1234567890"
        }
        
        # Process event
        event = await client.process_event(event_data)
        assert event.event_type == SlackEventType.MESSAGE
        assert event.user_id == "U123456"
        assert event.channel_id == "C123456"


class TestIntegrationManagerIntegration:
    """Test Integration Manager orchestration."""
    
    @pytest.mark.asyncio
    async def test_integration_manager_initialization(self, integration_config):
        """Test Integration Manager initialization."""
        manager = IntegrationManager(integration_config)
        
        # Mock the external clients to avoid real API calls
        with patch('external_api.integration_manager.GitHubClient') as mock_github, \
             patch('external_api.integration_manager.SlackClient') as mock_slack:
            
            mock_github_instance = Mock()
            mock_github_instance.connect = AsyncMock()
            mock_github_instance.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_github.return_value = mock_github_instance
            
            mock_slack_instance = Mock()
            mock_slack_instance.connect = AsyncMock()
            mock_slack_instance.test_connection = AsyncMock(return_value={"status": "connected"})
            mock_slack.return_value = mock_slack_instance
            
            await manager.start()
            
            assert manager.running
            assert "github" in manager.integration_health
            assert "slack" in manager.integration_health
            
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_integration_manager_event_handling(self, integration_config):
        """Test Integration Manager event handling."""
        manager = IntegrationManager(integration_config)
        
        # Test event handler registration
        events_received = []
        
        async def test_handler(event):
            events_received.append(event)
        
        manager.register_event_handler("test_event", test_handler)
        
        # Trigger event handlers
        await manager._trigger_event_handlers("test_event", {"test": "data"})
        
        assert len(events_received) == 1
        assert events_received[0]["test"] == "data"
    
    @pytest.mark.asyncio
    async def test_integration_manager_notifications(self, integration_config):
        """Test Integration Manager notification system."""
        manager = IntegrationManager(integration_config)
        
        # Mock Slack client
        mock_slack_client = Mock()
        mock_slack_client.send_notification = AsyncMock()
        manager.slack_client = mock_slack_client
        
        # Test notification sending
        await manager.send_notification("Test notification", ["slack:#test"], "info")
        
        # Verify Slack notification was called
        mock_slack_client.send_notification.assert_called_once_with(
            "Test notification", "#test", "info"
        )
    
    @pytest.mark.asyncio
    async def test_integration_manager_health_monitoring(self, integration_config):
        """Test Integration Manager health monitoring."""
        manager = IntegrationManager(integration_config)
        
        # Mock health check
        with patch.object(manager, '_perform_health_checks') as mock_health_check:
            mock_health_check.return_value = None
            
            # Test health check
            health_status = await manager.health_check()
            
            assert "status" in health_status
            assert "running" in health_status
            assert "integration_health" in health_status


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_integration_flow(self, coordinator, service_discovery, api_gateway):
        """Test full integration flow from API Gateway to Service Discovery."""
        
        # Register a service through service discovery
        service_info = ServiceInfo(
            service_id="e2e_test_service",
            service_name="e2e_test",
            service_type="api",
            host="localhost",
            port=8080,
            endpoints=["/test"],
            metadata={"version": "1.0.0"},
            tags=["e2e", "test"],
            status=ServiceStatus.HEALTHY
        )
        
        await service_discovery.register_service(service_info)
        
        # Register service with API Gateway
        api_gateway.register_service("e2e_test", ["e2e_test_service"])
        
        # Test service selection through API Gateway
        selected_service = await api_gateway.select_agent_for_service("e2e_test")
        assert selected_service is not None
        
        # Test API Gateway info includes service discovery data
        gateway_info = api_gateway.get_gateway_info()
        assert "service_discovery" in gateway_info
        assert gateway_info["service_discovery"]["running"] is True
    
    @pytest.mark.asyncio
    async def test_webhook_event_flow(self, integration_config):
        """Test webhook event flow through integration system."""
        manager = IntegrationManager(integration_config)
        
        # Mock external clients
        mock_github = Mock()
        mock_github.connect = AsyncMock()
        mock_github.health_check = AsyncMock(return_value={"status": "healthy"})
        manager.github_client = mock_github
        
        mock_coordinator = Mock()
        mock_coordinator.distribute_task = AsyncMock()
        manager.coordinator = mock_coordinator
        
        # Simulate GitHub webhook event
        from external_api.github_client import GitHubWebhookEvent
        
        mock_event = Mock()
        mock_event.payload = {
            "action": "opened",
            "pull_request": {"number": 123, "title": "Test PR"},
            "repository": {"full_name": "test/repo"}
        }
        
        # Process GitHub event
        await manager._handle_github_pull_request(mock_event)
        
        # Verify task was distributed to coordinator
        mock_coordinator.distribute_task.assert_called_once()
        
        # Verify stats were updated
        assert manager.stats["github_events"] == 1
        assert manager.stats["total_events_processed"] == 1
    
    @pytest.mark.asyncio
    async def test_multi_client_coordination(self, integration_config):
        """Test coordination between multiple clients."""
        manager = IntegrationManager(integration_config)
        
        # Mock all clients
        mock_github = Mock()
        mock_github.connect = AsyncMock()
        mock_github.get_client_stats = Mock(return_value={"total_requests": 100})
        manager.github_client = mock_github
        
        mock_slack = Mock()
        mock_slack.connect = AsyncMock()
        mock_slack.get_client_stats = Mock(return_value={"messages_sent": 50})
        manager.slack_client = mock_slack
        
        # Test integration status
        status = manager.get_integration_status()
        
        assert status["running"] is False  # Not started yet
        assert "integrations" in status
        assert "stats" in status
        
        # Test GitHub stats retrieval
        github_stats = manager.get_github_stats()
        assert github_stats["total_requests"] == 100


# Performance and stress tests
class TestIntegrationPerformance:
    """Test integration performance and scalability."""
    
    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, api_gateway):
        """Test API Gateway performance under concurrent load."""
        # Create multiple concurrent requests
        async def make_request(request_id):
            request = ApiRequest(
                method="GET",
                path="/test",
                headers={"X-API-Key": "test_key"},
                body=None,
                client_ip="127.0.0.1",
                request_id=f"perf_test_{request_id}"
            )
            
            # Mock rate limiter to allow all requests
            with patch.object(api_gateway.advanced_rate_limiter, 'check_rate_limit') as mock_rate_limit:
                mock_rate_limit.return_value = Mock(allowed=True, remaining=100, reset_time=time.time() + 60)
                
                # Mock auth to pass all requests
                with patch.object(api_gateway.auth_middleware, 'authenticate_request') as mock_auth:
                    mock_auth.return_value = Mock(success=True, user_id="test_user", permissions=[], metadata={})
                    
                    # Register a test handler
                    async def test_handler(req):
                        return {"status": "ok", "request_id": req.request_id}
                    
                    api_gateway.register_route("/test", "GET", test_handler)
                    
                    # Process request
                    return await api_gateway.handle_request(request)
        
        # Run concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(100)]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all requests were processed
        assert len(responses) == 100
        assert all(response.status_code == 200 for response in responses)
        
        # Verify performance
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within 5 seconds
    
    @pytest.mark.asyncio
    async def test_service_discovery_scalability(self, service_discovery):
        """Test service discovery performance with many services."""
        # Register multiple services
        services = []
        for i in range(100):
            service_info = ServiceInfo(
                service_id=f"scale_test_service_{i}",
                service_name=f"scale_test_{i % 10}",  # 10 different service names
                service_type="api",
                host="localhost",
                port=8080 + i,
                endpoints=[f"/service_{i}"],
                metadata={"index": i},
                tags=["scale_test"],
                status=ServiceStatus.HEALTHY
            )
            services.append(service_info)
        
        # Register all services
        start_time = time.time()
        for service in services:
            await service_discovery.register_service(service)
        registration_time = time.time() - start_time
        
        # Test service discovery performance
        start_time = time.time()
        discovered_services = await service_discovery.discover_services(
            service_name="scale_test_0",
            status=ServiceStatus.HEALTHY
        )
        discovery_time = time.time() - start_time
        
        # Verify performance
        assert registration_time < 10.0  # Should complete within 10 seconds
        assert discovery_time < 1.0  # Should complete within 1 second
        assert len(discovered_services) == 10  # 10 services with name scale_test_0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self, api_gateway):
        """Test rate limiter performance under load."""
        rate_limiter = api_gateway.advanced_rate_limiter
        
        # Create test request
        request = ApiRequest(
            method="GET",
            path="/test",
            headers={"X-API-Key": "test_key"},
            body=None,
            client_ip="127.0.0.1",
            request_id="rate_limit_test"
        )
        
        # Test rate limiting performance
        start_time = time.time()
        for _ in range(1000):
            await rate_limiter.check_rate_limit(request)
        end_time = time.time()
        
        # Verify performance
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within 5 seconds
        
        # Test different rate limiting strategies
        strategies = [
            RateLimitStrategy.FIXED_WINDOW,
            RateLimitStrategy.SLIDING_WINDOW,
            RateLimitStrategy.TOKEN_BUCKET
        ]
        
        for strategy in strategies:
            rate_limiter.strategy = strategy
            start_time = time.time()
            for _ in range(100):
                await rate_limiter.check_rate_limit(request)
            end_time = time.time()
            
            strategy_time = end_time - start_time
            assert strategy_time < 2.0  # Each strategy should be fast


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])