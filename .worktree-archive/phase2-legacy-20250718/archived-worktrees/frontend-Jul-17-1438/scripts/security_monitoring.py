#!/usr/bin/env python3
"""
Advanced Security Monitoring and Alerting System
LeanVibe Quality Agent - Continuous Security Assurance

This script provides comprehensive security monitoring with:
- Real-time vulnerability scanning
- Automated dependency updates
- Security metrics tracking
- Alert generation and reporting
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SecurityMonitor:
    """Advanced security monitoring and alerting system."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the security monitor."""
        self.config = self._load_config(config_path)
        self.reports_dir = Path("security_reports")
        self.reports_dir.mkdir(exist_ok=True)

        # Security thresholds
        self.critical_threshold = self.config.get("critical_threshold", 0)
        self.high_threshold = self.config.get("high_threshold", 5)
        self.medium_threshold = self.config.get("medium_threshold", 20)

        # Monitoring intervals
        self.scan_interval = self.config.get("scan_interval_hours", 6)
        self.dependency_check_interval = self.config.get("dependency_check_hours", 24)

        logger.info("Security Monitor initialized with enterprise-grade monitoring")

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            "email_alerts": False,
            "slack_alerts": False,
            "github_alerts": True,
            "critical_threshold": 0,
            "high_threshold": 5,
            "medium_threshold": 20,
            "scan_interval_hours": 6,
            "dependency_check_hours": 24,
            "auto_update_minor": False,
            "auto_update_security": True
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

        return default_config

    def run_comprehensive_security_scan(self) -> Dict:
        """Run complete security scanning suite."""
        logger.info("🔍 Starting comprehensive security scan")

        scan_results = {
            "timestamp": datetime.now().isoformat(),
            "bandit_scan": self._run_bandit_scan(),
            "safety_scan": self._run_safety_scan(),
            "pip_audit_scan": self._run_pip_audit_scan(),
            "dependency_check": self._check_dependency_updates(),
            "custom_security_checks": self._run_custom_security_checks()
        }

        # Calculate overall security score
        scan_results["security_score"] = self._calculate_security_score(scan_results)
        scan_results["risk_level"] = self._determine_risk_level(scan_results)

        # Save detailed report
        report_file = self.reports_dir / f"security_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(scan_results, f, indent=2)

        logger.info(f"✅ Security scan complete. Report saved: {report_file}")
        return scan_results

    def _run_bandit_scan(self) -> Dict:
        """Run Bandit static security analysis."""
        logger.info("Running Bandit security scan...")

        try:
            cmd = [
                'bandit', '-r', '.', '-f', 'json',
                '--exclude', 'tests,tutorials,venv,.venv',
                '--severity-level', 'low'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.stdout:
                bandit_data = json.loads(result.stdout)

                # Categorize issues by severity
                issues_by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}
                for issue in bandit_data.get("results", []):
                    severity = issue.get("issue_severity", "LOW")
                    issues_by_severity[severity].append(issue)

                return {
                    "status": "completed",
                    "total_issues": len(bandit_data.get("results", [])),
                    "high_severity": len(issues_by_severity["HIGH"]),
                    "medium_severity": len(issues_by_severity["MEDIUM"]),
                    "low_severity": len(issues_by_severity["LOW"]),
                    "issues_by_severity": issues_by_severity,
                    "execution_time": bandit_data.get("metrics", {}).get("_totals", {}).get("elapse", 0)
                }
            else:
                return {"status": "no_issues", "total_issues": 0}

        except subprocess.TimeoutExpired:
            logger.error("Bandit scan timed out")
            return {"status": "timeout", "error": "Scan timed out after 120 seconds"}
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            return {"status": "error", "error": str(e)}

    def _run_safety_scan(self) -> Dict:
        """Run Safety dependency vulnerability scan."""
        logger.info("Running Safety dependency scan...")

        try:
            cmd = ['safety', 'scan', '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.stdout:
                try:
                    safety_data = json.loads(result.stdout)
                    vulnerabilities = safety_data.get("vulnerabilities", [])

                    # Categorize vulnerabilities by severity
                    critical_vulns = [v for v in vulnerabilities if v.get("vulnerability_id", "").startswith("PVE")]

                    return {
                        "status": "completed",
                        "total_vulnerabilities": len(vulnerabilities),
                        "critical_vulnerabilities": len(critical_vulns),
                        "vulnerabilities": vulnerabilities[:10],  # First 10 for summary
                        "scan_timestamp": datetime.now().isoformat()
                    }
                except json.JSONDecodeError:
                    return {"status": "no_vulnerabilities", "total_vulnerabilities": 0}
            else:
                return {"status": "no_vulnerabilities", "total_vulnerabilities": 0}

        except subprocess.TimeoutExpired:
            logger.error("Safety scan timed out")
            return {"status": "timeout", "error": "Scan timed out after 60 seconds"}
        except Exception as e:
            logger.error(f"Safety scan failed: {e}")
            return {"status": "error", "error": str(e)}

    def _run_pip_audit_scan(self) -> Dict:
        """Run pip-audit vulnerability scan."""
        logger.info("Running pip-audit vulnerability scan...")

        try:
            cmd = ['pip-audit', '--format=json', '--desc']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.stdout:
                try:
                    audit_data = json.loads(result.stdout)
                    vulnerabilities = audit_data.get("vulnerabilities", [])

                    return {
                        "status": "completed",
                        "total_vulnerabilities": len(vulnerabilities),
                        "vulnerabilities": vulnerabilities,
                        "scan_version": audit_data.get("version", "unknown")
                    }
                except json.JSONDecodeError:
                    return {"status": "no_vulnerabilities", "total_vulnerabilities": 0}
            else:
                return {"status": "no_vulnerabilities", "total_vulnerabilities": 0}

        except subprocess.TimeoutExpired:
            logger.error("pip-audit scan timed out")
            return {"status": "timeout", "error": "Scan timed out after 60 seconds"}
        except Exception as e:
            logger.error(f"pip-audit scan failed: {e}")
            return {"status": "error", "error": str(e)}

    def _check_dependency_updates(self) -> Dict:
        """Check for available dependency updates."""
        logger.info("Checking for dependency updates...")

        try:
            # Get outdated packages
            cmd = ['pip', 'list', '--outdated', '--format=json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.stdout:
                outdated_packages = json.loads(result.stdout)

                # Categorize updates
                security_related = []
                major_updates = []
                minor_updates = []

                for package in outdated_packages:
                    name = package.get("name", "").lower()
                    current = package.get("version", "")
                    latest = package.get("latest_version", "")

                    # Check if security-related
                    if any(keyword in name for keyword in ['security', 'crypto', 'ssl', 'auth', 'jwt']):
                        security_related.append(package)

                    # Check update type (simplified version comparison)
                    try:
                        current_major = int(current.split('.')[0]) if current else 0
                        latest_major = int(latest.split('.')[0]) if latest else 0

                        if latest_major > current_major:
                            major_updates.append(package)
                        else:
                            minor_updates.append(package)
                    except:
                        minor_updates.append(package)

                return {
                    "status": "completed",
                    "total_updates": len(outdated_packages),
                    "security_related": len(security_related),
                    "major_updates": len(major_updates),
                    "minor_updates": len(minor_updates),
                    "packages": outdated_packages[:15],  # First 15 for summary
                    "security_packages": security_related
                }
            else:
                return {"status": "up_to_date", "total_updates": 0}

        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return {"status": "error", "error": str(e)}

    def _run_custom_security_checks(self) -> Dict:
        """Run custom security validation checks."""
        logger.info("Running custom security checks...")

        checks = {
            "hardcoded_secrets": self._check_hardcoded_secrets(),
            "insecure_configurations": self._check_insecure_configs(),
            "file_permissions": self._check_file_permissions(),
            "environment_security": self._check_environment_security()
        }

        total_issues = sum(check.get("issues_found", 0) for check in checks.values())

        return {
            "status": "completed",
            "total_custom_issues": total_issues,
            "checks": checks
        }

    def _check_hardcoded_secrets(self) -> Dict:
        """Check for hardcoded secrets and credentials."""
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']'
        ]

        issues = []
        try:
            import re
            for pattern in secret_patterns:
                cmd = ['grep', '-r', '-n', '-i', pattern, '.', '--include=*.py']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.stdout:
                    issues.extend(result.stdout.strip().split('\n'))
        except:
            pass

        return {
            "issues_found": len(issues),
            "description": "Hardcoded secrets detection",
            "issues": issues[:5]  # First 5 issues
        }

    def _check_insecure_configs(self) -> Dict:
        """Check for insecure configuration patterns."""
        config_issues = []

        # Check for debug mode in production configs
        try:
            for config_file in Path('.').rglob('*.yaml'):
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'debug: true' in content.lower():
                        config_issues.append(f"Debug mode enabled in {config_file}")
        except:
            pass

        return {
            "issues_found": len(config_issues),
            "description": "Insecure configuration detection",
            "issues": config_issues
        }

    def _check_file_permissions(self) -> Dict:
        """Check for insecure file permissions."""
        permission_issues = []

        try:
            # Check for world-writable files
            cmd = ['find', '.', '-type', 'f', '-perm', '0777']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout:
                permission_issues.extend(result.stdout.strip().split('\n'))
        except:
            pass

        return {
            "issues_found": len(permission_issues),
            "description": "File permission security check",
            "issues": permission_issues[:5]
        }

    def _check_environment_security(self) -> Dict:
        """Check environment security configuration."""
        env_issues = []

        # Check for .env files in version control
        if Path('.env').exists():
            env_issues.append(".env file detected - ensure it's in .gitignore")

        # Check for exposed environment variables
        try:
            cmd = ['grep', '-r', 'os.environ', '.', '--include=*.py']
            result = subprocess.run(cmd, capture_output=True, text=True)
            env_var_usage = len(result.stdout.split('\n')) if result.stdout else 0

            if env_var_usage > 10:
                env_issues.append(f"High environment variable usage detected: {env_var_usage} instances")
        except:
            pass

        return {
            "issues_found": len(env_issues),
            "description": "Environment security validation",
            "issues": env_issues
        }

    def _calculate_security_score(self, scan_results: Dict) -> float:
        """Calculate overall security score (0-100)."""
        base_score = 100.0

        # Deduct points for vulnerabilities
        bandit_results = scan_results.get("bandit_scan", {})
        safety_results = scan_results.get("safety_scan", {})
        audit_results = scan_results.get("pip_audit_scan", {})
        custom_results = scan_results.get("custom_security_checks", {})

        # Bandit deductions
        base_score -= bandit_results.get("high_severity", 0) * 15
        base_score -= bandit_results.get("medium_severity", 0) * 5
        base_score -= bandit_results.get("low_severity", 0) * 1

        # Safety deductions
        base_score -= safety_results.get("critical_vulnerabilities", 0) * 20
        base_score -= safety_results.get("total_vulnerabilities", 0) * 3

        # Pip-audit deductions
        base_score -= audit_results.get("total_vulnerabilities", 0) * 8

        # Custom checks deductions
        base_score -= custom_results.get("total_custom_issues", 0) * 2

        return max(0.0, base_score)

    def _determine_risk_level(self, scan_results: Dict) -> str:
        """Determine overall risk level based on scan results."""
        security_score = scan_results.get("security_score", 100)

        # Count critical issues
        bandit_high = scan_results.get("bandit_scan", {}).get("high_severity", 0)
        safety_critical = scan_results.get("safety_scan", {}).get("critical_vulnerabilities", 0)
        audit_vulns = scan_results.get("pip_audit_scan", {}).get("total_vulnerabilities", 0)

        critical_count = bandit_high + safety_critical + audit_vulns

        if critical_count > 0 or security_score < 50:
            return "CRITICAL"
        elif security_score < 70:
            return "HIGH"
        elif security_score < 85:
            return "MEDIUM"
        else:
            return "LOW"

    def generate_security_report(self, scan_results: Dict) -> str:
        """Generate human-readable security report."""
        timestamp = scan_results.get("timestamp", datetime.now().isoformat())
        security_score = scan_results.get("security_score", 0)
        risk_level = scan_results.get("risk_level", "UNKNOWN")

        report = f"""
# 🔒 LeanVibe Security Monitoring Report

**Generated**: {timestamp}
**Security Score**: {security_score:.1f}/100
**Risk Level**: {risk_level}

## 📊 Security Scan Summary

### Bandit Static Analysis
"""

        bandit_results = scan_results.get("bandit_scan", {})
        if bandit_results.get("status") == "completed":
            report += f"""
- **Total Issues**: {bandit_results.get("total_issues", 0)}
- **High Severity**: {bandit_results.get("high_severity", 0)}
- **Medium Severity**: {bandit_results.get("medium_severity", 0)}
- **Low Severity**: {bandit_results.get("low_severity", 0)}
"""
        else:
            report += f"- **Status**: {bandit_results.get('status', 'Unknown')}\n"

        safety_results = scan_results.get("safety_scan", {})
        report += f"""
### Safety Dependency Scan
- **Total Vulnerabilities**: {safety_results.get("total_vulnerabilities", 0)}
- **Critical Vulnerabilities**: {safety_results.get("critical_vulnerabilities", 0)}
"""

        audit_results = scan_results.get("pip_audit_scan", {})
        report += f"""
### Pip-Audit Vulnerability Scan
- **Total Vulnerabilities**: {audit_results.get("total_vulnerabilities", 0)}
"""

        dependency_results = scan_results.get("dependency_check", {})
        report += f"""
### Dependency Updates
- **Total Updates Available**: {dependency_results.get("total_updates", 0)}
- **Security-Related Updates**: {dependency_results.get("security_related", 0)}
- **Major Updates**: {dependency_results.get("major_updates", 0)}
"""

        custom_results = scan_results.get("custom_security_checks", {})
        report += f"""
### Custom Security Checks
- **Total Issues Found**: {custom_results.get("total_custom_issues", 0)}
"""

        # Add recommendations
        report += self._generate_recommendations(scan_results)

        return report

    def _generate_recommendations(self, scan_results: Dict) -> str:
        """Generate security recommendations based on scan results."""
        recommendations = "\n## 🎯 Recommendations\n\n"

        risk_level = scan_results.get("risk_level", "LOW")

        if risk_level == "CRITICAL":
            recommendations += """
### 🚨 CRITICAL ACTIONS REQUIRED
1. **Immediate**: Address all high-severity vulnerabilities
2. **Security Review**: Conduct comprehensive security audit
3. **Incident Response**: Activate security incident procedures
4. **Monitoring**: Increase security monitoring frequency
"""

        elif risk_level == "HIGH":
            recommendations += """
### ⚠️ HIGH PRIORITY ACTIONS
1. **Update Dependencies**: Apply security updates immediately
2. **Code Review**: Review flagged security issues
3. **Monitoring**: Implement additional security monitoring
"""

        elif risk_level == "MEDIUM":
            recommendations += """
### 📋 MEDIUM PRIORITY ACTIONS
1. **Scheduled Updates**: Plan dependency updates
2. **Code Improvements**: Address medium-severity issues
3. **Security Training**: Review security best practices
"""

        else:
            recommendations += """
### ✅ MAINTENANCE ACTIONS
1. **Regular Updates**: Continue regular dependency maintenance
2. **Monitoring**: Maintain current security monitoring
3. **Best Practices**: Continue following security guidelines
"""

        return recommendations

    def send_alert(self, scan_results: Dict) -> None:
        """Send security alerts based on configuration."""
        risk_level = scan_results.get("risk_level", "LOW")
        security_score = scan_results.get("security_score", 100)

        # Determine if alert should be sent
        should_alert = False
        if risk_level in ["CRITICAL", "HIGH"]:
            should_alert = True
        elif risk_level == "MEDIUM" and security_score < 75:
            should_alert = True

        if should_alert:
            logger.warning(f"🚨 Security alert triggered: {risk_level} risk level detected")

            if self.config.get("email_alerts"):
                self._send_email_alert(scan_results)

            if self.config.get("slack_alerts"):
                self._send_slack_alert(scan_results)

            if self.config.get("github_alerts"):
                logger.info("GitHub alerts handled by workflow automation")

    def _send_email_alert(self, scan_results: Dict) -> None:
        """Send email security alert."""
        # Implementation for email alerts
        logger.info("Email alert configured but not implemented in this version")

    def _send_slack_alert(self, scan_results: Dict) -> None:
        """Send Slack security alert."""
        # Implementation for Slack alerts
        logger.info("Slack alert configured but not implemented in this version")

    def start_continuous_monitoring(self) -> None:
        """Start continuous security monitoring."""
        logger.info(f"🔄 Starting continuous security monitoring (scan interval: {self.scan_interval}h)")

        last_full_scan = datetime.now() - timedelta(hours=self.scan_interval)
        last_dependency_check = datetime.now() - timedelta(hours=self.dependency_check_interval)

        try:
            while True:
                current_time = datetime.now()

                # Run full security scan
                if (current_time - last_full_scan).total_seconds() >= self.scan_interval * 3600:
                    logger.info("🔍 Running scheduled security scan")
                    scan_results = self.run_comprehensive_security_scan()
                    self.send_alert(scan_results)
                    last_full_scan = current_time

                # Run dependency check
                if (current_time - last_dependency_check).total_seconds() >= self.dependency_check_interval * 3600:
                    logger.info("📦 Running scheduled dependency check")
                    dependency_results = self._check_dependency_updates()

                    # Auto-update security dependencies if configured
                    if self.config.get("auto_update_security"):
                        self._auto_update_security_dependencies(dependency_results)

                    last_dependency_check = current_time

                # Sleep for 1 hour before next check
                time.sleep(3600)

        except KeyboardInterrupt:
            logger.info("🛑 Security monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Security monitoring error: {e}")

    def _auto_update_security_dependencies(self, dependency_results: Dict) -> None:
        """Automatically update security-related dependencies."""
        if dependency_results.get("status") != "completed":
            return

        security_packages = dependency_results.get("security_packages", [])

        if security_packages:
            logger.info(f"🔄 Auto-updating {len(security_packages)} security-related packages")

            for package in security_packages:
                package_name = package.get("name")
                try:
                    cmd = ['pip', 'install', '--upgrade', package_name]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

                    if result.returncode == 0:
                        logger.info(f"✅ Successfully updated {package_name}")
                    else:
                        logger.error(f"❌ Failed to update {package_name}: {result.stderr}")

                except subprocess.TimeoutExpired:
                    logger.error(f"⏱️ Timeout updating {package_name}")
                except Exception as e:
                    logger.error(f"❌ Error updating {package_name}: {e}")


def main():
    """Main function for security monitoring script."""
    import argparse

    parser = argparse.ArgumentParser(description="LeanVibe Security Monitoring System")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--scan", action="store_true", help="Run single security scan")
    parser.add_argument("--monitor", action="store_true", help="Start continuous monitoring")
    parser.add_argument("--report", help="Generate report from scan results file")

    args = parser.parse_args()

    monitor = SecurityMonitor(args.config)

    if args.scan:
        logger.info("🔍 Running single security scan")
        results = monitor.run_comprehensive_security_scan()

        # Generate and display report
        report = monitor.generate_security_report(results)
        print(report)

        # Send alerts if necessary
        monitor.send_alert(results)

    elif args.monitor:
        logger.info("🔄 Starting continuous monitoring mode")
        monitor.start_continuous_monitoring()

    elif args.report:
        logger.info(f"📊 Generating report from {args.report}")
        try:
            with open(args.report, 'r') as f:
                results = json.load(f)
            report = monitor.generate_security_report(results)
            print(report)
        except Exception as e:
            logger.error(f"❌ Failed to generate report: {e}")

    else:
        logger.info("🔍 Running default security scan")
        results = monitor.run_comprehensive_security_scan()
        report = monitor.generate_security_report(results)
        print(report)


if __name__ == "__main__":
    main()
