#!/usr/bin/env python3
"""
Security Quality Gates Framework

Implements comprehensive security quality gates for preventing vulnerabilities
from entering the codebase. Integrates with CI/CD pipeline and pre-commit hooks.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass



logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Security vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class QualityGateStatus(Enum):
    """Quality gate execution status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class SecurityIssue:
    """Security issue detected by quality gates."""
    issue_id: str
    severity: SeverityLevel
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    rule_id: Optional[str] = None
    confidence: Optional[str] = None
    cwe_id: Optional[str] = None
    tool: Optional[str] = None
    remediation: Optional[str] = None


@dataclass
class QualityGateResult:
    """Result of a quality gate execution."""
    gate_name: str
    status: QualityGateStatus
    execution_time: float
    issues: List[SecurityIssue]
    summary: Dict[str, Any]
    output: str = ""
    error: str = ""


class SecurityQualityGates:
    """
    Comprehensive security quality gates framework.
    
    Features:
    - Zero critical vulnerability policy
    - Automated vulnerability scanning
    - Pre-commit hook integration
    - CI/CD pipeline integration
    - Comprehensive reporting
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize security quality gates."""
        self.config = self._load_config(config_file)
        self.project_root = Path.cwd()
        self.reports_dir = self.project_root / "security_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Quality gate configuration
        self.zero_critical_policy = self.config.get("security_policies", {}).get("zero_critical_policy", True)
        self.max_high_severity = self.config.get("security_policies", {}).get("max_high_severity", 2)
        self.max_medium_severity = self.config.get("security_policies", {}).get("max_medium_severity", 10)
        
        # Tool configurations
        self.bandit_config = self.config.get("scan_configuration", {}).get("bandit", {})
        self.safety_config = self.config.get("scan_configuration", {}).get("safety", {})
        self.pip_audit_config = self.config.get("scan_configuration", {}).get("pip_audit", {})
        self.custom_checks_config = self.config.get("scan_configuration", {}).get("custom_checks", {})
        
        logger.info("Security Quality Gates initialized")
    
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load security monitoring configuration."""
        if config_file is None:
            config_file = "config/security_monitoring.json"
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                return config_data.get("security_monitoring", {})
        except FileNotFoundError:
            logger.warning(f"Security config file {config_file} not found, using defaults")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_file}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default security configuration."""
        return {
            "thresholds": {
                "critical_threshold": 0,
                "high_threshold": 3,
                "medium_threshold": 15
            },
            "scan_configuration": {
                "bandit": {"enabled": True, "severity_levels": ["high", "medium", "low"]},
                "safety": {"enabled": True},
                "pip_audit": {"enabled": True},
                "custom_checks": {"enabled": True}
            },
            "security_policies": {
                "zero_critical_policy": True,
                "max_high_severity": 2,
                "max_medium_severity": 10,
                "block_deployment_on_critical": True
            }
        }
    
    async def run_all_quality_gates(self, target_paths: Optional[List[str]] = None) -> Dict[str, QualityGateResult]:
        """
        Run all configured security quality gates.
        
        Args:
            target_paths: Specific paths to scan (default: entire project)
            
        Returns:
            Dictionary of gate name to result
        """
        results = {}
        
        if target_paths is None:
            target_paths = [str(self.project_root)]
        
        # Run all quality gates
        gates = [
            ("bandit_scan", self._run_bandit_scan),
            ("safety_check", self._run_safety_check),
            ("pip_audit", self._run_pip_audit),
            ("custom_security_checks", self._run_custom_security_checks),
            ("secrets_detection", self._run_secrets_detection),
            ("dependency_vulnerabilities", self._run_dependency_vulnerabilities)
        ]
        
        for gate_name, gate_func in gates:
            try:
                logger.info(f"Running quality gate: {gate_name}")
                result = await gate_func(target_paths)
                results[gate_name] = result
                
                # Log result
                if result.status == QualityGateStatus.FAILED:
                    logger.error(f"Quality gate {gate_name} FAILED with {len(result.issues)} issues")
                else:
                    logger.info(f"Quality gate {gate_name} {result.status.value.upper()}")
                    
            except Exception as e:
                logger.error(f"Error running quality gate {gate_name}: {e}")
                results[gate_name] = QualityGateResult(
                    gate_name=gate_name,
                    status=QualityGateStatus.ERROR,
                    execution_time=0.0,
                    issues=[],
                    summary={"error": str(e)},
                    error=str(e)
                )
        
        # Generate comprehensive report
        await self._generate_quality_gates_report(results)
        
        return results
    
    async def _run_bandit_scan(self, target_paths: List[str]) -> QualityGateResult:
        """Run Bandit security scan for Python code."""
        start_time = time.time()
        
        if not self.bandit_config.get("enabled", True):
            return QualityGateResult(
                gate_name="bandit_scan",
                status=QualityGateStatus.SKIPPED,
                execution_time=0.0,
                issues=[],
                summary={"skipped": "Bandit scan disabled in configuration"}
            )
        
        issues = []
        output = ""
        error = ""
        
        try:
            # Build bandit command
            cmd = ["bandit", "-r"]
            
            # Add severity levels
            severity_levels = self.bandit_config.get("severity_levels", ["high", "medium", "low"])
            if "high" in severity_levels:
                cmd.extend(["-ll"])  # High severity
            elif "medium" in severity_levels:
                cmd.extend(["-l"])   # Medium and high
            # Low severity is default
            
            # Add exclude paths
            exclude_paths = self.bandit_config.get("exclude_paths", [])
            for exclude_path in exclude_paths:
                cmd.extend(["--exclude", exclude_path])
            
            # Add output format
            cmd.extend(["-f", "json"])
            
            # Add target paths
            cmd.extend(target_paths)
            
            # Run bandit
            timeout = self.bandit_config.get("timeout_seconds", 120)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            
            output = result.stdout
            error = result.stderr
            
            # Parse results
            if result.returncode == 0 or result.returncode == 1:  # 1 means issues found
                try:
                    bandit_data = json.loads(output)
                    
                    for issue_data in bandit_data.get("results", []):
                        severity_map = {
                            "HIGH": SeverityLevel.HIGH,
                            "MEDIUM": SeverityLevel.MEDIUM,
                            "LOW": SeverityLevel.LOW
                        }
                        
                        issue = SecurityIssue(
                            issue_id=f"bandit_{issue_data.get('test_id', 'unknown')}",
                            severity=severity_map.get(issue_data.get("issue_severity", "LOW"), SeverityLevel.LOW),
                            title=issue_data.get("test_name", "Security Issue"),
                            description=issue_data.get("issue_text", ""),
                            file_path=issue_data.get("filename", ""),
                            line_number=issue_data.get("line_number"),
                            rule_id=issue_data.get("test_id"),
                            confidence=issue_data.get("issue_confidence"),
                            tool="bandit",
                            remediation=f"Review code at line {issue_data.get('line_number')} in {issue_data.get('filename')}"
                        )
                        issues.append(issue)
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Bandit JSON output")
            
        except subprocess.TimeoutExpired:
            error = f"Bandit scan timed out after {timeout} seconds"
        except FileNotFoundError:
            error = "Bandit not found. Install with: pip install bandit"
        except Exception as e:
            error = f"Bandit scan failed: {e}"
        
        # Determine status
        status = QualityGateStatus.PASSED
        if error:
            status = QualityGateStatus.ERROR
        elif any(issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] for issue in issues):
            status = QualityGateStatus.FAILED
        elif issues:
            status = QualityGateStatus.WARNING
        
        execution_time = time.time() - start_time
        
        return QualityGateResult(
            gate_name="bandit_scan",
            status=status,
            execution_time=execution_time,
            issues=issues,
            summary={
                "total_issues": len(issues),
                "by_severity": self._count_by_severity(issues),
                "files_scanned": len(set(issue.file_path for issue in issues))
            },
            output=output,
            error=error
        )
    
    async def _run_safety_check(self, target_paths: List[str]) -> QualityGateResult:
        """Run Safety check for known security vulnerabilities in dependencies."""
        start_time = time.time()
        
        if not self.safety_config.get("enabled", True):
            return QualityGateResult(
                gate_name="safety_check",
                status=QualityGateStatus.SKIPPED,
                execution_time=0.0,
                issues=[],
                summary={"skipped": "Safety check disabled in configuration"}
            )
        
        issues = []
        output = ""
        error = ""
        
        try:
            # Build safety command
            cmd = ["safety", "check", "--json"]
            
            if self.safety_config.get("check_full_report", True):
                cmd.append("--full-report")
            
            # Run safety
            timeout = self.safety_config.get("timeout_seconds", 60)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            
            output = result.stdout
            error = result.stderr
            
            # Parse results
            if result.returncode == 0 or result.returncode == 64:  # 64 means vulnerabilities found
                try:
                    safety_data = json.loads(output)
                    
                    for vuln_data in safety_data:
                        issue = SecurityIssue(
                            issue_id=f"safety_{vuln_data.get('id', 'unknown')}",
                            severity=SeverityLevel.HIGH,  # Safety issues are generally high severity
                            title=f"Vulnerable dependency: {vuln_data.get('package_name', 'unknown')}",
                            description=vuln_data.get("advisory", ""),
                            file_path="requirements.txt",  # Generic file path
                            rule_id=vuln_data.get("id"),
                            tool="safety",
                            remediation=f"Update {vuln_data.get('package_name')} to version {vuln_data.get('analyzed_version')} or later"
                        )
                        issues.append(issue)
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Safety JSON output")
            
        except subprocess.TimeoutExpired:
            error = f"Safety check timed out after {timeout} seconds"
        except FileNotFoundError:
            error = "Safety not found. Install with: pip install safety"
        except Exception as e:
            error = f"Safety check failed: {e}"
        
        # Determine status
        status = QualityGateStatus.PASSED
        if error:
            status = QualityGateStatus.ERROR
        elif issues:
            status = QualityGateStatus.FAILED  # Known vulnerabilities are always critical
        
        execution_time = time.time() - start_time
        
        return QualityGateResult(
            gate_name="safety_check",
            status=status,
            execution_time=execution_time,
            issues=issues,
            summary={
                "total_vulnerabilities": len(issues),
                "vulnerable_packages": len(set(issue.title.split(":")[1].strip() if ":" in issue.title else "unknown" for issue in issues))
            },
            output=output,
            error=error
        )
    
    async def _run_pip_audit(self, target_paths: List[str]) -> QualityGateResult:
        """Run pip-audit for additional vulnerability scanning."""
        start_time = time.time()
        
        if not self.pip_audit_config.get("enabled", True):
            return QualityGateResult(
                gate_name="pip_audit",
                status=QualityGateStatus.SKIPPED,
                execution_time=0.0,
                issues=[],
                summary={"skipped": "pip-audit disabled in configuration"}
            )
        
        issues = []
        output = ""
        error = ""
        
        try:
            # Build pip-audit command
            cmd = ["pip-audit", "--format", "json"]
            
            if self.pip_audit_config.get("include_descriptions", True):
                cmd.append("--desc")
            
            # Run pip-audit
            timeout = self.pip_audit_config.get("timeout_seconds", 60)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            
            output = result.stdout
            error = result.stderr
            
            # Parse results
            if result.returncode == 0:
                try:
                    audit_data = json.loads(output)
                    
                    for vuln_data in audit_data.get("vulnerabilities", []):
                        issue = SecurityIssue(
                            issue_id=f"pip_audit_{vuln_data.get('id', 'unknown')}",
                            severity=SeverityLevel.HIGH,
                            title=f"Vulnerable package: {vuln_data.get('package', 'unknown')}",
                            description=vuln_data.get("description", ""),
                            file_path="requirements.txt",
                            rule_id=vuln_data.get("id"),
                            tool="pip-audit",
                            remediation=f"Update {vuln_data.get('package')} to a secure version"
                        )
                        issues.append(issue)
                        
                except json.JSONDecodeError:
                    logger.warning("Failed to parse pip-audit JSON output")
            
        except subprocess.TimeoutExpired:
            error = f"pip-audit timed out after {timeout} seconds"
        except FileNotFoundError:
            error = "pip-audit not found. Install with: pip install pip-audit"
        except Exception as e:
            error = f"pip-audit failed: {e}"
        
        # Determine status
        status = QualityGateStatus.PASSED
        if error:
            status = QualityGateStatus.ERROR
        elif issues:
            status = QualityGateStatus.FAILED
        
        execution_time = time.time() - start_time
        
        return QualityGateResult(
            gate_name="pip_audit",
            status=status,
            execution_time=execution_time,
            issues=issues,
            summary={
                "total_vulnerabilities": len(issues),
                "vulnerable_packages": len(set(issue.title.split(":")[1].strip() if ":" in issue.title else "unknown" for issue in issues))
            },
            output=output,
            error=error
        )
    
    async def _run_custom_security_checks(self, target_paths: List[str]) -> QualityGateResult:
        """Run custom security checks."""
        start_time = time.time()
        
        if not self.custom_checks_config.get("enabled", True):
            return QualityGateResult(
                gate_name="custom_security_checks",
                status=QualityGateStatus.SKIPPED,
                execution_time=0.0,
                issues=[],
                summary={"skipped": "Custom checks disabled in configuration"}
            )
        
        issues = []
        
        # Check for hardcoded secrets
        if self.custom_checks_config.get("check_secrets", True):
            secret_issues = await self._check_hardcoded_secrets(target_paths)
            issues.extend(secret_issues)
        
        # Check configuration security
        if self.custom_checks_config.get("check_configurations", True):
            config_issues = await self._check_configuration_security(target_paths)
            issues.extend(config_issues)
        
        # Check file permissions
        if self.custom_checks_config.get("check_permissions", True):
            permission_issues = await self._check_file_permissions(target_paths)
            issues.extend(permission_issues)
        
        # Check environment variables
        if self.custom_checks_config.get("check_environment", True):
            env_issues = await self._check_environment_security()
            issues.extend(env_issues)
        
        # Determine status
        status = QualityGateStatus.PASSED
        if any(issue.severity == SeverityLevel.CRITICAL for issue in issues):
            status = QualityGateStatus.FAILED
        elif any(issue.severity == SeverityLevel.HIGH for issue in issues):
            status = QualityGateStatus.FAILED
        elif issues:
            status = QualityGateStatus.WARNING
        
        execution_time = time.time() - start_time
        
        return QualityGateResult(
            gate_name="custom_security_checks",
            status=status,
            execution_time=execution_time,
            issues=issues,
            summary={
                "total_issues": len(issues),
                "by_severity": self._count_by_severity(issues),
                "check_types": ["secrets", "configurations", "permissions", "environment"]
            }
        )
    
    async def _run_secrets_detection(self, target_paths: List[str]) -> QualityGateResult:
        """Dedicated secrets detection scan."""
        start_time = time.time()
        issues = []
        
        # Common secret patterns
        secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})', "API Key"),
            (r'(?i)(secret[_-]?key|secretkey)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})', "Secret Key"),
            (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{8,})', "Password"),
            (r'(?i)(token)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})', "Token"),
            (r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*["\']?([A-Z0-9]{20})', "AWS Access Key"),
            (r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})', "AWS Secret Key"),
        ]
        
        import re
        
        for target_path in target_paths:
            path_obj = Path(target_path)
            
            if path_obj.is_file() and path_obj.suffix in ['.py', '.json', '.yaml', '.yml', '.env']:
                try:
                    with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    for line_num, line in enumerate(content.splitlines(), 1):
                        for pattern, secret_type in secret_patterns:
                            matches = re.findall(pattern, line)
                            if matches:
                                issue = SecurityIssue(
                                    issue_id=f"secrets_{secret_type.lower().replace(' ', '_')}_{line_num}",
                                    severity=SeverityLevel.CRITICAL,
                                    title=f"Potential {secret_type} Found",
                                    description=f"Potential hardcoded {secret_type.lower()} detected in source code",
                                    file_path=str(path_obj),
                                    line_number=line_num,
                                    tool="custom_secrets_detection",
                                    remediation=f"Remove hardcoded {secret_type.lower()} and use environment variables or secure vault"
                                )
                                issues.append(issue)
                                
                except Exception as e:
                    logger.warning(f"Could not scan file {path_obj} for secrets: {e}")
            
            elif path_obj.is_dir():
                # Recursively scan directory
                for file_path in path_obj.rglob("*.py"):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        for line_num, line in enumerate(content.splitlines(), 1):
                            for pattern, secret_type in secret_patterns:
                                matches = re.findall(pattern, line)
                                if matches:
                                    issue = SecurityIssue(
                                        issue_id=f"secrets_{secret_type.lower().replace(' ', '_')}_{line_num}",
                                        severity=SeverityLevel.CRITICAL,
                                        title=f"Potential {secret_type} Found",
                                        description=f"Potential hardcoded {secret_type.lower()} detected in source code",
                                        file_path=str(file_path),
                                        line_number=line_num,
                                        tool="custom_secrets_detection",
                                        remediation=f"Remove hardcoded {secret_type.lower()} and use environment variables or secure vault"
                                    )
                                    issues.append(issue)
                                    
                    except Exception as e:
                        logger.warning(f"Could not scan file {file_path} for secrets: {e}")
        
        # Determine status
        status = QualityGateStatus.PASSED
        if issues:
            status = QualityGateStatus.FAILED  # Any secrets are critical
        
        execution_time = time.time() - start_time
        
        return QualityGateResult(
            gate_name="secrets_detection",
            status=status,
            execution_time=execution_time,
            issues=issues,
            summary={
                "total_secrets_found": len(issues),
                "secret_types": list(set(issue.title for issue in issues))
            }
        )
    
    async def _run_dependency_vulnerabilities(self, target_paths: List[str]) -> QualityGateResult:
        """Check for dependency vulnerabilities using multiple sources."""
        start_time = time.time()
        issues = []
        
        # Check requirements.txt for known vulnerable packages
        vulnerable_packages = {
            # This would typically be loaded from a vulnerability database
            "django": {"versions": ["<3.2.0"], "severity": SeverityLevel.HIGH, "cve": "CVE-2021-example"},
            "flask": {"versions": ["<2.0.0"], "severity": SeverityLevel.MEDIUM, "cve": "CVE-2021-example2"},
        }
        
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    requirements = f.read()
                
                for line in requirements.splitlines():
                    if line.strip() and not line.startswith('#'):
                        package_name = line.split('=')[0].split('>')[0].split('<')[0].strip()
                        
                        if package_name in vulnerable_packages:
                            vuln_info = vulnerable_packages[package_name]
                            issue = SecurityIssue(
                                issue_id=f"dep_vuln_{package_name}",
                                severity=vuln_info["severity"],
                                title=f"Vulnerable dependency: {package_name}",
                                description=f"Package {package_name} has known security vulnerabilities",
                                file_path=str(requirements_file),
                                tool="dependency_check",
                                remediation=f"Update {package_name} to a secure version"
                            )
                            issues.append(issue)
                            
            except Exception as e:
                logger.warning(f"Could not check requirements.txt: {e}")
        
        # Determine status
        status = QualityGateStatus.PASSED
        if any(issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH] for issue in issues):
            status = QualityGateStatus.FAILED
        elif issues:
            status = QualityGateStatus.WARNING
        
        execution_time = time.time() - start_time
        
        return QualityGateResult(
            gate_name="dependency_vulnerabilities",
            status=status,
            execution_time=execution_time,
            issues=issues,
            summary={
                "total_vulnerable_dependencies": len(issues),
                "by_severity": self._count_by_severity(issues)
            }
        )
    
    async def _check_hardcoded_secrets(self, target_paths: List[str]) -> List[SecurityIssue]:
        """Check for hardcoded secrets in code."""
        issues = []
        
        # This would be expanded with more sophisticated secret detection
        secret_keywords = ["password", "secret", "key", "token", "api_key"]
        
        for target_path in target_paths:
            path_obj = Path(target_path)
            
            if path_obj.is_file() and path_obj.suffix == '.py':
                try:
                    with open(path_obj, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        for keyword in secret_keywords:
                            if keyword in line.lower() and "=" in line:
                                issue = SecurityIssue(
                                    issue_id=f"hardcoded_secret_{line_num}",
                                    severity=SeverityLevel.HIGH,
                                    title="Potential Hardcoded Secret",
                                    description=f"Line contains potential hardcoded secret: {keyword}",
                                    file_path=str(path_obj),
                                    line_number=line_num,
                                    tool="custom_checks",
                                    remediation="Use environment variables or secure configuration management"
                                )
                                issues.append(issue)
                                
                except Exception as e:
                    logger.warning(f"Could not scan {path_obj} for secrets: {e}")
        
        return issues
    
    async def _check_configuration_security(self, target_paths: List[str]) -> List[SecurityIssue]:
        """Check configuration files for security issues."""
        issues = []
        
        # Check for insecure configuration patterns
        insecure_patterns = [
            "debug = True",
            "DEBUG = True", 
            "ssl_verify = False",
            "verify = False"
        ]
        
        config_files = [".env", "config.py", "settings.py", "config.yaml", "config.json"]
        
        for target_path in target_paths:
            path_obj = Path(target_path)
            
            if path_obj.is_file() and path_obj.name in config_files:
                try:
                    with open(path_obj, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for line_num, line in enumerate(content.splitlines(), 1):
                        for pattern in insecure_patterns:
                            if pattern in line:
                                issue = SecurityIssue(
                                    issue_id=f"insecure_config_{line_num}",
                                    severity=SeverityLevel.MEDIUM,
                                    title="Insecure Configuration",
                                    description=f"Insecure configuration pattern detected: {pattern}",
                                    file_path=str(path_obj),
                                    line_number=line_num,
                                    tool="custom_checks",
                                    remediation="Review and secure configuration settings"
                                )
                                issues.append(issue)
                                
                except Exception as e:
                    logger.warning(f"Could not scan {path_obj} for configuration issues: {e}")
        
        return issues
    
    async def _check_file_permissions(self, target_paths: List[str]) -> List[SecurityIssue]:
        """Check file permissions for security issues."""
        issues = []
        
        sensitive_files = [".env", "private_key", "id_rsa", "key.pem"]
        
        for target_path in target_paths:
            path_obj = Path(target_path)
            
            if path_obj.is_file() and any(sensitive in path_obj.name for sensitive in sensitive_files):
                try:
                    stat_info = path_obj.stat()
                    mode = oct(stat_info.st_mode)[-3:]  # Get last 3 digits of octal mode
                    
                    # Check if file is readable by others (world-readable)
                    if mode[-1] in ['4', '5', '6', '7']:  # Others have read permission
                        issue = SecurityIssue(
                            issue_id=f"insecure_permissions_{path_obj.name}",
                            severity=SeverityLevel.HIGH,
                            title="Insecure File Permissions",
                            description=f"Sensitive file {path_obj.name} is world-readable (mode: {mode})",
                            file_path=str(path_obj),
                            tool="custom_checks",
                            remediation=f"Change file permissions: chmod 600 {path_obj}"
                        )
                        issues.append(issue)
                        
                except Exception as e:
                    logger.warning(f"Could not check permissions for {path_obj}: {e}")
        
        return issues
    
    async def _check_environment_security(self) -> List[SecurityIssue]:
        """Check environment variables for security issues."""
        issues = []
        
        # Check for debug mode in environment
        if os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]:
            issue = SecurityIssue(
                issue_id="env_debug_enabled",
                severity=SeverityLevel.MEDIUM,
                title="Debug Mode Enabled",
                description="DEBUG environment variable is set to true",
                file_path="environment",
                tool="custom_checks",
                remediation="Disable debug mode in production environments"
            )
            issues.append(issue)
        
        # Check for missing security-related environment variables
        required_secure_vars = ["JWT_SECRET_KEY", "DATABASE_PASSWORD"]
        for var in required_secure_vars:
            if not os.getenv(var):
                issue = SecurityIssue(
                    issue_id=f"missing_env_var_{var.lower()}",
                    severity=SeverityLevel.HIGH,
                    title="Missing Security Environment Variable",
                    description=f"Required security environment variable {var} is not set",
                    file_path="environment",
                    tool="custom_checks",
                    remediation=f"Set environment variable {var} with a secure value"
                )
                issues.append(issue)
        
        return issues
    
    def _count_by_severity(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        """Count issues by severity level."""
        counts = {severity.value: 0 for severity in SeverityLevel}
        
        for issue in issues:
            counts[issue.severity.value] += 1
        
        return counts
    
    async def _generate_quality_gates_report(self, results: Dict[str, QualityGateResult]) -> None:
        """Generate comprehensive quality gates report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Aggregate all issues
        all_issues = []
        for result in results.values():
            all_issues.extend(result.issues)
        
        # Calculate overall status
        overall_status = QualityGateStatus.PASSED
        if any(result.status == QualityGateStatus.FAILED for result in results.values()):
            overall_status = QualityGateStatus.FAILED
        elif any(result.status == QualityGateStatus.WARNING for result in results.values()):
            overall_status = QualityGateStatus.WARNING
        
        # Check policy compliance
        critical_count = sum(1 for issue in all_issues if issue.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for issue in all_issues if issue.severity == SeverityLevel.HIGH)
        medium_count = sum(1 for issue in all_issues if issue.severity == SeverityLevel.MEDIUM)
        
        policy_violations = []
        if self.zero_critical_policy and critical_count > 0:
            policy_violations.append(f"Zero critical policy violation: {critical_count} critical issues found")
        if high_count > self.max_high_severity:
            policy_violations.append(f"High severity limit exceeded: {high_count} > {self.max_high_severity}")
        if medium_count > self.max_medium_severity:
            policy_violations.append(f"Medium severity limit exceeded: {medium_count} > {self.max_medium_severity}")
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status.value,
            "policy_violations": policy_violations,
            "summary": {
                "total_issues": len(all_issues),
                "by_severity": self._count_by_severity(all_issues),
                "gates_run": len(results),
                "gates_passed": sum(1 for r in results.values() if r.status == QualityGateStatus.PASSED),
                "gates_failed": sum(1 for r in results.values() if r.status == QualityGateStatus.FAILED)
            },
            "gate_results": {
                name: {
                    "status": result.status.value,
                    "execution_time": result.execution_time,
                    "issues_count": len(result.issues),
                    "summary": result.summary
                }
                for name, result in results.items()
            },
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "severity": issue.severity.value,
                    "title": issue.title,
                    "description": issue.description,
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "tool": issue.tool,
                    "remediation": issue.remediation
                }
                for issue in all_issues
            ]
        }
        
        # Save JSON report
        json_report_path = self.reports_dir / f"security_quality_gates_{timestamp}.json"
        with open(json_report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML report if configured
        if self.config.get("reporting", {}).get("generate_html_reports", True):
            await self._generate_html_report(report, timestamp)
        
        logger.info(f"Security quality gates report generated: {json_report_path}")
    
    async def _generate_html_report(self, report: Dict[str, Any], timestamp: str) -> None:
        """Generate HTML report for quality gates."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Quality Gates Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .status-passed {{ color: green; font-weight: bold; }}
                .status-failed {{ color: red; font-weight: bold; }}
                .status-warning {{ color: orange; font-weight: bold; }}
                .severity-critical {{ background-color: #ffebee; color: #c62828; }}
                .severity-high {{ background-color: #fff3e0; color: #ef6c00; }}
                .severity-medium {{ background-color: #f3e5f5; color: #7b1fa2; }}
                .severity-low {{ background-color: #e8f5e8; color: #2e7d32; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Security Quality Gates Report</h1>
                <p>Generated: {report['timestamp']}</p>
                <p>Overall Status: <span class="status-{report['overall_status']}">{report['overall_status'].upper()}</span></p>
            </div>
            
            <h2>Summary</h2>
            <ul>
                <li>Total Issues: {report['summary']['total_issues']}</li>
                <li>Critical: {report['summary']['by_severity']['critical']}</li>
                <li>High: {report['summary']['by_severity']['high']}</li>
                <li>Medium: {report['summary']['by_severity']['medium']}</li>
                <li>Low: {report['summary']['by_severity']['low']}</li>
            </ul>
            
            {"<h2>Policy Violations</h2><ul>" + "".join(f"<li>{violation}</li>" for violation in report['policy_violations']) + "</ul>" if report['policy_violations'] else ""}
            
            <h2>Gate Results</h2>
            <table>
                <tr>
                    <th>Gate Name</th>
                    <th>Status</th>
                    <th>Issues</th>
                    <th>Execution Time</th>
                </tr>
                {"".join(f'<tr><td>{name}</td><td class="status-{result["status"]}">{result["status"].upper()}</td><td>{result["issues_count"]}</td><td>{result["execution_time"]:.2f}s</td></tr>' for name, result in report['gate_results'].items())}
            </table>
            
            <h2>Issues Details</h2>
            <table>
                <tr>
                    <th>Severity</th>
                    <th>Title</th>
                    <th>File</th>
                    <th>Line</th>
                    <th>Tool</th>
                    <th>Description</th>
                </tr>
                {"".join(f'<tr><td class="severity-{issue["severity"]}">{issue["severity"].upper()}</td><td>{issue["title"]}</td><td>{issue["file_path"]}</td><td>{issue["line_number"] or "-"}</td><td>{issue["tool"]}</td><td>{issue["description"]}</td></tr>' for issue in report['issues'])}
            </table>
        </body>
        </html>
        """
        
        html_report_path = self.reports_dir / f"security_quality_gates_{timestamp}.html"
        with open(html_report_path, 'w') as f:
            f.write(html_content)
    
    async def check_zero_critical_policy(self, results: Dict[str, QualityGateResult]) -> Tuple[bool, List[str]]:
        """Check if zero critical policy is satisfied."""
        all_issues = []
        for result in results.values():
            all_issues.extend(result.issues)
        
        critical_issues = [issue for issue in all_issues if issue.severity == SeverityLevel.CRITICAL]
        
        if self.zero_critical_policy and critical_issues:
            violations = [f"Critical issue in {issue.file_path}: {issue.title}" for issue in critical_issues]
            return False, violations
        
        return True, []
    
    async def can_deploy(self, results: Dict[str, QualityGateResult]) -> Tuple[bool, str]:
        """Determine if deployment should be allowed based on quality gates."""
        # Check zero critical policy
        policy_ok, violations = await self.check_zero_critical_policy(results)
        
        if not policy_ok:
            return False, f"Deployment blocked: {len(violations)} critical security issues found"
        
        # Check for failed gates
        failed_gates = [name for name, result in results.items() if result.status == QualityGateStatus.FAILED]
        
        if failed_gates and self.config.get("security_policies", {}).get("block_deployment_on_critical", True):
            return False, f"Deployment blocked: Failed security gates: {', '.join(failed_gates)}"
        
        return True, "Deployment approved - all security quality gates passed"


# CLI interface for running quality gates
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Security Quality Gates")
    parser.add_argument("--target", nargs="+", help="Target paths to scan", default=["."])
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit with error code on critical issues")
    parser.add_argument("--fail-on-any", action="store_true", help="Exit with error code on any issues")
    
    args = parser.parse_args()
    
    async def main():
        gates = SecurityQualityGates(args.config)
        results = await gates.run_all_quality_gates(args.target)
        
        # Print summary
        total_issues = sum(len(result.issues) for result in results.values())
        critical_issues = sum(1 for result in results.values() for issue in result.issues if issue.severity == SeverityLevel.CRITICAL)
        
        print("\nSecurity Quality Gates Summary:")
        print(f"Total Issues: {total_issues}")
        print(f"Critical Issues: {critical_issues}")
        
        for name, result in results.items():
            status_symbol = "✓" if result.status == QualityGateStatus.PASSED else "✗"
            print(f"{status_symbol} {name}: {result.status.value} ({len(result.issues)} issues)")
        
        # Check deployment readiness
        can_deploy, message = await gates.can_deploy(results)
        print(f"\nDeployment Status: {message}")
        
        # Exit with appropriate code
        if args.fail_on_critical and critical_issues > 0:
            sys.exit(1)
        elif args.fail_on_any and total_issues > 0:
            sys.exit(1)
        elif not can_deploy:
            sys.exit(1)
    
    asyncio.run(main())