"""
Rollback Manager for Foundation Epic

Provides comprehensive rollback capabilities for migration failures.
Ensures safe recovery to previous stable state with data preservation.
"""

import asyncio
import json
import logging
import subprocess
import time
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SafetyCheckpoint:
    """Safety checkpoint for rollback operations."""
    checkpoint_id: str
    timestamp: datetime
    agent_states: Dict[str, Any]
    migration_phase: str
    bridge_config: Dict[str, Any]
    system_state: Dict[str, Any] = None
    rollback_instructions: List[str] = None

    def __post_init__(self):
        if self.system_state is None:
            self.system_state = {}
        if self.rollback_instructions is None:
            self.rollback_instructions = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_states": self.agent_states,
            "migration_phase": self.migration_phase,
            "bridge_config": self.bridge_config,
            "system_state": self.system_state,
            "rollback_instructions": self.rollback_instructions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SafetyCheckpoint':
        """Create checkpoint from dictionary."""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            agent_states=data["agent_states"],
            migration_phase=data["migration_phase"],
            bridge_config=data["bridge_config"],
            system_state=data.get("system_state", {}),
            rollback_instructions=data.get("rollback_instructions", [])
        )


class RollbackManager:
    """
    Comprehensive rollback manager for migration failures.

    Provides automated rollback capabilities with safety checkpoints,
    state preservation, and recovery validation.
    """

    def __init__(self, bridge):
        """
        Initialize rollback manager.

        Args:
            bridge: TmuxMessageBridge instance
        """
        self.bridge = bridge
        self.checkpoints: Dict[str, SafetyCheckpoint] = {}
        self.rollback_history: List[Dict[str, Any]] = []

        # Rollback configuration
        self.config = {
            "max_rollback_time": 300,  # 5 minutes
            "backup_directory": Path(".claude/migration_backups"),
            "max_checkpoints": 10,
            "validation_timeout": 60
        }

        # Ensure backup directory exists
        self.config["backup_directory"].mkdir(parents=True, exist_ok=True)

        logger.info("RollbackManager initialized")

    async def start(self) -> None:
        """Start rollback manager."""
        logger.info("RollbackManager started")

    async def stop(self) -> None:
        """Stop rollback manager."""
        logger.info("RollbackManager stopped")

    async def create_checkpoint(self, checkpoint_id: str, migration_phase: str = "unknown") -> bool:
        """
        Create safety checkpoint for rollback.

        Args:
            checkpoint_id: Unique identifier for checkpoint
            migration_phase: Current migration phase

        Returns:
            True if checkpoint created successfully
        """
        logger.info(f"💾 Creating safety checkpoint: {checkpoint_id}")

        try:
            # Capture current agent states
            agent_states = await self._capture_agent_states()

            # Capture bridge configuration
            bridge_config = await self._capture_bridge_config()

            # Capture system state
            system_state = await self._capture_system_state()

            # Create checkpoint
            checkpoint = SafetyCheckpoint(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.now(),
                agent_states=agent_states,
                migration_phase=migration_phase,
                bridge_config=bridge_config,
                system_state=system_state,
                rollback_instructions=self._generate_rollback_instructions(agent_states)
            )

            # Store checkpoint
            self.checkpoints[checkpoint_id] = checkpoint

            # Save to disk
            await self._save_checkpoint_to_disk(checkpoint)

            # Cleanup old checkpoints
            await self._cleanup_old_checkpoints()

            logger.info(f"✅ Checkpoint {checkpoint_id} created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create checkpoint {checkpoint_id}: {e}")
            return False

    async def execute_rollback(self, checkpoint_id: Optional[str] = None,
                             reason: str = "Manual rollback",
                             rollback_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute rollback to a specific checkpoint or latest stable state.

        Args:
            checkpoint_id: Specific checkpoint to rollback to (None for latest)
            reason: Reason for rollback
            rollback_plan: Optional rollback plan from migration manager

        Returns:
            Rollback execution results
        """
        logger.warning(f"🔄 Executing rollback: {reason}")

        start_time = datetime.now()

        result = {
            "status": "in_progress",
            "start_time": start_time,
            "checkpoint_id": checkpoint_id,
            "reason": reason,
            "steps_completed": [],
            "errors": [],
            "agent_results": {},
            "validation_results": {}
        }

        try:
            # Determine target checkpoint
            target_checkpoint = await self._select_rollback_checkpoint(checkpoint_id)
            if not target_checkpoint:
                result["status"] = "failed"
                result["errors"].append("No suitable checkpoint found for rollback")
                return result

            result["checkpoint_id"] = target_checkpoint.checkpoint_id
            logger.info(f"🎯 Rolling back to checkpoint: {target_checkpoint.checkpoint_id}")

            # Execute rollback steps
            if rollback_plan:
                # Use provided rollback plan
                rollback_result = await self._execute_planned_rollback(target_checkpoint, rollback_plan)
            else:
                # Use automatic rollback
                rollback_result = await self._execute_automatic_rollback(target_checkpoint)

            result["steps_completed"] = rollback_result.get("steps_completed", [])
            result["agent_results"] = rollback_result.get("agent_results", {})
            result["errors"].extend(rollback_result.get("errors", []))

            # Validate rollback success
            if not result["errors"]:
                validation_results = await self._validate_rollback_success(target_checkpoint)
                result["validation_results"] = validation_results

                if validation_results.get("overall_success", False):
                    result["status"] = "completed"
                    logger.info("✅ Rollback completed successfully")
                else:
                    result["status"] = "completed_with_issues"
                    logger.warning("⚠️ Rollback completed but validation found issues")
            else:
                result["status"] = "failed"
                logger.error("❌ Rollback failed")

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            logger.error(f"❌ Rollback execution error: {e}")

        result["end_time"] = datetime.now()
        result["duration"] = (result["end_time"] - start_time).total_seconds()

        # Record rollback in history
        self.rollback_history.append(result)

        return result

    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint information
        """
        checkpoints = []

        for checkpoint_id, checkpoint in self.checkpoints.items():
            checkpoint_info = {
                "checkpoint_id": checkpoint_id,
                "timestamp": checkpoint.timestamp.isoformat(),
                "migration_phase": checkpoint.migration_phase,
                "agent_count": len(checkpoint.agent_states),
                "age_minutes": (datetime.now() - checkpoint.timestamp).total_seconds() / 60
            }
            checkpoints.append(checkpoint_info)

        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x["timestamp"], reverse=True)

        return checkpoints

    async def validate_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Validate a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint to validate

        Returns:
            Validation results
        """
        checkpoint = self.checkpoints.get(checkpoint_id)
        if not checkpoint:
            return {"valid": False, "error": "Checkpoint not found"}

        validation = {
            "valid": True,
            "checkpoint_id": checkpoint_id,
            "issues": [],
            "warnings": []
        }

        # Check checkpoint age
        age_hours = (datetime.now() - checkpoint.timestamp).total_seconds() / 3600
        if age_hours > 24:
            validation["warnings"].append(f"Checkpoint is {age_hours:.1f} hours old")

        # Validate agent states
        if not checkpoint.agent_states:
            validation["issues"].append("No agent states captured")

        # Validate bridge config
        if not checkpoint.bridge_config:
            validation["issues"].append("No bridge configuration captured")

        # Check rollback instructions
        if not checkpoint.rollback_instructions:
            validation["warnings"].append("No specific rollback instructions")

        validation["valid"] = len(validation["issues"]) == 0

        return validation

    def get_rollback_status(self) -> Dict[str, Any]:
        """Get current rollback manager status."""
        return {
            "checkpoint_count": len(self.checkpoints),
            "latest_checkpoint": max(
                (cp.timestamp for cp in self.checkpoints.values()),
                default=None
            ),
            "rollback_history_count": len(self.rollback_history),
            "last_rollback": self.rollback_history[-1] if self.rollback_history else None,
            "backup_directory": str(self.config["backup_directory"]),
            "configuration": self.config
        }

    # Private methods

    async def _capture_agent_states(self) -> Dict[str, Any]:
        """Capture current state of all agents."""
        try:
            agent_status = await self.bridge.get_agent_status()

            if "error" in agent_status:
                logger.warning(f"Failed to capture agent states: {agent_status['error']}")
                return {}

            agent_states = {}

            for agent_name, status in agent_status.get("agents", {}).items():
                agent_states[agent_name] = {
                    "mode": status.get("mode", "unknown"),
                    "tmux_available": status.get("tmux_available", False),
                    "message_bus_status": status.get("message_bus_status"),
                    "capabilities": status.get("capabilities", []),
                    "capture_time": datetime.now().isoformat()
                }

            return agent_states

        except Exception as e:
            logger.error(f"Failed to capture agent states: {e}")
            return {}

    async def _capture_bridge_config(self) -> Dict[str, Any]:
        """Capture current bridge configuration."""
        try:
            return {
                "migration_status": dict(self.bridge.migration_status),
                "stats": dict(self.bridge.stats),
                "config": dict(self.bridge.config),
                "running": self.bridge.running,
                "message_bus_available": self.bridge.message_bus is not None
            }
        except Exception as e:
            logger.error(f"Failed to capture bridge config: {e}")
            return {}

    async def _capture_system_state(self) -> Dict[str, Any]:
        """Capture relevant system state."""
        try:
            system_state = {
                "timestamp": datetime.now().isoformat(),
                "working_directory": str(Path.cwd()),
                "environment_variables": {}
            }

            # Capture relevant environment variables
            import os
            relevant_vars = ["REDIS_URL", "TMUX_SESSION", "AGENT_HIVE_CONFIG"]
            for var in relevant_vars:
                if var in os.environ:
                    system_state["environment_variables"][var] = os.environ[var]

            # Check tmux session
            try:
                result = subprocess.run(
                    ["tmux", "list-sessions", "-F", "#{session_name}"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    system_state["tmux_sessions"] = result.stdout.strip().split('\n')
            except Exception:
                pass

            return system_state

        except Exception as e:
            logger.error(f"Failed to capture system state: {e}")
            return {}

    def _generate_rollback_instructions(self, agent_states: Dict[str, Any]) -> List[str]:
        """Generate rollback instructions based on agent states."""
        instructions = []

        for agent_name, state in agent_states.items():
            current_mode = state.get("mode", "tmux")

            if current_mode == "message_bus":
                instructions.append(f"Rollback {agent_name} from message_bus to tmux mode")
            elif current_mode == "hybrid":
                instructions.append(f"Rollback {agent_name} from hybrid to tmux mode")

            if not state.get("tmux_available", False):
                instructions.append(f"Restore tmux connectivity for {agent_name}")

        if not instructions:
            instructions.append("All agents in tmux mode - minimal rollback required")

        return instructions

    async def _save_checkpoint_to_disk(self, checkpoint: SafetyCheckpoint) -> None:
        """Save checkpoint to disk for persistence."""
        try:
            backup_file = self.config["backup_directory"] / f"{checkpoint.checkpoint_id}.json"

            checkpoint_data = checkpoint.to_dict()

            with open(backup_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)

            logger.debug(f"Checkpoint saved to {backup_file}")

        except Exception as e:
            logger.error(f"Failed to save checkpoint to disk: {e}")

    async def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints beyond the maximum limit."""
        if len(self.checkpoints) <= self.config["max_checkpoints"]:
            return

        # Sort checkpoints by timestamp
        sorted_checkpoints = sorted(
            self.checkpoints.items(),
            key=lambda x: x[1].timestamp,
            reverse=True
        )

        # Keep only the newest checkpoints
        checkpoints_to_keep = sorted_checkpoints[:self.config["max_checkpoints"]]
        checkpoints_to_remove = sorted_checkpoints[self.config["max_checkpoints"]:]

        # Remove old checkpoints
        for checkpoint_id, checkpoint in checkpoints_to_remove:
            del self.checkpoints[checkpoint_id]

            # Remove from disk
            try:
                backup_file = self.config["backup_directory"] / f"{checkpoint_id}.json"
                if backup_file.exists():
                    backup_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove old checkpoint file: {e}")

        if checkpoints_to_remove:
            logger.info(f"Cleaned up {len(checkpoints_to_remove)} old checkpoints")

    async def _select_rollback_checkpoint(self, checkpoint_id: Optional[str]) -> Optional[SafetyCheckpoint]:
        """Select the appropriate checkpoint for rollback."""
        if checkpoint_id:
            checkpoint = self.checkpoints.get(checkpoint_id)
            if checkpoint:
                return checkpoint
            else:
                logger.warning(f"Requested checkpoint {checkpoint_id} not found")

        # Find the most recent checkpoint
        if not self.checkpoints:
            logger.error("No checkpoints available for rollback")
            return None

        latest_checkpoint = max(
            self.checkpoints.values(),
            key=lambda cp: cp.timestamp
        )

        logger.info(f"Using latest checkpoint: {latest_checkpoint.checkpoint_id}")
        return latest_checkpoint

    async def _execute_planned_rollback(self, checkpoint: SafetyCheckpoint,
                                      rollback_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute rollback using provided plan."""
        result = {
            "steps_completed": [],
            "agent_results": {},
            "errors": []
        }

        try:
            rollback_steps = rollback_plan.get("rollback_steps", [])

            for step in rollback_steps:
                step_result = await self._execute_rollback_step(step, checkpoint)
                result["steps_completed"].append(step_result)

                if not step_result.get("success", False):
                    result["errors"].append(f"Rollback step failed: {step.get('action', 'unknown')}")

        except Exception as e:
            result["errors"].append(f"Planned rollback execution failed: {e}")

        return result

    async def _execute_automatic_rollback(self, checkpoint: SafetyCheckpoint) -> Dict[str, Any]:
        """Execute automatic rollback to checkpoint state."""
        result = {
            "steps_completed": [],
            "agent_results": {},
            "errors": []
        }

        try:
            # Rollback each agent to checkpoint state
            for agent_name, target_state in checkpoint.agent_states.items():
                agent_result = await self._rollback_agent(agent_name, target_state)
                result["agent_results"][agent_name] = agent_result

                if not agent_result.get("success", False):
                    result["errors"].append(f"Failed to rollback agent {agent_name}")

            # Restore bridge configuration
            bridge_result = await self._restore_bridge_config(checkpoint.bridge_config)
            result["steps_completed"].append(bridge_result)

            if not bridge_result.get("success", False):
                result["errors"].append("Failed to restore bridge configuration")

        except Exception as e:
            result["errors"].append(f"Automatic rollback execution failed: {e}")

        return result

    async def _execute_rollback_step(self, step: Dict[str, Any],
                                   checkpoint: SafetyCheckpoint) -> Dict[str, Any]:
        """Execute a single rollback step."""
        action = step.get("action", "unknown")
        timeout = step.get("timeout", 30)

        step_result = {
            "action": action,
            "success": False,
            "start_time": datetime.now(),
            "message": ""
        }

        try:
            if action == "stop_message_bus_communication":
                # Stop message bus for all agents
                for agent_name in checkpoint.agent_states:
                    await self.bridge.migrate_agent(agent_name, "tmux")
                step_result["success"] = True
                step_result["message"] = "Message bus communication stopped"

            elif action == "restore_tmux_communication":
                # Ensure all agents are in tmux mode
                for agent_name, state in checkpoint.agent_states.items():
                    if state.get("tmux_available", False):
                        await self.bridge.migrate_agent(agent_name, "tmux")
                step_result["success"] = True
                step_result["message"] = "Tmux communication restored"

            elif action == "validate_tmux_connectivity":
                # Test tmux connectivity
                connectivity_count = 0
                for agent_name in checkpoint.agent_states:
                    test_success = await self.bridge.send_message(agent_name, "Rollback connectivity test")
                    if test_success:
                        connectivity_count += 1

                total_agents = len(checkpoint.agent_states)
                success_rate = connectivity_count / total_agents if total_agents > 0 else 0
                step_result["success"] = success_rate >= 0.8  # 80% success rate
                step_result["message"] = f"Tmux connectivity: {connectivity_count}/{total_agents} agents"

            else:
                step_result["message"] = f"Unknown rollback action: {action}"

        except Exception as e:
            step_result["message"] = f"Rollback step failed: {e}"

        step_result["end_time"] = datetime.now()
        return step_result

    async def _rollback_agent(self, agent_name: str, target_state: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback a specific agent to target state."""
        result = {
            "agent": agent_name,
            "success": False,
            "target_mode": target_state.get("mode", "tmux"),
            "actions": []
        }

        try:
            target_mode = target_state.get("mode", "tmux")

            # Always rollback to tmux for safety
            if target_mode in ["hybrid", "message_bus"]:
                target_mode = "tmux"

            # Migrate agent to target mode
            migration_success = await self.bridge.migrate_agent(agent_name, target_mode)
            result["actions"].append(f"Migrated to {target_mode}: {'success' if migration_success else 'failed'}")

            # Test connectivity
            if migration_success:
                test_success = await self.bridge.send_message(agent_name, "Rollback test message")
                result["actions"].append(f"Connectivity test: {'success' if test_success else 'failed'}")
                result["success"] = test_success

        except Exception as e:
            result["actions"].append(f"Rollback failed: {e}")

        return result

    async def _restore_bridge_config(self, bridge_config: Dict[str, Any]) -> Dict[str, Any]:
        """Restore bridge configuration."""
        result = {
            "action": "restore_bridge_config",
            "success": False,
            "message": ""
        }

        try:
            # Reset bridge statistics
            self.bridge.stats = bridge_config.get("stats", {})

            # Reset migration status
            migration_status = bridge_config.get("migration_status", {})
            for status_key, agents in migration_status.items():
                if hasattr(self.bridge.migration_status, status_key):
                    self.bridge.migration_status[status_key] = set(agents) if isinstance(agents, list) else agents

            result["success"] = True
            result["message"] = "Bridge configuration restored"

        except Exception as e:
            result["message"] = f"Failed to restore bridge config: {e}"

        return result

    async def _validate_rollback_success(self, checkpoint: SafetyCheckpoint) -> Dict[str, Any]:
        """Validate that rollback was successful."""
        validation = {
            "overall_success": False,
            "agent_validations": {},
            "bridge_validation": {},
            "issues": []
        }

        try:
            # Validate each agent
            successful_agents = 0

            for agent_name in checkpoint.agent_states:
                agent_validation = await self._validate_agent_rollback(agent_name)
                validation["agent_validations"][agent_name] = agent_validation

                if agent_validation.get("success", False):
                    successful_agents += 1

            # Calculate success rate
            total_agents = len(checkpoint.agent_states)
            success_rate = successful_agents / total_agents if total_agents > 0 else 0

            # Bridge validation
            bridge_validation = await self._validate_bridge_rollback()
            validation["bridge_validation"] = bridge_validation

            # Overall success criteria
            validation["overall_success"] = (
                success_rate >= 0.8 and  # 80% of agents working
                bridge_validation.get("success", False)
            )

            if not validation["overall_success"]:
                if success_rate < 0.8:
                    validation["issues"].append(f"Agent success rate too low: {success_rate:.1%}")
                if not bridge_validation.get("success", False):
                    validation["issues"].append("Bridge validation failed")

        except Exception as e:
            validation["issues"].append(f"Rollback validation error: {e}")

        return validation

    async def _validate_agent_rollback(self, agent_name: str) -> Dict[str, Any]:
        """Validate rollback for a specific agent."""
        validation = {
            "agent": agent_name,
            "success": False,
            "tests": []
        }

        try:
            # Test agent status
            status = await self.bridge.get_agent_status(agent_name)
            status_test = {
                "test": "status_check",
                "passed": "error" not in status
            }
            validation["tests"].append(status_test)

            # Test message sending
            if status_test["passed"]:
                message_success = await self.bridge.send_message(agent_name, "Rollback validation test")
                message_test = {
                    "test": "message_sending",
                    "passed": message_success
                }
                validation["tests"].append(message_test)

            # Overall success
            validation["success"] = all(test["passed"] for test in validation["tests"])

        except Exception as e:
            validation["tests"].append({
                "test": "validation_error",
                "passed": False,
                "error": str(e)
            })

        return validation

    async def _validate_bridge_rollback(self) -> Dict[str, Any]:
        """Validate bridge state after rollback."""
        validation = {
            "success": False,
            "checks": []
        }

        try:
            # Check bridge is running
            validation["checks"].append({
                "check": "bridge_running",
                "passed": self.bridge.running
            })

            # Check agent discovery
            agent_status = await self.bridge.get_agent_status()
            agent_discovery_passed = "error" not in agent_status and len(agent_status.get("agents", {})) > 0
            validation["checks"].append({
                "check": "agent_discovery",
                "passed": agent_discovery_passed
            })

            # Overall success
            validation["success"] = all(check["passed"] for check in validation["checks"])

        except Exception as e:
            validation["checks"].append({
                "check": "validation_error",
                "passed": False,
                "error": str(e)
            })

        return validation
