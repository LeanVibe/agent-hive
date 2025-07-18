#!/usr/bin/env python3
"""
Automated Sprint Planning System
Part of PM/XP Methodology Enforcer

This module implements automated sprint planning workflows with GitHub Issues integration,
velocity tracking, and story point estimation for XP methodology enforcement.
"""

import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class SprintStory:
    """Represents a user story in a sprint."""
    id: str
    title: str
    description: str
    story_points: int
    status: str  # 'planned', 'in_progress', 'completed', 'blocked'
    assignee: Optional[str] = None
    github_issue_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class SprintPlan:
    """Represents a complete sprint plan."""
    sprint_id: str
    sprint_name: str
    start_date: str
    end_date: str
    goal: str
    team_velocity: int
    planned_points: int
    stories: List[SprintStory]
    status: str  # 'planned', 'active', 'completed', 'cancelled'
    created_at: str
    updated_at: str


class SprintPlanningSystem:
    """Automated sprint planning system with GitHub integration."""

    def __init__(self, db_path: str = "sprint_data.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for sprint data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sprints (
                    sprint_id TEXT PRIMARY KEY,
                    sprint_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    team_velocity INTEGER NOT NULL,
                    planned_points INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    sprint_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    story_points INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    assignee TEXT,
                    github_issue_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (sprint_id) REFERENCES sprints (sprint_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS velocity_history (
                    sprint_id TEXT PRIMARY KEY,
                    planned_points INTEGER NOT NULL,
                    completed_points INTEGER NOT NULL,
                    completion_rate REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)

            conn.commit()

    def calculate_team_velocity(
            self, lookback_sprints: int = 3) -> Tuple[int, Dict]:
        """Calculate team velocity based on historical data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT planned_points, completed_points, completion_rate
                FROM velocity_history
                ORDER BY recorded_at DESC
                LIMIT ?
            """, (lookback_sprints,))

            history = cursor.fetchall()

        if not history:
            # Default velocity for new teams
            return 40, {
                "average_velocity": 40,
                "completion_rate": 0.8,
                "confidence": "low",
                "recommendation": "Starting with conservative 40 points for new team"
            }

        # Calculate statistics
        total_completed = sum(row[1] for row in history)
        total_planned = sum(row[0] for row in history)
        avg_completion_rate = sum(row[2] for row in history) / len(history)

        # Calculate velocity with confidence adjustment
        avg_velocity = total_completed / len(history)
        confidence = "high" if len(history) >= 3 else "medium"

        metrics = {
            "average_velocity": int(avg_velocity),
            "completion_rate": avg_completion_rate,
            "confidence": confidence,
            "sprints_analyzed": len(history),
            "total_completed": total_completed,
            "total_planned": total_planned
        }

        return int(avg_velocity), metrics

    def estimate_story_points(self, title: str, description: str) -> int:
        """Estimate story points based on title and description complexity."""
        # Simple heuristic-based estimation
        # In production, this could use ML models or historical data

        complexity_score = 0

        # Factor 1: Description length
        desc_length = len(description.split())
        if desc_length < 20:
            complexity_score += 1
        elif desc_length < 50:
            complexity_score += 3
        else:
            complexity_score += 5

        # Factor 2: Keywords indicating complexity
        high_complexity_keywords = [
            "integration",
            "api",
            "database",
            "authentication",
            "security",
            "performance",
            "optimization",
            "migration",
            "refactor",
            "architecture"]

        low_complexity_keywords = [
            "fix", "update", "text", "ui", "style", "copy", "documentation"
        ]

        text = (title + " " + description).lower()

        for keyword in high_complexity_keywords:
            if keyword in text:
                complexity_score += 2

        for keyword in low_complexity_keywords:
            if keyword in text:
                complexity_score -= 1

        # Factor 3: Title complexity indicators
        if "implement" in title.lower():
            complexity_score += 2
        elif "create" in title.lower():
            complexity_score += 1
        elif "fix" in title.lower():
            complexity_score -= 1

        # Convert to Fibonacci story points (1, 2, 3, 5, 8, 13, 21)
        [1, 2, 3, 5, 8, 13, 21]

        if complexity_score <= 2:
            return 1
        elif complexity_score <= 4:
            return 2
        elif complexity_score <= 6:
            return 3
        elif complexity_score <= 8:
            return 5
        elif complexity_score <= 10:
            return 8
        elif complexity_score <= 12:
            return 13
        else:
            return 21

    def fetch_github_issues(self, labels: List[str] = None) -> List[Dict]:
        """Fetch GitHub issues for sprint planning."""
        try:
            # Build gh command
            cmd = ["gh", "issue", "list", "--json",
                   "number,title,body,labels,assignees", "--limit", "50"]

            if labels:
                for label in labels:
                    cmd.extend(["--label", label])

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)

        except subprocess.CalledProcessError as e:
            print(f"Error fetching GitHub issues: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub issues: {e}")
            return []

    def create_sprint_plan(self,
                           sprint_name: str,
                           goal: str,
                           duration_days: int = 14,
                           include_labels: List[str] = None) -> SprintPlan:
        """Create a new sprint plan with automated story selection."""

        # Calculate sprint dates
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=duration_days)
                    ).strftime("%Y-%m-%d")

        # Calculate team velocity
        team_velocity, velocity_metrics = self.calculate_team_velocity()

        # Fetch and process GitHub issues
        github_issues = self.fetch_github_issues(include_labels)

        # Convert issues to stories with point estimation
        stories = []
        total_points = 0

        for issue in github_issues:
            if total_points >= team_velocity:
                break

            title = issue["title"]
            description = issue.get("body", "")
            estimated_points = self.estimate_story_points(title, description)

            # Don't exceed velocity
            if total_points + estimated_points > team_velocity:
                continue

            assignee = issue["assignees"][0]["login"] if issue["assignees"] else None

            story = SprintStory(
                id=f"story-{issue['number']}",
                title=title,
                description=description,
                story_points=estimated_points,
                status="planned",
                assignee=assignee,
                github_issue_url=f"https://github.com/LeanVibe/agent-hive/issues/{
    issue['number']}",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )

            stories.append(story)
            total_points += estimated_points

        # Create sprint plan
        sprint_id = f"sprint-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        sprint_plan = SprintPlan(
            sprint_id=sprint_id,
            sprint_name=sprint_name,
            start_date=start_date,
            end_date=end_date,
            goal=goal,
            team_velocity=team_velocity,
            planned_points=total_points,
            stories=stories,
            status="planned",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        # Save to database
        self.save_sprint_plan(sprint_plan)

        return sprint_plan

    def save_sprint_plan(self, sprint_plan: SprintPlan):
        """Save sprint plan to database."""
        with sqlite3.connect(self.db_path) as conn:
            # Save sprint
            conn.execute("""
                INSERT OR REPLACE INTO sprints
                (sprint_id, sprint_name, start_date, end_date, goal, team_velocity,
                 planned_points, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sprint_plan.sprint_id, sprint_plan.sprint_name,
                sprint_plan.start_date, sprint_plan.end_date,
                sprint_plan.goal, sprint_plan.team_velocity,
                sprint_plan.planned_points, sprint_plan.status,
                sprint_plan.created_at, sprint_plan.updated_at
            ))

            # Save stories
            for story in sprint_plan.stories:
                conn.execute("""
                    INSERT OR REPLACE INTO stories
                    (id, sprint_id, title, description, story_points, status,
                     assignee, github_issue_url, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    story.id, sprint_plan.sprint_id, story.title,
                    story.description, story.story_points, story.status,
                    story.assignee, story.github_issue_url,
                    story.created_at, story.updated_at
                ))

            conn.commit()

    def get_active_sprint(self) -> Optional[SprintPlan]:
        """Get the currently active sprint."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sprints
                WHERE status = 'active'
                ORDER BY start_date DESC
                LIMIT 1
            """)

            sprint_row = cursor.fetchone()
            if not sprint_row:
                return None

            # Get stories for this sprint
            cursor.execute("""
                SELECT * FROM stories
                WHERE sprint_id = ?
                ORDER BY created_at
            """, (sprint_row[0],))

            story_rows = cursor.fetchall()

            # Convert to objects
            stories = []
            for row in story_rows:
                stories.append(
                    SprintStory(
                        id=row[0],
                        title=row[2],
                        description=row[3],
                        story_points=row[4],
                        status=row[5],
                        assignee=row[6],
                        github_issue_url=row[7],
                        created_at=row[8],
                        updated_at=row[9]))

            return SprintPlan(
                sprint_id=sprint_row[0], sprint_name=sprint_row[1],
                start_date=sprint_row[2], end_date=sprint_row[3],
                goal=sprint_row[4], team_velocity=sprint_row[5],
                planned_points=sprint_row[6], stories=stories,
                status=sprint_row[7], created_at=sprint_row[8],
                updated_at=sprint_row[9]
            )

    def generate_sprint_report(self, sprint_plan: SprintPlan) -> str:
        """Generate a comprehensive sprint planning report."""
        report = f"""
# Sprint Planning Report: {sprint_plan.sprint_name}

## Sprint Overview
- **Sprint ID**: {sprint_plan.sprint_id}
- **Duration**: {sprint_plan.start_date} to {sprint_plan.end_date}
- **Goal**: {sprint_plan.goal}
- **Team Velocity**: {sprint_plan.team_velocity} points
- **Planned Points**: {sprint_plan.planned_points} points
- **Stories**: {len(sprint_plan.stories)} stories
- **Status**: {sprint_plan.status}

## Sprint Goal
{sprint_plan.goal}

## Story Breakdown
"""

        for story in sprint_plan.stories:
            report += f"""
### {story.title} ({story.story_points} points)
- **Status**: {story.status}
- **Assignee**: {story.assignee or 'Unassigned'}
- **GitHub Issue**: {story.github_issue_url or 'Not linked'}
- **Description**: {story.description[:200]}{'...' if len(story.description) > 200 else ''}
"""

        # Add velocity analysis
        velocity_capacity = sprint_plan.team_velocity
        planned_capacity = sprint_plan.planned_points
        capacity_utilization = (planned_capacity / velocity_capacity) * 100

        report += f"""
## Capacity Analysis
- **Team Velocity**: {velocity_capacity} points
- **Planned Work**: {planned_capacity} points
- **Capacity Utilization**: {capacity_utilization:.1f}%
- **Recommendation**: {'Optimal capacity' if 70 <= capacity_utilization <= 90 else 'Consider adjusting scope'}

## Next Steps
1. Review and approve sprint plan
2. Assign unassigned stories to team members
3. Break down large stories (>8 points) if needed
4. Set up sprint tracking and monitoring
5. Begin sprint execution

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report


def main():
    """Main CLI interface for sprint planning."""
    if len(sys.argv) < 2:
        print("Usage: python sprint_planning.py <command> [options]")
        print("Commands:")
        print("  create <sprint_name> <goal> [duration_days]")
        print("  report [sprint_id]")
        print("  velocity")
        print("  active")
        sys.exit(1)

    planner = SprintPlanningSystem()
    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 4:
            print(
                "Usage: python sprint_planning.py create <sprint_name> <goal> [duration_days]")
            sys.exit(1)

        sprint_name = sys.argv[2]
        goal = sys.argv[3]
        duration_days = int(sys.argv[4]) if len(sys.argv) > 4 else 14

        print(f"Creating sprint: {sprint_name}")
        print(f"Goal: {goal}")
        print(f"Duration: {duration_days} days")
        print("\nFetching GitHub issues...")

        sprint_plan = planner.create_sprint_plan(
            sprint_name, goal, duration_days)

        print("\n✅ Sprint created successfully!")
        print(f"Sprint ID: {sprint_plan.sprint_id}")
        print(f"Planned Points: {sprint_plan.planned_points}")
        print(f"Stories: {len(sprint_plan.stories)}")

        # Generate and save report
        report = planner.generate_sprint_report(sprint_plan)
        report_file = f"sprint_report_{sprint_plan.sprint_id}.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"Report saved to: {report_file}")

    elif command == "report":
        active_sprint = planner.get_active_sprint()
        if not active_sprint:
            print("No active sprint found.")
            sys.exit(1)

        report = planner.generate_sprint_report(active_sprint)
        print(report)

    elif command == "velocity":
        velocity, metrics = planner.calculate_team_velocity()
        print(f"Team Velocity: {velocity} points")
        print(f"Metrics: {json.dumps(metrics, indent=2)}")

    elif command == "active":
        active_sprint = planner.get_active_sprint()
        if active_sprint:
            print(f"Active Sprint: {active_sprint.sprint_name}")
            print(f"Progress: {active_sprint.planned_points} points planned")
            print(f"Stories: {len(active_sprint.stories)}")
        else:
            print("No active sprint found.")


if __name__ == "__main__":
    main()
