#!/usr/bin/env python3
"""
Agent Heartbeat Monitoring System

Implements real-time heartbeat monitoring for all agents in the LeanVibe Agent Hive
system with configurable timeout detection and automated recovery actions.
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AgentStatus:
    """Agent status information."""
    agent_id: str
    window_name: str
    last_heartbeat: datetime
    status: str  # "alive", "timeout", "dead", "recovery"
    response_time_ms: float
    consecutive_failures: int = 0
    recovery_attempts: int = 0


@dataclass
class HeartbeatConfig:
    """Heartbeat monitoring configuration."""
    heartbeat_interval: float = 30.0  # seconds
    timeout_threshold: float = 900.0  # 15 minutes
    max_consecutive_failures: int = 3
    max_recovery_attempts: int = 2
    recovery_timeout: float = 300.0  # 5 minutes
    log_file: str = ".claude/logs/heartbeat_monitor.log"


class AgentHeartbeatMonitor:
    """Monitors agent heartbeats and handles timeout recovery."""
    
    def __init__(self, config: HeartbeatConfig = None):
        """Initialize the heartbeat monitor."""
        self.config = config or HeartbeatConfig()
        self.agents: Dict[str, AgentStatus] = {}
        self.monitored_agents: Set[str] = set()
        self.running = False
        self.recovery_lock = asyncio.Lock()
        
        # Set up logging
        log_path = Path(self.config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.file_handler = logging.FileHandler(log_path)
        self.file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        logger.addHandler(self.file_handler)
    
    def discover_agents(self) -> List[str]:
        """Discover all active agent tmux windows."""
        try:
            # Get all tmux windows
            result = subprocess.run(
                ["tmux", "list-windows", "-F", "#{window_name}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            windows = result.stdout.strip().split('\n')
            
            # Filter for agent windows
            agent_windows = []
            for window in windows:
                if window.startswith('agent-') or window.endswith('-agent'):
                    agent_windows.append(window)
            
            logger.info(f"Discovered {len(agent_windows)} agent windows: {agent_windows}")
            return agent_windows
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to discover agents: {e}")
            return []
        except FileNotFoundError:
            logger.warning("tmux not found, cannot discover agents")
            return []
    
    def register_agent(self, agent_id: str, window_name: str = None):
        """Register an agent for monitoring."""
        window_name = window_name or agent_id
        
        self.agents[agent_id] = AgentStatus(
            agent_id=agent_id,
            window_name=window_name,
            last_heartbeat=datetime.now(),
            status="alive",
            response_time_ms=0.0
        )
        
        self.monitored_agents.add(agent_id)
        logger.info(f"Registered agent {agent_id} (window: {window_name}) for monitoring")
    
    async def send_heartbeat_request(self, agent_id: str) -> Optional[float]:
        """Send heartbeat request to agent and measure response time."""
        try:
            start_time = time.time()
            
            # Send heartbeat command to tmux window
            agent_status = self.agents[agent_id]
            heartbeat_cmd = 'echo "HEARTBEAT_CHECK:$(date +%s)" && echo "STATUS: OK"'
            
            process = await asyncio.create_subprocess_exec(
                "tmux", "send-keys", "-t", agent_status.window_name,
                heartbeat_cmd, "Enter",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=30.0
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if process.returncode == 0:
                logger.debug(f"Heartbeat response from {agent_id}: {response_time:.2f}ms")
                return response_time
            else:
                logger.warning(f"Heartbeat failed for {agent_id}: {stderr.decode()}")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"Heartbeat timeout for agent {agent_id}")
            return None
        except Exception as e:
            logger.error(f"Heartbeat error for agent {agent_id}: {e}")
            return None
    
    async def check_agent_heartbeat(self, agent_id: str):
        """Check individual agent heartbeat."""
        if agent_id not in self.agents:
            return
        
        agent_status = self.agents[agent_id]
        response_time = await self.send_heartbeat_request(agent_id)
        
        now = datetime.now()
        
        if response_time is not None:
            # Agent responded - update status
            agent_status.last_heartbeat = now
            agent_status.response_time_ms = response_time
            agent_status.consecutive_failures = 0
            
            if agent_status.status != "alive":
                logger.info(f"Agent {agent_id} recovered")
                agent_status.status = "alive"
                agent_status.recovery_attempts = 0
        else:
            # Agent didn't respond
            agent_status.consecutive_failures += 1
            time_since_last = (now - agent_status.last_heartbeat).total_seconds()
            
            if time_since_last > self.config.timeout_threshold:
                if agent_status.status != "timeout":
                    logger.warning(f"Agent {agent_id} timeout detected ({time_since_last:.1f}s since last heartbeat)")
                    agent_status.status = "timeout"
                    await self.handle_agent_timeout(agent_id)
            elif agent_status.consecutive_failures >= self.config.max_consecutive_failures:
                if agent_status.status != "dead":
                    logger.error(f"Agent {agent_id} marked as dead after {agent_status.consecutive_failures} failures")
                    agent_status.status = "dead"
                    await self.handle_agent_failure(agent_id)
    
    async def handle_agent_timeout(self, agent_id: str):
        """Handle agent timeout with recovery actions."""
        async with self.recovery_lock:
            agent_status = self.agents[agent_id]
            
            if agent_status.recovery_attempts >= self.config.max_recovery_attempts:
                logger.error(f"Max recovery attempts reached for agent {agent_id}")
                agent_status.status = "dead"
                return
            
            logger.info(f"Attempting recovery for agent {agent_id} (attempt {agent_status.recovery_attempts + 1})")
            agent_status.status = "recovery"
            agent_status.recovery_attempts += 1
            
            # Try recovery actions
            recovery_success = await self.attempt_agent_recovery(agent_id)
            
            if recovery_success:
                logger.info(f"Recovery successful for agent {agent_id}")
                agent_status.status = "alive"
                agent_status.last_heartbeat = datetime.now()
                agent_status.consecutive_failures = 0
            else:
                logger.error(f"Recovery failed for agent {agent_id}")
                if agent_status.recovery_attempts >= self.config.max_recovery_attempts:
                    agent_status.status = "dead"
    
    async def attempt_agent_recovery(self, agent_id: str) -> bool:
        """Attempt to recover a failed agent."""
        try:
            agent_status = self.agents[agent_id]
            
            # Try to restart the agent window
            logger.info(f"Restarting agent window: {agent_status.window_name}")
            
            # Kill existing window if it exists
            subprocess.run(
                ["tmux", "kill-window", "-t", agent_status.window_name],
                capture_output=True
            )
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Create new window with agent
            subprocess.run(
                ["tmux", "new-window", "-n", agent_status.window_name, 
                 f"cd /Users/bogdan/work/leanvibe-dev/agent-hive && python -m agents.{agent_id.replace('-', '_')}"],
                check=True
            )
            
            # Wait for agent to start
            await asyncio.sleep(5)
            
            # Test heartbeat
            response_time = await self.send_heartbeat_request(agent_id)
            return response_time is not None
            
        except Exception as e:
            logger.error(f"Recovery attempt failed for {agent_id}: {e}")
            return False
    
    async def handle_agent_failure(self, agent_id: str):
        """Handle permanent agent failure."""
        logger.critical(f"Agent {agent_id} has failed permanently")
        
        # Log failure details
        agent_status = self.agents[agent_id]
        failure_report = {
            "agent_id": agent_id,
            "window_name": agent_status.window_name,
            "last_heartbeat": agent_status.last_heartbeat.isoformat(),
            "consecutive_failures": agent_status.consecutive_failures,
            "recovery_attempts": agent_status.recovery_attempts,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.error(f"Failure report: {json.dumps(failure_report, indent=2)}")
        
        # TODO: Send notification to PM or human operator
        # TODO: Trigger emergency protocols
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Starting heartbeat monitoring loop")
        
        while self.running:
            try:
                # Check all registered agents
                tasks = []
                for agent_id in list(self.monitored_agents):
                    tasks.append(self.check_agent_heartbeat(agent_id))
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log status summary
                self.log_status_summary()
                
                # Wait for next interval
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.config.heartbeat_interval)
    
    def log_status_summary(self):
        """Log a summary of all agent statuses."""
        status_counts = {}
        for agent_status in self.agents.values():
            status = agent_status.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_agents = len(self.agents)
        if total_agents > 0:
            alive_count = status_counts.get("alive", 0)
            logger.info(f"Agent status: {alive_count}/{total_agents} alive, {status_counts}")
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report."""
        now = datetime.now()
        
        report = {
            "timestamp": now.isoformat(),
            "total_agents": len(self.agents),
            "monitoring_config": asdict(self.config),
            "agents": {}
        }
        
        for agent_id, agent_status in self.agents.items():
            time_since_last = (now - agent_status.last_heartbeat).total_seconds()
            
            report["agents"][agent_id] = {
                "status": agent_status.status,
                "window_name": agent_status.window_name,
                "last_heartbeat": agent_status.last_heartbeat.isoformat(),
                "seconds_since_last_heartbeat": time_since_last,
                "response_time_ms": agent_status.response_time_ms,
                "consecutive_failures": agent_status.consecutive_failures,
                "recovery_attempts": agent_status.recovery_attempts
            }
        
        return report
    
    async def start(self):
        """Start the heartbeat monitor."""
        if self.running:
            logger.warning("Heartbeat monitor already running")
            return
        
        logger.info("Starting agent heartbeat monitor")
        self.running = True
        
        # Auto-discover agents if none registered
        if not self.monitored_agents:
            discovered_agents = self.discover_agents()
            for window_name in discovered_agents:
                # Extract agent ID from window name
                agent_id = window_name.replace('agent-', '').replace('-agent', '')
                self.register_agent(agent_id, window_name)
        
        # Start monitoring loop
        await self.monitor_loop()
    
    def stop(self):
        """Stop the heartbeat monitor."""
        logger.info("Stopping agent heartbeat monitor")
        self.running = False
    
    def __del__(self):
        """Cleanup when monitor is destroyed."""
        if hasattr(self, 'file_handler'):
            logger.removeHandler(self.file_handler)
            self.file_handler.close()


async def main():
    """Main function for standalone execution."""
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Heartbeat Monitor")
    parser.add_argument("--interval", type=float, default=30.0, help="Heartbeat interval in seconds")
    parser.add_argument("--timeout", type=float, default=900.0, help="Timeout threshold in seconds")
    parser.add_argument("--discover", action="store_true", help="Auto-discover agents")
    parser.add_argument("--agent", action="append", help="Monitor specific agent")
    
    args = parser.parse_args()
    
    # Create configuration
    config = HeartbeatConfig(
        heartbeat_interval=args.interval,
        timeout_threshold=args.timeout
    )
    
    # Create monitor
    monitor = AgentHeartbeatMonitor(config)
    
    # Register specific agents if provided
    if args.agent:
        for agent_id in args.agent:
            monitor.register_agent(agent_id)
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, stopping monitor...")
        monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())