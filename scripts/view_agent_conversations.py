#!/usr/bin/env python3
"""
Agent Conversation History Viewer

Views message history and conversations between agents.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class AgentConversationViewer:
    """View conversations between agents"""

    def __init__(self, db_path: str = "agent_conversations.db"):
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize conversation database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'normal',
                thread_id TEXT,
                read_status INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def log_message(self, from_agent: str, to_agent: str, message: str,
                   message_type: str = "normal", thread_id: Optional[str] = None):
        """Log a message between agents"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO agent_messages
            (timestamp, from_agent, to_agent, message, message_type, thread_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            from_agent,
            to_agent,
            message,
            message_type,
            thread_id
        ))
        conn.commit()
        conn.close()

    def get_conversation(self, agent1: str, agent2: str, hours: int = 24) -> List[Dict]:
        """Get conversation between two agents"""
        since = datetime.now() - timedelta(hours=hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT timestamp, from_agent, to_agent, message, message_type, thread_id
            FROM agent_messages
            WHERE ((from_agent = ? AND to_agent = ?) OR (from_agent = ? AND to_agent = ?))
            AND timestamp > ?
            ORDER BY timestamp ASC
        """, (agent1, agent2, agent2, agent1, since.isoformat()))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'timestamp': row[0],
                'from_agent': row[1],
                'to_agent': row[2],
                'message': row[3],
                'message_type': row[4],
                'thread_id': row[5]
            })

        conn.close()
        return messages

    def get_agent_activity(self, agent_name: str, hours: int = 24) -> List[Dict]:
        """Get all activity for a specific agent"""
        since = datetime.now() - timedelta(hours=hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT timestamp, from_agent, to_agent, message, message_type, thread_id
            FROM agent_messages
            WHERE (from_agent = ? OR to_agent = ?)
            AND timestamp > ?
            ORDER BY timestamp DESC
        """, (agent_name, agent_name, since.isoformat()))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'timestamp': row[0],
                'from_agent': row[1],
                'to_agent': row[2],
                'message': row[3],
                'message_type': row[4],
                'thread_id': row[5]
            })

        conn.close()
        return messages

    def get_recent_messages(self, hours: int = 24) -> List[Dict]:
        """Get all recent messages across agents"""
        since = datetime.now() - timedelta(hours=hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT timestamp, from_agent, to_agent, message, message_type, thread_id
            FROM agent_messages
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (since.isoformat(),))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'timestamp': row[0],
                'from_agent': row[1],
                'to_agent': row[2],
                'message': row[3],
                'message_type': row[4],
                'thread_id': row[5]
            })

        conn.close()
        return messages

    def get_help_requests(self, hours: int = 24) -> List[Dict]:
        """Get all help requests from agents"""
        since = datetime.now() - timedelta(hours=hours)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT timestamp, from_agent, to_agent, message, message_type, thread_id
            FROM agent_messages
            WHERE message_type = 'help_request'
            AND timestamp > ?
            ORDER BY timestamp DESC
        """, (since.isoformat(),))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'timestamp': row[0],
                'from_agent': row[1],
                'to_agent': row[2],
                'message': row[3],
                'message_type': row[4],
                'thread_id': row[5]
            })

        conn.close()
        return messages

    def print_conversation(self, agent1: str, agent2: str, hours: int = 24):
        """Print formatted conversation between two agents"""
        messages = self.get_conversation(agent1, agent2, hours)

        print(f"💬 CONVERSATION: {agent1} ↔ {agent2}")
        print("=" * 60)
        print(f"📅 Last {hours} hours | {len(messages)} messages")
        print()

        if not messages:
            print("No messages found in this timeframe.")
            return

        for msg in messages:
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
            from_agent = msg['from_agent']
            to_agent = msg['to_agent']
            message = msg['message']
            msg_type = msg['message_type']

            type_emoji = {
                'help_request': '🆘',
                'escalation': '🚨',
                'status_update': '📊',
                'normal': '💬'
            }.get(msg_type, '💬')

            print(f"{type_emoji} [{timestamp}] {from_agent} → {to_agent}")
            print(f"   {message[:100]}{'...' if len(message) > 100 else ''}")
            print()

    def print_agent_activity(self, agent_name: str, hours: int = 24):
        """Print formatted activity for a specific agent"""
        messages = self.get_agent_activity(agent_name, hours)

        print(f"🤖 ACTIVITY: {agent_name}")
        print("=" * 40)
        print(f"📅 Last {hours} hours | {len(messages)} messages")
        print()

        if not messages:
            print("No activity found in this timeframe.")
            return

        for msg in messages:
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
            from_agent = msg['from_agent']
            to_agent = msg['to_agent']
            message = msg['message']
            msg_type = msg['message_type']

            direction = "📤" if from_agent == agent_name else "📥"
            other_agent = to_agent if from_agent == agent_name else from_agent

            type_emoji = {
                'help_request': '🆘',
                'escalation': '🚨',
                'status_update': '📊',
                'normal': '💬'
            }.get(msg_type, '💬')

            print(f"{direction} {type_emoji} [{timestamp}] ↔ {other_agent}")
            print(f"   {message[:80]}{'...' if len(message) > 80 else ''}")
            print()

    def print_help_requests(self, hours: int = 24):
        """Print all help requests"""
        messages = self.get_help_requests(hours)

        print("🆘 HELP REQUESTS")
        print("=" * 30)
        print(f"📅 Last {hours} hours | {len(messages)} requests")
        print()

        if not messages:
            print("No help requests found.")
            return

        for msg in messages:
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
            from_agent = msg['from_agent']
            to_agent = msg['to_agent']
            message = msg['message']

            print(f"🆘 [{timestamp}] {from_agent} → {to_agent}")
            print(f"   {message}")
            print()

def main():
    """Main CLI interface"""
    import sys

    viewer = AgentConversationViewer()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python view_agent_conversations.py --agents agent1,agent2 [--hours 24]")
        print("  python view_agent_conversations.py --activity agent-name [--hours 24]")
        print("  python view_agent_conversations.py --help-requests [--hours 24]")
        print("  python view_agent_conversations.py --recent [--hours 24]")
        return

    command = sys.argv[1]
    hours = 24

    # Parse hours parameter
    if "--hours" in sys.argv:
        hours_index = sys.argv.index("--hours")
        if hours_index + 1 < len(sys.argv):
            hours = int(sys.argv[hours_index + 1])

    if command == "--agents":
        if len(sys.argv) < 3:
            print("Error: --agents requires agent1,agent2")
            return

        agents = sys.argv[2].split(',')
        if len(agents) != 2:
            print("Error: --agents requires exactly 2 agents separated by comma")
            return

        viewer.print_conversation(agents[0], agents[1], hours)

    elif command == "--activity":
        if len(sys.argv) < 3:
            print("Error: --activity requires agent name")
            return

        agent_name = sys.argv[2]
        viewer.print_agent_activity(agent_name, hours)

    elif command == "--help-requests":
        viewer.print_help_requests(hours)

    elif command == "--recent":
        messages = viewer.get_recent_messages(hours)
        print(f"📨 RECENT MESSAGES ({len(messages)} in last {hours}h)")
        print("=" * 50)

        for msg in messages[:20]:  # Show last 20 messages
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
            print(f"[{timestamp}] {msg['from_agent']} → {msg['to_agent']}")
            print(f"   {msg['message'][:80]}{'...' if len(msg['message']) > 80 else ''}")
            print()

    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
