import json
import sqlite3
import time
from pathlib import Path

import git


class StateManager:
    def __init__(self, base_path: Path):
        try:
            self.db = sqlite3.connect(base_path / ".claude/state.db")
            self.repo = git.Repo(base_path)
            self._init_db()
        except Exception as e:
            print(f"State init error: {e}")
            raise

    def _init_db(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                git_tag TEXT,
                metrics JSON,
                timestamp DATETIME
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                agent TEXT,
                status TEXT,
                confidence REAL
            );
            CREATE TABLE IF NOT EXISTS performance (
                agent TEXT,
                task_id TEXT,
                duration REAL,
                success BOOL
            );
        """)

    def checkpoint(self, name: str):
        try:
            tag = self.repo.create_tag(name)
            metrics = self._collect_metrics()
            self.db.execute(
                "INSERT INTO checkpoints VALUES (?, ?, ?, ?)",
                (name, tag.name, json.dumps(metrics), time.time()),
            )
            self.db.commit()
            print(f"Checkpoint created: {name}")  # For testability
        except Exception as e:
            print(f"Checkpoint error: {e}")
            self.rollback("last-good")

    def rollback(self, checkpoint_id: str):
        try:
            self.repo.git.checkout(checkpoint_id)
            print(f"Rolled back to {checkpoint_id}")
        except Exception as e:
            print(f"Rollback error: {e}")
            raise

    def _collect_metrics(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT AVG(confidence) FROM tasks")
        return {"avg_confidence": cursor.fetchone()[0] or 0.8}


if __name__ == "__main__":
    # Test stub
    sm = StateManager(Path("."))
    sm.checkpoint("test")
