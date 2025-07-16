#!/usr/bin/env python3
"""
Start Agent Status Enforcement Monitoring

Launcher script for the automated status enforcement system.
Runs the monitoring system in the background with proper logging.
"""

import asyncio
import subprocess
import sys
from pathlib import Path


def main():
    """Start the enforcement monitoring system."""
    print("🚀 Starting Agent Status Enforcement System...")
    
    # Ensure we're in the right directory
    base_dir = Path(__file__).parent.parent
    
    try:
        # Start the monitoring system
        result = subprocess.run([
            sys.executable, 
            str(base_dir / "scripts" / "agent_status_enforcer.py"),
            "--start"
        ], cwd=base_dir)
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Failed to start monitoring: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())