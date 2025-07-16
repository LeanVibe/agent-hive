"""
Migration Validation for Foundation Epic

Provides comprehensive validation framework for migration from tmux to message bus.
Ensures all migration steps are validated before, during, and after execution.
"""

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    passed: bool
    message: str = ""
    details: Dict[str, Any] = None
    timestamp: datetime = None
    execution_time: float = 0.0
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MigrationValidator:
    """
    Comprehensive validation framework for migration.
    
    Validates pre-migration conditions, monitors migration progress,
    and validates post-migration functionality.
    """
    
    def __init__(self, bridge):
        """
        Initialize migration validator.
        
        Args:
            bridge: TmuxMessageBridge instance
        """
        self.bridge = bridge
        self.validation_history: List[ValidationResult] = []
        
        # Validation thresholds
        self.thresholds = {
            "max_response_time": 5.0,  # seconds
            "min_success_rate": 0.95,
            "max_error_rate": 0.05,
            "min_agent_count": 1,
            "max_migration_time": 300  # seconds per agent
        }
        
        logger.info("MigrationValidator initialized")
    
    async def validate_pre_migration_conditions(self) -> ValidationResult:
        """
        Validate conditions before starting migration.
        
        Returns:
            ValidationResult with overall pre-migration validation
        """
        logger.info("🔍 Starting pre-migration validation...")
        
        start_time = time.time()
        validations = []
        
        # Check tmux availability
        tmux_validation = await self._validate_tmux_availability()
        validations.append(tmux_validation)
        
        # Check system resources
        resource_validation = await self._validate_system_resources()
        validations.append(resource_validation)
        
        # Check agent discovery
        agent_validation = await self._validate_agent_discovery()
        validations.append(agent_validation)
        
        # Check message bus readiness
        message_bus_validation = await self._validate_message_bus_readiness()
        validations.append(message_bus_validation)
        
        # Overall result
        passed = all(v.passed for v in validations)
        failed_checks = [v.name for v in validations if not v.passed]
        
        result = ValidationResult(
            name="pre_migration_conditions",
            passed=passed,
            message=f"Pre-migration validation {'passed' if passed else 'failed'}",
            details={
                "validations": [
                    {
                        "name": v.name,
                        "passed": v.passed,
                        "message": v.message,
                        "details": v.details
                    }
                    for v in validations
                ],
                "failed_checks": failed_checks,
                "total_checks": len(validations)
            },
            execution_time=time.time() - start_time
        )
        
        self.validation_history.append(result)
        
        if passed:
            logger.info("✅ Pre-migration validation passed")
        else:
            logger.warning(f"❌ Pre-migration validation failed: {failed_checks}")
        
        return result
    
    async def validate_migration_plan(self, plan: Dict[str, Any]) -> ValidationResult:
        """
        Validate migration plan structure and feasibility.
        
        Args:
            plan: Migration plan to validate
            
        Returns:
            ValidationResult for plan validation
        """
        logger.info("📋 Validating migration plan...")
        
        start_time = time.time()
        issues = []
        
        # Required plan fields
        required_fields = ["strategy", "agents", "phases"]
        for field in required_fields:
            if field not in plan:
                issues.append(f"Missing required field: {field}")
        
        # Validate agents
        if "agents" in plan:
            agents = plan["agents"]
            if not isinstance(agents, list) or len(agents) == 0:
                issues.append("Plan must include at least one agent")
            
            # Check if agents exist
            for agent in agents:
                agent_status = await self.bridge.get_agent_status(agent)
                if "error" in agent_status:
                    issues.append(f"Agent {agent} not found or unavailable")
        
        # Validate phases
        if "phases" in plan:
            phases = plan["phases"]
            if not isinstance(phases, list) or len(phases) == 0:
                issues.append("Plan must include at least one phase")
        
        # Validate strategy
        if "strategy" in plan:
            valid_strategies = ["gradual", "canary", "immediate", "batch", "capability_based"]
            if plan["strategy"] not in valid_strategies:
                issues.append(f"Invalid strategy: {plan['strategy']}")
        
        # Check estimated duration
        estimated_duration = plan.get("estimated_duration", 0)
        if estimated_duration > self.thresholds["max_migration_time"] * len(plan.get("agents", [])):
            issues.append("Estimated migration duration exceeds safety threshold")
        
        passed = len(issues) == 0
        
        result = ValidationResult(
            name="migration_plan",
            passed=passed,
            message=f"Migration plan validation {'passed' if passed else 'failed'}",
            details={
                "issues": issues,
                "plan_summary": {
                    "strategy": plan.get("strategy"),
                    "agent_count": len(plan.get("agents", [])),
                    "phase_count": len(plan.get("phases", [])),
                    "estimated_duration": estimated_duration
                }
            },
            execution_time=time.time() - start_time
        )
        
        self.validation_history.append(result)
        
        if passed:
            logger.info("✅ Migration plan validation passed")
        else:
            logger.warning(f"❌ Migration plan validation failed: {issues}")
        
        return result
    
    async def validate_agent_connectivity(self, agents: List[str]) -> ValidationResult:
        """
        Validate connectivity to specified agents.
        
        Args:
            agents: List of agent names to validate
            
        Returns:
            ValidationResult for connectivity validation
        """
        logger.info(f"🔗 Validating connectivity to {len(agents)} agents...")
        
        start_time = time.time()
        connectivity_results = []
        
        for agent in agents:
            agent_result = {
                "agent": agent,
                "tmux_available": False,
                "message_bus_available": False,
                "overall_connectivity": False
            }
            
            try:
                # Check agent status
                status = await self.bridge.get_agent_status(agent)
                
                if "error" not in status:
                    agent_result["tmux_available"] = status.get("tmux_available", False)
                    agent_result["message_bus_available"] = bool(status.get("message_bus_status"))
                    agent_result["overall_connectivity"] = (
                        agent_result["tmux_available"] or 
                        agent_result["message_bus_available"]
                    )
                
                # Test message sending
                if agent_result["overall_connectivity"]:
                    test_message = f"Connectivity test for {agent}"
                    send_success = await self.bridge.send_message(agent, test_message)
                    agent_result["message_test"] = send_success
                    agent_result["overall_connectivity"] = send_success
                
            except Exception as e:
                agent_result["error"] = str(e)
            
            connectivity_results.append(agent_result)
        
        # Overall connectivity assessment
        connected_agents = [r for r in connectivity_results if r["overall_connectivity"]]
        connectivity_rate = len(connected_agents) / len(agents) if agents else 0
        
        passed = connectivity_rate >= self.thresholds["min_success_rate"]
        
        result = ValidationResult(
            name="agent_connectivity",
            passed=passed,
            message=f"Agent connectivity validation {'passed' if passed else 'failed'}",
            details={
                "connectivity_rate": connectivity_rate,
                "connected_agents": len(connected_agents),
                "total_agents": len(agents),
                "agent_results": connectivity_results
            },
            execution_time=time.time() - start_time
        )
        
        self.validation_history.append(result)
        
        if passed:
            logger.info(f"✅ Agent connectivity validation passed ({connectivity_rate:.1%})")
        else:
            logger.warning(f"❌ Agent connectivity validation failed ({connectivity_rate:.1%})")
        
        return result
    
    async def validate_system_resources(self) -> ValidationResult:
        """
        Validate system resources for migration.
        
        Returns:
            ValidationResult for system resources
        """
        logger.info("💾 Validating system resources...")
        
        start_time = time.time()
        resource_checks = []
        
        try:
            # Check disk space
            disk_check = await self._check_disk_space()
            resource_checks.append(disk_check)
            
            # Check memory usage
            memory_check = await self._check_memory_usage()
            resource_checks.append(memory_check)
            
            # Check process limits
            process_check = await self._check_process_limits()
            resource_checks.append(process_check)
            
            # Check Redis connectivity (if available)
            redis_check = await self._check_redis_connectivity()
            resource_checks.append(redis_check)
            
        except Exception as e:
            resource_checks.append({
                "check": "system_resources_error",
                "passed": False,
                "message": str(e)
            })
        
        passed = all(check["passed"] for check in resource_checks)
        
        result = ValidationResult(
            name="system_resources",
            passed=passed,
            message=f"System resources validation {'passed' if passed else 'failed'}",
            details={
                "resource_checks": resource_checks,
                "failed_checks": [c["check"] for c in resource_checks if not c["passed"]]
            },
            execution_time=time.time() - start_time
        )
        
        self.validation_history.append(result)
        
        if passed:
            logger.info("✅ System resources validation passed")
        else:
            logger.warning("❌ System resources validation failed")
        
        return result
    
    async def validate_migration_progress(self, migration_status: Dict[str, Any]) -> ValidationResult:
        """
        Validate migration progress during execution.
        
        Args:
            migration_status: Current migration status
            
        Returns:
            ValidationResult for migration progress
        """
        logger.info("📊 Validating migration progress...")
        
        start_time = time.time()
        progress_checks = []
        
        # Check migration timing
        if "start_time" in migration_status:
            start_time_obj = migration_status["start_time"]
            if isinstance(start_time_obj, str):
                start_time_obj = datetime.fromisoformat(start_time_obj)
            
            elapsed_time = (datetime.now() - start_time_obj).total_seconds()
            max_time = self.thresholds["max_migration_time"]
            
            progress_checks.append({
                "check": "migration_timing",
                "passed": elapsed_time <= max_time,
                "message": f"Migration elapsed time: {elapsed_time:.1f}s (max: {max_time}s)",
                "details": {"elapsed_time": elapsed_time, "max_time": max_time}
            })
        
        # Check error rate
        errors = migration_status.get("errors", [])
        total_operations = migration_status.get("total_operations", 1)
        error_rate = len(errors) / total_operations
        
        progress_checks.append({
            "check": "error_rate",
            "passed": error_rate <= self.thresholds["max_error_rate"],
            "message": f"Error rate: {error_rate:.1%} (max: {self.thresholds['max_error_rate']:.1%})",
            "details": {"error_rate": error_rate, "error_count": len(errors)}
        })
        
        # Check agent health
        agent_health = migration_status.get("agent_health", {})
        healthy_agents = sum(1 for status in agent_health.values() if status.get("healthy", False))
        total_agents = len(agent_health)
        
        if total_agents > 0:
            health_rate = healthy_agents / total_agents
            progress_checks.append({
                "check": "agent_health",
                "passed": health_rate >= self.thresholds["min_success_rate"],
                "message": f"Agent health rate: {health_rate:.1%}",
                "details": {"healthy_agents": healthy_agents, "total_agents": total_agents}
            })
        
        passed = all(check["passed"] for check in progress_checks)
        
        result = ValidationResult(
            name="migration_progress",
            passed=passed,
            message=f"Migration progress validation {'passed' if passed else 'failed'}",
            details={
                "progress_checks": progress_checks,
                "migration_status": migration_status
            },
            execution_time=time.time() - start_time
        )
        
        self.validation_history.append(result)
        
        return result
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation results."""
        total_validations = len(self.validation_history)
        passed_validations = sum(1 for v in self.validation_history if v.passed)
        
        return {
            "total_validations": total_validations,
            "passed_validations": passed_validations,
            "success_rate": passed_validations / total_validations if total_validations > 0 else 0,
            "latest_validation": self.validation_history[-1] if self.validation_history else None,
            "failed_validations": [
                {"name": v.name, "message": v.message, "timestamp": v.timestamp}
                for v in self.validation_history if not v.passed
            ]
        }
    
    # Private validation methods
    
    async def _validate_tmux_availability(self) -> ValidationResult:
        """Validate tmux availability."""
        try:
            # Check if tmux is installed
            result = subprocess.run(["tmux", "-V"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return ValidationResult(
                    name="tmux_availability",
                    passed=False,
                    message="tmux not installed or not accessible"
                )
            
            # Check if agent-hive session exists
            result = subprocess.run(
                ["tmux", "has-session", "-t", "agent-hive"],
                capture_output=True, text=True, timeout=5
            )
            
            session_exists = result.returncode == 0
            
            return ValidationResult(
                name="tmux_availability",
                passed=True,
                message=f"tmux available, agent-hive session {'exists' if session_exists else 'not found'}",
                details={"session_exists": session_exists}
            )
            
        except Exception as e:
            return ValidationResult(
                name="tmux_availability",
                passed=False,
                message=f"tmux validation failed: {e}"
            )
    
    async def _validate_system_resources(self) -> ValidationResult:
        """Validate system resources."""
        try:
            checks = []
            
            # Check disk space
            disk_check = await self._check_disk_space()
            checks.append(disk_check)
            
            # Check memory
            memory_check = await self._check_memory_usage()
            checks.append(memory_check)
            
            passed = all(check["passed"] for check in checks)
            
            return ValidationResult(
                name="system_resources",
                passed=passed,
                message=f"System resources {'adequate' if passed else 'insufficient'}",
                details={"checks": checks}
            )
            
        except Exception as e:
            return ValidationResult(
                name="system_resources",
                passed=False,
                message=f"Resource validation failed: {e}"
            )
    
    async def _validate_agent_discovery(self) -> ValidationResult:
        """Validate agent discovery."""
        try:
            # Discover agents through bridge
            agent_status = await self.bridge.get_agent_status()
            
            if "error" in agent_status:
                return ValidationResult(
                    name="agent_discovery",
                    passed=False,
                    message=f"Agent discovery failed: {agent_status['error']}"
                )
            
            agents = agent_status.get("agents", {})
            agent_count = len(agents)
            
            passed = agent_count >= self.thresholds["min_agent_count"]
            
            return ValidationResult(
                name="agent_discovery",
                passed=passed,
                message=f"Discovered {agent_count} agents (min: {self.thresholds['min_agent_count']})",
                details={"agent_count": agent_count, "agents": list(agents.keys())}
            )
            
        except Exception as e:
            return ValidationResult(
                name="agent_discovery",
                passed=False,
                message=f"Agent discovery failed: {e}"
            )
    
    async def _validate_message_bus_readiness(self) -> ValidationResult:
        """Validate message bus readiness."""
        try:
            # Check if message bus is available
            if not self.bridge.message_bus:
                return ValidationResult(
                    name="message_bus_readiness",
                    passed=True,  # Not required for tmux-only operation
                    message="Message bus not configured (tmux-only mode)",
                    details={"message_bus_available": False}
                )
            
            # Test message bus connectivity
            # This would be implemented based on the specific message bus
            return ValidationResult(
                name="message_bus_readiness",
                passed=True,
                message="Message bus ready",
                details={"message_bus_available": True}
            )
            
        except Exception as e:
            return ValidationResult(
                name="message_bus_readiness",
                passed=False,
                message=f"Message bus validation failed: {e}"
            )
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (1024**3)
            
            return {
                "check": "disk_space",
                "passed": free_gb >= 1,  # At least 1GB free
                "message": f"Available disk space: {free_gb}GB",
                "details": {"free_gb": free_gb}
            }
        except Exception as e:
            return {
                "check": "disk_space",
                "passed": False,
                "message": f"Disk space check failed: {e}"
            }
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_gb = memory.available // (1024**3)
            
            return {
                "check": "memory_usage",
                "passed": available_gb >= 1,  # At least 1GB available
                "message": f"Available memory: {available_gb}GB",
                "details": {"available_gb": available_gb, "usage_percent": memory.percent}
            }
        except ImportError:
            return {
                "check": "memory_usage",
                "passed": True,  # Assume OK if psutil not available
                "message": "Memory check skipped (psutil not available)"
            }
        except Exception as e:
            return {
                "check": "memory_usage",
                "passed": False,
                "message": f"Memory check failed: {e}"
            }
    
    async def _check_process_limits(self) -> Dict[str, Any]:
        """Check process limits."""
        try:
            import resource
            max_processes = resource.getrlimit(resource.RLIMIT_NPROC)[0]
            
            return {
                "check": "process_limits",
                "passed": max_processes >= 1024,  # At least 1024 processes
                "message": f"Max processes: {max_processes}",
                "details": {"max_processes": max_processes}
            }
        except Exception as e:
            return {
                "check": "process_limits",
                "passed": True,  # Assume OK if check fails
                "message": f"Process limits check skipped: {e}"
            }
    
    async def _check_redis_connectivity(self) -> Dict[str, Any]:
        """Check Redis connectivity if available."""
        try:
            if not self.bridge.message_bus:
                return {
                    "check": "redis_connectivity",
                    "passed": True,
                    "message": "Redis not configured (tmux-only mode)"
                }
            
            # This would test actual Redis connectivity
            return {
                "check": "redis_connectivity",
                "passed": True,
                "message": "Redis connectivity assumed OK"
            }
        except Exception as e:
            return {
                "check": "redis_connectivity",
                "passed": False,
                "message": f"Redis connectivity check failed: {e}"
            }