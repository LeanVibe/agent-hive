#!/usr/bin/env python3
"""
Quality Gates Framework
Foundation Epic Phase 1: Security and compliance enforcement

Provides automated quality gates enforcement with security validation
and deployment readiness checks for the agent orchestration system.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class EnforcementLevel(Enum):
    """Quality gates enforcement levels."""
    STRICT = "strict"
    WARNING = "warning"
    PERMISSIVE = "permissive"


class SecurityLevel(Enum):
    """Security validation levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QualityGate:
    """Individual quality gate configuration."""
    name: str
    description: str
    threshold: float
    enforcement_level: EnforcementLevel
    security_level: SecurityLevel
    required: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "threshold": self.threshold,
            "enforcement_level": self.enforcement_level.value,
            "security_level": self.security_level.value,
            "required": self.required
        }


@dataclass
class ValidationResult:
    """Quality gate validation result."""
    gate_name: str
    passed: bool
    value: float
    threshold: float
    message: str
    security_implications: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QualityGatesFramework:
    """Core quality gates framework with security enforcement."""
    
    def __init__(self, config_path: str = ".quality-gates.json"):
        self.config_path = config_path
        self.gates: Dict[str, QualityGate] = {}
        self.validation_history: List[Dict[str, Any]] = []
        self._initialize_default_gates()
        self._load_config()
    
    def _initialize_default_gates(self):
        """Initialize default quality gates."""
        self.gates = {
            "pr_size_limit": QualityGate(
                name="pr_size_limit",
                description="Pull request size must be under limit",
                threshold=1000.0,
                enforcement_level=EnforcementLevel.STRICT,
                security_level=SecurityLevel.MEDIUM
            ),
            "test_coverage": QualityGate(
                name="test_coverage",
                description="Test coverage must meet minimum threshold",
                threshold=85.0,
                enforcement_level=EnforcementLevel.STRICT,
                security_level=SecurityLevel.HIGH
            ),
            "security_scan": QualityGate(
                name="security_scan",
                description="Security scan must pass without critical issues",
                threshold=0.0,
                enforcement_level=EnforcementLevel.STRICT,
                security_level=SecurityLevel.HIGH
            ),
            "code_quality": QualityGate(
                name="code_quality",
                description="Code quality score must meet standards",
                threshold=8.0,
                enforcement_level=EnforcementLevel.WARNING,
                security_level=SecurityLevel.MEDIUM
            ),
            "performance_check": QualityGate(
                name="performance_check",
                description="Performance metrics must meet baseline",
                threshold=70.0,
                enforcement_level=EnforcementLevel.WARNING,
                security_level=SecurityLevel.LOW
            )
        }
    
    def _load_config(self):
        """Load quality gates configuration from file."""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self._update_gates_from_config(config)
        except Exception as e:
            logger.warning(f"Failed to load quality gates config: {e}")
            # Use defaults if config loading fails
    
    def _update_gates_from_config(self, config: Dict[str, Any]):
        """Update gates from configuration."""
        if "quality_gates" in config:
            gates_config = config["quality_gates"]
            
            # Update PR size limit
            if "max_pr_size" in gates_config:
                self.gates["pr_size_limit"].threshold = gates_config["max_pr_size"]
            
            # Update test coverage
            if "min_coverage" in gates_config:
                self.gates["test_coverage"].threshold = gates_config["min_coverage"]
            
            # Update enforcement level
            if "enforcement_level" in config:
                level = EnforcementLevel(config["enforcement_level"])
                for gate in self.gates.values():
                    gate.enforcement_level = level
    
    def validate_pr_size(self, line_count: int) -> ValidationResult:
        """Validate pull request size."""
        gate = self.gates["pr_size_limit"]
        passed = line_count <= gate.threshold
        
        security_implications = []
        if not passed:
            security_implications = [
                "Large PRs are harder to review thoroughly",
                "Increased risk of security vulnerabilities being missed",
                "Potential for introducing technical debt"
            ]
        
        return ValidationResult(
            gate_name=gate.name,
            passed=passed,
            value=line_count,
            threshold=gate.threshold,
            message=f"PR size: {line_count} lines (limit: {gate.threshold})",
            security_implications=security_implications
        )
    
    def validate_test_coverage(self, coverage_percent: float) -> ValidationResult:
        """Validate test coverage."""
        gate = self.gates["test_coverage"]
        passed = coverage_percent >= gate.threshold
        
        security_implications = []
        if not passed:
            security_implications = [
                "Insufficient test coverage increases security risk",
                "Untested code paths may contain vulnerabilities",
                "Regression risk for security-critical functionality"
            ]
        
        return ValidationResult(
            gate_name=gate.name,
            passed=passed,
            value=coverage_percent,
            threshold=gate.threshold,
            message=f"Test coverage: {coverage_percent}% (minimum: {gate.threshold}%)",
            security_implications=security_implications
        )
    
    def validate_security_scan(self, critical_issues: int) -> ValidationResult:
        """Validate security scan results."""
        gate = self.gates["security_scan"]
        passed = critical_issues <= gate.threshold
        
        security_implications = []
        if not passed:
            security_implications = [
                f"Critical security issues detected: {critical_issues}",
                "Must resolve all critical security vulnerabilities",
                "Deployment blocked until security issues resolved"
            ]
        
        return ValidationResult(
            gate_name=gate.name,
            passed=passed,
            value=critical_issues,
            threshold=gate.threshold,
            message=f"Security scan: {critical_issues} critical issues (max: {gate.threshold})",
            security_implications=security_implications
        )
    
    def validate_code_quality(self, quality_score: float) -> ValidationResult:
        """Validate code quality score."""
        gate = self.gates["code_quality"]
        passed = quality_score >= gate.threshold
        
        security_implications = []
        if not passed:
            security_implications = [
                "Poor code quality increases security risk",
                "Code maintainability affects security updates",
                "Technical debt may hide security issues"
            ]
        
        return ValidationResult(
            gate_name=gate.name,
            passed=passed,
            value=quality_score,
            threshold=gate.threshold,
            message=f"Code quality: {quality_score}/10 (minimum: {gate.threshold}/10)",
            security_implications=security_implications
        )
    
    def validate_performance(self, performance_score: float) -> ValidationResult:
        """Validate performance metrics."""
        gate = self.gates["performance_check"]
        passed = performance_score >= gate.threshold
        
        security_implications = []
        if not passed:
            security_implications = [
                "Performance degradation may indicate security issues",
                "Resource exhaustion attacks become more likely",
                "Monitoring effectiveness may be reduced"
            ]
        
        return ValidationResult(
            gate_name=gate.name,
            passed=passed,
            value=performance_score,
            threshold=gate.threshold,
            message=f"Performance: {performance_score}% (minimum: {gate.threshold}%)",
            security_implications=security_implications
        )
    
    def validate_all_gates(self, metrics: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """Validate all quality gates."""
        results = {}
        
        # Validate PR size
        if "pr_size" in metrics:
            results["pr_size_limit"] = self.validate_pr_size(metrics["pr_size"])
        
        # Validate test coverage
        if "test_coverage" in metrics:
            results["test_coverage"] = self.validate_test_coverage(metrics["test_coverage"])
        
        # Validate security scan
        if "security_critical_issues" in metrics:
            results["security_scan"] = self.validate_security_scan(metrics["security_critical_issues"])
        
        # Validate code quality
        if "code_quality_score" in metrics:
            results["code_quality"] = self.validate_code_quality(metrics["code_quality_score"])
        
        # Validate performance
        if "performance_score" in metrics:
            results["performance_check"] = self.validate_performance(metrics["performance_score"])
        
        return results
    
    def should_block_deployment(self, validation_results: Dict[str, ValidationResult]) -> bool:
        """Determine if deployment should be blocked."""
        for gate_name, result in validation_results.items():
            gate = self.gates.get(gate_name)
            if not gate:
                continue
            
            if not result.passed:
                if gate.enforcement_level == EnforcementLevel.STRICT:
                    return True
                elif gate.enforcement_level == EnforcementLevel.WARNING:
                    if gate.security_level == SecurityLevel.HIGH:
                        return True
        
        return False
    
    def get_security_summary(self, validation_results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get security-focused summary of validation results."""
        security_issues = []
        high_risk_failures = []
        
        for result in validation_results.values():
            if not result.passed:
                gate = self.gates.get(result.gate_name)
                if gate and gate.security_level == SecurityLevel.HIGH:
                    high_risk_failures.append(result.gate_name)
                
                security_issues.extend(result.security_implications)
        
        return {
            "high_risk_failures": high_risk_failures,
            "security_issues": security_issues,
            "deployment_blocked": self.should_block_deployment(validation_results),
            "security_score": self._calculate_security_score(validation_results)
        }
    
    def _calculate_security_score(self, validation_results: Dict[str, ValidationResult]) -> float:
        """Calculate overall security score."""
        if not validation_results:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for result in validation_results.values():
            gate = self.gates.get(result.gate_name)
            if not gate:
                continue
            
            # Weight by security level
            weight = {
                SecurityLevel.HIGH: 3.0,
                SecurityLevel.MEDIUM: 2.0,
                SecurityLevel.LOW: 1.0
            }[gate.security_level]
            
            score = 100.0 if result.passed else 0.0
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def generate_compliance_report(self, validation_results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        passed_gates = sum(1 for r in validation_results.values() if r.passed)
        total_gates = len(validation_results)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "gates_passed": passed_gates,
            "gates_total": total_gates,
            "compliance_rate": (passed_gates / total_gates * 100) if total_gates > 0 else 0,
            "deployment_ready": not self.should_block_deployment(validation_results),
            "security_summary": self.get_security_summary(validation_results),
            "validation_results": {k: v.to_dict() for k, v in validation_results.items()},
            "gates_configuration": {k: v.to_dict() for k, v in self.gates.items()}
        }


# Global framework instance
quality_gates = QualityGatesFramework()


def validate_deployment_readiness(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Validate deployment readiness with security checks."""
    validation_results = quality_gates.validate_all_gates(metrics)
    return quality_gates.generate_compliance_report(validation_results)


def check_security_compliance(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Check security compliance specifically."""
    validation_results = quality_gates.validate_all_gates(metrics)
    return quality_gates.get_security_summary(validation_results)


if __name__ == "__main__":
    # Example usage
    test_metrics = {
        "pr_size": 850,
        "test_coverage": 88.5,
        "security_critical_issues": 0,
        "code_quality_score": 8.2,
        "performance_score": 75.0
    }
    
    print("Quality Gates Framework - Security Compliance Test")
    print("=" * 50)
    
    # Test validation
    report = validate_deployment_readiness(test_metrics)
    print(f"Compliance Rate: {report['compliance_rate']:.1f}%")
    print(f"Deployment Ready: {report['deployment_ready']}")
    print(f"Security Score: {report['security_summary']['security_score']:.1f}")
    
    # Test security compliance
    security_summary = check_security_compliance(test_metrics)
    print(f"High Risk Failures: {len(security_summary['high_risk_failures'])}")
    print(f"Security Issues: {len(security_summary['security_issues'])}")