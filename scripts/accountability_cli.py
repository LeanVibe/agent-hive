#!/usr/bin/env python3
"""
Accountability System CLI

Command-line interface for managing agent accountability, task assignment,
progress tracking, and escalation management.
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from accountability_system import AccountabilitySystem, TaskStatus, EscalationLevel
from accountability_monitor import AccountabilityMonitor


def assign_task_command(args):
    """Handle task assignment."""
    system = AccountabilitySystem()
    
    task_id = system.assign_task(
        agent_id=args.agent,
        title=args.title,
        description=args.description,
        deadline_hours=args.deadline,
        priority=args.priority
    )
    
    print(f"✅ Task assigned: {task_id}")
    print(f"📋 Agent: {args.agent}")
    print(f"⏰ Deadline: {args.deadline} hours")
    print(f"⭐ Priority: {args.priority}")
    
    return task_id


def update_progress_command(args):
    """Handle progress updates."""
    system = AccountabilitySystem()
    
    evidence_files = args.evidence.split(',') if args.evidence else []
    blockers = args.blockers.split(',') if args.blockers else []
    
    success = system.update_task_progress(
        agent_id=args.agent,
        task_id=args.task,
        progress_percentage=args.progress,
        status_summary=args.summary,
        evidence_files=evidence_files,
        blockers=blockers,
        eta_minutes=args.eta,
        confidence_level=args.confidence
    )
    
    if success:
        print(f"✅ Progress updated for task {args.task}")
        print(f"📊 Progress: {args.progress}%")
        print(f"📝 Summary: {args.summary}")
        if blockers:
            print(f"🚫 Blockers: {', '.join(blockers)}")
    else:
        print(f"❌ Failed to update progress for task {args.task}")


def check_escalations_command(args):
    """Check and display escalations."""
    system = AccountabilitySystem()
    
    escalations = system.check_timeouts_and_escalate()
    
    if not escalations:
        print("✅ No new escalations detected")
        return
    
    print(f"🚨 {len(escalations)} escalations detected:")
    print("=" * 50)
    
    for escalation in escalations:
        level_icon = {
            EscalationLevel.LOW: "🟡",
            EscalationLevel.MEDIUM: "🟠", 
            EscalationLevel.HIGH: "🔴",
            EscalationLevel.CRITICAL: "🚨",
            EscalationLevel.SYSTEM_FAILURE: "💥"
        }.get(escalation.level, "⚠️")
        
        print(f"{level_icon} {escalation.level.value.upper()}")
        print(f"   Agent: {escalation.agent_id}")
        print(f"   Task: {escalation.task_id}")
        print(f"   Reason: {escalation.reason}")
        print(f"   Time: {escalation.timestamp.strftime('%H:%M:%S')}")
        print()


def reassign_task_command(args):
    """Handle task reassignment."""
    system = AccountabilitySystem()
    
    success = system.reassign_task(
        task_id=args.task,
        new_agent_id=args.new_agent,
        reason=args.reason
    )
    
    if success:
        print(f"✅ Task {args.task} reassigned to {args.new_agent}")
        print(f"💬 Reason: {args.reason}")
    else:
        print(f"❌ Failed to reassign task {args.task}")


def agent_status_command(args):
    """Display agent status."""
    system = AccountabilitySystem()
    
    if args.all:
        # Show all agents
        all_agents = set(task.agent_id for task in system.active_tasks.values())
        
        print("👥 ALL AGENT STATUS")
        print("=" * 50)
        
        for agent_id in sorted(all_agents):
            status = system.get_agent_status(agent_id)
            
            print(f"🤖 {agent_id}")
            print(f"   Tasks: {status['total_tasks']} total, {status['active_tasks']} active")
            print(f"   Completed: {status['completed_tasks']}")
            print(f"   Issues: {status['overdue_tasks']} overdue, {status['blocked_tasks']} blocked")
            print(f"   Escalations: {status['escalation_count']}")
            print(f"   Last seen: {status['last_heartbeat'] or 'Never'}")
            print()
    
    else:
        # Show specific agent
        status = system.get_agent_status(args.agent)
        
        print(f"🤖 AGENT STATUS: {args.agent}")
        print("=" * 40)
        print(json.dumps(status, indent=2))


def system_status_command(args):
    """Display system status."""
    system = AccountabilitySystem()
    status = system.get_system_status()
    
    print("📊 ACCOUNTABILITY SYSTEM STATUS")
    print("=" * 40)
    
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print(f"📋 Tasks: {status['total_tasks']} total, {status['active_tasks']} active")
        print(f"✅ Completed: {status['completed_tasks']}")
        print(f"⚠️  Overdue: {status['overdue_tasks']}")
        print(f"🚫 Blocked: {status['blocked_tasks']}")
        print(f"🚨 Escalations: {status['total_escalations']} total, {status['critical_escalations']} critical")
        print(f"👥 Agents: {status['active_agents']}/{status['agents_tracked']} active")
        print(f"🕐 Updated: {status['timestamp']}")


def generate_report_command(args):
    """Generate comprehensive reports."""
    system = AccountabilitySystem()
    monitor = AccountabilityMonitor()
    
    if args.type == "accountability":
        report = system.generate_accountability_report()
        output_file = f"accountability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    elif args.type == "compliance":
        report = monitor.generate_compliance_report()
        output_file = f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    else:
        print(f"❌ Unknown report type: {args.type}")
        return
    
    # Save report
    if args.output:
        output_file = args.output
    
    report_path = Path(".claude/reports") / output_file
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"📄 Report generated: {report_path}")
    
    if args.summary:
        print("\n📊 REPORT SUMMARY:")
        print("=" * 30)
        
        if args.type == "accountability":
            status = report['system_status']
            print(f"Tasks: {status['active_tasks']} active, {status['completed_tasks']} completed")
            print(f"Issues: {status['overdue_tasks']} overdue, {status['blocked_tasks']} blocked")
            print(f"Agents: {len(report['agent_summaries'])} tracked")
            
        elif args.type == "compliance":
            system_comp = report['system_compliance']
            print(f"Average compliance: {system_comp['average_score']}%")
            print(f"Critical agents: {system_comp['critical_agents']}")
            print(f"Excellent agents: {system_comp['excellent_agents']}")


def interactive_mode():
    """Run interactive accountability management."""
    system = AccountabilitySystem()
    
    print("🚨 INTERACTIVE ACCOUNTABILITY SYSTEM")
    print("=" * 40)
    print("Commands: status, agents, escalations, assign, update, quit")
    print()
    
    while True:
        try:
            command = input("accountability> ").strip().lower()
            
            if command == "quit" or command == "exit":
                break
                
            elif command == "status":
                status = system.get_system_status()
                print(f"📊 {status['active_tasks']} active tasks, {status['critical_escalations']} critical escalations")
                
            elif command == "agents":
                all_agents = set(task.agent_id for task in system.active_tasks.values())
                for agent_id in sorted(all_agents):
                    status = system.get_agent_status(agent_id)
                    print(f"🤖 {agent_id}: {status['active_tasks']} active, {status['escalation_count']} escalations")
                    
            elif command == "escalations":
                escalations = system.check_timeouts_and_escalate()
                if escalations:
                    for esc in escalations:
                        print(f"🚨 {esc.agent_id}: {esc.reason}")
                else:
                    print("✅ No escalations")
                    
            elif command == "assign":
                agent = input("Agent ID: ")
                title = input("Task title: ")
                description = input("Description: ")
                hours = int(input("Deadline (hours): "))
                
                task_id = system.assign_task(agent, title, description, hours)
                print(f"✅ Assigned task: {task_id}")
                
            elif command == "update":
                task = input("Task ID: ")
                agent = input("Agent ID: ")
                progress = int(input("Progress (0-100): "))
                summary = input("Status summary: ")
                
                success = system.update_task_progress(agent, task, progress, summary)
                if success:
                    print("✅ Progress updated")
                else:
                    print("❌ Update failed")
                    
            elif command == "help":
                print("Commands: status, agents, escalations, assign, update, quit")
                
            else:
                print(f"Unknown command: {command}. Type 'help' for commands.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n👋 Accountability session ended")


def main():
    parser = argparse.ArgumentParser(description="Accountability System CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Assign task
    assign_parser = subparsers.add_parser('assign', help='Assign task to agent')
    assign_parser.add_argument('--agent', required=True, help='Agent ID')
    assign_parser.add_argument('--title', required=True, help='Task title')
    assign_parser.add_argument('--description', required=True, help='Task description')
    assign_parser.add_argument('--deadline', type=int, required=True, help='Deadline in hours')
    assign_parser.add_argument('--priority', type=float, default=1.0, help='Priority level')
    
    # Update progress
    progress_parser = subparsers.add_parser('update', help='Update task progress')
    progress_parser.add_argument('--agent', required=True, help='Agent ID')
    progress_parser.add_argument('--task', required=True, help='Task ID')
    progress_parser.add_argument('--progress', type=int, required=True, help='Progress percentage')
    progress_parser.add_argument('--summary', required=True, help='Status summary')
    progress_parser.add_argument('--evidence', help='Evidence files (comma-separated)')
    progress_parser.add_argument('--blockers', help='Blockers (comma-separated)')
    progress_parser.add_argument('--eta', type=int, help='ETA in minutes')
    progress_parser.add_argument('--confidence', type=int, default=100, help='Confidence level')
    
    # Check escalations
    escalations_parser = subparsers.add_parser('escalations', help='Check escalations')
    
    # Reassign task
    reassign_parser = subparsers.add_parser('reassign', help='Reassign task')
    reassign_parser.add_argument('--task', required=True, help='Task ID')
    reassign_parser.add_argument('--new-agent', required=True, help='New agent ID')
    reassign_parser.add_argument('--reason', required=True, help='Reassignment reason')
    
    # Agent status
    agent_parser = subparsers.add_parser('agent', help='Show agent status')
    agent_parser.add_argument('--agent', help='Specific agent ID')
    agent_parser.add_argument('--all', action='store_true', help='Show all agents')
    
    # System status
    status_parser = subparsers.add_parser('status', help='Show system status')
    status_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Generate reports
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--type', choices=['accountability', 'compliance'], 
                              required=True, help='Report type')
    report_parser.add_argument('--output', help='Output file name')
    report_parser.add_argument('--summary', action='store_true', help='Show summary')
    
    # Interactive mode
    interactive_parser = subparsers.add_parser('interactive', help='Interactive mode')
    
    args = parser.parse_args()
    
    if args.command == 'assign':
        assign_task_command(args)
    elif args.command == 'update':
        update_progress_command(args)
    elif args.command == 'escalations':
        check_escalations_command(args)
    elif args.command == 'reassign':
        reassign_task_command(args)
    elif args.command == 'agent':
        agent_status_command(args)
    elif args.command == 'status':
        system_status_command(args)
    elif args.command == 'report':
        generate_report_command(args)
    elif args.command == 'interactive':
        interactive_mode()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()