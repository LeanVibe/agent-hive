#!/usr/bin/env python3
"""
LeanVibe Smart Hook System - XP with minimal friction
"""

import asyncio
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ===== Smart Test Enforcer =====


class SmartTestEnforcer:
    """Ensures tests exist without blocking development"""

    def __init__(self):
        self.test_patterns = {
            "python": [
                "tests/test_{stem}.py",
                "tests/{stem}_test.py",
                "{dir}/test_{stem}.py",
            ],
            "javascript": [
                "{stem}.test.{ext}",
                "{stem}.spec.{ext}",
                "__tests__/{stem}.test.{ext}",
            ],
            "swift": ["{stem}Tests.swift", "Tests/{stem}Tests.swift"],
        }

    def check_and_generate(self, file_path: str) -> bool:
        """Check for tests, generate if missing"""
        path = Path(file_path)

        # Skip non-code files
        if not self._is_code_file(path):
            return True

        # Check if tests exist
        if self._find_existing_tests(path):
            return True

        # Generate tests asynchronously
        asyncio.create_task(self._generate_tests_async(path))

        # Don't block development
        print(f"Generating tests for {file_path} in background...")
        return True

    async def _generate_tests_async(self, path: Path):
        """Generate tests using Gemini without blocking"""
        content = path.read_text()

        prompt = f"""Generate comprehensive tests for this code:
        
{content}

Include:
- Edge cases
- Error handling
- Performance tests where applicable
- Mocks for external dependencies

Output only the test code, no explanations.
"""

        # Call Gemini
        result = subprocess.run(
            ["gemini", "--model", "gemini-1.5-flash", "--quiet"],
            input=prompt,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            test_path = self._get_test_path(path)
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(result.stdout)
            print(f"✅ Tests generated: {test_path}")


# ===== Intelligent Confidence Tracker =====


class ConfidenceTracker:
    """Tracks and learns optimal confidence thresholds"""

    def __init__(self):
        self.db_path = Path(".claude/state/confidence.db")
        self._init_db()

    def _init_db(self):
        """Initialize confidence tracking database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                context_hash TEXT,
                agent_confidence REAL,
                gemini_confidence REAL,
                human_involved BOOLEAN,
                outcome TEXT,
                timestamp TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS patterns (
                pattern_hash TEXT PRIMARY KEY,
                success_rate REAL,
                sample_count INTEGER,
                last_updated TIMESTAMP
            );
        """)
        conn.close()

    def should_involve_human(self, context: Dict) -> Tuple[bool, float]:
        """Decide if human involvement needed based on learned patterns"""

        # Get context hash for pattern matching
        context_hash = self._hash_context(context)

        # Check if we've seen similar patterns
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT success_rate, sample_count 
            FROM patterns 
            WHERE pattern_hash = ?
        """,
            (context_hash,),
        )

        result = cursor.fetchone()
        conn.close()

        if result and result[1] >= 5:  # Need at least 5 samples
            success_rate = result[0]
            if success_rate > 0.9:
                return False, success_rate

        # Calculate combined confidence
        agent_conf = context.get("agent_confidence", 0.7)
        gemini_conf = context.get("gemini_confidence", 0.7)
        combined = (agent_conf + gemini_conf) / 2

        # Dynamic threshold based on risk
        risk_score = self._calculate_risk(context)
        threshold = 0.85 if risk_score > 0.7 else 0.75

        return combined < threshold, combined

    def record_outcome(
        self, decision_id: str, context: Dict, human_involved: bool, outcome: str
    ):
        """Record decision outcome for learning"""
        context_hash = self._hash_context(context)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Record decision
        cursor.execute(
            """
            INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                decision_id,
                context_hash,
                context.get("agent_confidence", 0),
                context.get("gemini_confidence", 0),
                human_involved,
                outcome,
                datetime.now(),
            ),
        )

        # Update pattern statistics
        cursor.execute(
            """
            SELECT COUNT(*), SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END)
            FROM decisions
            WHERE context_hash = ?
        """,
            (context_hash,),
        )

        total, successes = cursor.fetchone()
        success_rate = successes / total if total > 0 else 0

        cursor.execute(
            """
            INSERT OR REPLACE INTO patterns VALUES (?, ?, ?, ?)
        """,
            (context_hash, success_rate, total, datetime.now()),
        )

        conn.commit()
        conn.close()

    def _hash_context(self, context: Dict) -> str:
        """Create hash of context for pattern matching"""
        # Extract key features
        features = {
            "task_type": context.get("task_type", ""),
            "complexity": context.get("complexity", "medium"),
            "has_architecture_changes": context.get("has_architecture_changes", False),
            "has_security_implications": context.get(
                "has_security_implications", False
            ),
            "affects_performance": context.get("affects_performance", False),
        }

        feature_str = json.dumps(features, sort_keys=True)
        return hashlib.md5(feature_str.encode()).hexdigest()[:16]

    def _calculate_risk(self, context: Dict) -> float:
        """Calculate risk score for decision"""
        risk_factors = {
            "has_architecture_changes": 0.3,
            "has_security_implications": 0.4,
            "affects_performance": 0.2,
            "is_customer_facing": 0.3,
            "modifies_critical_path": 0.4,
        }

        risk_score = 0.0
        for factor, weight in risk_factors.items():
            if context.get(factor, False):
                risk_score += weight

        return min(risk_score, 1.0)


# ===== Context Monitor Hook =====


class ContextMonitorHook:
    """Proactively manages context to prevent overflow"""

    def __init__(self):
        self.predictor = ContextGrowthPredictor()

    def check_context(self, agent_id: str, current_usage: float) -> Dict:
        """Check context and predict future usage"""

        # Predict growth
        predicted_growth = self.predictor.predict(agent_id, current_usage)
        time_to_limit = self._estimate_time_to_limit(current_usage, predicted_growth)

        response = {
            "current_usage": current_usage,
            "predicted_usage_1h": current_usage + predicted_growth,
            "time_to_limit_hours": time_to_limit,
            "action_required": "none",
        }

        if time_to_limit < 0.5:  # 30 minutes
            response["action_required"] = "immediate_summarize"
            response["reason"] = "Context will overflow within 30 minutes"

        elif time_to_limit < 1.0:  # 1 hour
            response["action_required"] = "prepare_checkpoint"
            response["reason"] = "Context will overflow within 1 hour"

        elif current_usage > 0.6:
            response["action_required"] = "monitor_closely"
            response["reason"] = "Context usage above 60%"

        return response

    def _estimate_time_to_limit(self, current: float, growth_rate: float) -> float:
        """Estimate hours until context limit reached"""
        if growth_rate <= 0:
            return 999.0  # No growth

        remaining = 0.85 - current  # Target 85% to leave buffer
        return remaining / growth_rate


class ContextGrowthPredictor:
    """Predicts context growth using historical patterns"""

    def __init__(self):
        self.history_db = Path(".claude/state/context_history.db")
        self._init_db()

    def _init_db(self):
        self.history_db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.history_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_history (
                agent_id TEXT,
                timestamp TIMESTAMP,
                usage_percent REAL,
                task_type TEXT,
                task_count INTEGER
            )
        """)
        conn.close()

    def predict(self, agent_id: str, current_usage: float) -> float:
        """Predict hourly growth rate"""
        conn = sqlite3.connect(self.history_db)
        cursor = conn.cursor()

        # Get recent history
        cursor.execute(
            """
            SELECT usage_percent, timestamp
            FROM context_history
            WHERE agent_id = ? 
            AND timestamp > datetime('now', '-6 hours')
            ORDER BY timestamp
        """,
            (agent_id,),
        )

        history = cursor.fetchall()
        conn.close()

        if len(history) < 2:
            # Default conservative estimate
            return 0.1  # 10% per hour

        # Calculate growth rates
        growth_rates = []
        for i in range(1, len(history)):
            time_diff = (history[i][1] - history[i - 1][1]).total_seconds() / 3600
            usage_diff = history[i][0] - history[i - 1][0]
            if time_diff > 0:
                growth_rates.append(usage_diff / time_diff)

        # Use 75th percentile for conservative estimate
        return np.percentile(growth_rates, 75) if growth_rates else 0.1


# ===== Quality Gate Hook =====


class SmartQualityGate:
    """Intelligent quality gate that learns over time"""

    def __init__(self):
        self.confidence_tracker = ConfidenceTracker()
        self.metrics_calculator = MetricsCalculator()

    def evaluate(self, context: Dict) -> Dict:
        """Evaluate quality with smart thresholds"""

        # Calculate all metrics
        metrics = self.metrics_calculator.calculate(context)

        # Get confidence scores
        claude_conf = context.get("claude_confidence", 0.7)
        gemini_conf = context.get("gemini_confidence", 0.7)

        # Check if human needed based on patterns
        need_human, combined_conf = self.confidence_tracker.should_involve_human(
            {
                **context,
                **metrics,
                "agent_confidence": claude_conf,
                "gemini_confidence": gemini_conf,
            }
        )

        # Generate decision
        decision = "block" if need_human else "allow"

        # Create response
        response = {
            "decision": decision,
            "confidence": combined_conf,
            "metrics": metrics,
            "reason": self._generate_reason(metrics, need_human),
            "learned_pattern": not need_human and combined_conf < 0.8,
        }

        # Record for learning
        decision_id = f"gate_{datetime.now().timestamp()}"
        self.confidence_tracker.record_outcome(
            decision_id, context, need_human, "pending"
        )

        return response

    def _generate_reason(self, metrics: Dict, need_human: bool) -> str:
        """Generate human-readable reason"""
        issues = []

        if not metrics.get("tests_passed", True):
            issues.append("tests failing")
        if metrics.get("security_issues", 0) > 0:
            issues.append(f"{metrics['security_issues']} security issues")
        if metrics.get("coverage", 100) < 80:
            issues.append(f"coverage {metrics['coverage']:.1f}%")

        if issues:
            return f"Quality issues: {', '.join(issues)}"
        elif need_human:
            return "Novel pattern requires human review"
        else:
            return "All quality checks passed"


class MetricsCalculator:
    """Calculate quality metrics efficiently"""

    def calculate(self, context: Dict) -> Dict:
        """Calculate all quality metrics"""
        metrics = {
            "tests_passed": self._check_tests(),
            "coverage": self._get_coverage(),
            "lint_passed": self._check_lint(),
            "security_issues": self._check_security(),
            "performance_impact": self._check_performance(),
        }

        # Add derived metrics
        metrics["quality_score"] = self._calculate_quality_score(metrics)

        return metrics

    def _check_tests(self) -> bool:
        """Run tests efficiently"""
        result = subprocess.run(["pytest", "-q", "--tb=no"], capture_output=True)
        return result.returncode == 0

    def _get_coverage(self) -> float:
        """Get test coverage percentage"""
        result = subprocess.run(
            ["pytest", "--cov", "--cov-report=json", "-q"], capture_output=True
        )

        if result.returncode == 0 and Path("coverage.json").exists():
            with open("coverage.json") as f:
                data = json.load(f)
                return data.get("totals", {}).get("percent_covered", 0.0)
        return 0.0

    def _check_lint(self) -> bool:
        """Run linting checks"""
        result = subprocess.run(["ruff", "check", ".", "--quiet"], capture_output=True)
        return result.returncode == 0

    def _check_security(self) -> int:
        """Count security issues"""
        result = subprocess.run(
            ["bandit", "-r", ".", "-f", "json", "-q"], capture_output=True, text=True
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return len(data.get("results", []))
            except:
                pass
        return 0

    def _check_performance(self) -> Optional[float]:
        """Check performance impact if benchmarks exist"""
        if not Path("benchmarks").exists():
            return None

        # Run benchmarks and compare to baseline
        # Implementation depends on benchmark framework
        return None

    def _calculate_quality_score(self, metrics: Dict) -> float:
        """Calculate overall quality score"""
        score = 1.0

        if not metrics["tests_passed"]:
            score *= 0.5
        if metrics["coverage"] < 80:
            score *= metrics["coverage"] / 100
        if not metrics["lint_passed"]:
            score *= 0.8
        if metrics["security_issues"] > 0:
            score *= max(0.5, 1.0 - (metrics["security_issues"] * 0.1))

        return score


# ===== Main Hook Handler =====


def main():
    """Main hook entry point"""
    # Read hook input
    hook_data = json.load(sys.stdin)

    hook_type = hook_data.get("hook_type")
    context = hook_data.get("context", {})

    if hook_type == "pre-commit":
        # Run quality checks
        gate = SmartQualityGate()
        result = gate.evaluate(context)

        print(json.dumps(result))
        sys.exit(0 if result["decision"] == "allow" else 1)

    elif hook_type == "test-check":
        # Ensure tests exist
        enforcer = SmartTestEnforcer()
        file_path = context.get("file_path")

        if file_path:
            success = enforcer.check_and_generate(file_path)
            sys.exit(0 if success else 1)

    elif hook_type == "context-monitor":
        # Check context usage
        monitor = ContextMonitorHook()
        agent_id = context.get("agent_id")
        usage = context.get("context_usage", 0.0)

        result = monitor.check_context(agent_id, usage)
        print(json.dumps(result))
        sys.exit(0)

    else:
        print(f"Unknown hook type: {hook_type}")
        sys.exit(1)


if __name__ == "__main__":
    main()
