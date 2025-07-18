#!/usr/bin/env python3
"""
Agent Accountability System

Comprehensive monitoring, tracking, and escalation system for agent coordination.
Prevents silent work and ensures continuous accountability with evidence validation.
"""

import asyncio
import json
import time
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REASSIGNED = "reassigned"


class EscalationLevel(Enum):
    """Escalation severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SYSTEM_FAILURE = "system_failure"


@dataclass
class AgentTask:
    """Agent task tracking."""
    task_id: str
    agent_id: str
    title: str
    description: str
    assigned_at: datetime
    deadline: datetime
    priority: float
    status: TaskStatus
    progress_percentage: int = 0
    last_update: Optional[datetime] = None
    evidence_hash: Optional[str] = None
    escalation_count: int = 0
    reassignment_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProgressReport:
    """Progress report structure."""
    report_id: str
    agent_id: str
    task_id: str
    timestamp: datetime
    progress_percentage: int
    status_summary: str
    evidence_files: List[str]
    blockers: List[str]
    eta_minutes: Optional[int]
    confidence_level: int  # 1-100
    evidence_hash: str
    is_valid: bool = True


@dataclass
class EscalationEvent:
    """Escalation event tracking."""
    escalation_id: str
    agent_id: str
    task_id: str
    timestamp: datetime
    level: EscalationLevel
    reason: str
    action_taken: str
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class AccountabilitySystem:
    """
    Comprehensive agent accountability and monitoring system.
    
    Features:
    - Real-time task tracking and progress monitoring
    - Evidence validation and integrity checking
    - Automatic timeout detection and escalation
    - Task reassignment protocols
    - Comprehensive audit trails
    """
    
    def __init__(self, db_path: str = ".claude/accountability.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = {
            "check_interval_seconds": 60,  # Check every minute
            "progress_timeout_minutes": 30,  # No progress for 30 min = escalation
            "response_timeout_minutes": 5,  # No response to ping for 5 min = escalation
            "completion_timeout_multiplier": 1.5,  # 50% over ETA = escalation
            "max_reassignments": 2,  # Maximum reassignments before human intervention
            "evidence_validation_required": True,
            "auto_escalation_enabled": True
        }
        
        # Initialize database
        self._init_database()
        
        # Active monitoring
        self.active_tasks: Dict[str, AgentTask] = {}
        self.progress_reports: Dict[str, List[ProgressReport]] = {}
        self.escalations: Dict[str, List[EscalationEvent]] = {}
        self.agent_heartbeats: Dict[str, datetime] = {}
        
        # Load existing data
        self._load_from_database()
        
        logger.info("AccountabilitySystem initialized")
    
    def _init_database(self):
        """Initialize SQLite database for persistence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    assigned_at TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    priority REAL NOT NULL,
                    status TEXT NOT NULL,
                    progress_percentage INTEGER DEFAULT 0,
                    last_update TEXT,
                    evidence_hash TEXT,
                    escalation_count INTEGER DEFAULT 0,
                    reassignment_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS progress_reports (
                    report_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    progress_percentage INTEGER NOT NULL,
                    status_summary TEXT NOT NULL,
                    evidence_files TEXT,
                    blockers TEXT,
                    eta_minutes INTEGER,
                    confidence_level INTEGER NOT NULL,
                    evidence_hash TEXT NOT NULL,
                    is_valid BOOLEAN DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS escalations (
                    escalation_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    action_taken TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT 0,
                    resolution_time TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_heartbeats (
                    agent_id TEXT PRIMARY KEY,
                    last_heartbeat TEXT NOT NULL,
                    status TEXT,
                    current_task TEXT
                )
            """)
    
    def _load_from_database(self):
        """Load existing data from database."""
        with sqlite3.connect(self.db_path) as conn:
            # Load tasks
            cursor = conn.execute("SELECT * FROM tasks")
            for row in cursor.fetchall():
                task = AgentTask(
                    task_id=row[0],
                    agent_id=row[1],
                    title=row[2],
                    description=row[3],
                    assigned_at=datetime.fromisoformat(row[4]),
                    deadline=datetime.fromisoformat(row[5]),
                    priority=row[6],
                    status=TaskStatus(row[7]),
                    progress_percentage=row[8],
                    last_update=datetime.fromisoformat(row[9]) if row[9] else None,
                    evidence_hash=row[10],
                    escalation_count=row[11],
                    reassignment_count=row[12],
                    metadata=json.loads(row[13]) if row[13] else {}
                )
                self.active_tasks[task.task_id] = task
            
            # Load heartbeats
            cursor = conn.execute("SELECT * FROM agent_heartbeats")
            for row in cursor.fetchall():
                self.agent_heartbeats[row[0]] = datetime.fromisoformat(row[1])
    
    def assign_task(self, agent_id: str, title: str, description: str,
                   deadline_hours: int, priority: float = 1.0) -> str:
        """Assign a new task to an agent."""
        task_id = f"task_{int(time.time())}_{agent_id}"
        assigned_at = datetime.now()
        deadline = assigned_at + timedelta(hours=deadline_hours)
        
        task = AgentTask(
            task_id=task_id,
            agent_id=agent_id,
            title=title,
            description=description,
            assigned_at=assigned_at,
            deadline=deadline,
            priority=priority,
            status=TaskStatus.ASSIGNED
        )
        
        self.active_tasks[task_id] = task
        self._save_task_to_db(task)
        
        logger.info(f"Task {task_id} assigned to agent {agent_id}")
        return task_id
    
    def update_task_progress(self, agent_id: str, task_id: str, 
                           progress_percentage: int, status_summary: str,
                           evidence_files: List[str] = None, 
                           blockers: List[str] = None,
                           eta_minutes: int = None,
                           confidence_level: int = 100) -> bool:
        """Update task progress with evidence validation."""
        if task_id not in self.active_tasks:
            logger.error(f"Task {task_id} not found")
            return False
        
        task = self.active_tasks[task_id]
        if task.agent_id != agent_id:
            logger.error(f"Agent {agent_id} not authorized for task {task_id}")
            return False
        
        # Generate evidence hash
        evidence_data = {
            "files": evidence_files or [],
            "progress": progress_percentage,
            "summary": status_summary,
            "timestamp": datetime.now().isoformat()
        }
        evidence_hash = hashlib.sha256(
            json.dumps(evidence_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Create progress report
        report = ProgressReport(
            report_id=f"report_{int(time.time())}_{agent_id}",
            agent_id=agent_id,
            task_id=task_id,
            timestamp=datetime.now(),
            progress_percentage=progress_percentage,
            status_summary=status_summary,
            evidence_files=evidence_files or [],
            blockers=blockers or [],
            eta_minutes=eta_minutes,
            confidence_level=confidence_level,
            evidence_hash=evidence_hash
        )
        
        # Validate evidence if required
        if self.config["evidence_validation_required"]:
            report.is_valid = self._validate_evidence(report)
        
        # Update task
        task.progress_percentage = progress_percentage
        task.last_update = datetime.now()
        task.evidence_hash = evidence_hash
        
        if progress_percentage >= 100:
            task.status = TaskStatus.COMPLETED
        elif blockers:
            task.status = TaskStatus.BLOCKED
        else:
            task.status = TaskStatus.IN_PROGRESS
        
        # Store report
        if task_id not in self.progress_reports:
            self.progress_reports[task_id] = []
        self.progress_reports[task_id].append(report)
        
        # Save to database
        self._save_task_to_db(task)
        self._save_progress_report_to_db(report)
        
        # Update heartbeat
        self.agent_heartbeats[agent_id] = datetime.now()
        self._save_heartbeat_to_db(agent_id)
        
        logger.info(f"Progress updated for task {task_id}: {progress_percentage}%")
        return True
    
    def _validate_evidence(self, report: ProgressReport) -> bool:
        """Validate evidence files and data integrity."""
        try:
            # Check if evidence files exist
            for file_path in report.evidence_files:
                if not Path(file_path).exists():
                    logger.warning(f"Evidence file not found: {file_path}")
                    return False
            
            # Validate progress consistency
            if report.progress_percentage < 0 or report.progress_percentage > 100:
                logger.warning(f"Invalid progress percentage: {report.progress_percentage}")
                return False
            
            # Check confidence level
            if report.confidence_level < 1 or report.confidence_level > 100:
                logger.warning(f"Invalid confidence level: {report.confidence_level}")
                return False
            
            # Validate summary content
            if len(report.status_summary.strip()) < 10:
                logger.warning(f"Status summary too brief: {report.status_summary}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Evidence validation failed: {e}")
            return False
    
    def check_timeouts_and_escalate(self) -> List[EscalationEvent]:
        """Check for timeouts and create escalations."""
        escalations = []
        current_time = datetime.now()
        
        for task_id, task in self.active_tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                continue
            
            # Check progress timeout
            if task.last_update:
                time_since_update = current_time - task.last_update
                if time_since_update.total_seconds() > (self.config["progress_timeout_minutes"] * 60):
                    escalation = self._create_escalation(
                        task.agent_id, task_id, EscalationLevel.HIGH,
                        f"No progress update for {time_since_update.total_seconds()/60:.1f} minutes",
                        "TIMEOUT_ESCALATION"
                    )
                    escalations.append(escalation)
            
            # Check deadline timeout
            if current_time > task.deadline:
                overtime_hours = (current_time - task.deadline).total_seconds() / 3600
                escalation = self._create_escalation(
                    task.agent_id, task_id, EscalationLevel.CRITICAL,
                    f"Task overdue by {overtime_hours:.1f} hours",
                    "DEADLINE_ESCALATION"
                )
                escalations.append(escalation)
            
            # Check agent heartbeat
            if task.agent_id in self.agent_heartbeats:
                last_heartbeat = self.agent_heartbeats[task.agent_id]
                time_since_heartbeat = current_time - last_heartbeat
                if time_since_heartbeat.total_seconds() > (self.config["response_timeout_minutes"] * 60):
                    escalation = self._create_escalation(
                        task.agent_id, task_id, EscalationLevel.MEDIUM,
                        f"No heartbeat for {time_since_heartbeat.total_seconds()/60:.1f} minutes",
                        "HEARTBEAT_ESCALATION"
                    )
                    escalations.append(escalation)
        
        return escalations
    
    def _create_escalation(self, agent_id: str, task_id: str, 
                          level: EscalationLevel, reason: str, 
                          action_taken: str) -> EscalationEvent:
        """Create and store escalation event."""
        escalation = EscalationEvent(
            escalation_id=f"esc_{int(time.time())}_{agent_id}",
            agent_id=agent_id,
            task_id=task_id,
            timestamp=datetime.now(),
            level=level,
            reason=reason,
            action_taken=action_taken
        )
        
        # Store escalation
        if task_id not in self.escalations:
            self.escalations[task_id] = []
        self.escalations[task_id].append(escalation)
        
        # Update task escalation count
        if task_id in self.active_tasks:
            self.active_tasks[task_id].escalation_count += 1
            self._save_task_to_db(self.active_tasks[task_id])
        
        # Save to database
        self._save_escalation_to_db(escalation)
        
        logger.warning(f"Escalation created: {escalation.escalation_id} - {reason}")
        return escalation
    
    def reassign_task(self, task_id: str, new_agent_id: str, reason: str) -> bool:
        """Reassign task to a different agent."""
        if task_id not in self.active_tasks:
            logger.error(f"Task {task_id} not found for reassignment")
            return False
        
        task = self.active_tasks[task_id]
        
        # Check reassignment limit
        if task.reassignment_count >= self.config["max_reassignments"]:
            escalation = self._create_escalation(
                task.agent_id, task_id, EscalationLevel.SYSTEM_FAILURE,
                f"Maximum reassignments ({self.config['max_reassignments']}) exceeded",
                "HUMAN_INTERVENTION_REQUIRED"
            )
            return False
        
        # Update task
        old_agent_id = task.agent_id
        task.agent_id = new_agent_id
        task.reassignment_count += 1
        task.status = TaskStatus.REASSIGNED
        task.last_update = datetime.now()
        
        # Create escalation for reassignment
        escalation = self._create_escalation(
            new_agent_id, task_id, EscalationLevel.HIGH,
            f"Task reassigned from {old_agent_id} to {new_agent_id}: {reason}",
            "TASK_REASSIGNMENT"
        )
        
        self._save_task_to_db(task)
        
        logger.info(f"Task {task_id} reassigned from {old_agent_id} to {new_agent_id}")
        return True
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        agent_tasks = [t for t in self.active_tasks.values() if t.agent_id == agent_id]
        active_tasks = [t for t in agent_tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]]
        
        last_heartbeat = self.agent_heartbeats.get(agent_id)
        heartbeat_status = "unknown"
        if last_heartbeat:
            minutes_since = (datetime.now() - last_heartbeat).total_seconds() / 60
            if minutes_since < 5:
                heartbeat_status = "active"
            elif minutes_since < 15:
                heartbeat_status = "recent"
            else:
                heartbeat_status = "stale"
        
        return {
            "agent_id": agent_id,
            "total_tasks": len(agent_tasks),
            "active_tasks": len(active_tasks),
            "completed_tasks": len([t for t in agent_tasks if t.status == TaskStatus.COMPLETED]),
            "overdue_tasks": len([t for t in active_tasks if datetime.now() > t.deadline]),
            "blocked_tasks": len([t for t in active_tasks if t.status == TaskStatus.BLOCKED]),
            "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None,
            "heartbeat_status": heartbeat_status,
            "escalation_count": sum(t.escalation_count for t in agent_tasks),
            "reassignment_count": sum(t.reassignment_count for t in agent_tasks)
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system accountability status."""
        total_tasks = len(self.active_tasks)
        active_tasks = [t for t in self.active_tasks.values() 
                       if t.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]]
        
        overdue_tasks = [t for t in active_tasks if datetime.now() > t.deadline]
        blocked_tasks = [t for t in active_tasks if t.status == TaskStatus.BLOCKED]
        
        recent_escalations = []
        for escalation_list in self.escalations.values():
            recent_escalations.extend([
                e for e in escalation_list 
                if not e.resolved and (datetime.now() - e.timestamp).days < 1
            ])
        
        return {
            "total_tasks": total_tasks,
            "active_tasks": len(active_tasks),
            "completed_tasks": len([t for t in self.active_tasks.values() if t.status == TaskStatus.COMPLETED]),
            "overdue_tasks": len(overdue_tasks),
            "blocked_tasks": len(blocked_tasks),
            "total_escalations": len(recent_escalations),
            "critical_escalations": len([e for e in recent_escalations if e.level == EscalationLevel.CRITICAL]),
            "agents_tracked": len(self.agent_heartbeats),
            "active_agents": len([h for h in self.agent_heartbeats.values() 
                                if (datetime.now() - h).total_seconds() < 300]),  # 5 minutes
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_accountability_report(self) -> Dict[str, Any]:
        """Generate comprehensive accountability report."""
        system_status = self.get_system_status()
        
        # Agent summaries
        agent_summaries = {}
        for agent_id in set(t.agent_id for t in self.active_tasks.values()):
            agent_summaries[agent_id] = self.get_agent_status(agent_id)
        
        # Recent escalations
        recent_escalations = []
        for escalation_list in self.escalations.values():
            recent_escalations.extend([
                asdict(e) for e in escalation_list 
                if (datetime.now() - e.timestamp).days < 7
            ])
        
        # Task breakdown
        task_breakdown = {}
        for status in TaskStatus:
            task_breakdown[status.value] = len([
                t for t in self.active_tasks.values() if t.status == status
            ])
        
        return {
            "report_timestamp": datetime.now().isoformat(),
            "system_status": system_status,
            "agent_summaries": agent_summaries,
            "task_breakdown": task_breakdown,
            "recent_escalations": recent_escalations,
            "config": self.config
        }
    
    def _save_task_to_db(self, task: AgentTask):
        """Save task to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id, task.agent_id, task.title, task.description,
                task.assigned_at.isoformat(), task.deadline.isoformat(),
                task.priority, task.status.value, task.progress_percentage,
                task.last_update.isoformat() if task.last_update else None,
                task.evidence_hash, task.escalation_count, task.reassignment_count,
                json.dumps(task.metadata)
            ))
    
    def _save_progress_report_to_db(self, report: ProgressReport):
        """Save progress report to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO progress_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.report_id, report.agent_id, report.task_id,
                report.timestamp.isoformat(), report.progress_percentage,
                report.status_summary, json.dumps(report.evidence_files),
                json.dumps(report.blockers), report.eta_minutes,
                report.confidence_level, report.evidence_hash, report.is_valid
            ))
    
    def _save_escalation_to_db(self, escalation: EscalationEvent):
        """Save escalation to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO escalations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                escalation.escalation_id, escalation.agent_id, escalation.task_id,
                escalation.timestamp.isoformat(), escalation.level.value,
                escalation.reason, escalation.action_taken, escalation.resolved,
                escalation.resolution_time.isoformat() if escalation.resolution_time else None
            ))
    
    def _save_heartbeat_to_db(self, agent_id: str):
        """Save agent heartbeat to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_heartbeats VALUES (?, ?, ?, ?)
            """, (
                agent_id, self.agent_heartbeats[agent_id].isoformat(),
                "active", None
            ))


async def run_accountability_monitor():
    """Run continuous accountability monitoring."""
    system = AccountabilitySystem()
    
    while True:
        try:
            # Check timeouts and escalate
            escalations = system.check_timeouts_and_escalate()
            
            if escalations:
                logger.warning(f"Created {len(escalations)} escalations")
                
                # Print critical escalations
                for escalation in escalations:
                    if escalation.level in [EscalationLevel.CRITICAL, EscalationLevel.SYSTEM_FAILURE]:
                        print(f"🚨 CRITICAL ESCALATION: {escalation.reason}")
            
            # Generate status report
            report = system.generate_accountability_report()
            if report["system_status"]["critical_escalations"] > 0:
                print(f"⚠️  ACCOUNTABILITY ALERT: {report['system_status']['critical_escalations']} critical escalations")
            
            # Wait for next check
            await asyncio.sleep(system.config["check_interval_seconds"])
            
        except Exception as e:
            logger.error(f"Accountability monitor error: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Accountability System")
    parser.add_argument("--monitor", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--agent", help="Show specific agent status")
    parser.add_argument("--report", action="store_true", help="Generate full report")
    
    args = parser.parse_args()
    
    if args.monitor:
        asyncio.run(run_accountability_monitor())
    else:
        system = AccountabilitySystem()
        
        if args.status:
            status = system.get_system_status()
            print(json.dumps(status, indent=2))
        elif args.agent:
            agent_status = system.get_agent_status(args.agent)
            print(json.dumps(agent_status, indent=2))
        elif args.report:
            report = system.generate_accountability_report()
            print(json.dumps(report, indent=2, default=str))
        else:
            print("Use --help for usage information")