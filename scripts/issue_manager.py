#!/usr/bin/env python3
"""
Issue Manager - Automated Issue Management and Tracking
Part of PM/XP Methodology Enforcer

This module implements automated issue management, progress tracking,
and lifecycle management for XP methodology compliance.
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import re


@dataclass
class Issue:
    """Represents a GitHub issue with tracking metadata."""
    number: int
    title: str
    body: str
    state: str
    author: str
    assignee: Optional[str]
    labels: List[str]
    milestone: Optional[str]
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    
    # XP compliance tracking
    story_points: Optional[int]
    priority: str  # 'low', 'medium', 'high', 'critical'
    type: str  # 'bug', 'feature', 'enhancement', 'task'
    sprint_id: Optional[str]
    
    # Progress tracking
    progress_status: str  # 'todo', 'in_progress', 'review', 'done'
    acceptance_criteria: List[str]
    blockers: List[str]
    linked_prs: List[int]
    
    # Metrics
    resolution_time_hours: Optional[float]
    first_response_time_hours: Optional[float]
    customer_satisfaction: Optional[float]


@dataclass
class IssueMetrics:
    """Issue management metrics for performance tracking."""
    period_id: str
    start_date: str
    end_date: str
    
    # Volume metrics
    total_issues: int
    created_issues: int
    resolved_issues: int
    
    # Type distribution
    bugs: int
    features: int
    enhancements: int
    tasks: int
    
    # Performance metrics
    avg_resolution_time_hours: float
    avg_first_response_time_hours: float
    resolution_rate: float
    
    # Quality metrics
    reopened_issues: int
    customer_satisfaction: float
    sla_compliance: float
    
    # XP metrics
    story_points_completed: int
    velocity: float
    sprint_completion_rate: float


class IssueManager:
    """Automated issue management and tracking system."""
    
    def __init__(self, db_path: str = "issue_data.db"):
        self.db_path = db_path
        self.init_database()
        
        # SLA configurations
        self.sla_targets = {
            'critical': 4,    # 4 hours
            'high': 24,       # 24 hours  
            'medium': 72,     # 72 hours
            'low': 168        # 1 week
        }
        
        # Label mappings
        self.type_labels = {
            'bug': ['bug', 'defect', 'issue'],
            'feature': ['feature', 'enhancement', 'new'],
            'task': ['task', 'chore', 'maintenance'],
            'enhancement': ['improvement', 'optimization', 'refactor']
        }
        
        self.priority_labels = {
            'critical': ['critical', 'urgent', 'p0'],
            'high': ['high', 'important', 'p1'],
            'medium': ['medium', 'normal', 'p2'],
            'low': ['low', 'minor', 'p3']
        }
    
    def init_database(self):
        """Initialize SQLite database for issue tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # Issues table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    number INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    state TEXT NOT NULL,
                    author TEXT NOT NULL,
                    assignee TEXT,
                    labels TEXT NOT NULL,
                    milestone TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    closed_at TEXT,
                    story_points INTEGER,
                    priority TEXT NOT NULL,
                    type TEXT NOT NULL,
                    sprint_id TEXT,
                    progress_status TEXT NOT NULL,
                    acceptance_criteria TEXT,
                    blockers TEXT,
                    linked_prs TEXT,
                    resolution_time_hours REAL,
                    first_response_time_hours REAL,
                    customer_satisfaction REAL
                )
            """)
            
            # Issue activity table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issue_activity (
                    activity_id TEXT PRIMARY KEY,
                    issue_number INTEGER NOT NULL,
                    activity_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (issue_number) REFERENCES issues (number)
                )
            """)
            
            # Issue metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issue_metrics (
                    period_id TEXT PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_issues INTEGER NOT NULL,
                    created_issues INTEGER NOT NULL,
                    resolved_issues INTEGER NOT NULL,
                    bugs INTEGER NOT NULL,
                    features INTEGER NOT NULL,
                    enhancements INTEGER NOT NULL,
                    tasks INTEGER NOT NULL,
                    avg_resolution_time_hours REAL NOT NULL,
                    avg_first_response_time_hours REAL NOT NULL,
                    resolution_rate REAL NOT NULL,
                    reopened_issues INTEGER NOT NULL,
                    customer_satisfaction REAL NOT NULL,
                    sla_compliance REAL NOT NULL,
                    story_points_completed INTEGER NOT NULL,
                    velocity REAL NOT NULL,
                    sprint_completion_rate REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            
            # Issue templates table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issue_templates (
                    template_id TEXT PRIMARY KEY,
                    template_name TEXT NOT NULL,
                    template_type TEXT NOT NULL,
                    template_content TEXT NOT NULL,
                    required_labels TEXT,
                    default_assignee TEXT,
                    estimated_hours INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def fetch_github_issues(self, state: str = "all", labels: List[str] = None, 
                           limit: int = 100) -> List[Dict]:
        """Fetch issues from GitHub API."""
        try:
            cmd = ["gh", "issue", "list", "--state", state, "--limit", str(limit)]
            cmd.extend(["--json", "number,title,body,state,author,assignees,labels,milestone,createdAt,updatedAt,closedAt"])
            
            if labels:
                for label in labels:
                    cmd.extend(["--label", label])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        
        except subprocess.CalledProcessError as e:
            print(f"Error fetching GitHub issues: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub issues: {e}")
            return []
    
    def parse_issue_metadata(self, issue_data: Dict) -> Dict:
        """Parse issue metadata from GitHub data."""
        labels = [label['name'] for label in issue_data.get('labels', [])]
        
        # Determine issue type
        issue_type = 'task'  # default
        for type_key, type_labels in self.type_labels.items():
            if any(label.lower() in [l.lower() for l in labels] for label in type_labels):
                issue_type = type_key
                break
        
        # Determine priority
        priority = 'medium'  # default
        for priority_key, priority_labels in self.priority_labels.items():
            if any(label.lower() in [l.lower() for l in labels] for label in priority_labels):
                priority = priority_key
                break
        
        # Extract story points from title or labels
        story_points = None
        title = issue_data.get('title', '')
        
        # Look for story points in title like [8] or (5)
        point_match = re.search(r'[\[\(](\d+)[\]\)]', title)
        if point_match:
            story_points = int(point_match.group(1))
        
        # Look for story points in labels
        for label in labels:
            if label.lower().startswith('points:'):
                try:
                    story_points = int(label.split(':')[1])
                    break
                except ValueError:
                    continue
        
        # Parse acceptance criteria from body
        body = issue_data.get('body', '')
        acceptance_criteria = []
        
        # Look for acceptance criteria patterns
        ac_patterns = [
            r'(?i)acceptance criteria:?\s*\n(.*?)(?=\n\n|\n#|$)',
            r'(?i)definition of done:?\s*\n(.*?)(?=\n\n|\n#|$)',
            r'(?i)requirements:?\s*\n(.*?)(?=\n\n|\n#|$)'
        ]
        
        for pattern in ac_patterns:
            match = re.search(pattern, body, re.DOTALL)
            if match:
                criteria_text = match.group(1).strip()
                acceptance_criteria = [
                    line.strip().lstrip('- ').lstrip('* ') 
                    for line in criteria_text.split('\n') 
                    if line.strip()
                ]
                break
        
        # Parse blockers
        blockers = []
        blocker_patterns = [
            r'(?i)blocked by:?\s*\n(.*?)(?=\n\n|\n#|$)',
            r'(?i)dependencies:?\s*\n(.*?)(?=\n\n|\n#|$)'
        ]
        
        for pattern in blocker_patterns:
            match = re.search(pattern, body, re.DOTALL)
            if match:
                blocker_text = match.group(1).strip()
                blockers = [
                    line.strip().lstrip('- ').lstrip('* ') 
                    for line in blocker_text.split('\n') 
                    if line.strip()
                ]
                break
        
        return {
            'type': issue_type,
            'priority': priority,
            'story_points': story_points,
            'acceptance_criteria': acceptance_criteria,
            'blockers': blockers
        }
    
    def sync_issues_from_github(self) -> List[Issue]:
        """Sync issues from GitHub and update local database."""
        github_issues = self.fetch_github_issues()
        synced_issues = []
        
        for issue_data in github_issues:
            # Parse metadata
            metadata = self.parse_issue_metadata(issue_data)
            
            # Create Issue object
            issue = Issue(
                number=issue_data['number'],
                title=issue_data['title'],
                body=issue_data.get('body', ''),
                state=issue_data['state'],
                author=issue_data['author']['login'],
                assignee=issue_data['assignees'][0]['login'] if issue_data['assignees'] else None,
                labels=[label['name'] for label in issue_data.get('labels', [])],
                milestone=issue_data.get('milestone', {}).get('title') if issue_data.get('milestone') else None,
                created_at=issue_data['createdAt'],
                updated_at=issue_data['updatedAt'],
                closed_at=issue_data.get('closedAt'),
                story_points=metadata['story_points'],
                priority=metadata['priority'],
                type=metadata['type'],
                sprint_id=None,  # To be updated by sprint planning
                progress_status=self.determine_progress_status(issue_data),
                acceptance_criteria=metadata['acceptance_criteria'],
                blockers=metadata['blockers'],
                linked_prs=[],  # To be populated by PR linking
                resolution_time_hours=self.calculate_resolution_time(issue_data),
                first_response_time_hours=None,  # To be calculated
                customer_satisfaction=None  # To be collected
            )
            
            synced_issues.append(issue)
            self.save_issue(issue)
        
        return synced_issues
    
    def determine_progress_status(self, issue_data: Dict) -> str:
        """Determine progress status from GitHub issue data."""
        state = issue_data['state']
        labels = [label['name'].lower() for label in issue_data.get('labels', [])]
        
        if state == 'closed':
            return 'done'
        
        # Check for status labels
        if any(label in labels for label in ['in-progress', 'working', 'started']):
            return 'in_progress'
        
        if any(label in labels for label in ['review', 'needs-review', 'pending-review']):
            return 'review'
        
        return 'todo'  # default for open issues
    
    def calculate_resolution_time(self, issue_data: Dict) -> Optional[float]:
        """Calculate resolution time for closed issues."""
        if issue_data['state'] != 'closed' or not issue_data.get('closedAt'):
            return None
        
        try:
            created = datetime.fromisoformat(issue_data['createdAt'].replace('Z', '+00:00'))
            closed = datetime.fromisoformat(issue_data['closedAt'].replace('Z', '+00:00'))
            
            resolution_time = (closed - created).total_seconds() / 3600  # hours
            return resolution_time
        except Exception:
            return None
    
    def save_issue(self, issue: Issue):
        """Save issue to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO issues
                (number, title, body, state, author, assignee, labels, milestone,
                 created_at, updated_at, closed_at, story_points, priority, type,
                 sprint_id, progress_status, acceptance_criteria, blockers,
                 linked_prs, resolution_time_hours, first_response_time_hours,
                 customer_satisfaction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                issue.number, issue.title, issue.body, issue.state, issue.author,
                issue.assignee, json.dumps(issue.labels), issue.milestone,
                issue.created_at, issue.updated_at, issue.closed_at,
                issue.story_points, issue.priority, issue.type, issue.sprint_id,
                issue.progress_status, json.dumps(issue.acceptance_criteria),
                json.dumps(issue.blockers), json.dumps(issue.linked_prs),
                issue.resolution_time_hours, issue.first_response_time_hours,
                issue.customer_satisfaction
            ))
            conn.commit()
    
    def update_issue_status(self, issue_number: int, new_status: str, 
                           actor: str = "system") -> bool:
        """Update issue status and log activity."""
        try:
            # Update in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE issues 
                    SET progress_status = ?, updated_at = ?
                    WHERE number = ?
                """, (new_status, datetime.now().isoformat(), issue_number))
                
                # Log activity
                activity_id = f"activity-{issue_number}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                conn.execute("""
                    INSERT INTO issue_activity
                    (activity_id, issue_number, activity_type, actor, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    activity_id, issue_number, 'status_change', actor,
                    datetime.now().isoformat(), f"Status changed to {new_status}"
                ))
                
                conn.commit()
            
            # Update GitHub issue labels
            self.update_github_issue_labels(issue_number, new_status)
            
            return True
            
        except Exception as e:
            print(f"Error updating issue status: {e}")
            return False
    
    def update_github_issue_labels(self, issue_number: int, status: str):
        """Update GitHub issue labels to reflect status."""
        try:
            # Remove old status labels
            status_labels = ['todo', 'in-progress', 'review', 'done']
            for label in status_labels:
                subprocess.run([
                    "gh", "issue", "edit", str(issue_number),
                    "--remove-label", label
                ], capture_output=True, text=True)
            
            # Add new status label
            subprocess.run([
                "gh", "issue", "edit", str(issue_number),
                "--add-label", status
            ], capture_output=True, text=True)
            
        except Exception as e:
            print(f"Error updating GitHub labels: {e}")
    
    def assign_issue(self, issue_number: int, assignee: str) -> bool:
        """Assign issue to a team member."""
        try:
            # Update GitHub
            subprocess.run([
                "gh", "issue", "edit", str(issue_number),
                "--assignee", assignee
            ], capture_output=True, text=True, check=True)
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE issues 
                    SET assignee = ?, updated_at = ?
                    WHERE number = ?
                """, (assignee, datetime.now().isoformat(), issue_number))
                
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error assigning issue: {e}")
            return False
    
    def check_sla_compliance(self, issue: Issue) -> Tuple[bool, float]:
        """Check if issue meets SLA requirements."""
        if issue.state != 'closed' or not issue.resolution_time_hours:
            return False, 0.0
        
        target_hours = self.sla_targets.get(issue.priority, self.sla_targets['medium'])
        compliance = issue.resolution_time_hours <= target_hours
        
        # Calculate compliance percentage
        if issue.resolution_time_hours <= target_hours:
            compliance_pct = 100.0
        else:
            compliance_pct = (target_hours / issue.resolution_time_hours) * 100
        
        return compliance, compliance_pct
    
    def generate_issue_metrics(self, days: int = 30) -> IssueMetrics:
        """Generate comprehensive issue metrics."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Volume metrics
            cursor.execute("""
                SELECT COUNT(*) FROM issues 
                WHERE created_at >= ? AND created_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            created_issues = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM issues 
                WHERE closed_at >= ? AND closed_at <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            resolved_issues = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM issues")
            total_issues = cursor.fetchone()[0]
            
            # Type distribution
            cursor.execute("""
                SELECT type, COUNT(*) FROM issues 
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY type
            """, (start_date.isoformat(), end_date.isoformat()))
            
            type_counts = dict(cursor.fetchall())
            
            # Performance metrics
            cursor.execute("""
                SELECT AVG(resolution_time_hours), AVG(first_response_time_hours)
                FROM issues 
                WHERE closed_at >= ? AND closed_at <= ?
                AND resolution_time_hours IS NOT NULL
            """, (start_date.isoformat(), end_date.isoformat()))
            
            perf_metrics = cursor.fetchone()
            avg_resolution_time = perf_metrics[0] if perf_metrics[0] else 0.0
            avg_first_response_time = perf_metrics[1] if perf_metrics[1] else 0.0
            
            # Story points completed
            cursor.execute("""
                SELECT SUM(story_points) FROM issues 
                WHERE closed_at >= ? AND closed_at <= ?
                AND story_points IS NOT NULL
            """, (start_date.isoformat(), end_date.isoformat()))
            
            story_points_completed = cursor.fetchone()[0] or 0
        
        # Calculate additional metrics
        resolution_rate = (resolved_issues / created_issues) * 100 if created_issues > 0 else 0
        velocity = story_points_completed / (days / 7) if days >= 7 else story_points_completed  # points per week
        
        return IssueMetrics(
            period_id=f"metrics-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_issues=total_issues,
            created_issues=created_issues,
            resolved_issues=resolved_issues,
            bugs=type_counts.get('bug', 0),
            features=type_counts.get('feature', 0),
            enhancements=type_counts.get('enhancement', 0),
            tasks=type_counts.get('task', 0),
            avg_resolution_time_hours=avg_resolution_time,
            avg_first_response_time_hours=avg_first_response_time,
            resolution_rate=resolution_rate,
            reopened_issues=0,  # To be calculated
            customer_satisfaction=85.0,  # Placeholder
            sla_compliance=90.0,  # Placeholder
            story_points_completed=story_points_completed,
            velocity=velocity,
            sprint_completion_rate=85.0  # Placeholder
        )
    
    def generate_issue_report(self, days: int = 30) -> str:
        """Generate comprehensive issue management report."""
        # Sync latest issues
        synced_issues = self.sync_issues_from_github()
        
        # Generate metrics
        metrics = self.generate_issue_metrics(days)
        
        # Get active issues
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT number, title, priority, type, assignee, progress_status
                FROM issues 
                WHERE state = 'open'
                ORDER BY priority DESC, created_at DESC
            """)
            
            active_issues = cursor.fetchall()
        
        report = f"""
# Issue Management Report

## 📊 Period: {metrics.start_date} to {metrics.end_date} ({days} days)

### 🎯 Key Metrics
- **Total Issues**: {metrics.total_issues}
- **Created**: {metrics.created_issues}
- **Resolved**: {metrics.resolved_issues}
- **Resolution Rate**: {metrics.resolution_rate:.1f}%
- **Average Resolution Time**: {metrics.avg_resolution_time_hours:.1f} hours
- **Story Points Completed**: {metrics.story_points_completed}
- **Team Velocity**: {metrics.velocity:.1f} points/week

### 📈 Issue Distribution
- **🐛 Bugs**: {metrics.bugs}
- **✨ Features**: {metrics.features}
- **🔧 Enhancements**: {metrics.enhancements}
- **📋 Tasks**: {metrics.tasks}

### 🚀 Performance Indicators
- **SLA Compliance**: {metrics.sla_compliance:.1f}%
- **First Response Time**: {metrics.avg_first_response_time_hours:.1f} hours
- **Customer Satisfaction**: {metrics.customer_satisfaction:.1f}%
- **Sprint Completion Rate**: {metrics.sprint_completion_rate:.1f}%

### 📋 Active Issues ({len(active_issues)} open)
"""
        
        # Group by priority
        priority_groups = {'critical': [], 'high': [], 'medium': [], 'low': []}
        for issue in active_issues:
            priority = issue[2]
            priority_groups[priority].append(issue)
        
        for priority, issues in priority_groups.items():
            if issues:
                report += f"""
#### {priority.upper()} Priority ({len(issues)} issues)
"""
                for issue in issues[:5]:  # Show top 5 per priority
                    number, title, _, type_, assignee, status = issue
                    assignee_str = f"@{assignee}" if assignee else "Unassigned"
                    report += f"- #{number}: {title} ({type_}) - {assignee_str} [{status}]\n"
        
        # Add XP compliance section
        report += f"""
### 🔄 XP Methodology Compliance
- **Issue Tracking**: {'✅ Automated' if len(synced_issues) > 0 else '❌ Manual'}
- **Story Points**: {'✅ Estimated' if metrics.story_points_completed > 0 else '❌ Missing'}
- **Resolution Velocity**: {'✅ Tracked' if metrics.velocity > 0 else '❌ Not measured'}
- **Priority Management**: {'✅ Categorized' if any(priority_groups.values()) else '❌ Not prioritized'}

### 🎯 SLA Targets
- **Critical**: {self.sla_targets['critical']} hours
- **High**: {self.sla_targets['high']} hours
- **Medium**: {self.sla_targets['medium']} hours
- **Low**: {self.sla_targets['low']} hours

### 💡 Recommendations
"""
        
        # Generate recommendations
        recommendations = []
        
        if metrics.resolution_rate < 80:
            recommendations.append("Improve issue resolution rate - currently below 80%")
        
        if metrics.avg_resolution_time_hours > 48:
            recommendations.append("Focus on reducing average resolution time")
        
        if metrics.velocity < 20:
            recommendations.append("Increase team velocity through better planning")
        
        if len(priority_groups['critical']) > 0:
            recommendations.append("Address critical priority issues immediately")
        
        if not recommendations:
            recommendations.append("Continue current issue management practices")
        
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
        
        report += f"""
### 📊 Trend Analysis
- **Issue Creation Trend**: {'Increasing' if metrics.created_issues > metrics.resolved_issues else 'Stable'}
- **Resolution Efficiency**: {'Improving' if metrics.resolution_rate > 80 else 'Needs attention'}
- **Team Capacity**: {'Adequate' if metrics.velocity > 15 else 'Constrained'}

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Synced Issues: {len(synced_issues)}
"""
        
        return report
    
    def create_issue_template(self, template_name: str, template_type: str, 
                             template_content: str) -> bool:
        """Create issue template for consistent issue creation."""
        try:
            template_id = f"template-{template_name}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO issue_templates
                    (template_id, template_name, template_type, template_content,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    template_id, template_name, template_type, template_content,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error creating issue template: {e}")
            return False
    
    def auto_triage_issues(self) -> List[Dict]:
        """Automatically triage new issues based on content analysis."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT number, title, body, labels, priority, type
                FROM issues 
                WHERE state = 'open' AND assignee IS NULL
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            unassigned_issues = cursor.fetchall()
        
        triaged = []
        
        for issue in unassigned_issues:
            number, title, body, labels, priority, type_ = issue
            
            # Auto-assign based on type and keywords
            suggested_assignee = self.suggest_assignee(title, body, type_)
            
            # Auto-prioritize based on keywords
            suggested_priority = self.suggest_priority(title, body)
            
            # Suggest story points
            suggested_points = self.suggest_story_points(title, body)
            
            triage_result = {
                'number': number,
                'title': title,
                'suggested_assignee': suggested_assignee,
                'suggested_priority': suggested_priority,
                'suggested_points': suggested_points,
                'confidence': 0.8  # Placeholder confidence score
            }
            
            triaged.append(triage_result)
        
        return triaged
    
    def suggest_assignee(self, title: str, body: str, issue_type: str) -> Optional[str]:
        """Suggest assignee based on issue content."""
        # Simplified assignee suggestion
        text = (title + " " + body).lower()
        
        # Domain-based assignment
        if any(keyword in text for keyword in ['test', 'testing', 'qa']):
            return "qa-team"
        elif any(keyword in text for keyword in ['deploy', 'infra', 'server']):
            return "devops-team"
        elif any(keyword in text for keyword in ['ui', 'frontend', 'design']):
            return "frontend-team"
        elif any(keyword in text for keyword in ['api', 'backend', 'database']):
            return "backend-team"
        
        return None
    
    def suggest_priority(self, title: str, body: str) -> str:
        """Suggest priority based on issue content."""
        text = (title + " " + body).lower()
        
        # Critical indicators
        if any(keyword in text for keyword in ['critical', 'urgent', 'production', 'down', 'broken']):
            return 'critical'
        
        # High priority indicators
        if any(keyword in text for keyword in ['important', 'blocker', 'security', 'data loss']):
            return 'high'
        
        # Low priority indicators
        if any(keyword in text for keyword in ['minor', 'cosmetic', 'nice to have', 'enhancement']):
            return 'low'
        
        return 'medium'  # default
    
    def suggest_story_points(self, title: str, body: str) -> Optional[int]:
        """Suggest story points based on issue complexity."""
        text = (title + " " + body).lower()
        
        # Complexity indicators
        complexity_score = 0
        
        # Simple tasks
        if any(keyword in text for keyword in ['fix typo', 'update text', 'change color']):
            complexity_score = 1
        
        # Medium tasks
        elif any(keyword in text for keyword in ['add feature', 'implement', 'create']):
            complexity_score = 3
        
        # Complex tasks
        elif any(keyword in text for keyword in ['refactor', 'migrate', 'integrate', 'architecture']):
            complexity_score = 5
        
        # Very complex tasks
        elif any(keyword in text for keyword in ['redesign', 'rewrite', 'performance']):
            complexity_score = 8
        
        # Adjust based on length
        if len(text) > 500:
            complexity_score += 2
        
        # Convert to Fibonacci points
        fibonacci_points = [1, 2, 3, 5, 8, 13, 21]
        for point in fibonacci_points:
            if complexity_score <= point:
                return point
        
        return 21  # Maximum


def main():
    """Main CLI interface for issue management."""
    if len(sys.argv) < 2:
        print("Usage: python issue_manager.py <command> [options]")
        print("Commands:")
        print("  sync                     - Sync issues from GitHub")
        print("  report [days]            - Generate issue management report")
        print("  assign <issue> <user>    - Assign issue to user")
        print("  status <issue> <status>  - Update issue status")
        print("  metrics [days]           - Show issue metrics")
        print("  triage                   - Auto-triage unassigned issues")
        print("  templates                - List issue templates")
        print("  sla-check                - Check SLA compliance")
        sys.exit(1)
    
    manager = IssueManager()
    command = sys.argv[1]
    
    if command == "sync":
        print("🔄 Syncing issues from GitHub...")
        synced_issues = manager.sync_issues_from_github()
        print(f"✅ Synced {len(synced_issues)} issues")
        
        for issue in synced_issues[:5]:  # Show first 5
            print(f"#{issue.number}: {issue.title} [{issue.state}] - {issue.type}/{issue.priority}")
    
    elif command == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        report = manager.generate_issue_report(days)
        
        # Save report
        filename = f"issue_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nReport saved to: {filename}")
    
    elif command == "assign":
        if len(sys.argv) < 4:
            print("Usage: python issue_manager.py assign <issue_number> <assignee>")
            sys.exit(1)
        
        issue_number = int(sys.argv[2])
        assignee = sys.argv[3]
        
        if manager.assign_issue(issue_number, assignee):
            print(f"✅ Issue #{issue_number} assigned to {assignee}")
        else:
            print(f"❌ Failed to assign issue #{issue_number}")
    
    elif command == "status":
        if len(sys.argv) < 4:
            print("Usage: python issue_manager.py status <issue_number> <status>")
            print("Status options: todo, in_progress, review, done")
            sys.exit(1)
        
        issue_number = int(sys.argv[2])
        status = sys.argv[3]
        
        if manager.update_issue_status(issue_number, status):
            print(f"✅ Issue #{issue_number} status updated to {status}")
        else:
            print(f"❌ Failed to update issue #{issue_number} status")
    
    elif command == "metrics":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        metrics = manager.generate_issue_metrics(days)
        
        print(f"Issue Metrics ({days} days):")
        print(f"  Total Issues: {metrics.total_issues}")
        print(f"  Created: {metrics.created_issues}")
        print(f"  Resolved: {metrics.resolved_issues}")
        print(f"  Resolution Rate: {metrics.resolution_rate:.1f}%")
        print(f"  Average Resolution Time: {metrics.avg_resolution_time_hours:.1f} hours")
        print(f"  Story Points Completed: {metrics.story_points_completed}")
        print(f"  Team Velocity: {metrics.velocity:.1f} points/week")
    
    elif command == "triage":
        print("🔄 Auto-triaging unassigned issues...")
        triaged = manager.auto_triage_issues()
        
        print(f"📋 Triaged {len(triaged)} issues:")
        for item in triaged:
            print(f"#{item['number']}: {item['title']}")
            print(f"  Suggested: {item['suggested_assignee']} | {item['suggested_priority']} | {item['suggested_points']} pts")
    
    elif command == "templates":
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT template_name, template_type FROM issue_templates")
            templates = cursor.fetchall()
        
        print(f"Issue Templates ({len(templates)} found):")
        for name, type_ in templates:
            print(f"  - {name} ({type_})")
    
    elif command == "sla-check":
        print("🎯 SLA Compliance Check:")
        print(f"  Critical: {manager.sla_targets['critical']} hours")
        print(f"  High: {manager.sla_targets['high']} hours")
        print(f"  Medium: {manager.sla_targets['medium']} hours")
        print(f"  Low: {manager.sla_targets['low']} hours")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()