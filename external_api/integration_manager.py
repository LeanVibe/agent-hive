"""
Integration Manager for External API Clients

Coordinates and manages all external API integrations including GitHub,
Slack, and other third-party services.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from .github_client import GitHubClient, GitHubConfig, GitHubEventType
from .api_gateway import ApiGateway
from .service_discovery import ServiceDiscovery
from ..advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator


logger = logging.getLogger(__name__)


class IntegrationStatus(Enum):
    """Integration status states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    INITIALIZING = "initializing"


@dataclass
class IntegrationConfig:
    """Configuration for external integrations."""
    github: Optional[GitHubConfig] = None
    slack_webhook_url: Optional[str] = None
    slack_token: Optional[str] = None
    notification_channels: Optional[List[str]] = None
    auto_sync_interval: int = 300  # 5 minutes
    health_check_interval: int = 60  # 1 minute
    retry_failed_operations: bool = True
    max_retry_attempts: int = 3


@dataclass
class IntegrationHealth:
    """Health status of an integration."""
    name: str
    status: IntegrationStatus
    last_check: datetime
    error_message: Optional[str] = None
    response_time: Optional[float] = None
    success_rate: float = 0.0


class IntegrationManager:
    """
    Manages all external API integrations.
    
    Coordinates GitHub, Slack, and other external service integrations
    with the agent-hive system.
    """
    
    def __init__(self, config: IntegrationConfig, 
                 coordinator: Optional[MultiAgentCoordinator] = None,
                 api_gateway: Optional[ApiGateway] = None,
                 service_discovery: Optional[ServiceDiscovery] = None):
        """
        Initialize integration manager.
        
        Args:
            config: Integration configuration
            coordinator: Multi-agent coordinator
            api_gateway: API gateway instance
            service_discovery: Service discovery instance
        """
        self.config = config
        self.coordinator = coordinator
        self.api_gateway = api_gateway
        self.service_discovery = service_discovery
        
        # Integration clients
        self.github_client: Optional[GitHubClient] = None
        self.slack_client: Optional[Any] = None  # To be implemented
        
        # Integration health tracking
        self.integration_health: Dict[str, IntegrationHealth] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Background tasks
        self.running = False
        self.sync_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_events_processed": 0,
            "github_events": 0,
            "slack_events": 0,
            "integration_failures": 0,
            "auto_sync_runs": 0
        }
        
        logger.info("IntegrationManager initialized")
    
    async def start(self) -> None:
        """Start the integration manager."""
        if self.running:
            logger.warning("Integration manager already running")
            return
        
        self.running = True
        logger.info("Starting integration manager")
        
        # Initialize integrations
        await self._initialize_integrations()
        
        # Start background tasks
        self.sync_task = asyncio.create_task(self._auto_sync_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Integration manager started")
    
    async def stop(self) -> None:
        """Stop the integration manager."""
        if not self.running:
            logger.warning("Integration manager not running")
            return
        
        self.running = False
        logger.info("Stopping integration manager")
        
        # Cancel background tasks
        if self.sync_task:
            self.sync_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Wait for tasks to complete
        if self.sync_task:
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        if self.health_check_task:
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect integrations
        await self._disconnect_integrations()
        
        logger.info("Integration manager stopped")
    
    async def _initialize_integrations(self) -> None:
        """Initialize all configured integrations."""
        # Initialize GitHub integration
        if self.config.github:
            try:
                self.github_client = GitHubClient(self.config.github)
                await self.github_client.connect()
                
                # Register webhook handlers
                self.github_client.register_webhook_handler(
                    GitHubEventType.PUSH, self._handle_github_push
                )
                self.github_client.register_webhook_handler(
                    GitHubEventType.PULL_REQUEST, self._handle_github_pull_request
                )
                self.github_client.register_webhook_handler(
                    GitHubEventType.ISSUES, self._handle_github_issues
                )
                
                # Update health status
                self.integration_health["github"] = IntegrationHealth(
                    name="github",
                    status=IntegrationStatus.CONNECTED,
                    last_check=datetime.now(),
                    success_rate=1.0
                )
                
                logger.info("GitHub integration initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize GitHub integration: {e}")
                self.integration_health["github"] = IntegrationHealth(
                    name="github",
                    status=IntegrationStatus.ERROR,
                    last_check=datetime.now(),
                    error_message=str(e)
                )
        
        # Initialize Slack integration (placeholder)
        if self.config.slack_token or self.config.slack_webhook_url:
            try:
                # TODO: Implement Slack client
                self.integration_health["slack"] = IntegrationHealth(
                    name="slack",
                    status=IntegrationStatus.INITIALIZING,
                    last_check=datetime.now()
                )
                
                logger.info("Slack integration placeholder initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize Slack integration: {e}")
                self.integration_health["slack"] = IntegrationHealth(
                    name="slack",
                    status=IntegrationStatus.ERROR,
                    last_check=datetime.now(),
                    error_message=str(e)
                )
    
    async def _disconnect_integrations(self) -> None:
        """Disconnect all integrations."""
        if self.github_client:
            await self.github_client.disconnect()
            self.github_client = None
        
        # Update health status
        for integration_name in self.integration_health:
            self.integration_health[integration_name].status = IntegrationStatus.DISCONNECTED
    
    async def _auto_sync_loop(self) -> None:
        """Auto-sync loop for periodic synchronization."""
        while self.running:
            try:
                await self._perform_auto_sync()
                self.stats["auto_sync_runs"] += 1
                await asyncio.sleep(self.config.auto_sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-sync loop: {e}")
                await asyncio.sleep(30)  # Short delay on error
    
    async def _health_check_loop(self) -> None:
        """Health check loop for monitoring integrations."""
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)  # Short delay on error
    
    async def _perform_auto_sync(self) -> None:
        """Perform automatic synchronization tasks."""
        # Sync GitHub data
        if self.github_client and self.coordinator:
            try:
                # Sync repository information with coordinator
                await self._sync_github_with_coordinator()
            except Exception as e:
                logger.error(f"Failed to sync GitHub with coordinator: {e}")
                self.stats["integration_failures"] += 1
        
        # Sync with service discovery
        if self.service_discovery:
            try:
                await self._sync_with_service_discovery()
            except Exception as e:
                logger.error(f"Failed to sync with service discovery: {e}")
                self.stats["integration_failures"] += 1
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all integrations."""
        # Check GitHub health
        if self.github_client:
            try:
                start_time = datetime.now()
                health_result = await self.github_client.health_check()
                response_time = (datetime.now() - start_time).total_seconds()
                
                if health_result["status"] == "healthy":
                    self.integration_health["github"].status = IntegrationStatus.CONNECTED
                    self.integration_health["github"].error_message = None
                    self.integration_health["github"].success_rate = min(
                        1.0, self.integration_health["github"].success_rate + 0.1
                    )
                else:
                    self.integration_health["github"].status = IntegrationStatus.ERROR
                    self.integration_health["github"].error_message = health_result.get("error")
                    self.integration_health["github"].success_rate = max(
                        0.0, self.integration_health["github"].success_rate - 0.2
                    )
                
                self.integration_health["github"].last_check = datetime.now()
                self.integration_health["github"].response_time = response_time
                
            except Exception as e:
                logger.error(f"GitHub health check failed: {e}")
                self.integration_health["github"].status = IntegrationStatus.ERROR
                self.integration_health["github"].error_message = str(e)
                self.integration_health["github"].last_check = datetime.now()
                self.integration_health["github"].success_rate = max(
                    0.0, self.integration_health["github"].success_rate - 0.3
                )
        
        # Check Slack health (placeholder)
        if "slack" in self.integration_health:
            # TODO: Implement Slack health check
            self.integration_health["slack"].last_check = datetime.now()
    
    async def _sync_github_with_coordinator(self) -> None:
        """Sync GitHub data with multi-agent coordinator."""
        if not self.github_client or not self.coordinator:
            return
        
        try:
            # Get agent-hive repositories
            repos = await self.github_client.list_repositories()
            
            # Filter for agent-hive related repositories
            agent_repos = [
                repo for repo in repos
                if "agent" in repo["name"].lower() or "hive" in repo["name"].lower()
            ]
            
            # Register repositories as tasks or update coordinator state
            for repo in agent_repos:
                task_data = {
                    "type": "repository_sync",
                    "repository": repo["full_name"],
                    "last_updated": repo["updated_at"],
                    "issues_url": repo["issues_url"],
                    "pulls_url": repo["pulls_url"]
                }
                
                # Create task for repository monitoring
                await self.coordinator.distribute_task(task_data, priority=5)
            
            logger.info(f"Synced {len(agent_repos)} repositories with coordinator")
            
        except Exception as e:
            logger.error(f"Failed to sync GitHub with coordinator: {e}")
            raise
    
    async def _sync_with_service_discovery(self) -> None:
        """Sync external integrations with service discovery."""
        if not self.service_discovery:
            return
        
        # Register GitHub integration as a service
        if self.github_client:
            from .service_discovery import ServiceInfo, ServiceStatus
            
            github_service = ServiceInfo(
                service_id="github-integration",
                service_name="github",
                service_type="external_api",
                host="api.github.com",
                port=443,
                endpoints=["repositories", "issues", "pulls", "webhooks"],
                metadata={"type": "github_api", "version": "v3"},
                tags=["external", "github", "api"],
                status=ServiceStatus.HEALTHY if self.integration_health.get("github", {}).status == IntegrationStatus.CONNECTED else ServiceStatus.UNHEALTHY
            )
            
            await self.service_discovery.register_service(github_service)
    
    # GitHub event handlers
    
    async def _handle_github_push(self, event: Any) -> None:
        """Handle GitHub push events."""
        try:
            payload = event.payload
            repository = payload.get("repository", {})
            commits = payload.get("commits", [])
            
            logger.info(f"GitHub push event: {len(commits)} commits to {repository.get('full_name')}")
            
            # Notify coordinator of new commits
            if self.coordinator:
                task_data = {
                    "type": "github_push",
                    "repository": repository.get("full_name"),
                    "commits": len(commits),
                    "ref": payload.get("ref"),
                    "pusher": payload.get("pusher", {}).get("name")
                }
                
                await self.coordinator.distribute_task(task_data, priority=3)
            
            # Trigger custom event handlers
            await self._trigger_event_handlers("github_push", event)
            
            self.stats["github_events"] += 1
            self.stats["total_events_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error handling GitHub push event: {e}")
            self.stats["integration_failures"] += 1
    
    async def _handle_github_pull_request(self, event: Any) -> None:
        """Handle GitHub pull request events."""
        try:
            payload = event.payload
            action = payload.get("action")
            pull_request = payload.get("pull_request", {})
            
            logger.info(f"GitHub PR event: {action} on PR #{pull_request.get('number')}")
            
            # Notify coordinator of PR events
            if self.coordinator:
                task_data = {
                    "type": "github_pull_request",
                    "action": action,
                    "pr_number": pull_request.get("number"),
                    "title": pull_request.get("title"),
                    "state": pull_request.get("state"),
                    "repository": payload.get("repository", {}).get("full_name")
                }
                
                await self.coordinator.distribute_task(task_data, priority=2)
            
            # Trigger custom event handlers
            await self._trigger_event_handlers("github_pull_request", event)
            
            self.stats["github_events"] += 1
            self.stats["total_events_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error handling GitHub PR event: {e}")
            self.stats["integration_failures"] += 1
    
    async def _handle_github_issues(self, event: Any) -> None:
        """Handle GitHub issues events."""
        try:
            payload = event.payload
            action = payload.get("action")
            issue = payload.get("issue", {})
            
            logger.info(f"GitHub issue event: {action} on issue #{issue.get('number')}")
            
            # Notify coordinator of issue events
            if self.coordinator:
                task_data = {
                    "type": "github_issue",
                    "action": action,
                    "issue_number": issue.get("number"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "repository": payload.get("repository", {}).get("full_name")
                }
                
                await self.coordinator.distribute_task(task_data, priority=4)
            
            # Trigger custom event handlers
            await self._trigger_event_handlers("github_issue", event)
            
            self.stats["github_events"] += 1
            self.stats["total_events_processed"] += 1
            
        except Exception as e:
            logger.error(f"Error handling GitHub issue event: {e}")
            self.stats["integration_failures"] += 1
    
    async def _trigger_event_handlers(self, event_type: str, event_data: Any) -> None:
        """Trigger registered event handlers."""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    # Public API methods
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered event handler for {event_type}")
    
    async def send_notification(self, message: str, channels: Optional[List[str]] = None) -> None:
        """
        Send notification to configured channels.
        
        Args:
            message: Notification message
            channels: Target channels (defaults to configured channels)
        """
        target_channels = channels or self.config.notification_channels or []
        
        for channel in target_channels:
            try:
                if channel.startswith("slack:"):
                    # TODO: Implement Slack notification
                    logger.info(f"Would send Slack notification to {channel}: {message}")
                elif channel.startswith("email:"):
                    # TODO: Implement email notification
                    logger.info(f"Would send email notification to {channel}: {message}")
                else:
                    logger.warning(f"Unknown notification channel: {channel}")
            except Exception as e:
                logger.error(f"Failed to send notification to {channel}: {e}")
    
    async def get_github_repository_info(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """
        Get GitHub repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository information or None if not available
        """
        if not self.github_client:
            return None
        
        try:
            return await self.github_client.get_repository(owner, repo)
        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            return None
    
    async def create_github_issue(self, owner: str, repo: str, title: str, 
                                 body: str, labels: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Create GitHub issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Issue labels
            
        Returns:
            Created issue information or None if failed
        """
        if not self.github_client:
            return None
        
        try:
            return await self.github_client.create_issue(owner, repo, title, body, labels)
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return None
    
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get integration status.
        
        Returns:
            Integration status information
        """
        return {
            "running": self.running,
            "integrations": {
                name: {
                    "status": health.status.value,
                    "last_check": health.last_check.isoformat(),
                    "error_message": health.error_message,
                    "response_time": health.response_time,
                    "success_rate": health.success_rate
                }
                for name, health in self.integration_health.items()
            },
            "event_handlers": {
                event_type: len(handlers)
                for event_type, handlers in self.event_handlers.items()
            },
            "stats": self.stats.copy()
        }
    
    def get_github_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get GitHub client statistics.
        
        Returns:
            GitHub client stats or None if not available
        """
        if not self.github_client:
            return None
        
        return self.github_client.get_client_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform integration manager health check.
        
        Returns:
            Health check result
        """
        healthy_integrations = sum(
            1 for health in self.integration_health.values()
            if health.status == IntegrationStatus.CONNECTED
        )
        
        total_integrations = len(self.integration_health)
        
        return {
            "status": "healthy" if healthy_integrations > 0 else "unhealthy",
            "running": self.running,
            "healthy_integrations": healthy_integrations,
            "total_integrations": total_integrations,
            "integration_health": self.integration_health,
            "stats": self.stats.copy(),
            "timestamp": datetime.now().isoformat()
        }