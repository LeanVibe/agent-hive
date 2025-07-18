#!/usr/bin/env python3
"""
Prompt Logger for Agent Dashboard

Simple SQLite-based logging system to track agent prompts and provide
PM review functionality for prompt optimization.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptLog:
    """Prompt log entry"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    agent_name: str = ""
    prompt_text: str = ""
    response_text: str = ""
    success: bool = True
    error_message: Optional[str] = None
    gemini_feedback: Optional[str] = None
    pm_review: Optional[str] = None
    suggested_improvement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'agent_name': self.agent_name,
            'prompt_text': self.prompt_text,
            'response_text': self.response_text,
            'success': self.success,
            'error_message': self.error_message,
            'gemini_feedback': self.gemini_feedback,
            'pm_review': self.pm_review,
            'suggested_improvement': self.suggested_improvement}


class PromptLogger:
    """Simple SQLite-based prompt logger"""

    def __init__(self, db_path: str = "dashboard/prompts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    response_text TEXT,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    gemini_feedback TEXT,
                    pm_review TEXT,
                    suggested_improvement TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_timestamp
                ON prompt_logs (agent_name, timestamp)
            """)

    def log_prompt(self, agent_name: str, prompt_text: str,
                   response_text: str = "", success: bool = True,
                   error_message: Optional[str] = None) -> int:
        """Log a prompt interaction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO prompt_logs
                (timestamp, agent_name, prompt_text, response_text, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                agent_name,
                prompt_text,
                response_text,
                success,
                error_message
            ))
            return cursor.lastrowid

    def add_gemini_feedback(self, log_id: int, feedback: str):
        """Add Gemini review feedback to a prompt log"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE prompt_logs
                SET gemini_feedback = ?
                WHERE id = ?
            """, (feedback, log_id))

    def add_pm_review(
            self,
            log_id: int,
            review: str,
            suggested_improvement: str):
        """Add PM review and improvement suggestion"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE prompt_logs
                SET pm_review = ?, suggested_improvement = ?
                WHERE id = ?
            """, (review, suggested_improvement, log_id))

    def get_recent_prompts(self, limit: int = 50) -> List[PromptLog]:
        """Get recent prompts for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM prompt_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            return [self._row_to_prompt_log(
                dict(zip(columns, row))) for row in rows]

    def get_prompts_for_agent(
            self,
            agent_name: str,
            limit: int = 20) -> List[PromptLog]:
        """Get prompts for specific agent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM prompt_logs
                WHERE agent_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agent_name, limit))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            return [self._row_to_prompt_log(
                dict(zip(columns, row))) for row in rows]

    def get_prompts_needing_review(self) -> List[PromptLog]:
        """Get prompts that need PM review"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM prompt_logs
                WHERE pm_review IS NULL
                ORDER BY timestamp DESC
            """)

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            return [self._row_to_prompt_log(
                dict(zip(columns, row))) for row in rows]

    def get_prompt_stats(self) -> Dict[str, Any]:
        """Get prompt statistics for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            # Total prompts
            total_prompts = conn.execute(
                "SELECT COUNT(*) FROM prompt_logs").fetchone()[0]

            # Success rate
            success_rate = conn.execute("""
                SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END)
                FROM prompt_logs
            """).fetchone()[0] or 0.0

            # Prompts by agent
            agent_stats = conn.execute("""
                SELECT agent_name, COUNT(*) as count
                FROM prompt_logs
                GROUP BY agent_name
                ORDER BY count DESC
            """).fetchall()

            # Prompts needing review
            needs_review = conn.execute("""
                SELECT COUNT(*) FROM prompt_logs
                WHERE pm_review IS NULL
            """).fetchone()[0]

            return {
                'total_prompts': total_prompts,
                'success_rate': success_rate,
                'agent_stats': dict(agent_stats),
                'needs_review': needs_review
            }

    def _row_to_prompt_log(self, row: Dict[str, Any]) -> PromptLog:
        """Convert database row to PromptLog object"""
        return PromptLog(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            agent_name=row['agent_name'],
            prompt_text=row['prompt_text'],
            response_text=row['response_text'] or "",
            success=bool(row['success']),
            error_message=row['error_message'],
            gemini_feedback=row['gemini_feedback'],
            pm_review=row['pm_review'],
            suggested_improvement=row['suggested_improvement']
        )


# Global logger instance
prompt_logger = PromptLogger()
