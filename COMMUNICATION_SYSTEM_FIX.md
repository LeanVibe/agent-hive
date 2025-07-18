# 🔧 COMMUNICATION SYSTEM FIX - Implementation Plan

**Generated**: July 18, 2025 12:55 PM  
**Status**: 🎯 **SOLUTION IDENTIFIED** - Root cause analysis complete, ready for implementation

## 📊 **GEMINI CLI ANALYSIS SUMMARY**

### **Root Cause Confirmed**
- **Window Name Mismatch**: Scripts expect `agent-{name}` but windows are named `SEC-Input-⏳`
- **Auto-Submit Failure**: Messages sent to non-existent windows
- **Solution Available**: `fixed_agent_communication.py` already handles both naming conventions

### **Strategic Recommendation**
> **"Complete rebuild unnecessary. Fix immediate problem with existing backward-compatible script, then standardize naming."**

## 🎯 **IMPLEMENTATION APPROACH**

### **Phase 1: Immediate Fix (Next 30 minutes)**
1. **Use Fixed Script**: Switch to `fixed_agent_communication.py` for all messages
2. **Test Communication**: Verify messages are delivered and processed
3. **Validate Auto-Submit**: Ensure Enter key is properly sent

### **Phase 2: Window Naming System (Next 2 hours)**  
1. **Descriptive Format**: Implement `SEC-SecurityAudit-🔄` style naming
2. **Real-time Updates**: Create new window updater with status detection
3. **Background Process**: Auto-updating every 30 seconds

### **Phase 3: Unified System (Next 4 hours)**
1. **Integrate Communication**: Combine message sending and window updating
2. **Standardize Process**: Create consistent, predictable workflow
3. **Add Monitoring**: Real-time agent activity tracking

## 🚀 **IMMEDIATE IMPLEMENTATION**

### **Step 1: Fix Message Sending Now**
```bash
# Test using the fixed script
python scripts/fixed_agent_communication.py --agent security --message "TEST: Can you confirm you received this message?"

# Verify it works with all agents
python scripts/fixed_agent_communication.py --agent performance --message "TEST: Can you confirm you received this message?"
python scripts/fixed_agent_communication.py --agent frontend --message "TEST: Can you confirm you received this message?"
python scripts/fixed_agent_communication.py --agent pm-agent-new --message "TEST: Can you confirm you received this message?"
```

### **Step 2: Create New Window Updater**
```python
# New tmux_window_updater.py with:
# - Maps current window names to agent activities
# - Detects agent status from pane content
# - Updates with descriptive names like SEC-SecurityAudit-🔄
# - Runs as background process for continuous updates
```

### **Step 3: Test Integration**
```bash
# Send message and verify window updates
python scripts/fixed_agent_communication.py --agent security --message "Start security audit task"
# Check: Does window name change to SEC-SecurityAudit-🔄?
```

## 📋 **DETAILED IMPLEMENTATION PLAN**

### **1. Test Current Fixed Script**
```bash
# Immediate test - does this work?
python scripts/fixed_agent_communication.py --agent security --message "COMMUNICATION TEST: Please respond with 'RECEIVED' if you got this message"
```

### **2. Create Window Updater Script**
```python
#!/usr/bin/env python3
"""
Enhanced Tmux Window Updater with Real-time Agent Status
Updates window names with format: PREFIX-FOCUS-STATUS_EMOTICON
"""

import subprocess
import time
import re
from datetime import datetime

class AgentWindowUpdater:
    def __init__(self):
        self.session_name = "agent-hive"
        self.window_mapping = {
            'SEC-Input-⏳': 'security',
            'PERF-Input-⏳': 'performance', 
            'FE-Input-⏳': 'frontend',
            'PM-Input-⏳': 'pm-agent-new'
        }
        self.status_emoticons = {
            'processing': '🔄',
            'waiting': '⏳',
            'completed': '✅',
            'error': '❌',
            'idle': '⏸️'
        }
        
    def detect_agent_activity(self, window_name):
        """Detect what agent is currently doing"""
        try:
            # Get pane content
            result = subprocess.run([
                'tmux', 'capture-pane', '-t', 
                f"{self.session_name}:{window_name}", '-p'
            ], capture_output=True, text=True)
            
            content = result.stdout.strip()
            
            # Analyze content for activity
            if 'Processing' in content or 'Analyzing' in content:
                return 'processing', 'Working'
            elif 'Complete' in content or 'Done' in content:
                return 'completed', 'Complete'
            elif 'Error' in content or 'Failed' in content:
                return 'error', 'Error'
            elif '-- INSERT --' in content:
                return 'waiting', 'Input'
            else:
                return 'idle', 'Ready'
                
        except Exception as e:
            return 'error', 'Unknown'
    
    def update_window_name(self, old_name, new_name):
        """Update tmux window name"""
        try:
            subprocess.run([
                'tmux', 'rename-window', '-t',
                f"{self.session_name}:{old_name}", new_name
            ], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def update_all_windows(self):
        """Update all agent windows with current status"""
        for window_name, agent_name in self.window_mapping.items():
            status, focus = self.detect_agent_activity(window_name)
            emoticon = self.status_emoticons.get(status, '❓')
            
            # Create new descriptive name
            prefix = window_name.split('-')[0]  # SEC, PERF, FE, PM
            new_name = f"{prefix}-{focus}-{emoticon}"
            
            # Update if name changed
            if window_name != new_name:
                if self.update_window_name(window_name, new_name):
                    print(f"Updated {window_name} -> {new_name}")
                    # Update our mapping
                    self.window_mapping[new_name] = agent_name
                    del self.window_mapping[window_name]
    
    def run_continuous(self, interval=30):
        """Run continuous updates"""
        print(f"Starting continuous window updates every {interval} seconds...")
        while True:
            try:
                self.update_all_windows()
                time.sleep(interval)
            except KeyboardInterrupt:
                print("Stopping window updater...")
                break
            except Exception as e:
                print(f"Error in update cycle: {e}")
                time.sleep(interval)

if __name__ == "__main__":
    updater = AgentWindowUpdater()
    updater.run_continuous()
```

### **3. Create Unified Communication Function**
```python
def send_message_and_update_status(agent_name, message):
    """Send message and update window status"""
    # Send message using fixed script
    result = subprocess.run([
        'python', 'scripts/fixed_agent_communication.py',
        '--agent', agent_name,
        '--message', message
    ])
    
    # Update window status
    updater = AgentWindowUpdater()
    updater.update_all_windows()
    
    return result.returncode == 0
```

## 🔍 **TESTING STRATEGY**

### **Test 1: Basic Communication**
```bash
# Test message delivery
python scripts/fixed_agent_communication.py --agent security --message "TEST: Respond with RECEIVED"
# Expected: Agent receives and processes message
```

### **Test 2: Window Updates**
```bash
# Test window name changes
python scripts/tmux_window_updater.py --test
# Expected: Window names change to descriptive format
```

### **Test 3: Integration**
```bash
# Test combined system
# Send message -> Window updates -> Agent responds
```

## 📊 **SUCCESS CRITERIA**

### **Immediate Success (30 minutes)**
- [ ] Messages sent to agents are automatically processed
- [ ] No manual Enter key required
- [ ] All agents receive and respond to test messages
- [ ] Communication works consistently across all agents

### **System Success (4 hours)**
- [ ] Window names update in real-time with agent status
- [ ] Descriptive format shows agent focus and status
- [ ] Background updating runs continuously
- [ ] Unified communication system works reliably

---

**Status**: 🎯 **READY FOR IMPLEMENTATION** - Clear plan with existing tools  
**Priority**: IMMEDIATE - Essential for agent coordination  
**Next Action**: Test fixed communication script, then implement window updater  
**Timeline**: 4 hours for complete system restoration