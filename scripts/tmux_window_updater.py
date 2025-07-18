#!/usr/bin/env python3
"""
Tmux Window Updater with Real-time Agent Status
Updates window names with format: PREFIX-ACTIVITY-STATUS_EMOTICON

Based on Gemini CLI evaluation recommendations:
- Performance: Capture only last 50 lines of pane content
- Robustness: Error handling and lock file mechanism
- UX: Focus indicator (🎯) for active window
- Prioritization: Clear priority order for pattern matching
"""

import subprocess
import time
import re
import json
import argparse
import sys
import os
import signal
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentWindowUpdater:
    def __init__(self, config_path: Optional[str] = None):
        self.session_name = "agent-hive"
        self.update_interval = 30
        self.lock_file = Path(".tmux_updater.lock")
        self.running = False
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Activity patterns (in priority order - first match wins)
        self.activity_patterns = {
            'error': [
                r'^Error:',
                r'Exception:',
                r'traceback',
                r'Failed:',
                r'FAILED',
                r'❌'
            ],
            'crisis': [
                r'CRISIS',
                r'EMERGENCY',
                r'CRITICAL',
                r'URGENT',
                r'🚨'
            ],
            'complete': [
                r'✅ Complete',
                r'SUCCESS',
                r'✅ Done',
                r'Finished',
                r'Task completed'
            ],
            'processing': [
                r'Processing',
                r'Analyzing',
                r'Generating',
                r'Working on',
                r'Implementing',
                r'Creating'
            ],
            'thinking': [
                r'Thinking',
                r'Planning',
                r'Considering',
                r'Evaluating',
                r'Reflecting'
            ],
            'testing': [
                r'Testing',
                r'Running tests',
                r'pytest',
                r'Validating'
            ],
            'reviewing': [
                r'Reviewing',
                r'Checking',
                r'Verifying',
                r'Auditing'
            ],
            'waiting': [
                r'-- INSERT --',
                r'waiting for',
                r'What should I',
                r'Please provide',
                r'>'
            ],
            'idle': [
                r'claude@',
                r'^\$',
                r'zsh',
                r'tmux'
            ]
        }
        
        # Status emoticons
        self.status_emoticons = {
            'error': '❌',
            'crisis': '🚨',
            'complete': '✅',
            'processing': '🔄',
            'thinking': '💭',
            'testing': '🧪',
            'reviewing': '👀',
            'waiting': '⏳',
            'idle': '⏸️',
            'focused': '🎯'
        }
        
        # Context patterns for activity detection
        self.context_patterns = {
            'security': ['security', 'vulnerability', 'audit', 'bandit', 'safety'],
            'performance': ['performance', 'mypy', 'technical debt', 'optimization'],
            'frontend': ['frontend', 'dashboard', 'UI', 'component', 'react'],
            'coordination': ['coordination', 'sprint', 'planning', 'agents', 'project'],
            'communication': ['communication', 'tmux', 'window', 'message'],
            'testing': ['test', 'pytest', 'coverage', 'validation']
        }
        
        # Window mapping (current format)
        self.window_mapping = {
            'SEC-Input-⏳': 'security',
            'PERF-Input-⏳': 'performance',
            'FE-Input-⏳': 'frontend',
            'PM-Input-⏳': 'pm'
        }
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file if provided"""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config {config_path}: {e}")
        return {}
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Clean up resources"""
        if self.lock_file.exists():
            try:
                self.lock_file.unlink()
                logger.info("Removed lock file")
            except Exception as e:
                logger.error(f"Failed to remove lock file: {e}")
    
    def _acquire_lock(self) -> bool:
        """Acquire lock to prevent multiple instances"""
        if self.lock_file.exists():
            try:
                # Check if process is still running
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    logger.error(f"Another instance is running (PID: {pid})")
                    return False
                except OSError:
                    # Process doesn't exist, remove stale lock
                    self.lock_file.unlink()
                    logger.info("Removed stale lock file")
            except Exception as e:
                logger.error(f"Failed to check lock file: {e}")
                return False
        
        try:
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.info("Acquired lock")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False
    
    def check_tmux_session(self) -> bool:
        """Check if tmux session exists"""
        try:
            result = subprocess.run(
                ['tmux', 'list-sessions', '-F', '#{session_name}'],
                capture_output=True, text=True, timeout=5
            )
            return self.session_name in result.stdout
        except Exception as e:
            logger.error(f"Failed to check tmux session: {e}")
            return False
    
    def get_windows(self) -> List[Dict]:
        """Get list of windows with their status"""
        try:
            result = subprocess.run([
                'tmux', 'list-windows', '-t', self.session_name,
                '-F', '#{window_name}|#{window_active}|#{window_index}'
            ], capture_output=True, text=True, timeout=10)
            
            windows = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        windows.append({
                            'name': parts[0],
                            'active': parts[1] == '1',
                            'index': parts[2]
                        })
            return windows
        except Exception as e:
            logger.error(f"Failed to get windows: {e}")
            return []
    
    def capture_pane_content(self, window_name: str, lines: int = 50) -> str:
        """Capture last N lines of pane content for analysis"""
        try:
            result = subprocess.run([
                'tmux', 'capture-pane', '-t', f"{self.session_name}:{window_name}",
                '-p', '-S', f'-{lines}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"Failed to capture pane {window_name}: {result.stderr}")
                return ""
        except Exception as e:
            logger.error(f"Error capturing pane {window_name}: {e}")
            return ""
    
    def classify_status(self, content: str) -> str:
        """Classify agent status based on content (priority order)"""
        if not content:
            return 'idle'
        
        # Check patterns in priority order
        for status, patterns in self.activity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    return status
        
        return 'idle'
    
    def detect_context(self, content: str) -> str:
        """Detect what the agent is working on"""
        if not content:
            return 'general'
        
        # Count context matches
        context_scores = {}
        for context, patterns in self.context_patterns.items():
            score = 0
            for pattern in patterns:
                score += len(re.findall(pattern, content, re.IGNORECASE))
            if score > 0:
                context_scores[context] = score
        
        # Return highest scoring context
        if context_scores:
            return max(context_scores, key=context_scores.get)
        return 'general'
    
    def generate_window_name(self, agent_name: str, context: str, status: str, is_active: bool) -> str:
        """Generate descriptive window name with emoticon"""
        # Agent prefix mapping
        agent_prefixes = {
            'security': 'SEC',
            'performance': 'PERF',
            'frontend': 'FE',
            'pm': 'PM'
        }
        
        # Context activity mapping
        context_activities = {
            'security': 'Audit',
            'performance': 'Optimize',
            'frontend': 'Dashboard',
            'coordination': 'Coordinate',
            'communication': 'Communicate',
            'testing': 'Test',
            'general': 'Work'
        }
        
        prefix = agent_prefixes.get(agent_name, agent_name.upper()[:4])
        activity = context_activities.get(context, context.capitalize())
        emoticon = self.status_emoticons.get(status, '❓')
        
        # Add focus indicator for active window
        if is_active:
            emoticon = f"{self.status_emoticons['focused']}{emoticon}"
        
        return f"{prefix}-{activity}-{emoticon}"
    
    def update_window_name(self, window_index: str, new_name: str) -> bool:
        """Update tmux window name"""
        try:
            result = subprocess.run([
                'tmux', 'rename-window', '-t',
                f"{self.session_name}:{window_index}", new_name
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                logger.info(f"Updated window {window_index} -> {new_name}")
                return True
            else:
                logger.warning(f"Failed to update window {window_index}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error updating window {window_index}: {e}")
            return False
    
    def update_all_windows(self) -> int:
        """Update all agent windows with current status"""
        updated_count = 0
        
        try:
            windows = self.get_windows()
            if not windows:
                logger.warning("No windows found")
                return 0
            
            for window in windows:
                window_name = window['name']
                is_active = window['active']
                window_index = window['index']
                
                # Find agent name from window mapping
                agent_name = None
                for pattern, agent in self.window_mapping.items():
                    if window_name.startswith(pattern.split('-')[0]):
                        agent_name = agent
                        break
                
                if not agent_name:
                    logger.debug(f"No agent mapping found for window: {window_name}")
                    continue
                
                # Capture pane content
                content = self.capture_pane_content(window_name)
                
                # Classify status and detect context
                status = self.classify_status(content)
                context = self.detect_context(content)
                
                # Generate new window name
                new_name = self.generate_window_name(agent_name, context, status, is_active)
                
                # Update if name has changed
                if window_name != new_name:
                    if self.update_window_name(window_index, new_name):
                        updated_count += 1
                        logger.info(f"Updated {window_name} -> {new_name}")
                    else:
                        logger.error(f"Failed to update {window_name}")
                
        except Exception as e:
            logger.error(f"Error in update_all_windows: {e}")
        
        return updated_count
    
    def monitor_continuously(self):
        """Run continuous monitoring and updates"""
        logger.info(f"Starting continuous monitoring every {self.update_interval} seconds...")
        self.running = True
        
        while self.running:
            try:
                # Check if tmux session still exists
                if not self.check_tmux_session():
                    logger.error(f"Tmux session '{self.session_name}' not found")
                    break
                
                # Update all windows
                updated_count = self.update_all_windows()
                logger.debug(f"Updated {updated_count} windows")
                
                # Sleep for interval
                time.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.update_interval)
        
        logger.info("Monitoring stopped")
    
    def test_update(self):
        """Test update functionality once"""
        logger.info("Testing window update functionality...")
        
        if not self.check_tmux_session():
            logger.error(f"Tmux session '{self.session_name}' not found")
            return False
        
        updated_count = self.update_all_windows()
        logger.info(f"Test completed: {updated_count} windows updated")
        return updated_count > 0

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Tmux Window Updater with Real-time Agent Status")
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('--test', action='store_true', help='Test update functionality once')
    parser.add_argument('--interval', type=int, default=30, help='Update interval in seconds')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create updater
    updater = AgentWindowUpdater(args.config)
    updater.update_interval = args.interval
    
    if args.test:
        # Test mode
        success = updater.test_update()
        sys.exit(0 if success else 1)
    
    elif args.daemon:
        # Daemon mode
        if not updater._acquire_lock():
            sys.exit(1)
        
        try:
            updater.monitor_continuously()
        finally:
            updater._cleanup()
    
    else:
        # Show help
        parser.print_help()
        print("\nExamples:")
        print("  python tmux_window_updater.py --test")
        print("  python tmux_window_updater.py --daemon")
        print("  python tmux_window_updater.py --daemon --interval 15")

if __name__ == "__main__":
    main()