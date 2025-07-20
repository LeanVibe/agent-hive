"""
ConfidenceTracker - ML-based decision learning system.

Extracted from hook_system.py as part of legacy refactoring.
Tracks and learns optimal confidence thresholds for human intervention decisions.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from config.config_loader import get_config
from utils.logging_config import get_logger

logger = get_logger('confidence_tracker')


class ConfidenceTracker:
    """Tracks and learns optimal confidence thresholds for decision making.

    This ML system learns from past decisions to optimize when human intervention
    is needed. It uses SQLite for persistent storage and pattern recognition.
    """

    def __init__(self, db_path: str = None):
        """Initialize the confidence tracker.

        Args:
            db_path: Optional custom database path. If None, uses config default.
        """
        config = get_config()
        if db_path is None:
            self.db_path = Path(config.get('state_management.confidence_db_path',
                                        '.claude/state/confidence.db'))
        else:
            self.db_path = Path(db_path)

        self._init_db()
        logger.info(f"ConfidenceTracker initialized with database: {self.db_path}")

    def _init_db(self):
        """Initialize confidence tracking database with proper schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    context_hash TEXT NOT NULL,
                    agent_confidence REAL NOT NULL,
                    gemini_confidence REAL NOT NULL,
                    human_involved BOOLEAN NOT NULL,
                    outcome TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_hash TEXT PRIMARY KEY,
                    success_rate REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                -- Add indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_decisions_context_hash
                    ON decisions(context_hash);
                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp
                    ON decisions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_patterns_success_rate
                    ON patterns(success_rate);
            """)

        logger.debug("Database schema initialized successfully")

    def should_involve_human(self, context: Dict) -> Tuple[bool, float]:
        """Decide if human involvement is needed based on learned patterns.

        Args:
            context: Decision context containing confidence scores and risk factors

        Returns:
            Tuple of (should_involve_human: bool, combined_confidence: float)
        """
        context_hash = self._hash_context(context)

        # Check if we've seen similar patterns with high success rate
        with sqlite3.connect(self.db_path) as conn:
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

        # If we have enough samples and high success rate, proceed autonomously
        config = get_config()
        min_samples = config.get('intelligence.confidence.min_samples', 5)
        high_success_threshold = config.get('intelligence.confidence.high_success_threshold', 0.9)

        if result and result[1] >= min_samples:
            success_rate = result[0]
            if success_rate > high_success_threshold:
                logger.debug(f"High success pattern found: {success_rate:.3f} from {result[1]} samples")
                return False, success_rate

        # Calculate combined confidence score
        agent_conf = context.get("agent_confidence", 0.7)
        gemini_conf = context.get("gemini_confidence", 0.7)
        combined = (agent_conf + gemini_conf) / 2

        # Apply dynamic threshold based on risk assessment
        risk_score = self._calculate_risk(context)
        base_threshold = config.get('intelligence.confidence.base_threshold', 0.75)
        high_risk_threshold = config.get('intelligence.confidence.high_risk_threshold', 0.85)

        threshold = high_risk_threshold if risk_score > 0.7 else base_threshold

        should_involve = combined < threshold

        logger.debug(
            f"Decision: involve_human={should_involve}, "
            f"combined_confidence={combined:.3f}, "
            f"threshold={threshold:.3f}, "
            f"risk_score={risk_score:.3f}"
        )

        return should_involve, combined

    def record_outcome(
        self, decision_id: str, context: Dict, human_involved: bool, outcome: str
    ) -> None:
        """Record decision outcome for learning and pattern recognition.

        Args:
            decision_id: Unique identifier for this decision
            context: The decision context that was used
            human_involved: Whether human intervention was used
            outcome: Result of the decision ('success', 'failure', 'partial')
        """
        context_hash = self._hash_context(context)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Record the decision
            cursor.execute(
                """
                INSERT OR REPLACE INTO decisions
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    context_hash,
                    context.get("agent_confidence", 0.0),
                    context.get("gemini_confidence", 0.0),
                    human_involved,
                    outcome,
                    datetime.now(),
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
            success_rate = successes / total if total > 0 else 0.0

            cursor.execute(
                """
                INSERT OR REPLACE INTO patterns
                VALUES (?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM patterns WHERE pattern_hash = ?),
                    ?
                ))
                """,
                (context_hash, success_rate, total, datetime.now(), context_hash, datetime.now()),
            )

        logger.info(
            f"Recorded outcome: decision_id={decision_id}, "
            f"outcome={outcome}, "
            f"pattern_success_rate={success_rate:.3f}, "
            f"total_samples={total}"
        )

    def get_pattern_stats(self, context: Dict = None) -> Dict:
        """Get statistics about learned patterns.

        Args:
            context: Optional context to get stats for specific pattern

        Returns:
            Dictionary with pattern statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if context:
                context_hash = self._hash_context(context)
                cursor.execute(
                    """
                    SELECT success_rate, sample_count, last_updated
                    FROM patterns
                    WHERE pattern_hash = ?
                    """,
                    (context_hash,),
                )
                result = cursor.fetchone()

                if result:
                    return {
                        "success_rate": result[0],
                        "sample_count": result[1],
                        "last_updated": result[2],
                        "pattern_hash": context_hash
                    }
                else:
                    return {"pattern_hash": context_hash, "sample_count": 0}
            else:
                # Get overall statistics
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_patterns,
                        AVG(success_rate) as avg_success_rate,
                        SUM(sample_count) as total_decisions,
                        MAX(last_updated) as last_activity
                    FROM patterns
                    """
                )
                result = cursor.fetchone()

                return {
                    "total_patterns": result[0] or 0,
                    "avg_success_rate": result[1] or 0.0,
                    "total_decisions": result[2] or 0,
                    "last_activity": result[3]
                }

    def _hash_context(self, context: Dict) -> str:
        """Create hash of context for pattern matching.

        Args:
            context: Decision context dictionary

        Returns:
            16-character hash string for pattern identification
        """
        # Extract key features that affect decision patterns
        features = {
            "task_type": context.get("task_type", ""),
            "complexity": context.get("complexity", "medium"),
            "has_architecture_changes": context.get("has_architecture_changes", False),
            "has_security_implications": context.get("has_security_implications", False),
            "affects_performance": context.get("affects_performance", False),
        }

        feature_str = json.dumps(features, sort_keys=True)
        return hashlib.md5(feature_str.encode(), usedforsecurity=False).hexdigest()[:16]

    def _calculate_risk(self, context: Dict) -> float:
        """Calculate risk score for decision context.

        Args:
            context: Decision context dictionary

        Returns:
            Risk score between 0.0 and 1.0
        """
        config = get_config()
        risk_factors = config.get('intelligence.confidence.risk_factors', {
            "has_architecture_changes": 0.3,
            "has_security_implications": 0.4,
            "affects_performance": 0.2,
            "is_customer_facing": 0.3,
            "modifies_critical_path": 0.4,
        })

        risk_score = 0.0
        for factor, weight in risk_factors.items():
            if context.get(factor, False):
                risk_score += weight

        return min(risk_score, 1.0)

    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Clean up old decision data to prevent database growth.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            Number of records deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Delete old decisions
            cursor.execute(
                """
                DELETE FROM decisions 
                WHERE timestamp < datetime('now', ? || ' days')
                """, (f'-{days_to_keep}',)
            )
            deleted_decisions = cursor.rowcount

            # Update patterns based on remaining decisions
            cursor.execute("""
                UPDATE patterns
                SET
                    sample_count = (
                        SELECT COUNT(*)
                        FROM decisions
                        WHERE decisions.context_hash = patterns.pattern_hash
                    ),
                    success_rate = (
                        SELECT
                            CAST(SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) AS REAL) / COUNT(*)
                        FROM decisions
                        WHERE decisions.context_hash = patterns.pattern_hash
                    ),
                    last_updated = datetime('now')
                WHERE pattern_hash IN (
                    SELECT DISTINCT context_hash FROM decisions
                )
            """)

            # Remove patterns with no remaining decisions
            cursor.execute("""
                DELETE FROM patterns
                WHERE pattern_hash NOT IN (
                    SELECT DISTINCT context_hash FROM decisions
                )
            """)
            deleted_patterns = cursor.rowcount

        logger.info(f"Cleanup completed: deleted {deleted_decisions} decisions and {deleted_patterns} patterns")
        return deleted_decisions + deleted_patterns
