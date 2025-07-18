"""
Unit tests for SmartQualityGate and MetricsCalculator.

Tests extracted from hook_system.py to ensure functionality is preserved
during refactoring process.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from intelligence.confidence_tracker import ConfidenceTracker
from quality.smart_quality_gate import MetricsCalculator, SmartQualityGate

# Add the .claude directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude'))


class TestMetricsCalculator:
    """Test suite for MetricsCalculator functionality."""

    @pytest.fixture
    def calculator(self):
        """Create MetricsCalculator instance."""
        return MetricsCalculator()

    def test_init(self, calculator):
        """Test calculator initialization."""
        assert calculator.config is not None

    @patch('subprocess.run')
    def test_check_tests_passing(self, mock_run, calculator):
        """Test test checking with passing tests."""
        mock_run.return_value = Mock(returncode=0)

        result = calculator._check_tests()

        assert result is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_check_tests_failing(self, mock_run, calculator):
        """Test test checking with failing tests."""
        mock_run.return_value = Mock(returncode=1)

        result = calculator._check_tests()

        assert result is False

    @patch('subprocess.run')
    def test_check_tests_timeout(self, mock_run, calculator):
        """Test test checking with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(['pytest'], 300)

        result = calculator._check_tests()

        assert result is False

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open,
           read_data='{"totals": {"percent_covered": 85.5}}')
    @patch('pathlib.Path.exists')
    def test_get_coverage_success(
            self,
            mock_exists,
            mock_file,
            mock_run,
            calculator):
        """Test coverage calculation with successful result."""
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0)

        result = calculator._get_coverage()

        assert result == 85.5

    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    def test_get_coverage_no_file(self, mock_exists, mock_run, calculator):
        """Test coverage calculation when coverage file doesn't exist."""
        mock_exists.return_value = False
        mock_run.return_value = Mock(returncode=0)

        result = calculator._get_coverage()

        assert result == 0.0

    @patch('subprocess.run')
    def test_check_lint_passing(self, mock_run, calculator):
        """Test lint checking with passing lints."""
        mock_run.return_value = Mock(returncode=0)

        result = calculator._check_lint()

        assert result is True

    @patch('subprocess.run')
    def test_check_lint_failing(self, mock_run, calculator):
        """Test lint checking with failing lints."""
        mock_run.return_value = Mock(returncode=1)

        result = calculator._check_lint()

        assert result is False

    @patch('subprocess.run')
    def test_check_security_no_issues(self, mock_run, calculator):
        """Test security checking with no issues."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"results": []}'
        )

        result = calculator._check_security()

        assert result == 0

    @patch('subprocess.run')
    def test_check_security_with_issues(self, mock_run, calculator):
        """Test security checking with issues found."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"results": [{"issue1": "data"}, {"issue2": "data"}]}'
        )

        result = calculator._check_security()

        assert result == 2

    @patch('subprocess.run')
    def test_check_security_parse_error(self, mock_run, calculator):
        """Test security checking with parse error."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='invalid json'
        )

        result = calculator._check_security()

        assert result == 0

    @patch('pathlib.Path.exists')
    def test_check_performance_no_benchmarks(self, mock_exists, calculator):
        """Test performance checking when no benchmark directory exists."""
        mock_exists.return_value = False

        result = calculator._check_performance()

        assert result is None

    def test_calculate_quality_score_perfect(self, calculator):
        """Test quality score calculation with perfect metrics."""
        metrics = {
            "tests_passed": True,
            "coverage": 100.0,
            "lint_passed": True,
            "security_issues": 0
        }

        score = calculator._calculate_quality_score(metrics)

        assert score == 1.0

    def test_calculate_quality_score_failing_tests(self, calculator):
        """Test quality score calculation with failing tests."""
        metrics = {
            "tests_passed": False,
            "coverage": 100.0,
            "lint_passed": True,
            "security_issues": 0
        }

        score = calculator._calculate_quality_score(metrics)

        # Should be reduced by test weight (default 0.4)
        assert score == 0.6

    def test_calculate_quality_score_low_coverage(self, calculator):
        """Test quality score calculation with low coverage."""
        metrics = {
            "tests_passed": True,
            "coverage": 50.0,
            "lint_passed": True,
            "security_issues": 0
        }

        score = calculator._calculate_quality_score(metrics)

        # Should be reduced by coverage weight
        assert 0.8 < score < 0.9

    def test_calculate_quality_score_security_issues(self, calculator):
        """Test quality score calculation with security issues."""
        metrics = {
            "tests_passed": True,
            "coverage": 100.0,
            "lint_passed": True,
            "security_issues": 3
        }

        score = calculator._calculate_quality_score(metrics)

        # Should be reduced by security penalty
        assert score < 1.0

    def test_calculate_comprehensive(self, calculator):
        """Test comprehensive metric calculation."""
        context = {"file_path": "test.py"}

        with patch.object(calculator, '_check_tests', return_value=True), \
                patch.object(calculator, '_get_coverage', return_value=85.0), \
                patch.object(calculator, '_check_lint', return_value=True), \
                patch.object(calculator, '_check_security', return_value=1), \
                patch.object(calculator, '_check_performance', return_value=None):

            metrics = calculator.calculate(context)

            assert metrics["tests_passed"] is True
            assert metrics["coverage"] == 85.0
            assert metrics["lint_passed"] is True
            assert metrics["security_issues"] == 1
            assert metrics["performance_impact"] is None
            assert "quality_score" in metrics


class TestSmartQualityGate:
    """Test suite for SmartQualityGate functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def mock_confidence_tracker(self):
        """Create mock ConfidenceTracker for testing."""
        mock_tracker = Mock(spec=ConfidenceTracker)
        mock_tracker.should_involve_human.return_value = (False, 0.8)
        mock_tracker.record_outcome.return_value = None
        mock_tracker.get_pattern_stats.return_value = {
            "total_patterns": 10,
            "avg_success_rate": 0.85,
            "total_decisions": 50,
            "last_activity": "2024-01-01T12:00:00"
        }
        return mock_tracker

    @pytest.fixture
    def mock_metrics_calculator(self):
        """Create mock MetricsCalculator for testing."""
        calculator = Mock(spec=MetricsCalculator)
        calculator.calculate.return_value = {
            "tests_passed": True,
            "coverage": 85.0,
            "lint_passed": True,
            "security_issues": 0,
            "performance_impact": None,
            "quality_score": 0.95
        }
        return calculator

    @pytest.fixture
    def quality_gate(self, mock_confidence_tracker, mock_metrics_calculator):
        """Create SmartQualityGate with mocked dependencies."""
        return SmartQualityGate(
            mock_confidence_tracker,
            mock_metrics_calculator)

    def test_init_with_dependencies(
            self,
            mock_confidence_tracker,
            mock_metrics_calculator):
        """Test initialization with provided dependencies."""
        gate = SmartQualityGate(mock_confidence_tracker,
                                mock_metrics_calculator)

        assert gate.confidence_tracker == mock_confidence_tracker
        assert gate.metrics_calculator == mock_metrics_calculator

    def test_init_without_dependencies(self):
        """Test initialization without provided dependencies."""
        with patch('quality.smart_quality_gate.ConfidenceTracker') as mock_ct, \
                patch('quality.smart_quality_gate.MetricsCalculator') as mock_mc:

            SmartQualityGate()

            mock_ct.assert_called_once()
            mock_mc.assert_called_once()

    def test_evaluate_allow_decision(
            self, quality_gate, mock_confidence_tracker):
        """Test evaluation resulting in allow decision."""
        context = {
            "claude_confidence": 0.8,
            "gemini_confidence": 0.85,
            "task_type": "simple_fix"
        }

        # Mock confidence tracker to not require human involvement
        mock_confidence_tracker.should_involve_human.return_value = (
            False, 0.825)

        result = quality_gate.evaluate(context)

        assert result["decision"] == "allow"
        assert result["confidence"] == 0.825
        assert "metrics" in result
        assert "reason" in result
        assert "timestamp" in result

    def test_evaluate_block_decision_tests_failing(
            self, quality_gate, mock_confidence_tracker):
        """Test evaluation resulting in block decision due to failing tests."""
        context = {
            "claude_confidence": 0.8,
            "gemini_confidence": 0.8
        }

        # Mock metrics with failing tests
        quality_gate.metrics_calculator.calculate.return_value = {
            "tests_passed": False,
            "coverage": 85.0,
            "lint_passed": True,
            "security_issues": 0,
            "performance_impact": None,
            "quality_score": 0.5
        }

        result = quality_gate.evaluate(context)

        assert result["decision"] == "block"
        assert "tests failing" in result["reason"]

    def test_evaluate_block_decision_security_issues(
            self, quality_gate, mock_confidence_tracker):
        """Test evaluation resulting in block decision due to security issues."""
        context = {"claude_confidence": 0.9, "gemini_confidence": 0.9}

        # Mock metrics with many security issues
        quality_gate.metrics_calculator.calculate.return_value = {
            "tests_passed": True,
            "coverage": 85.0,
            "lint_passed": True,
            "security_issues": 10,  # Above threshold
            "performance_impact": None,
            "quality_score": 0.3
        }

        result = quality_gate.evaluate(context)

        assert result["decision"] == "block"

    def test_evaluate_review_decision(
            self, quality_gate, mock_confidence_tracker):
        """Test evaluation resulting in review decision."""
        context = {
            "claude_confidence": 0.7,
            "gemini_confidence": 0.7
        }

        # Mock confidence tracker to require human involvement with medium
        # confidence
        mock_confidence_tracker.should_involve_human.return_value = (True, 0.7)

        result = quality_gate.evaluate(context)

        assert result["decision"] == "review"
        assert result["confidence"] == 0.7

    def test_evaluate_with_metrics_calculation_error(
            self, quality_gate, mock_confidence_tracker):
        """Test evaluation when metrics calculation fails."""
        context = {"claude_confidence": 0.8, "gemini_confidence": 0.8}

        # Mock metrics calculator to raise exception
        quality_gate.metrics_calculator.calculate.side_effect = Exception(
            "Calculation failed")
        mock_confidence_tracker.should_involve_human.return_value = (True, 0.8)

        result = quality_gate.evaluate(context)

        # Should use fallback metrics and block
        assert result["decision"] == "block"
        assert result["metrics"]["tests_passed"] is False

    def test_make_decision_allow(self, quality_gate):
        """Test decision making with good metrics and no human needed."""
        metrics = {
            "tests_passed": True,
            "coverage": 85.0,
            "security_issues": 1,
            "quality_score": 0.9
        }

        decision = quality_gate._make_decision(
            metrics, need_human=False, confidence=0.8)

        assert decision == "allow"

    def test_make_decision_block_failing_tests(self, quality_gate):
        """Test decision making blocking due to failing tests."""
        metrics = {
            "tests_passed": False,
            "coverage": 85.0,
            "security_issues": 0
        }

        decision = quality_gate._make_decision(
            metrics, need_human=False, confidence=0.9)

        assert decision == "block"

    def test_make_decision_block_low_coverage(self, quality_gate):
        """Test decision making blocking due to low coverage."""
        metrics = {
            "tests_passed": True,
            "coverage": 40.0,  # Below default threshold
            "security_issues": 0
        }

        decision = quality_gate._make_decision(
            metrics, need_human=False, confidence=0.9)

        assert decision == "block"

    def test_generate_reason_quality_issues(self, quality_gate):
        """Test reason generation with quality issues."""
        metrics = {
            "tests_passed": False,
            "coverage": 65.0,
            "lint_passed": False,
            "security_issues": 2
        }

        reason = quality_gate._generate_reason(
            metrics, need_human=False, decision="block")

        assert "tests failing" in reason
        assert "coverage 65.0%" in reason
        assert "linting issues" in reason
        assert "2 security issues" in reason

    def test_generate_reason_all_passed(self, quality_gate):
        """Test reason generation when all checks pass."""
        metrics = {
            "tests_passed": True,
            "coverage": 90.0,
            "lint_passed": True,
            "security_issues": 0,
            "quality_score": 0.95
        }

        reason = quality_gate._generate_reason(
            metrics, need_human=False, decision="allow")

        assert "All quality checks passed" in reason
        assert "0.95" in reason

    def test_generate_reason_novel_pattern(self, quality_gate):
        """Test reason generation for novel pattern detection."""
        metrics = {
            "tests_passed": True,
            "coverage": 85.0,
            "lint_passed": True,
            "security_issues": 0
        }

        reason = quality_gate._generate_reason(
            metrics, need_human=True, decision="review")

        assert "novel pattern" in reason.lower()

    def test_get_fallback_metrics(self, quality_gate):
        """Test fallback metrics generation."""
        metrics = quality_gate._get_fallback_metrics()

        assert metrics["tests_passed"] is False
        assert metrics["coverage"] == 0.0
        assert metrics["lint_passed"] is False
        assert metrics["security_issues"] == 999
        assert metrics["quality_score"] == 0.0

    def test_get_quality_stats(self, quality_gate, mock_confidence_tracker):
        """Test getting quality statistics."""
        # Mock confidence tracker stats
        mock_confidence_tracker.get_pattern_stats.return_value = {
            "total_patterns": 15,
            "avg_success_rate": 0.85,
            "total_decisions": 100,
            "last_activity": "2024-01-01T12:00:00"
        }

        stats = quality_gate.get_quality_stats(hours=48)

        assert stats["total_patterns"] == 15
        assert stats["avg_success_rate"] == 0.85
        assert stats["total_decisions"] == 100
        assert stats["hours_analyzed"] == 48

    def test_get_quality_stats_error(
            self, quality_gate, mock_confidence_tracker):
        """Test getting quality statistics when error occurs."""
        mock_confidence_tracker.get_pattern_stats.side_effect = Exception(
            "DB error")

        stats = quality_gate.get_quality_stats()

        assert "error" in stats

    @patch('quality.smart_quality_gate.get_config')
    def test_uses_config_settings(self, mock_get_config):
        """Test that quality gate uses configuration settings."""
        mock_config = {
            'quality.security.max_issues': 2,
            'quality.coverage.minimum': 70,
            'quality.confidence.review_threshold': 0.8
        }
        mock_get_config.return_value = Mock()
        mock_get_config.return_value.get.side_effect = lambda key, default: mock_config.get(
            key, default)

        confidence_tracker = Mock(spec=ConfidenceTracker)
        metrics_calculator = Mock(spec=MetricsCalculator)

        gate = SmartQualityGate(confidence_tracker, metrics_calculator)

        # Test with metrics that exceed configured security threshold
        metrics = {
            "tests_passed": True,
            "coverage": 80.0,
            "security_issues": 3,  # Above configured threshold of 2
            "quality_score": 0.8
        }

        decision = gate._make_decision(
            metrics, need_human=False, confidence=0.9)

        # Should block due to exceeding security threshold
        assert decision == "block"

    def test_record_final_outcome(self, quality_gate):
        """Test recording final outcome."""
        # This is mostly a logging operation for now
        quality_gate.record_final_outcome("test_decision_123", "success")

        # Test passes if no exception is raised

    def test_evaluate_comprehensive_flow(
            self, quality_gate, mock_confidence_tracker):
        """Test comprehensive evaluation flow."""
        context = {
            "claude_confidence": 0.85,
            "gemini_confidence": 0.8,
            "task_type": "feature_implementation",
            "file_path": "src/feature.py"
        }

        # Mock dependencies
        mock_confidence_tracker.should_involve_human.return_value = (
            False, 0.825)
        mock_confidence_tracker.record_outcome.return_value = None

        result = quality_gate.evaluate(context)

        # Verify comprehensive response
        assert "decision" in result
        assert "confidence" in result
        assert "metrics" in result
        assert "reason" in result
        assert "learned_pattern" in result
        assert "quality_score" in result
        assert "ml_recommendation" in result
        assert "timestamp" in result

        # Verify confidence tracker was called
        mock_confidence_tracker.should_involve_human.assert_called_once()
        mock_confidence_tracker.record_outcome.assert_called_once()
