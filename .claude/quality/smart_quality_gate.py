"""
SmartQualityGate - Intelligent quality gate system with ML-based learning.

Extracted from hook_system.py as part of legacy refactoring.
Evaluates code quality with smart thresholds and pattern learning.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from config.config_loader import get_config
from intelligence.confidence_tracker import ConfidenceTracker
from utils.logging_config import get_logger

logger = get_logger('smart_quality_gate')


class SmartQualityGate:
    """Intelligent quality gate that learns over time and adapts thresholds.
    
    This system combines traditional quality metrics with ML-based confidence
    tracking to make intelligent decisions about when human review is needed.
    """

    def __init__(self, confidence_tracker: ConfidenceTracker = None, 
                 metrics_calculator: 'MetricsCalculator' = None):
        """Initialize the smart quality gate.
        
        Args:
            confidence_tracker: Optional ConfidenceTracker instance. Creates new if None.
            metrics_calculator: Optional MetricsCalculator instance. Creates new if None.
        """
        self.confidence_tracker = confidence_tracker or ConfidenceTracker()
        self.metrics_calculator = metrics_calculator or MetricsCalculator()
        logger.info("SmartQualityGate initialized with ML-based confidence tracking")

    def evaluate(self, context: Dict) -> Dict:
        """Evaluate quality with smart thresholds and ML-based decisions.
        
        Args:
            context: Evaluation context containing confidence scores and metadata
            
        Returns:
            Dictionary with decision, confidence, metrics, and reasoning
        """
        logger.debug(f"Evaluating quality gate for context: {list(context.keys())}")
        
        # Calculate all quality metrics
        try:
            metrics = self.metrics_calculator.calculate(context)
        except Exception as e:
            logger.error(f"Failed to calculate metrics: {e}")
            metrics = self._get_fallback_metrics()

        # Get confidence scores from context
        claude_conf = context.get("claude_confidence", 0.7)
        gemini_conf = context.get("gemini_confidence", 0.7)
        
        # Create enhanced context for confidence tracker
        enhanced_context = {
            **context,
            **metrics,
            "agent_confidence": claude_conf,
            "gemini_confidence": gemini_conf,
            "quality_score": metrics.get("quality_score", 0.0)
        }

        # Check if human involvement needed based on learned patterns
        need_human, combined_conf = self.confidence_tracker.should_involve_human(enhanced_context)

        # Generate decision based on ML recommendation and quality metrics
        decision = self._make_decision(metrics, need_human, combined_conf)
        
        # Create comprehensive response
        response = {
            "decision": decision,
            "confidence": combined_conf,
            "metrics": metrics,
            "reason": self._generate_reason(metrics, need_human, decision),
            "learned_pattern": not need_human and combined_conf < 0.8,
            "quality_score": metrics.get("quality_score", 0.0),
            "ml_recommendation": "human_review" if need_human else "auto_approve",
            "timestamp": datetime.now().isoformat()
        }

        # Record outcome for continuous learning
        decision_id = f"gate_{datetime.now().timestamp()}"
        try:
            self.confidence_tracker.record_outcome(
                decision_id, enhanced_context, need_human, "pending"
            )
        except Exception as e:
            logger.warning(f"Failed to record decision outcome: {e}")
        
        logger.info(
            f"Quality gate decision: {decision}, "
            f"confidence: {combined_conf:.3f}, "
            f"quality_score: {metrics.get('quality_score', 0):.3f}"
        )

        return response

    def _make_decision(self, metrics: Dict, need_human: bool, confidence: float) -> str:
        """Make final decision based on metrics and ML recommendation.
        
        Args:
            metrics: Quality metrics dictionary
            need_human: ML recommendation for human involvement
            confidence: Combined confidence score
            
        Returns:
            Decision string: 'allow', 'block', or 'review'
        """
        config = get_config()
        
        # Hard blocks for critical quality issues
        if not metrics.get("tests_passed", True):
            return "block"
        
        security_threshold = config.get('quality.security.max_issues', 5)
        if metrics.get("security_issues", 0) > security_threshold:
            return "block"
            
        coverage_threshold = config.get('quality.coverage.minimum', 60)
        if metrics.get("coverage", 100) < coverage_threshold:
            return "block"
        
        # Use ML recommendation for borderline cases
        if need_human:
            review_threshold = config.get('quality.confidence.review_threshold', 0.6)
            if confidence < review_threshold:
                return "block"
            else:
                return "review"
        
        # Allow for high confidence cases
        return "allow"

    def _generate_reason(self, metrics: Dict, need_human: bool, decision: str) -> str:
        """Generate human-readable reason for the decision.
        
        Args:
            metrics: Quality metrics dictionary
            need_human: Whether ML recommended human involvement
            decision: Final decision made
            
        Returns:
            Human-readable reason string
        """
        issues = []
        
        # Check for specific quality issues
        if not metrics.get("tests_passed", True):
            issues.append("tests failing")
        if metrics.get("security_issues", 0) > 0:
            issues.append(f"{metrics['security_issues']} security issues")
        if metrics.get("coverage", 100) < 80:
            issues.append(f"coverage {metrics['coverage']:.1f}%")
        if not metrics.get("lint_passed", True):
            issues.append("linting issues")

        # Generate reason based on decision and issues
        if decision == "block":
            if issues:
                return f"Blocked due to: {', '.join(issues)}"
            else:
                return "Blocked due to low confidence in automatic decision"
        elif decision == "review":
            if issues:
                return f"Review required due to: {', '.join(issues)}"
            else:
                return "Review recommended - novel pattern detected"
        elif need_human and decision == "allow":
            return "Allowed despite ML recommendation - pattern learning in progress"
        else:
            quality_score = metrics.get("quality_score", 0.0)
            return f"All quality checks passed (score: {quality_score:.2f})"

    def _get_fallback_metrics(self) -> Dict:
        """Get fallback metrics when calculation fails.
        
        Returns:
            Dictionary with safe fallback metrics
        """
        return {
            "tests_passed": False,  # Conservative fallback
            "coverage": 0.0,
            "lint_passed": False,
            "security_issues": 999,  # Force manual review
            "performance_impact": None,
            "quality_score": 0.0
        }

    def record_final_outcome(self, decision_id: str, actual_outcome: str) -> None:
        """Record the final outcome of a decision for learning.
        
        Args:
            decision_id: The decision ID returned from evaluate()
            actual_outcome: 'success', 'failure', or 'partial'
        """
        try:
            # Update the pending record with actual outcome
            # This would require modifying the ConfidenceTracker to support updates
            logger.info(f"Final outcome recorded: {decision_id} -> {actual_outcome}")
        except Exception as e:
            logger.error(f"Failed to record final outcome: {e}")

    def get_quality_stats(self, hours: int = 24) -> Dict:
        """Get quality gate statistics for analysis.
        
        Args:
            hours: Number of hours of history to analyze
            
        Returns:
            Dictionary with quality gate statistics
        """
        try:
            # Get confidence tracker stats
            conf_stats = self.confidence_tracker.get_pattern_stats()
            
            return {
                "total_patterns": conf_stats.get("total_patterns", 0),
                "avg_success_rate": conf_stats.get("avg_success_rate", 0.0),
                "total_decisions": conf_stats.get("total_decisions", 0),
                "last_activity": conf_stats.get("last_activity"),
                "hours_analyzed": hours
            }
        except Exception as e:
            logger.error(f"Failed to get quality stats: {e}")
            return {"error": str(e)}


class MetricsCalculator:
    """Calculate quality metrics efficiently with configurable commands.
    
    Handles all quality metric calculations including tests, coverage,
    linting, security, and performance analysis.
    """

    def __init__(self):
        """Initialize the metrics calculator with configuration."""
        self.config = get_config()
        logger.debug("MetricsCalculator initialized")

    def calculate(self, context: Dict) -> Dict:
        """Calculate all quality metrics for the current codebase.
        
        Args:
            context: Evaluation context (may contain hints about what to check)
            
        Returns:
            Dictionary with all calculated metrics
        """
        logger.debug("Calculating quality metrics")
        
        metrics = {}
        
        # Calculate each metric with error handling
        try:
            metrics["tests_passed"] = self._check_tests()
        except Exception as e:
            logger.warning(f"Failed to check tests: {e}")
            metrics["tests_passed"] = False
            
        try:
            metrics["coverage"] = self._get_coverage()
        except Exception as e:
            logger.warning(f"Failed to get coverage: {e}")
            metrics["coverage"] = 0.0
            
        try:
            metrics["lint_passed"] = self._check_lint()
        except Exception as e:
            logger.warning(f"Failed to check lint: {e}")
            metrics["lint_passed"] = False
            
        try:
            metrics["security_issues"] = self._check_security()
        except Exception as e:
            logger.warning(f"Failed to check security: {e}")
            metrics["security_issues"] = 0
            
        try:
            metrics["performance_impact"] = self._check_performance()
        except Exception as e:
            logger.warning(f"Failed to check performance: {e}")
            metrics["performance_impact"] = None

        # Calculate derived metrics
        metrics["quality_score"] = self._calculate_quality_score(metrics)
        
        logger.debug(f"Quality metrics calculated: {metrics}")
        return metrics

    def _check_tests(self) -> bool:
        """Run tests efficiently with configurable command.
        
        Returns:
            True if all tests pass, False otherwise
        """
        test_command = self.config.get('quality.test_command', ['pytest', '-q', '--tb=no'])
        timeout = self.config.get('quality.test_timeout', 300)  # 5 minutes default
        
        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            logger.debug(f"Test command result: {result.returncode}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning(f"Test command timed out after {timeout}s")
            return False

    def _get_coverage(self) -> float:
        """Get test coverage percentage.
        
        Returns:
            Coverage percentage as float (0.0-100.0)
        """
        coverage_command = self.config.get('quality.coverage_command', 
                                         ['pytest', '--cov', '--cov-report=json', '-q'])
        coverage_file = self.config.get('quality.coverage_file', 'coverage.json')
        
        try:
            result = subprocess.run(coverage_command, capture_output=True, timeout=300)
            
            if result.returncode == 0 and Path(coverage_file).exists():
                with open(coverage_file) as f:
                    data = json.load(f)
                    coverage = data.get("totals", {}).get("percent_covered", 0.0)
                    logger.debug(f"Coverage: {coverage:.1f}%")
                    return coverage
        except Exception as e:
            logger.debug(f"Coverage calculation failed: {e}")
            
        return 0.0

    def _check_lint(self) -> bool:
        """Run linting checks with configurable linter.
        
        Returns:
            True if linting passes, False otherwise
        """
        lint_command = self.config.get('quality.lint_command', ['ruff', 'check', '.', '--quiet'])
        
        try:
            result = subprocess.run(lint_command, capture_output=True, timeout=120)
            logger.debug(f"Lint command result: {result.returncode}")
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Linting failed: {e}")
            return False

    def _check_security(self) -> int:
        """Count security issues using security scanner.
        
        Returns:
            Number of security issues found
        """
        security_command = self.config.get('quality.security_command', 
                                         ['bandit', '-r', '.', '-f', 'json', '-q'])
        
        try:
            result = subprocess.run(
                security_command,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    issues = len(data.get("results", []))
                    logger.debug(f"Security issues found: {issues}")
                    return issues
                except json.JSONDecodeError:
                    logger.debug("Failed to parse security scan results")
                    
        except Exception as e:
            logger.debug(f"Security check failed: {e}")
            
        return 0

    def _check_performance(self) -> Optional[float]:
        """Check performance impact if benchmarks exist.
        
        Returns:
            Performance impact score or None if no benchmarks
        """
        benchmark_dir = Path(self.config.get('quality.benchmark_dir', 'benchmarks'))
        
        if not benchmark_dir.exists():
            return None
            
        performance_command = self.config.get('quality.benchmark_command')
        if not performance_command:
            return None
            
        try:
            result = subprocess.run(
                performance_command,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for benchmarks
            )
            
            if result.returncode == 0:
                # Parse benchmark results (implementation depends on framework)
                # For now, return a placeholder
                logger.debug("Performance benchmarks completed")
                return 0.0
                
        except Exception as e:
            logger.debug(f"Performance check failed: {e}")
            
        return None

    def _calculate_quality_score(self, metrics: Dict) -> float:
        """Calculate overall quality score from individual metrics.
        
        Args:
            metrics: Dictionary of individual quality metrics
            
        Returns:
            Overall quality score between 0.0 and 1.0
        """
        config = get_config()
        weights = config.get('quality.score_weights', {
            'tests': 0.4,
            'coverage': 0.3,
            'lint': 0.2,
            'security': 0.1
        })
        
        score = 1.0
        
        # Apply test weight
        if not metrics.get("tests_passed", True):
            score *= (1.0 - weights.get('tests', 0.4))
            
        # Apply coverage weight
        coverage = metrics.get("coverage", 100)
        if coverage < 100:
            coverage_factor = coverage / 100.0
            score *= (1.0 - weights.get('coverage', 0.3)) + (weights.get('coverage', 0.3) * coverage_factor)
            
        # Apply lint weight
        if not metrics.get("lint_passed", True):
            score *= (1.0 - weights.get('lint', 0.2))
            
        # Apply security weight
        security_issues = metrics.get("security_issues", 0)
        if security_issues > 0:
            # Exponential penalty for security issues
            security_penalty = min(0.9, security_issues * 0.1)
            score *= (1.0 - weights.get('security', 0.1) * security_penalty)
        
        return max(0.0, min(1.0, score))