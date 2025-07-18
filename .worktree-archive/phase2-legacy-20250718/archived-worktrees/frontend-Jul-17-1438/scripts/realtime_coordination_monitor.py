#!/usr/bin/env python3
"""
Real-time Coordination Event Monitor
Monitors coordination_alerts.json for events and triggers appropriate responses
Event-driven coordination system built on existing accountability infrastructure
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class CoordinationEventHandler(FileSystemEventHandler):
    """Event handler for coordination alerts file changes."""
    
    def __init__(self, monitor: 'RealTimeCoordinationMonitor'):
        self.monitor = monitor
        self.last_processed_time = datetime.now()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.src_path.endswith('coordination_alerts.json'):
            asyncio.create_task(self.monitor.process_new_events())

class RealTimeCoordinationMonitor:
    """Real-time coordination event monitor and response system."""
    
    def __init__(self, alerts_file: str = "coordination_alerts.json"):
        self.alerts_file = Path(alerts_file)
        self.processed_events: set = set()
        self.response_handlers = {}
        self.running = False
        self.observer = None
        self.last_file_size = 0
        
        # Initialize response handlers
        self._setup_response_handlers()
    
    def _setup_response_handlers(self):
        """Set up response handlers for different event types."""
        self.response_handlers = {
            "COORDINATION_CRISIS": self._handle_coordination_crisis,
            "DEADLINE_WARNING": self._handle_deadline_warning,
            "AGENT_UNRESPONSIVE": self._handle_agent_unresponsive,
            "TASK_REASSIGNMENT": self._handle_task_reassignment,
            "ESCALATION_TRIGGER": self._handle_escalation_trigger,
            "EMERGENCY_PROTOCOL": self._handle_emergency_protocol
        }
    
    async def start_monitoring(self):
        """Start real-time monitoring of coordination events."""
        logger.info("🚀 Starting real-time coordination event monitoring...")
        
        if not self.alerts_file.exists():
            logger.warning(f"Alerts file {self.alerts_file} does not exist - creating it")
            self.alerts_file.touch()
        
        self.running = True
        
        # Set up file system watcher
        event_handler = CoordinationEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.alerts_file.parent), recursive=False)
        self.observer.start()
        
        logger.info(f"📡 Monitoring {self.alerts_file} for real-time coordination events")
        
        # Process any existing events
        await self.process_new_events()
        
        try:
            while self.running:
                await asyncio.sleep(1)  # Keep the event loop alive
        except KeyboardInterrupt:
            logger.info("🛑 Stopping coordination monitoring...")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop the monitoring system."""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        logger.info("✅ Coordination monitoring stopped")
    
    async def process_new_events(self):
        """Process new events from the alerts file."""
        try:
            if not self.alerts_file.exists():
                return
            
            current_size = self.alerts_file.stat().st_size
            if current_size <= self.last_file_size:
                return  # No new content
            
            # Read new events
            with open(self.alerts_file, 'r') as f:
                content = f.read()
            
            self.last_file_size = current_size
            
            # Parse events (file contains JSON objects, one per line)
            events = []
            for line in content.strip().split('\n'):
                if line.strip():
                    try:
                        event = json.loads(line.strip())
                        event_id = self._get_event_id(event)
                        if event_id not in self.processed_events:
                            events.append(event)
                            self.processed_events.add(event_id)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse event line: {line}")
            
            # Process new events
            for event in events:
                await self._process_event(event)
                
        except Exception as e:
            logger.error(f"Error processing events: {e}")
    
    def _get_event_id(self, event: Dict[str, Any]) -> str:
        """Generate unique event ID."""
        return f"{event.get('type', 'unknown')}_{event.get('timestamp', '')}_{event.get('task_id', '')}"
    
    async def _process_event(self, event: Dict[str, Any]):
        """Process a single coordination event."""
        event_type = event.get('type', 'UNKNOWN')
        timestamp = event.get('timestamp', '')
        
        logger.info(f"📨 Processing event: {event_type} at {timestamp}")
        
        # Call appropriate handler
        handler = self.response_handlers.get(event_type)
        if handler:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error handling {event_type} event: {e}")
        else:
            logger.warning(f"No handler for event type: {event_type}")
    
    async def _handle_coordination_crisis(self, event: Dict[str, Any]):
        """Handle coordination crisis events."""
        task_id = event.get('task_id', 'unknown')
        agent_id = event.get('agent_id', 'unknown')
        escalation_level = event.get('escalation_level', 'unknown')
        
        logger.warning(f"🚨 COORDINATION CRISIS: Task {task_id}, Agent {agent_id}, Level {escalation_level}")
        
        # Immediate actions for coordination crisis
        actions = []
        
        if escalation_level == 'red':
            # Critical escalation - immediate intervention
            actions.extend([
                self._notify_pm_agent(f"CRITICAL: Coordination crisis for task {task_id}"),
                self._attempt_agent_ping(agent_id),
                self._trigger_emergency_reassignment(task_id, agent_id)
            ])
        elif escalation_level in ['orange', 'yellow']:
            # Warning escalation - monitoring and gentle intervention
            actions.extend([
                self._notify_pm_agent(f"WARNING: Coordination issue for task {task_id}"),
                self._send_agent_reminder(agent_id, task_id)
            ])
        
        # Execute actions concurrently
        await asyncio.gather(*actions, return_exceptions=True)
    
    async def _handle_deadline_warning(self, event: Dict[str, Any]):
        """Handle deadline warning events."""
        task_id = event.get('task_id', 'unknown')
        agent_id = event.get('agent_id', 'unknown')
        time_remaining = event.get('time_remaining', 'unknown')
        
        logger.warning(f"⏰ DEADLINE WARNING: Task {task_id}, Agent {agent_id}, Time: {time_remaining}")
        
        await asyncio.gather(
            self._notify_pm_agent(f"Deadline approaching for task {task_id}"),
            self._send_agent_reminder(agent_id, task_id),
            return_exceptions=True
        )
    
    async def _handle_agent_unresponsive(self, event: Dict[str, Any]):
        """Handle unresponsive agent events."""
        agent_id = event.get('agent_id', 'unknown')
        last_activity = event.get('last_activity', 'unknown')
        
        logger.warning(f"😴 AGENT UNRESPONSIVE: {agent_id}, Last activity: {last_activity}")
        
        await asyncio.gather(
            self._attempt_agent_ping(agent_id),
            self._notify_pm_agent(f"Agent {agent_id} is unresponsive"),
            return_exceptions=True
        )
    
    async def _handle_task_reassignment(self, event: Dict[str, Any]):
        """Handle task reassignment events."""
        task_id = event.get('task_id', 'unknown')
        old_agent = event.get('old_agent', 'unknown')
        new_agent = event.get('new_agent', 'unknown')
        
        logger.info(f"🔄 TASK REASSIGNMENT: {task_id} from {old_agent} to {new_agent}")
        
        await asyncio.gather(
            self._notify_pm_agent(f"Task {task_id} reassigned from {old_agent} to {new_agent}"),
            self._notify_agent_assignment(new_agent, task_id),
            return_exceptions=True
        )
    
    async def _handle_escalation_trigger(self, event: Dict[str, Any]):
        """Handle escalation trigger events."""
        escalation_level = event.get('escalation_level', 'unknown')
        reason = event.get('reason', 'No reason provided')
        
        logger.warning(f"📈 ESCALATION TRIGGER: Level {escalation_level} - {reason}")
        
        await self._notify_pm_agent(f"Escalation triggered: {escalation_level} - {reason}")
    
    async def _handle_emergency_protocol(self, event: Dict[str, Any]):
        """Handle emergency protocol events."""
        protocol = event.get('protocol', 'unknown')
        details = event.get('details', {})
        
        logger.critical(f"🚨 EMERGENCY PROTOCOL: {protocol}")
        
        # Emergency protocols require immediate PM agent notification
        await self._notify_pm_agent(
            f"EMERGENCY: Protocol {protocol} activated. Details: {json.dumps(details)}"
        )
    
    async def _notify_pm_agent(self, message: str):
        """Send notification to PM agent via fixed communication system."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            full_message = f"[COORDINATION EVENT {timestamp}] {message}"
            
            # Use fixed agent communication
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', 'pm-agent',
                '--message', full_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ PM agent notified: {message}")
            else:
                logger.error(f"❌ Failed to notify PM agent: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error notifying PM agent: {e}")
    
    async def _send_agent_reminder(self, agent_id: str, task_id: str):
        """Send reminder to specific agent."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            reminder = f"[COORDINATION REMINDER {timestamp}] Please provide status update for task {task_id}"
            
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', agent_id,
                '--message', reminder,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ Reminder sent to {agent_id}")
            else:
                logger.warning(f"⚠️ Could not reach agent {agent_id}: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error sending reminder to {agent_id}: {e}")
    
    async def _attempt_agent_ping(self, agent_id: str):
        """Attempt to ping agent for responsiveness check."""
        try:
            ping_message = f"[PING {datetime.now().strftime('%H:%M:%S')}] Health check - please respond with your current status"
            
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', agent_id,
                '--message', ping_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"📡 Ping sent to {agent_id}")
            else:
                logger.warning(f"📡 Ping failed for {agent_id}")
                
        except Exception as e:
            logger.error(f"Error pinging {agent_id}: {e}")
    
    async def _trigger_emergency_reassignment(self, task_id: str, failed_agent_id: str):
        """Trigger emergency task reassignment."""
        try:
            logger.warning(f"🔄 Triggering emergency reassignment for task {task_id}")
            
            # Use accountability system for reassignment
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/automated_accountability.py',
                '--reassign', task_id,
                '--reason', f'Agent {failed_agent_id} unresponsive',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ Emergency reassignment initiated for {task_id}")
            else:
                logger.error(f"❌ Emergency reassignment failed: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error triggering emergency reassignment: {e}")
    
    async def _notify_agent_assignment(self, agent_id: str, task_id: str):
        """Notify agent of new task assignment."""
        try:
            assignment_message = f"[NEW ASSIGNMENT] You have been assigned task {task_id}. Please acknowledge and begin work."
            
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', agent_id,
                '--message', assignment_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ Assignment notification sent to {agent_id}")
            else:
                logger.warning(f"⚠️ Assignment notification failed for {agent_id}")
                
        except Exception as e:
            logger.error(f"Error notifying assignment to {agent_id}: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "is_running": self.running,
            "alerts_file": str(self.alerts_file),
            "processed_events_count": len(self.processed_events),
            "file_size": self.last_file_size,
            "handlers_registered": len(self.response_handlers),
            "start_time": getattr(self, 'start_time', None)
        }

async def main():
    """Main entry point for the coordination monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-time Coordination Event Monitor")
    parser.add_argument(
        '--alerts-file', 
        default='coordination_alerts.json',
        help='Path to coordination alerts file'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show monitoring statistics and exit'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    monitor = RealTimeCoordinationMonitor(args.alerts_file)
    
    if args.stats:
        stats = monitor.get_monitoring_stats()
        print("📊 Real-time Coordination Monitor Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        return
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped by user")
    except Exception as e:
        logger.error(f"❌ Monitoring error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())