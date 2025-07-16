#!/usr/bin/env python3
"""
Agent Status Enforcement System - Phase 1.1 Workflow Improvement

Implements automated monitoring and escalation for non-responsive agents
with 5/10/15/20 minute escalation tiers and automatic git command execution.

Features:
- Real-time agent activity monitoring
- Multi-tier escalation with automated interventions
- Git command auto-execution for blocked agents
- Status persistence and recovery
- Notification system integration
"""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import argparse


class EscalationLevel(Enum):
    """Escalation levels for non-responsive agents"""
    NORMAL = "normal"
    WARNING_5MIN = "warning_5min"  
    CRITICAL_10MIN = "critical_10min"
    EMERGENCY_15MIN = "emergency_15min"
    TERMINAL_20MIN = "terminal_20min"


class AgentStatus(Enum):
    """Agent operational status"""
    ACTIVE = "active"
    IDLE = "idle"
    BLOCKED = "blocked"
    NON_RESPONSIVE = "non_responsive"
    TERMINATED = "terminated"


@dataclass
class AgentState:
    """Agent state tracking"""
    name: str
    status: AgentStatus
    last_activity: datetime
    last_response: datetime
    escalation_level: EscalationLevel
    escalation_count: int
    git_status: Dict[str, str]
    worktree_path: Optional[str]
    tmux_window: Optional[str]
    blocked_duration: float  # minutes
    intervention_history: List[Dict]
    
    def __post_init__(self):
        if isinstance(self.last_activity, str):
            self.last_activity = datetime.fromisoformat(self.last_activity)
        if isinstance(self.last_response, str):
            self.last_response = datetime.fromisoformat(self.last_response)


class AgentStatusEnforcer:
    """
    Automated status enforcement system for agent monitoring and intervention.
    
    Monitors agent activity and implements escalation procedures:
    - 5 min: Warning notification + status check
    - 10 min: Critical alert + force status update
    - 15 min: Emergency intervention + git command execution
    - 20 min: Terminal escalation + agent restart
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the status enforcement system."""
        self.base_dir = Path(".")
        self.worktrees_dir = self.base_dir / "new-worktrees"
        self.config_path = config_path or self.base_dir / ".claude" / "enforcement_config.json"
        self.state_file = self.base_dir / ".claude" / "agent_states.json"
        
        # Escalation timing (minutes)
        self.escalation_timings = {
            EscalationLevel.WARNING_5MIN: 5,
            EscalationLevel.CRITICAL_10MIN: 10,
            EscalationLevel.EMERGENCY_15MIN: 15,
            EscalationLevel.TERMINAL_20MIN: 20
        }
        
        # Agent states
        self.agent_states: Dict[str, AgentState] = {}
        self.monitoring_active = False
        
        # Configuration
        self.config = self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Load existing states
        self._load_agent_states()
        
        logging.info("AgentStatusEnforcer initialized")
    
    def _load_config(self) -> Dict:
        """Load enforcement configuration."""
        default_config = {
            "enabled": True,
            "check_interval": 60,  # seconds
            "max_escalations": 3,
            "auto_git_execution": True,
            "auto_restart_agents": True,
            "notification_webhooks": [],
            "excluded_agents": ["pm-agent"],
            "git_commands": {
                "status_check": ["git", "status", "--porcelain"],
                "force_commit": ["git", "add", ".", "&&", "git", "commit", "-m", "🤖 Auto-commit by status enforcer"],
                "force_push": ["git", "push", "origin", "HEAD"]
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logging.warning(f"Failed to load config: {e}, using defaults")
        
        return default_config
    
    def _setup_logging(self):
        """Setup enforcement logging."""
        log_dir = self.base_dir / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "enforcement.log"),
                logging.StreamHandler()
            ]
        )
    
    def _load_agent_states(self):
        """Load persisted agent states."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for name, state_data in data.items():
                        self.agent_states[name] = AgentState(**state_data)
                logging.info(f"Loaded {len(self.agent_states)} agent states")
            except Exception as e:
                logging.error(f"Failed to load agent states: {e}")
    
    def _save_agent_states(self):
        """Persist agent states."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                states_data = {name: asdict(state) for name, state in self.agent_states.items()}
                # Convert datetime objects to ISO strings
                for state_data in states_data.values():
                    if isinstance(state_data['last_activity'], datetime):
                        state_data['last_activity'] = state_data['last_activity'].isoformat()
                    if isinstance(state_data['last_response'], datetime):
                        state_data['last_response'] = state_data['last_response'].isoformat()
                json.dump(states_data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save agent states: {e}")
    
    async def start_monitoring(self):
        """Start the monitoring and enforcement loop."""
        if not self.config["enabled"]:
            logging.info("Status enforcement disabled by configuration")
            return
        
        self.monitoring_active = True
        logging.info("🚀 Agent status enforcement monitoring started")
        
        try:
            while self.monitoring_active:
                await self._monitoring_cycle()
                await asyncio.sleep(self.config["check_interval"])
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
        except Exception as e:
            logging.error(f"Monitoring error: {e}")
        finally:
            self.monitoring_active = False
            self._save_agent_states()
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.monitoring_active = False
        self._save_agent_states()
        logging.info("Agent status enforcement monitoring stopped")
    
    async def _monitoring_cycle(self):
        """Execute one monitoring cycle."""
        try:
            # Discover active agents
            agents = await self._discover_agents()
            
            # Update agent states
            for agent_name, agent_info in agents.items():
                if agent_name in self.config["excluded_agents"]:
                    continue
                
                await self._update_agent_state(agent_name, agent_info)
            
            # Process escalations
            await self._process_escalations()
            
            # Cleanup old states
            self._cleanup_old_states()
            
            # Save states
            self._save_agent_states()
            
        except Exception as e:
            logging.error(f"Error in monitoring cycle: {e}")
    
    async def _discover_agents(self) -> Dict[str, Dict]:
        """Discover all active agents."""
        agents = {}
        
        # Check worktrees
        if self.worktrees_dir.exists():
            for worktree_dir in self.worktrees_dir.iterdir():
                if worktree_dir.is_dir():
                    agent_name = worktree_dir.name
                    agents[agent_name] = {
                        "name": agent_name,
                        "worktree_path": str(worktree_dir),
                        "last_activity": self._get_last_activity(worktree_dir),
                        "tmux_window": await self._check_tmux_window(agent_name),
                        "git_status": await self._get_git_status(worktree_dir)
                    }
        
        return agents
    
    def _get_last_activity(self, worktree_dir: Path) -> datetime:
        """Get last activity timestamp for worktree."""
        try:
            # Check git log for last commit
            result = subprocess.run([
                "git", "-C", str(worktree_dir), "log", "-1", "--format=%ct"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                return datetime.fromtimestamp(int(result.stdout.strip()))
            
            # Fallback to directory modification time
            return datetime.fromtimestamp(worktree_dir.stat().st_mtime)
        except Exception:
            return datetime.fromtimestamp(worktree_dir.stat().st_mtime)
    
    async def _check_tmux_window(self, agent_name: str) -> Optional[str]:
        """Check if agent has an active tmux window."""
        try:
            # Try both naming conventions
            for window_name in [f"agent-{agent_name}", agent_name]:
                result = subprocess.run([
                    "tmux", "list-windows", "-t", "agent-hive", "-F", "#{window_name}"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and window_name in result.stdout:
                    return window_name
            
            return None
        except Exception:
            return None
    
    async def _get_git_status(self, worktree_dir: Path) -> Dict[str, str]:
        """Get git status for worktree."""
        try:
            # Check if there are uncommitted changes
            result = subprocess.run([
                "git", "-C", str(worktree_dir), "status", "--porcelain"
            ], capture_output=True, text=True, timeout=10)
            
            uncommitted_changes = bool(result.stdout.strip()) if result.returncode == 0 else False
            
            # Check if ahead of remote
            result = subprocess.run([
                "git", "-C", str(worktree_dir), "rev-list", "--count", "HEAD@{upstream}..HEAD"
            ], capture_output=True, text=True, timeout=10)
            
            ahead_count = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else 0
            
            return {
                "uncommitted_changes": str(uncommitted_changes),
                "ahead_of_remote": str(ahead_count > 0),
                "ahead_count": str(ahead_count)
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _update_agent_state(self, agent_name: str, agent_info: Dict):
        """Update state for a specific agent."""
        now = datetime.now()
        
        if agent_name not in self.agent_states:
            # Initialize new agent state
            self.agent_states[agent_name] = AgentState(
                name=agent_name,
                status=AgentStatus.ACTIVE,
                last_activity=agent_info["last_activity"],
                last_response=now,
                escalation_level=EscalationLevel.NORMAL,
                escalation_count=0,
                git_status=agent_info["git_status"],
                worktree_path=agent_info["worktree_path"],
                tmux_window=agent_info["tmux_window"],
                blocked_duration=0.0,
                intervention_history=[]
            )
        else:
            # Update existing state
            state = self.agent_states[agent_name]
            
            # Check if agent has been active
            if agent_info["last_activity"] > state.last_activity:
                state.last_activity = agent_info["last_activity"]
                state.last_response = now
                state.escalation_level = EscalationLevel.NORMAL
                state.escalation_count = 0
                state.blocked_duration = 0.0
                state.status = AgentStatus.ACTIVE
            else:
                # Calculate blocked duration
                state.blocked_duration = (now - state.last_response).total_seconds() / 60
                
                # Update git status
                state.git_status = agent_info["git_status"]
                state.tmux_window = agent_info["tmux_window"]
    
    async def _process_escalations(self):
        """Process escalation for all agents."""
        for agent_name, state in self.agent_states.items():
            if state.status == AgentStatus.TERMINATED:
                continue
            
            await self._check_escalation(agent_name, state)
    
    async def _check_escalation(self, agent_name: str, state: AgentState):
        """Check and process escalation for a specific agent."""
        current_escalation = self._determine_escalation_level(state.blocked_duration)
        
        if current_escalation != state.escalation_level:
            await self._escalate_agent(agent_name, state, current_escalation)
    
    def _determine_escalation_level(self, blocked_minutes: float) -> EscalationLevel:
        """Determine escalation level based on blocked duration."""
        if blocked_minutes >= 20:
            return EscalationLevel.TERMINAL_20MIN
        elif blocked_minutes >= 15:
            return EscalationLevel.EMERGENCY_15MIN
        elif blocked_minutes >= 10:
            return EscalationLevel.CRITICAL_10MIN
        elif blocked_minutes >= 5:
            return EscalationLevel.WARNING_5MIN
        else:
            return EscalationLevel.NORMAL
    
    async def _escalate_agent(self, agent_name: str, state: AgentState, new_level: EscalationLevel):
        """Execute escalation procedure for agent."""
        logging.warning(f"🚨 Escalating {agent_name} to {new_level.value} (blocked {state.blocked_duration:.1f}m)")
        
        state.escalation_level = new_level
        state.escalation_count += 1
        
        intervention = {
            "timestamp": datetime.now().isoformat(),
            "escalation_level": new_level.value,
            "blocked_duration": state.blocked_duration,
            "actions_taken": []
        }
        
        try:
            if new_level == EscalationLevel.WARNING_5MIN:
                await self._warning_intervention(agent_name, state, intervention)
            elif new_level == EscalationLevel.CRITICAL_10MIN:
                await self._critical_intervention(agent_name, state, intervention)
            elif new_level == EscalationLevel.EMERGENCY_15MIN:
                await self._emergency_intervention(agent_name, state, intervention)
            elif new_level == EscalationLevel.TERMINAL_20MIN:
                await self._terminal_intervention(agent_name, state, intervention)
        
        except Exception as e:
            logging.error(f"Escalation failed for {agent_name}: {e}")
            intervention["actions_taken"].append(f"ERROR: {str(e)}")
        
        state.intervention_history.append(intervention)
        
        # Limit intervention history size
        if len(state.intervention_history) > 10:
            state.intervention_history = state.intervention_history[-10:]
    
    async def _warning_intervention(self, agent_name: str, state: AgentState, intervention: Dict):
        """5-minute warning intervention."""
        actions = []
        
        # Send status check message
        if state.tmux_window:
            message = f"⚠️ STATUS CHECK: Agent {agent_name} has been inactive for {state.blocked_duration:.1f} minutes. Please provide status update."
            success = await self._send_message_to_agent(agent_name, message)
            actions.append(f"Status check message sent: {success}")
        
        # Log warning
        logging.warning(f"⚠️ WARNING: {agent_name} inactive for {state.blocked_duration:.1f}m")
        actions.append("Warning logged")
        
        intervention["actions_taken"].extend(actions)
    
    async def _critical_intervention(self, agent_name: str, state: AgentState, intervention: Dict):
        """10-minute critical intervention."""
        actions = []
        
        # Force status update
        if state.tmux_window:
            message = f"🚨 CRITICAL: Agent {agent_name} non-responsive for {state.blocked_duration:.1f} minutes. Immediate response required or automatic intervention will begin."
            success = await self._send_message_to_agent(agent_name, message)
            actions.append(f"Critical alert sent: {success}")
        
        # Check git status more thoroughly
        if state.worktree_path:
            git_check = await self._detailed_git_check(state.worktree_path)
            actions.append(f"Git status check: {git_check}")
        
        intervention["actions_taken"].extend(actions)
    
    async def _emergency_intervention(self, agent_name: str, state: AgentState, intervention: Dict):
        """15-minute emergency intervention with git commands."""
        actions = []
        
        # Execute git commands if enabled
        if self.config["auto_git_execution"] and state.worktree_path:
            git_actions = await self._execute_git_commands(state.worktree_path)
            actions.extend(git_actions)
        
        # Send emergency notification
        if state.tmux_window:
            message = f"🆘 EMERGENCY: Agent {agent_name} unresponsive for {state.blocked_duration:.1f} minutes. Auto-execution of git commands initiated."
            success = await self._send_message_to_agent(agent_name, message)
            actions.append(f"Emergency notification sent: {success}")
        
        # Update agent status
        state.status = AgentStatus.BLOCKED
        actions.append("Agent marked as BLOCKED")
        
        intervention["actions_taken"].extend(actions)
    
    async def _terminal_intervention(self, agent_name: str, state: AgentState, intervention: Dict):
        """20-minute terminal intervention with restart."""
        actions = []
        
        # Mark as terminated
        state.status = AgentStatus.TERMINATED
        actions.append("Agent marked as TERMINATED")
        
        # Final git cleanup
        if self.config["auto_git_execution"] and state.worktree_path:
            git_actions = await self._execute_git_commands(state.worktree_path, force=True)
            actions.extend(git_actions)
        
        # Attempt agent restart if enabled
        if self.config["auto_restart_agents"]:
            restart_success = await self._restart_agent(agent_name, state)
            actions.append(f"Agent restart attempted: {restart_success}")
        
        # Send terminal notification
        message = f"💀 TERMINAL: Agent {agent_name} terminated after {state.blocked_duration:.1f} minutes of non-responsiveness."
        logging.error(message)
        actions.append("Terminal notification logged")
        
        intervention["actions_taken"].extend(actions)
    
    async def _send_message_to_agent(self, agent_name: str, message: str) -> bool:
        """Send message to agent via tmux."""
        try:
            # Use the fixed agent communication system
            result = subprocess.run([
                "python", "scripts/fixed_agent_communication.py",
                "--agent", agent_name,
                "--message", message
            ], capture_output=True, text=True, timeout=15)
            
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Failed to send message to {agent_name}: {e}")
            return False
    
    async def _detailed_git_check(self, worktree_path: str) -> Dict:
        """Perform detailed git status check."""
        try:
            checks = {}
            
            # Check for uncommitted changes
            result = subprocess.run([
                "git", "-C", worktree_path, "status", "--porcelain"
            ], capture_output=True, text=True, timeout=10)
            checks["uncommitted_files"] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            # Check branch status
            result = subprocess.run([
                "git", "-C", worktree_path, "branch", "--show-current"
            ], capture_output=True, text=True, timeout=10)
            checks["current_branch"] = result.stdout.strip()
            
            # Check for unpushed commits
            result = subprocess.run([
                "git", "-C", worktree_path, "log", "--oneline", "@{u}.."
            ], capture_output=True, text=True, timeout=10)
            checks["unpushed_commits"] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            return checks
        except Exception as e:
            return {"error": str(e)}
    
    async def _execute_git_commands(self, worktree_path: str, force: bool = False) -> List[str]:
        """Execute git commands for blocked agent."""
        actions = []
        
        try:
            # Check if there are changes to commit
            result = subprocess.run([
                "git", "-C", worktree_path, "status", "--porcelain"
            ], capture_output=True, text=True, timeout=10)
            
            if result.stdout.strip():
                # Add and commit changes
                subprocess.run([
                    "git", "-C", worktree_path, "add", "."
                ], timeout=30)
                actions.append("Staged all changes")
                
                commit_msg = "🤖 Auto-commit by status enforcer - non-responsive agent intervention"
                if force:
                    commit_msg += " (TERMINAL)"
                
                result = subprocess.run([
                    "git", "-C", worktree_path, "commit", "-m", commit_msg
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    actions.append("Created auto-commit")
                else:
                    actions.append(f"Commit failed: {result.stderr}")
            
            # Push to remote if enabled
            if force or self.config.get("auto_push", False):
                result = subprocess.run([
                    "git", "-C", worktree_path, "push", "origin", "HEAD"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    actions.append("Pushed to remote")
                else:
                    actions.append(f"Push failed: {result.stderr}")
        
        except Exception as e:
            actions.append(f"Git command error: {str(e)}")
        
        return actions
    
    async def _restart_agent(self, agent_name: str, state: AgentState) -> bool:
        """Attempt to restart terminated agent."""
        try:
            # Kill existing tmux window if it exists
            if state.tmux_window:
                subprocess.run([
                    "tmux", "kill-window", "-t", f"agent-hive:{state.tmux_window}"
                ], capture_output=True, timeout=10)
            
            # Restart agent using enhanced spawner
            result = subprocess.run([
                "python", "scripts/enhanced_agent_spawner.py",
                "--agent-type", agent_name,
                "--task", "Resume work after status enforcement intervention"
            ], capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Failed to restart {agent_name}: {e}")
            return False
    
    def _cleanup_old_states(self):
        """Remove states for agents that no longer exist."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        to_remove = []
        for agent_name, state in self.agent_states.items():
            if state.last_activity < cutoff_time:
                to_remove.append(agent_name)
        
        for agent_name in to_remove:
            del self.agent_states[agent_name]
            logging.info(f"Cleaned up old state for {agent_name}")
    
    def get_status_report(self) -> Dict:
        """Generate comprehensive status report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self.monitoring_active,
            "total_agents": len(self.agent_states),
            "agents_by_status": {},
            "agents_by_escalation": {},
            "interventions_last_hour": 0,
            "agents": {}
        }
        
        # Count agents by status and escalation
        for state in self.agent_states.values():
            # By status
            status_key = state.status.value
            report["agents_by_status"][status_key] = report["agents_by_status"].get(status_key, 0) + 1
            
            # By escalation
            escalation_key = state.escalation_level.value
            report["agents_by_escalation"][escalation_key] = report["agents_by_escalation"].get(escalation_key, 0) + 1
            
            # Count recent interventions
            hour_ago = datetime.now() - timedelta(hours=1)
            recent_interventions = [
                i for i in state.intervention_history 
                if datetime.fromisoformat(i["timestamp"]) > hour_ago
            ]
            report["interventions_last_hour"] += len(recent_interventions)
            
            # Agent details
            report["agents"][state.name] = {
                "status": state.status.value,
                "escalation_level": state.escalation_level.value,
                "blocked_duration": state.blocked_duration,
                "last_activity": state.last_activity.isoformat(),
                "intervention_count": len(state.intervention_history)
            }
        
        return report


async def main():
    """Main CLI interface for agent status enforcement."""
    parser = argparse.ArgumentParser(description="Agent Status Enforcement System")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--start", action="store_true", help="Start monitoring")
    parser.add_argument("--status", action="store_true", help="Show status report")
    parser.add_argument("--agent", help="Check specific agent status")
    parser.add_argument("--escalate", help="Manually escalate agent")
    parser.add_argument("--reset", help="Reset agent escalation state")
    
    args = parser.parse_args()
    
    enforcer = AgentStatusEnforcer(args.config)
    
    if args.start:
        print("🚀 Starting agent status enforcement monitoring...")
        await enforcer.start_monitoring()
    elif args.status:
        report = enforcer.get_status_report()
        print(json.dumps(report, indent=2))
    elif args.agent:
        if args.agent in enforcer.agent_states:
            state = enforcer.agent_states[args.agent]
            print(json.dumps(asdict(state), indent=2, default=str))
        else:
            print(f"Agent {args.agent} not found")
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())