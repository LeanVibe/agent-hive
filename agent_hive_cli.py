#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Unified CLI
Streamlined agent management with auto-discovery and cross-platform support
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

# Database models
Base = declarative_base()

class AgentRecord(Base):
    """Agent registry record"""
    __tablename__ = 'agent_registry'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    capabilities = Column(Text, nullable=True)  # JSON string
    specializations = Column(Text, nullable=True)  # JSON string
    last_seen = Column(DateTime, server_default=func.now())
    status = Column(String, default='discovered')

class AgentEnvironment:
    """Abstract base for agent environments"""
    def create_session(self, agent_id: str) -> bool:
        raise NotImplementedError
    
    def send_message(self, agent_id: str, message: str) -> bool:
        raise NotImplementedError
    
    def get_status(self, agent_id: str) -> Dict:
        raise NotImplementedError
    
    def terminate_session(self, agent_id: str) -> bool:
        raise NotImplementedError

class TmuxEnvironment(AgentEnvironment):
    """Tmux-based agent environment"""
    def __init__(self, session_name: str = "agent-hive"):
        self.session_name = session_name
        self._ensure_session()
    
    def _ensure_session(self):
        """Ensure tmux session exists"""
        try:
            subprocess.run(["tmux", "has-session", "-t", self.session_name], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["tmux", "new-session", "-d", "-s", self.session_name])
    
    def create_session(self, agent_id: str) -> bool:
        """Create tmux window for agent"""
        try:
            # Find agent worktree
            worktree_path = self._find_agent_worktree(agent_id)
            if not worktree_path:
                return False
            
            window_name = f"agent-{agent_id}"
            subprocess.run([
                "tmux", "new-window", "-t", self.session_name,
                "-n", window_name, "-c", str(worktree_path)
            ], check=True)
            
            # Start Claude Code
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:{window_name}",
                "claude --dangerously-skip-permissions", "Enter"
            ])
            
            return True
        except Exception as e:
            print(f"Failed to create tmux session: {e}")
            return False
    
    def send_message(self, agent_id: str, message: str) -> bool:
        """Send message to agent via tmux"""
        try:
            window_name = f"agent-{agent_id}"
            subprocess.run(["tmux", "set-buffer", message])
            subprocess.run(["tmux", "send-keys", "-t", f"{self.session_name}:{window_name}", "C-c"])
            time.sleep(0.3)
            subprocess.run(["tmux", "paste-buffer", "-t", f"{self.session_name}:{window_name}"])
            time.sleep(0.2)
            subprocess.run(["tmux", "send-keys", "-t", f"{self.session_name}:{window_name}", "Enter"])
            return True
        except Exception as e:
            print(f"Failed to send message: {e}")
            return False
    
    def get_status(self, agent_id: str) -> Dict:
        """Get agent status from tmux"""
        try:
            window_name = f"agent-{agent_id}"
            result = subprocess.run([
                "tmux", "list-windows", "-t", self.session_name, "-F", "#{window_name}:#{window_active}"
            ], capture_output=True, text=True)
            
            for line in result.stdout.strip().split('\n'):
                if line.startswith(window_name):
                    active = line.split(':')[1] == "1"
                    return {"active": active, "window": window_name}
            
            return {"active": False, "window": None}
        except Exception:
            return {"active": False, "window": None}
    
    def terminate_session(self, agent_id: str) -> bool:
        """Terminate agent session"""
        try:
            window_name = f"agent-{agent_id}"
            subprocess.run(["tmux", "kill-window", "-t", f"{self.session_name}:{window_name}"])
            return True
        except Exception:
            return False
    
    def _find_agent_worktree(self, agent_id: str) -> Optional[Path]:
        """Find worktree for agent"""
        possible_paths = [
            Path("worktrees") / agent_id,
            Path("new-worktrees") / agent_id,
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "CLAUDE.md").exists():
                return path
        
        return None

class ProcessEnvironment(AgentEnvironment):
    """Process-based agent environment (for non-tmux systems)"""
    def __init__(self):
        self.processes = {}
    
    def create_session(self, agent_id: str) -> bool:
        """Create process for agent"""
        # Implementation for process-based agents
        print(f"Process environment not fully implemented for {agent_id}")
        return False
    
    def send_message(self, agent_id: str, message: str) -> bool:
        """Send message via file system"""
        try:
            worktree_path = self._find_agent_worktree(agent_id)
            if worktree_path:
                msg_file = worktree_path / "MESSAGE.txt"
                with open(msg_file, 'w') as f:
                    f.write(f"{datetime.now().isoformat()}: {message}\n")
                return True
        except Exception:
            pass
        return False
    
    def get_status(self, agent_id: str) -> Dict:
        """Get process status"""
        return {"active": agent_id in self.processes}
    
    def terminate_session(self, agent_id: str) -> bool:
        """Terminate process"""
        if agent_id in self.processes:
            self.processes[agent_id].terminate()
            del self.processes[agent_id]
            return True
        return False
    
    def _find_agent_worktree(self, agent_id: str) -> Optional[Path]:
        """Find worktree for agent"""
        possible_paths = [
            Path("worktrees") / agent_id,
            Path("new-worktrees") / agent_id,
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "CLAUDE.md").exists():
                return path
        
        return None

class AgentDiscovery:
    """Agent discovery and capability extraction"""
    
    def discover_agents(self) -> List[Dict]:
        """Discover agents from file system"""
        agents = []
        
        # Check standard locations
        for base_dir in [Path("worktrees"), Path("new-worktrees")]:
            if base_dir.exists():
                for agent_dir in base_dir.iterdir():
                    if agent_dir.is_dir():
                        claude_file = agent_dir / "CLAUDE.md"
                        if claude_file.exists():
                            agent_info = self._extract_agent_info(agent_dir, claude_file)
                            if agent_info:
                                agents.append(agent_info)
        
        return agents
    
    def _extract_agent_info(self, agent_dir: Path, claude_file: Path) -> Optional[Dict]:
        """Extract agent information from CLAUDE.md"""
        try:
            content = claude_file.read_text()
            
            # Skip generic orchestrator files
            if "LeanVibe Orchestrator" in content and "Role: Orchestrator" in content:
                return None
            
            # Extract basic info
            agent_info = {
                "id": agent_dir.name,
                "name": agent_dir.name,
                "path": str(agent_dir),
                "claude_file": str(claude_file),
                "capabilities": self._extract_capabilities(content),
                "specializations": self._extract_specializations(content),
                "last_modified": datetime.fromtimestamp(claude_file.stat().st_mtime).isoformat()
            }
            
            return agent_info
        except Exception as e:
            print(f"Error extracting agent info from {agent_dir}: {e}")
            return None
    
    def _extract_capabilities(self, content: str) -> List[str]:
        """Extract capabilities from CLAUDE.md content"""
        capabilities = []
        
        # Look for capability keywords
        capability_keywords = [
            "documentation", "integration", "testing", "security", "performance",
            "monitoring", "coordination", "quality", "api", "authentication",
            "frontend", "backend", "database", "machine learning", "orchestration"
        ]
        
        content_lower = content.lower()
        for keyword in capability_keywords:
            if keyword in content_lower:
                capabilities.append(keyword)
        
        return capabilities
    
    def _extract_specializations(self, content: str) -> List[str]:
        """Extract specializations from CLAUDE.md content"""
        specializations = []
        
        # Look for specialization patterns
        if "specialist" in content.lower():
            if "integration" in content.lower():
                specializations.append("integration-specialist")
            if "frontend" in content.lower():
                specializations.append("frontend-specialist")
            if "security" in content.lower():
                specializations.append("security-specialist")
            if "performance" in content.lower():
                specializations.append("performance-specialist")
        
        return specializations

class AgentRegistry:
    """Unified agent registry and management"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or self._get_database_url()
        self.discovery = AgentDiscovery()
        self.environment = self._select_environment()
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._init_database()
    
    def _get_database_url(self) -> str:
        """Get PostgreSQL database URL from environment variables"""
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "agent_hive")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    def _select_environment(self) -> AgentEnvironment:
        """Select appropriate environment based on system"""
        try:
            subprocess.run(["tmux", "-V"], capture_output=True, check=True)
            return TmuxEnvironment()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ProcessEnvironment()
    
    def _init_database(self):
        """Initialize registry database"""
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            print(f"Warning: Could not initialize database: {e}")
            print("Using fallback SQLite database")
            # Fallback to SQLite if PostgreSQL is not available
            self.db_url = "sqlite:///agent_registry.db"
            self.engine = create_engine(self.db_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
    
    def discover_and_register(self) -> int:
        """Discover and register all agents"""
        agents = self.discovery.discover_agents()
        
        session = self.SessionLocal()
        count = 0
        
        try:
            for agent in agents:
                # Check if agent already exists
                existing_agent = session.query(AgentRecord).filter_by(id=agent["id"]).first()
                
                if existing_agent:
                    # Update existing agent
                    existing_agent.name = agent["name"]
                    existing_agent.path = agent["path"]
                    existing_agent.capabilities = json.dumps(agent["capabilities"])
                    existing_agent.specializations = json.dumps(agent["specializations"])
                    existing_agent.last_seen = datetime.fromisoformat(agent["last_modified"])
                else:
                    # Create new agent record
                    new_agent = AgentRecord(
                        id=agent["id"],
                        name=agent["name"],
                        path=agent["path"],
                        capabilities=json.dumps(agent["capabilities"]),
                        specializations=json.dumps(agent["specializations"]),
                        last_seen=datetime.fromisoformat(agent["last_modified"])
                    )
                    session.add(new_agent)
                
                count += 1
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"Error registering agents: {e}")
        finally:
            session.close()
        
        return count
    
    def list_agents(self) -> List[Dict]:
        """List all registered agents"""
        session = self.SessionLocal()
        agents = []
        
        try:
            agent_records = session.query(AgentRecord).order_by(AgentRecord.name).all()
            
            for record in agent_records:
                agents.append({
                    "id": record.id,
                    "name": record.name,
                    "path": record.path,
                    "capabilities": json.loads(record.capabilities) if record.capabilities else [],
                    "specializations": json.loads(record.specializations) if record.specializations else [],
                    "last_seen": record.last_seen.isoformat() if record.last_seen else "",
                    "status": record.status
                })
        
        except Exception as e:
            print(f"Error listing agents: {e}")
        finally:
            session.close()
        
        return agents
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get specific agent details"""
        session = self.SessionLocal()
        
        try:
            record = session.query(AgentRecord).filter_by(id=agent_id).first()
            
            if record:
                return {
                    "id": record.id,
                    "name": record.name,
                    "path": record.path,
                    "capabilities": json.loads(record.capabilities) if record.capabilities else [],
                    "specializations": json.loads(record.specializations) if record.specializations else [],
                    "last_seen": record.last_seen.isoformat() if record.last_seen else "",
                    "status": record.status
                }
        
        except Exception as e:
            print(f"Error getting agent {agent_id}: {e}")
        finally:
            session.close()
        
        return None
    
    def spawn_agent(self, agent_id: str, initial_message: str = "") -> bool:
        """Spawn an agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            print(f"Agent {agent_id} not found")
            return False
        
        success = self.environment.create_session(agent_id)
        if success:
            # Update status
            self._update_agent_status(agent_id, "active")
            
            # Send initial message if provided
            if initial_message:
                time.sleep(3)  # Wait for initialization
                self.environment.send_message(agent_id, initial_message)
            
            print(f"✅ Agent {agent_id} spawned successfully")
            return True
        else:
            print(f"❌ Failed to spawn agent {agent_id}")
            return False
    
    def send_message(self, agent_id: str, message: str) -> bool:
        """Send message to agent"""
        return self.environment.send_message(agent_id, message)
    
    def get_status(self, agent_id: str) -> Dict:
        """Get agent status"""
        env_status = self.environment.get_status(agent_id)
        agent = self.get_agent(agent_id)
        
        if agent:
            return {
                "agent_id": agent_id,
                "name": agent["name"],
                "path": agent["path"],
                "capabilities": agent["capabilities"],
                "specializations": agent["specializations"],
                "registry_status": agent["status"],
                "environment_status": env_status
            }
        else:
            return {"agent_id": agent_id, "error": "Agent not found"}
    
    def terminate_agent(self, agent_id: str) -> bool:
        """Terminate agent"""
        success = self.environment.terminate_session(agent_id)
        if success:
            self._update_agent_status(agent_id, "terminated")
        return success
    
    def recommend_agent(self, task_description: str) -> List[Dict]:
        """Recommend agents for a task"""
        agents = self.list_agents()
        recommendations = []
        
        task_lower = task_description.lower()
        
        for agent in agents:
            score = 0
            matched_capabilities = []
            
            # Score based on capabilities
            for capability in agent["capabilities"]:
                if capability.lower() in task_lower:
                    score += 2
                    matched_capabilities.append(capability)
            
            # Score based on specializations
            for specialization in agent["specializations"]:
                if any(word in task_lower for word in specialization.split('-')):
                    score += 3
                    matched_capabilities.append(specialization)
            
            if score > 0:
                recommendations.append({
                    "agent": agent,
                    "score": score,
                    "matched_capabilities": matched_capabilities
                })
        
        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:5]  # Top 5
    
    def _update_agent_status(self, agent_id: str, status: str):
        """Update agent status in database"""
        session = self.SessionLocal()
        
        try:
            record = session.query(AgentRecord).filter_by(id=agent_id).first()
            if record:
                record.status = status
                record.last_seen = datetime.now()
                session.commit()
        
        except Exception as e:
            session.rollback()
            print(f"Error updating agent status: {e}")
        finally:
            session.close()

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="LeanVibe Agent Hive - Unified Agent Management")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Discover command
    subparsers.add_parser("discover", help="Discover and register agents")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List agents")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get agent status")
    status_parser.add_argument("agent_id", nargs="?", help="Agent ID (optional)")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Spawn command
    spawn_parser = subparsers.add_parser("spawn", help="Spawn an agent")
    spawn_parser.add_argument("agent_id", help="Agent ID to spawn")
    spawn_parser.add_argument("--message", help="Initial message to send")
    
    # Message command
    message_parser = subparsers.add_parser("message", help="Send message to agent")
    message_parser.add_argument("agent_id", help="Agent ID")
    message_parser.add_argument("message", help="Message to send")
    
    # Recommend command
    recommend_parser = subparsers.add_parser("recommend", help="Recommend agents for task")
    recommend_parser.add_argument("task", help="Task description")
    
    # Terminate command
    terminate_parser = subparsers.add_parser("terminate", help="Terminate agent")
    terminate_parser.add_argument("agent_id", help="Agent ID to terminate")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    registry = AgentRegistry()
    
    if args.command == "discover":
        count = registry.discover_and_register()
        print(f"✅ Discovered and registered {count} agents")
    
    elif args.command == "list":
        agents = registry.list_agents()
        if args.json:
            print(json.dumps(agents, indent=2))
        else:
            print(f"📋 Found {len(agents)} agents:")
            for agent in agents:
                caps = ", ".join(agent["capabilities"][:3])
                if len(agent["capabilities"]) > 3:
                    caps += f" (+{len(agent['capabilities'])-3} more)"
                print(f"  • {agent['name']} - {caps}")
    
    elif args.command == "status":
        if args.agent_id:
            status = registry.get_status(args.agent_id)
            if args.json:
                print(json.dumps(status, indent=2))
            else:
                if "error" in status:
                    print(f"❌ {status['error']}")
                else:
                    env_status = status["environment_status"]
                    active = env_status.get("active", False)
                    emoji = "✅" if active else "❌"
                    print(f"{emoji} {status['name']} - {'Active' if active else 'Inactive'}")
                    print(f"   Path: {status['path']}")
                    print(f"   Capabilities: {', '.join(status['capabilities'])}")
        else:
            agents = registry.list_agents()
            active_count = 0
            for agent in agents:
                status = registry.get_status(agent["id"])
                if status.get("environment_status", {}).get("active", False):
                    active_count += 1
            print(f"📊 Agent Status: {active_count}/{len(agents)} active")
    
    elif args.command == "spawn":
        success = registry.spawn_agent(args.agent_id, args.message or "")
        sys.exit(0 if success else 1)
    
    elif args.command == "message":
        success = registry.send_message(args.agent_id, args.message)
        if success:
            print(f"✅ Message sent to {args.agent_id}")
        else:
            print(f"❌ Failed to send message to {args.agent_id}")
        sys.exit(0 if success else 1)
    
    elif args.command == "recommend":
        recommendations = registry.recommend_agent(args.task)
        if recommendations:
            print(f"💡 Recommended agents for '{args.task}':")
            for i, rec in enumerate(recommendations, 1):
                agent = rec["agent"]
                print(f"  {i}. {agent['name']} (score: {rec['score']})")
                print(f"     Matched: {', '.join(rec['matched_capabilities'])}")
        else:
            print("No suitable agents found")
    
    elif args.command == "terminate":
        success = registry.terminate_agent(args.agent_id)
        if success:
            print(f"✅ Agent {args.agent_id} terminated")
        else:
            print(f"❌ Failed to terminate agent {args.agent_id}")
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()