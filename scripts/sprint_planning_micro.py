#!/usr/bin/env python3
"""
Sprint Planning Micro-Component - XP Methodology Enforcement
Part of PM/XP Methodology Enforcer (Micro-Component #1)

This micro-component handles ONLY core sprint planning functionality.
Follows XP Small Releases principle: ≤500 lines, single responsibility.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class SprintMicro:
    """Minimal sprint data structure for micro-component."""
    sprint_id: str
    name: str
    start_date: str
    end_date: str
    goal: str
    status: str  # 'planning', 'active', 'completed'
    capacity: int
    velocity_target: int


class SprintPlanningMicro:
    """Micro-component for core sprint planning functionality only."""
    
    def __init__(self, db_path: str = "sprint_micro.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize minimal database for sprint planning micro-component."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sprints_micro (
                    sprint_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    capacity INTEGER NOT NULL,
                    velocity_target INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def create_sprint(self, name: str, goal: str, days: int = 14, 
                     capacity: int = 40, velocity_target: int = 25) -> SprintMicro:
        """Create a new sprint - micro-component core functionality."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        sprint_id = f"sprint-{start_date.strftime('%Y%m%d')}"
        
        sprint = SprintMicro(
            sprint_id=sprint_id,
            name=name,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            goal=goal,
            status='planning',
            capacity=capacity,
            velocity_target=velocity_target
        )
        
        self.save_sprint(sprint)
        return sprint
    
    def save_sprint(self, sprint: SprintMicro):
        """Save sprint to database - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sprints_micro
                (sprint_id, name, start_date, end_date, goal, status, 
                 capacity, velocity_target, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sprint.sprint_id, sprint.name, sprint.start_date,
                sprint.end_date, sprint.goal, sprint.status,
                sprint.capacity, sprint.velocity_target,
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_current_sprint(self) -> Optional[SprintMicro]:
        """Get current active sprint - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sprint_id, name, start_date, end_date, goal, 
                       status, capacity, velocity_target
                FROM sprints_micro
                WHERE status IN ('planning', 'active')
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                return SprintMicro(*result)
            return None
    
    def start_sprint(self, sprint_id: str) -> bool:
        """Start a planned sprint - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sprints_micro 
                SET status = 'active'
                WHERE sprint_id = ? AND status = 'planning'
            """, (sprint_id,))
            
            return conn.total_changes > 0
    
    def complete_sprint(self, sprint_id: str) -> bool:
        """Complete an active sprint - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sprints_micro 
                SET status = 'completed'
                WHERE sprint_id = ? AND status = 'active'
            """, (sprint_id,))
            
            return conn.total_changes > 0
    
    def list_sprints(self, limit: int = 10) -> List[SprintMicro]:
        """List recent sprints - micro-component functionality."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sprint_id, name, start_date, end_date, goal,
                       status, capacity, velocity_target
                FROM sprints_micro
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [SprintMicro(*row) for row in cursor.fetchall()]
    
    def get_sprint_summary(self, sprint_id: str) -> Dict:
        """Get sprint summary - micro-component functionality."""
        sprint = self.get_current_sprint()
        if not sprint or sprint.sprint_id != sprint_id:
            return {"error": "Sprint not found"}
        
        return {
            "sprint_id": sprint.sprint_id,
            "name": sprint.name,
            "status": sprint.status,
            "goal": sprint.goal,
            "capacity": sprint.capacity,
            "velocity_target": sprint.velocity_target,
            "start_date": sprint.start_date,
            "end_date": sprint.end_date
        }


def main():
    """CLI interface for sprint planning micro-component."""
    import sys
    
    if len(sys.argv) < 2:
        print("Sprint Planning Micro-Component")
        print("Commands:")
        print("  create <name> <goal> [days] - Create new sprint")
        print("  start <sprint_id>          - Start planned sprint")
        print("  complete <sprint_id>       - Complete active sprint")
        print("  current                    - Show current sprint")
        print("  list [limit]               - List recent sprints")
        return
    
    planner = SprintPlanningMicro()
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 4:
            print("Usage: create <name> <goal> [days]")
            return
        
        name = sys.argv[2]
        goal = sys.argv[3]
        days = int(sys.argv[4]) if len(sys.argv) > 4 else 14
        
        sprint = planner.create_sprint(name, goal, days)
        print(f"✅ Created sprint: {sprint.sprint_id}")
        print(f"Name: {sprint.name}")
        print(f"Goal: {sprint.goal}")
        print(f"Duration: {sprint.start_date} to {sprint.end_date}")
    
    elif command == "start":
        if len(sys.argv) < 3:
            print("Usage: start <sprint_id>")
            return
        
        sprint_id = sys.argv[2]
        if planner.start_sprint(sprint_id):
            print(f"✅ Started sprint: {sprint_id}")
        else:
            print(f"❌ Could not start sprint: {sprint_id}")
    
    elif command == "complete":
        if len(sys.argv) < 3:
            print("Usage: complete <sprint_id>")
            return
        
        sprint_id = sys.argv[2]
        if planner.complete_sprint(sprint_id):
            print(f"✅ Completed sprint: {sprint_id}")
        else:
            print(f"❌ Could not complete sprint: {sprint_id}")
    
    elif command == "current":
        sprint = planner.get_current_sprint()
        if sprint:
            print(f"Current Sprint: {sprint.sprint_id}")
            print(f"Name: {sprint.name}")
            print(f"Status: {sprint.status}")
            print(f"Goal: {sprint.goal}")
            print(f"Capacity: {sprint.capacity}")
            print(f"Target Velocity: {sprint.velocity_target}")
        else:
            print("No active sprint")
    
    elif command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        sprints = planner.list_sprints(limit)
        
        print(f"Recent Sprints (last {limit}):")
        for sprint in sprints:
            print(f"  {sprint.sprint_id}: {sprint.name} [{sprint.status}]")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()