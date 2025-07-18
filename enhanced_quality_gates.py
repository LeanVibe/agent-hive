#!/usr/bin/env python3
"""
Enhanced Quality Gates System
Automated enforcement of performance and code quality standards.
"""

from datetime import datetime
from pathlib import Path
import json
import os
import subprocess
import sys
import time

class QualityGate:
    """Base class for quality gates."""

    def __init__(self, name: str, threshold: float, critical: bool = False):
        self.name = name
        self.threshold = threshold
        self.critical = critical
        self.last_result: Optional[Dict[str, Any]] = None

    def check(self) -> Dict[str, Any]:
        """Check the quality gate. Must be implemented by subclasses."""
        raise NotImplementedError

    def passes(self, result: Dict[str, Any]) -> bool:
        """Check if the gate passes based on the result."""
        raise NotImplementedError


class PerformanceGate(QualityGate):
    """Performance-based quality gate."""

    def check(self) -> Dict[str, Any]:
        """Check performance metrics."""
        try:
            # Read performance baseline
            if os.path.exists('performance_baseline.json'):
                with open('performance_baseline.json', 'r') as f:
                    baseline = json.load(f)

                result = {
                    "memory_percent": baseline.get("system", {}).get("memory_percent", 0),
                    "cpu_percent": baseline.get("system", {}).get("cpu_percent", 0),
                    "collection_time": baseline.get("collection_time", 0),
                    "python_files": baseline.get("files", {}).get("python_files", 0),
                    "total_lines": baseline.get("files", {}).get("total_lines", 0)
                }

                self.last_result = result
                return result
            else:
                return {"error": "No performance baseline found"}
        except Exception as e:
            return {"error": str(e)}

    def passes(self, result: Dict[str, Any]) -> bool:
        """Check if performance gate passes."""
        if "error" in result:
            return False

        # Memory usage should be under threshold
        if result.get("memory_percent", 100) > self.threshold:
            return False

        # Collection time should be reasonable
        if result.get("collection_time", 10) > 5.0:
            return False

        return True


class CodeQualityGate(QualityGate):
    """Code quality-based quality gate."""

    def check(self) -> Dict[str, Any]:
        """Check code quality metrics."""
        try:
            result = {
                "pylint_score": 0,
                "mypy_errors": 0,
                "flake8_issues": 0,
                "complexity_issues": 0
            }

            # Check pylint report
            pylint_path = "test_reports/quality/pylint_report.json"
            if os.path.exists(pylint_path):
                with open(pylint_path, 'r') as f:
                    pylint_data = json.load(f)
                    result["pylint_issues"] = len(pylint_data)

            # Check mypy report
            mypy_path = "analysis_reports/mypy_current_critical.txt"
            if os.path.exists(mypy_path):
                with open(mypy_path, 'r') as f:
                    mypy_lines = f.readlines()
                    # Count error lines
                    error_lines = [line for line in mypy_lines if "error:" in line]
                    result["mypy_errors"] = len(error_lines)

            # Check flake8 report
            flake8_path = "test_reports/quality/flake8_report.txt"
            if os.path.exists(flake8_path):
                with open(flake8_path, 'r') as f:
                    flake8_lines = f.readlines()
                    result["flake8_issues"] = len(flake8_lines)

            # Check complexity report
            complexity_path = "test_reports/quality/complexity_report.json"
            if os.path.exists(complexity_path):
                with open(complexity_path, 'r') as f:
                    complexity_data = json.load(f)
                    if isinstance(complexity_data, list):
                        high_complexity = [item for item in complexity_data if item.get("complexity", 0) > 10]
                        result["complexity_issues"] = len(high_complexity)

            self.last_result = result
            return result

        except Exception as e:
            return {"error": str(e)}

    def passes(self, result: Dict[str, Any]) -> bool:
        """Check if code quality gate passes."""
        if "error" in result:
            return False

        # Check various quality metrics
        if result.get("mypy_errors", 0) > self.threshold:
            return False

        if result.get("pylint_issues", 0) > self.threshold * 10:  # Allow more pylint issues
            return False

        if result.get("complexity_issues", 0) > self.threshold:
            return False

        return True


class SecurityGate(QualityGate):
    """Security-based quality gate."""

    def check(self) -> Dict[str, Any]:
        """Check security metrics."""
        try:
            result = {
                "bandit_issues": 0,
                "safety_issues": 0,
                "audit_issues": 0
            }

            # Check bandit report
            bandit_path = "test_reports/security/bandit_security_report.json"
            if os.path.exists(bandit_path):
                with open(bandit_path, 'r') as f:
                    bandit_data = json.load(f)
                    result["bandit_issues"] = len(bandit_data.get("results", []))

            # Check safety report
            safety_path = "test_reports/security/safety_report.json"
            if os.path.exists(safety_path):
                with open(safety_path, 'r') as f:
                    safety_data = json.load(f)
                    result["safety_issues"] = len(safety_data.get("vulnerabilities", []))

            # Check pip audit report
            audit_path = "test_reports/security/pip_audit_report.json"
            if os.path.exists(audit_path):
                with open(audit_path, 'r') as f:
                    audit_data = json.load(f)
                    result["audit_issues"] = len(audit_data.get("vulnerabilities", []))

            self.last_result = result
            return result

        except Exception as e:
            return {"error": str(e)}

    def passes(self, result: Dict[str, Any]) -> bool:
        """Check if security gate passes."""
        if "error" in result:
            return False

        # Zero tolerance for high-severity security issues
        if result.get("bandit_issues", 0) > 0:
            return False

        if result.get("safety_issues", 0) > 0:
            return False

        if result.get("audit_issues", 0) > 0:
            return False

        return True


class EnhancedQualityGatesSystem:
    """Enhanced quality gates system with automated enforcement."""

    def __init__(self):
        self.gates: List[QualityGate] = []
        self.results: Dict[str, Any] = {}
        self.setup_gates()

    def setup_gates(self):
        """Setup quality gates with appropriate thresholds."""
        # Performance gates
        self.gates.append(PerformanceGate("Memory Usage", 80.0, critical=True))

        # Code quality gates
        self.gates.append(CodeQualityGate("Code Quality", 10.0, critical=True))

        # Security gates
        self.gates.append(SecurityGate("Security", 0.0, critical=True))

    def run_all_gates(self) -> Dict[str, Any]:
        """Run all quality gates and return results."""
        print("🚦 Running Enhanced Quality Gates...")

        gate_results = {}
        all_passed = True
        critical_failed = False

        for gate in self.gates:
            print(f"   Checking {gate.name}...")

            start_time = time.time()
            result = gate.check()
            check_time = time.time() - start_time

            passed = gate.passes(result)

            gate_results[gate.name] = {
                "passed": passed,
                "critical": gate.critical,
                "threshold": gate.threshold,
                "result": result,
                "check_time": check_time
            }

            if not passed:
                all_passed = False
                if gate.critical:
                    critical_failed = True
                    print(f"   ❌ {gate.name} FAILED (CRITICAL)")
                else:
                    print(f"   ⚠️  {gate.name} FAILED")
            else:
                print(f"   ✅ {gate.name} PASSED")

        # Overall results
        overall_result = {
            "timestamp": datetime.now().isoformat(),
            "all_passed": all_passed,
            "critical_failed": critical_failed,
            "gates": gate_results,
            "summary": {
                "total_gates": len(self.gates),
                "passed": sum(1 for g in gate_results.values() if g["passed"]),
                "failed": sum(1 for g in gate_results.values() if not g["passed"]),
                "critical_failed": sum(1 for g in gate_results.values() if g["critical"] and not g["passed"])
            }
        }

        self.results = overall_result
        return overall_result

    def generate_report(self) -> str:
        """Generate a comprehensive quality gates report."""
        if not self.results:
            return "No quality gates have been run yet."

        report = []
        report.append("=" * 60)
        report.append("🚦 ENHANCED QUALITY GATES REPORT")
        report.append("=" * 60)

        summary = self.results["summary"]
        report.append(f"🎯 Overall Status: {'✅ PASSED' if self.results['all_passed'] else '❌ FAILED'}")
        report.append(f"📊 Summary: {summary['passed']}/{summary['total_gates']} gates passed")

        if summary['critical_failed'] > 0:
            report.append(f"🚨 Critical Failures: {summary['critical_failed']}")

        report.append("\n📋 Gate Details:")

        for gate_name, gate_result in self.results["gates"].items():
            status = "✅ PASSED" if gate_result["passed"] else "❌ FAILED"
            critical = " (CRITICAL)" if gate_result["critical"] else ""

            report.append(f"\n   {gate_name}{critical}: {status}")
            report.append(f"   Threshold: {gate_result['threshold']}")
            report.append(f"   Check Time: {gate_result['check_time']:.3f}s")

            # Add specific details based on gate type
            result = gate_result["result"]
            if gate_name == "Memory Usage":
                if "memory_percent" in result:
                    report.append(f"   Memory Usage: {result['memory_percent']:.1f}%")
                if "cpu_percent" in result:
                    report.append(f"   CPU Usage: {result['cpu_percent']:.1f}%")
            elif gate_name == "Code Quality":
                if "mypy_errors" in result:
                    report.append(f"   MyPy Errors: {result['mypy_errors']}")
                if "pylint_issues" in result:
                    report.append(f"   Pylint Issues: {result['pylint_issues']}")
                if "complexity_issues" in result:
                    report.append(f"   High Complexity: {result['complexity_issues']}")
            elif gate_name == "Security":
                if "bandit_issues" in result:
                    report.append(f"   Bandit Issues: {result['bandit_issues']}")
                if "safety_issues" in result:
                    report.append(f"   Safety Issues: {result['safety_issues']}")
                if "audit_issues" in result:
                    report.append(f"   Audit Issues: {result['audit_issues']}")

        report.append("\n⏱️  Report Generated: " + self.results["timestamp"])
        report.append("=" * 60)

        return "\n".join(report)

    def save_results(self, filename: str = "quality_gates_enhanced.json"):
        """Save results to file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)

    def enforce_gates(self) -> bool:
        """Enforce quality gates - return True if all critical gates pass."""
        if not self.results:
            self.run_all_gates()

        if self.results["critical_failed"]:
            print("🚨 Critical quality gates failed! Enforcement action required.")
            return False

        print("✅ All critical quality gates passed!")
        return True


def main():
    """Main execution function."""
    system = EnhancedQualityGatesSystem()

    # Run quality gates
    results = system.run_all_gates()

    # Generate and print report
    report = system.generate_report()
    print("\n" + report)

    # Save results
    system.save_results()

    # Save report to file
    with open('quality_gates_enhanced_report.txt', 'w') as f:
        f.write(report)

    print(f"\n💾 Results saved to:")
    print(f"   - quality_gates_enhanced.json (raw data)")
    print(f"   - quality_gates_enhanced_report.txt (formatted report)")

    # Enforce gates
    if system.enforce_gates():
        print("\n🎉 Quality gates enforcement: PASSED")
        return 0
    else:
        print("\n💥 Quality gates enforcement: FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())