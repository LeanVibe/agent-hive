#!/usr/bin/env python3
"""
Agent Finalization Script
Gracefully finalizes all agents' work and prepares for sprint transition.
"""

import json
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentFinalizer:
    """Finalizes agent work and prepares for sprint transition."""
    
    def __init__(self, session_name: str = "agent-hive"):
        self.session_name = session_name
        self.agents = ['performance', 'security', 'frontend', 'pm-agent-new']
        self.finalization_report = {
            'timestamp': datetime.now().isoformat(),
            'session': session_name,
            'agents': {}
        }
        
    def send_finalization_command(self, agent_name: str) -> bool:
        """Send finalization command to agent."""
        try:
            # Send completion command
            result = subprocess.run([
                'python', 'scripts/fixed_agent_communication.py',
                '--agent', agent_name,
                '--message', 'FINALIZE: Complete current task, commit any changes, and respond with final status for sprint transition.'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Sent finalization command to {agent_name}")
                return True
            else:
                logger.error(f"❌ Failed to send finalization command to {agent_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending finalization command to {agent_name}: {e}")
            return False
    
    def wait_for_agent_response(self, agent_name: str, timeout: int = 120) -> Dict[str, Any]:
        """Wait for agent to respond with finalization status."""
        logger.info(f"⏳ Waiting for {agent_name} to finalize (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check agent's current state
                result = subprocess.run([
                    'tmux', 'capture-pane', '-t', 
                    f"{self.session_name}:agent-{agent_name}", '-p'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    content = result.stdout.strip()
                    
                    # Check for completion indicators
                    if any(keyword in content.lower() for keyword in ['completed', 'finished', 'done', 'finalized']):
                        logger.info(f"✅ {agent_name} reported completion")
                        return {
                            'status': 'completed',
                            'timestamp': datetime.now().isoformat(),
                            'final_output': content[-500:]  # Last 500 chars
                        }
                    elif any(keyword in content.lower() for keyword in ['error', 'failed', 'exception']):
                        logger.warning(f"⚠️ {agent_name} reported error")
                        return {
                            'status': 'error',
                            'timestamp': datetime.now().isoformat(),
                            'final_output': content[-500:]
                        }
                    
            except Exception as e:
                logger.error(f"Error checking {agent_name}: {e}")
            
            time.sleep(5)  # Check every 5 seconds
        
        # Timeout reached
        logger.warning(f"⏰ {agent_name} finalization timeout reached")
        return {
            'status': 'timeout',
            'timestamp': datetime.now().isoformat(),
            'final_output': 'Timeout waiting for finalization'
        }
    
    def force_finalize_agent(self, agent_name: str) -> Dict[str, Any]:
        """Force finalize an agent that didn't respond."""
        logger.warning(f"🔄 Force finalizing {agent_name}...")
        
        try:
            # Send Ctrl+C to interrupt any running process
            subprocess.run([
                'tmux', 'send-keys', '-t', 
                f"{self.session_name}:agent-{agent_name}", 'C-c'
            ], timeout=5)
            
            time.sleep(2)
            
            # Send exit command
            subprocess.run([
                'tmux', 'send-keys', '-t', 
                f"{self.session_name}:agent-{agent_name}", 'exit', 'Enter'
            ], timeout=5)
            
            return {
                'status': 'force_finalized',
                'timestamp': datetime.now().isoformat(),
                'final_output': 'Agent was force finalized'
            }
            
        except Exception as e:
            logger.error(f"❌ Error force finalizing {agent_name}: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'final_output': f'Error during force finalization: {e}'
            }
    
    def finalize_all_agents(self, timeout: int = 120) -> Dict[str, Any]:
        """Finalize all agents."""
        logger.info("🎯 Starting agent finalization process...")
        
        # Send finalization commands to all agents
        for agent_name in self.agents:
            success = self.send_finalization_command(agent_name)
            self.finalization_report['agents'][agent_name] = {
                'finalization_sent': success,
                'start_time': datetime.now().isoformat()
            }
        
        # Wait for responses
        for agent_name in self.agents:
            if self.finalization_report['agents'][agent_name]['finalization_sent']:
                response = self.wait_for_agent_response(agent_name, timeout)
                self.finalization_report['agents'][agent_name].update(response)
            else:
                self.finalization_report['agents'][agent_name]['status'] = 'failed_to_send'
        
        # Force finalize any agents that didn't respond
        for agent_name in self.agents:
            agent_data = self.finalization_report['agents'][agent_name]
            if agent_data.get('status') in ['timeout', 'failed_to_send']:
                force_result = self.force_finalize_agent(agent_name)
                agent_data.update(force_result)
        
        # Generate summary
        completed = sum(1 for agent_data in self.finalization_report['agents'].values() 
                       if agent_data.get('status') == 'completed')
        total = len(self.agents)
        
        logger.info(f"📊 Finalization complete: {completed}/{total} agents completed successfully")
        
        return self.finalization_report
    
    def save_finalization_report(self, report_path: str = "finalization_report.json"):
        """Save finalization report to file."""
        try:
            with open(report_path, 'w') as f:
                json.dump(self.finalization_report, f, indent=2)
            logger.info(f"📄 Finalization report saved to {report_path}")
        except Exception as e:
            logger.error(f"❌ Error saving finalization report: {e}")
    
    def prepare_for_next_sprint(self):
        """Prepare system for next sprint."""
        logger.info("🚀 Preparing for next sprint...")
        
        # Update window names to show finalized status
        try:
            subprocess.run(['python', 'scripts/tmux_window_updater.py'], timeout=30)
            logger.info("✅ Updated tmux window names")
        except Exception as e:
            logger.error(f"❌ Error updating window names: {e}")
        
        # Create sprint transition summary
        sprint_summary = {
            'transition_date': datetime.now().isoformat(),
            'finalized_agents': len(self.agents),
            'ready_for_sprint': True,
            'next_actions': [
                'Review finalization report',
                'Plan next sprint objectives',
                'Restart agents with new tasks',
                'Monitor system health'
            ]
        }
        
        try:
            with open('sprint_transition_summary.json', 'w') as f:
                json.dump(sprint_summary, f, indent=2)
            logger.info("📋 Sprint transition summary created")
        except Exception as e:
            logger.error(f"❌ Error creating sprint summary: {e}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Finalize all agents for sprint transition')
    parser.add_argument('--session', default='agent-hive', help='Tmux session name')
    parser.add_argument('--timeout', type=int, default=120, help='Timeout per agent in seconds')
    parser.add_argument('--force', action='store_true', help='Skip waiting and force finalize')
    
    args = parser.parse_args()
    
    finalizer = AgentFinalizer(args.session)
    
    if args.force:
        # Force finalize all agents immediately
        for agent_name in finalizer.agents:
            result = finalizer.force_finalize_agent(agent_name)
            finalizer.finalization_report['agents'][agent_name] = result
    else:
        # Normal finalization process
        finalizer.finalize_all_agents(args.timeout)
    
    # Save report and prepare for next sprint
    finalizer.save_finalization_report()
    finalizer.prepare_for_next_sprint()
    
    logger.info("🎉 Agent finalization process completed!")

if __name__ == "__main__":
    main()