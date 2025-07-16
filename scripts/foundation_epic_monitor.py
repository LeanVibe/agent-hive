#!/usr/bin/env python3
"""
Foundation Epic Progress Monitor
Tracks foundation team progress and coordinates epic milestones.
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FoundationEpicMonitor:
    """Monitor and coordinate Foundation Epic Phase 1 progress"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tracking_file = project_root / ".claude/state/foundation_epic_tracking.json"
        self.communication_script = project_root / "scripts/fixed_agent_communication.py"
        
    def load_tracking_data(self) -> Dict:
        """Load foundation epic tracking data"""
        if not self.tracking_file.exists():
            logger.error("Foundation epic tracking file not found")
            return {}
            
        with open(self.tracking_file, 'r') as f:
            return json.load(f)
    
    def save_tracking_data(self, data: Dict):
        """Save updated tracking data"""
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_agent_status(self) -> Dict:
        """Get current agent status from status script"""
        try:
            result = subprocess.run([
                "python", "scripts/check_agent_status.py", "--format", "json"
            ], cwd=self.project_root, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse the status output (simplified for demo)
                return {"status": "success", "output": result.stdout}
            else:
                return {"status": "error", "error": result.stderr}
                
        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
            return {"status": "error", "error": str(e)}
    
    def send_agent_message(self, agent_id: str, message: str) -> bool:
        """Send message to specific agent"""
        try:
            result = subprocess.run([
                "python", str(self.communication_script),
                "--agent", agent_id,
                "--message", message
            ], cwd=self.project_root, capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to send message to {agent_id}: {e}")
            return False
    
    def check_foundation_team_progress(self) -> Dict:
        """Check progress of foundation team agents"""
        data = self.load_tracking_data()
        foundation_epic = data.get("foundation_epic_phase1", {})
        foundation_team = foundation_epic.get("foundation_team", {})
        
        progress_summary = {
            "timestamp": datetime.now().isoformat(),
            "agents_checked": 0,
            "agents_responsive": 0,
            "overdue_reports": [],
            "progress_reports": {}
        }
        
        current_time = datetime.now()
        report_interval = timedelta(hours=6)
        
        for role, agent_info in foundation_team.items():
            agent_id = agent_info.get("agent_id")
            last_update = agent_info.get("last_update")
            
            progress_summary["agents_checked"] += 1
            
            if last_update:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00').replace('+00:00', ''))
                time_since_update = current_time - last_update_time
                
                if time_since_update > report_interval:
                    progress_summary["overdue_reports"].append({
                        "agent_id": agent_id,
                        "role": role,
                        "hours_overdue": time_since_update.total_seconds() / 3600
                    })
                else:
                    progress_summary["agents_responsive"] += 1
        
        return progress_summary
    
    def request_progress_reports(self, overdue_agents: List[Dict]) -> bool:
        """Request progress reports from overdue agents"""
        success_count = 0
        
        for agent_info in overdue_agents:
            agent_id = agent_info["agent_id"]
            role = agent_info["role"]
            hours_overdue = agent_info["hours_overdue"]
            
            message = f"""FOUNDATION EPIC PROGRESS REPORT REQUIRED:

Agent: {agent_id}
Role: {role}
Report overdue by: {hours_overdue:.1f} hours

Please provide immediate status update:
1. Current milestone progress
2. Technical decisions made
3. Implementation status
4. Blockers or dependencies
5. Revised timeline estimate

Foundation Epic coordination requires regular progress visibility."""
            
            if self.send_agent_message(agent_id, message):
                success_count += 1
                logger.info(f"✅ Progress report requested from {agent_id}")
            else:
                logger.error(f"❌ Failed to request report from {agent_id}")
        
        return success_count == len(overdue_agents)
    
    def generate_foundation_epic_status(self) -> Dict:
        """Generate comprehensive foundation epic status"""
        data = self.load_tracking_data()
        foundation_epic = data.get("foundation_epic_phase1", {})
        
        progress_check = self.check_foundation_team_progress()
        agent_status = self.get_agent_status()
        
        epic_status = {
            "timestamp": datetime.now().isoformat(),
            "epic_phase": "Phase 1",
            "start_date": foundation_epic.get("start_date"),
            "strategy": foundation_epic.get("strategy"),
            "foundation_team_status": {
                "total_agents": progress_check["agents_checked"],
                "responsive_agents": progress_check["agents_responsive"],
                "overdue_reports": len(progress_check["overdue_reports"]),
                "team_health": "healthy" if progress_check["agents_responsive"] >= 2 else "attention_needed"
            },
            "success_criteria_progress": {
                "message_queue_implementation": "in_progress",
                "intelligence_ml_implementation": "in_progress", 
                "migration_tools": "in_progress",
                "timeline_status": "on_track"  # Will be updated based on reports
            },
            "next_actions": []
        }
        
        # Generate next actions based on status
        if progress_check["overdue_reports"]:
            epic_status["next_actions"].append("Request overdue progress reports")
        
        if progress_check["agents_responsive"] < 2:
            epic_status["next_actions"].append("Escalate agent responsiveness issues")
        
        return epic_status
    
    def escalate_timeline_risks(self, epic_status: Dict):
        """Escalate timeline risks to PM agent and human"""
        pm_agent = "pm-agent-new"
        
        team_health = epic_status["foundation_team_status"]["team_health"]
        overdue_count = epic_status["foundation_team_status"]["overdue_reports"]
        
        if team_health == "attention_needed" or overdue_count >= 2:
            escalation_message = f"""FOUNDATION EPIC ESCALATION REQUIRED:

Epic Status: {epic_status['foundation_team_status']['team_health']}
Overdue Reports: {overdue_count}
Responsive Agents: {epic_status['foundation_team_status']['responsive_agents']}/3

RISKS IDENTIFIED:
- Foundation team communication gaps
- Potential timeline delays
- Coordination challenges

RECOMMENDED ACTIONS:
1. Direct agent contact and status verification
2. Timeline risk assessment
3. Potential scope adjustment
4. Human escalation if no response within 2 hours

Please coordinate immediate foundation team assessment."""
            
            if self.send_agent_message(pm_agent, escalation_message):
                logger.warning(f"⚠️ Foundation Epic escalated to {pm_agent}")
                return True
            else:
                logger.error(f"❌ Failed to escalate to {pm_agent}")
                return False
        
        return True

def main():
    """CLI interface for foundation epic monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Foundation Epic Progress Monitor")
    parser.add_argument("--check-progress", action="store_true", help="Check foundation team progress")
    parser.add_argument("--request-reports", action="store_true", help="Request overdue progress reports")
    parser.add_argument("--status", action="store_true", help="Generate epic status report")
    parser.add_argument("--escalate", action="store_true", help="Check and escalate risks")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    monitor = FoundationEpicMonitor(project_root)
    
    if args.check_progress:
        progress = monitor.check_foundation_team_progress()
        print(json.dumps(progress, indent=2))
    
    elif args.request_reports:
        progress = monitor.check_foundation_team_progress()
        if progress["overdue_reports"]:
            success = monitor.request_progress_reports(progress["overdue_reports"])
            print(f"✅ Progress reports requested: {success}")
        else:
            print("✅ No overdue reports")
    
    elif args.status:
        epic_status = monitor.generate_foundation_epic_status()
        print(json.dumps(epic_status, indent=2))
    
    elif args.escalate:
        epic_status = monitor.generate_foundation_epic_status()
        escalated = monitor.escalate_timeline_risks(epic_status)
        print(f"Escalation status: {escalated}")
    
    else:
        # Default: comprehensive monitoring
        progress = monitor.check_foundation_team_progress()
        
        if progress["overdue_reports"]:
            monitor.request_progress_reports(progress["overdue_reports"])
        
        epic_status = monitor.generate_foundation_epic_status()
        monitor.escalate_timeline_risks(epic_status)
        
        print(json.dumps(epic_status, indent=2))

if __name__ == "__main__":
    main()