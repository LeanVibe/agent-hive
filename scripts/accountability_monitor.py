#!/usr/bin/env python3
"""
Real-time Accountability Monitor

Provides real-time monitoring dashboard and immediate escalation alerts
for agent accountability system.
"""

import time
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from accountability_system import AccountabilitySystem, TaskStatus, EscalationLevel


class AccountabilityMonitor:
    """Real-time accountability monitoring and alerting."""
    
    def __init__(self):
        self.system = AccountabilitySystem()
        self.alert_history = []
        
    def run_continuous_monitor(self):
        """Run continuous monitoring with live updates."""
        print("🚨 AGENT ACCOUNTABILITY MONITOR - LIVE")
        print("=" * 60)
        print("Monitoring agent performance, timeouts, and escalations...")
        print("Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                self._display_live_status()
                self._check_and_alert()
                time.sleep(30)  # Update every 30 seconds
                
        except KeyboardInterrupt:
            print("\n\n✅ Monitoring stopped by user")
            self._generate_final_report()
    
    def _display_live_status(self):
        """Display live system status."""
        status = self.system.get_system_status()
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Clear screen and show header
        print(f"\033[2J\033[H")  # Clear screen
        print(f"🚨 ACCOUNTABILITY MONITOR - {timestamp}")
        print("=" * 60)
        
        # System overview
        print(f"📊 SYSTEM STATUS:")
        print(f"   Total Tasks: {status['total_tasks']}")
        print(f"   Active Tasks: {status['active_tasks']}")
        print(f"   Completed: {status['completed_tasks']}")
        print(f"   ⚠️  Overdue: {status['overdue_tasks']}")
        print(f"   🚫 Blocked: {status['blocked_tasks']}")
        print(f"   🔥 Critical Escalations: {status['critical_escalations']}")
        print()
        
        # Agent status
        print(f"👥 AGENT STATUS:")
        print(f"   Tracked Agents: {status['agents_tracked']}")
        print(f"   Active Agents: {status['active_agents']}")
        
        # Show agent details
        for task in self.system.active_tasks.values():
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                agent_status = self.system.get_agent_status(task.agent_id)
                heartbeat_icon = self._get_heartbeat_icon(agent_status['heartbeat_status'])
                progress_bar = self._get_progress_bar(task.progress_percentage)
                
                print(f"   {heartbeat_icon} {task.agent_id}: {progress_bar} {task.title[:30]}...")
        
        print()
        
        # Recent alerts
        recent_alerts = [a for a in self.alert_history if (datetime.now() - a['timestamp']).seconds < 300]
        if recent_alerts:
            print(f"🚨 RECENT ALERTS (Last 5 min):")
            for alert in recent_alerts[-5:]:
                print(f"   {alert['timestamp'].strftime('%H:%M:%S')} - {alert['message']}")
        
        print(f"\n🔄 Last updated: {timestamp} | Next check in 30s")
    
    def _get_heartbeat_icon(self, status: str) -> str:
        """Get icon for heartbeat status."""
        icons = {
            "active": "🟢",
            "recent": "🟡", 
            "stale": "🔴",
            "unknown": "⚫"
        }
        return icons.get(status, "⚫")
    
    def _get_progress_bar(self, percentage: int) -> str:
        """Generate progress bar visualization."""
        bar_length = 10
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "▒" * (bar_length - filled)
        return f"[{bar}] {percentage:3d}%"
    
    def _check_and_alert(self):
        """Check for issues and send alerts."""
        escalations = self.system.check_timeouts_and_escalate()
        
        for escalation in escalations:
            alert = {
                "timestamp": datetime.now(),
                "level": escalation.level.value,
                "message": f"{escalation.agent_id}: {escalation.reason}",
                "escalation_id": escalation.escalation_id
            }
            
            self.alert_history.append(alert)
            
            # Send immediate alert for critical issues
            if escalation.level in [EscalationLevel.CRITICAL, EscalationLevel.SYSTEM_FAILURE]:
                self._send_critical_alert(escalation)
    
    def _send_critical_alert(self, escalation):
        """Send critical alert notification."""
        message = f"""
🚨 CRITICAL ACCOUNTABILITY ALERT 🚨

Agent: {escalation.agent_id}
Task: {escalation.task_id}
Level: {escalation.level.value}
Reason: {escalation.reason}
Time: {escalation.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Action Required: Immediate intervention needed
"""
        
        # Print to console
        print("\n" + "🚨" * 20)
        print(message)
        print("🚨" * 20 + "\n")
        
        # Log to file
        alert_file = Path(".claude/critical_alerts.log")
        alert_file.parent.mkdir(exist_ok=True)
        with open(alert_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")
    
    def _generate_final_report(self):
        """Generate final monitoring report."""
        report = self.system.generate_accountability_report()
        
        print("\n📋 FINAL ACCOUNTABILITY REPORT")
        print("=" * 50)
        
        # System summary
        status = report['system_status']
        print(f"Tasks: {status['total_tasks']} total, {status['active_tasks']} active")
        print(f"Issues: {status['overdue_tasks']} overdue, {status['blocked_tasks']} blocked")
        print(f"Escalations: {status['total_escalations']} total, {status['critical_escalations']} critical")
        
        # Agent performance
        print(f"\nAgent Performance:")
        for agent_id, agent_data in report['agent_summaries'].items():
            efficiency = 0 if agent_data['total_tasks'] == 0 else (agent_data['completed_tasks'] / agent_data['total_tasks'] * 100)
            print(f"  {agent_id}: {efficiency:.1f}% completion rate, {agent_data['escalation_count']} escalations")
        
        # Save full report
        report_file = Path(f".claude/accountability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Full report saved: {report_file}")
    
    def check_agent_compliance(self, agent_id: str) -> Dict[str, Any]:
        """Check specific agent compliance."""
        agent_status = self.system.get_agent_status(agent_id)
        
        # Calculate compliance metrics
        total_tasks = agent_status['total_tasks']
        if total_tasks == 0:
            return {"agent_id": agent_id, "compliance_score": 100, "status": "no_tasks"}
        
        # Scoring factors
        completion_rate = agent_status['completed_tasks'] / total_tasks
        overdue_penalty = agent_status['overdue_tasks'] / total_tasks * 0.5
        escalation_penalty = min(agent_status['escalation_count'] / total_tasks * 0.3, 0.3)
        
        # Heartbeat status
        heartbeat_penalty = 0
        if agent_status['heartbeat_status'] == 'stale':
            heartbeat_penalty = 0.2
        elif agent_status['heartbeat_status'] == 'unknown':
            heartbeat_penalty = 0.4
        
        # Calculate final score
        compliance_score = max(0, (completion_rate - overdue_penalty - escalation_penalty - heartbeat_penalty) * 100)
        
        # Determine status
        if compliance_score >= 90:
            status = "excellent"
        elif compliance_score >= 75:
            status = "good"
        elif compliance_score >= 60:
            status = "needs_improvement"
        else:
            status = "critical"
        
        return {
            "agent_id": agent_id,
            "compliance_score": round(compliance_score, 1),
            "status": status,
            "completion_rate": round(completion_rate * 100, 1),
            "penalties": {
                "overdue": round(overdue_penalty * 100, 1),
                "escalations": round(escalation_penalty * 100, 1),
                "heartbeat": round(heartbeat_penalty * 100, 1)
            },
            "raw_data": agent_status
        }
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report for all agents."""
        all_agents = set(task.agent_id for task in self.system.active_tasks.values())
        
        compliance_data = {}
        for agent_id in all_agents:
            compliance_data[agent_id] = self.check_agent_compliance(agent_id)
        
        # System-wide metrics
        if compliance_data:
            avg_compliance = sum(data['compliance_score'] for data in compliance_data.values()) / len(compliance_data)
            critical_agents = [aid for aid, data in compliance_data.items() if data['status'] == 'critical']
            excellent_agents = [aid for aid, data in compliance_data.items() if data['status'] == 'excellent']
        else:
            avg_compliance = 100
            critical_agents = []
            excellent_agents = []
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_compliance": {
                "average_score": round(avg_compliance, 1),
                "total_agents": len(compliance_data),
                "critical_agents": len(critical_agents),
                "excellent_agents": len(excellent_agents)
            },
            "agent_compliance": compliance_data,
            "recommendations": self._generate_recommendations(compliance_data)
        }
    
    def _generate_recommendations(self, compliance_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        for agent_id, data in compliance_data.items():
            if data['status'] == 'critical':
                recommendations.append(f"URGENT: Agent {agent_id} requires immediate intervention (score: {data['compliance_score']})")
            elif data['penalties']['heartbeat'] > 10:
                recommendations.append(f"Agent {agent_id} has poor communication - check heartbeat system")
            elif data['penalties']['overdue'] > 20:
                recommendations.append(f"Agent {agent_id} frequently misses deadlines - review task allocation")
        
        return recommendations


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Accountability Monitor")
    parser.add_argument("--live", action="store_true", help="Run live monitoring dashboard")
    parser.add_argument("--compliance", action="store_true", help="Generate compliance report")
    parser.add_argument("--agent", help="Check specific agent compliance")
    parser.add_argument("--alerts", action="store_true", help="Show recent alerts")
    
    args = parser.parse_args()
    
    monitor = AccountabilityMonitor()
    
    if args.live:
        monitor.run_continuous_monitor()
    elif args.compliance:
        report = monitor.generate_compliance_report()
        print(json.dumps(report, indent=2))
    elif args.agent:
        compliance = monitor.check_agent_compliance(args.agent)
        print(json.dumps(compliance, indent=2))
    elif args.alerts:
        # Show recent critical alerts
        alert_file = Path(".claude/critical_alerts.log")
        if alert_file.exists():
            print("🚨 RECENT CRITICAL ALERTS:")
            print("=" * 40)
            with open(alert_file) as f:
                lines = f.readlines()[-10:]  # Last 10 alerts
                for line in lines:
                    print(line.strip())
        else:
            print("No critical alerts found")
    else:
        # Default: show current status
        status = monitor.system.get_system_status()
        print("📊 ACCOUNTABILITY SYSTEM STATUS")
        print("=" * 40)
        print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()