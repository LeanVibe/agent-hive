#!/usr/bin/env python3
"""
Message Bus Protocol - Hub-and-Spoke Communication System
Based on Gemini CLI recommendations for multi-agent coordination
"""

import json
import os
from datetime import datetime
from pathlib import Path

class MessageBus:
    def __init__(self, base_path="/Users/bogdan/work/leanvibe-dev/agent-hive/message_bus"):
        self.base_path = Path(base_path)
        self.inboxes = self.base_path / "inboxes"
        self.outbox = self.base_path / "outbox"
        
        # Ensure directories exist
        self.inboxes.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)
    
    def send_message(self, from_agent: str, to_agent: str, message_type: str, content: str, priority: str = "normal"):
        """Send message from one agent to another"""
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "from": from_agent,
            "to": to_agent,
            "type": message_type,
            "content": content,
            "priority": priority,
            "id": f"{from_agent}_{datetime.now().strftime('%H%M%S')}"
        }
        
        # Save to recipient's inbox
        inbox_file = self.inboxes / f"{to_agent}.json"
        
        messages = []
        if inbox_file.exists():
            with open(inbox_file, 'r') as f:
                messages = json.load(f)
        
        messages.append(message)
        
        with open(inbox_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        print(f"📬 Message sent: {from_agent} → {to_agent} ({message_type})")
        return message["id"]
    
    def broadcast_from_pm(self, message_type: str, content: str, agents: list, priority: str = "normal"):
        """Broadcast message from PM to multiple agents"""
        
        message_ids = []
        for agent in agents:
            msg_id = self.send_message("pm-coordinator", agent, message_type, content, priority)
            message_ids.append(msg_id)
        
        print(f"📡 Broadcast sent to {len(agents)} agents")
        return message_ids

# Convenience functions for agents
def send_to_pm(agent_id: str, message_type: str, content: str, priority: str = "normal"):
    """Send message to PM agent"""
    bus = MessageBus()
    return bus.send_message(agent_id, "pm-coordinator", message_type, content, priority)

def send_status_update(agent_id: str, status: str, task: str, result: str = ""):
    """Standardized status update to PM"""
    content = f"STATUS: {status} | TASK: {task} | RESULT: {result}"
    return send_to_pm(agent_id, "status_update", content)