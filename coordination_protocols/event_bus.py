#!/usr/bin/env python3
"""
Event Bus Infrastructure for Multi-Agent Coordination
Foundation Epic Evolution - Performance Agent Event Integration

Watches event files for changes, parses/validates JSON events, routes events 
to appropriate handlers, and supports event subscription patterns.

Integration with existing coordination protocols for performance agent's
accountability system events (COORDINATION_CRISIS, DEADLINE_WARNING).
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Supported event types from performance agent accountability system."""
    COORDINATION_CRISIS = "COORDINATION_CRISIS"
    DEADLINE_WARNING = "DEADLINE_WARNING"
    TASK_ESCALATION = "TASK_ESCALATION"
    AGENT_STATUS_CHANGE = "AGENT_STATUS_CHANGE"
    PR_MERGE_EVENT = "PR_MERGE_EVENT"
    QUALITY_GATE_FAILURE = "QUALITY_GATE_FAILURE"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class EventPriority(Enum):
    """Event priority levels for routing and handling."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class EventMessage:
    """Structured event message for coordination."""
    event_id: str
    event_type: EventType
    priority: EventPriority
    timestamp: datetime
    source_agent: str
    source_file: str
    payload: Dict[str, Any]
    tags: Dict[str, str]
    processed: bool = False
    retry_count: int = 0


@dataclass
class EventHandler:
    """Event handler registration."""
    handler_id: str
    handler_func: Callable
    event_types: List[EventType]
    priority_filter: Optional[List[EventPriority]]
    active: bool = True


class EventFileWatcher(FileSystemEventHandler):
    """File system watcher for event files."""
    
    def __init__(self, event_bus: 'EventBus'):
        super().__init__()
        self.event_bus = event_bus
        self.watched_files: Set[str] = set()
        self.file_checksums: Dict[str, str] = {}
    
    def add_watched_file(self, file_path: str):
        """Add file to watch list."""
        resolved_path = str(Path(file_path).resolve())
        self.watched_files.add(resolved_path)
        logger.debug(f"Added file to watch list: {resolved_path}")
    
    def _calculate_file_checksum(self, file_path: str) -> Optional[str]:
        """Calculate file checksum to detect real changes."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return None
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = str(Path(event.src_path).resolve())
        if file_path not in self.watched_files:
            return
        
        # Check if file actually changed (avoid duplicate events)
        current_checksum = self._calculate_file_checksum(file_path)
        if current_checksum is None:
            return
        
        previous_checksum = self.file_checksums.get(file_path)
        if current_checksum == previous_checksum:
            return  # No real change
        
        self.file_checksums[file_path] = current_checksum
        
        logger.debug(f"Detected real change in event file: {file_path}")
        
        # Schedule event processing
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.event_bus._process_event_file(file_path))
        else:
            logger.warning(f"Event loop not running, cannot process {file_path}")


class EventBus:
    """
    Event Bus Infrastructure for multi-agent coordination.
    
    Provides file watching, event parsing/validation, routing, and 
    subscription patterns for performance agent accountability system.
    """
    
    def __init__(self, config_path: str = ".claude/event_bus_config.json"):
        """Initialize event bus."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Event handling infrastructure
        self.handlers: Dict[str, EventHandler] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.processed_events: Dict[str, EventMessage] = {}
        
        # File watching
        self.file_watcher = EventFileWatcher(self)
        self.observer = Observer()
        
        # State management
        self.active = False
        self.processing_task: Optional[asyncio.Task] = None
        self.stats = {
            "events_processed": 0,
            "events_failed": 0,
            "handlers_executed": 0,
            "files_watched": 0
        }
        
        # Discover and setup event files
        self.event_files = self._discover_event_files()
        
        logger.info(f"EventBus initialized with {len(self.event_files)} event files")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load event bus configuration."""
        default_config = {
            "event_file_patterns": [
                "**/coordination_alerts.json",
                "**/accountability_events.json", 
                "**/*_events.json",
                ".claude/events/*.json",
                "coordination_protocols/events/*.json"
            ],
            "watch_directories": [
                ".claude",
                "coordination_protocols", 
                "worktrees",
                "."
            ],
            "event_retention_hours": 48,
            "processing_batch_size": 20,
            "max_retry_attempts": 3,
            "debounce_interval_ms": 500
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.error(f"Failed to load event bus config: {e}")
        
        return default_config
    
    def _discover_event_files(self) -> List[Path]:
        """Discover existing event files."""
        files = []
        
        for pattern in self.config["event_file_patterns"]:
            try:
                import glob
                for file_path in glob.glob(pattern, recursive=True):
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        files.append(path)
                        logger.debug(f"Found event file: {path}")
            except Exception as e:
                logger.warning(f"Error discovering files with pattern {pattern}: {e}")
        
        return files
    
    async def start_event_bus(self) -> None:
        """Start event bus processing."""
        if self.active:
            logger.warning("Event bus already active")
            return
        
        try:
            logger.info("Starting event bus...")
            
            # Setup file watching
            await self._setup_file_watching()
            
            # Start event processing
            self.processing_task = asyncio.create_task(self._event_processing_loop())
            
            # Process existing event files
            await self._process_existing_event_files()
            
            self.active = True
            self.stats["files_watched"] = len(self.event_files)
            
            logger.info(f"Event bus started successfully, watching {len(self.event_files)} files")
            
        except Exception as e:
            logger.error(f"Failed to start event bus: {e}")
            raise
    
    async def stop_event_bus(self) -> None:
        """Stop event bus processing."""
        if not self.active:
            logger.warning("Event bus not active")
            return
        
        try:
            logger.info("Stopping event bus...")
            
            self.active = False
            
            # Stop file watching
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
            
            # Stop processing task
            if self.processing_task:
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            
            # Process remaining events
            await self._flush_event_queue()
            
            logger.info("Event bus stopped")
            
        except Exception as e:
            logger.error(f"Error stopping event bus: {e}")
            raise
    
    async def _setup_file_watching(self) -> None:
        """Setup file system watching for event files."""
        try:
            # Add discovered event files to watcher
            for file_path in self.event_files:
                self.file_watcher.add_watched_file(str(file_path))
            
            # Watch configured directories for new event files
            for dir_path in self.config["watch_directories"]:
                watch_dir = Path(dir_path)
                if watch_dir.exists():
                    self.observer.schedule(self.file_watcher, str(watch_dir), recursive=True)
                    logger.debug(f"Watching directory: {watch_dir}")
            
            # Start observer
            self.observer.start()
            logger.info("File system watching started")
            
        except Exception as e:
            logger.error(f"Failed to setup file watching: {e}")
            raise
    
    async def _process_existing_event_files(self) -> None:
        """Process all existing event files for initial state."""
        for file_path in self.event_files:
            await self._process_event_file(str(file_path))
    
    async def _process_event_file(self, file_path: str) -> None:
        """Process a single event file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return
            
            logger.debug(f"Processing event file: {file_path}")
            
            with open(path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return
            
            # Parse JSON events
            events_data = []
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    events_data = data
                elif isinstance(data, dict):
                    if "events" in data:
                        events_data = data["events"]
                    else:
                        events_data = [data]  # Single event
                else:
                    logger.warning(f"Unexpected data format in {file_path}")
                    return
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in {file_path}: {e}")
                return
            
            # Validate and queue events
            for event_data in events_data:
                event_message = await self._validate_and_create_event(event_data, file_path)
                if event_message:
                    await self._queue_event(event_message)
            
        except Exception as e:
            logger.error(f"Error processing event file {file_path}: {e}")
    
    async def _validate_and_create_event(self, event_data: Dict[str, Any], source_file: str) -> Optional[EventMessage]:
        """Validate event data and create EventMessage."""
        try:
            # Extract required fields
            event_type_str = event_data.get("event_type", event_data.get("type", "SYSTEM_ALERT"))
            
            # Validate event type
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                logger.warning(f"Unknown event type: {event_type_str}, defaulting to SYSTEM_ALERT")
                event_type = EventType.SYSTEM_ALERT
            
            # Extract priority
            priority_str = event_data.get("priority", "medium")
            try:
                priority = EventPriority(priority_str.lower())
            except ValueError:
                logger.warning(f"Unknown priority: {priority_str}, defaulting to medium")
                priority = EventPriority.MEDIUM
            
            # Generate event ID if not present
            event_id = event_data.get("event_id", event_data.get("id", f"evt_{int(time.time()*1000)}"))
            
            # Parse timestamp
            timestamp_str = event_data.get("timestamp", datetime.now().isoformat())
            try:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.now()
            except ValueError:
                timestamp = datetime.now()
            
            # Extract source agent
            source_agent = event_data.get("source_agent", event_data.get("agent_id", "unknown"))
            
            # Build event message
            event_message = EventMessage(
                event_id=event_id,
                event_type=event_type,
                priority=priority,
                timestamp=timestamp,
                source_agent=source_agent,
                source_file=source_file,
                payload=event_data,
                tags=event_data.get("tags", {}),
                processed=False,
                retry_count=0
            )
            
            return event_message
            
        except Exception as e:
            logger.error(f"Error validating event data: {e}")
            return None
    
    async def _queue_event(self, event_message: EventMessage) -> None:
        """Queue event for processing."""
        try:
            # Check for duplicates
            if event_message.event_id in self.processed_events:
                logger.debug(f"Duplicate event ignored: {event_message.event_id}")
                return
            
            # Add to queue
            await self.event_queue.put(event_message)
            logger.debug(f"Queued event: {event_message.event_type.value} from {event_message.source_agent}")
            
        except asyncio.QueueFull:
            logger.error(f"Event queue full, dropping event: {event_message.event_id}")
            self.stats["events_failed"] += 1
        except Exception as e:
            logger.error(f"Error queuing event: {e}")
            self.stats["events_failed"] += 1
    
    async def _event_processing_loop(self) -> None:
        """Main event processing loop."""
        while self.active:
            try:
                # Get event from queue
                try:
                    event_message = await asyncio.wait_for(
                        self.event_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process event
                success = await self._process_event(event_message)
                
                if success:
                    self.stats["events_processed"] += 1
                    self.processed_events[event_message.event_id] = event_message
                else:
                    self.stats["events_failed"] += 1
                    
                    # Retry logic
                    if event_message.retry_count < self.config["max_retry_attempts"]:
                        event_message.retry_count += 1
                        await asyncio.sleep(1)  # Brief delay before retry
                        await self.event_queue.put(event_message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _process_event(self, event_message: EventMessage) -> bool:
        """Process single event through registered handlers."""
        try:
            logger.info(f"Processing event: {event_message.event_type.value} from {event_message.source_agent}")
            
            # Find matching handlers
            matching_handlers = []
            for handler in self.handlers.values():
                if not handler.active:
                    continue
                
                # Check event type match
                if event_message.event_type not in handler.event_types:
                    continue
                
                # Check priority filter
                if (handler.priority_filter and 
                    event_message.priority not in handler.priority_filter):
                    continue
                
                matching_handlers.append(handler)
            
            if not matching_handlers:
                logger.debug(f"No handlers found for event: {event_message.event_id}")
                return True  # Not an error, just no handlers
            
            # Execute handlers
            handler_results = []
            for handler in matching_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler.handler_func):
                        result = await handler.handler_func(event_message)
                    else:
                        result = handler.handler_func(event_message)
                    
                    handler_results.append(True)
                    self.stats["handlers_executed"] += 1
                    logger.debug(f"Handler {handler.handler_id} executed successfully")
                    
                except Exception as e:
                    logger.error(f"Handler {handler.handler_id} failed: {e}")
                    handler_results.append(False)
            
            # Mark as processed
            event_message.processed = True
            
            # Return success if any handler succeeded
            return any(handler_results)
            
        except Exception as e:
            logger.error(f"Error processing event {event_message.event_id}: {e}")
            return False
    
    async def _flush_event_queue(self) -> None:
        """Process remaining events in queue."""
        while not self.event_queue.empty():
            try:
                event_message = self.event_queue.get_nowait()
                await self._process_event(event_message)
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error flushing event queue: {e}")
    
    def register_handler(
        self, 
        handler_id: str, 
        handler_func: Callable, 
        event_types: List[Union[EventType, str]],
        priority_filter: Optional[List[EventPriority]] = None
    ) -> None:
        """
        Register event handler.
        
        Args:
            handler_id: Unique handler identifier
            handler_func: Function to handle events (sync or async)
            event_types: List of event types to handle
            priority_filter: Optional priority filter
        """
        # Convert string event types to EventType enums
        processed_event_types = []
        for event_type in event_types:
            if isinstance(event_type, str):
                try:
                    processed_event_types.append(EventType(event_type))
                except ValueError:
                    logger.warning(f"Unknown event type: {event_type}")
            else:
                processed_event_types.append(event_type)
        
        handler = EventHandler(
            handler_id=handler_id,
            handler_func=handler_func,
            event_types=processed_event_types,
            priority_filter=priority_filter,
            active=True
        )
        
        self.handlers[handler_id] = handler
        logger.info(f"Registered handler: {handler_id} for {len(processed_event_types)} event types")
    
    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister event handler."""
        if handler_id in self.handlers:
            del self.handlers[handler_id]
            logger.info(f"Unregistered handler: {handler_id}")
            return True
        return False
    
    def get_handler_status(self, handler_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific handler."""
        if handler_id not in self.handlers:
            return None
        
        handler = self.handlers[handler_id]
        return {
            "handler_id": handler.handler_id,
            "active": handler.active,
            "event_types": [et.value for et in handler.event_types],
            "priority_filter": [pf.value for pf in handler.priority_filter] if handler.priority_filter else None
        }
    
    async def publish_event(
        self, 
        event_type: Union[EventType, str],
        payload: Dict[str, Any],
        source_agent: str = "event_bus",
        priority: EventPriority = EventPriority.MEDIUM,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Publish event directly to bus.
        
        Args:
            event_type: Type of event
            payload: Event payload data
            source_agent: Source agent identifier
            priority: Event priority
            tags: Optional metadata tags
            
        Returns:
            Event ID
        """
        if isinstance(event_type, str):
            try:
                event_type = EventType(event_type)
            except ValueError:
                logger.warning(f"Unknown event type: {event_type}, using SYSTEM_ALERT")
                event_type = EventType.SYSTEM_ALERT
        
        event_message = EventMessage(
            event_id=f"pub_{int(time.time()*1000)}",
            event_type=event_type,
            priority=priority,
            timestamp=datetime.now(),
            source_agent=source_agent,
            source_file="direct_publish",
            payload=payload,
            tags=tags or {},
            processed=False,
            retry_count=0
        )
        
        await self._queue_event(event_message)
        return event_message.event_id
    
    def get_event_bus_status(self) -> Dict[str, Any]:
        """Get event bus status and statistics."""
        return {
            "active": self.active,
            "handlers_registered": len(self.handlers),
            "event_files_watched": len(self.event_files),
            "queue_size": self.event_queue.qsize(),
            "processed_events_cached": len(self.processed_events),
            "statistics": self.stats.copy(),
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Event Bus Infrastructure")
    parser.add_argument("--start", action="store_true", help="Start event bus")
    parser.add_argument("--status", action="store_true", help="Show event bus status")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    async def main():
        event_bus = EventBus(args.config or ".claude/event_bus_config.json")
        
        if args.start:
            # Register sample handlers for testing
            def crisis_handler(event: EventMessage):
                print(f"🚨 CRISIS: {event.payload.get('message', 'Unknown crisis')}")
            
            def deadline_handler(event: EventMessage):
                print(f"⏰ DEADLINE: {event.payload.get('message', 'Deadline warning')}")
            
            event_bus.register_handler("crisis_handler", crisis_handler, [EventType.COORDINATION_CRISIS])
            event_bus.register_handler("deadline_handler", deadline_handler, [EventType.DEADLINE_WARNING])
            
            await event_bus.start_event_bus()
            print("Event bus started. Press Ctrl+C to stop...")
            
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await event_bus.stop_event_bus()
                print("Event bus stopped")
        
        elif args.status:
            status = event_bus.get_event_bus_status()
            print(json.dumps(status, indent=2, default=str))
        
        else:
            print("Event Bus Infrastructure - Foundation Epic Evolution")
            print("Performance Agent Event Integration")
            print("")
            print("Usage: python coordination_protocols/event_bus.py [--start|--status]")
            print("")
            print("Supports: COORDINATION_CRISIS, DEADLINE_WARNING, TASK_ESCALATION")
            print("Features: File watching, JSON validation, event routing, subscriptions")
    
    asyncio.run(main())