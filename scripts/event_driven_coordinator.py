#!/usr/bin/env python3
"""
Event-Driven Coordinator
Real-time coordination system built on accountability infrastructure
Monitors coordination_alerts.json and triggers intelligent responses
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import time
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('event_coordinator')

class EventDrivenCoordinator:
    """
    Real-time event-driven coordination system.
    Processes events from accountability system and triggers appropriate responses.
    """
    
    def __init__(self, alerts_file: str = "coordination_alerts.json"):
        self.alerts_file = Path(alerts_file)
        self.processed_events: Set[str] = set()
        self.last_file_size = 0
        self.running = False
        self.start_time = datetime.now()
        
        # Event processing statistics
        self.stats = {
            "events_processed": 0,
            "coordination_crises": 0,
            "deadline_warnings": 0,
            "agent_alerts": 0,
            "escalations_triggered": 0,
            "responses_sent": 0,
            "errors_encountered": 0,
            "last_event_time": None
        }
        
        # Response configuration
        self.response_config = {
            "pm_agent_id": "pm-agent",
            "notification_cooldown": 300,  # 5 minutes between similar notifications
            "escalation_thresholds": {
                "red": "CRITICAL",
                "orange": "HIGH", 
                "yellow": "MEDIUM"
            }
        }
        
        # Track notification history to prevent spam
        self.notification_history: Dict[str, datetime] = {}
        
        logger.info("🚀 Event-Driven Coordinator initialized")
        logger.info(f"📡 Monitoring: {self.alerts_file}")
    
    async def start(self):
        """Start the event-driven coordination system."""
        logger.info("🎯 Starting event-driven coordination...")
        
        # Ensure alerts file exists
        if not self.alerts_file.exists():
            logger.warning(f"Creating alerts file: {self.alerts_file}")
            self.alerts_file.touch()
            self.last_file_size = 0
        else:
            self.last_file_size = self.alerts_file.stat().st_size
            logger.info(f"📊 Initial file size: {self.last_file_size} bytes")
        
        self.running = True
        
        # Process any existing events first
        await self._process_existing_events()
        
        # Start main monitoring loop
        try:
            while self.running:
                await self._check_for_new_events()
                await asyncio.sleep(0.5)  # Check every 500ms for responsiveness
                
        except KeyboardInterrupt:
            logger.info("🛑 Coordinator stopped by user")
        except Exception as e:
            logger.error(f"❌ Coordinator error: {e}")
            self.stats["errors_encountered"] += 1
            raise
        finally:
            await self._shutdown()
    
    def stop(self):
        """Stop the coordinator."""
        self.running = False
    
    async def _shutdown(self):
        """Clean shutdown with statistics."""
        uptime = datetime.now() - self.start_time
        logger.info("📊 Event-Driven Coordinator Statistics:")
        logger.info(f"   Uptime: {uptime}")
        logger.info(f"   Events processed: {self.stats['events_processed']}")
        logger.info(f"   Coordination crises: {self.stats['coordination_crises']}")
        logger.info(f"   Deadline warnings: {self.stats['deadline_warnings']}")
        logger.info(f"   Responses sent: {self.stats['responses_sent']}")
        logger.info(f"   Errors: {self.stats['errors_encountered']}")
        logger.info("✅ Coordinator shutdown complete")
    
    async def _process_existing_events(self):
        """Process any existing events in the file."""
        if not self.alerts_file.exists() or self.alerts_file.stat().st_size == 0:
            return
        
        logger.info("🔍 Processing existing events...")
        
        try:
            with open(self.alerts_file, 'r') as f:
                content = f.read()
            
            events = self._parse_events_from_content(content)
            logger.info(f"📋 Found {len(events)} existing events")
            
            for event in events:
                await self._process_event(event)
                
        except Exception as e:
            logger.error(f"Error processing existing events: {e}")
            self.stats["errors_encountered"] += 1
    
    async def _check_for_new_events(self):
        """Check for new events in the alerts file."""
        try:
            if not self.alerts_file.exists():
                return
            
            current_size = self.alerts_file.stat().st_size
            if current_size <= self.last_file_size:
                return  # No new content
            
            # Read new content only
            with open(self.alerts_file, 'r') as f:
                f.seek(self.last_file_size)
                new_content = f.read()
            
            if new_content.strip():
                events = self._parse_events_from_content(new_content)
                logger.info(f"📨 {len(events)} new event(s) detected")
                
                for event in events:
                    await self._process_event(event)
            
            self.last_file_size = current_size
            
        except Exception as e:
            logger.error(f"Error checking for new events: {e}")
            self.stats["errors_encountered"] += 1
    
    def _parse_events_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse events from file content (one JSON object per line)."""
        events = []
        for line in content.strip().split('\n'):
            if line.strip():
                try:
                    event = json.loads(line.strip())
                    event_id = self._get_event_id(event)
                    if event_id not in self.processed_events:
                        events.append(event)
                        self.processed_events.add(event_id)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse event line: {line[:100]}... - {e}")
        return events
    
    def _get_event_id(self, event: Dict[str, Any]) -> str:
        """Generate unique event ID to prevent duplicate processing."""
        return f"{event.get('type', 'unknown')}_{event.get('timestamp', '')}_{event.get('task_id', '')}"
    
    async def _process_event(self, event: Dict[str, Any]):
        """Process a single coordination event."""
        event_type = event.get('type', 'UNKNOWN')
        timestamp = event.get('timestamp', '')
        task_id = event.get('task_id', 'unknown')
        agent_id = event.get('agent_id', 'unknown')
        
        self.stats["events_processed"] += 1
        self.stats["last_event_time"] = datetime.now()
        
        logger.info(f"🎯 Processing {event_type} | Task: {task_id} | Agent: {agent_id}")
        
        # Route to appropriate handler
        try:
            if event_type == "COORDINATION_CRISIS":
                await self._handle_coordination_crisis(event)
            elif event_type == "DEADLINE_WARNING":
                await self._handle_deadline_warning(event)
            elif event_type == "AGENT_UNRESPONSIVE":
                await self._handle_agent_unresponsive(event)
            elif event_type == "TASK_REASSIGNMENT":
                await self._handle_task_reassignment(event)
            elif event_type == "ESCALATION_TRIGGER":
                await self._handle_escalation_trigger(event)
            elif event_type == "EMERGENCY_PROTOCOL":
                await self._handle_emergency_protocol(event)
            else:
                logger.warning(f"⚠️ Unknown event type: {event_type}")
                await self._handle_unknown_event(event)
                
        except Exception as e:
            logger.error(f"❌ Error processing {event_type} event: {e}")
            self.stats["errors_encountered"] += 1
    
    async def _handle_coordination_crisis(self, event: Dict[str, Any]):
        """Handle coordination crisis events - highest priority."""
        self.stats["coordination_crises"] += 1
        
        task_id = event.get('task_id', 'unknown')
        agent_id = event.get('agent_id', 'unknown')
        escalation_level = event.get('escalation_level', 'unknown')
        description = event.get('description', 'No description')
        
        logger.critical(f"🚨 COORDINATION CRISIS | Level: {escalation_level} | Task: {task_id}")
        
        # Critical response protocol
        priority = self.response_config["escalation_thresholds"].get(escalation_level, "HIGH")
        
        responses = []
        
        if escalation_level == 'red':
            # CRITICAL - Immediate escalation
            responses.extend([
                self._send_urgent_notification(
                    f"🚨 CRITICAL COORDINATION CRISIS: Task {task_id} in crisis state. "
                    f"Agent {agent_id} unresponsive. Immediate intervention required. "
                    f"Details: {description}"
                ),
                self._ping_agent(agent_id, f"URGENT: Coordination crisis for task {task_id}"),
                self._log_crisis_event(event, "CRITICAL")
            ])
            self.stats["escalations_triggered"] += 1
            
        elif escalation_level in ['orange', 'yellow']:
            # WARNING - Monitor and alert
            responses.extend([
                self._send_notification(
                    f"⚠️ Coordination Issue: Task {task_id} needs attention. "
                    f"Agent {agent_id} status unclear. Details: {description}"
                ),
                self._send_agent_reminder(agent_id, task_id),
                self._log_crisis_event(event, "WARNING")
            ])
        
        # Execute all responses concurrently
        await asyncio.gather(*responses, return_exceptions=True)
    
    async def _handle_deadline_warning(self, event: Dict[str, Any]):
        """Handle deadline warning events."""
        self.stats["deadline_warnings"] += 1
        
        task_id = event.get('task_id', 'unknown')
        agent_id = event.get('agent_id', 'unknown')
        time_remaining = event.get('time_remaining', 'unknown')
        
        logger.warning(f"⏰ DEADLINE WARNING | Task: {task_id} | Time: {time_remaining}")
        
        # Deadline response protocol
        await asyncio.gather(
            self._send_notification(
                f"⏰ Deadline approaching for task {task_id}. "
                f"Time remaining: {time_remaining}. "
                f"Agent {agent_id} should prioritize completion."
            ),
            self._send_agent_reminder(
                agent_id, 
                f"Deadline approaching for task {task_id} - time remaining: {time_remaining}"
            ),
            return_exceptions=True
        )
    
    async def _handle_agent_unresponsive(self, event: Dict[str, Any]):
        """Handle unresponsive agent events."""
        self.stats["agent_alerts"] += 1
        
        agent_id = event.get('agent_id', 'unknown')
        last_activity = event.get('last_activity', 'unknown')
        
        logger.warning(f"😴 AGENT UNRESPONSIVE | Agent: {agent_id} | Last: {last_activity}")
        
        await asyncio.gather(
            self._send_notification(f"Agent {agent_id} unresponsive since {last_activity}"),
            self._ping_agent(agent_id, "Health check - please respond"),
            return_exceptions=True
        )
    
    async def _handle_task_reassignment(self, event: Dict[str, Any]):
        """Handle task reassignment events."""
        task_id = event.get('task_id', 'unknown')
        old_agent = event.get('old_agent', 'unknown')
        new_agent = event.get('new_agent', 'unknown')
        
        logger.info(f"🔄 TASK REASSIGNMENT | Task: {task_id} | {old_agent} → {new_agent}")
        
        await asyncio.gather(
            self._send_notification(f"Task {task_id} reassigned from {old_agent} to {new_agent}"),
            self._notify_new_assignment(new_agent, task_id),
            return_exceptions=True
        )
    
    async def _handle_escalation_trigger(self, event: Dict[str, Any]):
        """Handle escalation trigger events."""
        escalation_level = event.get('escalation_level', 'unknown')
        reason = event.get('reason', 'No reason provided')
        
        logger.warning(f"📈 ESCALATION | Level: {escalation_level} | Reason: {reason}")
        self.stats["escalations_triggered"] += 1
        
        await self._send_notification(f"Escalation triggered: {escalation_level} - {reason}")
    
    async def _handle_emergency_protocol(self, event: Dict[str, Any]):
        """Handle emergency protocol events."""
        protocol = event.get('protocol', 'unknown')
        details = event.get('details', {})
        
        logger.critical(f"🚨 EMERGENCY PROTOCOL | Protocol: {protocol}")
        
        await self._send_urgent_notification(
            f"🚨 EMERGENCY: Protocol {protocol} activated. "
            f"Details: {json.dumps(details)}"
        )
    
    async def _handle_unknown_event(self, event: Dict[str, Any]):
        """Handle unknown event types."""
        event_type = event.get('type', 'UNKNOWN')
        logger.info(f"❓ Unknown event type: {event_type}")
        
        # Log for investigation
        await self._send_notification(f"Unknown coordination event: {event_type}")
    
    async def _send_notification(self, message: str):
        """Send notification to PM agent."""
        # Check cooldown to prevent spam
        if self._is_in_cooldown("notification", message):
            return
        
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            full_message = f"[COORDINATION {timestamp}] {message}"
            
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', self.response_config["pm_agent_id"],
                '--message', full_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ PM notification sent: {message[:50]}...")
                self.stats["responses_sent"] += 1
                self._record_notification("notification", message)
            else:
                logger.error(f"❌ PM notification failed: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            self.stats["errors_encountered"] += 1
    
    async def _send_urgent_notification(self, message: str):
        """Send urgent notification with priority marking."""
        urgent_message = f"🚨 URGENT: {message}"
        await self._send_notification(urgent_message)
    
    async def _send_agent_reminder(self, agent_id: str, task_info: str):
        """Send reminder to specific agent."""
        try:
            reminder = f"[REMINDER] {task_info}"
            
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', agent_id,
                '--message', reminder,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"✅ Reminder sent to {agent_id}")
                self.stats["responses_sent"] += 1
            else:
                logger.warning(f"⚠️ Agent reminder failed for {agent_id}")
                
        except Exception as e:
            logger.error(f"Error sending agent reminder: {e}")
    
    async def _ping_agent(self, agent_id: str, message: str):
        """Ping agent for responsiveness."""
        try:
            ping_message = f"[PING] {message}"
            
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', agent_id,
                '--message', ping_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"📡 Ping sent to {agent_id}")
            else:
                logger.warning(f"📡 Ping failed for {agent_id}")
                
        except Exception as e:
            logger.error(f"Error pinging agent: {e}")
    
    async def _notify_new_assignment(self, agent_id: str, task_id: str):
        """Notify agent of new task assignment."""
        assignment_message = f"[NEW TASK] You have been assigned task {task_id}. Please acknowledge."
        await self._send_agent_reminder(agent_id, assignment_message)
    
    async def _log_crisis_event(self, event: Dict[str, Any], severity: str):
        """Log crisis event for audit trail."""
        crisis_log = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "original_event": event,
            "coordinator_response": "Event processed and notifications sent"
        }
        
        crisis_log_file = Path("coordination_crisis_log.json")
        
        try:
            with open(crisis_log_file, 'a') as f:
                json.dump(crisis_log, f)
                f.write('\n')
            logger.info(f"📝 Crisis event logged: {severity}")
        except Exception as e:
            logger.error(f"Error logging crisis event: {e}")
    
    def _is_in_cooldown(self, notification_type: str, message: str) -> bool:
        """Check if notification is in cooldown period."""
        key = f"{notification_type}_{hash(message[:50])}"
        last_sent = self.notification_history.get(key)
        
        if last_sent:
            time_since = datetime.now() - last_sent
            if time_since.total_seconds() < self.response_config["notification_cooldown"]:
                return True
        
        return False
    
    def _record_notification(self, notification_type: str, message: str):
        """Record notification timestamp."""
        key = f"{notification_type}_{hash(message[:50])}"
        self.notification_history[key] = datetime.now()
    
    def get_status(self) -> Dict[str, Any]:
        """Get coordinator status."""
        uptime = datetime.now() - self.start_time
        return {
            "running": self.running,
            "uptime_seconds": uptime.total_seconds(),
            "alerts_file": str(self.alerts_file),
            "file_size": self.last_file_size,
            "processed_events": len(self.processed_events),
            "statistics": self.stats,
            "last_check": datetime.now().isoformat()
        }

# Signal handlers for graceful shutdown
def signal_handler(coordinator):
    """Handle shutdown signals."""
    def handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, shutting down...")
        coordinator.stop()
    return handler

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Event-Driven Coordination System")
    parser.add_argument(
        '--alerts-file',
        default='coordination_alerts.json',
        help='Path to coordination alerts file'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show coordinator status and exit'
    )
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode with verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.test_mode:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🧪 Running in test mode")
    
    coordinator = EventDrivenCoordinator(args.alerts_file)
    
    if args.status:
        status = coordinator.get_status()
        print("📊 Event-Driven Coordinator Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        return
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler(coordinator))
    signal.signal(signal.SIGTERM, signal_handler(coordinator))
    
    logger.info("🚀 Event-Driven Coordinator starting...")
    logger.info("📋 Press Ctrl+C to stop")
    
    try:
        await coordinator.start()
    except Exception as e:
        logger.error(f"❌ Coordinator failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())