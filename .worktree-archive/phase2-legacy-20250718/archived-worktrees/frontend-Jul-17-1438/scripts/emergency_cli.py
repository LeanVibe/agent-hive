#!/usr/bin/env python3
"""
Emergency Completion CLI Wrapper
=================================

Quick access interface for emergency completion functionality.
Integrates with existing LeanVibe CLI for seamless workflow automation.

Usage:
    python scripts/emergency_cli.py --task "Task Name"
    python scripts/emergency_cli.py --emergency --force
"""

import sys
import subprocess

def main():
    """Quick emergency completion wrapper."""
    if len(sys.argv) < 2:
        print("🚨 EMERGENCY COMPLETION CLI")
        print("=" * 40)
        print("Quick commands:")
        print("  emergency-complete <task>     - Emergency complete with defaults")
        print("  emergency-force <task>        - Force complete with emergency settings")
        print("  emergency-milestone <task>    - Milestone completion")
        print("")
        print("Full usage:")
        print("  python scripts/emergency_complete.py --help")
        return
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Preset commands for common emergency scenarios
    emergency_commands = {
        "emergency-complete": [
            "python", "scripts/emergency_complete.py",
            "--template-type", "emergency",
            "--force"
        ],
        "emergency-force": [
            "python", "scripts/emergency_complete.py", 
            "--template-type", "emergency",
            "--force", "--emergency"
        ],
        "emergency-milestone": [
            "python", "scripts/emergency_complete.py",
            "--template-type", "milestone",
            "--force"
        ]
    }
    
    if command in emergency_commands:
        cmd = emergency_commands[command]
        if args:
            cmd.extend(["--task"] + args)
        
        print(f"🚨 Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    else:
        # Pass through to main emergency completion script
        cmd = ["python", "scripts/emergency_complete.py"] + sys.argv[1:]
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()