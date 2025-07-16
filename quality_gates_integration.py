#!/usr/bin/env python3
"""
Quality Gates Integration for Monitoring System
Foundation Epic Phase 1: System monitoring and health validation

Integrates monitoring health validation with quality gates enforcement
to ensure system reliability and performance standards.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from monitoring_health_validation import health_validator, HealthStatus

logger = logging.getLogger(__name__)


class QualityGatesMonitoringIntegration:
    """Integrates monitoring with quality gates enforcement."""
    
    def __init__(self, quality_gates_path: str = ".quality-gates.json"):
        self.quality_gates_path = quality_gates_path
        self.quality_gates = self._load_quality_gates()
        
    def _load_quality_gates(self) -> Dict[str, Any]:
        """Load quality gates configuration."""
        try:
            with open(self.quality_gates_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Quality gates file not found: {self.quality_gates_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid quality gates JSON: {e}")
            return {}
    
    async def validate_system_quality_gates(self) -> Dict[str, Any]:
        """Validate system against quality gates using monitoring data."""
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "gates_passed": 0,
            "gates_total": 0,
            "gate_results": {}
        }
        
        if not self.quality_gates:
            validation_results["error"] = "No quality gates configuration found"
            return validation_results
        
        # Get current system health
        health_report = await health_validator.get_system_health()
        
        # Validate performance requirements
        performance_result = await self._validate_performance_gates(health_report)
        validation_results["gate_results"]["performance"] = performance_result
        
        # Validate monitoring requirements
        monitoring_result = await self._validate_monitoring_gates(health_report)
        validation_results["gate_results"]["monitoring"] = monitoring_result
        
        # Validate system health requirements
        health_result = await self._validate_health_gates(health_report)
        validation_results["gate_results"]["system_health"] = health_result
        
        # Calculate overall results
        passed_gates = sum(1 for result in validation_results["gate_results"].values() if result["passed"])
        total_gates = len(validation_results["gate_results"])
        
        validation_results["gates_passed"] = passed_gates
        validation_results["gates_total"] = total_gates
        validation_results["overall_status"] = "passed" if passed_gates == total_gates else "failed"
        
        return validation_results
    
    async def _validate_performance_gates(self, health_report) -> Dict[str, Any]:
        """Validate performance-related quality gates."""
        gate_result = {
            "gate_name": "performance_check",
            "required": self.quality_gates.get("quality_gates", {}).get("required_performance_check", True),
            "passed": False,
            "checks": {},
            "message": ""
        }
        
        if not gate_result["required"]:
            gate_result["passed"] = True
            gate_result["message"] = "Performance check not required"
            return gate_result
        
        checks = gate_result["checks"]
        
        # Check system health score
        health_threshold = 0.7  # 70% minimum health score
        checks["system_health_score"] = {
            "value": health_report.overall_score,
            "threshold": health_threshold,
            "passed": health_report.overall_score >= health_threshold
        }
        
        # Check for critical alerts
        critical_alerts = [a for a in health_report.active_alerts if a.get("level") == "critical"]
        checks["no_critical_alerts"] = {
            "value": len(critical_alerts),
            "threshold": 0,
            "passed": len(critical_alerts) == 0
        }
        
        # Check monitoring systems are active
        monitoring_validation = await health_validator.validate_monitoring_systems()
        active_systems = sum(1 for system in monitoring_validation.values() 
                           if system.get("status") == "healthy")
        total_systems = len(monitoring_validation)
        
        checks["monitoring_systems_active"] = {
            "value": f"{active_systems}/{total_systems}",
            "threshold": "3/3",
            "passed": active_systems == total_systems
        }
        
        # Overall performance gate result
        all_checks_passed = all(check["passed"] for check in checks.values())
        gate_result["passed"] = all_checks_passed
        
        if all_checks_passed:
            gate_result["message"] = "All performance checks passed"
        else:
            failed_checks = [name for name, check in checks.items() if not check["passed"]]
            gate_result["message"] = f"Failed checks: {', '.join(failed_checks)}"
        
        return gate_result
    
    async def _validate_monitoring_gates(self, health_report) -> Dict[str, Any]:
        """Validate monitoring-specific quality gates."""
        gate_result = {
            "gate_name": "monitoring_validation",
            "required": True,  # Always required for monitoring agent
            "passed": False,
            "checks": {},
            "message": ""
        }
        
        checks = gate_result["checks"]
        
        # Check baseline metrics collection
        baseline_component = next(
            (c for c in health_report.component_health if c.component_name == "baseline_metrics"),
            None
        )
        checks["baseline_metrics_active"] = {
            "value": baseline_component.status.value if baseline_component else "unknown",
            "threshold": "healthy",
            "passed": baseline_component and baseline_component.status.value in ["healthy", "warning"]
        }
        
        # Check hook manager
        hook_component = next(
            (c for c in health_report.component_health if c.component_name == "hook_manager"),
            None
        )
        checks["hook_manager_active"] = {
            "value": hook_component.status.value if hook_component else "unknown",
            "threshold": "healthy",
            "passed": hook_component and hook_component.status.value == "healthy"
        }
        
        # Check performance monitoring
        perf_component = next(
            (c for c in health_report.component_health if c.component_name == "performance_monitoring"),
            None
        )
        checks["performance_monitoring_active"] = {
            "value": perf_component.status.value if perf_component else "unknown",
            "threshold": "healthy",
            "passed": perf_component and perf_component.status.value == "healthy"
        }
        
        # Check metrics collection rate
        if baseline_component and baseline_component.metrics:
            metrics_collected = baseline_component.metrics.get("metrics_collected", 0)
            checks["metrics_collection_rate"] = {
                "value": metrics_collected,
                "threshold": 5,  # Minimum 5 metrics collected
                "passed": metrics_collected >= 5
            }
        
        # Overall monitoring gate result
        all_checks_passed = all(check["passed"] for check in checks.values())
        gate_result["passed"] = all_checks_passed
        
        if all_checks_passed:
            gate_result["message"] = "All monitoring checks passed"
        else:
            failed_checks = [name for name, check in checks.items() if not check["passed"]]
            gate_result["message"] = f"Failed checks: {', '.join(failed_checks)}"
        
        return gate_result
    
    async def _validate_health_gates(self, health_report) -> Dict[str, Any]:
        """Validate system health quality gates."""
        gate_result = {
            "gate_name": "system_health",
            "required": True,
            "passed": False,
            "checks": {},
            "message": ""
        }
        
        checks = gate_result["checks"]
        
        # Check overall system status
        checks["overall_status_acceptable"] = {
            "value": health_report.overall_status.value,
            "threshold": "not critical",
            "passed": health_report.overall_status.value != "critical"
        }
        
        # Check component health
        critical_components = [
            c.component_name for c in health_report.component_health 
            if c.status.value == "critical"
        ]
        checks["no_critical_components"] = {
            "value": len(critical_components),
            "threshold": 0,
            "passed": len(critical_components) == 0
        }
        
        # Check system resources
        resource_component = next(
            (c for c in health_report.component_health if c.component_name == "system_resources"),
            None
        )
        if resource_component:
            checks["system_resources_healthy"] = {
                "value": resource_component.status.value,
                "threshold": "not critical",
                "passed": resource_component.status.value != "critical"
            }
        
        # Check recommendations don't include critical issues
        critical_recommendations = [
            rec for rec in health_report.recommendations 
            if rec.startswith("CRITICAL:")
        ]
        checks["no_critical_recommendations"] = {
            "value": len(critical_recommendations),
            "threshold": 0,
            "passed": len(critical_recommendations) == 0
        }
        
        # Overall health gate result
        all_checks_passed = all(check["passed"] for check in checks.values())
        gate_result["passed"] = all_checks_passed
        
        if all_checks_passed:
            gate_result["message"] = "All health checks passed"
        else:
            failed_checks = [name for name, check in checks.items() if not check["passed"]]
            gate_result["message"] = f"Failed checks: {', '.join(failed_checks)}"
        
        return gate_result
    
    async def generate_quality_gates_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality gates validation report."""
        validation_results = await self.validate_system_quality_gates()
        
        # Get detailed system information
        health_report = await health_validator.get_system_health()
        monitoring_validation = await health_validator.validate_monitoring_systems()
        
        report = {
            "report_metadata": {
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.quality_gates.get("agent_name", "monitoring"),
                "enforcement_level": self.quality_gates.get("enforcement_level", "strict")
            },
            "validation_results": validation_results,
            "system_health_summary": {
                "overall_status": health_report.overall_status.value,
                "overall_score": health_report.overall_score,
                "component_count": len(health_report.component_health),
                "active_alerts": len(health_report.active_alerts),
                "recommendations": len(health_report.recommendations)
            },
            "monitoring_systems_summary": monitoring_validation,
            "quality_gates_configuration": self.quality_gates
        }
        
        return report
    
    def should_block_deployment(self, validation_results: Dict[str, Any]) -> bool:
        """Determine if deployment should be blocked based on quality gates."""
        enforcement_level = self.quality_gates.get("enforcement_level", "strict")
        
        if enforcement_level == "strict":
            return validation_results["overall_status"] != "passed"
        elif enforcement_level == "warning":
            # Only block on critical failures
            critical_failures = []
            for gate_name, gate_result in validation_results["gate_results"].items():
                if not gate_result["passed"]:
                    # Check if any failed checks are critical
                    for check_name, check_result in gate_result.get("checks", {}).items():
                        if not check_result["passed"] and "critical" in check_name.lower():
                            critical_failures.append(f"{gate_name}.{check_name}")
            
            return len(critical_failures) > 0
        else:
            return False  # permissive mode


# Global instance
quality_gates_integration = QualityGatesMonitoringIntegration()


async def validate_quality_gates() -> Dict[str, Any]:
    """Validate system against quality gates."""
    return await quality_gates_integration.validate_system_quality_gates()


async def generate_quality_report() -> Dict[str, Any]:
    """Generate quality gates validation report."""
    return await quality_gates_integration.generate_quality_gates_report()


async def check_deployment_readiness() -> Dict[str, Any]:
    """Check if system is ready for deployment based on quality gates."""
    validation_results = await quality_gates_integration.validate_system_quality_gates()
    should_block = quality_gates_integration.should_block_deployment(validation_results)
    
    return {
        "deployment_ready": not should_block,
        "should_block_deployment": should_block,
        "validation_results": validation_results,
        "enforcement_level": quality_gates_integration.quality_gates.get("enforcement_level", "strict")
    }


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("Quality Gates Integration Validation")
        print("=" * 40)
        
        # Start monitoring
        await health_validator.start_monitoring()
        
        # Wait for metrics collection
        print("Collecting metrics for quality gates validation...")
        await asyncio.sleep(35)
        
        # Validate quality gates
        print("\nQuality Gates Validation:")
        validation_results = await validate_quality_gates()
        print(json.dumps(validation_results, indent=2))
        
        # Check deployment readiness
        print("\nDeployment Readiness Check:")
        deployment_check = await check_deployment_readiness()
        print(f"Deployment Ready: {deployment_check['deployment_ready']}")
        print(f"Should Block: {deployment_check['should_block_deployment']}")
        
        # Generate full report
        print("\nFull Quality Gates Report:")
        report = await generate_quality_report()
        print(f"Overall Status: {report['validation_results']['overall_status']}")
        print(f"Gates Passed: {report['validation_results']['gates_passed']}/{report['validation_results']['gates_total']}")
        
        # Stop monitoring
        await health_validator.stop_monitoring()
        
        print("\nQuality gates integration validation complete!")
    
    asyncio.run(main())