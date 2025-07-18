#!/usr/bin/env python3
"""
Real-time Coordination Event Consumer

Foundation Epic coordination model - transitions from polling to real-time 
event stream consumption using existing coordination_alerts.json structure.
"""

import asyncio
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from accountability_system import AccountabilitySystem

logger = logging.getLogger(__name__)


class CoordinationEventHandler(FileSystemEventHandler):
    """Real-time coordination event handler for file system events."""
    
    def __init__(self, consumer: 'RealtimeCoordinationConsumer'):
        self.consumer = consumer
        self.coordination_files = {
            'coordination_dashboard.json',
            'coordination_status_report.json',
            'coordination_alerts.json'
        }
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.name in self.coordination_files:
            asyncio.create_task(self.consumer.process_coordination_event(file_path))
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.name in self.coordination_files or 'progress_' in file_path.name:
            asyncio.create_task(self.consumer.process_coordination_event(file_path))


class RealtimeCoordinationConsumer:
    """
    Real-time coordination event consumer for Foundation Epic coordination.
    
    Replaces 3-minute polling with real-time event stream consumption,
    integrating with existing coordination infrastructure.
    """
    
    def __init__(self, coordination_dir: str = "coordination_protocols"):
        self.coordination_dir = Path(coordination_dir)
        self.accountability = AccountabilitySystem()
        
        # Event processing configuration
        self.config = {
            "coordination_files": [
                "coordination_dashboard.json",
                "coordination_status_report.json", 
                "coordination_alerts.json"
            ],
            "progress_file_pattern": "progress_*.json",
            "debounce_seconds": 1,  # Prevent duplicate processing
            "max_retries": 3,
            "retry_delay": 2
        }
        
        # State tracking
        self.last_processed = {}
        self.event_queue = asyncio.Queue()
        self.observers = []
        self.event_handlers = []
        self.running = False
        
        # Coordination state
        self.current_state = {
            "infrastructure_status": {},
            "component_progress": {},
            "quality_metrics": {},
            "agent_coordination": {},
            "milestone_tracking": {},
            "system_health": {}
        }
        
        logger.info("RealtimeCoordinationConsumer initialized")
    
    async def start_realtime_consumption(self):
        """Start real-time coordination event consumption."""
        print("🚀 STARTING REAL-TIME COORDINATION CONSUMPTION")
        print("=" * 60)
        print("Foundation Epic coordination model - event stream active")
        print(f"Monitoring: {self.coordination_dir}")
        print()
        
        self.running = True
        
        # Initialize file system watching
        await self._setup_file_watching()
        
        # Start event processing
        processing_task = asyncio.create_task(self._process_event_queue())
        
        # Initial state load
        await self._load_initial_state()
        
        print("✅ Real-time coordination consumption active")
        print("🔄 Event stream monitoring started")
        print("📊 Foundation Epic coordination model operational")
        
        try:
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping real-time coordination consumption...")
        finally:
            await self._cleanup()
            processing_task.cancel()
    
    async def _setup_file_watching(self):
        """Setup file system watching for coordination files."""
        if not self.coordination_dir.exists():
            self.coordination_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file system observer
        observer = Observer()
        event_handler = CoordinationEventHandler(self)
        
        observer.schedule(event_handler, str(self.coordination_dir), recursive=True)
        observer.start()
        
        self.observers.append(observer)
        self.event_handlers.append(event_handler)
        
        logger.info(f"File system watching setup for {self.coordination_dir}")
    
    async def _process_event_queue(self):
        """Process coordination events from the queue."""
        while self.running:
            try:
                # Wait for events with timeout
                try:
                    file_path = await asyncio.wait_for(self.event_queue.get(), timeout=5.0)
                    await self._process_coordination_file(file_path)
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                await asyncio.sleep(1)
    
    async def process_coordination_event(self, file_path: Path):
        """Process a coordination event from file system."""
        # Debounce duplicate events
        now = time.time()
        file_key = str(file_path)
        
        if file_key in self.last_processed:
            if now - self.last_processed[file_key] < self.config["debounce_seconds"]:
                return
        
        self.last_processed[file_key] = now
        
        # Add to processing queue
        await self.event_queue.put(file_path)
    
    async def _process_coordination_file(self, file_path: Path):
        """Process a specific coordination file."""
        try:
            if not file_path.exists():
                return
            
            # Read and parse coordination data
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Process based on file type
            if file_path.name == "coordination_dashboard.json":
                await self._process_dashboard_event(data)
            elif file_path.name == "coordination_alerts.json":
                await self._process_alerts_event(data)
            elif file_path.name.startswith("progress_"):
                await self._process_progress_event(data, file_path)
            else:
                await self._process_generic_coordination_event(data, file_path)
            
            print(f"📡 Processed coordination event: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to process coordination file {file_path}: {e}")
    
    async def _process_dashboard_event(self, data: Dict[str, Any]):
        """Process coordination dashboard events."""
        # Update current state
        self.current_state.update({
            "infrastructure_status": data.get("infrastructure_status", {}),
            "component_progress": data.get("component_progress", {}),
            "quality_metrics": data.get("quality_metrics", {}),
            "agent_coordination": data.get("agent_coordination", {}),
            "milestone_tracking": data.get("milestone_tracking", {}),
            "system_health": data.get("system_health", {})
        })
        
        # Check for critical state changes
        await self._check_critical_state_changes(data)
        
        # Update accountability system
        await self._update_accountability_from_coordination(data)
        
        # Generate coordination alerts if needed
        await self._generate_coordination_alerts(data)
    
    async def _process_alerts_event(self, data: Dict[str, Any]):
        """Process coordination alerts events."""
        alerts = data.get("alerts", [])
        
        for alert in alerts:
            await self._handle_coordination_alert(alert)
    
    async def _process_progress_event(self, data: Dict[str, Any], file_path: Path):
        """Process progress events from component files."""
        component_name = file_path.stem.replace("progress_", "")
        
        progress_info = {
            "component": component_name,
            "progress": data.get("progress_percentage", 0),
            "status": data.get("status", "unknown"),
            "timestamp": data.get("last_updated", datetime.now().isoformat()),
            "quality_score": data.get("quality_score", 0),
            "blockers": data.get("blockers", []),
            "responsible_agent": data.get("responsible_agent", "unknown")
        }
        
        # Update accountability system with progress
        await self._update_accountability_progress(progress_info)
        
        # Check for progress issues
        await self._check_progress_issues(progress_info)
    
    async def _process_generic_coordination_event(self, data: Dict[str, Any], file_path: Path):
        """Process generic coordination events."""
        event_info = {
            "file": file_path.name,
            "timestamp": datetime.now().isoformat(),
            "data_keys": list(data.keys()),
            "event_type": "coordination_update"
        }
        
        logger.info(f"Generic coordination event processed: {event_info}")
    
    async def _check_critical_state_changes(self, data: Dict[str, Any]):
        """Check for critical state changes requiring immediate attention."""
        system_health = data.get("system_health", {})
        health_score = system_health.get("health_score", 100)
        
        # Critical health score
        if health_score < 50:
            await self._generate_critical_alert(
                "CRITICAL_HEALTH",
                f"System health score critically low: {health_score}%",
                {"health_score": health_score, "system_health": system_health}
            )
        
        # Check component progress issues
        component_progress = data.get("component_progress", {})
        overall_progress = component_progress.get("overall_progress", {})
        blocked_components = overall_progress.get("blocked_components", 0)
        
        if blocked_components > 0:
            await self._generate_critical_alert(
                "COMPONENTS_BLOCKED",
                f"{blocked_components} components blocked",
                {"blocked_count": blocked_components, "progress": component_progress}
            )
        
        # Check quality gate failures
        quality_metrics = data.get("quality_metrics", {})
        gates_status = quality_metrics.get("gates_status", {})
        failed_gates = gates_status.get("failed", 0)
        
        if failed_gates > 2:
            await self._generate_critical_alert(
                "QUALITY_GATES_FAILING",
                f"{failed_gates} quality gates failing",
                {"failed_gates": failed_gates, "quality_metrics": quality_metrics}
            )
    
    async def _update_accountability_from_coordination(self, data: Dict[str, Any]):
        """Update accountability system from coordination data."""
        component_progress = data.get("component_progress", {})
        component_details = component_progress.get("component_details", {})
        
        for component_id, component_info in component_details.items():
            agent_id = component_info.get("responsible_agent", "unknown")
            progress = component_info.get("progress_percentage", 0)
            status = component_info.get("status", "unknown")
            
            # Create summary from component data
            summary = f"Component {component_info.get('name', component_id)}: {status}"
            if component_info.get("blockers"):
                summary += f" (Blocked: {', '.join(component_info['blockers'])})"
            
            # Update accountability system
            # Note: In a real implementation, we'd need task IDs
            # For now, we'll track general agent progress
            try:
                self.accountability.agent_heartbeats[agent_id] = datetime.now()
                self.accountability._save_heartbeat_to_db(agent_id)
            except Exception as e:
                logger.warning(f"Failed to update heartbeat for {agent_id}: {e}")
    
    async def _update_accountability_progress(self, progress_info: Dict[str, Any]):
        """Update accountability system with progress information."""
        agent_id = progress_info["responsible_agent"]
        component = progress_info["component"]
        progress = progress_info["progress"]
        status = progress_info["status"]
        blockers = progress_info["blockers"]
        
        # Update agent heartbeat
        self.accountability.agent_heartbeats[agent_id] = datetime.now()
        
        # Log progress update
        logger.info(f"Progress update: {agent_id} - {component}: {progress}% ({status})")
        
        if blockers:
            logger.warning(f"Blockers detected for {component}: {blockers}")
    
    async def _check_progress_issues(self, progress_info: Dict[str, Any]):
        """Check for progress-related issues."""
        progress = progress_info["progress"]
        status = progress_info["status"]
        blockers = progress_info["blockers"]
        component = progress_info["component"]
        
        # Check for stalled progress
        if status == "in_progress" and progress < 10:
            await self._generate_coordination_alert({
                "type": "PROGRESS_STALLED",
                "message": f"Component {component} progress stalled at {progress}%",
                "severity": "medium",
                "component": component,
                "data": progress_info
            })
        
        # Check for blockers
        if blockers:
            await self._generate_coordination_alert({
                "type": "COMPONENT_BLOCKED",
                "message": f"Component {component} has blockers: {', '.join(blockers)}",
                "severity": "high",
                "component": component,
                "data": progress_info
            })
    
    async def _handle_coordination_alert(self, alert: Dict[str, Any]):
        """Handle a coordination alert."""
        alert_type = alert.get("type", "unknown")
        severity = alert.get("severity", "medium")
        message = alert.get("message", "No message")
        
        # Map to accountability escalation levels
        if severity == "critical":
            print(f"🚨 CRITICAL COORDINATION ALERT: {message}")
        elif severity == "high":
            print(f"🔴 HIGH COORDINATION ALERT: {message}")
        elif severity == "medium":
            print(f"🟡 MEDIUM COORDINATION ALERT: {message}")
        else:
            print(f"🔵 COORDINATION ALERT: {message}")
        
        # Log alert
        logger.warning(f"Coordination alert [{severity}]: {alert_type} - {message}")
    
    async def _generate_critical_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
        """Generate a critical coordination alert."""
        alert = {
            "type": alert_type,
            "severity": "critical",
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        await self._handle_coordination_alert(alert)
        
        # Save to alerts file
        await self._save_coordination_alert(alert)
    
    async def _generate_coordination_alerts(self, data: Dict[str, Any]):
        """Generate coordination alerts based on dashboard data."""
        alerts = []
        
        # Check system health
        system_health = data.get("system_health", {})
        if system_health.get("overall_health") == "🟠 needs attention":
            alerts.append({
                "type": "SYSTEM_ATTENTION_NEEDED",
                "severity": "medium",
                "message": "System health needs attention",
                "timestamp": datetime.now().isoformat(),
                "data": system_health
            })
        
        # Check milestone risks
        milestone_tracking = data.get("milestone_tracking", {})
        at_risk_milestones = milestone_tracking.get("at_risk_milestones", [])
        if at_risk_milestones:
            alerts.append({
                "type": "MILESTONES_AT_RISK",
                "severity": "high",
                "message": f"{len(at_risk_milestones)} milestones at risk",
                "timestamp": datetime.now().isoformat(),
                "data": {"at_risk_milestones": at_risk_milestones}
            })
        
        # Process alerts
        for alert in alerts:
            await self._handle_coordination_alert(alert)
    
    async def _generate_coordination_alert(self, alert: Dict[str, Any]):
        """Generate and process a coordination alert."""
        alert["timestamp"] = datetime.now().isoformat()
        await self._handle_coordination_alert(alert)
        await self._save_coordination_alert(alert)
    
    async def _save_coordination_alert(self, alert: Dict[str, Any]):
        """Save coordination alert to alerts file."""
        alerts_file = self.coordination_dir / "coordination_alerts.json"
        
        try:
            # Load existing alerts
            if alerts_file.exists():
                with open(alerts_file, 'r') as f:
                    alerts_data = json.load(f)
            else:
                alerts_data = {"alerts": []}
            
            # Add new alert
            alerts_data["alerts"].append(alert)
            
            # Keep only recent alerts (last 100)
            alerts_data["alerts"] = alerts_data["alerts"][-100:]
            
            # Save back
            with open(alerts_file, 'w') as f:
                json.dump(alerts_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save coordination alert: {e}")
    
    async def _load_initial_state(self):
        """Load initial coordination state."""
        dashboard_file = self.coordination_dir / "coordination_dashboard.json"
        
        if dashboard_file.exists():
            try:
                with open(dashboard_file, 'r') as f:
                    data = json.load(f)
                await self._process_dashboard_event(data)
                print("📊 Initial coordination state loaded")
            except Exception as e:
                logger.error(f"Failed to load initial state: {e}")
    
    async def _cleanup(self):
        """Cleanup resources."""
        self.running = False
        
        # Stop file system observers
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        print("✅ Real-time coordination consumption stopped")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current coordination state."""
        return {
            "timestamp": datetime.now().isoformat(),
            "coordination_state": self.current_state,
            "system_status": "active" if self.running else "stopped",
            "monitoring_directory": str(self.coordination_dir),
            "event_queue_size": self.event_queue.qsize() if hasattr(self.event_queue, 'qsize') else 0
        }
    
    def generate_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive status report."""
        current_state = self.get_current_state()
        
        # Add accountability system status
        accountability_status = self.accountability.get_system_status()
        
        return {
            "realtime_coordination": current_state,
            "accountability_system": accountability_status,
            "coordination_model": "event_stream",
            "foundation_epic_status": "operational"
        }


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-time Coordination Consumer")
    parser.add_argument("--coordination-dir", default="coordination_protocols", 
                       help="Coordination protocols directory")
    parser.add_argument("--status", action="store_true", help="Show current status")
    
    args = parser.parse_args()
    
    consumer = RealtimeCoordinationConsumer(args.coordination_dir)
    
    if args.status:
        status = consumer.generate_status_report()
        print(json.dumps(status, indent=2))
    else:
        await consumer.start_realtime_consumption()


if __name__ == "__main__":
    asyncio.run(main())