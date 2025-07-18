#!/usr/bin/env python3
"""
Velocity Tracking Micro-Component - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer (Micro-Component #2)

This micro-component handles ONLY velocity tracking and trend analysis.
Follows XP Small Releases principle: ≤300 lines, single responsibility.
"""

import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List


@dataclass
class VelocityRecord:
    """Minimal velocity record for micro-component."""
    record_id: str
    sprint_id: str
    period_start: str
    period_end: str
    planned_points: int
    completed_points: int
    velocity: float
    team_size: int


class VelocityTrackingMicro:
    """Micro-component for velocity tracking functionality only."""

    def __init__(self, db_path: str = "velocity_micro.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize minimal database for velocity tracking micro-component."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS velocity_records (
                    record_id TEXT PRIMARY KEY,
                    sprint_id TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    planned_points INTEGER NOT NULL,
                    completed_points INTEGER NOT NULL,
                    velocity REAL NOT NULL,
                    team_size INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def record_velocity(
            self,
            sprint_id: str,
            planned_points: int,
            completed_points: int,
            team_size: int = 3) -> VelocityRecord:
        """Record velocity for a sprint - micro-component core functionality."""
        velocity = completed_points / team_size if team_size > 0 else 0

        # Calculate period (assume 2-week sprint ending now)
        period_end = datetime.now()
        period_start = period_end - timedelta(days=14)

        record_id = f"velocity-{sprint_id}-{period_end.strftime('%Y%m%d')}"

        record = VelocityRecord(
            record_id=record_id,
            sprint_id=sprint_id,
            period_start=period_start.strftime('%Y-%m-%d'),
            period_end=period_end.strftime('%Y-%m-%d'),
            planned_points=planned_points,
            completed_points=completed_points,
            velocity=velocity,
            team_size=team_size
        )

        self.save_velocity_record(record)
        return record

    def save_velocity_record(self, record: VelocityRecord):
        """Save velocity record to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO velocity_records
                (record_id, sprint_id, period_start, period_end,
                 planned_points, completed_points, velocity, team_size, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (record.record_id,
                 record.sprint_id,
                 record.period_start,
                 record.period_end,
                 record.planned_points,
                 record.completed_points,
                 record.velocity,
                 record.team_size,
                 datetime.now().isoformat()))
            conn.commit()

    def get_current_velocity(self) -> float:
        """Get most recent velocity - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT velocity FROM velocity_records
                ORDER BY recorded_at DESC
                LIMIT 1
            """)

            result = cursor.fetchone()
            return result[0] if result else 0.0

    def get_velocity_trend(self, periods: int = 5) -> Dict:
        """Get velocity trend analysis - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT velocity, completed_points, planned_points
                FROM velocity_records
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (periods,))

            records = cursor.fetchall()

        if not records:
            return {
                "trend": "no_data",
                "current_velocity": 0.0,
                "avg_velocity": 0.0}

        velocities = [r[0] for r in records]
        current_velocity = velocities[0]
        avg_velocity = statistics.mean(velocities)

        # Simple trend analysis
        if len(velocities) >= 3:
            recent_avg = statistics.mean(velocities[:2])
            older_avg = statistics.mean(velocities[2:])

            if recent_avg > older_avg * 1.1:
                trend = "improving"
            elif recent_avg < older_avg * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "current_velocity": current_velocity,
            "avg_velocity": avg_velocity,
            "periods_analyzed": len(velocities)
        }

    def predict_capacity(self, team_size: int = 3) -> Dict:
        """Predict sprint capacity based on velocity - micro-component functionality."""
        trend = self.get_velocity_trend()
        base_velocity = trend["avg_velocity"]

        # Simple capacity prediction
        predicted_points = int(base_velocity * team_size)
        confidence = min(90, trend["periods_analyzed"] * 20)

        return {
            "predicted_points": predicted_points,
            "confidence_percentage": confidence,
            "based_on_velocity": base_velocity,
            "team_size": team_size
        }

    def list_velocity_records(self, limit: int = 10) -> List[VelocityRecord]:
        """List recent velocity records - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT record_id, sprint_id, period_start, period_end,
                       planned_points, completed_points, velocity, team_size
                FROM velocity_records
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (limit,))

            return [VelocityRecord(*row) for row in cursor.fetchall()]


def main():
    """CLI interface for velocity tracking micro-component."""
    import sys

    if len(sys.argv) < 2:
        print("Velocity Tracking Micro-Component")
        print("Commands:")
        print(
            "  record <sprint_id> <planned> <completed> [team_size] - Record velocity")
        print(
            "  current                                              - Show current velocity")
        print(
            "  trend [periods]                                      - Show velocity trend")
        print(
            "  predict [team_size]                                  - Predict capacity")
        print(
            "  list [limit]                                         - List records")
        return

    tracker = VelocityTrackingMicro()
    command = sys.argv[1]

    if command == "record":
        if len(sys.argv) < 5:
            print(
                "Usage: record <sprint_id> <planned> <completed> [team_size]")
            return

        sprint_id = sys.argv[2]
        planned = int(sys.argv[3])
        completed = int(sys.argv[4])
        team_size = int(sys.argv[5]) if len(sys.argv) > 5 else 3

        record = tracker.record_velocity(
            sprint_id, planned, completed, team_size)
        print(f"✅ Recorded velocity: {record.velocity:.1f} points/person")
        print(f"Sprint: {record.sprint_id}")
        print(f"Completed: {completed}/{planned} points")
        print(f"Team size: {team_size}")

    elif command == "current":
        velocity = tracker.get_current_velocity()
        print(f"Current Velocity: {velocity:.1f} points/person")

    elif command == "trend":
        periods = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        trend = tracker.get_velocity_trend(periods)

        print(f"Velocity Trend (last {periods} periods):")
        print(f"  Current: {trend['current_velocity']:.1f} points/person")
        print(f"  Average: {trend['avg_velocity']:.1f} points/person")
        print(f"  Trend: {trend['trend']}")
        print(f"  Periods: {trend['periods_analyzed']}")

    elif command == "predict":
        team_size = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        prediction = tracker.predict_capacity(team_size)

        print("Capacity Prediction:")
        print(f"  Predicted Points: {prediction['predicted_points']}")
        print(f"  Confidence: {prediction['confidence_percentage']}%")
        print(f"  Based on Velocity: {prediction['based_on_velocity']:.1f}")
        print(f"  Team Size: {prediction['team_size']}")

    elif command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        records = tracker.list_velocity_records(limit)

        print(f"Velocity Records (last {limit}):")
        for record in records:
            print(f"  {record.sprint_id}: {record.velocity:.1f} points/person "
                  f"({record.completed_points}/{record.planned_points} points)")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
