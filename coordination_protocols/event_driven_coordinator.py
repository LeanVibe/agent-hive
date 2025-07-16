#!/usr/bin/env python3
"""
Event-Driven Coordination System
Foundation Epic Evolution - Real-time Pub/Sub Infrastructure

Monitors coordination_alerts.json events from accountability system and agent status files
for real-time coordination using existing EventStreaming infrastructure.

Strategic Pivot: From polling to event-driven coordination per Gemini analysis.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import existing EventStreaming infrastructure  
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from external_api.event_streaming import EventStreaming, EventBuffer
from external_api.models import EventStreamConfig, StreamEvent, EventPriority

logger = logging.getLogger(__name__)


@dataclass
class CoordinationAlert:
    """Coordination alert from accountability system."""
    alert_id: str
    alert_type: str  # "task_overdue", "escalation", "reassignment", "status_update"
    agent_id: str
    task_id: Optional[str]
    priority: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass 
class AgentStatus:
    """Agent status information."""
    agent_id: str
    status: str  # "active", "inactive", "working", "blocked"
    last_activity: datetime
    current_task: Optional[str]
    worktree_path: str
    git_status: Dict[str, Any]
    metadata: Dict[str, Any]


class CoordinationFileWatcher(FileSystemEventHandler):
    """File system watcher for coordination files."""
    
    def __init__(self, coordinator: 'EventDrivenCoordinator'):
        super().__init__()
        self.coordinator = coordinator
        self.watched_files = set()
        
    def add_watched_file(self, file_path: str):
        """Add file to watch list."""
        self.watched_files.add(str(Path(file_path).resolve()))
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        file_path = str(Path(event.src_path).resolve())
        if file_path in self.watched_files:
            logger.debug(f"Detected change in watched file: {file_path}")
            asyncio.create_task(self.coordinator._handle_file_change(file_path))


class EventDrivenCoordinator:
    """
    Event-driven coordination system using existing EventStreaming infrastructure.
    
    Monitors coordination_alerts.json events and agent status files for real-time
    coordination without polling, building on Foundation Epic infrastructure.
    """
    
    def __init__(self, config_path: str = ".claude/coordination_config.json"):
        """Initialize event-driven coordinator."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # EventStreaming infrastructure for Pub/Sub
        stream_config = EventStreamConfig(
            stream_name="coordination_events",
            buffer_size=1000,
            batch_size=50,
            flush_interval=1.0,  # Real-time processing
            compression_enabled=True,
            max_retries=3,
            retry_delay=1.0
        )
        self.event_stream = EventStreaming(stream_config)
        
        # File watching infrastructure
        self.file_watcher = CoordinationFileWatcher(self)
        self.observer = Observer()
        
        # State tracking
        self.active = False
        self.last_processed_events: Dict[str, datetime] = {}
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.coordination_subscribers: Dict[str, Callable] = {}
        
        # Coordination file paths
        self.coordination_files = self._discover_coordination_files()
        
        logger.info("EventDrivenCoordinator initialized with event streaming")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load coordination configuration."""
        default_config = {
            "coordination_alert_files": [
                ".claude/coordination_alerts.json",
                "coordination_alerts.json", 
                ".claude/logs/accountability_alerts.json"
            ],
            "agent_status_patterns": [
                "**/agent-*/.claude/status.json",
                "**/worktrees/*/agent_status.json",
                ".claude/agent_statuses/*.json"
            ],
            "watch_directories": [
                ".claude",
                "worktrees",
                "coordination_protocols"
            ],
            "event_retention_hours": 24,
            "alert_debounce_seconds": 1.0
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.error(f"Failed to load coordination config: {e}")
        
        return default_config
    
    def _discover_coordination_files(self) -> List[Path]:
        """Discover existing coordination and status files."""
        files = []
        
        # Add coordination alert files
        for pattern in self.config["coordination_alert_files"]:
            file_path = Path(pattern)
            if file_path.exists():
                files.append(file_path)
                logger.info(f"Found coordination alert file: {file_path}")
        
        # Discover agent status files
        for pattern in self.config["agent_status_patterns"]:
            try:
                import glob
                for file_path in glob.glob(pattern, recursive=True):
                    path = Path(file_path)
                    if path.exists():
                        files.append(path)
                        logger.debug(f"Found agent status file: {path}")
            except Exception as e:
                logger.warning(f"Error discovering files with pattern {pattern}: {e}")
        
        return files
    
    async def start_coordination(self) -> None:
        """Start event-driven coordination system."""
        if self.active:
            logger.warning("Event-driven coordination already active")
            return
        
        try:
            logger.info("Starting event-driven coordination system...")
            
            # Start EventStreaming infrastructure
            await self.event_stream.start_streaming()
            
            # Register built-in event consumers
            await self._register_builtin_consumers()
            
            # Setup file watching
            await self._setup_file_watching()
            
            # Process existing files for initial state
            await self._process_existing_files()
            
            self.active = True
            logger.info("Event-driven coordination started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start coordination: {e}")
            raise
    
    async def stop_coordination(self) -> None:
        """Stop event-driven coordination system."""
        if not self.active:
            logger.warning("Event-driven coordination not active")
            return
        
        try:
            logger.info("Stopping event-driven coordination...")
            
            self.active = False
            
            # Stop file watching
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
            
            # Stop EventStreaming
            await self.event_stream.stop_streaming()
            
            logger.info("Event-driven coordination stopped")
            
        except Exception as e:
            logger.error(f"Error stopping coordination: {e}")
            raise
    
    async def _register_builtin_consumers(self) -> None:
        """Register built-in event consumers for coordination."""
        
        # PM coordination consumer
        async def pm_coordination_consumer(batch_data: Dict[str, Any]) -> None:
            """Handle PM coordination events."""
            try:
                events = batch_data.get("events", [])
                for event_data in events:
                    if event_data.get("event_type") == "coordination_alert":
                        await self._handle_coordination_alert(event_data["data"])
                    elif event_data.get("event_type") == "agent_status_change":
                        await self._handle_agent_status_change(event_data["data"])
                        
                logger.debug(f"PM coordinator processed {len(events)} events")
                
            except Exception as e:
                logger.error(f"PM coordination consumer error: {e}")
        
        # Agent synchronization consumer
        async def agent_sync_consumer(batch_data: Dict[str, Any]) -> None:
            """Handle agent synchronization events."""
            try:
                events = batch_data.get("events", [])
                coordination_events = [
                    e for e in events 
                    if e.get("event_type") in ["task_escalation", "agent_reassignment", "critical_alert"]
                ]
                
                if coordination_events:
                    await self._broadcast_to_agents(coordination_events)
                    
            except Exception as e:
                logger.error(f"Agent sync consumer error: {e}")
        
        # Register consumers
        self.event_stream.register_consumer("pm_coordination", pm_coordination_consumer)
        self.event_stream.register_consumer("agent_sync", agent_sync_consumer)
        
        logger.info("Built-in coordination consumers registered")
    
    async def _setup_file_watching(self) -> None:
        """Setup file system watching for coordination files."""
        try:
            # Add coordination files to watcher
            for file_path in self.coordination_files:
                self.file_watcher.add_watched_file(str(file_path))
                
                # Watch parent directory for file creation
                parent_dir = file_path.parent
                if parent_dir.exists():
                    self.observer.schedule(self.file_watcher, str(parent_dir), recursive=False)
            
            # Watch configured directories
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
    
    async def _process_existing_files(self) -> None:
        """Process existing coordination files for initial state."""
        for file_path in self.coordination_files:
            if file_path.exists():
                await self._handle_file_change(str(file_path))
    
    async def _handle_file_change(self, file_path: str) -> None:
        """Handle coordination file changes."""
        try:
            # Debounce rapid file changes
            current_time = datetime.now()
            last_processed = self.last_processed_events.get(file_path)
            debounce_threshold = timedelta(seconds=self.config["alert_debounce_seconds"])
            
            if last_processed and (current_time - last_processed) < debounce_threshold:
                return
            
            self.last_processed_events[file_path] = current_time
            
            # Process file based on type
            path = Path(file_path)
            
            if "coordination_alerts" in path.name or "accountability_alerts" in path.name:
                await self._process_coordination_alerts_file(path)
            elif "status" in path.name:
                await self._process_agent_status_file(path)
            
        except Exception as e:
            logger.error(f"Error handling file change {file_path}: {e}")
    
    async def _process_coordination_alerts_file(self, file_path: Path) -> None:
        """Process coordination alerts JSON file."""
        try:
            if not file_path.exists():
                return
                
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Handle different alert file formats
            alerts = []
            if isinstance(data, list):
                alerts = data
            elif isinstance(data, dict):
                if "alerts" in data:
                    alerts = data["alerts"]
                elif "events" in data:
                    alerts = data["events"]
                else:
                    alerts = [data]  # Single alert
            
            # Process each alert
            for alert_data in alerts:
                await self._publish_coordination_alert(alert_data, str(file_path))
                
            logger.debug(f"Processed {len(alerts)} coordination alerts from {file_path}")
            
        except Exception as e:
            logger.error(f"Error processing coordination alerts file {file_path}: {e}")
    
    async def _process_agent_status_file(self, file_path: Path) -> None:
        """Process agent status JSON file."""
        try:
            if not file_path.exists():
                return
                
            with open(file_path, 'r') as f:
                status_data = json.load(f)
            
            # Extract agent ID from file path or data
            agent_id = self._extract_agent_id(file_path, status_data)
            
            if agent_id:
                await self._publish_agent_status_update(agent_id, status_data, str(file_path))
                
        except Exception as e:
            logger.error(f"Error processing agent status file {file_path}: {e}")
    
    def _extract_agent_id(self, file_path: Path, status_data: Dict[str, Any]) -> Optional[str]:
        """Extract agent ID from file path or status data."""
        # Try from status data first
        if "agent_id" in status_data:
            return status_data["agent_id"]
        
        # Extract from file path patterns
        path_parts = file_path.parts
        for i, part in enumerate(path_parts):
            if part.startswith("agent-") and i + 1 < len(path_parts):
                return part
            elif "worktrees" in path_parts and i + 1 < len(path_parts):
                worktree_name = path_parts[i + 1]
                if worktree_name.startswith("agent-") or "agent" in worktree_name:
                    return worktree_name
        
        return None
    
    async def _publish_coordination_alert(self, alert_data: Dict[str, Any], source_file: str) -> None:
        """Publish coordination alert as event."""
        try:
            event_data = {
                "alert": alert_data,
                "source_file": source_file,
                "processed_at": datetime.now().isoformat()
            }
            
            # Determine priority from alert
            priority = EventPriority.MEDIUM
            if alert_data.get("priority") == "critical" or alert_data.get("escalation_level") == "emergency":
                priority = EventPriority.HIGH
            elif alert_data.get("priority") == "low":
                priority = EventPriority.LOW
            
            # Publish to event stream
            await self.event_stream.publish_event(
                event_type="coordination_alert",
                data=event_data,
                partition_key=alert_data.get("agent_id", "unknown"),
                priority=priority,
                tags={
                    "alert_type": alert_data.get("alert_type", "unknown"),
                    "source": "accountability_system"
                }
            )
            
            logger.debug(f"Published coordination alert: {alert_data.get('alert_type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error publishing coordination alert: {e}")
    
    async def _publish_agent_status_update(self, agent_id: str, status_data: Dict[str, Any], source_file: str) -> None:
        """Publish agent status update as event."""
        try:
            event_data = {
                "agent_id": agent_id,
                "status": status_data,
                "source_file": source_file,
                "processed_at": datetime.now().isoformat()
            }
            
            # Determine priority from status change
            priority = EventPriority.LOW
            if status_data.get("status") in ["blocked", "failed", "error"]:
                priority = EventPriority.HIGH
            elif status_data.get("status") in ["working", "active"]:
                priority = EventPriority.MEDIUM
            
            # Publish to event stream
            await self.event_stream.publish_event(
                event_type="agent_status_change",
                data=event_data,
                partition_key=agent_id,
                priority=priority,
                tags={
                    "agent_id": agent_id,
                    "status": status_data.get("status", "unknown")
                }
            )
            
            logger.debug(f"Published agent status update: {agent_id} -> {status_data.get('status', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error publishing agent status update: {e}")
    
    async def _handle_coordination_alert(self, alert_data: Dict[str, Any]) -> None:
        """Handle coordination alert event."""
        try:
            alert = alert_data.get("alert", {})
            alert_type = alert.get("alert_type", "unknown")
            agent_id = alert.get("agent_id", "unknown")
            
            logger.info(f"Handling coordination alert: {alert_type} for agent {agent_id}")
            
            # Notify subscribers
            for subscriber_id, callback in self.coordination_subscribers.items():
                try:
                    await callback("coordination_alert", alert_data)
                except Exception as e:
                    logger.error(f"Error notifying subscriber {subscriber_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error handling coordination alert: {e}")
    
    async def _handle_agent_status_change(self, status_data: Dict[str, Any]) -> None:
        """Handle agent status change event."""
        try:
            agent_id = status_data.get("agent_id", "unknown")
            status = status_data.get("status", {})
            
            logger.info(f"Handling agent status change: {agent_id} -> {status.get('status', 'unknown')}")
            
            # Update local agent status cache
            self.agent_statuses[agent_id] = AgentStatus(
                agent_id=agent_id,
                status=status.get("status", "unknown"),
                last_activity=datetime.now(),
                current_task=status.get("current_task"),
                worktree_path=status.get("worktree_path", ""),
                git_status=status.get("git_status", {}),
                metadata=status
            )
            
            # Notify subscribers
            for subscriber_id, callback in self.coordination_subscribers.items():
                try:
                    await callback("agent_status_change", status_data)
                except Exception as e:
                    logger.error(f"Error notifying subscriber {subscriber_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error handling agent status change: {e}")
    
    async def _broadcast_to_agents(self, events: List[Dict[str, Any]]) -> None:
        """Broadcast coordination events to agents."""
        try:
            for event in events:
                event_type = event.get("event_type")
                data = event.get("data", {})
                
                logger.info(f"Broadcasting {event_type} to agents")
                
                # Here you would integrate with agent communication systems
                # For now, log the broadcast
                logger.debug(f"Broadcast event: {event_type} - {data}")
            
        except Exception as e:
            logger.error(f"Error broadcasting to agents: {e}")
    
    def subscribe_to_coordination_events(self, subscriber_id: str, callback: Callable) -> None:
        """
        Subscribe to coordination events.
        
        Args:
            subscriber_id: Unique subscriber identifier
            callback: Async function to handle events (event_type, data)
        """
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callback must be async function")
        
        self.coordination_subscribers[subscriber_id] = callback
        logger.info(f"Registered coordination subscriber: {subscriber_id}")
    
    def unsubscribe_from_coordination_events(self, subscriber_id: str) -> bool:
        """Unsubscribe from coordination events."""
        if subscriber_id in self.coordination_subscribers:
            del self.coordination_subscribers[subscriber_id]
            logger.info(f"Unregistered coordination subscriber: {subscriber_id}")
            return True
        return False
    
    async def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination system status."""
        buffer_stats = await self.event_stream.get_buffer_stats()
        stream_info = self.event_stream.get_stream_info()
        
        return {
            "active": self.active,
            "coordination_files_watched": len(self.coordination_files),
            "agent_statuses_cached": len(self.agent_statuses),
            "subscribers_count": len(self.coordination_subscribers),
            "event_stream": stream_info,
            "buffer_stats": buffer_stats,
            "last_processed_events": len(self.last_processed_events),
            "timestamp": datetime.now().isoformat()
        }


# CLI Interface for event-driven coordination
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Event-Driven Coordination System")
    parser.add_argument("--start", action="store_true", help="Start coordination system")
    parser.add_argument("--stop", action="store_true", help="Stop coordination system") 
    parser.add_argument("--status", action="store_true", help="Show coordination status")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    async def main():
        coordinator = EventDrivenCoordinator(args.config or ".claude/coordination_config.json")
        
        if args.start:
            await coordinator.start_coordination()
            print("Event-driven coordination started. Press Ctrl+C to stop...")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await coordinator.stop_coordination()
                print("Coordination stopped")
        
        elif args.stop:
            await coordinator.stop_coordination()
            print("Coordination stopped")
        
        elif args.status:
            if coordinator.active:
                await coordinator.start_coordination()
            status = await coordinator.get_coordination_status()
            print(json.dumps(status, indent=2, default=str))
            if coordinator.active:
                await coordinator.stop_coordination()
        
        else:
            print("Event-Driven Coordination System")
            print("Foundation Epic Evolution - Real-time Pub/Sub Infrastructure")
            print("")
            print("Usage: python coordination_protocols/event_driven_coordinator.py [--start|--stop|--status]")
            print("")
            print("Strategic pivot from polling to event-driven coordination")
            print("Monitors coordination_alerts.json and agent status files")
            print("Built on existing EventStreaming infrastructure")
    
    asyncio.run(main())