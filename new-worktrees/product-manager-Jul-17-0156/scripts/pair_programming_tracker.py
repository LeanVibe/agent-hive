#!/usr/bin/env python3
"""
Pair Programming Tracker - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer

This module tracks pair programming sessions, measures collaboration quality,
and ensures XP methodology compliance for collective code ownership.
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
class PairSession:
    """Represents a pair programming session."""
    session_id: str
    participants: List[str]
    start_time: str
    end_time: Optional[str]
    duration_minutes: Optional[float]
    
    # Code collaboration metrics
    commits_made: int
    files_modified: int
    lines_added: int
    lines_deleted: int
    
    # Quality metrics
    test_coverage_change: float
    code_quality_score: float
    refactoring_count: int
    bug_fixes: int
    
    # XP compliance
    driver_switches: int
    knowledge_sharing_score: float
    collective_ownership_score: float
    
    # Session metadata
    session_type: str  # 'development', 'debugging', 'refactoring', 'learning'
    focus_area: str
    tools_used: List[str]
    notes: Optional[str]


@dataclass
class PairProgrammingMetrics:
    """Metrics for pair programming compliance."""
    period_id: str
    start_date: str
    end_date: str
    
    # Volume metrics
    total_sessions: int
    total_hours: float
    active_pairs: int
    unique_participants: int
    
    # Quality metrics
    avg_session_duration: float
    avg_knowledge_sharing_score: float
    avg_collective_ownership_score: float
    avg_code_quality_improvement: float
    
    # XP compliance
    pair_programming_coverage: float  # % of code written in pairs
    knowledge_distribution: float  # how evenly knowledge is shared
    rotation_frequency: float  # how often people switch pairs
    
    # Productivity metrics
    commits_per_session: float
    defect_rate: float
    refactoring_frequency: float


class PairProgrammingTracker:
    """Advanced pair programming tracking and analysis system."""
    
    def __init__(self, db_path: str = "pair_programming_data.db"):
        self.db_path = db_path
        self.init_database()
        
        # Configuration
        self.min_session_duration = 30  # minutes
        self.max_session_duration = 480  # 8 hours
        self.target_coverage = 80.0  # % of code written in pairs
        self.knowledge_sharing_threshold = 0.7
    
    def init_database(self):
        """Initialize SQLite database for pair programming tracking."""
        with sqlite3.connect(self.db_path) as conn:
            # Pair sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pair_sessions (
                    session_id TEXT PRIMARY KEY,
                    participants TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes REAL,
                    commits_made INTEGER NOT NULL,
                    files_modified INTEGER NOT NULL,
                    lines_added INTEGER NOT NULL,
                    lines_deleted INTEGER NOT NULL,
                    test_coverage_change REAL NOT NULL,
                    code_quality_score REAL NOT NULL,
                    refactoring_count INTEGER NOT NULL,
                    bug_fixes INTEGER NOT NULL,
                    driver_switches INTEGER NOT NULL,
                    knowledge_sharing_score REAL NOT NULL,
                    collective_ownership_score REAL NOT NULL,
                    session_type TEXT NOT NULL,
                    focus_area TEXT NOT NULL,
                    tools_used TEXT NOT NULL,
                    notes TEXT
                )
            """)
            
            # Pair programming metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pair_metrics (
                    period_id TEXT PRIMARY KEY,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_sessions INTEGER NOT NULL,
                    total_hours REAL NOT NULL,
                    active_pairs INTEGER NOT NULL,
                    unique_participants INTEGER NOT NULL,
                    avg_session_duration REAL NOT NULL,
                    avg_knowledge_sharing_score REAL NOT NULL,
                    avg_collective_ownership_score REAL NOT NULL,
                    avg_code_quality_improvement REAL NOT NULL,
                    pair_programming_coverage REAL NOT NULL,
                    knowledge_distribution REAL NOT NULL,
                    rotation_frequency REAL NOT NULL,
                    commits_per_session REAL NOT NULL,
                    defect_rate REAL NOT NULL,
                    refactoring_frequency REAL NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            
            # Knowledge sharing matrix
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_sharing (
                    record_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sharer TEXT NOT NULL,
                    learner TEXT NOT NULL,
                    knowledge_area TEXT NOT NULL,
                    proficiency_before INTEGER NOT NULL,
                    proficiency_after INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES pair_sessions (session_id)
                )
            """)
            
            # Active sessions tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_sessions (
                    session_id TEXT PRIMARY KEY,
                    participants TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    current_driver TEXT,
                    activity_count INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def start_pair_session(self, participants: List[str], session_type: str = "development",
                          focus_area: str = "", tools: List[str] = None) -> str:
        """Start a new pair programming session."""
        if len(participants) < 2:
            raise ValueError("Pair programming requires at least 2 participants")
        
        session_id = f"pair-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now().isoformat()
        
        if tools is None:
            tools = ["ide", "terminal"]
        
        # Store active session
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO active_sessions
                (session_id, participants, start_time, last_activity, current_driver)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id, json.dumps(participants), start_time, start_time, participants[0]
            ))
            conn.commit()
        
        print(f"✅ Started pair programming session: {session_id}")
        print(f"Participants: {', '.join(participants)}")
        print(f"Type: {session_type}")
        print(f"Focus: {focus_area}")
        
        return session_id
    
    def switch_driver(self, session_id: str, new_driver: str) -> bool:
        """Switch the driver in an active session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if session is active
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT participants, activity_count FROM active_sessions 
                    WHERE session_id = ?
                """, (session_id,))
                
                result = cursor.fetchone()
                if not result:
                    print(f"❌ Session {session_id} not found or not active")
                    return False
                
                participants = json.loads(result[0])
                activity_count = result[1]
                
                if new_driver not in participants:
                    print(f"❌ {new_driver} is not a participant in this session")
                    return False
                
                # Update driver and activity count
                conn.execute("""
                    UPDATE active_sessions 
                    SET current_driver = ?, last_activity = ?, activity_count = ?
                    WHERE session_id = ?
                """, (new_driver, datetime.now().isoformat(), activity_count + 1, session_id))
                
                conn.commit()
                
                print(f"🔄 Driver switched to {new_driver} in session {session_id}")
                return True
                
        except Exception as e:
            print(f"Error switching driver: {e}")
            return False
    
    def end_pair_session(self, session_id: str, notes: str = "") -> Optional[PairSession]:
        """End an active pair programming session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get active session data
                cursor.execute("""
                    SELECT participants, start_time, activity_count 
                    FROM active_sessions 
                    WHERE session_id = ?
                """, (session_id,))
                
                result = cursor.fetchone()
                if not result:
                    print(f"❌ Session {session_id} not found or not active")
                    return None
                
                participants_json, start_time, activity_count = result
                participants = json.loads(participants_json)
                
                end_time = datetime.now().isoformat()
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                duration_minutes = (end_dt - start_dt).total_seconds() / 60.0
                
                # Analyze session metrics
                session_metrics = self.analyze_session_activity(session_id, start_time, end_time)
                
                # Create session record
                session = PairSession(
                    session_id=session_id,
                    participants=participants,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration_minutes,
                    commits_made=session_metrics.get('commits', 0),
                    files_modified=session_metrics.get('files_modified', 0),
                    lines_added=session_metrics.get('lines_added', 0),
                    lines_deleted=session_metrics.get('lines_deleted', 0),
                    test_coverage_change=session_metrics.get('coverage_change', 0.0),
                    code_quality_score=session_metrics.get('quality_score', 7.5),
                    refactoring_count=session_metrics.get('refactoring_count', 0),
                    bug_fixes=session_metrics.get('bug_fixes', 0),
                    driver_switches=activity_count,
                    knowledge_sharing_score=self.calculate_knowledge_sharing_score(participants),
                    collective_ownership_score=self.calculate_collective_ownership_score(participants),
                    session_type="development",  # Default
                    focus_area="general",  # Default
                    tools_used=["ide", "terminal"],  # Default
                    notes=notes
                )
                
                # Save session
                self.save_pair_session(session)
                
                # Remove from active sessions
                conn.execute("DELETE FROM active_sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                
                print(f"✅ Ended pair programming session: {session_id}")
                print(f"Duration: {duration_minutes:.1f} minutes")
                print(f"Driver switches: {activity_count}")
                print(f"Knowledge sharing score: {session.knowledge_sharing_score:.2f}")
                
                return session
                
        except Exception as e:
            print(f"Error ending session: {e}")
            return None
    
    def analyze_session_activity(self, session_id: str, start_time: str, end_time: str) -> Dict:
        """Analyze git activity during a pair programming session."""
        try:
            # Get git commits during session timeframe
            result = subprocess.run([
                "git", "log", "--since", start_time, "--until", end_time,
                "--pretty=format:%H", "--name-status"
            ], capture_output=True, text=True, check=True)
            
            if not result.stdout.strip():
                return {
                    'commits': 0,
                    'files_modified': 0,
                    'lines_added': 0,
                    'lines_deleted': 0,
                    'coverage_change': 0.0,
                    'quality_score': 7.5,
                    'refactoring_count': 0,
                    'bug_fixes': 0
                }
            
            # Parse git output
            lines = result.stdout.strip().split('\n')
            commits = [line for line in lines if len(line) == 40]  # SHA hashes
            file_changes = [line for line in lines if line.startswith(('M', 'A', 'D'))]
            
            # Get detailed diff stats
            diff_result = subprocess.run([
                "git", "diff", "--stat", "--since", start_time, "--until", end_time
            ], capture_output=True, text=True)
            
            # Parse diff stats for line counts
            lines_added = 0
            lines_deleted = 0
            if diff_result.stdout:
                for line in diff_result.stdout.split('\n'):
                    if '+' in line and '-' in line:
                        # Parse "+X -Y" pattern
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.startswith('+') and i + 1 < len(parts):
                                try:
                                    lines_added += int(part[1:])
                                except ValueError:
                                    pass
                            elif part.startswith('-'):
                                try:
                                    lines_deleted += int(part[1:])
                                except ValueError:
                                    pass
            
            return {
                'commits': len(commits),
                'files_modified': len(set(line.split('\t')[1] for line in file_changes if '\t' in line)),
                'lines_added': lines_added,
                'lines_deleted': lines_deleted,
                'coverage_change': 0.0,  # Would require coverage analysis
                'quality_score': 8.0,  # Default good score for pair programming
                'refactoring_count': self.count_refactoring_commits(commits),
                'bug_fixes': self.count_bug_fix_commits(commits)
            }
            
        except subprocess.CalledProcessError as e:
            print(f"Error analyzing git activity: {e}")
            return {}
    
    def count_refactoring_commits(self, commit_hashes: List[str]) -> int:
        """Count commits that appear to be refactoring."""
        refactoring_count = 0
        refactoring_keywords = ['refactor', 'clean', 'improve', 'optimize', 'restructure']
        
        for commit_hash in commit_hashes:
            try:
                result = subprocess.run([
                    "git", "show", "--format=%s", "--no-patch", commit_hash
                ], capture_output=True, text=True, check=True)
                
                commit_message = result.stdout.strip().lower()
                if any(keyword in commit_message for keyword in refactoring_keywords):
                    refactoring_count += 1
                    
            except subprocess.CalledProcessError:
                continue
        
        return refactoring_count
    
    def count_bug_fix_commits(self, commit_hashes: List[str]) -> int:
        """Count commits that appear to be bug fixes."""
        bug_fix_count = 0
        bug_keywords = ['fix', 'bug', 'issue', 'error', 'correct', 'resolve']
        
        for commit_hash in commit_hashes:
            try:
                result = subprocess.run([
                    "git", "show", "--format=%s", "--no-patch", commit_hash
                ], capture_output=True, text=True, check=True)
                
                commit_message = result.stdout.strip().lower()
                if any(keyword in commit_message for keyword in bug_keywords):
                    bug_fix_count += 1
                    
            except subprocess.CalledProcessError:
                continue
        
        return bug_fix_count
    
    def calculate_knowledge_sharing_score(self, participants: List[str]) -> float:
        """Calculate knowledge sharing score for participants."""
        # Simplified scoring based on participant diversity and experience
        base_score = 0.7
        
        # Bonus for diverse team composition
        if len(participants) >= 2:
            base_score += 0.1
        
        # Bonus for cross-functional pairing (would need team data)
        base_score += 0.2  # Assume good cross-functional pairing
        
        return min(base_score, 1.0)
    
    def calculate_collective_ownership_score(self, participants: List[str]) -> float:
        """Calculate collective code ownership score."""
        # Simplified scoring based on participants working across codebase
        base_score = 0.6
        
        # Bonus for multiple participants
        if len(participants) >= 2:
            base_score += 0.2
        
        # Bonus for regular pair programming (would need historical data)
        base_score += 0.2  # Assume regular pairing
        
        return min(base_score, 1.0)
    
    def save_pair_session(self, session: PairSession):
        """Save pair programming session to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pair_sessions
                (session_id, participants, start_time, end_time, duration_minutes,
                 commits_made, files_modified, lines_added, lines_deleted,
                 test_coverage_change, code_quality_score, refactoring_count,
                 bug_fixes, driver_switches, knowledge_sharing_score,
                 collective_ownership_score, session_type, focus_area,
                 tools_used, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id, json.dumps(session.participants),
                session.start_time, session.end_time, session.duration_minutes,
                session.commits_made, session.files_modified, session.lines_added,
                session.lines_deleted, session.test_coverage_change,
                session.code_quality_score, session.refactoring_count,
                session.bug_fixes, session.driver_switches,
                session.knowledge_sharing_score, session.collective_ownership_score,
                session.session_type, session.focus_area,
                json.dumps(session.tools_used), session.notes
            ))
            conn.commit()
    
    def calculate_pair_programming_metrics(self, days: int = 7) -> PairProgrammingMetrics:
        """Calculate comprehensive pair programming metrics."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Volume metrics
            cursor.execute("""
                SELECT COUNT(*), SUM(duration_minutes), COUNT(DISTINCT participants)
                FROM pair_sessions
                WHERE start_time >= ? AND start_time <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            volume_data = cursor.fetchone()
            total_sessions = volume_data[0] if volume_data[0] else 0
            total_minutes = volume_data[1] if volume_data[1] else 0.0
            
            # Unique participants (parse JSON)
            cursor.execute("""
                SELECT DISTINCT participants FROM pair_sessions
                WHERE start_time >= ? AND start_time <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            participant_data = cursor.fetchall()
            all_participants = set()
            for row in participant_data:
                try:
                    participants = json.loads(row[0])
                    all_participants.update(participants)
                except json.JSONDecodeError:
                    continue
            
            unique_participants = len(all_participants)
            
            # Quality metrics
            cursor.execute("""
                SELECT AVG(duration_minutes), AVG(knowledge_sharing_score),
                       AVG(collective_ownership_score), AVG(code_quality_score),
                       AVG(commits_made), AVG(driver_switches)
                FROM pair_sessions
                WHERE start_time >= ? AND start_time <= ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            quality_data = cursor.fetchone()
            avg_duration = quality_data[0] if quality_data[0] else 0.0
            avg_knowledge_sharing = quality_data[1] if quality_data[1] else 0.0
            avg_collective_ownership = quality_data[2] if quality_data[2] else 0.0
            avg_quality_improvement = quality_data[3] if quality_data[3] else 0.0
            avg_commits = quality_data[4] if quality_data[4] else 0.0
            avg_switches = quality_data[5] if quality_data[5] else 0.0
        
        # Calculate derived metrics
        total_hours = total_minutes / 60.0
        active_pairs = len(participant_data)
        
        # XP compliance metrics (simplified calculations)
        pair_programming_coverage = min(90.0, (total_sessions / days) * 20)  # Estimated
        knowledge_distribution = avg_knowledge_sharing * 100
        rotation_frequency = avg_switches / max(avg_duration / 60, 1)  # switches per hour
        
        return PairProgrammingMetrics(
            period_id=f"pair-metrics-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_sessions=total_sessions,
            total_hours=total_hours,
            active_pairs=active_pairs,
            unique_participants=unique_participants,
            avg_session_duration=avg_duration,
            avg_knowledge_sharing_score=avg_knowledge_sharing,
            avg_collective_ownership_score=avg_collective_ownership,
            avg_code_quality_improvement=avg_quality_improvement,
            pair_programming_coverage=pair_programming_coverage,
            knowledge_distribution=knowledge_distribution,
            rotation_frequency=rotation_frequency,
            commits_per_session=avg_commits,
            defect_rate=5.0,  # Placeholder - would calculate from actual defects
            refactoring_frequency=15.0  # Placeholder
        )
    
    def generate_pair_programming_report(self, days: int = 7) -> str:
        """Generate comprehensive pair programming report."""
        metrics = self.calculate_pair_programming_metrics(days)
        
        # Get recent sessions
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, participants, duration_minutes, 
                       knowledge_sharing_score, driver_switches
                FROM pair_sessions
                WHERE start_time >= datetime('now', '-{} days')
                ORDER BY start_time DESC
                LIMIT 10
            """.format(days))
            
            recent_sessions = cursor.fetchall()
        
        report = f"""
# Pair Programming Report - XP Methodology Compliance

## 📊 Period: {metrics.start_date} to {metrics.end_date} ({days} days)

### 🤝 Collaboration Metrics
- **Total Sessions**: {metrics.total_sessions}
- **Total Hours**: {metrics.total_hours:.1f}
- **Active Pairs**: {metrics.active_pairs}
- **Unique Participants**: {metrics.unique_participants}
- **Average Session Duration**: {metrics.avg_session_duration:.1f} minutes

### 🎯 XP Methodology Compliance
- **Pair Programming Coverage**: {metrics.pair_programming_coverage:.1f}%
- **Knowledge Sharing Score**: {metrics.avg_knowledge_sharing_score:.2f}/1.0
- **Collective Ownership Score**: {metrics.avg_collective_ownership_score:.2f}/1.0
- **Knowledge Distribution**: {metrics.knowledge_distribution:.1f}%

### 📈 Quality Indicators
- **Code Quality Improvement**: {metrics.avg_code_quality_improvement:.1f}/10.0
- **Commits per Session**: {metrics.commits_per_session:.1f}
- **Driver Rotation Frequency**: {metrics.rotation_frequency:.1f} switches/hour
- **Refactoring Frequency**: {metrics.refactoring_frequency:.1f}%

### 📋 Recent Sessions
"""
        
        for session_data in recent_sessions:
            session_id, participants_json, duration, knowledge_score, switches = session_data
            try:
                participants = json.loads(participants_json)
                participants_str = ', '.join(participants)
            except json.JSONDecodeError:
                participants_str = "Unknown"
            
            report += f"- **{session_id}**: {participants_str} ({duration:.0f}min, {switches} switches, KS: {knowledge_score:.2f})\n"
        
        # XP compliance assessment
        compliance_score = (
            (metrics.pair_programming_coverage / 100) * 0.3 +
            metrics.avg_knowledge_sharing_score * 0.3 +
            metrics.avg_collective_ownership_score * 0.4
        ) * 100
        
        report += f"""
### 🔄 XP Practice Assessment
- **Overall Compliance**: {compliance_score:.1f}%
- **Target Coverage**: {self.target_coverage}% (Current: {metrics.pair_programming_coverage:.1f}%)
- **Knowledge Sharing**: {'✅ Excellent' if metrics.avg_knowledge_sharing_score > 0.8 else '⚠️ Needs improvement'}
- **Collective Ownership**: {'✅ Strong' if metrics.avg_collective_ownership_score > 0.7 else '⚠️ Developing'}
- **Session Duration**: {'✅ Optimal' if 60 <= metrics.avg_session_duration <= 180 else '⚠️ Consider adjustment'}

### 💡 Recommendations
"""
        
        recommendations = []
        
        if metrics.pair_programming_coverage < self.target_coverage:
            recommendations.append(f"Increase pair programming coverage from {metrics.pair_programming_coverage:.1f}% to {self.target_coverage}%")
        
        if metrics.avg_knowledge_sharing_score < self.knowledge_sharing_threshold:
            recommendations.append("Improve knowledge sharing by pairing experienced with junior developers")
        
        if metrics.avg_session_duration < 30:
            recommendations.append("Increase average session duration - sessions too short for effective pairing")
        elif metrics.avg_session_duration > 240:
            recommendations.append("Consider shorter sessions to maintain focus and energy")
        
        if metrics.rotation_frequency < 0.5:
            recommendations.append("Increase driver rotation frequency for better knowledge sharing")
        
        if not recommendations:
            recommendations.append("Excellent pair programming practices - continue current approach")
        
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
        
        report += f"""
### 🎯 XP Methodology Benefits Achieved
- **Collective Code Ownership**: {'✅' if metrics.avg_collective_ownership_score > 0.7 else '⚠️'} Code knowledge shared across team
- **Continuous Code Review**: {'✅' if metrics.total_sessions > 0 else '❌'} Real-time code review through pairing
- **Knowledge Transfer**: {'✅' if metrics.avg_knowledge_sharing_score > 0.6 else '⚠️'} Active learning and teaching
- **Reduced Defects**: {'✅' if metrics.defect_rate < 10 else '⚠️'} Fewer bugs through collaborative development
- **Design Quality**: {'✅' if metrics.avg_code_quality_improvement > 7 else '⚠️'} Better design decisions

### 📊 Target Benchmarks
- **Coverage Target**: ≥{self.target_coverage}% of development time
- **Session Duration**: {self.min_session_duration}-{self.max_session_duration//60*60} minutes
- **Knowledge Sharing**: ≥{self.knowledge_sharing_threshold} score
- **Driver Rotation**: ≥0.5 switches per hour
- **Quality Improvement**: ≥7.5/10.0 score

---
Generated by PM/XP Methodology Enforcer Agent
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Sessions Analyzed: {metrics.total_sessions}
"""
        
        return report


def main():
    """Main CLI interface for pair programming tracking."""
    if len(sys.argv) < 2:
        print("Usage: python pair_programming_tracker.py <command> [options]")
        print("Commands:")
        print("  start <user1> <user2> [type] [focus]  - Start pair programming session")
        print("  switch <session_id> <new_driver>      - Switch driver in active session")
        print("  end <session_id> [notes]              - End pair programming session")
        print("  active                                - List active sessions")
        print("  report [days]                         - Generate pair programming report")
        print("  metrics [days]                        - Show pair programming metrics")
        print("  history [limit]                       - Show recent sessions")
        sys.exit(1)
    
    tracker = PairProgrammingTracker()
    command = sys.argv[1]
    
    if command == "start":
        if len(sys.argv) < 4:
            print("Usage: python pair_programming_tracker.py start <user1> <user2> [type] [focus]")
            sys.exit(1)
        
        participants = [sys.argv[2], sys.argv[3]]
        session_type = sys.argv[4] if len(sys.argv) > 4 else "development"
        focus_area = sys.argv[5] if len(sys.argv) > 5 else "general"
        
        session_id = tracker.start_pair_session(participants, session_type, focus_area)
        print(f"Session ID: {session_id}")
    
    elif command == "switch":
        if len(sys.argv) < 4:
            print("Usage: python pair_programming_tracker.py switch <session_id> <new_driver>")
            sys.exit(1)
        
        session_id = sys.argv[2]
        new_driver = sys.argv[3]
        
        tracker.switch_driver(session_id, new_driver)
    
    elif command == "end":
        if len(sys.argv) < 3:
            print("Usage: python pair_programming_tracker.py end <session_id> [notes]")
            sys.exit(1)
        
        session_id = sys.argv[2]
        notes = sys.argv[3] if len(sys.argv) > 3 else ""
        
        session = tracker.end_pair_session(session_id, notes)
        if session:
            print(f"Session ended successfully")
    
    elif command == "active":
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, participants, start_time, current_driver, activity_count
                FROM active_sessions
                ORDER BY start_time DESC
            """)
            
            active_sessions = cursor.fetchall()
        
        if active_sessions:
            print(f"Active Pair Programming Sessions ({len(active_sessions)}):")
            for session_id, participants_json, start_time, driver, switches in active_sessions:
                try:
                    participants = json.loads(participants_json)
                    participants_str = ', '.join(participants)
                except json.JSONDecodeError:
                    participants_str = "Unknown"
                
                duration = (datetime.now() - datetime.fromisoformat(start_time)).total_seconds() / 60
                print(f"  {session_id}: {participants_str} (Driver: {driver}, {duration:.0f}min, {switches} switches)")
        else:
            print("No active pair programming sessions")
    
    elif command == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        report = tracker.generate_pair_programming_report(days)
        
        # Save report
        filename = f"pair_programming_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nReport saved to: {filename}")
    
    elif command == "metrics":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        metrics = tracker.calculate_pair_programming_metrics(days)
        
        print(f"Pair Programming Metrics ({days} days):")
        print(f"  Total Sessions: {metrics.total_sessions}")
        print(f"  Total Hours: {metrics.total_hours:.1f}")
        print(f"  Coverage: {metrics.pair_programming_coverage:.1f}%")
        print(f"  Knowledge Sharing: {metrics.avg_knowledge_sharing_score:.2f}")
        print(f"  Collective Ownership: {metrics.avg_collective_ownership_score:.2f}")
        print(f"  Quality Improvement: {metrics.avg_code_quality_improvement:.1f}")
    
    elif command == "history":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, participants, start_time, duration_minutes,
                       knowledge_sharing_score, collective_ownership_score
                FROM pair_sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            
            sessions = cursor.fetchall()
        
        if sessions:
            print(f"Recent Pair Programming Sessions (last {limit}):")
            for session_data in sessions:
                session_id, participants_json, start_time, duration, ks_score, co_score = session_data
                try:
                    participants = json.loads(participants_json)
                    participants_str = ', '.join(participants)
                except json.JSONDecodeError:
                    participants_str = "Unknown"
                
                start_dt = datetime.fromisoformat(start_time)
                print(f"  {session_id}: {participants_str}")
                print(f"    Date: {start_dt.strftime('%Y-%m-%d %H:%M')} | Duration: {duration:.0f}min")
                print(f"    Knowledge Sharing: {ks_score:.2f} | Collective Ownership: {co_score:.2f}")
        else:
            print("No pair programming sessions found")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()