#!/usr/bin/env python3
"""
Coordination Event API
Provides programmatic interface for consuming coordination events
Built on existing accountability infrastructure and coordination_alerts.json
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class CoordinationEvent:
    """Structured representation of a coordination event."""
    event_type: str
    task_id: Optional[str]
    agent_id: Optional[str]
    timestamp: datetime
    data: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> 'CoordinationEvent':
        """Create CoordinationEvent from dictionary."""
        timestamp_str = event_dict.get('timestamp', '')
        try:
            # Handle various timestamp formats
            if 'T' in timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now()
        except ValueError:
            timestamp = datetime.now()
        
        return cls(
            event_type=event_dict.get('type', 'UNKNOWN'),
            task_id=event_dict.get('task_id'),
            agent_id=event_dict.get('agent_id'),
            timestamp=timestamp,
            data=event_dict
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.data

class CoordinationEventConsumer:
    """Event consumer for coordination events."""
    
    def __init__(self, alerts_file: str = "coordination_alerts.json"):
        self.alerts_file = Path(alerts_file)
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.last_position = 0
        self.processed_events: set = set()
    
    def subscribe(self, event_type: str, handler: Callable[[CoordinationEvent], None]):
        """Subscribe to specific event types."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Subscribed handler for {event_type}")
    
    def subscribe_all(self, handler: Callable[[CoordinationEvent], None]):
        """Subscribe to all event types."""
        self.subscribe('*', handler)
    
    async def read_new_events(self) -> List[CoordinationEvent]:
        """Read new events from the alerts file."""
        if not self.alerts_file.exists():
            return []
        
        events = []
        try:
            with open(self.alerts_file, 'r') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            
            # Process lines starting from last position
            for i, line in enumerate(lines[self.last_position:], start=self.last_position):
                if line.strip():
                    try:
                        event_dict = json.loads(line.strip())
                        event = CoordinationEvent.from_dict(event_dict)
                        
                        # Avoid duplicate processing
                        event_id = f"{event.event_type}_{event.timestamp}_{event.task_id}"
                        if event_id not in self.processed_events:
                            events.append(event)
                            self.processed_events.add(event_id)
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse event at line {i}: {e}")
            
            self.last_position = len(lines)
            
        except Exception as e:
            logger.error(f"Error reading events: {e}")
        
        return events
    
    async def process_events(self, events: List[CoordinationEvent]):
        """Process a list of events through registered handlers."""
        for event in events:
            await self._process_single_event(event)
    
    async def _process_single_event(self, event: CoordinationEvent):
        """Process a single event."""
        # Call specific event type handlers
        handlers = self.event_handlers.get(event.event_type, [])
        
        # Also call wildcard handlers
        handlers.extend(self.event_handlers.get('*', []))
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def stream_events(self, poll_interval: float = 1.0) -> AsyncGenerator[CoordinationEvent, None]:
        """Stream events as they arrive."""
        while True:
            events = await self.read_new_events()
            for event in events:
                yield event
            await asyncio.sleep(poll_interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        return {
            "alerts_file": str(self.alerts_file),
            "last_position": self.last_position,
            "processed_events": len(self.processed_events),
            "subscribed_handlers": {
                event_type: len(handlers) 
                for event_type, handlers in self.event_handlers.items()
            }
        }

class CoordinationEventProcessor:
    """High-level event processor with built-in coordination logic."""
    
    def __init__(self, alerts_file: str = "coordination_alerts.json"):
        self.consumer = CoordinationEventConsumer(alerts_file)
        self.response_metrics = {
            "events_processed": 0,
            "notifications_sent": 0,
            "escalations_triggered": 0,
            "errors_encountered": 0
        }
        
        # Set up built-in handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Set up default coordination response handlers."""
        self.consumer.subscribe("COORDINATION_CRISIS", self._handle_crisis)
        self.consumer.subscribe("DEADLINE_WARNING", self._handle_deadline_warning)
        self.consumer.subscribe("AGENT_UNRESPONSIVE", self._handle_unresponsive_agent)
        self.consumer.subscribe("TASK_REASSIGNMENT", self._handle_reassignment)
        self.consumer.subscribe("ESCALATION_TRIGGER", self._handle_escalation)
    
    async def _handle_crisis(self, event: CoordinationEvent):
        """Handle coordination crisis events."""
        logger.warning(f"🚨 CRISIS: {event.task_id} - {event.agent_id}")
        self.response_metrics["escalations_triggered"] += 1
        
        # Trigger appropriate response based on escalation level
        escalation_level = event.data.get('escalation_level', 'unknown')
        
        if escalation_level == 'red':
            await self._send_urgent_notification(
                f"CRITICAL: Coordination crisis for task {event.task_id}"
            )
        else:
            await self._send_notification(
                f"Coordination issue detected for task {event.task_id}"
            )
    
    async def _handle_deadline_warning(self, event: CoordinationEvent):
        """Handle deadline warning events."""
        logger.warning(f"⏰ DEADLINE: {event.task_id}")
        await self._send_notification(
            f"Deadline approaching for task {event.task_id}"
        )
    
    async def _handle_unresponsive_agent(self, event: CoordinationEvent):
        """Handle unresponsive agent events."""
        logger.warning(f"😴 UNRESPONSIVE: {event.agent_id}")
        await self._send_notification(
            f"Agent {event.agent_id} is not responding"
        )
    
    async def _handle_reassignment(self, event: CoordinationEvent):
        """Handle task reassignment events."""
        logger.info(f"🔄 REASSIGNMENT: {event.task_id}")
        await self._send_notification(
            f"Task {event.task_id} has been reassigned"
        )
    
    async def _handle_escalation(self, event: CoordinationEvent):
        """Handle escalation trigger events."""
        logger.warning(f"📈 ESCALATION: {event.data.get('reason', 'Unknown')}")
        self.response_metrics["escalations_triggered"] += 1
    
    async def _send_notification(self, message: str):
        """Send notification via fixed agent communication."""
        try:
            process = await asyncio.create_subprocess_exec(
                'python3', 'scripts/fixed_agent_communication.py',
                '--agent', 'pm-agent',
                '--message', f"[COORDINATION] {message}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.response_metrics["notifications_sent"] += 1
                logger.info(f"✅ Notification sent: {message}")
            else:
                self.response_metrics["errors_encountered"] += 1
                logger.error(f"❌ Notification failed: {stderr.decode()}")
                
        except Exception as e:
            self.response_metrics["errors_encountered"] += 1
            logger.error(f"Error sending notification: {e}")
    
    async def _send_urgent_notification(self, message: str):
        """Send urgent notification with higher priority."""
        urgent_message = f"🚨 URGENT: {message}"
        await self._send_notification(urgent_message)
    
    async def start_processing(self, poll_interval: float = 1.0):
        """Start processing events continuously."""
        logger.info("🚀 Starting coordination event processing...")
        
        try:
            async for event in self.consumer.stream_events(poll_interval):
                self.response_metrics["events_processed"] += 1
                logger.info(f"📨 Processing: {event.event_type} for {event.task_id}")
                await self.consumer._process_single_event(event)
                
        except KeyboardInterrupt:
            logger.info("🛑 Processing stopped by user")
        except Exception as e:
            logger.error(f"❌ Processing error: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        consumer_stats = self.consumer.get_stats()
        return {
            **consumer_stats,
            "response_metrics": self.response_metrics,
            "uptime": time.time()  # Could track actual uptime
        }

# Convenience functions for easy integration

async def consume_coordination_events(
    handler: Callable[[CoordinationEvent], None],
    event_types: Optional[List[str]] = None,
    alerts_file: str = "coordination_alerts.json"
):
    """Simple function to consume coordination events."""
    consumer = CoordinationEventConsumer(alerts_file)
    
    if event_types:
        for event_type in event_types:
            consumer.subscribe(event_type, handler)
    else:
        consumer.subscribe_all(handler)
    
    async for event in consumer.stream_events():
        await consumer._process_single_event(event)

def start_coordination_processor(alerts_file: str = "coordination_alerts.json"):
    """Start the coordination event processor."""
    processor = CoordinationEventProcessor(alerts_file)
    return asyncio.run(processor.start_processing())

# CLI interface for testing
async def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Coordination Event API")
    parser.add_argument(
        '--mode',
        choices=['consume', 'process', 'stats'],
        default='process',
        help='Operation mode'
    )
    parser.add_argument(
        '--alerts-file',
        default='coordination_alerts.json',
        help='Path to alerts file'
    )
    parser.add_argument(
        '--event-types',
        nargs='*',
        help='Specific event types to consume'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'stats':
        consumer = CoordinationEventConsumer(args.alerts_file)
        stats = consumer.get_stats()
        print("📊 Coordination Event Consumer Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
    elif args.mode == 'consume':
        def event_handler(event: CoordinationEvent):
            print(f"📨 Event: {event.event_type} | Task: {event.task_id} | Agent: {event.agent_id}")
            print(f"   Time: {event.timestamp}")
            print(f"   Data: {json.dumps(event.data, indent=2)}")
            print("---")
        
        await consume_coordination_events(
            event_handler,
            args.event_types,
            args.alerts_file
        )
        
    elif args.mode == 'process':
        start_coordination_processor(args.alerts_file)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    asyncio.run(main())