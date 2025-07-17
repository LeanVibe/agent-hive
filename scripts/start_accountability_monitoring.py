#!/usr/bin/env python3
"""
Accountability Framework Launcher
Starts automated accountability monitoring system.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.accountability_framework import AccountabilityFramework

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('.claude/logs/accountability.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class AccountabilityLauncher:
    """Launcher for accountability monitoring system."""
    
    def __init__(self):
        self.framework = AccountabilityFramework()
        self.running = False
    
    async def start(self):
        """Start accountability monitoring."""
        try:
            print("🚀 Starting Automated Accountability Framework...")
            print("📋 Configuration:")
            print("   - Default deadline: 4 hours")
            print("   - Checkpoint intervals: 25%, 50%, 75%, 100%")
            print("   - Escalation levels: WARNING → CRITICAL → URGENT → EMERGENCY")
            print("   - Max reassignments: 2 per task")
            print("   - Monitoring interval: 60 seconds")
            print()
            
            await self.framework.start_monitoring()
            self.running = True
            
            print("✅ Accountability monitoring active")
            print("📊 Use Ctrl+C to stop monitoring")
            print()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(60)
                
                # Generate periodic status report
                report = await self.framework.generate_accountability_report()
                if report["summary"]["total_tasks"] > 0:
                    print(f"📈 Status: {report['summary']['completed_tasks']}/{report['summary']['total_tasks']} tasks completed "
                          f"({report['summary']['completion_rate']}% success rate)")
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping accountability monitoring...")
            await self.stop()
        except Exception as e:
            logger.error(f"Accountability monitoring error: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop accountability monitoring."""
        if self.framework.monitoring_active:
            await self.framework.stop_monitoring()
        self.running = False
        print("✅ Accountability monitoring stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n🔄 Shutdown signal received...")
    # Will be caught by KeyboardInterrupt in main loop


if __name__ == "__main__":
    # Handle shutdown signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    launcher = AccountabilityLauncher()
    asyncio.run(launcher.start())