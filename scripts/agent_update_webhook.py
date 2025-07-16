#!/usr/bin/env python3
"""
Agent Update Webhook - Integration point for agent status monitoring
Triggered when agents post updates to automatically notify PM system.
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def trigger_agent_update_processing(agent_name: str, update_content: str, update_type: str = "status"):
    """Main entry point for processing agent updates"""
    
    project_root = Path(__file__).parent.parent
    
    logger.info(f"📨 Processing update from {agent_name}")
    
    try:
        # Step 1: Record the update via status monitor
        monitor_cmd = [
            "python", ".claude/hooks/agent_status_monitor.py",
            "--agent", agent_name,
            "--type", update_type,
            "--content", update_content
        ]
        
        monitor_result = subprocess.run(
            monitor_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if monitor_result.returncode != 0:
            logger.error(f"❌ Status monitor failed: {monitor_result.stderr}")
            return False
        
        # Step 2: Trigger PM evaluation
        evaluator_cmd = [
            "python", ".claude/hooks/pm_auto_evaluator.py", 
            "--agent", agent_name,
            "--status", update_content
        ]
        
        evaluator_result = subprocess.run(
            evaluator_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if evaluator_result.returncode == 0:
            logger.info(f"✅ PM evaluation completed for {agent_name}")
            logger.info(f"📊 Result: {evaluator_result.stdout.strip()}")
        else:
            logger.error(f"❌ PM evaluation failed: {evaluator_result.stderr}")
            
        # Step 3: Check for idle agents (background task)
        idle_check_cmd = [
            "python", ".claude/hooks/agent_status_monitor.py",
            "--check-idle"
        ]
        
        subprocess.Popen(
            idle_check_cmd,
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Exception processing update from {agent_name}: {e}")
        return False

def integrate_with_agent_communication():
    """Integration point to hook into existing agent communication"""
    
    # This would be called from the agent communication system
    # when messages are sent/received
    
    integration_code = '''
# Add this to scripts/fixed_agent_communication.py after message sending:

# Trigger update processing
if result.returncode == 0:
    try:
        from agent_update_webhook import trigger_agent_update_processing
        trigger_agent_update_processing(
            agent_name=agent_name,
            update_content=message,
            update_type="outbound_message"
        )
    except ImportError:
        pass  # Webhook not available
'''
    
    print(integration_code)
    return integration_code

def main():
    """CLI interface for webhook testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Update Webhook")
    parser.add_argument("--agent", required=True, help="Agent name")
    parser.add_argument("--content", required=True, help="Update content")
    parser.add_argument("--type", default="status", help="Update type")
    parser.add_argument("--integrate", action="store_true", help="Show integration code")
    
    args = parser.parse_args()
    
    if args.integrate:
        integrate_with_agent_communication()
        return
    
    success = trigger_agent_update_processing(args.agent, args.content, args.type)
    
    if success:
        print(f"✅ Successfully processed update from {args.agent}")
        sys.exit(0)
    else:
        print(f"❌ Failed to process update from {args.agent}")
        sys.exit(1)

if __name__ == "__main__":
    main()