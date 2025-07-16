"""
Main orchestrator for the Message Queue Communication System.
Provides unified startup and management for all components.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional
import argparse

from .queue_service import MessageQueueService, QueueConfig
from .agent_registry import AgentRegistry
from .message_broker import MessageBroker
from .api_server import CommunicationAPI, create_communication_api
from .monitoring import MetricsCollector
from .migration import MigrationOrchestrator, create_migration_orchestrator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('message_queue.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MessageQueueSystem:
    """Main system orchestrator for the message queue infrastructure."""
    
    def __init__(self,
                 redis_url: str = "redis://localhost:6379",
                 api_host: str = "localhost",
                 api_port: int = 8080,
                 enable_monitoring: bool = True,
                 enable_migration: bool = False):
        
        self.redis_url = redis_url
        self.api_host = api_host
        self.api_port = api_port
        self.enable_monitoring = enable_monitoring
        self.enable_migration = enable_migration
        
        # Core components
        self.queue_service: Optional[MessageQueueService] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.message_broker: Optional[MessageBroker] = None
        self.communication_api: Optional[CommunicationAPI] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.migration_orchestrator: Optional[MigrationOrchestrator] = None
        
        # System state
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start all system components."""
        logger.info("Starting Message Queue System")
        
        try:
            # Initialize core services
            await self._initialize_services()
            
            # Start services in order
            await self._start_services()
            
            # Initialize migration if enabled
            if self.enable_migration:
                await self._initialize_migration()
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            self.is_running = True
            logger.info("Message Queue System started successfully")
            
            # Display system information
            await self._display_system_info()
            
        except Exception as e:
            logger.error(f"Failed to start Message Queue System: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all system components."""
        if not self.is_running:
            return
        
        logger.info("Stopping Message Queue System")
        self.is_running = False
        
        # Stop services in reverse order
        services = [
            ('Migration Orchestrator', self.migration_orchestrator),
            ('Metrics Collector', self.metrics_collector),
            ('Message Broker', self.message_broker),
            ('Queue Service', self.queue_service)
        ]
        
        for service_name, service in services:
            if service and hasattr(service, 'stop'):
                try:
                    await service.stop()
                    logger.info(f"Stopped {service_name}")
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")
        
        # Signal shutdown complete
        self.shutdown_event.set()
        logger.info("Message Queue System stopped")
    
    async def run(self):
        """Run the system until shutdown signal."""
        await self.start()
        
        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.stop()
    
    async def _initialize_services(self):
        """Initialize all services."""
        logger.info("Initializing services")
        
        # Queue Service
        queue_config = QueueConfig(
            name="agent-messages",
            max_size=10000,
            message_ttl=86400,  # 24 hours
            retry_delay=60,
            max_retry_attempts=3,
            enable_persistence=True,
            persistence_backend="redis"
        )
        self.queue_service = MessageQueueService(queue_config, self.redis_url)
        
        # Agent Registry
        self.agent_registry = AgentRegistry([
            "worktrees/",
            "new-worktrees/"
        ])
        
        # Message Broker
        self.message_broker = MessageBroker(
            self.queue_service,
            self.agent_registry
        )
        
        # Communication API
        self.communication_api = CommunicationAPI(
            self.queue_service,
            self.agent_registry,
            self.api_host,
            self.api_port
        )
        
        # Metrics Collector (if enabled)
        if self.enable_monitoring:
            self.metrics_collector = MetricsCollector(
                self.queue_service,
                self.agent_registry,
                self.message_broker,
                retention_hours=24
            )
        
        logger.info("Services initialized")
    
    async def _start_services(self):
        """Start all services in correct order."""
        logger.info("Starting services")
        
        # Start Queue Service
        await self.queue_service.start()
        logger.info("Queue Service started")
        
        # Discover and register agents
        discovered_agents = await self.agent_registry.discover_agents()
        for agent in discovered_agents:
            await self.agent_registry.register_agent(agent)
        logger.info(f"Registered {len(discovered_agents)} agents")
        
        # Start auto-discovery
        asyncio.create_task(self.agent_registry.auto_discovery_loop())
        
        # Start Message Broker
        await self.message_broker.start()
        logger.info("Message Broker started")
        
        # Start Metrics Collection (if enabled)
        if self.metrics_collector:
            await self.metrics_collector.start_collection()
            logger.info("Metrics Collector started")
        
        # Start Communication API (runs indefinitely)
        asyncio.create_task(self.communication_api.start())
        logger.info("Communication API started")
    
    async def _initialize_migration(self):
        """Initialize migration orchestrator if enabled."""
        logger.info("Initializing migration system")
        
        self.migration_orchestrator = MigrationOrchestrator(
            self.queue_service,
            self.agent_registry,
            self.communication_api
        )
        
        logger.info("Migration system ready")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _display_system_info(self):
        """Display system information and status."""
        logger.info("=== MESSAGE QUEUE SYSTEM STATUS ===")
        logger.info(f"Redis URL: {self.redis_url}")
        logger.info(f"API Server: http://{self.api_host}:{self.api_port}")
        logger.info(f"WebSocket: ws://{self.api_host}:{self.api_port}/ws/{{agent_id}}")
        logger.info(f"Monitoring: {'Enabled' if self.enable_monitoring else 'Disabled'}")
        logger.info(f"Migration: {'Enabled' if self.enable_migration else 'Disabled'}")
        
        # Agent status
        if self.agent_registry:
            agents = await self.agent_registry.list_agents()
            online_agents = await self.agent_registry.list_online_agents()
            logger.info(f"Agents: {len(agents)} total, {len(online_agents)} online")
        
        # Queue status
        if self.queue_service:
            stats = await self.queue_service.get_queue_stats()
            logger.info(f"Queue: {stats.queue_size} pending, {stats.delivered_messages} delivered")
        
        logger.info("=================================")
    
    async def get_system_status(self) -> dict:
        """Get comprehensive system status."""
        status = {
            'system': {
                'running': self.is_running,
                'redis_url': self.redis_url,
                'api_endpoint': f"http://{self.api_host}:{self.api_port}",
                'monitoring_enabled': self.enable_monitoring,
                'migration_enabled': self.enable_migration
            }
        }
        
        if self.queue_service:
            status['queue'] = await self.queue_service.get_queue_stats()
        
        if self.agent_registry:
            status['agents'] = await self.agent_registry.get_registry_stats()
        
        if self.message_broker:
            status['broker'] = await self.message_broker.get_broker_stats()
        
        if self.metrics_collector:
            status['metrics'] = await self.metrics_collector.get_metrics_summary()
        
        if self.migration_orchestrator:
            status['migration'] = await self.migration_orchestrator.get_migration_status()
        
        return status


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Message Queue Communication System")
    parser.add_argument("--redis-url", default="redis://localhost:6379",
                       help="Redis connection URL")
    parser.add_argument("--api-host", default="localhost",
                       help="API server host")
    parser.add_argument("--api-port", type=int, default=8080,
                       help="API server port")
    parser.add_argument("--enable-monitoring", action="store_true",
                       help="Enable metrics collection")
    parser.add_argument("--enable-migration", action="store_true",
                       help="Enable migration from tmux")
    parser.add_argument("--migrate-now", action="store_true",
                       help="Start migration immediately")
    parser.add_argument("--status-only", action="store_true",
                       help="Show status and exit")
    
    args = parser.parse_args()
    
    # Create system
    system = MessageQueueSystem(
        redis_url=args.redis_url,
        api_host=args.api_host,
        api_port=args.api_port,
        enable_monitoring=args.enable_monitoring,
        enable_migration=args.enable_migration
    )
    
    if args.status_only:
        # Just show status
        await system.start()
        status = await system.get_system_status()
        print(json.dumps(status, indent=2, default=str))
        await system.stop()
        return
    
    if args.migrate_now:
        # Run migration
        logger.info("Starting immediate migration")
        orchestrator = await create_migration_orchestrator(args.redis_url)
        success = await orchestrator.start_migration()
        
        if success:
            logger.info("Migration completed successfully")
        else:
            logger.error("Migration failed")
            sys.exit(1)
        return
    
    # Run the system
    try:
        await system.run()
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())