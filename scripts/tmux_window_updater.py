#!/usr/bin/env python3
"""
Auto-updating Tmux Window Names for Agent Hive
Updates window names with format: PREFIX-FOCUS-STATUS_EMOTICON
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

class TmuxWindowUpdater:
    """Updates tmux window names with agent status and focus."""
    
    def __init__(self, session_name: str = "agent-hive"):
        self.session_name = session_name
        self.agent_mapping = {
            'performance': 'PERF',
            'security': 'SEC',
            'frontend': 'FE',
            'pm-agent-new': 'PM',
            'integration': 'INT'
        }
        self.status_emoticons = {
            'idle': '⏸️',
            'working': '🔄',
            'waiting': '⏳',
            'completed': '✅',
            'error': '❌',
            'paused': '⏸️',
            'blocked': '🚫',
            'reviewing': '👀',
            'testing': '🧪',
            'deploying': '🚀'
        }
        
    def get_agent_status(self, agent_name: str) -> Dict[str, str]:
        """Get agent status from various sources."""
        try:
            # Check if agent is in tmux session
            result = subprocess.run(
                ['tmux', 'list-windows', '-t', self.session_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return {'status': 'error', 'focus': 'NotFound'}
            
            # Map agent names to actual window names
            window_mapping = {
                'performance': 'PERF-Input-⏳',
                'security': 'SEC-Input-⏳', 
                'frontend': 'FE-Input-⏳',
                'pm-agent-new': 'PM-Input-⏳'
            }
            
            # Find the actual window name
            agent_window = window_mapping.get(agent_name, f"agent-{agent_name}")
            try:
                pane_result = subprocess.run(
                    ['tmux', 'capture-pane', '-t', f"{self.session_name}:{agent_window}", '-p'],
                    capture_output=True, text=True
                )
                
                if pane_result.returncode == 0:
                    pane_content = pane_result.stdout.strip()
                    return self._analyze_pane_content(pane_content)
                    
            except Exception as e:
                logger.warning(f"Could not capture pane for {agent_name}: {e}")
                
            return {'status': 'idle', 'focus': 'Unknown'}
            
        except Exception as e:
            logger.error(f"Error getting agent status for {agent_name}: {e}")
            return {'status': 'error', 'focus': 'Error'}
    
    def _analyze_pane_content(self, content: str) -> Dict[str, str]:
        """Analyze pane content to determine status and focus."""
        lines = content.split('\n')
        last_lines = lines[-5:]  # Check last 5 lines
        
        # Check for common patterns
        if any('-- INSERT --' in line for line in last_lines):
            return {'status': 'waiting', 'focus': 'Input'}
        elif any('Context left until auto-compact:' in line for line in last_lines):
            return {'status': 'working', 'focus': 'Processing'}
        elif any('>' in line and line.strip() == '>' for line in last_lines):
            return {'status': 'idle', 'focus': 'Ready'}
        elif any('✅' in line for line in last_lines):
            return {'status': 'completed', 'focus': 'Done'}
        elif any('❌' in line for line in last_lines):
            return {'status': 'error', 'focus': 'Failed'}
        elif any('test' in line.lower() for line in last_lines):
            return {'status': 'testing', 'focus': 'Testing'}
        elif any('commit' in line.lower() for line in last_lines):
            return {'status': 'deploying', 'focus': 'Commit'}
        
        return {'status': 'idle', 'focus': 'Unknown'}
    
    def update_window_name(self, agent_name: str, prefix: str, focus: str, status: str):
        """Update tmux window name with new format."""
        try:
            status_emoji = self.status_emoticons.get(status, '❓')
            new_name = f"{prefix}-{focus}-{status_emoji}"
            
            # Update tmux window name
            subprocess.run([
                'tmux', 'rename-window', '-t', 
                f"{self.session_name}:agent-{agent_name}", 
                new_name
            ], check=True)
            
            logger.info(f"Updated {agent_name} window to: {new_name}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update window name for {agent_name}: {e}")
    
    def get_current_windows(self) -> List[str]:
        """Get current tmux windows."""
        try:
            result = subprocess.run(
                ['tmux', 'list-windows', '-t', self.session_name, '-F', '#{window_name}'],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip().split('\n')
        except subprocess.CalledProcessError:
            return []
    
    def update_all_windows(self):
        """Update all agent windows."""
        logger.info("Updating all agent window names...")
        
        for agent_name, prefix in self.agent_mapping.items():
            try:
                status_info = self.get_agent_status(agent_name)
                self.update_window_name(
                    agent_name, 
                    prefix, 
                    status_info['focus'], 
                    status_info['status']
                )
            except Exception as e:
                logger.error(f"Error updating {agent_name}: {e}")
    
    def continuous_update(self, interval: int = 30):
        """Continuously update window names."""
        logger.info(f"Starting continuous updates every {interval} seconds...")
        
        while True:
            try:
                self.update_all_windows()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Stopping continuous updates...")
                break
            except Exception as e:
                logger.error(f"Error in continuous update: {e}")
                time.sleep(interval)

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update tmux window names for agents')
    parser.add_argument('--session', default='agent-hive', help='Tmux session name')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=30, help='Update interval in seconds')
    
    args = parser.parse_args()
    
    updater = TmuxWindowUpdater(args.session)
    
    if args.continuous:
        updater.continuous_update(args.interval)
    else:
        updater.update_all_windows()

if __name__ == "__main__":
    main()