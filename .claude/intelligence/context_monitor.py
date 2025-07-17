"""
ContextMonitor - Proactive context usage monitoring and prediction system.

Extracted from hook_system.py as part of legacy refactoring.
Monitors and predicts context growth to prevent overflow with intelligent early warning.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict

import numpy as np

from config.config_loader import get_config
from utils.logging_config import get_logger

logger = get_logger('context_monitor')


class ContextMonitor:
    """Proactively manages context to prevent overflow with predictive analytics.

    This system monitors context usage patterns and predicts when intervention
    is needed to prevent context overflow. Uses ML-based growth prediction.
    """

    def __init__(self, db_path: str = None):
        """Initialize the context monitor.

        Args:
            db_path: Optional custom database path. If None, uses config default.
        """
        config = get_config()
        if db_path is None:
            self.db_path = Path(config.get('state_management.context_db_path',
                                        '.claude/state/context_history.db'))
        else:
            self.db_path = Path(db_path)

        self.predictor = ContextGrowthPredictor(self.db_path)
        logger.info(f"ContextMonitor initialized with database: {self.db_path}")

    def check_context(self, agent_id: str, current_usage: float, context: Dict = None) -> Dict:
        """Check context and predict future usage with intelligent recommendations.

        Args:
            agent_id: Unique identifier for the agent
            current_usage: Current context usage as percentage (0.0-1.0)
            context: Optional additional context information

        Returns:
            Dictionary with usage analysis and recommended actions
        """
        if context is None:
            context = {}

        # Record current usage for future predictions
        self.predictor.record_usage(agent_id, current_usage, context)

        # Predict growth
        predicted_growth = self.predictor.predict(agent_id, current_usage)
        time_to_limit = self._estimate_time_to_limit(current_usage, predicted_growth)

        config = get_config()
        thresholds = config.get('intelligence.context.thresholds', {
            'immediate_action': 0.5,      # 30 minutes
            'prepare_checkpoint': 1.0,    # 1 hour
            'monitor_closely': 0.6        # 60% usage
        })

        response = {
            "agent_id": agent_id,
            "current_usage": current_usage,
            "predicted_usage_1h": min(current_usage + predicted_growth, 1.0),
            "predicted_growth_rate": predicted_growth,
            "time_to_limit_hours": time_to_limit,
            "action_required": "none",
            "confidence": self.predictor.get_prediction_confidence(agent_id),
            "timestamp": datetime.now().isoformat()
        }

        # Determine required action based on intelligent thresholds
        if time_to_limit < thresholds['immediate_action']:
            response["action_required"] = "immediate_summarize"
            response["reason"] = f"Context will overflow within {time_to_limit*60:.0f} minutes"
            response["urgency"] = "critical"

        elif time_to_limit < thresholds['prepare_checkpoint']:
            response["action_required"] = "prepare_checkpoint"
            response["reason"] = f"Context will overflow within {time_to_limit:.1f} hours"
            response["urgency"] = "high"

        elif current_usage > thresholds['monitor_closely']:
            response["action_required"] = "monitor_closely"
            response["reason"] = f"Context usage above {thresholds['monitor_closely']*100:.0f}%"
            response["urgency"] = "medium"

        else:
            response["reason"] = "Context usage within normal parameters"
            response["urgency"] = "low"

        logger.debug(
            f"Context check: agent={agent_id}, "
            f"usage={current_usage:.3f}, "
            f"predicted_growth={predicted_growth:.3f}, "
            f"time_to_limit={time_to_limit:.2f}h, "
            f"action={response['action_required']}"
        )

        return response

    def _estimate_time_to_limit(self, current: float, growth_rate: float) -> float:
        """Estimate hours until context limit reached with safety buffer.

        Args:
            current: Current usage percentage (0.0-1.0)
            growth_rate: Predicted hourly growth rate

        Returns:
            Hours until limit reached, or 999.0 if no growth
        """
        if growth_rate <= 0:
            return 999.0  # No growth or negative growth

        config = get_config()
        target_limit = config.get('intelligence.context.target_limit', 0.85)
        remaining = target_limit - current

        return max(0.0, remaining / growth_rate)

    def get_usage_stats(self, agent_id: str = None, hours: int = 24) -> Dict:
        """Get context usage statistics for analysis.

        Args:
            agent_id: Specific agent ID, or None for all agents
            hours: Number of hours of history to analyze

        Returns:
            Dictionary with usage statistics
        """
        return self.predictor.get_usage_stats(agent_id, hours)

    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old context history data.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            Number of records deleted
        """
        return self.predictor.cleanup_old_data(days_to_keep)


class ContextGrowthPredictor:
    """Predicts context growth using historical patterns and machine learning.

    Uses SQLite database to store usage patterns and statistical analysis
    to predict future context growth rates.
    """

    def __init__(self, db_path: Path):
        """Initialize the growth predictor.

        Args:
            db_path: Path to SQLite database for storing history
        """
        self.db_path = db_path
        self._init_db()
        logger.debug(f"ContextGrowthPredictor initialized with database: {db_path}")

    def _init_db(self):
        """Initialize context history database with proper schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS context_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    usage_percent REAL NOT NULL,
                    task_type TEXT,
                    task_count INTEGER DEFAULT 0,
                    growth_rate REAL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS prediction_accuracy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    predicted_growth REAL NOT NULL,
                    actual_growth REAL NOT NULL,
                    prediction_error REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_context_history_agent_time
                    ON context_history(agent_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_context_history_timestamp
                    ON context_history(timestamp);
                CREATE INDEX IF NOT EXISTS idx_prediction_accuracy_agent
                    ON prediction_accuracy(agent_id);
            """)

        logger.debug("Context history database schema initialized successfully")

    def record_usage(self, agent_id: str, usage_percent: float, context: Dict = None) -> None:
        """Record current usage for future predictions.

        Args:
            agent_id: Unique agent identifier
            usage_percent: Current usage as percentage (0.0-1.0)
            context: Optional context information (task_type, etc.)
        """
        if context is None:
            context = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO context_history
                (agent_id, usage_percent, task_type, task_count, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_id,
                    usage_percent,
                    context.get('task_type'),
                    context.get('task_count', 0),
                    datetime.now(),
                    datetime.now()
                )
            )

    def predict(self, agent_id: str, current_usage: float) -> float:
        """Predict hourly growth rate using historical patterns.

        Args:
            agent_id: Agent identifier
            current_usage: Current usage percentage

        Returns:
            Predicted growth rate per hour
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get recent history for this agent
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

        if len(history) < 2:
            # Default conservative estimate
            config = get_config()
            default_growth = config.get('intelligence.context.default_growth_rate', 0.1)
            logger.debug(f"Insufficient history for {agent_id}, using default growth rate: {default_growth}")
            return default_growth

        # Calculate growth rates from historical data
        growth_rates = []
        for i in range(1, len(history)):
            prev_usage, prev_time = history[i-1]
            curr_usage, curr_time = history[i]

            # Parse timestamps and calculate time difference
            if isinstance(prev_time, str):
                prev_time = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
            if isinstance(curr_time, str):
                curr_time = datetime.fromisoformat(curr_time.replace('Z', '+00:00'))

            time_diff_hours = (curr_time - prev_time).total_seconds() / 3600
            usage_diff = curr_usage - prev_usage

            if time_diff_hours > 0:
                growth_rate = usage_diff / time_diff_hours
                growth_rates.append(growth_rate)

        if not growth_rates:
            config = get_config()
            return config.get('intelligence.context.default_growth_rate', 0.1)

        # Use configurable percentile for conservative estimate
        config = get_config()
        percentile = config.get('intelligence.context.growth_percentile', 75)
        predicted_growth = np.percentile(growth_rates, percentile)

        # Apply smoothing and bounds
        min_growth = config.get('intelligence.context.min_growth_rate', 0.0)
        max_growth = config.get('intelligence.context.max_growth_rate', 0.5)
        predicted_growth = max(min_growth, min(max_growth, predicted_growth))

        logger.debug(
            f"Growth prediction for {agent_id}: {predicted_growth:.4f}/hour "
            f"from {len(growth_rates)} samples"
        )

        return predicted_growth

    def get_prediction_confidence(self, agent_id: str) -> float:
        """Get confidence level in predictions for this agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Confidence score between 0.0 and 1.0
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Count recent data points
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM context_history
                WHERE agent_id = ?
                AND timestamp > datetime('now', '-24 hours')
                """,
                (agent_id,)
            )

            recent_count = cursor.fetchone()[0]

            # Get prediction accuracy if available
            cursor.execute(
                """
                SELECT AVG(ABS(prediction_error))
                FROM prediction_accuracy
                WHERE agent_id = ?
                AND timestamp > datetime('now', '-7 days')
                """,
                (agent_id,)
            )

            avg_error = cursor.fetchone()[0] or 0.2

        # Calculate confidence based on data availability and accuracy
        data_confidence = min(1.0, recent_count / 10.0)  # More data = higher confidence
        accuracy_confidence = max(0.1, 1.0 - avg_error)  # Lower error = higher confidence

        return (data_confidence + accuracy_confidence) / 2

    def get_usage_stats(self, agent_id: str = None, hours: int = 24) -> Dict:
        """Get usage statistics for analysis.

        Args:
            agent_id: Specific agent ID, or None for all agents
            hours: Number of hours of history to analyze

        Returns:
            Dictionary with comprehensive usage statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Build query based on whether agent_id is specified
            if agent_id:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_records,
                        AVG(usage_percent) as avg_usage,
                        MAX(usage_percent) as peak_usage,
                        MIN(usage_percent) as min_usage,
                        MAX(timestamp) as last_update
                    FROM context_history
                    WHERE agent_id = ?
                    AND timestamp > datetime('now', '-{} hours')
                    """.format(hours),
                    (agent_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_records,
                        AVG(usage_percent) as avg_usage,
                        MAX(usage_percent) as peak_usage,
                        MIN(usage_percent) as min_usage,
                        MAX(timestamp) as last_update
                    FROM context_history
                    WHERE timestamp > datetime('now', '-{} hours')
                    """.format(hours)
                )

            result = cursor.fetchone()

            return {
                "agent_id": agent_id or "all",
                "hours_analyzed": hours,
                "total_records": result[0] or 0,
                "avg_usage": result[1] or 0.0,
                "peak_usage": result[2] or 0.0,
                "min_usage": result[3] or 0.0,
                "last_update": result[4],
                "data_points_per_hour": (result[0] or 0) / hours if hours > 0 else 0
            }

    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old context history data to prevent database growth.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            Number of records deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Delete old context history
            cursor.execute(
                """
                DELETE FROM context_history
                WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep)
            )
            deleted_history = cursor.rowcount

            # Delete old prediction accuracy data
            cursor.execute(
                """
                DELETE FROM prediction_accuracy
                WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep)
            )
            deleted_accuracy = cursor.rowcount

            total_deleted = deleted_history + deleted_accuracy

        logger.info(f"Cleanup completed: deleted {deleted_history} history records and {deleted_accuracy} accuracy records")
        return total_deleted
