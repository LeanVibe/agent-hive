"""
AdaptiveLearning - Self-improving learning system with continuous optimization

Implements adaptive learning algorithms that continuously improve system performance
based on feedback and historical patterns within the multi-agent coordination system.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

from .models import MLConfig, LearningMetrics


logger = logging.getLogger(__name__)


class AdaptiveLearning:
    """
    Self-improving learning system with continuous optimization and feedback integration.

    This component provides:
    - Self-improving learning algorithms
    - Feedback integration mechanisms
    - Model update and evaluation systems
    - Continuous optimization based on historical data
    """

    def __init__(self, config: Optional[MLConfig] = None, db_path: Optional[str] = None):
        """Initialize AdaptiveLearning with configuration and database."""
        self.config = config or MLConfig()
        self.db_path = db_path or "adaptive_learning.db"
        self.model_version = "1.0.0"

        # Adaptive models with online learning capability
        self.adaptive_models = {
            'performance_optimizer': SGDRegressor(
                learning_rate='adaptive',
                eta0=self.config.learning_rate,
                random_state=42
            ),
            'resource_optimizer': SGDRegressor(
                learning_rate='adaptive',
                eta0=self.config.learning_rate,
                random_state=42
            ),
            'task_scheduler': RandomForestRegressor(
                n_estimators=50,
                max_depth=8,
                random_state=42
            )
        }

        self.scalers = {
            model_name: StandardScaler() for model_name in self.adaptive_models.keys()
        }

        # Learning state tracking - properly typed
        self.learning_state: Dict[str, Any] = {
            'current_session': None,
            'adaptation_history': [],
            'last_update': {},
        }

        # Type-safe accessors
        self.model_performance: Dict[str, List[float]] = {}
        self.convergence_tracking: Dict[str, Dict[str, Any]] = {}

        # Feedback integration - properly typed
        self.feedback_buffer: Dict[str, List[Dict[str, Any]]] = {
            'positive_feedback': [],
            'negative_feedback': [],
            'performance_feedback': []
        }

        # Initialize database
        self._init_database()

        logger.info(f"AdaptiveLearning initialized with config: {self.config}")

    def _init_database(self) -> None:
        """Initialize SQLite database for adaptive learning data."""
        with sqlite3.connect(self.db_path) as conn:
            # Learning sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    session_id TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    initial_performance REAL NOT NULL,
                    final_performance REAL,
                    improvement_rate REAL,
                    samples_processed INTEGER NOT NULL,
                    convergence_time REAL,
                    hyperparameters TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # Feedback table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_data (
                    feedback_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    feedback_value REAL NOT NULL,
                    context TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    source_agent TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
                )
            """)

            # Model adaptations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_adaptations (
                    adaptation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    adaptation_type TEXT NOT NULL,
                    before_performance REAL NOT NULL,
                    after_performance REAL NOT NULL,
                    adaptation_details TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    success BOOLEAN NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
                )
            """)

            # Performance history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_history (
                    history_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    performance_metric REAL NOT NULL,
                    measurement_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    context TEXT,
                    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_model_time
                ON learning_sessions(model_type, start_time)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_session_type
                ON feedback_data(session_id, feedback_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_adaptations_session_time
                ON model_adaptations(session_id, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_session_time
                ON performance_history(session_id, timestamp)
            """)

            conn.commit()

    def start_learning_session(
        self,
        model_type: str,
        initial_context: Dict[str, Any],
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new adaptive learning session."""

        session_id = f"session_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Initialize session state
        self.learning_state['current_session'] = session_id
        self.model_performance[session_id] = []
        self.learning_state['adaptation_history'].append({
            'session_id': session_id,
            'start_time': datetime.now(),
            'model_type': model_type
        })

        # Reset feedback buffer for new session
        for buffer in self.feedback_buffer.values():
            buffer.clear()

        # Store session in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO learning_sessions
                (session_id, model_type, start_time, initial_performance,
                 samples_processed, hyperparameters, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, model_type, datetime.now(), 0.5,  # Default initial performance
                0, json.dumps(hyperparameters or {}), json.dumps(initial_context)
            ))
            conn.commit()

        logger.info(f"Started learning session: {session_id} for model: {model_type}")
        return session_id

    def provide_feedback(
        self,
        session_id: str,
        feedback_type: str,
        feedback_value: float,
        context: Dict[str, Any],
        source_agent: Optional[str] = None
    ) -> None:
        """Provide feedback for adaptive learning."""

        feedback_id = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Store in buffer for immediate use
        feedback_data = {
            'feedback_id': feedback_id,
            'type': feedback_type,
            'value': feedback_value,
            'context': context,
            'timestamp': datetime.now(),
            'source': source_agent
        }

        if feedback_type == 'positive':
            self.feedback_buffer['positive_feedback'].append(feedback_data)
        elif feedback_type == 'negative':
            self.feedback_buffer['negative_feedback'].append(feedback_data)
        else:
            self.feedback_buffer['performance_feedback'].append(feedback_data)

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO feedback_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id, session_id, feedback_type, feedback_value,
                json.dumps(context), datetime.now(), source_agent, json.dumps({})
            ))
            conn.commit()

        # Trigger immediate adaptation if enough feedback
        self._process_feedback_adaptation(session_id)

        logger.debug(f"Received {feedback_type} feedback: {feedback_value}")

    def adapt_model(
        self,
        session_id: str,
        model_type: str,
        training_data: List[Dict[str, Any]],
        target_values: List[float]
    ) -> LearningMetrics:
        """Adapt model based on new training data and feedback."""

        if model_type not in self.adaptive_models:
            raise ValueError(f"Unknown model type: {model_type}")

        model = self.adaptive_models[model_type]
        scaler = self.scalers[model_type]

        # Measure performance before adaptation
        before_performance = self._measure_model_performance(model_type, training_data, target_values)

        # Prepare training data
        X, y = self._prepare_training_data(training_data, target_values)

        if len(X) == 0:
            logger.warning(f"No training data available for {model_type}")
            return self._create_default_metrics(session_id)

        # Scale features
        if hasattr(model, 'partial_fit'):
            # Online learning for SGD models
            X_scaled = scaler.partial_fit(X).transform(X) if not hasattr(scaler, 'mean_') else scaler.transform(X)
            model.partial_fit(X_scaled, y)
        else:
            # Batch learning for tree models
            X_scaled = scaler.fit_transform(X)
            model.fit(X_scaled, y)

        # Measure performance after adaptation
        after_performance = self._measure_model_performance(model_type, training_data, target_values)

        # Calculate improvement metrics
        improvement_rate = (after_performance - before_performance) / max(before_performance, 0.001)
        accuracy_change = after_performance - before_performance

        # Update learning state
        session_performance = self.model_performance.get(session_id, [])
        session_performance.append(after_performance)