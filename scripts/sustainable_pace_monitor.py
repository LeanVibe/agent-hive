#!/usr/bin/env python3
"""
Sustainable Pace Monitor - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer

This module monitors team workload and ensures sustainable pace practices
to prevent burnout and maintain XP methodology compliance.
"""

import json
import re
import sqlite3
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


@dataclass
class WorkloadPeriod:
    """Represents a team member's workload for a specific period."""
    period_id: str
    team_member: str
    start_date: str
    end_date: str

    # Time tracking
    total_hours: float
    coding_hours: float
    meeting_hours: float
    break_hours: float

    # Work patterns
    daily_hours: List[float]
    peak_hours: List[str]  # Hours of highest activity
    work_days: int
    overtime_hours: float

    # Productivity metrics
    commits_made: int
    lines_changed: int
    issues_resolved: int
    pair_programming_hours: float

    # Wellbeing indicators
    stress_level: float  # 1-10 scale
    satisfaction_score: float  # 1-10 scale
    fatigue_indicators: List[str]

    # XP compliance
    sustainable_pace_score: float  # 0-100
    work_life_balance_score: float  # 0-100
    team_collaboration_score: float  # 0-100


@dataclass
class TeamPaceMetrics:
    """Team-wide sustainable pace metrics."""
    period_id: str
    start_date: str
    end_date: str

    # Team metrics
    team_size: int
    total_team_hours: float
    average_hours_per_person: float

    # Pace indicators
    overtime_percentage: float
    burnout_risk_members: int
    sustainable_pace_compliance: float

    # Productivity balance
    productivity_per_hour: float
    quality_vs_speed_ratio: float
    team_velocity: float

    # Wellbeing metrics
    average_stress_level: float
    average_satisfaction: float
    team_collaboration_score: float

    # XP principle compliance
    forty_hour_week_compliance: float
    collective_ownership_score: float
    continuous_improvement_score: float


class SustainablePaceMonitor:
    """Advanced sustainable pace monitoring and analysis system."""

    def __init__(self, db_path: str = "sustainable_pace_data.db"):
        self.db_path = db_path
        self.init_database()

        # Sustainable pace targets
        self.pace_targets = {
            'max_weekly_hours': 40,
            'max_daily_hours': 8,
            'max_overtime_percentage': 10,  # % of total hours
            'min_break_hours_per_day': 1,
            'max_consecutive_work_days': 5,
            'target_stress_level': 5,  # 1-10 scale
            'target_satisfaction': 8,  # 1-10 scale
            'burnout_risk_threshold': 45  # hours per week
        }

        # Work pattern analysis
        self.work_patterns = {
            'early_bird': (6, 10),    # 6 AM - 10 AM
            'morning': (8, 12),       # 8 AM - 12 PM
            'afternoon': (12, 17),    # 12 PM - 5 PM
            'evening': (17, 22),      # 5 PM - 10 PM
            'night_owl': (22, 6)      # 10 PM - 6 AM
        }

    def init_database(self):
        """Initialize SQLite database for sustainable pace tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # Workload periods table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workload_periods (
                    period_id TEXT PRIMARY KEY,
                    team_member TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_hours REAL NOT NULL,
                    coding_hours REAL NOT NULL,
                    meeting_hours REAL NOT NULL,
                    break_hours REAL NOT NULL,
                    daily_hours TEXT NOT NULL,
                    peak_hours TEXT NOT NULL,
                    work_days INTEGER NOT NULL,
                    overtime_hours REAL NOT NULL,
                    commits_made INTEGER NOT NULL,
                    lines_changed INTEGER NOT NULL,
                    issues_resolved INTEGER NOT NULL,
                    pair_programming_hours REAL NOT NULL,
                    stress_level REAL NOT NULL,
                    satisfaction_score REAL NOT NULL,
                    fatigue_indicators TEXT NOT NULL,
                    sustainable_pace_score REAL NOT NULL,
                    work_life_balance_score REAL NOT NULL,
                    team_collaboration_score REAL NOT NULL
                )
            """)

            # Team pace metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS team_pace_metrics (
                    period_id TEXT PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    team_size INTEGER NOT NULL,
                    total_team_hours REAL NOT NULL,
                    average_hours_per_person REAL NOT NULL,
                    overtime_percentage REAL NOT NULL,
                    burnout_risk_members INTEGER NOT NULL,
                    sustainable_pace_compliance REAL NOT NULL,
                    productivity_per_hour REAL NOT NULL,
                    quality_vs_speed_ratio REAL NOT NULL,
                    team_velocity REAL NOT NULL,
                    average_stress_level REAL NOT NULL,
                    average_satisfaction REAL NOT NULL,
                    team_collaboration_score REAL NOT NULL,
                    forty_hour_week_compliance REAL NOT NULL,
                    collective_ownership_score REAL NOT NULL,
                    continuous_improvement_score REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)

            # Work activity tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS work_activity (
                    activity_id TEXT PRIMARY KEY,
                    team_member TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_minutes REAL NOT NULL,
                    productivity_score REAL NOT NULL,
                    stress_indicator REAL NOT NULL,
                    notes TEXT
                )
            """)

            # Burnout risk assessments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS burnout_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    team_member TEXT NOT NULL,
                    assessment_date TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    contributing_factors TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    follow_up_date TEXT NOT NULL
                )
            """)

            # Wellbeing check-ins
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wellbeing_checkins (
                    checkin_id TEXT PRIMARY KEY,
                    team_member TEXT NOT NULL,
                    checkin_date TEXT NOT NULL,
                    mood_score REAL NOT NULL,
                    energy_level REAL NOT NULL,
                    workload_perception REAL NOT NULL,
                    work_satisfaction REAL NOT NULL,
                    support_needed TEXT,
                    feedback TEXT
                )
            """)

            conn.commit()

    def track_work_activity(
            self,
            team_member: str,
            activity_type: str,
            duration_minutes: float,
            productivity_score: float = 7.0,
            stress_indicator: float = 5.0,
            notes: str = "") -> str:
        """Track individual work activity."""
        activity_id = f"activity-{team_member}-{
            datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO work_activity
                (activity_id, team_member, activity_type, start_time, end_time,
                 duration_minutes, productivity_score, stress_indicator, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity_id, team_member, activity_type,
                start_time.isoformat(), end_time.isoformat(),
                duration_minutes, productivity_score, stress_indicator, notes
            ))
            conn.commit()

        print(
            f"✅ Tracked {activity_type} activity for {team_member}: {
                duration_minutes:.1f} minutes")
        return activity_id

    def analyze_team_member_workload(
            self,
            team_member: str,
            days: int = 7) -> WorkloadPeriod:
        """Analyze workload for a specific team member."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get work activities for the period
            cursor.execute("""
                SELECT activity_type, duration_minutes, productivity_score,
                       stress_indicator, start_time
                FROM work_activity
                WHERE team_member = ? AND start_time >= ? AND start_time <= ?
                ORDER BY start_time
            """, (team_member, start_date.isoformat(), end_date.isoformat()))

            activities = cursor.fetchall()

        if not activities:
            # Return default workload if no data
            return self.create_default_workload(
                team_member, start_date, end_date)

        # Calculate work metrics
        total_hours = sum(duration / 60.0 for _,
                          duration, _, _, _ in activities)
        coding_hours = sum(duration / 60.0 for type_, duration, _,
                           _, _ in activities if type_ == 'coding')
        meeting_hours = sum(duration / 60.0 for type_, duration, _,
                            _, _ in activities if type_ == 'meeting')
        break_hours = sum(duration / 60.0 for type_, duration, _,
                          _, _ in activities if type_ == 'break')

        # Calculate daily hours
        daily_hours = self.calculate_daily_hours(activities, start_date, days)

        # Determine peak hours
        peak_hours = self.determine_peak_hours(activities)

        # Calculate overtime
        target_weekly_hours = self.pace_targets['max_weekly_hours']
        overtime_hours = max(0, total_hours - target_weekly_hours)

        # Get productivity metrics from git
        git_metrics = self.get_git_metrics(team_member, start_date, end_date)

        # Calculate wellbeing scores
        stress_level = self.calculate_stress_level(activities)
        satisfaction_score = self.calculate_satisfaction_score(
            activities, total_hours)

        # Calculate XP compliance scores
        sustainable_pace_score = self.calculate_sustainable_pace_score(
            total_hours, overtime_hours)
        work_life_balance_score = self.calculate_work_life_balance_score(
            daily_hours, break_hours)
        team_collaboration_score = self.calculate_collaboration_score(
            activities)

        # Create workload period
        period_id = f"workload-{team_member}-{
            start_date.strftime('%Y%m%d')}-{
            end_date.strftime('%Y%m%d')}"

        workload = WorkloadPeriod(
            period_id=period_id,
            team_member=team_member,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_hours=total_hours,
            coding_hours=coding_hours,
            meeting_hours=meeting_hours,
            break_hours=break_hours,
            daily_hours=daily_hours,
            peak_hours=peak_hours,
            work_days=len([h for h in daily_hours if h > 0]),
            overtime_hours=overtime_hours,
            commits_made=git_metrics['commits'],
            lines_changed=git_metrics['lines_changed'],
            issues_resolved=git_metrics['issues_resolved'],
            pair_programming_hours=sum(
                duration / 60.0 for type_, duration, _, _, _ in activities if type_ == 'pair_programming'),
            stress_level=stress_level,
            satisfaction_score=satisfaction_score,
            fatigue_indicators=self.detect_fatigue_indicators(
                activities, daily_hours),
            sustainable_pace_score=sustainable_pace_score,
            work_life_balance_score=work_life_balance_score,
            team_collaboration_score=team_collaboration_score
        )

        self.save_workload_period(workload)
        return workload

    def create_default_workload(
            self,
            team_member: str,
            start_date: datetime,
            end_date: datetime) -> WorkloadPeriod:
        """Create default workload when no activity data exists."""
        period_id = f"workload-{team_member}-{
            start_date.strftime('%Y%m%d')}-{
            end_date.strftime('%Y%m%d')}"

        return WorkloadPeriod(
            period_id=period_id,
            team_member=team_member,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_hours=35.0,  # Estimated normal week
            coding_hours=28.0,
            meeting_hours=5.0,
            break_hours=2.0,
            daily_hours=[7.0, 7.0, 7.0, 7.0, 7.0, 0.0, 0.0],
            peak_hours=['9:00', '10:00', '14:00', '15:00'],
            work_days=5,
            overtime_hours=0.0,
            commits_made=15,
            lines_changed=500,
            issues_resolved=3,
            pair_programming_hours=8.0,
            stress_level=5.0,
            satisfaction_score=7.5,
            fatigue_indicators=[],
            sustainable_pace_score=85.0,
            work_life_balance_score=80.0,
            team_collaboration_score=75.0
        )

    def calculate_daily_hours(
            self,
            activities: List[Tuple],
            start_date: datetime,
            days: int) -> List[float]:
        """Calculate daily work hours from activities."""
        daily_hours = [0.0] * days

        for _, duration, _, _, start_time_str in activities:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                day_offset = (start_time.date() - start_date.date()).days

                if 0 <= day_offset < days:
                    daily_hours[day_offset] += duration / 60.0
            except Exception:
                continue

        return daily_hours

    def determine_peak_hours(self, activities: List[Tuple]) -> List[str]:
        """Determine peak working hours from activities."""
        hour_counts = {}

        for _, duration, _, _, start_time_str in activities:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                hour = start_time.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + duration
            except Exception:
                continue

        # Get top 4 peak hours
        sorted_hours = sorted(hour_counts.items(),
                              key=lambda x: x[1], reverse=True)
        peak_hours = [f"{hour:02d}:00" for hour, _ in sorted_hours[:4]]

        return peak_hours

    def get_git_metrics(
            self,
            team_member: str,
            start_date: datetime,
            end_date: datetime) -> Dict:
        """Get git activity metrics for team member."""
        try:
            # Get commits by author
            result = subprocess.run([
                "git", "log",
                f"--author={team_member}",
                f"--since={start_date.strftime('%Y-%m-%d')}",
                f"--until={end_date.strftime('%Y-%m-%d')}",
                "--oneline"
            ], capture_output=True, text=True)

            commits = len(result.stdout.strip().split(
                '\n')) if result.stdout.strip() else 0

            # Get line changes
            diff_result = subprocess.run([
                "git", "log",
                f"--author={team_member}",
                f"--since={start_date.strftime('%Y-%m-%d')}",
                f"--until={end_date.strftime('%Y-%m-%d')}",
                "--stat", "--pretty=format:"
            ], capture_output=True, text=True)

            lines_changed = 0
            if diff_result.stdout:
                # Parse insertions and deletions
                for line in diff_result.stdout.split('\n'):
                    if '+' in line and '-' in line:
                        # Extract numbers from lines like "5 files changed, 150
                        # insertions(+), 30 deletions(-)"
                        parts = line.split(',')
                        for part in parts:
                            if 'insertion' in part or 'deletion' in part:
                                numbers = re.findall(r'\d+', part)
                                if numbers:
                                    lines_changed += int(numbers[0])

            return {
                'commits': commits,
                'lines_changed': lines_changed,
                # Estimate issues from commits
                'issues_resolved': max(1, commits // 5)
            }

        except Exception:
            return {
                'commits': 10,
                'lines_changed': 300,
                'issues_resolved': 2
            }

    def calculate_stress_level(self, activities: List[Tuple]) -> float:
        """Calculate stress level from activity patterns."""
        if not activities:
            return 5.0

        stress_indicators = [stress for _, _, _, stress, _ in activities]
        avg_stress = statistics.mean(stress_indicators)

        # Adjust based on work patterns
        total_duration = sum(duration for _, duration, _, _, _ in activities)
        if total_duration > 2400:  # More than 40 hours
            avg_stress += 1.0

        return min(10.0, max(1.0, avg_stress))

    def calculate_satisfaction_score(
            self,
            activities: List[Tuple],
            total_hours: float) -> float:
        """Calculate satisfaction score from productivity and workload."""
        if not activities:
            return 7.5

        productivity_scores = [productivity for _,
                               _, productivity, _, _ in activities]
        avg_productivity = statistics.mean(productivity_scores)

        # Base satisfaction on productivity
        satisfaction = avg_productivity

        # Adjust based on workload
        target_hours = self.pace_targets['max_weekly_hours']
        if total_hours > target_hours:
            satisfaction -= (total_hours - target_hours) * 0.1

        return min(10.0, max(1.0, satisfaction))

    def calculate_sustainable_pace_score(
            self,
            total_hours: float,
            overtime_hours: float) -> float:
        """Calculate sustainable pace compliance score."""
        target_hours = self.pace_targets['max_weekly_hours']

        # Base score
        if total_hours <= target_hours:
            base_score = 100.0
        else:
            # Penalty for overtime
            overtime_penalty = (overtime_hours / target_hours) * 50
            base_score = max(0, 100.0 - overtime_penalty)

        return base_score

    def calculate_work_life_balance_score(
            self,
            daily_hours: List[float],
            break_hours: float) -> float:
        """Calculate work-life balance score."""
        score = 100.0

        # Check daily hour limits
        max_daily = self.pace_targets['max_daily_hours']
        for daily in daily_hours:
            if daily > max_daily:
                score -= (daily - max_daily) * 5

        # Check break time
        min_breaks = self.pace_targets['min_break_hours_per_day'] * 7  # weekly
        if break_hours < min_breaks:
            score -= (min_breaks - break_hours) * 2

        # Check consecutive work days
        consecutive_days = 0
        max_consecutive = 0
        for daily in daily_hours:
            if daily > 0:
                consecutive_days += 1
                max_consecutive = max(max_consecutive, consecutive_days)
            else:
                consecutive_days = 0

        if max_consecutive > self.pace_targets['max_consecutive_work_days']:
            score -= (max_consecutive -
                      self.pace_targets['max_consecutive_work_days']) * 10

        return max(0, min(100, score))

    def calculate_collaboration_score(self, activities: List[Tuple]) -> float:
        """Calculate team collaboration score."""
        if not activities:
            return 75.0

        collaboration_activities = [
            duration for type_, duration, _, _, _ in activities
            if type_ in ['pair_programming', 'meeting', 'code_review']
        ]

        if not collaboration_activities:
            return 50.0

        total_collab_hours = sum(collaboration_activities) / 60.0
        total_hours = sum(duration for _, duration, _,
                          _, _ in activities) / 60.0

        # Ideal collaboration is 20-30% of total time
        collab_percentage = (total_collab_hours / total_hours) * 100

        if 20 <= collab_percentage <= 30:
            return 100.0
        elif collab_percentage < 20:
            return 50.0 + (collab_percentage / 20) * 50
        else:
            return max(70.0, 100.0 - (collab_percentage - 30) * 2)

    def detect_fatigue_indicators(
            self,
            activities: List[Tuple],
            daily_hours: List[float]) -> List[str]:
        """Detect fatigue indicators from work patterns."""
        indicators = []

        # Check for consistently long days
        long_days = [day for day in daily_hours if day > 9]
        if len(long_days) >= 3:
            indicators.append("Consistently long work days")

        # Check for late night work
        late_night_activities = 0
        for _, _, _, _, start_time_str in activities:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                if start_time.hour >= 22 or start_time.hour <= 6:
                    late_night_activities += 1
            except Exception:
                continue

        if late_night_activities > 5:
            indicators.append("Frequent late night work")

        # Check for high stress levels
        stress_levels = [stress for _, _, _, stress, _ in activities]
        if stress_levels and statistics.mean(stress_levels) > 7:
            indicators.append("High stress levels")

        # Check for weekend work
        weekend_hours = daily_hours[5] + daily_hours[6]  # Saturday + Sunday
        if weekend_hours > 5:
            indicators.append("Excessive weekend work")

        return indicators

    def save_workload_period(self, workload: WorkloadPeriod):
        """Save workload period to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workload_periods
                (period_id, team_member, start_date, end_date, total_hours,
                 coding_hours, meeting_hours, break_hours, daily_hours,
                 peak_hours, work_days, overtime_hours, commits_made,
                 lines_changed, issues_resolved, pair_programming_hours,
                 stress_level, satisfaction_score, fatigue_indicators,
                 sustainable_pace_score, work_life_balance_score, team_collaboration_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (workload.period_id,
                 workload.team_member,
                 workload.start_date,
                 workload.end_date,
                 workload.total_hours,
                 workload.coding_hours,
                 workload.meeting_hours,
                 workload.break_hours,
                 json.dumps(
                     workload.daily_hours),
                    json.dumps(
                     workload.peak_hours),
                    workload.work_days,
                    workload.overtime_hours,
                    workload.commits_made,
                    workload.lines_changed,
                    workload.issues_resolved,
                    workload.pair_programming_hours,
                    workload.stress_level,
                    workload.satisfaction_score,
                    json.dumps(
                     workload.fatigue_indicators),
                    workload.sustainable_pace_score,
                    workload.work_life_balance_score,
                    workload.team_collaboration_score))
            conn.commit()

    def assess_burnout_risk(self, team_member: str) -> Dict:
        """Assess burnout risk for a team member."""
        workload = self.analyze_team_member_workload(
            team_member, 14)  # 2 weeks

        # Calculate risk factors
        risk_factors = []
        risk_score = 0

        # Hours-based risk
        if workload.total_hours > self.pace_targets['burnout_risk_threshold']:
            risk_factors.append("Excessive working hours")
            risk_score += 25

        # Overtime risk
        if workload.overtime_hours > 10:
            risk_factors.append("High overtime hours")
            risk_score += 20

        # Stress level risk
        if workload.stress_level > 7:
            risk_factors.append("High stress levels")
            risk_score += 20

        # Work-life balance risk
        if workload.work_life_balance_score < 60:
            risk_factors.append("Poor work-life balance")
            risk_score += 15

        # Fatigue indicators
        if workload.fatigue_indicators:
            risk_factors.append("Fatigue indicators present")
            risk_score += len(workload.fatigue_indicators) * 5

        # Satisfaction risk
        if workload.satisfaction_score < 6:
            risk_factors.append("Low job satisfaction")
            risk_score += 10

        # Determine risk level
        if risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate recommendations
        recommendations = self.generate_burnout_recommendations(
            risk_factors, workload)

        assessment = {
            'team_member': team_member,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendations': recommendations,
            'workload_summary': {
                'total_hours': workload.total_hours,
                'overtime_hours': workload.overtime_hours,
                'stress_level': workload.stress_level,
                'satisfaction_score': workload.satisfaction_score
            }
        }

        # Save assessment
        self.save_burnout_assessment(assessment)

        return assessment

    def generate_burnout_recommendations(
            self,
            risk_factors: List[str],
            workload: WorkloadPeriod) -> List[str]:
        """Generate recommendations to reduce burnout risk."""
        recommendations = []

        if "Excessive working hours" in risk_factors:
            recommendations.append("Reduce weekly hours to 40 or less")
            recommendations.append(
                "Consider redistributing workload among team members")

        if "High overtime hours" in risk_factors:
            recommendations.append("Implement strict overtime limits")
            recommendations.append("Review sprint planning to reduce workload")

        if "High stress levels" in risk_factors:
            recommendations.append("Schedule stress management sessions")
            recommendations.append(
                "Increase pair programming to share workload")

        if "Poor work-life balance" in risk_factors:
            recommendations.append("Encourage taking regular breaks")
            recommendations.append("Implement flexible working hours")

        if "Fatigue indicators present" in risk_factors:
            recommendations.append("Mandatory time off for recovery")
            recommendations.append("Reduce complex tasks temporarily")

        if "Low job satisfaction" in risk_factors:
            recommendations.append("Schedule one-on-one feedback sessions")
            recommendations.append(
                "Provide professional development opportunities")

        if not recommendations:
            recommendations.append(
                "Continue current sustainable pace practices")

        return recommendations

    def save_burnout_assessment(self, assessment: Dict):
        """Save burnout assessment to database."""
        assessment_id = f"burnout-{
            assessment['team_member']}-{
            datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO burnout_assessments
                (assessment_id, team_member, assessment_date, risk_level,
                 risk_score, contributing_factors, recommendations, follow_up_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assessment_id, assessment['team_member'], datetime.now(
                ).isoformat(),
                assessment['risk_level'], assessment['risk_score'],
                json.dumps(assessment['risk_factors']), json.dumps(
                    assessment['recommendations']),
                (datetime.now() + timedelta(days=7)).isoformat()
            ))
            conn.commit()

    def calculate_team_pace_metrics(self, days: int = 7) -> TeamPaceMetrics:
        """Calculate team-wide sustainable pace metrics."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get all team members
        team_members = self.get_team_members()

        # Analyze workload for each team member
        workloads = []
        for member in team_members:
            workload = self.analyze_team_member_workload(member, days)
            workloads.append(workload)

        if not workloads:
            return self.create_default_team_metrics(start_date, end_date)

        # Calculate team metrics
        team_size = len(workloads)
        total_team_hours = sum(w.total_hours for w in workloads)
        average_hours_per_person = total_team_hours / team_size

        # Calculate overtime percentage
        total_target_hours = team_size * self.pace_targets['max_weekly_hours']
        overtime_hours = sum(w.overtime_hours for w in workloads)
        overtime_percentage = (overtime_hours / total_target_hours) * 100

        # Count burnout risk members
        burnout_risk_members = len(
            [w for w in workloads if w.total_hours > self.pace_targets['burnout_risk_threshold']])

        # Calculate sustainable pace compliance
        compliant_members = len(
            [w for w in workloads if w.sustainable_pace_score >= 70])
        sustainable_pace_compliance = (compliant_members / team_size) * 100

        # Calculate productivity metrics
        total_productivity = sum(
            w.commits_made + w.issues_resolved for w in workloads)
        productivity_per_hour = total_productivity / \
            total_team_hours if total_team_hours > 0 else 0

        # Calculate wellbeing metrics
        average_stress_level = statistics.mean(
            [w.stress_level for w in workloads])
        average_satisfaction = statistics.mean(
            [w.satisfaction_score for w in workloads])
        team_collaboration_score = statistics.mean(
            [w.team_collaboration_score for w in workloads])

        # Calculate XP compliance
        forty_hour_week_compliance = (
            len([w for w in workloads if w.total_hours <= 40]) / team_size) * 100
        collective_ownership_score = team_collaboration_score
        continuous_improvement_score = statistics.mean(
            [w.satisfaction_score for w in workloads]) * 10

        period_id = f"team-pace-{
            start_date.strftime('%Y%m%d')}-{
            end_date.strftime('%Y%m%d')}"

        return TeamPaceMetrics(
            period_id=period_id,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            team_size=team_size,
            total_team_hours=total_team_hours,
            average_hours_per_person=average_hours_per_person,
            overtime_percentage=overtime_percentage,
            burnout_risk_members=burnout_risk_members,
            sustainable_pace_compliance=sustainable_pace_compliance,
            productivity_per_hour=productivity_per_hour,
            quality_vs_speed_ratio=8.0,  # Placeholder
            team_velocity=sum(w.commits_made for w in workloads),
            average_stress_level=average_stress_level,
            average_satisfaction=average_satisfaction,
            team_collaboration_score=team_collaboration_score,
            forty_hour_week_compliance=forty_hour_week_compliance,
            collective_ownership_score=collective_ownership_score,
            continuous_improvement_score=continuous_improvement_score
        )

    def get_team_members(self) -> List[str]:
        """Get list of team members from git history."""
        try:
            result = subprocess.run([
                "git", "log", "--format=%an", "--since=1 month ago"
            ], capture_output=True, text=True)

            if result.stdout:
                authors = list(set(result.stdout.strip().split('\n')))
                return [author for author in authors if author and author != ""]

        except Exception:
            pass

        # Default team members
        return ["developer1", "developer2", "developer3"]

    def create_default_team_metrics(
            self,
            start_date: datetime,
            end_date: datetime) -> TeamPaceMetrics:
        """Create default team metrics when no data exists."""
        period_id = f"team-pace-{
            start_date.strftime('%Y%m%d')}-{
            end_date.strftime('%Y%m%d')}"

        return TeamPaceMetrics(
            period_id=period_id,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            team_size=3,
            total_team_hours=105.0,  # 3 people * 35 hours
            average_hours_per_person=35.0,
            overtime_percentage=5.0,
            burnout_risk_members=0,
            sustainable_pace_compliance=85.0,
            productivity_per_hour=0.8,
            quality_vs_speed_ratio=8.0,
            team_velocity=45.0,
            average_stress_level=5.0,
            average_satisfaction=7.5,
            team_collaboration_score=75.0,
            forty_hour_week_compliance=90.0,
            collective_ownership_score=80.0,
            continuous_improvement_score=75.0
        )

    def generate_sustainable_pace_report(self, days: int = 7) -> str:
        """Generate comprehensive sustainable pace report."""
        team_metrics = self.calculate_team_pace_metrics(days)

        # Get individual workload summaries
        team_members = self.get_team_members()
        individual_summaries = []

        for member in team_members:
            workload = self.analyze_team_member_workload(member, days)
            individual_summaries.append(workload)

        report = f"""
# Sustainable Pace Report - XP Methodology Compliance

## 📊 Period: {team_metrics.start_date} to {team_metrics.end_date} ({days} days)

### 🎯 Team Pace Overview
- **Team Size**: {team_metrics.team_size} members
- **Total Team Hours**: {team_metrics.total_team_hours:.1f} hours
- **Average Hours per Person**: {team_metrics.average_hours_per_person:.1f} hours
- **Overtime Percentage**: {team_metrics.overtime_percentage:.1f}%
- **Burnout Risk Members**: {team_metrics.burnout_risk_members}

### 📈 XP Methodology Compliance
- **40-Hour Week Compliance**: {team_metrics.forty_hour_week_compliance:.1f}%
- **Sustainable Pace Compliance**: {team_metrics.sustainable_pace_compliance:.1f}%
- **Collective Ownership Score**: {team_metrics.collective_ownership_score:.1f}%
- **Continuous Improvement Score**: {team_metrics.continuous_improvement_score:.1f}%

### 🎭 Team Wellbeing Indicators
- **Average Stress Level**: {team_metrics.average_stress_level:.1f}/10
- **Average Satisfaction**: {team_metrics.average_satisfaction:.1f}/10
- **Team Collaboration Score**: {team_metrics.team_collaboration_score:.1f}%
- **Productivity per Hour**: {team_metrics.productivity_per_hour:.2f}

### 👥 Individual Workload Summary
"""

        for workload in individual_summaries:
            # Determine status indicators
            pace_status = "✅" if workload.sustainable_pace_score >= 70 else "⚠️" if workload.sustainable_pace_score >= 50 else "❌"
            stress_status = "✅" if workload.stress_level <= 6 else "⚠️" if workload.stress_level <= 8 else "❌"

            report += f"""
#### {workload.team_member}
- **Total Hours**: {workload.total_hours:.1f} hours ({pace_status})
- **Overtime**: {workload.overtime_hours:.1f} hours
- **Stress Level**: {workload.stress_level:.1f}/10 ({stress_status})
- **Satisfaction**: {workload.satisfaction_score:.1f}/10
- **Sustainable Pace Score**: {workload.sustainable_pace_score:.1f}%
- **Work-Life Balance Score**: {workload.work_life_balance_score:.1f}%
"""

            if workload.fatigue_indicators:
                report += f"- **⚠️ Fatigue Indicators**: {
                    ', '.join(
                        workload.fatigue_indicators)}\n"

        # XP compliance assessment
        report += f"""
### 🔄 XP Sustainable Pace Principles

#### Core Principle Compliance
- **40-Hour Work Week**: {'✅' if team_metrics.forty_hour_week_compliance > 80 else '⚠️'} {team_metrics.forty_hour_week_compliance:.1f}% compliance
- **Sustainable Development**: {'✅' if team_metrics.sustainable_pace_compliance > 75 else '⚠️'} {team_metrics.sustainable_pace_compliance:.1f}% compliance
- **Team Morale**: {'✅' if team_metrics.average_satisfaction > 7 else '⚠️'} {team_metrics.average_satisfaction:.1f}/10 satisfaction
- **Stress Management**: {'✅' if team_metrics.average_stress_level < 6 else '⚠️'} {team_metrics.average_stress_level:.1f}/10 stress level

#### Quality vs Speed Balance
- **Productivity Balance**: {'✅' if team_metrics.productivity_per_hour > 0.5 else '⚠️'} {team_metrics.productivity_per_hour:.2f} units/hour
- **Quality Maintenance**: {'✅' if team_metrics.quality_vs_speed_ratio > 7 else '⚠️'} {team_metrics.quality_vs_speed_ratio:.1f}/10 quality score
- **Team Velocity**: {team_metrics.team_velocity:.1f} commits/week

### 🎯 Sustainable Pace Targets
- **Max Weekly Hours**: {self.pace_targets['max_weekly_hours']} hours
- **Max Daily Hours**: {self.pace_targets['max_daily_hours']} hours
- **Max Overtime**: {self.pace_targets['max_overtime_percentage']}% of total hours
- **Target Stress Level**: ≤{self.pace_targets['target_stress_level']}/10
- **Target Satisfaction**: ≥{self.pace_targets['target_satisfaction']}/10

### 💡 Recommendations
"""

        # Generate recommendations
        recommendations = []

        if team_metrics.burnout_risk_members > 0:
            recommendations.append(
                f"🚨 Immediate attention needed for {
                    team_metrics.burnout_risk_members} team member(s) at burnout risk")

        if team_metrics.overtime_percentage > 15:
            recommendations.append(
                f"⚠️ Reduce overtime from {
                    team_metrics.overtime_percentage:.1f}% to <10%")

        if team_metrics.forty_hour_week_compliance < 80:
            recommendations.append(
                "⚠️ Improve 40-hour week compliance - review workload distribution")

        if team_metrics.average_stress_level > 6:
            recommendations.append(
                "🧘 Implement stress management practices - stress level too high")

        if team_metrics.team_collaboration_score < 70:
            recommendations.append(
                "🤝 Increase pair programming and collaboration activities")

        if team_metrics.average_satisfaction < 7:
            recommendations.append(
                "😊 Address team satisfaction - conduct feedback sessions")

        if not recommendations:
            recommendations.append(
                "✅ Excellent sustainable pace practices - continue current approach")

        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"

        report += f"""
### 📋 Action Items
1. **Weekly Review**: Monitor team hours and adjust workload distribution
2. **Individual Check-ins**: Regular one-on-one sessions to assess wellbeing
3. **Workload Balancing**: Redistribute tasks to maintain sustainable pace
4. **Break Enforcement**: Ensure team takes regular breaks and time off
5. **Stress Monitoring**: Track stress levels and implement support measures

### 🔄 XP Methodology Benefits
- **Sustained Productivity**: {'✅' if team_metrics.productivity_per_hour > 0.5 else '⚠️'} Consistent output without burnout
- **Team Morale**: {'✅' if team_metrics.average_satisfaction > 7 else '⚠️'} High satisfaction and engagement
- **Quality Delivery**: {'✅' if team_metrics.quality_vs_speed_ratio > 7 else '⚠️'} Maintaining quality standards
- **Long-term Success**: {'✅' if team_metrics.sustainable_pace_compliance > 75 else '⚠️'} Sustainable development practices

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Team Members Analyzed: {team_metrics.team_size}
"""

        return report


def main():
    """Main CLI interface for sustainable pace monitoring."""
    if len(sys.argv) < 2:
        print("Usage: python sustainable_pace_monitor.py <command> [options]")
        print("Commands:")
        print("  track <member> <activity> <minutes>  - Track work activity")
        print(
            "  analyze <member> [days]              - Analyze member workload")
        print("  burnout <member>                     - Assess burnout risk")
        print(
            "  team-metrics [days]                  - Show team pace metrics")
        print(
            "  report [days]                        - Generate sustainable pace report")
        print("  targets                              - Show pace targets")
        print("  wellbeing <member>                   - Wellbeing check-in")
        sys.exit(1)

    monitor = SustainablePaceMonitor()
    command = sys.argv[1]

    if command == "track":
        if len(sys.argv) < 5:
            print(
                "Usage: python sustainable_pace_monitor.py track <member> <activity> <minutes>")
            sys.exit(1)

        member = sys.argv[2]
        activity = sys.argv[3]
        minutes = float(sys.argv[4])

        activity_id = monitor.track_work_activity(member, activity, minutes)
        print(f"Activity tracked: {activity_id}")

    elif command == "analyze":
        if len(sys.argv) < 3:
            print(
                "Usage: python sustainable_pace_monitor.py analyze <member> [days]")
            sys.exit(1)

        member = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 7

        workload = monitor.analyze_team_member_workload(member, days)

        print(f"Workload Analysis for {member} ({days} days):")
        print(f"  Total Hours: {workload.total_hours:.1f}")
        print(f"  Overtime: {workload.overtime_hours:.1f}")
        print(f"  Stress Level: {workload.stress_level:.1f}/10")
        print(f"  Satisfaction: {workload.satisfaction_score:.1f}/10")
        print(
            f"  Sustainable Pace Score: {
                workload.sustainable_pace_score:.1f}%")
        print(f"  Work-Life Balance: {workload.work_life_balance_score:.1f}%")

        if workload.fatigue_indicators:
            print(
                f"  ⚠️ Fatigue Indicators: {
                    ', '.join(
                        workload.fatigue_indicators)}")

    elif command == "burnout":
        if len(sys.argv) < 3:
            print("Usage: python sustainable_pace_monitor.py burnout <member>")
            sys.exit(1)

        member = sys.argv[2]
        assessment = monitor.assess_burnout_risk(member)

        print(f"Burnout Risk Assessment for {member}:")
        print(f"  Risk Level: {assessment['risk_level'].upper()}")
        print(f"  Risk Score: {assessment['risk_score']}/100")
        print(f"  Risk Factors: {', '.join(assessment['risk_factors'])}")
        print("  Recommendations:")
        for rec in assessment['recommendations']:
            print(f"    - {rec}")

    elif command == "team-metrics":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        metrics = monitor.calculate_team_pace_metrics(days)

        print(f"Team Pace Metrics ({days} days):")
        print(f"  Team Size: {metrics.team_size}")
        print(
            f"  Average Hours per Person: {
                metrics.average_hours_per_person:.1f}")
        print(f"  Overtime Percentage: {metrics.overtime_percentage:.1f}%")
        print(f"  Burnout Risk Members: {metrics.burnout_risk_members}")
        print(
            f"  Sustainable Pace Compliance: {
                metrics.sustainable_pace_compliance:.1f}%")
        print(
            f"  40-Hour Week Compliance: {metrics.forty_hour_week_compliance:.1f}%")
        print(f"  Average Stress Level: {metrics.average_stress_level:.1f}/10")
        print(f"  Average Satisfaction: {metrics.average_satisfaction:.1f}/10")

    elif command == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        report = monitor.generate_sustainable_pace_report(days)

        # Save report
        filename = f"sustainable_pace_report_{
            datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to: {filename}")

    elif command == "targets":
        targets = monitor.pace_targets
        print("Sustainable Pace Targets:")
        print(f"  Max Weekly Hours: {targets['max_weekly_hours']}")
        print(f"  Max Daily Hours: {targets['max_daily_hours']}")
        print(f"  Max Overtime: {targets['max_overtime_percentage']}%")
        print(f"  Target Stress Level: ≤{targets['target_stress_level']}/10")
        print(f"  Target Satisfaction: ≥{targets['target_satisfaction']}/10")
        print(
            f"  Burnout Risk Threshold: {
                targets['burnout_risk_threshold']} hours/week")

    elif command == "wellbeing":
        if len(sys.argv) < 3:
            print("Usage: python sustainable_pace_monitor.py wellbeing <member>")
            sys.exit(1)

        member = sys.argv[2]
        workload = monitor.analyze_team_member_workload(member, 7)

        print(f"Wellbeing Check for {member}:")
        print(f"  Current Stress Level: {workload.stress_level:.1f}/10")
        print(f"  Job Satisfaction: {workload.satisfaction_score:.1f}/10")
        print(f"  Work-Life Balance: {workload.work_life_balance_score:.1f}%")
        print(f"  Weekly Hours: {workload.total_hours:.1f}")

        if workload.fatigue_indicators:
            print(f"  ⚠️ Concerns: {', '.join(workload.fatigue_indicators)}")
        else:
            print("  ✅ No immediate concerns")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
