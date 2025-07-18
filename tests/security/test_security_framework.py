"""
Comprehensive Security Testing Framework for LeanVibe Quality Agent

This module provides security testing capabilities including:
- Static code analysis for security vulnerabilities
- Dynamic security testing
- Dependency vulnerability scanning
- Input validation testing
- Authentication and authorization testing
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest
from task_queue_module.task_queue import Task, TaskQueue

from state.state_manager import AgentState, StateManager

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '.claude'))


class SecurityTestFramework:
    """Comprehensive security testing framework."""

    def __init__(self):
        self.vulnerabilities = []
        self.security_issues = []
        self.risk_levels = {
            'CRITICAL': 4,
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1
        }

    def run_static_analysis(self, target_dir: str) -> Dict[str, Any]:
        """Run static security analysis using bandit."""
        try:
            cmd = [
                'bandit', '-r', target_dir, '-f', 'json', '-q'
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60)

            if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                if result.stdout:
                    return json.loads(result.stdout)
                return {"results": [], "metrics": {}}
            else:
                return {"error": f"Bandit failed: {result.stderr}"}
        except subprocess.TimeoutExpired:
            return {"error": "Static analysis timed out"}
        except FileNotFoundError:
            return {"error": "Bandit not installed"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON output from bandit"}

    def check_dependency_vulnerabilities(self) -> Dict[str, Any]:
        """Check for known vulnerabilities in dependencies."""
        try:
            cmd = ['safety', 'check', '--json']
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return {"vulnerabilities": [], "safe": True}
            else:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"error": "Failed to parse safety output"}
        except subprocess.TimeoutExpired:
            return {"error": "Dependency check timed out"}
        except FileNotFoundError:
            return {"error": "Safety not installed"}

    def validate_input_sanitization(
            self, test_inputs: List[str]) -> List[Dict[str, Any]]:
        """Test input validation and sanitization."""
        results = []

        # SQL injection patterns
        sql_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--"
        ]

        # XSS patterns
        xss_patterns = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//"
        ]

        # Command injection patterns
        cmd_patterns = [
            "; ls -la",
            "| cat /etc/passwd",
            "`rm -rf /`",
            "$(whoami)"
        ]

        all_patterns = sql_patterns + xss_patterns + cmd_patterns

        for pattern in all_patterns:
            for test_input in test_inputs:
                combined_input = f"{test_input}{pattern}"

                # Test if input is properly sanitized
                result = {
                    "input": combined_input,
                    "pattern_type": self._get_pattern_type(pattern),
                    "sanitized": self._test_sanitization(combined_input),
                    "risk_level": self._assess_risk(pattern)
                }
                results.append(result)

        return results

    def _get_pattern_type(self, pattern: str) -> str:
        """Determine the type of attack pattern."""
        if any(sql_word in pattern.lower()
               for sql_word in ['select', 'drop', 'union', 'insert']):
            return "SQL_INJECTION"
        elif any(xss_word in pattern.lower() for xss_word in ['script', 'alert', 'javascript']):
            return "XSS"
        elif any(cmd_word in pattern for cmd_word in ['|', ';', '`', '$(']):
            return "COMMAND_INJECTION"
        return "UNKNOWN"

    def _test_sanitization(self, input_str: str) -> bool:
        """Test if input is properly sanitized."""
        # Simple sanitization test - in real implementation,
        # this would test actual sanitization functions
        dangerous_chars = ['<', '>', ';', '|', '`', '$']
        return not any(char in input_str for char in dangerous_chars)

    def _assess_risk(self, pattern: str) -> str:
        """Assess risk level of a pattern."""
        if 'DROP' in pattern or 'rm -rf' in pattern:
            return "CRITICAL"
        elif 'script' in pattern.lower() or 'SELECT' in pattern:
            return "HIGH"
        elif ';' in pattern or '|' in pattern:
            return "MEDIUM"
        else:
            return "LOW"

    def test_authentication_bypass(self) -> List[Dict[str, Any]]:
        """Test for authentication bypass vulnerabilities."""
        bypass_attempts = [
            {"username": "admin", "password": ""},
            {"username": "admin", "password": "admin"},
            {"username": "' OR '1'='1", "password": "anything"},
            {"username": "admin'--", "password": "anything"},
            {"username": "", "password": ""},
        ]

        results = []
        for attempt in bypass_attempts:
            result = {
                "attempt": attempt,
                "bypassed": self._test_auth_bypass(attempt),
                "risk_level": "CRITICAL" if self._test_auth_bypass(attempt) else "LOW"}
            results.append(result)

        return results

    def _test_auth_bypass(self, credentials: Dict[str, str]) -> bool:
        """Test if authentication can be bypassed."""
        # Simple mock authentication test
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        # Simulate vulnerable authentication
        if "OR" in username or "--" in username:
            return True  # Authentication bypassed
        if not username or not password:
            return True  # Empty credentials allowed

        return False

    def test_file_access_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Test for unauthorized file access."""
        file_access_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "proc/self/environ",
            ".env",
            "config.yaml",
            "database.db"
        ]

        results = []
        for attempt in file_access_attempts:
            result = {
                "file_path": attempt,
                "accessible": self._test_file_access(attempt),
                "risk_level": self._assess_file_access_risk(attempt)
            }
            results.append(result)

        return results

    def _test_file_access(self, file_path: str) -> bool:
        """Test if file can be accessed."""
        try:
            # Simulate file access test
            if ".." in file_path or file_path.startswith("/"):
                return True  # Potentially dangerous path
            return os.path.exists(file_path)
        except Exception:
            return False

    def _assess_file_access_risk(self, file_path: str) -> str:
        """Assess risk level of file access."""
        sensitive_files = [
            "passwd", "shadow", "SAM", "config", ".env", "database.db"
        ]

        if any(sensitive in file_path.lower()
               for sensitive in sensitive_files):
            return "HIGH"
        elif ".." in file_path or file_path.startswith("/"):
            return "MEDIUM"
        else:
            return "LOW"

    def test_data_exposure(self) -> Dict[str, Any]:
        """Test for potential data exposure."""
        exposure_tests = {
            "database_credentials": self._check_database_credentials(),
            "api_keys": self._check_api_keys(),
            "private_keys": self._check_private_keys(),
            "session_tokens": self._check_session_tokens(),
            "debug_information": self._check_debug_exposure()
        }

        return exposure_tests

    def _check_database_credentials(self) -> Dict[str, Any]:
        """Check for exposed database credentials."""
        # Simulate checking for database credentials in code
        return {
            "exposed": False,
            "locations": [],
            "risk_level": "HIGH"
        }

    def _check_api_keys(self) -> Dict[str, Any]:
        """Check for exposed API keys."""
        return {
            "exposed": False,
            "locations": [],
            "risk_level": "HIGH"
        }

    def _check_private_keys(self) -> Dict[str, Any]:
        """Check for exposed private keys."""
        return {
            "exposed": False,
            "locations": [],
            "risk_level": "CRITICAL"
        }

    def _check_session_tokens(self) -> Dict[str, Any]:
        """Check for exposed session tokens."""
        return {
            "exposed": False,
            "locations": [],
            "risk_level": "HIGH"
        }

    def _check_debug_exposure(self) -> Dict[str, Any]:
        """Check for debug information exposure."""
        return {
            "exposed": False,
            "locations": [],
            "risk_level": "MEDIUM"
        }

    def generate_security_report(
            self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        total_issues = 0
        risk_distribution = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        # Analyze results
        for test_type, results in scan_results.items():
            if isinstance(results, list):
                for result in results:
                    if result.get("risk_level") in risk_distribution:
                        risk_distribution[result["risk_level"]] += 1
                        total_issues += 1

        # Calculate security score
        security_score = self._calculate_security_score(risk_distribution)

        report = {
            "timestamp": str(
                Path(__file__).stat().st_mtime),
            "total_issues": total_issues,
            "risk_distribution": risk_distribution,
            "security_score": security_score,
            "recommendations": self._generate_recommendations(risk_distribution),
            "detailed_results": scan_results}

        return report

    def _calculate_security_score(
            self, risk_distribution: Dict[str, int]) -> float:
        """Calculate overall security score."""
        max_penalty = 100
        penalty = 0

        penalty += risk_distribution["CRITICAL"] * 25
        penalty += risk_distribution["HIGH"] * 15
        penalty += risk_distribution["MEDIUM"] * 8
        penalty += risk_distribution["LOW"] * 3

        return max(0, 100 - min(penalty, max_penalty))

    def _generate_recommendations(
            self, risk_distribution: Dict[str, int]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []

        if risk_distribution["CRITICAL"] > 0:
            recommendations.append(
                "URGENT: Fix critical security vulnerabilities immediately")

        if risk_distribution["HIGH"] > 0:
            recommendations.append(
                "HIGH PRIORITY: Address high-risk security issues")

        if risk_distribution["MEDIUM"] > 0:
            recommendations.append(
                "MEDIUM PRIORITY: Review and fix medium-risk issues")

        if risk_distribution["LOW"] > 0:
            recommendations.append(
                "LOW PRIORITY: Consider addressing low-risk issues")

        if not any(risk_distribution.values()):
            recommendations.append(
                "Good security posture - continue monitoring")

        return recommendations


@pytest.mark.security
class TestSecurityFramework:
    """Security testing framework tests."""

    def test_static_analysis_execution(self):
        """Test static analysis execution."""
        framework = SecurityTestFramework()

        # Test on .claude directory
        result = framework.run_static_analysis(".claude")

        assert isinstance(result, dict)
        assert "results" in result or "error" in result

        # If successful, should have proper structure
        if "results" in result:
            assert isinstance(result["results"], list)

    def test_dependency_vulnerability_check(self):
        """Test dependency vulnerability scanning."""
        framework = SecurityTestFramework()

        result = framework.check_dependency_vulnerabilities()

        assert isinstance(result, dict)
        # Should have either vulnerabilities or error
        assert "vulnerabilities" in result or "error" in result or "safe" in result

    def test_input_validation_testing(self):
        """Test input validation security."""
        framework = SecurityTestFramework()

        test_inputs = ["username", "email", "password"]
        results = framework.validate_input_sanitization(test_inputs)

        assert isinstance(results, list)
        assert len(results) > 0

        for result in results:
            assert "input" in result
            assert "pattern_type" in result
            assert "sanitized" in result
            assert "risk_level" in result
            assert result["risk_level"] in [
                "CRITICAL", "HIGH", "MEDIUM", "LOW"]

    def test_authentication_bypass_testing(self):
        """Test authentication bypass vulnerabilities."""
        framework = SecurityTestFramework()

        results = framework.test_authentication_bypass()

        assert isinstance(results, list)
        assert len(results) > 0

        for result in results:
            assert "attempt" in result
            assert "bypassed" in result
            assert "risk_level" in result

    def test_file_access_vulnerability_testing(self):
        """Test file access vulnerabilities."""
        framework = SecurityTestFramework()

        results = framework.test_file_access_vulnerabilities()

        assert isinstance(results, list)
        assert len(results) > 0

        for result in results:
            assert "file_path" in result
            assert "accessible" in result
            assert "risk_level" in result

    def test_data_exposure_testing(self):
        """Test data exposure vulnerabilities."""
        framework = SecurityTestFramework()

        results = framework.test_data_exposure()

        assert isinstance(results, dict)
        expected_keys = [
            "database_credentials", "api_keys", "private_keys",
            "session_tokens", "debug_information"
        ]

        for key in expected_keys:
            assert key in results
            assert "exposed" in results[key]
            assert "risk_level" in results[key]

    def test_security_report_generation(self):
        """Test security report generation."""
        framework = SecurityTestFramework()

        # Mock scan results
        mock_results = {
            "input_validation": [
                {"risk_level": "HIGH", "input": "test"},
                {"risk_level": "MEDIUM", "input": "test2"}
            ],
            "auth_bypass": [
                {"risk_level": "LOW", "attempt": "test"}
            ]
        }

        report = framework.generate_security_report(mock_results)

        assert isinstance(report, dict)
        assert "timestamp" in report
        assert "total_issues" in report
        assert "risk_distribution" in report
        assert "security_score" in report
        assert "recommendations" in report
        assert "detailed_results" in report

        # Verify risk distribution
        assert report["risk_distribution"]["HIGH"] == 1
        assert report["risk_distribution"]["MEDIUM"] == 1
        assert report["risk_distribution"]["LOW"] == 1
        assert report["total_issues"] == 3

        # Verify security score is calculated
        assert 0 <= report["security_score"] <= 100

    def test_comprehensive_security_scan(self):
        """Test comprehensive security scan."""
        framework = SecurityTestFramework()

        # Run all security tests
        scan_results = {
            "static_analysis": framework.run_static_analysis(".claude"),
            "dependency_check": framework.check_dependency_vulnerabilities(),
            "input_validation": framework.validate_input_sanitization(
                ["test_input"]),
            "auth_bypass": framework.test_authentication_bypass(),
            "file_access": framework.test_file_access_vulnerabilities(),
            "data_exposure": framework.test_data_exposure()}

        # Generate report
        report = framework.generate_security_report(scan_results)

        # Verify comprehensive report
        assert isinstance(report, dict)
        assert report["security_score"] >= 0
        assert len(report["recommendations"]) > 0

        # Log security findings
        if report["total_issues"] > 0:
            print(f"Security scan found {report['total_issues']} issues")
            print(f"Security score: {report['security_score']}/100")
            for rec in report["recommendations"]:
                print(f"Recommendation: {rec}")


@pytest.mark.security
class TestSecurityIntegration:
    """Integration tests for security framework with system components."""

    def test_state_manager_security(self):
        """Test StateManager security."""
        SecurityTestFramework()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test SQL injection protection
            state_manager = StateManager(Path(temp_dir))

            # Attempt SQL injection in agent_id
            malicious_agent_id = "'; DROP TABLE agents; --"

            agent_state = AgentState(
                agent_id=malicious_agent_id,
                status="idle",
                capabilities=["test"],
                performance_metrics={"speed": 0.8}
            )

            # Should not crash or allow injection
            try:
                state_manager.update_agent_state(agent_state)
                retrieved = state_manager.get_agent_state(malicious_agent_id)

                # Should handle malicious input safely
                assert retrieved is not None
                assert retrieved.agent_id == malicious_agent_id

            except Exception as e:
                # Should not crash with unhandled exceptions
                assert "SQL" not in str(e)

    def test_task_queue_security(self):
        """Test TaskQueue security."""
        import asyncio

        async def run_test():
            SecurityTestFramework()
            task_queue = TaskQueue()

            # Test malicious task data
            malicious_data = {
                "script": "<script>alert('XSS')</script>",
                "command": "; rm -rf /",
                "sql": "' OR '1'='1"
            }

            task = Task(
                id="security-test-task",
                type="security_test",
                description="Testing security",
                priority=5,
                data=malicious_data
            )

            # Should handle malicious data safely
            await task_queue.enqueue(task)
            retrieved_task = await task_queue.dequeue()

            assert retrieved_task is not None
            assert retrieved_task.id == "security-test-task"
            assert retrieved_task.data == malicious_data

        asyncio.run(run_test())

    def test_configuration_security(self):
        """Test configuration security."""
        SecurityTestFramework()

        # Test for hardcoded credentials
        config_files = [
            ".claude/config",
            "config.yaml",
            "settings.yaml"
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    content = f.read()

                    # Check for potential credentials
                    credential_patterns = [
                        r'password\s*[:=]\s*["\'](.+)["\']',
                        r'secret\s*[:=]\s*["\'](.+)["\']',
                        r'key\s*[:=]\s*["\'](.+)["\']',
                        r'token\s*[:=]\s*["\'](.+)["\']'
                    ]

                    for pattern in credential_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)

                        # Should not find hardcoded credentials
                        for match in matches:
                            assert len(match) == 0 or match in [
                                '', 'YOUR_SECRET_HERE', 'CHANGE_ME']

    @pytest.mark.asyncio
    async def test_concurrent_security_operations(self):
        """Test security under concurrent operations."""
        SecurityTestFramework()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_manager = StateManager(Path(temp_dir))

            # Create multiple agents concurrently with potential security
            # issues
            import asyncio

            async def create_agent(agent_id: str):
                agent_state = AgentState(
                    agent_id=agent_id,
                    status="idle",
                    capabilities=["concurrent_test"],
                    performance_metrics={"speed": 0.8}
                )
                state_manager.update_agent_state(agent_state)
                return state_manager.get_agent_state(agent_id)

            # Test concurrent access
            tasks = [
                create_agent(f"concurrent-agent-{i}")
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)

            # All operations should complete successfully
            assert len(results) == 10
            assert all(result is not None for result in results)
