#!/usr/bin/env python3
"""
Velocity Tracker - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer

This module tracks team velocity, analyzes performance trends, and provides
velocity-based recommendations for sprint planning and capacity management.
"""

import json
import sqlite3
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class VelocityMetrics:
    """Velocity metrics for a sprint or time period."""
    period_id: str
    period_name: str
    start_date: str
    end_date: str
    planned_points: int
    completed_points: int
    completion_rate: float
    story_count: int
    avg_story_points: float
    cycle_time_days: float
    throughput: float  # stories per day
    predictability_score: float  # consistency measure


@dataclass
class VelocityTrend:
    """Velocity trend analysis over multiple periods."""
    periods_analyzed: int
    avg_velocity: float
    velocity_trend: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0-1, how strong the trend is
    predictability: float  # 0-1, how predictable the team is
    recommendations: List[str]
    confidence_level: str  # 'low', 'medium', 'high'


class VelocityTracker:
    """Advanced velocity tracking and analysis system."""

    def __init__(self, db_path: str = "sprint_data.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database tables for velocity tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # Velocity metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS velocity_metrics (
                    period_id TEXT PRIMARY KEY,
                    period_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    planned_points INTEGER NOT NULL,
                    completed_points INTEGER NOT NULL,
                    completion_rate REAL NOT NULL,
                    story_count INTEGER NOT NULL,
                    avg_story_points REAL NOT NULL,
                    cycle_time_days REAL NOT NULL,
                    throughput REAL NOT NULL,
                    predictability_score REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)

            # Story completion tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS story_completion (
                    story_id TEXT PRIMARY KEY,
                    period_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    planned_points INTEGER NOT NULL,
                    actual_points INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    start_date TEXT,
                    completion_date TEXT,
                    cycle_time_hours REAL,
                    blocked_time_hours REAL DEFAULT 0,
                    revision_count INTEGER DEFAULT 0,
                    FOREIGN KEY (period_id) REFERENCES velocity_metrics (period_id)
                )
            """)

            # Velocity forecasting data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS velocity_forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    period_id TEXT NOT NULL,
                    forecast_date TEXT NOT NULL,
                    predicted_velocity INTEGER NOT NULL,
                    actual_velocity INTEGER,
                    accuracy_score REAL,
                    model_version TEXT NOT NULL,
                    confidence_interval_low INTEGER,
                    confidence_interval_high INTEGER
                )
            """)

            conn.commit()

    def calculate_sprint_velocity(
            self, sprint_id: str) -> Optional[VelocityMetrics]:
        """Calculate comprehensive velocity metrics for a sprint."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get sprint data
            cursor.execute("""
                SELECT sprint_name, start_date, end_date, planned_points, status
                FROM sprints
                WHERE sprint_id = ?
            """, (sprint_id,))

            sprint_data = cursor.fetchone()
            if not sprint_data:
                return None

            sprint_name, start_date, end_date, planned_points, status = sprint_data

            # Get story completion data
            cursor.execute("""
                SELECT story_points, status, created_at, updated_at
                FROM stories
                WHERE sprint_id = ?
            """, (sprint_id,))

            stories = cursor.fetchall()

        if not stories:
            return None

        # Calculate metrics
        total_planned = planned_points
        completed_stories = [s for s in stories if s[1] == 'completed']
        total_completed = sum(s[0] for s in completed_stories)

        completion_rate = total_completed / total_planned if total_planned > 0 else 0
        story_count = len(stories)
        avg_story_points = sum(s[0] for s in stories) / \
            story_count if story_count > 0 else 0

        # Calculate cycle time (simplified)
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        sprint_duration = (end_dt - start_dt).days
        cycle_time_days = sprint_duration / story_count if story_count > 0 else 0

        # Calculate throughput
        throughput = story_count / sprint_duration if sprint_duration > 0 else 0

        # Calculate predictability score (how close actual vs planned)
        predictability_score = 1.0 - \
            abs(total_completed - total_planned) / \
            total_planned if total_planned > 0 else 0
        predictability_score = max(0, min(1, predictability_score))

        return VelocityMetrics(
            period_id=sprint_id,
            period_name=sprint_name,
            start_date=start_date,
            end_date=end_date,
            planned_points=total_planned,
            completed_points=total_completed,
            completion_rate=completion_rate,
            story_count=story_count,
            avg_story_points=avg_story_points,
            cycle_time_days=cycle_time_days,
            throughput=throughput,
            predictability_score=predictability_score
        )

    def save_velocity_metrics(self, metrics: VelocityMetrics):
        """Save velocity metrics to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO velocity_metrics
                (period_id, period_name, start_date, end_date, planned_points,
                 completed_points, completion_rate, story_count, avg_story_points,
                 cycle_time_days, throughput, predictability_score, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (metrics.period_id,
                 metrics.period_name,
                 metrics.start_date,
                 metrics.end_date,
                 metrics.planned_points,
                 metrics.completed_points,
                 metrics.completion_rate,
                 metrics.story_count,
                 metrics.avg_story_points,
                 metrics.cycle_time_days,
                 metrics.throughput,
                 metrics.predictability_score,
                 datetime.now().isoformat()))
            conn.commit()

    def analyze_velocity_trend(
            self, lookback_periods: int = 6) -> VelocityTrend:
        """Analyze velocity trends over recent periods."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT completed_points, completion_rate, predictability_score, recorded_at
                FROM velocity_metrics
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (lookback_periods,))

            metrics = cursor.fetchall()

        if len(metrics) < 2:
            return VelocityTrend(
                periods_analyzed=len(metrics),
                avg_velocity=metrics[0][0] if metrics else 0,
                velocity_trend="insufficient_data",
                trend_strength=0.0,
                predictability=metrics[0][2] if metrics else 0.0,
                recommendations=["Need more sprint data for trend analysis"],
                confidence_level="low"
            )

        # Calculate trend metrics
        velocities = [m[0] for m in metrics]
        [m[1] for m in metrics]
        predictability_scores = [m[2] for m in metrics]

        avg_velocity = statistics.mean(velocities)
        avg_predictability = statistics.mean(predictability_scores)

        # Calculate trend direction and strength
        if len(velocities) >= 3:
            # Simple linear trend analysis
            x = list(range(len(velocities)))
            y = velocities

            # Calculate correlation coefficient as trend strength
            if len(x) > 1:
                mean_x = statistics.mean(x)
                mean_y = statistics.mean(y)

                numerator = sum((x[i] - mean_x) * (y[i] - mean_y)
                                for i in range(len(x)))
                denominator_x = sum((x[i] - mean_x) **
                                    2 for i in range(len(x)))
                denominator_y = sum((y[i] - mean_y) **
                                    2 for i in range(len(y)))

                if denominator_x > 0 and denominator_y > 0:
                    correlation = numerator / \
                        (denominator_x * denominator_y) ** 0.5
                    trend_strength = abs(correlation)

                    if correlation > 0.3:
                        velocity_trend = "increasing"
                    elif correlation < -0.3:
                        velocity_trend = "decreasing"
                    else:
                        velocity_trend = "stable"
                else:
                    velocity_trend = "stable"
                    trend_strength = 0.0
            else:
                velocity_trend = "stable"
                trend_strength = 0.0
        else:
            velocity_trend = "stable"
            trend_strength = 0.0

        # Generate recommendations
        recommendations = []

        if avg_predictability < 0.7:
            recommendations.append(
                "Improve sprint planning accuracy - high variance in delivery")

        if velocity_trend == "decreasing":
            recommendations.append(
                "Investigate factors causing velocity decline")
            recommendations.append(
                "Consider reducing scope or addressing blockers")
        elif velocity_trend == "increasing":
            recommendations.append(
                "Team is improving - consider gradually increasing commitment")

        if statistics.stdev(velocities) / avg_velocity > 0.3:
            recommendations.append(
                "High velocity variance - focus on consistent delivery")

        if avg_velocity < 30:
            recommendations.append(
                "Low velocity - investigate capacity constraints")

        # Determine confidence level
        if len(metrics) >= 5 and trend_strength > 0.6:
            confidence_level = "high"
        elif len(metrics) >= 3 and trend_strength > 0.4:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        return VelocityTrend(
            periods_analyzed=len(metrics),
            avg_velocity=avg_velocity,
            velocity_trend=velocity_trend,
            trend_strength=trend_strength,
            predictability=avg_predictability,
            recommendations=recommendations,
            confidence_level=confidence_level
        )

    def predict_next_velocity(
            self, confidence_interval: float = 0.8) -> Tuple[int, int, int]:
        """Predict next sprint velocity with confidence interval."""
        trend = self.analyze_velocity_trend()

        if trend.periods_analyzed < 2:
            # Default prediction for new teams
            return 30, 20, 40

        base_velocity = int(trend.avg_velocity)

        # Adjust based on trend
        if trend.velocity_trend == "increasing" and trend.trend_strength > 0.5:
            predicted_velocity = int(base_velocity * 1.1)
        elif trend.velocity_trend == "decreasing" and trend.trend_strength > 0.5:
            predicted_velocity = int(base_velocity * 0.9)
        else:
            predicted_velocity = base_velocity

        # Calculate confidence interval
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT completed_points
                FROM velocity_metrics
                ORDER BY recorded_at DESC
                LIMIT 5
            """)
            recent_velocities = [row[0] for row in cursor.fetchall()]

        if len(recent_velocities) > 1:
            std_dev = statistics.stdev(recent_velocities)
            margin = int(std_dev * confidence_interval)

            low_estimate = max(1, predicted_velocity - margin)
            high_estimate = predicted_velocity + margin
        else:
            # Default confidence interval
            low_estimate = max(1, int(predicted_velocity * 0.7))
            high_estimate = int(predicted_velocity * 1.3)

        return predicted_velocity, low_estimate, high_estimate

    def generate_velocity_report(self, periods: int = 6) -> str:
        """Generate comprehensive velocity analysis report."""
        trend = self.analyze_velocity_trend(periods)
        predicted_velocity, low_est, high_est = self.predict_next_velocity()

        report = f"""
# Team Velocity Analysis Report

## Summary
- **Periods Analyzed**: {trend.periods_analyzed}
- **Average Velocity**: {trend.avg_velocity:.1f} points
- **Velocity Trend**: {trend.velocity_trend.title()}
- **Trend Strength**: {trend.trend_strength:.2f}
- **Predictability**: {trend.predictability:.2f}
- **Confidence Level**: {trend.confidence_level.title()}

## Velocity Prediction
- **Next Sprint Prediction**: {predicted_velocity} points
- **Confidence Interval**: {low_est} - {high_est} points
- **Recommendation**: Plan for {predicted_velocity} points with {low_est}-{high_est} buffer

## Trend Analysis
"""

        if trend.velocity_trend == "increasing":
            report += f"📈 **Positive Trend**: Team velocity is increasing (strength: {
                trend.trend_strength:.2f})\n"
        elif trend.velocity_trend == "decreasing":
            report += f"📉 **Declining Trend**: Team velocity is decreasing (strength: {
                trend.trend_strength:.2f})\n"
        else:
            report += "📊 **Stable Trend**: Team velocity is consistent\n"

        report += """
## Recommendations
"""

        for i, rec in enumerate(trend.recommendations, 1):
            report += f"{i}. {rec}\n"

        if not trend.recommendations:
            report += "No specific recommendations - team performance is satisfactory.\n"

        report += """
## Historical Performance
"""

        # Get recent velocity data
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT period_name, completed_points, completion_rate, predictability_score, recorded_at
                FROM velocity_metrics
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (periods,))

            history = cursor.fetchall()

        for period_name, completed, completion_rate, predictability, recorded_at in history:
            report += f"- **{period_name}**: {completed} points ({
                completion_rate:.1%} completion, {
                predictability:.2f} predictability)\n"

        report += f"""
## Capacity Planning Guidelines
- **Conservative Estimate**: {low_est} points (80% confidence)
- **Aggressive Estimate**: {high_est} points (stretch goal)
- **Recommended Planning**: {predicted_velocity} points (balanced approach)

## Quality Metrics
- **Predictability Score**: {trend.predictability:.2f} (target: >0.8)
- **Trend Confidence**: {trend.confidence_level} (based on {trend.periods_analyzed} periods)
- **Velocity Variance**: {'Low' if trend.trend_strength < 0.3 else 'High'} (consistency indicator)

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report

    def sync_with_github(self):
        """Sync velocity data with GitHub issues and PRs."""
        try:
            # Get recent closed issues
            result = subprocess.run([
                "gh", "issue", "list", "--state", "closed",
                "--json", "number,title,labels,closedAt,assignees",
                "--limit", "100"
            ], capture_output=True, text=True, check=True)

            closed_issues = json.loads(result.stdout)

            # Get recent merged PRs
            result = subprocess.run([
                "gh", "pr", "list", "--state", "merged",
                "--json", "number,title,labels,mergedAt,assignees",
                "--limit", "100"
            ], capture_output=True, text=True, check=True)

            merged_prs = json.loads(result.stdout)

            # Analyze completion patterns
            print(
                f"Analyzed {
                    len(closed_issues)} closed issues and {
                    len(merged_prs)} merged PRs")

            # This could be enhanced to automatically update velocity metrics
            # based on GitHub activity patterns

        except subprocess.CalledProcessError as e:
            print(f"Error syncing with GitHub: {e}")
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub data: {e}")


def main():
    """Main CLI interface for velocity tracking."""
    if len(sys.argv) < 2:
        print("Usage: python velocity_tracker.py <command> [options]")
        print("Commands:")
        print("  calculate <sprint_id>    - Calculate velocity for specific sprint")
        print("  trend [periods]          - Analyze velocity trends")
        print("  predict                  - Predict next sprint velocity")
        print(
            "  report [periods]         - Generate comprehensive velocity report")
        print("  sync                     - Sync with GitHub data")
        sys.exit(1)

    tracker = VelocityTracker()
    command = sys.argv[1]

    if command == "calculate":
        if len(sys.argv) < 3:
            print("Usage: python velocity_tracker.py calculate <sprint_id>")
            sys.exit(1)

        sprint_id = sys.argv[2]
        metrics = tracker.calculate_sprint_velocity(sprint_id)

        if metrics:
            tracker.save_velocity_metrics(metrics)
            print(f"✅ Velocity calculated for {metrics.period_name}")
            print(
                f"Completed Points: {metrics.completed_points}/{metrics.planned_points}")
            print(f"Completion Rate: {metrics.completion_rate:.1%}")
            print(f"Predictability: {metrics.predictability_score:.2f}")
        else:
            print(f"❌ No data found for sprint: {sprint_id}")

    elif command == "trend":
        periods = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        trend = tracker.analyze_velocity_trend(periods)

        print(f"Velocity Trend Analysis ({periods} periods)")
        print(f"Average Velocity: {trend.avg_velocity:.1f} points")
        print(
            f"Trend: {
                trend.velocity_trend} (strength: {
                trend.trend_strength:.2f})")
        print(f"Predictability: {trend.predictability:.2f}")
        print(f"Confidence: {trend.confidence_level}")

        if trend.recommendations:
            print("\nRecommendations:")
            for i, rec in enumerate(trend.recommendations, 1):
                print(f"{i}. {rec}")

    elif command == "predict":
        predicted, low, high = tracker.predict_next_velocity()
        print(f"Next Sprint Velocity Prediction: {predicted} points")
        print(f"Confidence Interval: {low} - {high} points")

    elif command == "report":
        periods = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        report = tracker.generate_velocity_report(periods)

        # Save report to file
        filename = f"velocity_report_{
            datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to: {filename}")

    elif command == "sync":
        tracker.sync_with_github()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
