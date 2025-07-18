#!/usr/bin/env python3
"""
Dashboard Coordinator Integration

Integrates the enhanced dashboard with the multi-agent coordinator
to provide unified agent management and monitoring capabilities.
"""

import asyncio
import logging
from typing import Dict, Any
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from advanced_orchestration.multi_agent_coordinator import MultiAgentCoordinator
from advanced_orchestration.models import CoordinatorConfig, ResourceLimits
from dashboard.enhanced_server import EnhancedDashboardServer
from dashboard.prompt_logger import prompt_logger

logger = logging.getLogger(__name__)

class DashboardCoordinatorIntegration:
    """Integration layer between dashboard and multi-agent coordinator"""

    def __init__(self, session_name: str = "agent-hive"):
        self.session_name = session_name
        self.base_dir = Path(".")

        # Initialize coordinator with default config
        self.coordinator_config = CoordinatorConfig(
            max_agents=10,
            task_timeout=300.0,  # 5 minutes
            health_check_interval=30.0,
            resource_limits=ResourceLimits(
                max_cpu_cores=8,
                max_memory_mb=8192,
                max_disk_mb=10240,
                max_network_mbps=1000,
                max_agents=10
            )
        )

        self.coordinator = MultiAgentCoordinator(self.coordinator_config)
        self.dashboard_server = EnhancedDashboardServer(session_name, str(self.base_dir))

        # Integration state
        self.coordinator_running = False
        self.dashboard_running = False

    async def start_integration(self):
        """Start the integrated dashboard and coordinator"""
        try:
            logger.info("Starting dashboard-coordinator integration...")

            # Start coordinator
            await self.coordinator.start()
            self.coordinator_running = True
            logger.info("✅ Multi-agent coordinator started")

            # Discover and register existing agents
            await self._discover_and_register_agents()

            # Add coordinator endpoints to dashboard
            self._add_coordinator_endpoints()

            # Start dashboard server
            self.dashboard_running = True
            logger.info("✅ Dashboard integration complete")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start integration: {e}")
            return False

    async def stop_integration(self):
        """Stop the integrated system"""
        try:
            if self.coordinator_running:
                await self.coordinator.stop()
                self.coordinator_running = False

            self.dashboard_running = False
            logger.info("✅ Dashboard-coordinator integration stopped")

        except Exception as e:
            logger.error(f"❌ Error stopping integration: {e}")

    async def _discover_and_register_agents(self):
        """Discover existing agents and register them with coordinator"""
        try:
            # Get agents from dashboard server
            agents = await self.dashboard_server._discover_agents()

            for agent_name, agent_info in agents.items():
                try:
                    # Register agent with coordinator
                    registration = await self.coordinator.register_agent(
                        agent_name,
                        {
                            'path': agent_info.path,
                            'window_name': agent_info.window_name,
                            'capabilities': ['general'],
                            'max_concurrent_tasks': 3
                        }
                    )

                    logger.info(f"✅ Registered agent: {agent_name}")

                    # Log to dashboard
                    prompt_logger.log_prompt(
                        "coordinator-integration",
                        f"Registered agent {agent_name} with coordinator",
                        "Agent registration successful",
                        True
                    )

                except Exception as e:
                    logger.warning(f"⚠️ Failed to register agent {agent_name}: {e}")

        except Exception as e:
            logger.error(f"❌ Error discovering agents: {e}")

    def _add_coordinator_endpoints(self):
        """Add coordinator-specific endpoints to dashboard"""
        app = self.dashboard_server.app

        @app.get("/api/coordinator/agents")
        async def get_coordinator_agents():
            """Get agents from coordinator"""
            if not self.coordinator_running:
                return {"agents": [], "error": "Coordinator not running"}

            try:
                agents = await self.coordinator.get_agents()
                return {"agents": [agent.to_dict() for agent in agents]}
            except Exception as e:
                return {"agents": [], "error": str(e)}

        @app.get("/api/coordinator/tasks")
        async def get_coordinator_tasks():
            """Get tasks from coordinator"""
            if not self.coordinator_running:
                return {"tasks": [], "error": "Coordinator not running"}

            try:
                tasks = await self.coordinator.get_tasks()
                return {"tasks": [task.to_dict() for task in tasks]}
            except Exception as e:
                return {"tasks": [], "error": str(e)}

        @app.post("/api/coordinator/tasks/assign")
        async def assign_task(task_data: dict):
            """Assign a task through coordinator"""
            if not self.coordinator_running:
                return {"success": False, "error": "Coordinator not running"}

            try:
                task_id = await self.coordinator.assign_task(
                    task_data.get('description', ''),
                    task_data.get('agent_preferences', []),
                    task_data.get('priority', 'medium'),
                    task_data.get('timeout', 300)
                )

                return {"success": True, "task_id": task_id}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @app.get("/api/coordinator/health")
        async def get_coordinator_health():
            """Get coordinator health status"""
            if not self.coordinator_running:
                return {"healthy": False, "error": "Coordinator not running"}

            try:
                health = await self.coordinator.get_health_status()
                return {"healthy": True, "health": health}
            except Exception as e:
                return {"healthy": False, "error": str(e)}

        @app.post("/api/coordinator/scale")
        async def scale_agents(scale_data: dict):
            """Scale agents through coordinator"""
            if not self.coordinator_running:
                return {"success": False, "error": "Coordinator not running"}

            try:
                action = scale_data.get('action', 'scale_up')
                count = scale_data.get('count', 1)

                if action == 'scale_up':
                    result = await self.coordinator.scale_up(count)
                elif action == 'scale_down':
                    result = await self.coordinator.scale_down(count)
                else:
                    return {"success": False, "error": "Invalid scale action"}

                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        logger.info("✅ Added coordinator endpoints to dashboard")

    async def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status"""
        return {
            "coordinator_running": self.coordinator_running,
            "dashboard_running": self.dashboard_running,
            "registered_agents": len(self.coordinator.agents) if self.coordinator_running else 0,
            "pending_tasks": len(self.coordinator.pending_tasks) if self.coordinator_running else 0,
            "assigned_tasks": len(self.coordinator.assigned_tasks) if self.coordinator_running else 0
        }

async def main():
    """Main function to run the integrated system"""
    integration = DashboardCoordinatorIntegration()

    try:
        # Start integration
        if await integration.start_integration():
            logger.info("🚀 Dashboard-Coordinator Integration started successfully")
            logger.info("📊 Dashboard available at: http://localhost:8002")

            # Run dashboard server
            import uvicorn
            uvicorn.run(
                integration.dashboard_server.app,
                host="0.0.0.0",
                port=8002,
                log_level="info"
            )
        else:
            logger.error("❌ Failed to start integration")

    except KeyboardInterrupt:
        logger.info("🛑 Shutting down integration...")
        await integration.stop_integration()
    except Exception as e:
        logger.error(f"❌ Integration error: {e}")
        await integration.stop_integration()

if __name__ == "__main__":
    asyncio.run(main())
