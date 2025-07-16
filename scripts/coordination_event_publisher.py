#!/usr/bin/env python3
"""
Coordination Event Publisher

Publishes coordination events to the real-time event stream for Foundation Epic
coordination model integration.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CoordinationEventPublisher:
    """
    Publisher for coordination events in the Foundation Epic coordination model.
    
    Publishes events to the coordination event stream for real-time consumption
    by the coordination consumer and accountability system.
    """
    
    def __init__(self, coordination_dir: str = "coordination_protocols"):
        self.coordination_dir = Path(coordination_dir)
        self.coordination_dir.mkdir(parents=True, exist_ok=True)
        
        # Publisher configuration
        self.config = {
            "event_retention_hours": 24,
            "max_events_per_file": 1000,
            "enable_event_compression": True,
            "event_schema_version": "1.0"
        }
        
        logger.info("CoordinationEventPublisher initialized")
    
    def publish_progress_event(self, agent_id: str, component: str, 
                             progress: int, status: str, 
                             blockers: List[str] = None,
                             quality_score: float = None,
                             evidence_files: List[str] = None) -> str:
        """Publish a progress update event."""
        
        event_data = {
            "event_type": "progress_update",
            "event_id": f"progress_{agent_id}_{component}_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "component": component,
            "progress_percentage": progress,
            "status": status,
            "blockers": blockers or [],
            "quality_score": quality_score,
            "evidence_files": evidence_files or [],
            "schema_version": self.config["event_schema_version"]
        }
        
        # Save to component-specific progress file
        progress_file = self.coordination_dir / f"progress_{component}.json"
        self._save_event_data(progress_file, event_data)
        
        # Update coordination dashboard
        self._update_coordination_dashboard(event_data)
        
        print(f"📡 Published progress event: {agent_id} - {component}: {progress}%")
        return event_data["event_id"]
    
    def publish_completion_event(self, agent_id: str, component: str,
                               evidence_files: List[str],
                               quality_metrics: Dict[str, Any] = None) -> str:
        """Publish a component completion event."""
        
        event_data = {
            "event_type": "component_completion",
            "event_id": f"completion_{agent_id}_{component}_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "component": component,
            "progress_percentage": 100,
            "status": "completed",
            "evidence_files": evidence_files,
            "quality_metrics": quality_metrics or {},
            "schema_version": self.config["event_schema_version"]
        }
        
        # Save to component progress file
        progress_file = self.coordination_dir / f"progress_{component}.json"
        self._save_event_data(progress_file, event_data)
        
        # Update coordination dashboard
        self._update_coordination_dashboard(event_data)
        
        # Generate completion alert
        self.publish_alert_event(
            "COMPONENT_COMPLETED",
            f"Component {component} completed by {agent_id}",
            "info",
            {"component": component, "agent_id": agent_id, "evidence": evidence_files}
        )
        
        print(f"🎉 Published completion event: {agent_id} - {component}")
        return event_data["event_id"]
    
    def publish_blocker_event(self, agent_id: str, component: str,
                            blocker_description: str,
                            severity: str = "medium",
                            estimated_delay_hours: int = None) -> str:
        """Publish a blocker event."""
        
        event_data = {
            "event_type": "blocker_detected",
            "event_id": f"blocker_{agent_id}_{component}_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "component": component,
            "blocker_description": blocker_description,
            "severity": severity,
            "estimated_delay_hours": estimated_delay_hours,
            "status": "blocked",
            "schema_version": self.config["event_schema_version"]
        }
        
        # Save to component progress file
        progress_file = self.coordination_dir / f"progress_{component}.json"
        existing_data = self._load_event_data(progress_file)
        if existing_data:
            existing_data.update({
                "status": "blocked",
                "blockers": existing_data.get("blockers", []) + [blocker_description],
                "last_updated": event_data["timestamp"]
            })
            self._save_event_data(progress_file, existing_data)
        
        # Generate blocker alert
        self.publish_alert_event(
            "BLOCKER_DETECTED",
            f"Blocker in {component}: {blocker_description}",
            severity,
            {"component": component, "agent_id": agent_id, "blocker": blocker_description}
        )
        
        print(f"🚫 Published blocker event: {agent_id} - {component}: {blocker_description}")
        return event_data["event_id"]
    
    def publish_alert_event(self, alert_type: str, message: str,
                          severity: str = "medium",
                          data: Dict[str, Any] = None) -> str:
        """Publish an alert event."""
        
        event_data = {
            "event_type": "coordination_alert",
            "event_id": f"alert_{alert_type}_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "data": data or {},
            "resolved": False,
            "schema_version": self.config["event_schema_version"]
        }
        
        # Save to alerts file
        alerts_file = self.coordination_dir / "coordination_alerts.json"
        alerts_data = self._load_event_data(alerts_file) or {"alerts": []}
        alerts_data["alerts"].append(event_data)
        
        # Keep only recent alerts
        alerts_data["alerts"] = alerts_data["alerts"][-self.config["max_events_per_file"]:]
        
        self._save_event_data(alerts_file, alerts_data)
        
        print(f"🚨 Published alert event: [{severity}] {alert_type}: {message}")
        return event_data["event_id"]
    
    def publish_milestone_event(self, milestone_name: str, status: str,
                              completion_percentage: float,
                              target_date: str = None,
                              risk_level: str = "low") -> str:
        """Publish a milestone update event."""
        
        event_data = {
            "event_type": "milestone_update",
            "event_id": f"milestone_{milestone_name}_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "milestone_name": milestone_name,
            "status": status,
            "completion_percentage": completion_percentage,
            "target_date": target_date,
            "risk_level": risk_level,
            "schema_version": self.config["event_schema_version"]
        }
        
        # Update coordination dashboard
        self._update_coordination_dashboard(event_data)
        
        print(f"🎯 Published milestone event: {milestone_name}: {completion_percentage}% ({status})")
        return event_data["event_id"]
    
    def publish_agent_heartbeat(self, agent_id: str, status: str = "active",
                              current_task: str = None,
                              next_eta_minutes: int = None) -> str:
        """Publish an agent heartbeat event."""
        
        event_data = {
            "event_type": "agent_heartbeat",
            "event_id": f"heartbeat_{agent_id}_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "status": status,
            "current_task": current_task,
            "next_eta_minutes": next_eta_minutes,
            "schema_version": self.config["event_schema_version"]
        }
        
        # Save to agent-specific heartbeat file
        heartbeat_file = self.coordination_dir / f"heartbeat_{agent_id}.json"
        self._save_event_data(heartbeat_file, event_data)
        
        # Update coordination dashboard
        self._update_coordination_dashboard(event_data)
        
        return event_data["event_id"]
    
    def _update_coordination_dashboard(self, event_data: Dict[str, Any]):
        """Update the coordination dashboard with new event data."""
        dashboard_file = self.coordination_dir / "coordination_dashboard.json"
        
        # Load existing dashboard data
        dashboard_data = self._load_event_data(dashboard_file)
        if not dashboard_data:
            dashboard_data = self._create_default_dashboard()
        
        # Update based on event type
        event_type = event_data.get("event_type")
        
        if event_type == "progress_update":
            self._update_dashboard_progress(dashboard_data, event_data)
        elif event_type == "component_completion":
            self._update_dashboard_completion(dashboard_data, event_data)
        elif event_type == "blocker_detected":
            self._update_dashboard_blocker(dashboard_data, event_data)
        elif event_type == "milestone_update":
            self._update_dashboard_milestone(dashboard_data, event_data)
        elif event_type == "agent_heartbeat":
            self._update_dashboard_agent(dashboard_data, event_data)
        
        # Update metadata
        dashboard_data["dashboard_info"]["generated_at"] = datetime.now().isoformat()
        
        # Add to recent activities
        if "recent_activities" not in dashboard_data:
            dashboard_data["recent_activities"] = []
        
        activity = {
            "timestamp": event_data["timestamp"],
            "type": f"📡 {event_type}",
            "description": self._generate_activity_description(event_data),
            "event_id": event_data["event_id"]
        }
        dashboard_data["recent_activities"].insert(0, activity)
        
        # Keep only recent activities
        dashboard_data["recent_activities"] = dashboard_data["recent_activities"][:20]
        
        # Save updated dashboard
        self._save_event_data(dashboard_file, dashboard_data)
    
    def _update_dashboard_progress(self, dashboard_data: Dict[str, Any], event_data: Dict[str, Any]):
        """Update dashboard with progress event."""
        component = event_data.get("component")
        agent_id = event_data.get("agent_id")
        progress = event_data.get("progress_percentage", 0)
        status = event_data.get("status", "unknown")
        
        # Update component progress
        if "component_progress" not in dashboard_data:
            dashboard_data["component_progress"] = {"component_details": {}}
        
        component_details = dashboard_data["component_progress"]["component_details"]
        
        if component not in component_details:
            component_details[component] = {
                "name": component.replace("_", " ").title(),
                "responsible_agent": agent_id,
                "phase": "development",
                "progress_percentage": 0,
                "status": "not_started",
                "quality_score": 0,
                "test_coverage": 0,
                "current_issues": [],
                "blockers": []
            }
        
        # Update progress
        component_details[component].update({
            "progress_percentage": progress,
            "status": status,
            "responsible_agent": agent_id,
            "last_updated": event_data["timestamp"]
        })
        
        # Update blockers if present
        if event_data.get("blockers"):
            component_details[component]["blockers"] = event_data["blockers"]
    
    def _update_dashboard_completion(self, dashboard_data: Dict[str, Any], event_data: Dict[str, Any]):
        """Update dashboard with completion event."""
        component = event_data.get("component")
        
        if "component_progress" in dashboard_data:
            component_details = dashboard_data["component_progress"]["component_details"]
            if component in component_details:
                component_details[component].update({
                    "progress_percentage": 100,
                    "status": "completed",
                    "phase": "completed",
                    "completed_at": event_data["timestamp"]
                })
                
                # Update quality metrics if present
                if event_data.get("quality_metrics"):
                    component_details[component]["quality_score"] = event_data["quality_metrics"].get("score", 100)
    
    def _update_dashboard_blocker(self, dashboard_data: Dict[str, Any], event_data: Dict[str, Any]):
        """Update dashboard with blocker event."""
        component = event_data.get("component")
        blocker = event_data.get("blocker_description")
        
        if "component_progress" in dashboard_data:
            component_details = dashboard_data["component_progress"]["component_details"]
            if component in component_details:
                component_details[component]["status"] = "blocked"
                if blocker not in component_details[component]["blockers"]:
                    component_details[component]["blockers"].append(blocker)
    
    def _update_dashboard_milestone(self, dashboard_data: Dict[str, Any], event_data: Dict[str, Any]):
        """Update dashboard with milestone event."""
        milestone_name = event_data.get("milestone_name")
        
        if "milestone_tracking" not in dashboard_data:
            dashboard_data["milestone_tracking"] = {"milestone_details": {}}
        
        milestone_details = dashboard_data["milestone_tracking"]["milestone_details"]
        
        milestone_key = milestone_name.lower().replace(" ", "_")
        milestone_details[milestone_key] = {
            "name": milestone_name,
            "status": event_data.get("status"),
            "completion_percentage": event_data.get("completion_percentage"),
            "target_date": event_data.get("target_date"),
            "risk_level": event_data.get("risk_level"),
            "last_updated": event_data["timestamp"]
        }
    
    def _update_dashboard_agent(self, dashboard_data: Dict[str, Any], event_data: Dict[str, Any]):
        """Update dashboard with agent heartbeat."""
        agent_id = event_data.get("agent_id")
        
        if "agent_coordination" not in dashboard_data:
            dashboard_data["agent_coordination"] = {"active_agents": []}
        
        active_agents = dashboard_data["agent_coordination"]["active_agents"]
        if agent_id not in active_agents:
            active_agents.append(agent_id)
        
        # Update agent status
        if "agent_status" not in dashboard_data["agent_coordination"]:
            dashboard_data["agent_coordination"]["agent_status"] = {}
        
        dashboard_data["agent_coordination"]["agent_status"][agent_id] = {
            "status": event_data.get("status"),
            "current_task": event_data.get("current_task"),
            "last_heartbeat": event_data["timestamp"],
            "next_eta_minutes": event_data.get("next_eta_minutes")
        }
    
    def _generate_activity_description(self, event_data: Dict[str, Any]) -> str:
        """Generate human-readable activity description."""
        event_type = event_data.get("event_type")
        
        if event_type == "progress_update":
            return f"{event_data.get('agent_id')} updated {event_data.get('component')}: {event_data.get('progress_percentage')}%"
        elif event_type == "component_completion":
            return f"Component {event_data.get('component')} completed by {event_data.get('agent_id')}"
        elif event_type == "blocker_detected":
            return f"Blocker detected in {event_data.get('component')}: {event_data.get('blocker_description')}"
        elif event_type == "milestone_update":
            return f"Milestone {event_data.get('milestone_name')}: {event_data.get('completion_percentage')}%"
        elif event_type == "agent_heartbeat":
            return f"Agent {event_data.get('agent_id')} heartbeat: {event_data.get('status')}"
        else:
            return f"Coordination event: {event_type}"
    
    def _create_default_dashboard(self) -> Dict[str, Any]:
        """Create default dashboard structure."""
        return {
            "dashboard_info": {
                "generated_at": datetime.now().isoformat(),
                "dashboard_version": "1.0.0",
                "coordination_status": "active"
            },
            "infrastructure_status": {
                "overall_status": "✅ operational",
                "components": {},
                "infrastructure_score": 100.0
            },
            "component_progress": {
                "overall_progress": {
                    "total_components": 0,
                    "completed_components": 0,
                    "in_progress_components": 0,
                    "blocked_components": 0,
                    "overall_percentage": 0.0
                },
                "component_details": {}
            },
            "quality_metrics": {
                "overall_score": 100.0,
                "gates_status": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0
                }
            },
            "agent_coordination": {
                "coordination_health": "✅ operational",
                "active_agents": []
            },
            "milestone_tracking": {
                "milestone_details": {}
            },
            "system_health": {
                "overall_health": "✅ operational",
                "health_score": 100.0
            },
            "recent_activities": []
        }
    
    def _load_event_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load event data from file."""
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load event data from {file_path}: {e}")
        return None
    
    def _save_event_data(self, file_path: Path, data: Dict[str, Any]):
        """Save event data to file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save event data to {file_path}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get publisher status."""
        return {
            "publisher_status": "active",
            "coordination_directory": str(self.coordination_dir),
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Coordination Event Publisher")
    parser.add_argument("--coordination-dir", default="coordination_protocols",
                       help="Coordination protocols directory")
    parser.add_argument("--test-events", action="store_true",
                       help="Publish test events")
    parser.add_argument("--status", action="store_true",
                       help="Show publisher status")
    
    args = parser.parse_args()
    
    publisher = CoordinationEventPublisher(args.coordination_dir)
    
    if args.status:
        status = publisher.get_status()
        print(json.dumps(status, indent=2))
    elif args.test_events:
        print("🧪 Publishing test coordination events...")
        
        # Test progress event
        publisher.publish_progress_event(
            "integration-specialist-Jul-16-1339",
            "api_gateway_foundation",
            75,
            "in_progress",
            evidence_files=["external_api/api_gateway.py", "tests/test_api_gateway.py"]
        )
        
        # Test heartbeat
        publisher.publish_agent_heartbeat(
            "integration-specialist-Jul-16-1339",
            "active",
            "API Gateway implementation",
            30
        )
        
        print("✅ Test events published")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()