#!/usr/bin/env python3
"""
Test Suite for Quality Gates Framework
Foundation Epic Phase 1: Security and compliance testing

Comprehensive test coverage for quality gates framework
with security validation and deployment readiness checks.
"""

import unittest
import json
from unittest.mock import patch, mock_open
from quality_gates_framework import (
    QualityGatesFramework,
    QualityGate,
    ValidationResult,
    EnforcementLevel,
    SecurityLevel,
    validate_deployment_readiness,
    check_security_compliance
)


class TestQualityGatesFramework(unittest.TestCase):
    """Test cases for Quality Gates Framework."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.framework = QualityGatesFramework()
    
    def test_default_gates_initialization(self):
        """Test default quality gates are properly initialized."""
        self.assertIn("pr_size_limit", self.framework.gates)
        self.assertIn("test_coverage", self.framework.gates)
        self.assertIn("security_scan", self.framework.gates)
        self.assertIn("code_quality", self.framework.gates)
        self.assertIn("performance_check", self.framework.gates)
        
        # Check default values
        pr_gate = self.framework.gates["pr_size_limit"]
        self.assertEqual(pr_gate.threshold, 1000.0)
        self.assertEqual(pr_gate.enforcement_level, EnforcementLevel.STRICT)
    
    def test_pr_size_validation_pass(self):
        """Test PR size validation with passing value."""
        result = self.framework.validate_pr_size(500)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.value, 500)
        self.assertEqual(result.threshold, 1000.0)
        self.assertEqual(len(result.security_implications), 0)
    
    def test_pr_size_validation_fail(self):
        """Test PR size validation with failing value."""
        result = self.framework.validate_pr_size(1500)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.value, 1500)
        self.assertEqual(result.threshold, 1000.0)
        self.assertGreater(len(result.security_implications), 0)
        self.assertIn("Large PRs are harder to review", result.security_implications[0])
    
    def test_test_coverage_validation_pass(self):
        """Test test coverage validation with passing value."""
        result = self.framework.validate_test_coverage(90.0)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.value, 90.0)
        self.assertEqual(result.threshold, 85.0)
        self.assertEqual(len(result.security_implications), 0)
    
    def test_test_coverage_validation_fail(self):
        """Test test coverage validation with failing value."""
        result = self.framework.validate_test_coverage(70.0)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.value, 70.0)
        self.assertEqual(result.threshold, 85.0)
        self.assertGreater(len(result.security_implications), 0)
        self.assertIn("Insufficient test coverage", result.security_implications[0])
    
    def test_security_scan_validation_pass(self):
        """Test security scan validation with passing value."""
        result = self.framework.validate_security_scan(0)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.value, 0)
        self.assertEqual(result.threshold, 0.0)
        self.assertEqual(len(result.security_implications), 0)
    
    def test_security_scan_validation_fail(self):
        """Test security scan validation with failing value."""
        result = self.framework.validate_security_scan(3)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.value, 3)
        self.assertEqual(result.threshold, 0.0)
        self.assertGreater(len(result.security_implications), 0)
        self.assertIn("Critical security issues detected", result.security_implications[0])
    
    def test_code_quality_validation_pass(self):
        """Test code quality validation with passing value."""
        result = self.framework.validate_code_quality(8.5)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.value, 8.5)
        self.assertEqual(result.threshold, 8.0)
        self.assertEqual(len(result.security_implications), 0)
    
    def test_code_quality_validation_fail(self):
        """Test code quality validation with failing value."""
        result = self.framework.validate_code_quality(6.5)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.value, 6.5)
        self.assertEqual(result.threshold, 8.0)
        self.assertGreater(len(result.security_implications), 0)
        self.assertIn("Poor code quality increases security risk", result.security_implications[0])
    
    def test_performance_validation_pass(self):
        """Test performance validation with passing value."""
        result = self.framework.validate_performance(75.0)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.value, 75.0)
        self.assertEqual(result.threshold, 70.0)
        self.assertEqual(len(result.security_implications), 0)
    
    def test_performance_validation_fail(self):
        """Test performance validation with failing value."""
        result = self.framework.validate_performance(60.0)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.value, 60.0)
        self.assertEqual(result.threshold, 70.0)
        self.assertGreater(len(result.security_implications), 0)
        self.assertIn("Performance degradation may indicate", result.security_implications[0])
    
    def test_validate_all_gates_pass(self):
        """Test validation of all gates with passing metrics."""
        metrics = {
            "pr_size": 500,
            "test_coverage": 90.0,
            "security_critical_issues": 0,
            "code_quality_score": 8.5,
            "performance_score": 75.0
        }
        
        results = self.framework.validate_all_gates(metrics)
        
        self.assertEqual(len(results), 5)
        for result in results.values():
            self.assertTrue(result.passed)
    
    def test_validate_all_gates_mixed(self):
        """Test validation of all gates with mixed results."""
        metrics = {
            "pr_size": 1200,  # Fail
            "test_coverage": 90.0,  # Pass
            "security_critical_issues": 2,  # Fail
            "code_quality_score": 8.5,  # Pass
            "performance_score": 60.0  # Fail
        }
        
        results = self.framework.validate_all_gates(metrics)
        
        self.assertEqual(len(results), 5)
        self.assertFalse(results["pr_size_limit"].passed)
        self.assertTrue(results["test_coverage"].passed)
        self.assertFalse(results["security_scan"].passed)
        self.assertTrue(results["code_quality"].passed)
        self.assertFalse(results["performance_check"].passed)
    
    def test_should_block_deployment_strict_failure(self):
        """Test deployment blocking with strict enforcement failure."""
        metrics = {
            "pr_size": 1500,  # Strict failure
            "test_coverage": 90.0,
            "security_critical_issues": 0,
            "code_quality_score": 8.5,
            "performance_score": 75.0
        }
        
        results = self.framework.validate_all_gates(metrics)
        should_block = self.framework.should_block_deployment(results)
        
        self.assertTrue(should_block)
    
    def test_should_block_deployment_warning_pass(self):
        """Test deployment not blocked with warning level failure."""
        metrics = {
            "pr_size": 500,
            "test_coverage": 90.0,
            "security_critical_issues": 0,
            "code_quality_score": 6.0,  # Warning level failure
            "performance_score": 60.0  # Warning level failure
        }
        
        results = self.framework.validate_all_gates(metrics)
        should_block = self.framework.should_block_deployment(results)
        
        self.assertFalse(should_block)
    
    def test_should_block_deployment_high_security_warning(self):
        """Test deployment blocked with high security warning failure."""
        metrics = {
            "pr_size": 500,
            "test_coverage": 80.0,  # High security warning failure
            "security_critical_issues": 0,
            "code_quality_score": 8.5,
            "performance_score": 75.0
        }
        
        results = self.framework.validate_all_gates(metrics)
        should_block = self.framework.should_block_deployment(results)
        
        self.assertTrue(should_block)
    
    def test_get_security_summary(self):
        """Test security summary generation."""
        metrics = {
            "pr_size": 1200,
            "test_coverage": 70.0,
            "security_critical_issues": 2,
            "code_quality_score": 6.0,
            "performance_score": 60.0
        }
        
        results = self.framework.validate_all_gates(metrics)
        security_summary = self.framework.get_security_summary(results)
        
        self.assertIn("high_risk_failures", security_summary)
        self.assertIn("security_issues", security_summary)
        self.assertIn("deployment_blocked", security_summary)
        self.assertIn("security_score", security_summary)
        
        # Should have high risk failures
        self.assertGreater(len(security_summary["high_risk_failures"]), 0)
        self.assertGreater(len(security_summary["security_issues"]), 0)
        self.assertTrue(security_summary["deployment_blocked"])
        self.assertLess(security_summary["security_score"], 50.0)
    
    def test_calculate_security_score_perfect(self):
        """Test security score calculation with perfect results."""
        metrics = {
            "pr_size": 500,
            "test_coverage": 95.0,
            "security_critical_issues": 0,
            "code_quality_score": 9.0,
            "performance_score": 85.0
        }
        
        results = self.framework.validate_all_gates(metrics)
        security_score = self.framework._calculate_security_score(results)
        
        self.assertEqual(security_score, 100.0)
    
    def test_calculate_security_score_mixed(self):
        """Test security score calculation with mixed results."""
        metrics = {
            "pr_size": 1200,  # Medium security failure
            "test_coverage": 70.0,  # High security failure
            "security_critical_issues": 1,  # High security failure
            "code_quality_score": 8.5,  # Medium security pass
            "performance_score": 75.0  # Low security pass
        }
        
        results = self.framework.validate_all_gates(metrics)
        security_score = self.framework._calculate_security_score(results)
        
        self.assertGreater(security_score, 0.0)
        self.assertLess(security_score, 100.0)
    
    def test_generate_compliance_report(self):
        """Test compliance report generation."""
        metrics = {
            "pr_size": 800,
            "test_coverage": 88.0,
            "security_critical_issues": 0,
            "code_quality_score": 8.2,
            "performance_score": 72.0
        }
        
        results = self.framework.validate_all_gates(metrics)
        report = self.framework.generate_compliance_report(results)
        
        self.assertIn("timestamp", report)
        self.assertIn("gates_passed", report)
        self.assertIn("gates_total", report)
        self.assertIn("compliance_rate", report)
        self.assertIn("deployment_ready", report)
        self.assertIn("security_summary", report)
        self.assertIn("validation_results", report)
        self.assertIn("gates_configuration", report)
        
        self.assertEqual(report["gates_passed"], 5)
        self.assertEqual(report["gates_total"], 5)
        self.assertEqual(report["compliance_rate"], 100.0)
        self.assertTrue(report["deployment_ready"])
    
    @patch("builtins.open", new_callable=mock_open, read_data='{"quality_gates": {"max_pr_size": 800}, "enforcement_level": "warning"}')
    def test_load_config(self, mock_file):
        """Test configuration loading from file."""
        framework = QualityGatesFramework()
        
        # Check updated values
        self.assertEqual(framework.gates["pr_size_limit"].threshold, 800.0)
        self.assertEqual(framework.gates["pr_size_limit"].enforcement_level, EnforcementLevel.WARNING)
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization."""
        result = ValidationResult(
            gate_name="test_gate",
            passed=True,
            value=85.0,
            threshold=80.0,
            message="Test passed",
            security_implications=[]
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict["gate_name"], "test_gate")
        self.assertTrue(result_dict["passed"])
        self.assertEqual(result_dict["value"], 85.0)
        self.assertEqual(result_dict["threshold"], 80.0)
        self.assertEqual(result_dict["message"], "Test passed")
        self.assertEqual(result_dict["security_implications"], [])
    
    def test_quality_gate_to_dict(self):
        """Test QualityGate serialization."""
        gate = QualityGate(
            name="test_gate",
            description="Test gate",
            threshold=80.0,
            enforcement_level=EnforcementLevel.STRICT,
            security_level=SecurityLevel.HIGH
        )
        
        gate_dict = gate.to_dict()
        
        self.assertEqual(gate_dict["name"], "test_gate")
        self.assertEqual(gate_dict["description"], "Test gate")
        self.assertEqual(gate_dict["threshold"], 80.0)
        self.assertEqual(gate_dict["enforcement_level"], "strict")
        self.assertEqual(gate_dict["security_level"], "high")
        self.assertTrue(gate_dict["required"])


class TestQualityGatesAPI(unittest.TestCase):
    """Test cases for Quality Gates API functions."""
    
    def test_validate_deployment_readiness(self):
        """Test deployment readiness validation API."""
        metrics = {
            "pr_size": 750,
            "test_coverage": 87.0,
            "security_critical_issues": 0,
            "code_quality_score": 8.3,
            "performance_score": 74.0
        }
        
        report = validate_deployment_readiness(metrics)
        
        self.assertIn("deployment_ready", report)
        self.assertIn("compliance_rate", report)
        self.assertIn("security_summary", report)
        self.assertTrue(report["deployment_ready"])
        self.assertEqual(report["compliance_rate"], 100.0)
    
    def test_check_security_compliance(self):
        """Test security compliance check API."""
        metrics = {
            "pr_size": 1200,
            "test_coverage": 75.0,
            "security_critical_issues": 1,
            "code_quality_score": 7.0,
            "performance_score": 65.0
        }
        
        security_summary = check_security_compliance(metrics)
        
        self.assertIn("high_risk_failures", security_summary)
        self.assertIn("security_issues", security_summary)
        self.assertIn("deployment_blocked", security_summary)
        self.assertIn("security_score", security_summary)
        
        self.assertGreater(len(security_summary["high_risk_failures"]), 0)
        self.assertTrue(security_summary["deployment_blocked"])
        self.assertLess(security_summary["security_score"], 100.0)


if __name__ == "__main__":
    unittest.main()