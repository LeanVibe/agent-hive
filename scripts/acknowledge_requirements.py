#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Agent Requirements Acknowledgment System

This script implements the mandatory acknowledgment system for agent requirements.
All agents must acknowledge understanding of workflow rules before starting work.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Constants
REQUIREMENTS_VERSION = "1.0"
ACKNOWLEDGMENT_DIR = Path("acknowledgments")
REQUIREMENTS_FILE = Path("AGENT_REQUIREMENTS.md")

class RequirementsAcknowledgment:
    """Handles agent acknowledgment of requirements"""
    
    def __init__(self):
        """Initialize acknowledgment system"""
        self.acknowledgment_dir = ACKNOWLEDGMENT_DIR
        self.acknowledgment_dir.mkdir(exist_ok=True)
        
        # Ensure requirements file exists
        if not REQUIREMENTS_FILE.exists():
            print(f"❌ ERROR: Requirements file {REQUIREMENTS_FILE} not found")
            sys.exit(1)
    
    def acknowledge_requirements(self, agent_name: str, version: str = REQUIREMENTS_VERSION) -> bool:
        """
        Record agent acknowledgment of requirements
        
        Args:
            agent_name: Name of the agent acknowledging requirements
            version: Version of requirements being acknowledged
            
        Returns:
            bool: True if acknowledgment successful, False otherwise
        """
        try:
            # Create acknowledgment record
            acknowledgment = {
                "agent": agent_name,
                "version": version,
                "timestamp": datetime.now().isoformat(),
                "requirements_understood": True,
                "pr_size_limit_confirmed": True,
                "quality_gates_accepted": True,
                "communication_protocols_acknowledged": True,
                "escalation_procedures_confirmed": True,
                "compliance_validated": True
            }
            
            # Save acknowledgment
            ack_file = self.acknowledgment_dir / f"{agent_name}_v{version}.json"
            with open(ack_file, 'w') as f:
                json.dump(acknowledgment, f, indent=2)
            
            print(f"✅ ACKNOWLEDGMENT RECORDED: {agent_name} v{version}")
            print(f"📅 Timestamp: {acknowledgment['timestamp']}")
            print(f"📁 File: {ack_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR recording acknowledgment: {e}")
            return False
    
    def check_acknowledgment(self, agent_name: str, version: str = REQUIREMENTS_VERSION) -> bool:
        """
        Check if agent has acknowledged requirements
        
        Args:
            agent_name: Name of the agent to check
            version: Version of requirements to check
            
        Returns:
            bool: True if agent has acknowledged, False otherwise
        """
        try:
            ack_file = self.acknowledgment_dir / f"{agent_name}_v{version}.json"
            
            if not ack_file.exists():
                return False
            
            with open(ack_file, 'r') as f:
                acknowledgment = json.load(f)
            
            # Validate acknowledgment completeness
            required_fields = [
                "requirements_understood",
                "pr_size_limit_confirmed", 
                "quality_gates_accepted",
                "communication_protocols_acknowledged",
                "escalation_procedures_confirmed",
                "compliance_validated"
            ]
            
            for field in required_fields:
                if not acknowledgment.get(field, False):
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR checking acknowledgment: {e}")
            return False
    
    def list_acknowledgments(self) -> list:
        """
        List all agent acknowledgments
        
        Returns:
            list: List of acknowledgment records
        """
        acknowledgments = []
        
        try:
            for ack_file in self.acknowledgment_dir.glob("*.json"):
                with open(ack_file, 'r') as f:
                    acknowledgment = json.load(f)
                    acknowledgments.append(acknowledgment)
            
            return sorted(acknowledgments, key=lambda x: x.get('timestamp', ''))
            
        except Exception as e:
            print(f"❌ ERROR listing acknowledgments: {e}")
            return []
    
    def validate_agent_compliance(self, agent_name: str) -> bool:
        """
        Validate agent compliance with requirements
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            bool: True if compliant, False otherwise
        """
        if not self.check_acknowledgment(agent_name):
            print(f"❌ COMPLIANCE FAILURE: {agent_name} has not acknowledged requirements v{REQUIREMENTS_VERSION}")
            print(f"🛡️ ACTION REQUIRED: Run acknowledgment before starting work")
            return False
        
        print(f"✅ COMPLIANCE VERIFIED: {agent_name} has acknowledged requirements v{REQUIREMENTS_VERSION}")
        return True
    
    def display_requirements_summary(self):
        """Display summary of key requirements"""
        print("\n🛡️ LEANVIBE AGENT REQUIREMENTS SUMMARY")
        print("=" * 50)
        print("⚠️  CRITICAL: <500 LINE PR LIMIT - NO EXCEPTIONS")
        print("✅ Quality gates required before all commits")
        print("📊 Status updates every 2 hours during work")
        print("🚨 Escalation required for architecture/security changes")
        print("🔄 Autonomous operation within defined boundaries")
        print("📋 Documentation updates required with all changes")
        print("🎯 Compliance validation before starting work")
        print("=" * 50)
        print(f"📖 Full requirements: {REQUIREMENTS_FILE}")
        print(f"🔢 Version: {REQUIREMENTS_VERSION}")
        print()

def main():
    """Main CLI interface for acknowledgment system"""
    parser = argparse.ArgumentParser(
        description="LeanVibe Agent Requirements Acknowledgment System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Acknowledge requirements as an agent
  python acknowledge_requirements.py --agent frontend-agent --acknowledge
  
  # Check if agent has acknowledged
  python acknowledge_requirements.py --agent frontend-agent --check
  
  # List all acknowledgments
  python acknowledge_requirements.py --list
  
  # Validate compliance before work
  python acknowledge_requirements.py --agent frontend-agent --validate
        """
    )
    
    parser.add_argument(
        '--agent',
        required=False,
        help='Agent name for acknowledgment operations'
    )
    
    parser.add_argument(
        '--acknowledge',
        action='store_true',
        help='Acknowledge requirements (requires --agent)'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check if agent has acknowledged requirements'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate agent compliance before work'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all acknowledgments'
    )
    
    parser.add_argument(
        '--version',
        default=REQUIREMENTS_VERSION,
        help=f'Requirements version (default: {REQUIREMENTS_VERSION})'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Display requirements summary'
    )
    
    args = parser.parse_args()
    
    # Initialize acknowledgment system
    ack_system = RequirementsAcknowledgment()
    
    # Display summary if requested
    if args.summary:
        ack_system.display_requirements_summary()
        return
    
    # Handle acknowledgment
    if args.acknowledge:
        if not args.agent:
            print("❌ ERROR: --agent required for acknowledgment")
            sys.exit(1)
        
        print(f"🛡️ REQUIREMENTS ACKNOWLEDGMENT: {args.agent}")
        ack_system.display_requirements_summary()
        
        # Confirm acknowledgment
        confirm = input("Do you acknowledge and agree to follow ALL requirements? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ ACKNOWLEDGMENT CANCELLED: 'yes' required for compliance")
            sys.exit(1)
        
        success = ack_system.acknowledge_requirements(args.agent, args.version)
        if success:
            print("✅ REQUIREMENTS ACKNOWLEDGED SUCCESSFULLY")
        else:
            print("❌ ACKNOWLEDGMENT FAILED")
            sys.exit(1)
    
    # Handle check
    elif args.check:
        if not args.agent:
            print("❌ ERROR: --agent required for check")
            sys.exit(1)
        
        has_acknowledged = ack_system.check_acknowledgment(args.agent, args.version)
        if has_acknowledged:
            print(f"✅ ACKNOWLEDGED: {args.agent} has acknowledged requirements v{args.version}")
        else:
            print(f"❌ NOT ACKNOWLEDGED: {args.agent} has not acknowledged requirements v{args.version}")
            sys.exit(1)
    
    # Handle validation
    elif args.validate:
        if not args.agent:
            print("❌ ERROR: --agent required for validation")
            sys.exit(1)
        
        is_compliant = ack_system.validate_agent_compliance(args.agent)
        if not is_compliant:
            sys.exit(1)
    
    # Handle list
    elif args.list:
        acknowledgments = ack_system.list_acknowledgments()
        
        if not acknowledgments:
            print("📋 No acknowledgments found")
            return
        
        print(f"📋 AGENT ACKNOWLEDGMENTS (Total: {len(acknowledgments)})")
        print("=" * 60)
        
        for ack in acknowledgments:
            print(f"🤖 Agent: {ack['agent']}")
            print(f"🔢 Version: {ack['version']}")
            print(f"📅 Timestamp: {ack['timestamp']}")
            print(f"✅ Compliant: {all(ack.get(field, False) for field in [
                'requirements_understood',
                'pr_size_limit_confirmed',
                'quality_gates_accepted',
                'communication_protocols_acknowledged'
            ])}")
            print("-" * 40)
    
    # Default help
    else:
        parser.print_help()
        print("\n🛡️ PREVENTION-FIRST APPROACH")
        print("All agents must acknowledge requirements before starting work.")
        print("Use --summary to see key requirements.")

if __name__ == '__main__':
    main()