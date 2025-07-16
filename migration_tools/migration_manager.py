"""
Migration Manager for Foundation Epic

Orchestrates zero-disruption migration from tmux to message bus.
Provides comprehensive migration strategies, monitoring, and safety controls.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from .compatibility_layer import TmuxMessageBridge, DualModeOperator
from .validation import MigrationValidator
from .rollback import RollbackManager


logger = logging.getLogger(__name__)


class MigrationStrategy(Enum):
    """Migration strategy options."""
    GRADUAL = "gradual"           # Migrate one agent at a time
    CANARY = "canary"            # Test with one agent first
    IMMEDIATE = "immediate"       # Migrate all at once (risky)
    BATCH = "batch"              # Migrate in small batches
    CAPABILITY_BASED = "capability_based"  # Migrate by agent type


class MigrationPhase(Enum):
    """Migration phase states."""
    PLANNING = "planning"
    PREPARATION = "preparation"
    VALIDATION = "validation"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    COMPLETION = "completion"
    ROLLBACK = "rollback"


@dataclass
class MigrationConfig:
    """Configuration for migration process."""
    strategy: MigrationStrategy = MigrationStrategy.GRADUAL
    target_agents: List[str] = None
    validation_timeout: int = 300  # 5 minutes
    rollback_threshold: float = 0.8  # 80% success rate
    monitoring_duration: int = 1800  # 30 minutes
    backup_enabled: bool = True
    dry_run: bool = False
    
    def __post_init__(self):
        if self.target_agents is None:
            self.target_agents = []


@dataclass 
class MigrationStep:
    """Individual migration step."""
    step_id: str
    agent: str
    action: str  # "discover", "migrate_to_hybrid", "migrate_to_message_bus", "validate"
    expected_duration: int  # seconds
    retry_count: int = 0
    max_retries: int = 3
    rollback_actions: List[str] = None
    
    def __post_init__(self):
        if self.rollback_actions is None:
            self.rollback_actions = []


class MigrationManager:
    """
    Comprehensive migration manager for Foundation Epic.
    
    Orchestrates zero-disruption migration from tmux to production message bus.
    Provides safety controls, monitoring, and rollback capabilities.
    """
    
    def __init__(self, config: MigrationConfig):
        """
        Initialize migration manager.
        
        Args:
            config: Migration configuration
        """
        self.config = config
        self.bridge = TmuxMessageBridge()
        self.dual_mode = DualModeOperator(self.bridge)
        self.validator = MigrationValidator(self.bridge)
        self.rollback_manager = RollbackManager(self.bridge)
        
        # Migration state
        self.current_phase = MigrationPhase.PLANNING
        self.migration_plan: Optional[Dict[str, Any]] = None
        self.execution_log: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        
        # Performance tracking
        self.performance_baseline: Dict[str, Any] = {}
        self.current_performance: Dict[str, Any] = {}
        
        # Safety controls
        self.emergency_stop = False
        self.rollback_triggered = False
        
        logger.info("MigrationManager initialized")
    
    async def start(self) -> None:
        """Start migration manager components."""
        await self.bridge.start()
        await self.rollback_manager.start()
        logger.info("Migration manager started")
    
    async def stop(self) -> None:
        """Stop migration manager components."""
        await self.rollback_manager.stop()
        await self.bridge.stop()
        logger.info("Migration manager stopped")
    
    async def discover_agents(self) -> Dict[str, Any]:
        """
        Discover all available agents in the system.
        
        Returns:
            Agent discovery results
        """
        logger.info("🔍 Starting agent discovery...")
        
        # Get current agent status from bridge
        status = await self.bridge.get_agent_status()
        
        discovered_agents = []
        if "agents" in status:
            for agent_name, agent_info in status["agents"].items():
                if not agent_info.get("error"):
                    discovered_agents.append({
                        "name": agent_name,
                        "mode": agent_info.get("mode", "tmux"),
                        "capabilities": agent_info.get("capabilities", []),
                        "tmux_available": agent_info.get("tmux_available", False),
                        "migration_ready": self._assess_migration_readiness(agent_info)
                    })
        
        discovery_result = {
            "total_agents": len(discovered_agents),
            "agents": discovered_agents,
            "migration_candidates": [a for a in discovered_agents if a["migration_ready"]],
            "discovery_time": datetime.now(),
            "bridge_stats": status.get("statistics", {})
        }
        
        logger.info(f"✅ Discovered {len(discovered_agents)} agents, {len(discovery_result['migration_candidates'])} ready for migration")
        
        return discovery_result
    
    async def create_migration_plan(self, target_agents: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create comprehensive migration plan.
        
        Args:
            target_agents: Specific agents to migrate (None for all)
            
        Returns:
            Migration plan
        """
        logger.info("📋 Creating migration plan...")
        self.current_phase = MigrationPhase.PLANNING
        
        # Discover agents if not specified
        if not target_agents:
            discovery = await self.discover_agents()
            target_agents = [a["name"] for a in discovery["migration_candidates"]]
        
        # Create base plan using dual-mode operator
        base_plan = await self.dual_mode.create_migration_plan(
            target_agents, 
            self.config.strategy.value
        )
        
        # Enhance plan with safety controls
        enhanced_plan = {
            **base_plan,
            "config": self.config,
            "safety_controls": {
                "pre_migration_backup": self.config.backup_enabled,
                "rollback_threshold": self.config.rollback_threshold,
                "validation_timeout": self.config.validation_timeout,
                "monitoring_duration": self.config.monitoring_duration
            },
            "checkpoints": self._create_checkpoints(base_plan),
            "rollback_plan": self._create_rollback_plan(target_agents),
            "validation_matrix": self._create_validation_matrix(target_agents)
        }
        
        self.migration_plan = enhanced_plan
        
        logger.info(f"✅ Migration plan created for {len(target_agents)} agents")
        logger.info(f"📊 Strategy: {self.config.strategy.value}")
        logger.info(f"⏱️ Estimated duration: {enhanced_plan.get('estimated_duration', 0)} minutes")
        
        return enhanced_plan
    
    async def execute_migration(self, dry_run: bool = None) -> Dict[str, Any]:
        """
        Execute the migration plan.
        
        Args:
            dry_run: Override config dry_run setting
            
        Returns:
            Migration execution results
        """
        if not self.migration_plan:
            raise ValueError("No migration plan available. Call create_migration_plan() first.")
        
        is_dry_run = dry_run if dry_run is not None else self.config.dry_run
        
        logger.info(f"🚀 {'DRY RUN: ' if is_dry_run else ''}Starting migration execution...")
        
        self.current_phase = MigrationPhase.PREPARATION
        self.start_time = datetime.now()
        
        execution_result = {
            "status": "in_progress",
            "dry_run": is_dry_run,
            "start_time": self.start_time,
            "phases_completed": [],
            "current_phase": None,
            "performance_impact": {},
            "errors": [],
            "rollback_triggered": False
        }
        
        try:
            # Phase 1: Preparation
            prep_result = await self._execute_preparation_phase(is_dry_run)
            execution_result["phases_completed"].append(prep_result)
            
            if not prep_result["success"]:
                execution_result["status"] = "failed"
                execution_result["errors"].extend(prep_result.get("errors", []))
                return execution_result
            
            # Phase 2: Pre-migration validation
            self.current_phase = MigrationPhase.VALIDATION
            validation_result = await self._execute_validation_phase(is_dry_run)
            execution_result["phases_completed"].append(validation_result)
            
            if not validation_result["success"]:
                execution_result["status"] = "failed"
                execution_result["errors"].extend(validation_result.get("errors", []))
                return execution_result
            
            # Phase 3: Migration execution
            self.current_phase = MigrationPhase.EXECUTION
            migration_result = await self._execute_migration_phase(is_dry_run)
            execution_result["phases_completed"].append(migration_result)
            
            if not migration_result["success"] or self.rollback_triggered:
                execution_result["status"] = "failed"
                execution_result["rollback_triggered"] = self.rollback_triggered
                execution_result["errors"].extend(migration_result.get("errors", []))
                return execution_result
            
            # Phase 4: Post-migration monitoring
            self.current_phase = MigrationPhase.MONITORING
            monitoring_result = await self._execute_monitoring_phase(is_dry_run)
            execution_result["phases_completed"].append(monitoring_result)
            
            # Final status
            if monitoring_result["success"] and not self.rollback_triggered:
                execution_result["status"] = "completed"
                self.current_phase = MigrationPhase.COMPLETION
            else:
                execution_result["status"] = "completed_with_issues"
            
            execution_result["end_time"] = datetime.now()
            execution_result["total_duration"] = (execution_result["end_time"] - self.start_time).total_seconds()
            
            logger.info(f"✅ Migration execution {'completed' if execution_result['status'] == 'completed' else 'finished with issues'}")
            
        except Exception as e:
            execution_result["status"] = "error"
            execution_result["errors"].append(str(e))
            logger.error(f"❌ Migration execution failed: {e}")
            
            # Trigger emergency rollback if not dry run
            if not is_dry_run:
                await self._trigger_emergency_rollback()
        
        return execution_result
    
    async def monitor_migration_health(self) -> Dict[str, Any]:
        """
        Monitor migration health and performance.
        
        Returns:
            Health monitoring results
        """
        health_status = {
            "overall_health": "unknown",
            "agent_health": {},
            "performance_metrics": {},
            "recommendations": [],
            "timestamp": datetime.now()
        }
        
        try:
            # Check each agent's health
            agent_statuses = await self.bridge.get_agent_status()
            
            if "agents" in agent_statuses:
                healthy_agents = 0
                total_agents = len(agent_statuses["agents"])
                
                for agent_name, status in agent_statuses["agents"].items():
                    agent_healthy = not status.get("error") and (
                        status.get("tmux_available") or 
                        status.get("message_bus_status")
                    )
                    
                    health_status["agent_health"][agent_name] = {
                        "healthy": agent_healthy,
                        "mode": status.get("mode", "unknown"),
                        "last_check": datetime.now().isoformat()
                    }
                    
                    if agent_healthy:
                        healthy_agents += 1
                
                # Calculate overall health
                health_ratio = healthy_agents / total_agents if total_agents > 0 else 0
                
                if health_ratio >= 0.9:
                    health_status["overall_health"] = "excellent"
                elif health_ratio >= 0.8:
                    health_status["overall_health"] = "good"
                elif health_ratio >= 0.6:
                    health_status["overall_health"] = "degraded"
                else:
                    health_status["overall_health"] = "critical"
                
                # Performance metrics
                bridge_stats = agent_statuses.get("statistics", {})
                health_status["performance_metrics"] = {
                    "message_success_rate": self._calculate_success_rate(bridge_stats),
                    "bridge_stats": bridge_stats,
                    "health_ratio": health_ratio
                }
                
                # Recommendations
                if health_ratio < self.config.rollback_threshold:
                    health_status["recommendations"].append(
                        f"Health ratio {health_ratio:.1%} below threshold {self.config.rollback_threshold:.1%} - consider rollback"
                    )
                
                if bridge_stats.get("failed_messages", 0) > 10:
                    health_status["recommendations"].append("High message failure rate detected")
        
        except Exception as e:
            health_status["overall_health"] = "error"
            health_status["error"] = str(e)
        
        return health_status
    
    async def trigger_rollback(self, reason: str = "Manual rollback requested") -> Dict[str, Any]:
        """
        Trigger migration rollback.
        
        Args:
            reason: Reason for rollback
            
        Returns:
            Rollback results
        """
        logger.warning(f"🔄 Triggering migration rollback: {reason}")
        
        self.rollback_triggered = True
        self.current_phase = MigrationPhase.ROLLBACK
        
        rollback_result = await self.rollback_manager.execute_rollback(
            reason=reason,
            rollback_plan=self.migration_plan.get("rollback_plan") if self.migration_plan else None
        )
        
        return rollback_result
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        return {
            "current_phase": self.current_phase.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "migration_plan_exists": self.migration_plan is not None,
            "emergency_stop": self.emergency_stop,
            "rollback_triggered": self.rollback_triggered,
            "execution_log_entries": len(self.execution_log)
        }
    
    # Private methods
    
    def _assess_migration_readiness(self, agent_info: Dict[str, Any]) -> bool:
        """Assess if agent is ready for migration."""
        # Agent is ready if it has tmux availability and no critical errors
        return (
            agent_info.get("tmux_available", False) and
            not agent_info.get("error") and
            agent_info.get("mode") == "tmux"  # Only migrate tmux agents
        )
    
    def _create_checkpoints(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create safety checkpoints for migration plan."""
        checkpoints = []
        
        phases = plan.get("phases", [])
        for i, phase in enumerate(phases):
            checkpoint = {
                "checkpoint_id": f"checkpoint_{i+1}",
                "after_phase": phase.get("phase", i+1),
                "validation_required": True,
                "rollback_point": True,
                "estimated_time": phase.get("estimated_time", 5)
            }
            checkpoints.append(checkpoint)
        
        return checkpoints
    
    def _create_rollback_plan(self, agents: List[str]) -> Dict[str, Any]:
        """Create rollback plan for agents."""
        return {
            "rollback_strategy": "immediate",
            "agents": agents,
            "rollback_steps": [
                {"action": "stop_message_bus_communication", "timeout": 30},
                {"action": "restore_tmux_communication", "timeout": 60},
                {"action": "validate_tmux_connectivity", "timeout": 30}
            ],
            "validation_timeout": 120
        }
    
    def _create_validation_matrix(self, agents: List[str]) -> Dict[str, Any]:
        """Create validation matrix for migration."""
        return {
            "pre_migration": [
                "tmux_connectivity",
                "agent_responsiveness", 
                "baseline_performance"
            ],
            "during_migration": [
                "dual_mode_functionality",
                "message_delivery",
                "performance_impact"
            ],
            "post_migration": [
                "message_bus_connectivity",
                "end_to_end_communication",
                "performance_validation"
            ],
            "agents": agents
        }
    
    async def _execute_preparation_phase(self, dry_run: bool) -> Dict[str, Any]:
        """Execute preparation phase."""
        logger.info("🔧 Executing preparation phase...")
        
        result = {
            "phase": "preparation",
            "success": False,
            "start_time": datetime.now(),
            "actions": [],
            "errors": []
        }
        
        try:
            # Create backup if enabled
            if self.config.backup_enabled and not dry_run:
                backup_result = await self.rollback_manager.create_checkpoint("pre_migration_backup")
                result["actions"].append({"action": "create_backup", "success": backup_result})
            
            # Capture performance baseline
            baseline = await self._capture_performance_baseline()
            self.performance_baseline = baseline
            result["actions"].append({"action": "capture_baseline", "success": True, "data": baseline})
            
            # Validate pre-conditions
            validation = await self.validator.validate_pre_migration_conditions()
            result["actions"].append({"action": "validate_preconditions", "success": validation["passed"], "data": validation})
            
            if not validation["passed"]:
                result["errors"].extend([f"Precondition failed: {f}" for f in validation["failed_checks"]])
            
            result["success"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(str(e))
        
        result["end_time"] = datetime.now()
        return result
    
    async def _execute_validation_phase(self, dry_run: bool) -> Dict[str, Any]:
        """Execute validation phase."""
        logger.info("✅ Executing validation phase...")
        
        result = {
            "phase": "validation",
            "success": False,
            "start_time": datetime.now(),
            "validations": [],
            "errors": []
        }
        
        try:
            # Validate migration plan
            plan_validation = await self.validator.validate_migration_plan(self.migration_plan)
            result["validations"].append(plan_validation)
            
            # Test connectivity to all agents
            connectivity_validation = await self.validator.validate_agent_connectivity(
                self.migration_plan.get("agents", [])
            )
            result["validations"].append(connectivity_validation)
            
            # Check system resources
            resource_validation = await self.validator.validate_system_resources()
            result["validations"].append(resource_validation)
            
            # Overall validation success
            result["success"] = all(v["passed"] for v in result["validations"])
            
            if not result["success"]:
                failed_validations = [v["name"] for v in result["validations"] if not v["passed"]]
                result["errors"].append(f"Failed validations: {', '.join(failed_validations)}")
        
        except Exception as e:
            result["errors"].append(str(e))
        
        result["end_time"] = datetime.now()
        return result
    
    async def _execute_migration_phase(self, dry_run: bool) -> Dict[str, Any]:
        """Execute migration phase."""
        logger.info("🔄 Executing migration phase...")
        
        result = {
            "phase": "migration",
            "success": False,
            "start_time": datetime.now(),
            "agent_results": [],
            "errors": []
        }
        
        try:
            if dry_run:
                # Simulate migration
                for agent in self.migration_plan.get("agents", []):
                    result["agent_results"].append({
                        "agent": agent,
                        "success": True,
                        "simulated": True,
                        "steps": ["tmux_test", "hybrid_test", "message_bus_test"]
                    })
                result["success"] = True
            else:
                # Execute actual migration
                migration_execution = await self.dual_mode.execute_migration(self.migration_plan)
                result["agent_results"] = migration_execution.get("completed_phases", [])
                result["errors"] = migration_execution.get("errors", [])
                result["success"] = migration_execution.get("status") == "completed"
            
        except Exception as e:
            result["errors"].append(str(e))
        
        result["end_time"] = datetime.now()
        return result
    
    async def _execute_monitoring_phase(self, dry_run: bool) -> Dict[str, Any]:
        """Execute monitoring phase."""
        logger.info("📊 Executing monitoring phase...")
        
        result = {
            "phase": "monitoring", 
            "success": False,
            "start_time": datetime.now(),
            "health_checks": [],
            "performance_impact": {},
            "errors": []
        }
        
        try:
            # Monitor for configured duration (shortened for testing)
            monitor_duration = 30 if dry_run else min(self.config.monitoring_duration, 300)  # Max 5 minutes
            
            for i in range(3):  # 3 health checks
                health = await self.monitor_migration_health()
                result["health_checks"].append(health)
                
                # Check if rollback is needed
                if health["overall_health"] in ["critical", "error"]:
                    if not dry_run:
                        await self.trigger_rollback("Health degraded below acceptable level")
                    break
                
                if i < 2:  # Don't sleep after last check
                    await asyncio.sleep(monitor_duration / 3)
            
            # Calculate performance impact
            result["performance_impact"] = await self._calculate_performance_impact()
            
            # Success if no critical health issues
            result["success"] = all(
                h["overall_health"] not in ["critical", "error"] 
                for h in result["health_checks"]
            )
            
        except Exception as e:
            result["errors"].append(str(e))
        
        result["end_time"] = datetime.now()
        return result
    
    async def _capture_performance_baseline(self) -> Dict[str, Any]:
        """Capture performance baseline before migration."""
        try:
            bridge_stats = await self.bridge.get_agent_status()
            return {
                "timestamp": datetime.now().isoformat(),
                "bridge_statistics": bridge_stats.get("statistics", {}),
                "agent_count": len(bridge_stats.get("agents", {})),
                "message_success_rate": self._calculate_success_rate(bridge_stats.get("statistics", {}))
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def _calculate_performance_impact(self) -> Dict[str, Any]:
        """Calculate performance impact of migration."""
        try:
            current_stats = await self.bridge.get_agent_status()
            current_performance = {
                "bridge_statistics": current_stats.get("statistics", {}),
                "agent_count": len(current_stats.get("agents", {})),
                "message_success_rate": self._calculate_success_rate(current_stats.get("statistics", {}))
            }
            
            baseline_rate = self.performance_baseline.get("message_success_rate", 1.0)
            current_rate = current_performance.get("message_success_rate", 1.0)
            
            return {
                "baseline": self.performance_baseline,
                "current": current_performance,
                "success_rate_change": current_rate - baseline_rate,
                "impact_assessment": "positive" if current_rate >= baseline_rate else "negative"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_success_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate message success rate from statistics."""
        total_messages = (
            stats.get("tmux_messages", 0) + 
            stats.get("message_bus_messages", 0) + 
            stats.get("bridge_messages", 0)
        )
        failed_messages = stats.get("failed_messages", 0)
        
        if total_messages == 0:
            return 1.0
        
        return (total_messages - failed_messages) / total_messages
    
    async def _trigger_emergency_rollback(self) -> None:
        """Trigger emergency rollback."""
        logger.critical("🚨 Triggering emergency rollback!")
        self.emergency_stop = True
        await self.trigger_rollback("Emergency rollback due to critical failure")