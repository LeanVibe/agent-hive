"""
PatternOptimizer - ML-based workflow optimization and pattern recognition

Analyzes historical workflow data to identify patterns and optimize task distribution
and execution strategies within the multi-agent coordination system.
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score

from .models import MLConfig, PatternData, WorkflowOptimization


logger = logging.getLogger(__name__)


class PatternOptimizer:
    """
    Advanced pattern recognition and workflow optimization using machine learning.

    This component analyzes historical workflow data to:
    - Identify recurring patterns in task execution
    - Optimize task distribution strategies
    - Predict optimal resource allocation
    - Recommend workflow improvements
    """

    def __init__(self, config: Optional[MLConfig] = None, db_path: Optional[str] = None):
        """Initialize PatternOptimizer with configuration and database."""
        self.config = config or MLConfig()
        self.db_path = db_path or "pattern_optimizer.db"
        self.scaler = StandardScaler()
        self.cluster_model: Optional[KMeans] = None
        self.performance_model: Optional[RandomForestRegressor] = None
        self.model_version = "1.0.0"

        # Initialize database
        self._init_database()

        # Feature columns for ML models
        self.feature_columns = [
            'task_complexity', 'agent_count', 'resource_usage',
            'queue_size', 'time_of_day', 'day_of_week',
            'historical_success_rate', 'avg_completion_time'
        ]

        logger.info(f"PatternOptimizer initialized with config: {self.config}")

    def _init_database(self) -> None:
        """Initialize SQLite database for pattern storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    workflow_type TEXT NOT NULL,
                    feature_hash TEXT NOT NULL,
                    performance_score REAL NOT NULL,
                    optimization_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    execution_id TEXT PRIMARY KEY,
                    workflow_type TEXT NOT NULL,
                    features TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    execution_time REAL NOT NULL,
                    success BOOLEAN NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    agent_id TEXT,
                    resource_usage TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_type
                ON workflow_patterns(workflow_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_type_time
                ON workflow_executions(workflow_type, timestamp)
            """)

            conn.commit()

    def record_workflow_execution(
        self,
        execution_id: str,
        workflow_type: str,
        features: Dict[str, float],
        performance_metrics: Dict[str, float],
        execution_time: float,
        success: bool,
        agent_id: Optional[str] = None,
        resource_usage: Optional[Dict[str, float]] = None
    ) -> None:
        """Record a workflow execution for pattern analysis."""

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflow_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                workflow_type,
                json.dumps(features),
                json.dumps(performance_metrics),
                execution_time,
                success,
                datetime.now(),
                agent_id,
                json.dumps(resource_usage or {})
            ))
            conn.commit()

        # Update patterns after recording
        if success:  # Only learn from successful executions
            self._update_patterns(workflow_type, features, performance_metrics)

        logger.debug(f"Recorded workflow execution: {execution_id}")

    def _update_patterns(
        self,
        workflow_type: str,
        features: Dict[str, float],
        performance_metrics: Dict[str, float]
    ) -> None:
        """Update pattern data based on new execution."""

        feature_hash = self._hash_features(features)
        performance_score = self._calculate_performance_score(performance_metrics)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if pattern exists
            cursor.execute("""
                SELECT sample_count, performance_score, confidence
                FROM workflow_patterns
                WHERE workflow_type = ? AND feature_hash = ?
            """, (workflow_type, feature_hash))

            result = cursor.fetchone()

            if result:
                # Update existing pattern
                sample_count, old_score, old_confidence = result
                new_sample_count = sample_count + 1

                # Weighted average of performance scores
                alpha = 1.0 / new_sample_count
                new_score = (1 - alpha) * old_score + alpha * performance_score

                # Update confidence based on sample count
                new_confidence = min(0.95, 0.5 + 0.45 * (new_sample_count / 100))

                optimization_score = self._calculate_optimization_score(
                    new_score, new_confidence, new_sample_count
                )

                cursor.execute("""
                    UPDATE workflow_patterns
                    SET performance_score = ?, optimization_score = ?,
                        confidence = ?, sample_count = ?, last_updated = ?
                    WHERE workflow_type = ? AND feature_hash = ?
                """, (
                    new_score, optimization_score, new_confidence,
                    new_sample_count, datetime.now(), workflow_type, feature_hash
                ))
            else:
                # Create new pattern
                pattern_id = f"{workflow_type}_{feature_hash[:8]}"
                optimization_score = self._calculate_optimization_score(
                    performance_score, 0.5, 1
                )

                cursor.execute("""
                    INSERT INTO workflow_patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_id, workflow_type, feature_hash, performance_score,
                    optimization_score, 0.5, 1, datetime.now(), datetime.now(),
                    json.dumps({})
                ))

            conn.commit()

    def _hash_features(self, features: Dict[str, float]) -> str:
        """Create hash of feature values for pattern matching."""
        # Normalize feature values to create consistent patterns
        normalized_features: Dict[str, Any] = {}
        for key, value in features.items():
            if key in ['task_complexity', 'agent_count', 'queue_size']:
                # Bin into categories for better pattern matching
                normalized_features[key] = int(value // 1)
            elif key in ['resource_usage', 'historical_success_rate']:
                # Bin into 10% increments
                normalized_features[key] = round(float(value), 1)
            else:
                # Default: keep as is
                normalized_features[key] = value