#!/usr/bin/env python3
"""
Burndown Chart Generator - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer

This module generates burndown charts for sprint tracking and provides
real-time progress visualization for XP methodology enforcement.
"""

import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


@dataclass
class BurndownPoint:
    """Represents a single point on the burndown chart."""
    date: str
    remaining_points: int
    completed_points: int
    ideal_remaining: int
    actual_remaining: int
    daily_velocity: float
    cumulative_velocity: float


@dataclass
class BurndownData:
    """Complete burndown data for a sprint."""
    sprint_id: str
    sprint_name: str
    start_date: str
    end_date: str
    total_points: int
    points: List[BurndownPoint]
    status: str
    progress_percentage: float
    days_remaining: int
    current_velocity: float
    projected_completion: str
    risk_level: str  # 'low', 'medium', 'high'


class BurndownGenerator:
    """Advanced burndown chart generator with predictive analytics."""

    def __init__(self, db_path: str = "sprint_data.db"):
        self.db_path = db_path

    def calculate_ideal_burndown(
            self,
            total_points: int,
            sprint_days: int) -> List[int]:
        """Calculate ideal burndown line."""
        if sprint_days == 0:
            return [total_points]

        daily_burn = total_points / sprint_days
        ideal_line = []

        for day in range(sprint_days + 1):
            remaining = max(0, total_points - (day * daily_burn))
            ideal_line.append(int(remaining))

        return ideal_line

    def get_sprint_progress(self, sprint_id: str) -> Optional[BurndownData]:
        """Get current sprint progress and calculate burndown data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get sprint information
            cursor.execute("""
                SELECT sprint_name, start_date, end_date, planned_points, status
                FROM sprints
                WHERE sprint_id = ?
            """, (sprint_id,))

            sprint_data = cursor.fetchone()
            if not sprint_data:
                return None

            sprint_name, start_date, end_date, total_points, status = sprint_data

            # Get story progress
            cursor.execute("""
                SELECT id, story_points, status, updated_at
                FROM stories
                WHERE sprint_id = ?
                ORDER BY updated_at
            """, (sprint_id,))

            stories = cursor.fetchall()

        if not stories:
            return None

        # Calculate dates and duration
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        current_dt = datetime.now()

        sprint_days = (end_dt - start_dt).days
        elapsed_days = (current_dt - start_dt).days
        remaining_days = max(0, (end_dt - current_dt).days)

        # Calculate ideal burndown
        ideal_burndown = self.calculate_ideal_burndown(
            total_points, sprint_days)

        # Calculate daily progress
        burndown_points = []
        completed_points = 0

        # Create daily progress tracking
        for day in range(max(1, elapsed_days + 1)):
            day_date = start_dt + timedelta(days=day)

            # Calculate completed points up to this day
            day_completed = 0
            for story_id, story_points, story_status, updated_at in stories:
                if story_status == 'completed':
                    story_update_dt = datetime.fromisoformat(updated_at)
                    if story_update_dt <= day_date:
                        day_completed += story_points

            remaining_points = total_points - day_completed
            daily_velocity = day_completed - completed_points if day > 0 else 0
            cumulative_velocity = day_completed / day if day > 0 else 0

            ideal_remaining = ideal_burndown[min(day, len(ideal_burndown) - 1)]

            burndown_points.append(BurndownPoint(
                date=day_date.strftime("%Y-%m-%d"),
                remaining_points=remaining_points,
                completed_points=day_completed,
                ideal_remaining=ideal_remaining,
                actual_remaining=remaining_points,
                daily_velocity=daily_velocity,
                cumulative_velocity=cumulative_velocity
            ))

            completed_points = day_completed

        # Calculate current metrics
        current_completed = sum(s[1] for s in stories if s[2] == 'completed')
        current_remaining = total_points - current_completed
        progress_percentage = (current_completed / total_points) * \
            100 if total_points > 0 else 0

        # Calculate current velocity (last 3 days average)
        recent_velocities = [p.daily_velocity for p in burndown_points[-3:]]
        current_velocity = sum(recent_velocities) / \
            len(recent_velocities) if recent_velocities else 0

        # Project completion date
        if current_velocity > 0:
            days_to_completion = current_remaining / current_velocity
            projected_completion = (
                current_dt +
                timedelta(
                    days=days_to_completion)).strftime("%Y-%m-%d")
        else:
            projected_completion = end_date

        # Calculate risk level
        if elapsed_days > 0:
            expected_completion = (elapsed_days / sprint_days) * 100
            actual_completion = progress_percentage

            if actual_completion >= expected_completion * 0.9:
                risk_level = "low"
            elif actual_completion >= expected_completion * 0.7:
                risk_level = "medium"
            else:
                risk_level = "high"
        else:
            risk_level = "low"

        return BurndownData(
            sprint_id=sprint_id,
            sprint_name=sprint_name,
            start_date=start_date,
            end_date=end_date,
            total_points=total_points,
            points=burndown_points,
            status=status,
            progress_percentage=progress_percentage,
            days_remaining=remaining_days,
            current_velocity=current_velocity,
            projected_completion=projected_completion,
            risk_level=risk_level
        )

    def generate_burndown_chart(
            self,
            burndown_data: BurndownData,
            output_file: str = None) -> str:
        """Generate burndown chart visualization."""
        if not burndown_data.points:
            return "No data available for burndown chart"

        # Prepare data for plotting
        dates = [datetime.fromisoformat(p.date) for p in burndown_data.points]
        actual_remaining = [p.actual_remaining for p in burndown_data.points]
        ideal_remaining = [p.ideal_remaining for p in burndown_data.points]

        # Create the plot
        plt.figure(figsize=(12, 8))

        # Plot lines
        plt.plot(dates, actual_remaining, 'b-', linewidth=2,
                 label='Actual Burndown', marker='o')
        plt.plot(dates, ideal_remaining, 'r--', linewidth=2,
                 label='Ideal Burndown', alpha=0.7)

        # Add zero line
        plt.axhline(y=0, color='green', linestyle='-',
                    alpha=0.5, label='Sprint Goal')

        # Add today's date line
        today = datetime.now()
        if dates[0] <= today <= dates[-1]:
            plt.axvline(x=today, color='orange', linestyle=':',
                        alpha=0.7, label='Today')

        # Formatting
        plt.xlabel('Date')
        plt.ylabel('Remaining Story Points')
        plt.title(f'Burndown Chart: {burndown_data.sprint_name}')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Format x-axis
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.xticks(rotation=45)

        # Add annotations
        risk_color = {'low': 'green', 'medium': 'orange', 'high': 'red'}
        plt.text(
            0.02,
            0.98,
            f'Progress: {
                burndown_data.progress_percentage:.1f}%',
            transform=plt.gca().transAxes,
            verticalalignment='top',
            bbox=dict(
                boxstyle='round',
                facecolor='lightblue',
                alpha=0.8))

        plt.text(0.02,
                 0.92,
                 f'Risk Level: {burndown_data.risk_level.upper()}',
                 transform=plt.gca().transAxes,
                 verticalalignment='top',
                 bbox=dict(boxstyle='round',
                           facecolor=risk_color[burndown_data.risk_level],
                           alpha=0.8))

        plt.text(
            0.02,
            0.86,
            f'Current Velocity: {
                burndown_data.current_velocity:.1f} pts/day',
            transform=plt.gca().transAxes,
            verticalalignment='top',
            bbox=dict(
                boxstyle='round',
                facecolor='lightyellow',
                alpha=0.8))

        # Save the chart
        if not output_file:
            output_file = f"burndown_{
                burndown_data.sprint_id}_{
                datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        return output_file

    def generate_velocity_trend_chart(
            self,
            sprint_id: str,
            output_file: str = None) -> str:
        """Generate velocity trend chart for the sprint."""
        burndown_data = self.get_sprint_progress(sprint_id)
        if not burndown_data or not burndown_data.points:
            return "No data available for velocity trend chart"

        # Prepare velocity data
        dates = [datetime.fromisoformat(p.date) for p in burndown_data.points]
        daily_velocities = [p.daily_velocity for p in burndown_data.points]
        cumulative_velocities = [
            p.cumulative_velocity for p in burndown_data.points]

        # Create the plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Daily velocity chart
        ax1.bar(dates, daily_velocities, alpha=0.7,
                color='skyblue', label='Daily Velocity')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Story Points Completed')
        ax1.set_title(f'Daily Velocity: {burndown_data.sprint_name}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # Cumulative velocity chart
        ax2.plot(dates, cumulative_velocities, 'g-', linewidth=2,
                 marker='o', label='Cumulative Velocity')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Average Points per Day')
        ax2.set_title('Cumulative Velocity Trend')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        # Save the chart
        if not output_file:
            output_file = f"velocity_trend_{
                burndown_data.sprint_id}_{
                datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        return output_file

    def generate_burndown_report(self, sprint_id: str) -> str:
        """Generate comprehensive burndown analysis report."""
        burndown_data = self.get_sprint_progress(sprint_id)
        if not burndown_data:
            return "No data available for burndown report"

        # Generate charts
        burndown_chart = self.generate_burndown_chart(burndown_data)
        velocity_chart = self.generate_velocity_trend_chart(sprint_id)

        # Calculate additional metrics
        total_days = len(burndown_data.points)
        working_days = sum(
            1 for p in burndown_data.points if p.daily_velocity > 0)

        # Risk assessment
        risk_indicators = []
        if burndown_data.risk_level == "high":
            risk_indicators.append("Sprint is significantly behind schedule")
        if burndown_data.current_velocity < 1.0:
            risk_indicators.append(
                "Current velocity is below sustainable pace")
        if burndown_data.days_remaining < 3 and burndown_data.progress_percentage < 80:
            risk_indicators.append("Sprint unlikely to complete on time")

        report = f"""
# Sprint Burndown Report: {burndown_data.sprint_name}

## Sprint Overview
- **Sprint ID**: {burndown_data.sprint_id}
- **Duration**: {burndown_data.start_date} to {burndown_data.end_date}
- **Total Points**: {burndown_data.total_points}
- **Status**: {burndown_data.status}

## Current Progress
- **Completion**: {burndown_data.progress_percentage:.1f}%
- **Days Remaining**: {burndown_data.days_remaining}
- **Current Velocity**: {burndown_data.current_velocity:.1f} points/day
- **Projected Completion**: {burndown_data.projected_completion}
- **Risk Level**: {burndown_data.risk_level.upper()}

## Performance Metrics
- **Total Sprint Days**: {total_days}
- **Active Working Days**: {working_days}
- **Average Daily Velocity**: {sum(p.daily_velocity for p in burndown_data.points) / total_days:.1f} points/day
- **Peak Daily Velocity**: {max(p.daily_velocity for p in burndown_data.points):.1f} points/day

## Risk Assessment
"""

        if risk_indicators:
            for indicator in risk_indicators:
                report += f"⚠️ {indicator}\n"
        else:
            report += "✅ Sprint is on track with no significant risks identified\n"

        report += """
## Recommendations
"""

        if burndown_data.risk_level == "high":
            report += """
1. **Immediate Action Required**
   - Review scope and consider removing lower-priority stories
   - Identify and remove blockers
   - Consider adding team capacity if possible
   - Conduct daily stand-ups to track progress closely

2. **Process Improvements**
   - Break down large stories into smaller, manageable tasks
   - Improve story estimation accuracy
   - Address any technical debt that's slowing development
"""
        elif burndown_data.risk_level == "medium":
            report += """
1. **Monitor Closely**
   - Track daily progress and velocity
   - Identify potential blockers early
   - Ensure team is following XP practices

2. **Optimization**
   - Look for opportunities to improve efficiency
   - Consider pair programming for complex tasks
   - Maintain consistent daily velocity
"""
        else:
            report += """
1. **Maintain Momentum**
   - Continue current practices
   - Monitor for any emerging issues
   - Prepare for sprint review and retrospective

2. **Continuous Improvement**
   - Document successful practices
   - Share knowledge across team
   - Plan for next sprint based on current velocity
"""

        report += """
## Daily Progress Tracking
"""

        for point in burndown_data.points[-7:]:  # Last 7 days
            report += f"- **{
                point.date}**: {
                point.daily_velocity:.1f} points completed, {
                point.actual_remaining} remaining\n"

        report += f"""
## Charts Generated
- **Burndown Chart**: {burndown_chart}
- **Velocity Trend**: {velocity_chart}

## XP Methodology Compliance
- **Daily Progress**: {'✅ Tracked' if total_days > 0 else '❌ Not tracked'}
- **Velocity Measurement**: {'✅ Measured' if burndown_data.current_velocity > 0 else '❌ No velocity'}
- **Risk Monitoring**: {'✅ Monitored' if burndown_data.risk_level else '❌ Not monitored'}
- **Predictive Planning**: {'✅ Implemented' if burndown_data.projected_completion else '❌ Not implemented'}

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report


def main():
    """Main CLI interface for burndown generation."""
    if len(sys.argv) < 2:
        print("Usage: python burndown_generator.py <command> [options]")
        print("Commands:")
        print(
            "  chart <sprint_id> [output_file]     - Generate burndown chart")
        print(
            "  velocity <sprint_id> [output_file]  - Generate velocity trend chart")
        print(
            "  report <sprint_id>                  - Generate comprehensive burndown report")
        print("  progress <sprint_id>                - Show current sprint progress")
        sys.exit(1)

    generator = BurndownGenerator()
    command = sys.argv[1]

    if command == "chart":
        if len(sys.argv) < 3:
            print(
                "Usage: python burndown_generator.py chart <sprint_id> [output_file]")
            sys.exit(1)

        sprint_id = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None

        burndown_data = generator.get_sprint_progress(sprint_id)
        if not burndown_data:
            print(f"❌ No data found for sprint: {sprint_id}")
            sys.exit(1)

        chart_file = generator.generate_burndown_chart(
            burndown_data, output_file)
        print(f"✅ Burndown chart generated: {chart_file}")

    elif command == "velocity":
        if len(sys.argv) < 3:
            print(
                "Usage: python burndown_generator.py velocity <sprint_id> [output_file]")
            sys.exit(1)

        sprint_id = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None

        chart_file = generator.generate_velocity_trend_chart(
            sprint_id, output_file)
        print(f"✅ Velocity trend chart generated: {chart_file}")

    elif command == "report":
        if len(sys.argv) < 3:
            print("Usage: python burndown_generator.py report <sprint_id>")
            sys.exit(1)

        sprint_id = sys.argv[2]
        report = generator.generate_burndown_report(sprint_id)

        # Save report to file
        report_file = f"burndown_report_{sprint_id}_{
            datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to: {report_file}")

    elif command == "progress":
        if len(sys.argv) < 3:
            print("Usage: python burndown_generator.py progress <sprint_id>")
            sys.exit(1)

        sprint_id = sys.argv[2]
        burndown_data = generator.get_sprint_progress(sprint_id)

        if not burndown_data:
            print(f"❌ No data found for sprint: {sprint_id}")
            sys.exit(1)

        print(f"Sprint Progress: {burndown_data.sprint_name}")
        print(f"Completion: {burndown_data.progress_percentage:.1f}%")
        print(f"Days Remaining: {burndown_data.days_remaining}")
        print(
            f"Current Velocity: {
                burndown_data.current_velocity:.1f} points/day")
        print(f"Risk Level: {burndown_data.risk_level.upper()}")
        print(f"Projected Completion: {burndown_data.projected_completion}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
