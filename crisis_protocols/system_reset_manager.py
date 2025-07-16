#!/usr/bin/env python3
"""
System Reset Manager - Emergency Crisis Intervention
Foundation Epic Phase 1 Termination and Coordination Crisis Response

Handles multiple converging crises: Phase 1 termination, coordination breakdown,
unresponsive agents, and system discipline failures with micro-PR strategy deployment.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SystemCrisisType(Enum):
    """Types of system crises requiring intervention."""
    PHASE_TERMINATION = "phase_termination"
    COORDINATION_BREAKDOWN = "coordination_breakdown"
    AGENT_UNRESPONSIVE = "agent_unresponsive"
    DISCIPLINE_FAILURE = "discipline_failure"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    MICRO_PR_EMERGENCY = "micro_pr_emergency"


class ResetLevel(Enum):
    """System reset intervention levels."""
    SOFT_RESET = "soft_reset"          # Restart services, maintain state
    HARD_RESET = "hard_reset"          # Full restart, preserve critical data
    EMERGENCY_RESET = "emergency_reset" # Nuclear option, minimal preservation
    DISCIPLINE_RESET = "discipline_reset" # Process enforcement reset


@dataclass
class SystemCrisis:
    """System crisis requiring reset intervention."""
    crisis_id: str
    crisis_type: SystemCrisisType
    reset_level: ResetLevel
    description: str
    affected_components: List[str]
    trigger_time: datetime
    intervention_required: bool
    auto_resettable: bool
    context: Dict[str, Any]


@dataclass
class MicroPRStrategy:
    """Micro-PR deployment strategy for crisis recovery."""
    strategy_id: str
    target_size_lines: int
    priority_components: List[str]
    emergency_mode: bool
    bypass_quality_gates: bool
    immediate_deployment: bool
    rollback_plan: str


class SystemResetManager:
    """
    Emergency system reset manager for crisis intervention.
    
    Handles Phase 1 termination, coordination crises, unresponsive agents,
    and system discipline breakdowns with micro-PR deployment support.
    """
    
    def __init__(self, config_path: str = ".claude/system_reset_config.json"):
        """Initialize system reset manager."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Crisis tracking
        self.active_crises: Dict[str, SystemCrisis] = {}
        self.reset_history: List[SystemCrisis] = []
        
        # Component status tracking
        self.component_status: Dict[str, Any] = {}
        self.agent_status: Dict[str, Any] = {}
        
        # Emergency protocols
        self.emergency_active = False
        self.micro_pr_strategy: Optional[MicroPRStrategy] = None
        
        # Statistics
        self.stats = {
            "crises_detected": 0,
            "resets_performed": 0,
            "micro_prs_deployed": 0,
            "agents_recovered": 0,
            "discipline_interventions": 0
        }
        
        logger.info("SystemResetManager initialized for crisis intervention")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load system reset configuration."""
        default_config = {
            "crisis_detection_interval": 30,  # seconds
            "agent_response_timeout": 120,     # seconds
            "micro_pr_max_lines": 100,
            "emergency_reset_threshold": 5,   # concurrent crises
            "discipline_failure_threshold": 3,
            "components": {
                "event_bus": {"critical": True, "auto_restart": True},
                "crisis_manager": {"critical": True, "auto_restart": True},
                "coordination_protocols": {"critical": True, "auto_restart": False},
                "agent_manager": {"critical": True, "auto_restart": True},
                "accountability_framework": {"critical": False, "auto_restart": True}
            },
            "agents": {
                "pm-agent-new": {"critical": True, "backup_available": False},
                "performance-agent": {"critical": True, "backup_available": True},
                "integration-specialist": {"critical": False, "backup_available": True}
            },
            "micro_pr_strategy": {
                "emergency_size_limit": 50,
                "bypass_gates_on_crisis": True,
                "immediate_deployment": True,
                "rollback_timeout_minutes": 15
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.error(f"Failed to load reset config: {e}")
        
        return default_config
    
    async def detect_system_crises(self) -> List[SystemCrisis]:
        """Detect current system crises requiring intervention."""
        crises = []
        
        # Check for Phase 1 termination crisis
        phase_crisis = await self._detect_phase_termination_crisis()
        if phase_crisis:
            crises.append(phase_crisis)
        
        # Check for coordination breakdown
        coord_crisis = await self._detect_coordination_breakdown()
        if coord_crisis:
            crises.append(coord_crisis)
        
        # Check for unresponsive agents
        agent_crises = await self._detect_unresponsive_agents()
        crises.extend(agent_crises)
        
        # Check for discipline failures
        discipline_crisis = await self._detect_discipline_failures()
        if discipline_crisis:
            crises.append(discipline_crisis)
        
        # Check for infrastructure failures
        infra_crisis = await self._detect_infrastructure_failures()
        if infra_crisis:
            crises.append(infra_crisis)
        
        return crises
    
    async def _detect_phase_termination_crisis(self) -> Optional[SystemCrisis]:
        """Detect Phase 1 termination crisis."""
        try:
            # Check for Phase 1 completion markers
            phase_markers = [
                ".claude/phase_1_complete.json",
                "foundation_epic_complete.marker",
                ".claude/logs/phase_termination.log"
            ]
            
            termination_indicators = []
            for marker in phase_markers:
                if Path(marker).exists():
                    termination_indicators.append(marker)
            
            # Check for critical PR failures
            critical_failures = await self._check_critical_pr_failures()
            
            if termination_indicators or critical_failures:
                return SystemCrisis(
                    crisis_id=f"phase_term_{int(datetime.now().timestamp())}",
                    crisis_type=SystemCrisisType.PHASE_TERMINATION,
                    reset_level=ResetLevel.HARD_RESET,
                    description="Foundation Epic Phase 1 termination detected with critical failures",
                    affected_components=["foundation_epic", "coordination_protocols", "accountability_framework"],
                    trigger_time=datetime.now(),
                    intervention_required=True,
                    auto_resettable=False,
                    context={
                        "termination_indicators": termination_indicators,
                        "critical_failures": critical_failures,
                        "phase": "foundation_epic_phase_1"
                    }
                )
        
        except Exception as e:
            logger.error(f"Error detecting phase termination crisis: {e}")
        
        return None
    
    async def _detect_coordination_breakdown(self) -> Optional[SystemCrisis]:
        """Detect coordination system breakdown."""
        try:
            # Check coordination alert files
            alert_files = [
                ".claude/coordination_alerts.json",
                "coordination_protocols/crisis_alerts.json",
                ".claude/emergency_alert.json"
            ]
            
            crisis_indicators = 0
            for alert_file in alert_files:
                if Path(alert_file).exists():
                    try:
                        with open(alert_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, dict) and data.get("crisis_level") in ["red", "critical"]:
                                crisis_indicators += 1
                    except Exception:
                        pass
            
            # Check for coordination system failures
            coord_failures = await self._check_coordination_system_health()
            
            if crisis_indicators >= 2 or coord_failures:
                return SystemCrisis(
                    crisis_id=f"coord_breakdown_{int(datetime.now().timestamp())}",
                    crisis_type=SystemCrisisType.COORDINATION_BREAKDOWN,
                    reset_level=ResetLevel.HARD_RESET,
                    description="Coordination system breakdown detected",
                    affected_components=["event_bus", "crisis_manager", "coordination_protocols"],
                    trigger_time=datetime.now(),
                    intervention_required=True,
                    auto_resettable=True,
                    context={
                        "crisis_indicators": crisis_indicators,
                        "coordination_failures": coord_failures
                    }
                )
        
        except Exception as e:
            logger.error(f"Error detecting coordination breakdown: {e}")
        
        return None
    
    async def _detect_unresponsive_agents(self) -> List[SystemCrisis]:
        """Detect unresponsive agents."""
        crises = []
        
        try:
            for agent_id, agent_config in self.config["agents"].items():
                if await self._is_agent_unresponsive(agent_id):
                    crisis = SystemCrisis(
                        crisis_id=f"agent_unresponsive_{agent_id}_{int(datetime.now().timestamp())}",
                        crisis_type=SystemCrisisType.AGENT_UNRESPONSIVE,
                        reset_level=ResetLevel.SOFT_RESET if agent_config.get("backup_available") else ResetLevel.HARD_RESET,
                        description=f"Agent {agent_id} unresponsive",
                        affected_components=[f"agent_{agent_id}"],
                        trigger_time=datetime.now(),
                        intervention_required=agent_config.get("critical", False),
                        auto_resettable=agent_config.get("backup_available", False),
                        context={
                            "agent_id": agent_id,
                            "critical": agent_config.get("critical", False),
                            "backup_available": agent_config.get("backup_available", False)
                        }
                    )
                    crises.append(crisis)
        
        except Exception as e:
            logger.error(f"Error detecting unresponsive agents: {e}")
        
        return crises
    
    async def _detect_discipline_failures(self) -> Optional[SystemCrisis]:
        """Detect system discipline failures."""
        try:
            # Check for discipline violation indicators
            violations = []
            
            # Check for quality gate bypasses
            bypass_files = list(Path(".").glob("**/*_bypass_*.json"))
            if len(bypass_files) > self.config["discipline_failure_threshold"]:
                violations.append(f"Quality gate bypasses: {len(bypass_files)}")
            
            # Check for oversized PRs
            oversized_prs = await self._check_oversized_prs()
            if oversized_prs > self.config["discipline_failure_threshold"]:
                violations.append(f"Oversized PRs: {oversized_prs}")
            
            # Check for failed quality checks
            failed_checks = await self._check_failed_quality_checks()
            if failed_checks > self.config["discipline_failure_threshold"]:
                violations.append(f"Failed quality checks: {failed_checks}")
            
            if violations:
                return SystemCrisis(
                    crisis_id=f"discipline_failure_{int(datetime.now().timestamp())}",
                    crisis_type=SystemCrisisType.DISCIPLINE_FAILURE,
                    reset_level=ResetLevel.DISCIPLINE_RESET,
                    description="System discipline breakdown detected",
                    affected_components=["quality_gates", "pr_management", "development_process"],
                    trigger_time=datetime.now(),
                    intervention_required=True,
                    auto_resettable=False,
                    context={
                        "violations": violations,
                        "intervention_required": "micro_pr_strategy"
                    }
                )
        
        except Exception as e:
            logger.error(f"Error detecting discipline failures: {e}")
        
        return None
    
    async def _detect_infrastructure_failures(self) -> Optional[SystemCrisis]:
        """Detect infrastructure component failures."""
        try:
            failed_components = []
            
            for component, config in self.config["components"].items():
                if not await self._check_component_health(component):
                    failed_components.append(component)
            
            if failed_components:
                # Determine reset level based on criticality
                critical_failures = [c for c in failed_components 
                                   if self.config["components"][c].get("critical", False)]
                
                reset_level = ResetLevel.HARD_RESET if critical_failures else ResetLevel.SOFT_RESET
                
                return SystemCrisis(
                    crisis_id=f"infra_failure_{int(datetime.now().timestamp())}",
                    crisis_type=SystemCrisisType.INFRASTRUCTURE_FAILURE,
                    reset_level=reset_level,
                    description=f"Infrastructure failures: {', '.join(failed_components)}",
                    affected_components=failed_components,
                    trigger_time=datetime.now(),
                    intervention_required=bool(critical_failures),
                    auto_resettable=all(self.config["components"][c].get("auto_restart", False) 
                                      for c in failed_components),
                    context={
                        "failed_components": failed_components,
                        "critical_failures": critical_failures
                    }
                )
        
        except Exception as e:
            logger.error(f"Error detecting infrastructure failures: {e}")
        
        return None
    
    async def _check_critical_pr_failures(self) -> List[str]:
        """Check for critical PR failures."""
        failures = []
        try:
            # This would integrate with GitHub API to check PR status
            # For now, simulate failure detection
            pr_failure_indicators = [
                ".claude/logs/pr_failures.log",
                "quality_gate_failures.json"
            ]
            
            for indicator in pr_failure_indicators:
                if Path(indicator).exists():
                    failures.append(indicator)
        
        except Exception as e:
            logger.error(f"Error checking PR failures: {e}")
        
        return failures
    
    async def _check_coordination_system_health(self) -> bool:
        """Check coordination system health."""
        try:
            # Check if coordination files are being updated
            coord_files = [
                ".claude/coordination_alerts.json",
                "coordination_protocols/event_bus_status.json"
            ]
            
            stale_threshold = datetime.now() - timedelta(minutes=10)
            
            for coord_file in coord_files:
                if Path(coord_file).exists():
                    mtime = datetime.fromtimestamp(Path(coord_file).stat().st_mtime)
                    if mtime < stale_threshold:
                        return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking coordination health: {e}")
            return False
    
    async def _is_agent_unresponsive(self, agent_id: str) -> bool:
        """Check if agent is unresponsive."""
        try:
            # Check agent status files
            status_files = [
                f"worktrees/{agent_id}/agent_status.json",
                f".claude/agent_statuses/{agent_id}.json"
            ]
            
            timeout_threshold = datetime.now() - timedelta(seconds=self.config["agent_response_timeout"])
            
            for status_file in status_files:
                if Path(status_file).exists():
                    mtime = datetime.fromtimestamp(Path(status_file).stat().st_mtime)
                    if mtime > timeout_threshold:
                        return False  # Agent is responsive
            
            return True  # No recent activity
        
        except Exception as e:
            logger.error(f"Error checking agent {agent_id} responsiveness: {e}")
            return True  # Assume unresponsive on error
    
    async def _check_component_health(self, component: str) -> bool:
        """Check infrastructure component health."""
        try:
            # Component-specific health checks
            if component == "event_bus":
                return Path(".claude/event_bus_active.marker").exists()
            elif component == "crisis_manager":
                return Path(".claude/crisis_manager_active.marker").exists()
            elif component == "coordination_protocols":
                return Path("coordination_protocols").exists() and any(Path("coordination_protocols").iterdir())
            else:
                return True  # Default to healthy
        
        except Exception as e:
            logger.error(f"Error checking component {component} health: {e}")
            return False
    
    async def _check_oversized_prs(self) -> int:
        """Check for oversized PRs."""
        # This would integrate with GitHub API
        # For now, return simulated count
        return 0
    
    async def _check_failed_quality_checks(self) -> int:
        """Check for failed quality checks."""
        try:
            failure_files = list(Path(".").glob("**/*quality_failure*.log"))
            return len(failure_files)
        except Exception:
            return 0
    
    async def execute_system_reset(self, crisis: SystemCrisis) -> bool:
        """Execute system reset for crisis intervention."""
        try:
            logger.critical(f"Executing {crisis.reset_level.value} for crisis: {crisis.description}")
            
            # Add to active crises
            self.active_crises[crisis.crisis_id] = crisis
            
            # Execute reset based on level
            if crisis.reset_level == ResetLevel.SOFT_RESET:
                success = await self._execute_soft_reset(crisis)
            elif crisis.reset_level == ResetLevel.HARD_RESET:
                success = await self._execute_hard_reset(crisis)
            elif crisis.reset_level == ResetLevel.EMERGENCY_RESET:
                success = await self._execute_emergency_reset(crisis)
            elif crisis.reset_level == ResetLevel.DISCIPLINE_RESET:
                success = await self._execute_discipline_reset(crisis)
            else:
                logger.error(f"Unknown reset level: {crisis.reset_level}")
                return False
            
            if success:
                self.stats["resets_performed"] += 1
                crisis.context["reset_completed"] = datetime.now().isoformat()
                
                # Move to history
                self.reset_history.append(crisis)
                if crisis.crisis_id in self.active_crises:
                    del self.active_crises[crisis.crisis_id]
            
            return success
        
        except Exception as e:
            logger.error(f"Error executing system reset: {e}")
            return False
    
    async def _execute_soft_reset(self, crisis: SystemCrisis) -> bool:
        """Execute soft reset - restart services, maintain state."""
        try:
            logger.info("Executing soft reset...")
            
            # Restart auto-restartable components
            for component in crisis.affected_components:
                if (component in self.config["components"] and 
                    self.config["components"][component].get("auto_restart", False)):
                    await self._restart_component(component)
            
            # Activate micro-PR strategy if needed
            if crisis.crisis_type == SystemCrisisType.AGENT_UNRESPONSIVE:
                await self._activate_micro_pr_strategy("soft_reset")
            
            return True
        
        except Exception as e:
            logger.error(f"Soft reset failed: {e}")
            return False
    
    async def _execute_hard_reset(self, crisis: SystemCrisis) -> bool:
        """Execute hard reset - full restart, preserve critical data."""
        try:
            logger.warning("Executing hard reset...")
            
            # Preserve critical data
            await self._preserve_critical_data()
            
            # Stop all services
            await self._stop_all_services()
            
            # Clear non-critical state
            await self._clear_transient_state()
            
            # Restart services
            await self._restart_all_services()
            
            # Activate emergency micro-PR strategy
            await self._activate_micro_pr_strategy("emergency")
            
            return True
        
        except Exception as e:
            logger.error(f"Hard reset failed: {e}")
            return False
    
    async def _execute_emergency_reset(self, crisis: SystemCrisis) -> bool:
        """Execute emergency reset - nuclear option, minimal preservation."""
        try:
            logger.critical("Executing EMERGENCY reset...")
            
            self.emergency_active = True
            
            # Preserve only absolutely critical data
            await self._preserve_critical_data()
            
            # Nuclear reset
            await self._nuclear_reset()
            
            # Deploy emergency micro-PR strategy
            await self._activate_micro_pr_strategy("nuclear")
            
            # Write emergency status
            emergency_status = {
                "emergency_reset_executed": True,
                "crisis_id": crisis.crisis_id,
                "timestamp": datetime.now().isoformat(),
                "description": crisis.description,
                "recovery_mode": "emergency"
            }
            
            with open(".claude/emergency_reset_status.json", "w") as f:
                json.dump(emergency_status, f, indent=2)
            
            return True
        
        except Exception as e:
            logger.critical(f"Emergency reset failed: {e}")
            return False
    
    async def _execute_discipline_reset(self, crisis: SystemCrisis) -> bool:
        """Execute discipline reset - process enforcement reset."""
        try:
            logger.warning("Executing discipline reset...")
            
            # Reset quality gates
            await self._reset_quality_gates()
            
            # Enforce micro-PR strategy
            await self._enforce_micro_pr_discipline()
            
            # Reset development process
            await self._reset_development_process()
            
            self.stats["discipline_interventions"] += 1
            
            return True
        
        except Exception as e:
            logger.error(f"Discipline reset failed: {e}")
            return False
    
    async def _activate_micro_pr_strategy(self, mode: str) -> None:
        """Activate micro-PR deployment strategy."""
        try:
            strategy_config = self.config["micro_pr_strategy"]
            
            if mode == "emergency" or mode == "nuclear":
                max_lines = strategy_config["emergency_size_limit"]
                bypass_gates = True
                immediate_deploy = True
            else:
                max_lines = self.config["micro_pr_max_lines"]
                bypass_gates = strategy_config["bypass_gates_on_crisis"]
                immediate_deploy = strategy_config["immediate_deployment"]
            
            self.micro_pr_strategy = MicroPRStrategy(
                strategy_id=f"crisis_recovery_{mode}_{int(datetime.now().timestamp())}",
                target_size_lines=max_lines,
                priority_components=["crisis_recovery", "system_stability"],
                emergency_mode=(mode in ["emergency", "nuclear"]),
                bypass_quality_gates=bypass_gates,
                immediate_deployment=immediate_deploy,
                rollback_plan=f"Rollback after {strategy_config['rollback_timeout_minutes']} minutes if unstable"
            )
            
            # Write micro-PR strategy file
            strategy_file = Path(".claude/micro_pr_strategy.json")
            with open(strategy_file, "w") as f:
                json.dump(asdict(self.micro_pr_strategy), f, indent=2, default=str)
            
            self.stats["micro_prs_deployed"] += 1
            
            logger.info(f"Activated micro-PR strategy: {mode} mode, max {max_lines} lines")
        
        except Exception as e:
            logger.error(f"Failed to activate micro-PR strategy: {e}")
    
    async def _restart_component(self, component: str) -> None:
        """Restart specific component."""
        logger.info(f"Restarting component: {component}")
        # Component-specific restart logic would go here
    
    async def _preserve_critical_data(self) -> None:
        """Preserve critical system data."""
        logger.info("Preserving critical data...")
        # Data preservation logic would go here
    
    async def _stop_all_services(self) -> None:
        """Stop all system services."""
        logger.info("Stopping all services...")
        # Service shutdown logic would go here
    
    async def _clear_transient_state(self) -> None:
        """Clear non-critical transient state."""
        logger.info("Clearing transient state...")
        # State clearing logic would go here
    
    async def _restart_all_services(self) -> None:
        """Restart all system services."""
        logger.info("Restarting all services...")
        # Service restart logic would go here
    
    async def _nuclear_reset(self) -> None:
        """Perform nuclear reset."""
        logger.critical("Performing nuclear reset...")
        # Nuclear reset logic would go here
    
    async def _reset_quality_gates(self) -> None:
        """Reset quality gate system."""
        logger.info("Resetting quality gates...")
        # Quality gate reset logic would go here
    
    async def _enforce_micro_pr_discipline(self) -> None:
        """Enforce micro-PR discipline."""
        logger.info("Enforcing micro-PR discipline...")
        # Discipline enforcement logic would go here
    
    async def _reset_development_process(self) -> None:
        """Reset development process."""
        logger.info("Resetting development process...")
        # Development process reset logic would go here
    
    def get_reset_status(self) -> Dict[str, Any]:
        """Get system reset status."""
        return {
            "emergency_active": self.emergency_active,
            "active_crises": len(self.active_crises),
            "micro_pr_strategy_active": self.micro_pr_strategy is not None,
            "statistics": self.stats.copy(),
            "recent_resets": len([r for r in self.reset_history 
                                if r.trigger_time > datetime.now() - timedelta(hours=24)]),
            "timestamp": datetime.now().isoformat()
        }


# CLI Interface for emergency operations
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="System Reset Manager - Emergency Crisis Intervention")
    parser.add_argument("--detect", action="store_true", help="Detect system crises")
    parser.add_argument("--reset", choices=["soft", "hard", "emergency", "discipline"], help="Execute reset")
    parser.add_argument("--status", action="store_true", help="Show reset status")
    parser.add_argument("--micro-pr", action="store_true", help="Activate micro-PR strategy")
    
    args = parser.parse_args()
    
    async def main():
        reset_manager = SystemResetManager()
        
        if args.detect:
            crises = await reset_manager.detect_system_crises()
            print(f"Detected {len(crises)} system crises:")
            for crisis in crises:
                print(f"  - {crisis.crisis_type.value}: {crisis.description}")
        
        elif args.reset:
            # Create dummy crisis for manual reset
            reset_level_map = {
                "soft": ResetLevel.SOFT_RESET,
                "hard": ResetLevel.HARD_RESET,
                "emergency": ResetLevel.EMERGENCY_RESET,
                "discipline": ResetLevel.DISCIPLINE_RESET
            }
            
            crisis = SystemCrisis(
                crisis_id=f"manual_reset_{int(datetime.now().timestamp())}",
                crisis_type=SystemCrisisType.COORDINATION_BREAKDOWN,
                reset_level=reset_level_map[args.reset],
                description=f"Manual {args.reset} reset requested",
                affected_components=["all"],
                trigger_time=datetime.now(),
                intervention_required=True,
                auto_resettable=False,
                context={"manual": True}
            )
            
            success = await reset_manager.execute_system_reset(crisis)
            print(f"Reset {'successful' if success else 'failed'}")
        
        elif args.micro_pr:
            await reset_manager._activate_micro_pr_strategy("manual")
            print("Micro-PR strategy activated")
        
        elif args.status:
            status = reset_manager.get_reset_status()
            print(json.dumps(status, indent=2, default=str))
        
        else:
            print("System Reset Manager - Emergency Crisis Intervention")
            print("Foundation Epic Phase 1 Termination and Coordination Crisis Response")
            print("")
            print("Usage: python crisis_protocols/system_reset_manager.py [--detect|--reset|--status|--micro-pr]")
            print("")
            print("Crisis Types: PHASE_TERMINATION, COORDINATION_BREAKDOWN, AGENT_UNRESPONSIVE")
            print("Reset Levels: SOFT_RESET, HARD_RESET, EMERGENCY_RESET, DISCIPLINE_RESET")
    
    asyncio.run(main())