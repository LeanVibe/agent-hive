#!/usr/bin/env python3
"""
Agent Status Monitor Hook - Auto-notify PM agent of status updates
Triggers when any agent posts updates and notifies PM for evaluation.
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentStatusMonitor:
    """Monitor agent status updates and trigger PM evaluation"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pm_agent = "pm-agent-new"
        self.status_file = project_root / ".claude/state/agent_status_updates.json"
        self.escalation_threshold = 300  # 5 minutes idle threshold
        
    def detect_agent_update(self, agent_name: str, update_type: str, content: str) -> Dict:
        """Detect and log agent status update"""
        timestamp = datetime.now().isoformat()
        
        update = {
            "timestamp": timestamp,
            "agent": agent_name,
            "type": update_type,
            "content": content,
            "processed": False
        }
        
        # Save update to status file
        self._save_update(update)
        
        # Trigger PM notification
        self._notify_pm_agent(update)
        
        return update
    
    def _save_update(self, update: Dict):
        """Save status update to tracking file"""
        updates = []
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                updates = json.load(f)
        
        updates.append(update)
        
        # Keep only last 50 updates
        updates = updates[-50:]
        
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, 'w') as f:
            json.dump(updates, f, indent=2)
    
    def _notify_pm_agent(self, update: Dict):
        """Notify PM agent of status update for evaluation"""
        notification_msg = f"""AGENT UPDATE NOTIFICATION:

Agent: {update['agent']}
Type: {update['type']}
Timestamp: {update['timestamp']}
Content: {update['content'][:200]}...

REQUIRED ACTIONS:
1. Evaluate agent status and progress
2. Check if agent needs next task assignment
3. Consult Gemini CLI if complex decision needed
4. Either:
   - Assign next task to agent
   - Escalate to human for guidance
   - Mark as complete if work finished

Use: python scripts/fixed_agent_communication.py --agent {update['agent']} --message "NEXT_TASK"
Or escalate if needed."""

        try:
            cmd = [
                "python", "scripts/fixed_agent_communication.py",
                "--agent", self.pm_agent,
                "--message", notification_msg
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ PM agent notified of update from {update['agent']}")
            else:
                logger.error(f"❌ Failed to notify PM agent: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Exception notifying PM agent: {e}")
    
    def check_idle_agents(self) -> List[Dict]:
        """Check for agents that may be idle and need task assignment"""
        idle_agents = []
        
        if not self.status_file.exists():
            return idle_agents
            
        with open(self.status_file, 'r') as f:
            updates = json.load(f)
        
        # Get latest update per agent
        latest_by_agent = {}
        for update in updates:
            agent = update['agent']
            if agent not in latest_by_agent or update['timestamp'] > latest_by_agent[agent]['timestamp']:
                latest_by_agent[agent] = update
        
        # Check for idle agents
        current_time = datetime.now()
        for agent, last_update in latest_by_agent.items():
            update_time = datetime.fromisoformat(last_update['timestamp'])
            idle_seconds = (current_time - update_time).total_seconds()
            
            if idle_seconds > self.escalation_threshold and not last_update.get('processed', False):
                idle_agents.append({
                    "agent": agent,
                    "idle_seconds": idle_seconds,
                    "last_update": last_update
                })
        
        return idle_agents
    
    def escalate_idle_agents(self):
        """Escalate idle agents to PM for task assignment"""
        idle_agents = self.check_idle_agents()
        
        if not idle_agents:
            logger.info("✅ No idle agents detected")
            return
        
        for idle_info in idle_agents:
            escalation_msg = f"""IDLE AGENT ESCALATION:

Agent: {idle_info['agent']}
Idle for: {idle_info['idle_seconds']:.0f} seconds
Last update: {idle_info['last_update']['content'][:150]}...

REQUIRED ACTION:
Agent appears to be waiting for next task assignment. Please:
1. Check agent current status
2. Assign next task or provide guidance
3. If stuck, escalate to human

Agent may need: next task, clarification, or human intervention."""

            try:
                cmd = [
                    "python", "scripts/fixed_agent_communication.py",
                    "--agent", self.pm_agent,
                    "--message", escalation_msg
                ]
                
                subprocess.run(cmd, cwd=self.project_root, timeout=30)
                logger.info(f"⚠️ Escalated idle agent {idle_info['agent']} to PM")
                
            except Exception as e:
                logger.error(f"❌ Failed to escalate {idle_info['agent']}: {e}")

def main():
    """CLI interface for agent status monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Status Monitor Hook")
    parser.add_argument("--agent", required=True, help="Agent name that posted update")
    parser.add_argument("--type", default="status", help="Update type")
    parser.add_argument("--content", required=True, help="Update content")
    parser.add_argument("--check-idle", action="store_true", help="Check for idle agents")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    monitor = AgentStatusMonitor(project_root)
    
    if args.check_idle:
        monitor.escalate_idle_agents()
    else:
        update = monitor.detect_agent_update(args.agent, args.type, args.content)
        logger.info(f"✅ Processed update from {args.agent}")

if __name__ == "__main__":
    main()