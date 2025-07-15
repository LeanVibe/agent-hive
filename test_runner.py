#!/usr/bin/env python3
"""
Comprehensive test runner for LeanVibe Quality Agent

This script provides a comprehensive test runner with coverage analysis,
performance benchmarking, and quality gate validation.
"""

import argparse
import subprocess
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class TestRunner:
    """Comprehensive test runner with quality gates."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "coverage": 0.0,
            "duration": 0.0,
            "quality_gates": []
        }
        
    def run_unit_tests(self, pattern: str = "tests/") -> Dict[str, Any]:
        """Run unit tests with coverage analysis."""
        print("🧪 Running unit tests...")
        
        start_time = time.time()
        
        cmd = [
            sys.executable, "-m", "pytest",
            pattern,
            "--cov=.claude",
            "--cov-report=html:htmlcov",
            "--cov-report=json:coverage.json",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
            "--tb=short",
            "-v" if self.verbose else "-q"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # Parse test results
                    break
            
            # Load coverage data
            coverage_data = self._load_coverage_data()
            
            test_result = {
                "type": "unit_tests",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "coverage": coverage_data
            }
            
            self.results["duration"] += duration
            if coverage_data:
                self.results["coverage"] = coverage_data.get("totals", {}).get("percent_covered", 0)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            return {
                "type": "unit_tests",
                "duration": time.time() - start_time,
                "return_code": -1,
                "error": "Test execution timed out"
            }
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        start_time = time.time()
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/integration/",
            "-v" if self.verbose else "-q",
            "--tb=short"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            duration = time.time() - start_time
            
            return {
                "type": "integration_tests",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "type": "integration_tests",
                "duration": time.time() - start_time,
                "return_code": -1,
                "error": "Integration tests timed out"
            }
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarks."""
        print("⚡ Running performance tests...")
        
        start_time = time.time()
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/performance/",
            "-v" if self.verbose else "-q",
            "--tb=short",
            "-m", "performance"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.time() - start_time
            
            return {
                "type": "performance_tests",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "type": "performance_tests",
                "duration": time.time() - start_time,
                "return_code": -1,
                "error": "Performance tests timed out"
            }
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests using bandit."""
        print("🔒 Running security tests...")
        
        start_time = time.time()
        
        cmd = [
            "bandit", "-r", ".claude/", "-f", "json", "-o", "security_report.json"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            duration = time.time() - start_time
            
            # Load security report
            security_data = self._load_security_data()
            
            return {
                "type": "security_tests",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "security_report": security_data
            }
            
        except subprocess.TimeoutExpired:
            return {
                "type": "security_tests",
                "duration": time.time() - start_time,
                "return_code": -1,
                "error": "Security tests timed out"
            }
        except FileNotFoundError:
            return {
                "type": "security_tests",
                "duration": time.time() - start_time,
                "return_code": -1,
                "error": "bandit not installed"
            }
    
    def validate_quality_gates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate quality gates based on test results."""
        print("🚪 Validating quality gates...")
        
        gates = []
        
        # Coverage gate
        coverage_gate = {
            "name": "Code Coverage",
            "threshold": 80.0,
            "actual": self.results["coverage"],
            "passed": self.results["coverage"] >= 80.0,
            "details": f"Coverage: {self.results['coverage']:.1f}%"
        }
        gates.append(coverage_gate)
        
        # Test success rate gate
        total_tests = sum(1 for r in results if r["return_code"] == 0)
        success_rate = (total_tests / len(results)) * 100 if results else 0
        
        test_gate = {
            "name": "Test Success Rate",
            "threshold": 100.0,
            "actual": success_rate,
            "passed": success_rate >= 100.0,
            "details": f"Success rate: {success_rate:.1f}%"
        }
        gates.append(test_gate)
        
        # Performance gate
        performance_gate = {
            "name": "Test Performance",
            "threshold": 300.0,  # 5 minutes max
            "actual": self.results["duration"],
            "passed": self.results["duration"] <= 300.0,
            "details": f"Duration: {self.results['duration']:.1f}s"
        }
        gates.append(performance_gate)
        
        # Security gate
        security_result = next((r for r in results if r["type"] == "security_tests"), None)
        security_gate = {
            "name": "Security",
            "threshold": 0,  # No high-severity issues
            "actual": 0,
            "passed": True,
            "details": "No security scanner available"
        }
        
        if security_result and security_result.get("security_report"):
            high_severity = len([
                issue for issue in security_result["security_report"].get("results", [])
                if issue.get("issue_severity") == "HIGH"
            ])
            security_gate.update({
                "actual": high_severity,
                "passed": high_severity == 0,
                "details": f"High severity issues: {high_severity}"
            })
        
        gates.append(security_gate)
        
        self.results["quality_gates"] = gates
        return gates
    
    def _load_coverage_data(self) -> Optional[Dict[str, Any]]:
        """Load coverage data from JSON report."""
        try:
            with open("coverage.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def _load_security_data(self) -> Optional[Dict[str, Any]]:
        """Load security data from JSON report."""
        try:
            with open("security_report.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def generate_report(self, results: List[Dict[str, Any]]) -> None:
        """Generate comprehensive test report."""
        print("\n📊 Test Report")
        print("=" * 50)
        
        # Summary
        passed_gates = sum(1 for gate in self.results["quality_gates"] if gate["passed"])
        total_gates = len(self.results["quality_gates"])
        
        print(f"📅 Timestamp: {self.results['timestamp']}")
        print(f"⏱️  Duration: {self.results['duration']:.1f}s")
        print(f"📈 Coverage: {self.results['coverage']:.1f}%")
        print(f"🚪 Quality Gates: {passed_gates}/{total_gates} passed")
        
        # Test results
        print("\n🧪 Test Results:")
        for result in results:
            status = "✅ PASS" if result["return_code"] == 0 else "❌ FAIL"
            print(f"  {result['type']}: {status} ({result['duration']:.1f}s)")
            
            if result["return_code"] != 0 and "error" in result:
                print(f"    Error: {result['error']}")
        
        # Quality gates
        print("\n🚪 Quality Gates:")
        for gate in self.results["quality_gates"]:
            status = "✅ PASS" if gate["passed"] else "❌ FAIL"
            print(f"  {gate['name']}: {status}")
            print(f"    {gate['details']}")
        
        # Overall result
        all_passed = all(r["return_code"] == 0 for r in results)
        gates_passed = all(gate["passed"] for gate in self.results["quality_gates"])
        overall_passed = all_passed and gates_passed
        
        print(f"\n🎯 Overall Result: {'✅ PASS' if overall_passed else '❌ FAIL'}")
        
        # Save detailed report
        with open("test_report.json", "w") as f:
            json.dump({
                "results": self.results,
                "test_results": results
            }, f, indent=2)
        
        print("\n📄 Detailed report saved to test_report.json")
        print("📊 HTML coverage report available at htmlcov/index.html")
    
    def run_all_tests(self) -> int:
        """Run all tests and return exit code."""
        print("🚀 Starting comprehensive test suite...")
        
        results = []
        
        # Run unit tests
        unit_result = self.run_unit_tests()
        results.append(unit_result)
        
        # Run integration tests
        integration_result = self.run_integration_tests()
        results.append(integration_result)
        
        # Run performance tests
        performance_result = self.run_performance_tests()
        results.append(performance_result)
        
        # Run security tests
        security_result = self.run_security_tests()
        results.append(security_result)
        
        # Validate quality gates
        gates = self.validate_quality_gates(results)
        
        # Generate report
        self.generate_report(results)
        
        # Return exit code
        all_passed = all(r["return_code"] == 0 for r in results)
        gates_passed = all(gate["passed"] for gate in gates)
        
        return 0 if all_passed and gates_passed else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner for LeanVibe Quality Agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--security-only", action="store_true", help="Run only security tests")
    parser.add_argument("--pattern", default="tests/", help="Test pattern to run")
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    if args.unit_only:
        result = runner.run_unit_tests(args.pattern)
        return result["return_code"]
    elif args.integration_only:
        result = runner.run_integration_tests()
        return result["return_code"]
    elif args.performance_only:
        result = runner.run_performance_tests()
        return result["return_code"]
    elif args.security_only:
        result = runner.run_security_tests()
        return result["return_code"]
    else:
        return runner.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())