#!/usr/bin/env python3
"""
Context Monitor Hook - Automatic context window management
Triggers at 70% usage to prevent knowledge loss through context overflow
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContextMonitorHook:
    """Automatic context monitoring and memory consolidation"""
    
    def __init__(self):
        self.project_root = project_root
        self.enabled = True
        
    async def check_and_handle_context(self):
        """Check context usage and handle if needed"""
        if not self.enabled:
            return
        
        try:
            # Run context memory manager check
            cmd = ["python", "scripts/context_memory_manager.py", "--check"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                output = result.stdout
                
                # Parse output for threshold status
                if "Action Required" in output:
                    logger.warning("🚨 Context threshold reached - triggering memory consolidation")
                    
                    # Trigger memory consolidation
                    consolidate_cmd = ["python", "scripts/context_memory_manager.py", "--consolidate", "critical"]
                    consolidate_result = subprocess.run(consolidate_cmd, cwd=self.project_root, timeout=120)
                    
                    if consolidate_result.returncode == 0:
                        logger.info("✅ Memory consolidation completed successfully")
                        
                        # Save hook trigger log
                        self._log_hook_trigger()
                        
                        return True
                    else:
                        logger.error("❌ Memory consolidation failed")
                        return False
                
            return False
            
        except Exception as e:
            logger.error(f"Context monitor hook error: {e}")
            return False
    
    def _log_hook_trigger(self):
        """Log that the hook was triggered"""
        hook_log = self.project_root / ".claude/logs/context_hook.log"
        hook_log.parent.mkdir(parents=True, exist_ok=True)
        
        with open(hook_log, "a") as f:
            f.write(f"{asyncio.get_event_loop().time()}: Context monitor hook triggered memory consolidation\n")


# Hook entry point - called by Claude Code when context usage is high
async def on_context_threshold():
    """Entry point for context threshold hook"""
    hook = ContextMonitorHook()
    return await hook.check_and_handle_context()


# Manual testing entry point
if __name__ == "__main__":
    async def test_hook():
        hook = ContextMonitorHook()
        result = await hook.check_and_handle_context()
        print(f"Hook test result: {result}")
    
    asyncio.run(test_hook())