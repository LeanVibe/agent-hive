#!/usr/bin/env python3
"""
Coordination Dashboard for PR #28 Multi-Agent Development.

This module provides a comprehensive dashboard view of all coordination
activities, component progress, and system status.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CoordinationDashboard:
    """Comprehensive coordination dashboard for multi-agent development."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.coordination_protocols_dir = Path("coordination_protocols")

    def generate_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive coordination dashboard."""

        dashboard = {
            "dashboard_info": {
                "generated_at": datetime.now().isoformat(),
                "dashboard_version": "1.0.0",
                "coordination_status": "active"
            },
            "infrastructure_status": self._get_infrastructure_status(),
            "component_progress": self._get_component_progress(),
            "quality_metrics": self._get_quality_metrics(),
            "ci_cd_status": self._get_ci_cd_status(),
            "agent_coordination": self._get_agent_coordination_status(),
            "milestone_tracking": self._get_milestone_tracking(),
            "system_health": self._get_system_health(),
            "recent_activities": self._get_recent_activities(),
            "next_actions": self._get_next_actions()
        }

        return dashboard

    def _get_infrastructure_status(self) -> Dict[str, Any]:
        """Get coordination infrastructure status."""

        infrastructure_files = {
            "quality_gates": "quality_gate_validation.py",
            "progress_monitoring": "progress_monitoring.py",
            "ci_cd_pipeline": "continuous_integration_pipeline.py",
            "agent_communication": "integration_agent_communication.py",
            "github_actions": "../.github/workflows/component-ci.yml"
        }

        status = {}
        for component, file_path in infrastructure_files.items():
            full_path = self.coordination_protocols_dir / file_path
            if full_path.exists():
                status[component] = {
                    "status": "✅ operational",
                    "file": str(full_path),
                    "last_updated": datetime.fromtimestamp(full_path.stat().st_mtime).isoformat()
                }
            else:
                status[component] = {
                    "status": "❌ missing",
                    "file": str(full_path),
                    "last_updated": None
                }

        return {
            "overall_status": "✅ fully operational" if all(
                s["status"].startswith("✅") for s in status.values()
            ) else "⚠️ partial",
            "components": status,
            "infrastructure_score": sum(1 for s in status.values() if s["status"].startswith("✅")) / len(status) * 100
        }

    def _get_component_progress(self) -> Dict[str, Any]:
        """Get PR #28 component development progress."""

        # Try to load progress report
        progress_file = self.coordination_protocols_dir / "progress_report.json"
        if progress_file.exists():
            with open(progress_file) as f:
                progress_data = json.load(f)

            return {
                "overall_progress": progress_data.get("overall_progress", {}),
                "component_details": progress_data.get("component_summary", {}),
                "last_updated": progress_data.get("report_timestamp"),
                "components_status": {
                    "total": progress_data.get("overall_progress", {}).get("total_components", 0),
                    "completed": progress_data.get("overall_progress", {}).get("completed_components", 0),
                    "in_progress": progress_data.get("overall_progress", {}).get("in_progress_components", 0),
                    "blocked": progress_data.get("overall_progress", {}).get("blocked_components", 0)
                }
            }
        else:
            return {
                "status": "⚠️ progress data not available",
                "components_status": {
                    "total": 5,
                    "completed": 0,
                    "in_progress": 1,
                    "blocked": 0
                }
            }

    def _get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics from validation reports."""

        quality_reports = list(self.coordination_protocols_dir.glob("*_quality_report.json"))

        if quality_reports:
            # Get latest quality report
            latest_report = max(quality_reports, key=lambda p: p.stat().st_mtime)

            with open(latest_report) as f:
                quality_data = json.load(f)

            return {
                "latest_component": quality_data.get("component_info", {}).get("name"),
                "overall_score": quality_data.get("overall_results", {}).get("percentage", 0),
                "gates_status": {
                    "total": quality_data.get("summary", {}).get("total_gates", 0),
                    "passed": quality_data.get("summary", {}).get("passed_gates", 0),
                    "failed": quality_data.get("summary", {}).get("failed_gates", 0)
                },
                "gate_details": quality_data.get("gate_results", []),
                "last_validation": quality_data.get("component_info", {}).get("validation_date")
            }
        else:
            return {
                "status": "⚠️ no quality reports available",
                "gates_status": {"total": 5, "passed": 0, "failed": 0}
            }

    def _get_ci_cd_status(self) -> Dict[str, Any]:
        """Get CI/CD pipeline status."""

        ci_reports = list(self.coordination_protocols_dir.glob("ci_pipeline_*.json"))

        if ci_reports:
            # Get latest CI report
            latest_ci = max(ci_reports, key=lambda p: p.stat().st_mtime)

            with open(latest_ci) as f:
                ci_data = json.load(f)

            run_info = ci_data.get("run_info", {})

            return {
                "latest_run": {
                    "run_id": run_info.get("run_id"),
                    "component": run_info.get("component_id"),
                    "status": run_info.get("status"),
                    "success_rate": run_info.get("success_rate", 0),
                    "deployment_ready": run_info.get("deployment_ready", False),
                    "duration": run_info.get("total_duration", 0)
                },
                "pipeline_health": "✅ operational" if run_info.get("status") == "success" else "⚠️ issues detected",
                "github_actions": "✅ configured" if Path(".github/workflows/component-ci.yml").exists() else "❌ missing"
            }
        else:
            return {
                "status": "⚠️ no CI pipeline runs found",
                "pipeline_health": "🔄 not yet executed",
                "github_actions": "✅ configured" if Path(".github/workflows/component-ci.yml").exists() else "❌ missing"
            }

    def _get_agent_coordination_status(self) -> Dict[str, Any]:
        """Get agent coordination status."""

        coordination_files = {
            "integration_communication": "integration_agent_communication.py",
            "coordination_request": "integration_agent_coordination_request.json",
            "development_handoff": "integration_agent_development_handoff.json"
        }

        status = {}
        for coord_type, file_name in coordination_files.items():
            file_path = self.coordination_protocols_dir / file_name
            if file_path.exists():
                status[coord_type] = {
                    "status": "✅ active",
                    "last_updated": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
            else:
                status[coord_type] = {
                    "status": "❌ missing",
                    "last_updated": None
                }

        return {
            "coordination_health": "✅ fully coordinated" if all(
                s["status"].startswith("✅") for s in status.values()
            ) else "⚠️ partial coordination",
            "active_agents": ["orchestration_agent", "integration_agent"],
            "coordination_channels": status,
            "next_handoff": "API Gateway Foundation development completion"
        }

    def _get_milestone_tracking(self) -> Dict[str, Any]:
        """Get milestone tracking information."""

        # Try to load progress report for milestone data
        progress_file = self.coordination_protocols_dir / "progress_report.json"
        if progress_file.exists():
            with open(progress_file) as f:
                progress_data = json.load(f)

            milestones = progress_data.get("milestone_summary", {})

            return {
                "total_milestones": len(milestones),
                "milestone_details": milestones,
                "next_milestone": "Foundation Components Complete",
                "at_risk_milestones": [
                    m_id for m_id, m_data in milestones.items()
                    if m_data.get("risk_level") in ["high", "critical"]
                ]
            }
        else:
            return {
                "status": "⚠️ milestone data not available",
                "total_milestones": 4,
                "next_milestone": "Foundation Components Complete"
            }

    def _get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""

        infrastructure = self._get_infrastructure_status()
        component_progress = self._get_component_progress()
        quality = self._get_quality_metrics()
        ci_cd = self._get_ci_cd_status()

        # Calculate health score
        health_factors = {
            "infrastructure": infrastructure.get("infrastructure_score", 0),
            "component_progress": component_progress.get("overall_progress", {}).get("overall_percentage", 0),
            "quality_gates": quality.get("overall_score", 0) if "overall_score" in quality else 50,
            "ci_cd_pipeline": 100 if ci_cd.get("pipeline_health", "").startswith("✅") else 50
        }

        overall_health = sum(health_factors.values()) / len(health_factors)

        health_status = "🟢 excellent" if overall_health >= 90 else \
                       "🟡 good" if overall_health >= 75 else \
                       "🟠 needs attention" if overall_health >= 60 else \
                       "🔴 critical"

        return {
            "overall_health": health_status,
            "health_score": overall_health,
            "health_factors": health_factors,
            "recommendations": self._get_health_recommendations(health_factors)
        }

    def _get_health_recommendations(self, health_factors: Dict[str, float]) -> List[str]:
        """Generate health recommendations based on factors."""

        recommendations = []

        for factor, score in health_factors.items():
            if score < 75:
                if factor == "infrastructure":
                    recommendations.append("Review and complete missing infrastructure components")
                elif factor == "component_progress":
                    recommendations.append("Accelerate component development to meet timeline")
                elif factor == "quality_gates":
                    recommendations.append("Address quality gate failures before proceeding")
                elif factor == "ci_cd_pipeline":
                    recommendations.append("Investigate and resolve CI/CD pipeline issues")

        if not recommendations:
            recommendations.append("System operating at optimal levels - continue current approach")

        return recommendations

    def _get_recent_activities(self) -> List[Dict[str, Any]]:
        """Get recent coordination activities."""

        activities = []

        # Check for recent file modifications
        recent_files = []
        for file_path in self.coordination_protocols_dir.iterdir():
            if file_path.is_file() and file_path.suffix in ['.py', '.json', '.md']:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                recent_files.append((file_path, mtime))

        # Sort by modification time, most recent first
        recent_files.sort(key=lambda x: x[1], reverse=True)

        for file_path, mtime in recent_files[:10]:  # Last 10 activities
            activity_type = "📝 file_update" if file_path.suffix == '.py' else \
                           "📊 report_generated" if file_path.suffix == '.json' else \
                           "📋 documentation_update"

            activities.append({
                "timestamp": mtime.isoformat(),
                "type": activity_type,
                "description": f"Updated {file_path.name}",
                "file": str(file_path)
            })

        return activities

    def _get_next_actions(self) -> List[Dict[str, Any]]:
        """Get recommended next actions."""

        actions = [
            {
                "priority": "🔴 high",
                "action": "Begin API Gateway Foundation implementation",
                "assigned_to": "integration_agent",
                "estimated_time": "4-6 hours",
                "dependencies": ["specification review", "environment setup"]
            },
            {
                "priority": "🟡 medium",
                "action": "Monitor development progress",
                "assigned_to": "orchestration_agent",
                "estimated_time": "ongoing",
                "dependencies": ["progress monitoring system"]
            },
            {
                "priority": "🟡 medium",
                "action": "Validate quality gates during development",
                "assigned_to": "integration_agent",
                "estimated_time": "5 minutes per validation",
                "dependencies": ["quality gate system"]
            },
            {
                "priority": "🟢 low",
                "action": "Prepare service discovery specification",
                "assigned_to": "orchestration_agent",
                "estimated_time": "2-3 hours",
                "dependencies": ["API Gateway Foundation completion"]
            }
        ]

        return actions

    def save_dashboard(self, output_path: Optional[Path] = None) -> Path:
        """Save dashboard to file."""

        if output_path is None:
            output_path = self.coordination_protocols_dir / "coordination_dashboard.json"

        dashboard = self.generate_dashboard()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(dashboard, f, indent=2, default=str)

        self.logger.info(f"Coordination dashboard saved to: {output_path}")
        return output_path

    def print_dashboard_summary(self):
        """Print a formatted dashboard summary."""

        dashboard = self.generate_dashboard()

        print("🎯 COORDINATION DASHBOARD")
        print("=" * 50)
        print(f"Generated: {dashboard['dashboard_info']['generated_at']}")
        print(f"Status: {dashboard['dashboard_info']['coordination_status']}")
        print()

        # Infrastructure Status
        infra = dashboard['infrastructure_status']
        print(f"🏗️  INFRASTRUCTURE: {infra['overall_status']}")
        print(f"   Score: {infra['infrastructure_score']:.1f}%")
        for component, status in infra['components'].items():
            print(f"   • {component}: {status['status']}")
        print()

        # Component Progress
        progress = dashboard['component_progress']
        if 'components_status' in progress:
            comp_status = progress['components_status']
            print(f"📦 COMPONENTS: {comp_status['in_progress']} in progress, {comp_status['completed']} completed")
            if 'overall_progress' in progress:
                print(f"   Overall Progress: {progress['overall_progress'].get('overall_percentage', 0):.1f}%")
        print()

        # Quality Metrics
        quality = dashboard['quality_metrics']
        if 'overall_score' in quality:
            print(f"✅ QUALITY: {quality['overall_score']:.1f}%")
            gates = quality['gates_status']
            print(f"   Gates: {gates['passed']}/{gates['total']} passed")
        print()

        # System Health
        health = dashboard['system_health']
        print(f"🏥 HEALTH: {health['overall_health']} ({health['health_score']:.1f}%)")
        print()

        # Next Actions
        actions = dashboard['next_actions']
        print("🎯 NEXT ACTIONS:")
        for action in actions[:3]:  # Show top 3 actions
            print(f"   {action['priority']} {action['action']} ({action['assigned_to']})")
        print()

        print("📄 Full dashboard saved to coordination_protocols/coordination_dashboard.json")


def main():
    """Generate and display coordination dashboard."""

    print("🎯 GENERATING COORDINATION DASHBOARD")
    print("=" * 50)

    dashboard = CoordinationDashboard()

    # Generate and save dashboard
    output_path = dashboard.save_dashboard()

    # Display summary
    dashboard.print_dashboard_summary()

    print("✅ Coordination dashboard generated successfully")
    return output_path


if __name__ == "__main__":
    main()
