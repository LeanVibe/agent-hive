"""
Migration API Endpoints for Zero-Disruption Agent Transition

Provides HTTP API endpoints for managing and monitoring the migration
from tmux-based to message queue-based agent communication.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from .migration_manager import MigrationManager, MigrationConfig, MigrationPhase, AgentMigrationState
from .event_streaming import EventStreaming
from .models import ApiRequest, ApiResponse, EventStreamConfig

logger = logging.getLogger(__name__)


class MigrationAPI:
    """
    REST API interface for migration management.
    
    Provides endpoints for:
    - Starting/stopping migrations
    - Monitoring migration status
    - Agent health checks
    - Manual interventions
    - Rollback operations
    """
    
    def __init__(self, migration_manager: MigrationManager):
        """
        Initialize migration API.
        
        Args:
            migration_manager: Migration manager instance
        """
        self.migration_manager = migration_manager
        self.api_routes = {
            "/api/migration/start": {"POST": self.start_migration},
            "/api/migration/status": {"GET": self.get_migration_status},
            "/api/migration/stop": {"POST": self.stop_migration},
            "/api/migration/rollback": {"POST": self.rollback_migration},
            "/api/migration/agents": {"GET": self.list_agents},
            "/api/migration/agents/{agent_id}": {"GET": self.get_agent_status},
            "/api/migration/agents/{agent_id}/health": {"POST": self.check_agent_health},
            "/api/migration/agents/{agent_id}/migrate": {"POST": self.migrate_single_agent},
            "/api/migration/agents/{agent_id}/rollback": {"POST": self.rollback_single_agent},
            "/api/migration/config": {"GET": self.get_config, "PUT": self.update_config},
            "/api/migration/phases": {"GET": self.get_phases},
            "/api/migration/logs": {"GET": self.get_migration_logs}
        }
        
        # Migration event history
        self.migration_events: List[Dict[str, Any]] = []
        
        # Add phase callbacks for logging
        self._setup_phase_callbacks()
    
    def _setup_phase_callbacks(self):
        """Setup callbacks for migration phases."""
        for phase in MigrationPhase:
            self.migration_manager.add_phase_callback(
                phase, 
                self._log_phase_event
            )
    
    async def _log_phase_event(self, phase: MigrationPhase, agent_statuses: Dict[str, Any]):
        """Log migration phase events."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase.value,
            "agent_count": len(agent_statuses),
            "agents": list(agent_statuses.keys())
        }
        self.migration_events.append(event)
        
        # Keep only last 1000 events
        if len(self.migration_events) > 1000:
            self.migration_events = self.migration_events[-1000:]
    
    async def start_migration(self, request: ApiRequest) -> ApiResponse:
        """
        Start migration process.
        
        Request body:
        {
            "agent_filter": ["agent1", "agent2"],  // optional
            "force": false  // optional
        }
        """
        try:
            data = request.data or {}
            agent_filter = data.get("agent_filter")
            force = data.get("force", False)
            
            # Check if migration is already active
            if self.migration_manager.migration_active and not force:
                return ApiResponse(
                    success=False,
                    message="Migration already in progress",
                    status_code=409
                )
            
            # Start migration
            migration_id = await self.migration_manager.start_migration(agent_filter)
            
            return ApiResponse(
                success=True,
                message="Migration started successfully",
                data={"migration_id": migration_id},
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to start migration: {e}")
            return ApiResponse(
                success=False,
                message=f"Migration start failed: {str(e)}",
                status_code=500
            )
    
    async def get_migration_status(self, request: ApiRequest) -> ApiResponse:
        """Get current migration status."""
        try:
            status = self.migration_manager.get_migration_status()
            
            # Add summary statistics
            total_agents = len(status["agents"])
            if total_agents > 0:
                state_counts = {}
                for agent_data in status["agents"].values():
                    state = agent_data["current_state"]
                    state_counts[state] = state_counts.get(state, 0) + 1
                
                status["summary"] = {
                    "total_agents": total_agents,
                    "state_distribution": state_counts,
                    "completion_percentage": (
                        state_counts.get("message_queue_only", 0) / total_agents * 100
                        if total_agents > 0 else 0
                    )
                }
            
            return ApiResponse(
                success=True,
                data=status,
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return ApiResponse(
                success=False,
                message=f"Status retrieval failed: {str(e)}",
                status_code=500
            )
    
    async def stop_migration(self, request: ApiRequest) -> ApiResponse:
        """Stop current migration."""
        try:
            if not self.migration_manager.migration_active:
                return ApiResponse(
                    success=False,
                    message="No migration in progress",
                    status_code=400
                )
            
            # Force rollback to stop migration
            await self.migration_manager.force_rollback()
            
            return ApiResponse(
                success=True,
                message="Migration stopped and rolled back",
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to stop migration: {e}")
            return ApiResponse(
                success=False,
                message=f"Migration stop failed: {str(e)}",
                status_code=500
            )
    
    async def rollback_migration(self, request: ApiRequest) -> ApiResponse:
        """
        Rollback migration.
        
        Request body:
        {
            "agent_id": "specific_agent"  // optional, rollback specific agent
        }
        """
        try:
            data = request.data or {}
            agent_id = data.get("agent_id")
            
            await self.migration_manager.force_rollback(agent_id)
            
            message = f"Rollback completed for agent {agent_id}" if agent_id else "Full rollback completed"
            
            return ApiResponse(
                success=True,
                message=message,
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            return ApiResponse(
                success=False,
                message=f"Rollback failed: {str(e)}",
                status_code=500
            )
    
    async def list_agents(self, request: ApiRequest) -> ApiResponse:
        """List all agents in migration."""
        try:
            status = self.migration_manager.get_migration_status()
            agents = status.get("agents", {})
            
            agent_list = []
            for agent_id, agent_data in agents.items():
                agent_list.append({
                    "agent_id": agent_id,
                    "current_state": agent_data["current_state"],
                    "migration_phase": agent_data["migration_phase"],
                    "error_count": agent_data["error_count"],
                    "last_activity": {
                        "tmux": agent_data.get("last_tmux_activity"),
                        "queue": agent_data.get("last_queue_activity")
                    }
                })
            
            return ApiResponse(
                success=True,
                data={"agents": agent_list},
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return ApiResponse(
                success=False,
                message=f"Agent listing failed: {str(e)}",
                status_code=500
            )
    
    async def get_agent_status(self, request: ApiRequest) -> ApiResponse:
        """Get status for a specific agent."""
        try:
            agent_id = request.path_params.get("agent_id")
            if not agent_id:
                return ApiResponse(
                    success=False,
                    message="Agent ID required",
                    status_code=400
                )
            
            status = self.migration_manager.get_migration_status()
            agents = status.get("agents", {})
            
            if agent_id not in agents:
                return ApiResponse(
                    success=False,
                    message=f"Agent {agent_id} not found",
                    status_code=404
                )
            
            agent_status = agents[agent_id]
            
            # Add detailed validation results if available
            if agent_id in self.migration_manager.agent_statuses:
                agent_obj = self.migration_manager.agent_statuses[agent_id]
                agent_status["validation_results"] = agent_obj.validation_results
                agent_status["rollback_data"] = agent_obj.rollback_data
            
            return ApiResponse(
                success=True,
                data={"agent": agent_status},
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
            return ApiResponse(
                success=False,
                message=f"Agent status retrieval failed: {str(e)}",
                status_code=500
            )
    
    async def check_agent_health(self, request: ApiRequest) -> ApiResponse:
        """
        Check health of a specific agent.
        
        Request body:
        {
            "check_tmux": true,  // optional
            "check_queue": true  // optional
        }
        """
        try:
            agent_id = request.path_params.get("agent_id")
            if not agent_id:
                return ApiResponse(
                    success=False,
                    message="Agent ID required",
                    status_code=400
                )
            
            data = request.data or {}
            check_tmux = data.get("check_tmux", True)
            check_queue = data.get("check_queue", True)
            
            health_results = {}
            
            # Check tmux communication
            if check_tmux:
                tmux_health = await self.migration_manager._test_tmux_communication(agent_id)
                health_results["tmux"] = {
                    "healthy": tmux_health,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Check message queue communication
            if check_queue:
                queue_health = await self.migration_manager._test_message_queue_communication(agent_id)
                health_results["message_queue"] = {
                    "healthy": queue_health,
                    "timestamp": datetime.now().isoformat()
                }
            
            overall_health = all(
                result["healthy"] for result in health_results.values()
            )
            
            return ApiResponse(
                success=True,
                data={
                    "agent_id": agent_id,
                    "overall_health": overall_health,
                    "details": health_results
                },
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to check agent health: {e}")
            return ApiResponse(
                success=False,
                message=f"Health check failed: {str(e)}",
                status_code=500
            )
    
    async def migrate_single_agent(self, request: ApiRequest) -> ApiResponse:
        """Migrate a single agent."""
        try:
            agent_id = request.path_params.get("agent_id")
            if not agent_id:
                return ApiResponse(
                    success=False,
                    message="Agent ID required",
                    status_code=400
                )
            
            # Start migration for single agent
            migration_id = await self.migration_manager.start_migration([agent_id])
            
            return ApiResponse(
                success=True,
                message=f"Migration started for agent {agent_id}",
                data={"migration_id": migration_id},
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to migrate single agent: {e}")
            return ApiResponse(
                success=False,
                message=f"Single agent migration failed: {str(e)}",
                status_code=500
            )
    
    async def rollback_single_agent(self, request: ApiRequest) -> ApiResponse:
        """Rollback a single agent."""
        try:
            agent_id = request.path_params.get("agent_id")
            if not agent_id:
                return ApiResponse(
                    success=False,
                    message="Agent ID required",
                    status_code=400
                )
            
            await self.migration_manager.force_rollback(agent_id)
            
            return ApiResponse(
                success=True,
                message=f"Rollback completed for agent {agent_id}",
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to rollback single agent: {e}")
            return ApiResponse(
                success=False,
                message=f"Single agent rollback failed: {str(e)}",
                status_code=500
            )
    
    async def get_config(self, request: ApiRequest) -> ApiResponse:
        """Get current migration configuration."""
        try:
            config_dict = {
                "detection_timeout": self.migration_manager.config.detection_timeout,
                "dual_mode_duration": self.migration_manager.config.dual_mode_duration,
                "validation_timeout": self.migration_manager.config.validation_timeout,
                "max_error_count": self.migration_manager.config.max_error_count,
                "min_dual_mode_success_rate": self.migration_manager.config.min_dual_mode_success_rate,
                "validation_interval": self.migration_manager.config.validation_interval,
                "health_check_interval": self.migration_manager.config.health_check_interval,
                "auto_rollback_enabled": self.migration_manager.config.auto_rollback_enabled,
                "rollback_on_failure_rate": self.migration_manager.config.rollback_on_failure_rate,
                "tmux_session_name": self.migration_manager.config.tmux_session_name,
                "message_queue_base_url": self.migration_manager.config.message_queue_base_url
            }
            
            return ApiResponse(
                success=True,
                data={"config": config_dict},
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return ApiResponse(
                success=False,
                message=f"Config retrieval failed: {str(e)}",
                status_code=500
            )
    
    async def update_config(self, request: ApiRequest) -> ApiResponse:
        """Update migration configuration."""
        try:
            if self.migration_manager.migration_active:
                return ApiResponse(
                    success=False,
                    message="Cannot update config during active migration",
                    status_code=409
                )
            
            data = request.data or {}
            config = self.migration_manager.config
            
            # Update configuration values
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            return ApiResponse(
                success=True,
                message="Configuration updated successfully",
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return ApiResponse(
                success=False,
                message=f"Config update failed: {str(e)}",
                status_code=500
            )
    
    async def get_phases(self, request: ApiRequest) -> ApiResponse:
        """Get information about migration phases."""
        try:
            phases = []
            for phase in MigrationPhase:
                phases.append({
                    "name": phase.value,
                    "description": self._get_phase_description(phase)
                })
            
            return ApiResponse(
                success=True,
                data={"phases": phases},
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to get phases: {e}")
            return ApiResponse(
                success=False,
                message=f"Phase retrieval failed: {str(e)}",
                status_code=500
            )
    
    def _get_phase_description(self, phase: MigrationPhase) -> str:
        """Get description for a migration phase."""
        descriptions = {
            MigrationPhase.DETECTION: "Detect active tmux agents",
            MigrationPhase.PREPARATION: "Prepare message queue infrastructure",
            MigrationPhase.DUAL_MODE_ACTIVATION: "Activate dual-mode operation",
            MigrationPhase.VALIDATION: "Validate dual-mode functionality",
            MigrationPhase.CUTOVER: "Switch to message queue only",
            MigrationPhase.CLEANUP: "Clean up tmux infrastructure",
            MigrationPhase.ROLLBACK: "Rollback to tmux-only mode"
        }
        return descriptions.get(phase, "Unknown phase")
    
    async def get_migration_logs(self, request: ApiRequest) -> ApiResponse:
        """Get migration event logs."""
        try:
            # Parse query parameters
            limit = int(request.query_params.get("limit", 100))
            offset = int(request.query_params.get("offset", 0))
            
            # Apply pagination
            total_events = len(self.migration_events)
            events = self.migration_events[offset:offset + limit]
            
            return ApiResponse(
                success=True,
                data={
                    "events": events,
                    "pagination": {
                        "total": total_events,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + limit < total_events
                    }
                },
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"Failed to get migration logs: {e}")
            return ApiResponse(
                success=False,
                message=f"Log retrieval failed: {str(e)}",
                status_code=500
            )
    
    def get_routes(self) -> Dict[str, Dict[str, Any]]:
        """Get all API routes for registration with API Gateway."""
        return self.api_routes