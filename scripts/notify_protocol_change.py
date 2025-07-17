#!/usr/bin/env python3
"""
Protocol Change Notification Script
Broadcasts new communication protocols to all agents
"""

import json
import os
from datetime import datetime
from pathlib import Path

def send_protocol_notification():
    """Send protocol change notification to all agents"""
    
    # Create message bus directories if they don't exist
    message_bus_path = Path("/Users/bogdan/work/leanvibe-dev/agent-hive/message_bus")
    inboxes_path = message_bus_path / "inboxes"
    inboxes_path.mkdir(parents=True, exist_ok=True)
    
    agents = [
        "infrastructure-primary",
        "integration-coordinator", 
        "monitoring-Jul-17-1349",
        "performance-Jul-17-1349"
    ]
    
    protocol_message = {
        "timestamp": datetime.now().isoformat(),
        "from": "COORDINATOR",
        "type": "protocol_update",
        "priority": "high",
        "content": """🔄 NEW COMMUNICATION PROTOCOL ACTIVE:

STRUCTURE:
- Central Hub: agent-pm-coordinator
- Hub-and-Spoke Model: All communication flows through PM
- No direct agent-to-agent communication

YOUR ACTIONS REQUIRED:
1. Acknowledge this protocol change
2. Send status update to PM coordinator immediately  
3. Use message bus for all future PM communication
4. Report progress every 15 minutes to PM

CRITICAL: Old delegation chains discontinued. PM coordinator is your new authority.

Send acknowledgment and current status to PM coordinator now.""",
        "id": f"protocol_update_{datetime.now().strftime('%H%M%S')}"
    }
    
    # Send to each agent's inbox
    for agent in agents:
        inbox_file = inboxes_path / f"{agent}.json"
        
        messages = []
        if inbox_file.exists():
            with open(inbox_file, 'r') as f:
                try:
                    messages = json.load(f)
                except json.JSONDecodeError:
                    messages = []
        
        messages.append(protocol_message)
        
        with open(inbox_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        print(f"📬 Protocol notification sent to {agent}")
    
    # Also notify PM coordinator
    pm_message = {
        "timestamp": datetime.now().isoformat(),
        "from": "COORDINATOR",
        "type": "coordination_handoff",
        "priority": "high", 
        "content": """🎯 COORDINATION HANDOFF: All agents notified of new protocol.

AGENTS UNDER YOUR COMMAND:
- infrastructure-primary (import fixes)
- integration-coordinator (worktree integration)
- monitoring-Jul-17-1349 (system monitoring)
- performance-Jul-17-1349 (performance tracking)

EXPECT INCOMING:
- Acknowledgment messages from all 4 agents
- Status updates on current work
- Regular progress reports every 15 minutes

YOUR AUTHORITY: Full coordination control. Use message bus system for all communication.""",
        "id": f"handoff_{datetime.now().strftime('%H%M%S')}"
    }
    
    pm_inbox = inboxes_path / "pm-coordinator.json"
    pm_messages = []
    if pm_inbox.exists():
        with open(pm_inbox, 'r') as f:
            try:
                pm_messages = json.load(f)
            except json.JSONDecodeError:
                pm_messages = []
    
    pm_messages.append(pm_message)
    
    with open(pm_inbox, 'w') as f:
        json.dump(pm_messages, f, indent=2)
    
    print(f"📬 Coordination handoff sent to PM coordinator")
    print(f"✅ Protocol change notification complete - {len(agents)} agents + PM notified")

if __name__ == "__main__":
    send_protocol_notification()