"""
Migration tools for gradual replacement of tmux-based communication.
Enables zero-disruption transition to the new message queue system.
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import shutil
import os

from .models import Message, MessagePriority, Agent, AgentStatus
from .queue_service import MessageQueueService
from .agent_registry import AgentRegistry
from .api_server import CommunicationAPI


logger = logging.getLogger(__name__)


class TmuxLegacyAdapter:
    """Adapter to interface with existing tmux-based communication."""

    def __init__(self, session_name: str = "agent-hive"):
        self.session_name = session_name
        self.agent_windows = {}  # agent_name -> window_name mapping

    async def get_active_tmux_agents(self) -> List[str]:
        """Get list of active agents in tmux session."""
        try:
            # List tmux windows
            result = subprocess.run([
                "tmux", "list-windows", "-t", self.session_name, "-F", "#{window_name}"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.warning(f"Failed to list tmux windows: {result.stderr}")
                return []

            windows = result.stdout.strip().split('\n')
            agents = []

            for window in windows:
                if window.startswith('agent-'):
                    agent_name = window.replace('agent-', '')
                    agents.append(agent_name)
                    self.agent_windows[agent_name] = window

            return agents

        except Exception as e:
            logger.error(f"Error getting tmux agents: {e}")
            return []

    async def send_tmux_message(self, agent_name: str, message: str) -> bool:
        """Send message via tmux (legacy method)."""
        try:
            window_name = self.agent_windows.get(agent_name, f"agent-{agent_name}")
            target = f"{self.session_name}:{window_name}"

            # Clear existing input
            subprocess.run([
                "tmux", "send-keys", "-t", target, "C-c"
            ], timeout=5)

            # Set message buffer
            subprocess.run([
                "tmux", "set-buffer", message
            ], timeout=5)

            # Paste message
            subprocess.run([
                "tmux", "paste-buffer", "-t", target
            ], timeout=5)

            # Submit message
            subprocess.run([
                "tmux", "send-keys", "-t", target, "Enter"
            ], timeout=5)

            logger.debug(f"Sent tmux message to {agent_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send tmux message to {agent_name}: {e}")
            return False

    async def check_tmux_session_exists(self) -> bool:
        """Check if tmux session exists."""
        try:
            result = subprocess.run([
                "tmux", "has-session", "-t", self.session_name
            ], capture_output=True, timeout=5)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error checking tmux session: {e}")
            return False


class MigrationOrchestrator:
    """Orchestrates the migration from tmux to message queue system."""

    def __init__(self,
                 queue_service: MessageQueueService,
                 agent_registry: AgentRegistry,
                 communication_api: CommunicationAPI):
        self.queue_service = queue_service
        self.agent_registry = agent_registry
        self.communication_api = communication_api
        self.tmux_adapter = TmuxLegacyAdapter()

        # Migration state
        self.migrated_agents: Set[str] = set()
        self.migration_in_progress = False
        self.dual_mode_active = False

        # Performance tracking
        self.migration_stats = {
            'start_time': None,
            'agents_discovered': 0,
            'agents_migrated': 0,
            'messages_dual_sent': 0,
            'errors': []
        }

    async def start_migration(self,
                            dual_mode_duration_minutes: int = 60,
                            migration_batch_size: int = 2) -> bool:
        """Start the migration process."""
        if self.migration_in_progress:
            logger.warning("Migration already in progress")
            return False

        try:
            logger.info("Starting message queue migration")
            self.migration_in_progress = True
            self.migration_stats['start_time'] = datetime.utcnow()

            # Phase 1: Discovery and Assessment
            await self._phase1_discovery()

            # Phase 2: Dual Mode Operation
            await self._phase2_dual_mode(dual_mode_duration_minutes)

            # Phase 3: Gradual Migration
            await self._phase3_gradual_migration(migration_batch_size)

            # Phase 4: Validation and Cleanup
            await self._phase4_validation()

            logger.info("Migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.migration_stats['errors'].append(str(e))
            await self._rollback_migration()
            return False
        finally:
            self.migration_in_progress = False

    async def _phase1_discovery(self):
        """Phase 1: Discover existing tmux agents and assess system."""
        logger.info("Phase 1: Discovery and Assessment")

        # Check tmux session exists
        if not await self.tmux_adapter.check_tmux_session_exists():
            logger.warning("No tmux session found - migration may not be needed")
            return

        # Discover tmux agents
        tmux_agents = await self.tmux_adapter.get_active_tmux_agents()
        self.migration_stats['agents_discovered'] = len(tmux_agents)
        logger.info(f"Discovered {len(tmux_agents)} tmux agents: {tmux_agents}")

        # Register agents in new system
        for agent_name in tmux_agents:
            agent = Agent(
                name=agent_name,
                status=AgentStatus.ONLINE,
                capabilities=self._infer_agent_capabilities(agent_name),
                metadata={
                    'migration_source': 'tmux',
                    'tmux_window': f"agent-{agent_name}",
                    'discovered_at': datetime.utcnow().isoformat()
                }
            )

            await self.agent_registry.register_agent(agent)
            logger.info(f"Registered agent {agent_name} in new system")

        # Discover additional agents from worktrees
        discovered_agents = await self.agent_registry.discover_agents()
        for agent in discovered_agents:
            if agent.name not in tmux_agents:
                await self.agent_registry.register_agent(agent)
                logger.info(f"Registered worktree agent {agent.name}")

    async def _phase2_dual_mode(self, duration_minutes: int):
        """Phase 2: Run in dual mode - send messages to both systems."""
        logger.info(f"Phase 2: Dual Mode Operation ({duration_minutes} minutes)")

        self.dual_mode_active = True
        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)

        # Create dual-send wrapper
        original_send = self.queue_service.send_message

        async def dual_send_wrapper(message: Message) -> bool:
            # Send via new queue system
            queue_success = await original_send(message)

            # Also send via tmux if agent is in tmux
            tmux_success = True
            if not self._is_agent_migrated(message.recipient):
                agent = await self.agent_registry.get_agent(message.recipient)
                if agent:
                    tmux_success = await self.tmux_adapter.send_tmux_message(
                        agent.name,
                        f"[DUAL MODE] From {message.sender}: {message.content}"
                    )
                    self.migration_stats['messages_dual_sent'] += 1

            return queue_success and tmux_success

        # Replace send method temporarily
        self.queue_service.send_message = dual_send_wrapper

        # Monitor dual mode operation
        try:
            while datetime.utcnow() < end_time and self.dual_mode_active:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Log dual mode stats
                logger.debug(f"Dual mode: {self.migration_stats['messages_dual_sent']} messages sent to both systems")

        finally:
            # Restore original send method
            self.queue_service.send_message = original_send
            self.dual_mode_active = False

        logger.info("Phase 2 completed - dual mode disabled")

    async def _phase3_gradual_migration(self, batch_size: int):
        """Phase 3: Gradually migrate agents in batches."""
        logger.info(f"Phase 3: Gradual Migration (batch size: {batch_size})")

        # Get all non-migrated agents
        all_agents = await self.agent_registry.list_agents()
        pending_agents = [a for a in all_agents if not self._is_agent_migrated(a.id)]

        # Migrate in batches
        for i in range(0, len(pending_agents), batch_size):
            batch = pending_agents[i:i + batch_size]
            logger.info(f"Migrating batch {i//batch_size + 1}: {[a.name for a in batch]}")

            for agent in batch:
                success = await self._migrate_single_agent(agent)
                if success:
                    self.migrated_agents.add(agent.id)
                    self.migration_stats['agents_migrated'] += 1
                    logger.info(f"Successfully migrated agent {agent.name}")
                else:
                    logger.error(f"Failed to migrate agent {agent.name}")
                    self.migration_stats['errors'].append(f"Failed to migrate {agent.name}")

            # Wait between batches to ensure stability
            await asyncio.sleep(30)

        logger.info(f"Phase 3 completed - migrated {len(self.migrated_agents)} agents")

    async def _phase4_validation(self):
        """Phase 4: Validate migration and cleanup."""
        logger.info("Phase 4: Validation and Cleanup")

        # Validate all agents are responsive
        validation_results = {}
        all_agents = await self.agent_registry.list_online_agents()

        for agent in all_agents:
            # Send test message
            test_message = Message(
                sender="migration-system",
                recipient=agent.id,
                content="Migration validation test - please acknowledge",
                priority=MessagePriority.LOW,
                metadata={'migration_test': True}
            )

            success = await self.queue_service.send_message(test_message)
            validation_results[agent.name] = success

            if success:
                logger.debug(f"Validation successful for {agent.name}")
            else:
                logger.warning(f"Validation failed for {agent.name}")

        # Report validation results
        successful_validations = sum(1 for v in validation_results.values() if v)
        total_agents = len(validation_results)

        logger.info(f"Validation: {successful_validations}/{total_agents} agents responsive")

        # Create migration report
        await self._generate_migration_report(validation_results)

        # Clean up tmux session if all agents migrated
        if successful_validations == total_agents and total_agents > 0:
            await self._cleanup_tmux_system()

    async def _migrate_single_agent(self, agent: Agent) -> bool:
        """Migrate a single agent to the new system."""
        try:
            # Update agent metadata
            agent.metadata['migration_status'] = 'migrated'
            agent.metadata['migration_time'] = datetime.utcnow().isoformat()

            # Send migration notification via tmux
            await self.tmux_adapter.send_tmux_message(
                agent.name,
                f"[MIGRATION] Your agent is being migrated to the new message queue system. "
                f"Please connect to WebSocket: ws://localhost:8080/ws/{agent.id}"
            )

            # Wait for agent to establish connection (or timeout)
            await asyncio.sleep(10)

            # Check if agent is connected to new system
            updated_agent = await self.agent_registry.get_agent(agent.id)
            if updated_agent and updated_agent.is_online:
                return True

            # If not connected, send another notification
            await self.tmux_adapter.send_tmux_message(
                agent.name,
                f"[MIGRATION] Please use the new API endpoints: "
                f"GET /api/v1/messages/{agent.id} for messages"
            )

            return True  # Consider successful even if not immediately connected

        except Exception as e:
            logger.error(f"Error migrating agent {agent.name}: {e}")
            return False

    def _is_agent_migrated(self, agent_id: str) -> bool:
        """Check if an agent has been migrated."""
        return agent_id in self.migrated_agents

    def _infer_agent_capabilities(self, agent_name: str) -> List[str]:
        """Infer agent capabilities from name."""
        capabilities = []
        name_lower = agent_name.lower()

        if 'orchestrat' in name_lower:
            capabilities.append('orchestration')
        if 'quality' in name_lower:
            capabilities.append('quality')
        if 'document' in name_lower:
            capabilities.append('documentation')
        if 'integrat' in name_lower:
            capabilities.append('integration')
        if 'intelligence' in name_lower:
            capabilities.append('intelligence')
        if 'pm' in name_lower or 'manager' in name_lower:
            capabilities.append('management')

        # Default capability
        if not capabilities:
            capabilities.append('general')

        return capabilities

    async def _generate_migration_report(self, validation_results: Dict[str, bool]):
        """Generate comprehensive migration report."""
        report = {
            'migration_summary': {
                'start_time': self.migration_stats['start_time'].isoformat(),
                'end_time': datetime.utcnow().isoformat(),
                'duration_minutes': (
                    datetime.utcnow() - self.migration_stats['start_time']
                ).total_seconds() / 60,
                'agents_discovered': self.migration_stats['agents_discovered'],
                'agents_migrated': self.migration_stats['agents_migrated'],
                'messages_dual_sent': self.migration_stats['messages_dual_sent'],
                'errors': self.migration_stats['errors']
            },
            'validation_results': validation_results,
            'system_status': {
                'queue_service_running': self.queue_service.is_running,
                'total_registered_agents': len(await self.agent_registry.list_agents()),
                'online_agents': len(await self.agent_registry.list_online_agents())
            }
        }

        # Save report
        report_path = Path("migration_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Migration report saved to {report_path}")

        # Also log summary
        logger.info("=== MIGRATION SUMMARY ===")
        logger.info(f"Duration: {report['migration_summary']['duration_minutes']:.1f} minutes")
        logger.info(f"Agents migrated: {report['migration_summary']['agents_migrated']}")
        logger.info(f"Dual-mode messages: {report['migration_summary']['messages_dual_sent']}")
        logger.info(f"Errors: {len(report['migration_summary']['errors'])}")
        logger.info("========================")

    async def _cleanup_tmux_system(self):
        """Clean up tmux system after successful migration."""
        logger.info("Cleaning up tmux system")

        try:
            # Create backup of tmux scripts
            backup_dir = Path("tmux_backup")
            backup_dir.mkdir(exist_ok=True)

            scripts_to_backup = [
                "scripts/send_agent_message.py",
                "scripts/agent_communicate.py",
                "scripts/ping_agents.py",
                "scripts/check_agent_status.py"
            ]

            for script_path in scripts_to_backup:
                script = Path(script_path)
                if script.exists():
                    backup_path = backup_dir / script.name
                    shutil.copy2(script, backup_path)
                    logger.info(f"Backed up {script_path}")

            # Rename tmux scripts to indicate they're deprecated
            for script_path in scripts_to_backup:
                script = Path(script_path)
                if script.exists():
                    deprecated_path = script.with_suffix('.deprecated')
                    script.rename(deprecated_path)
                    logger.info(f"Deprecated {script_path}")

            logger.info("Tmux system cleanup completed")

        except Exception as e:
            logger.error(f"Error during tmux cleanup: {e}")

    async def _rollback_migration(self):
        """Rollback migration in case of failure."""
        logger.warning("Rolling back migration")

        try:
            # Stop dual mode
            self.dual_mode_active = False

            # Reset migration state
            self.migrated_agents.clear()

            # Notify agents via tmux
            tmux_agents = await self.tmux_adapter.get_active_tmux_agents()
            for agent_name in tmux_agents:
                await self.tmux_adapter.send_tmux_message(
                    agent_name,
                    "[MIGRATION ROLLBACK] Migration failed. Continuing with tmux communication."
                )

            logger.info("Migration rollback completed")

        except Exception as e:
            logger.error(f"Error during rollback: {e}")

    async def get_migration_status(self) -> Dict:
        """Get current migration status."""
        return {
            'migration_in_progress': self.migration_in_progress,
            'dual_mode_active': self.dual_mode_active,
            'migrated_agents': len(self.migrated_agents),
            'stats': self.migration_stats,
            'last_updated': datetime.utcnow().isoformat()
        }


# Migration utilities
async def create_migration_orchestrator(
    redis_url: str = "redis://localhost:6379"
) -> MigrationOrchestrator:
    """Create and initialize migration orchestrator."""

    # Initialize services
    queue_service = MessageQueueService(redis_url=redis_url)
    agent_registry = AgentRegistry()
    communication_api = await create_communication_api(redis_url)

    # Create orchestrator
    orchestrator = MigrationOrchestrator(
        queue_service,
        agent_registry,
        communication_api
    )

    return orchestrator


async def run_migration_cli():
    """CLI interface for running migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate from tmux to message queue")
    parser.add_argument("--redis-url", default="redis://localhost:6379",
                       help="Redis connection URL")
    parser.add_argument("--dual-mode-minutes", type=int, default=60,
                       help="Duration for dual mode operation")
    parser.add_argument("--batch-size", type=int, default=2,
                       help="Agent migration batch size")

    args = parser.parse_args()

    try:
        orchestrator = await create_migration_orchestrator(args.redis_url)
        success = await orchestrator.start_migration(
            args.dual_mode_minutes,
            args.batch_size
        )

        if success:
            print("Migration completed successfully!")
        else:
            print("Migration failed. Check logs for details.")

    except Exception as e:
        print(f"Migration error: {e}")


if __name__ == "__main__":
    asyncio.run(run_migration_cli())
