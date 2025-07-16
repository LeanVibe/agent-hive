"""
Agent Registry Service for dynamic agent discovery and management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import yaml

from .models import Agent, AgentStatus


logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Service for managing agent registration, discovery, and capabilities.
    Replaces hardcoded agent lists with dynamic discovery.
    """
    
    def __init__(self, worktree_paths: List[str] = None):
        """Initialize agent registry."""
        self.agents: Dict[str, Agent] = {}
        self.worktree_paths = worktree_paths or [
            "worktrees/",
            "new-worktrees/"
        ]
        self._lock = asyncio.Lock()
        
    async def register_agent(self, agent: Agent) -> bool:
        """Register a new agent or update existing one."""
        async with self._lock:
            try:
                agent.last_seen = datetime.utcnow()
                self.agents[agent.id] = agent
                logger.info(f"Registered agent: {agent.name} ({agent.id})")
                return True
            except Exception as e:
                logger.error(f"Failed to register agent {agent.name}: {e}")
                return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        async with self._lock:
            if agent_id in self.agents:
                agent = self.agents.pop(agent_id)
                logger.info(f"Unregistered agent: {agent.name} ({agent_id})")
                return True
            return False
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    async def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        for agent in self.agents.values():
            if agent.name == name:
                return agent
        return None
    
    async def list_agents(self, status_filter: Optional[AgentStatus] = None) -> List[Agent]:
        """List all agents, optionally filtered by status."""
        agents = list(self.agents.values())
        if status_filter:
            agents = [a for a in agents if a.status == status_filter]
        return agents
    
    async def list_online_agents(self) -> List[Agent]:
        """List all online agents."""
        return [agent for agent in self.agents.values() if agent.is_online]
    
    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """Update agent status."""
        async with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].status = status
                self.agents[agent_id].last_seen = datetime.utcnow()
                logger.debug(f"Updated agent {agent_id} status to {status.value}")
                return True
            return False
    
    async def heartbeat(self, agent_id: str) -> bool:
        """Record agent heartbeat."""
        async with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].last_seen = datetime.utcnow()
                if self.agents[agent_id].status == AgentStatus.OFFLINE:
                    self.agents[agent_id].status = AgentStatus.ONLINE
                return True
            return False
    
    async def discover_agents(self) -> List[Agent]:
        """
        Discover agents from worktree directories.
        Scans for CLAUDE.md files and agent configuration.
        """
        discovered_agents = []
        
        for worktree_base in self.worktree_paths:
            worktree_path = Path(worktree_base)
            if not worktree_path.exists():
                continue
                
            # Scan subdirectories for agent configurations
            for agent_dir in worktree_path.iterdir():
                if not agent_dir.is_dir():
                    continue
                    
                agent = await self._parse_agent_config(agent_dir)
                if agent:
                    discovered_agents.append(agent)
        
        return discovered_agents
    
    async def _parse_agent_config(self, agent_dir: Path) -> Optional[Agent]:
        """Parse agent configuration from directory."""
        try:
            # Check for CLAUDE.md file
            claude_md = agent_dir / "CLAUDE.md"
            if not claude_md.exists():
                return None
            
            # Extract agent name from directory
            agent_name = agent_dir.name
            
            # Read capabilities and metadata from CLAUDE.md
            capabilities = []
            metadata = {}
            
            try:
                with open(claude_md, 'r') as f:
                    content = f.read()
                    
                # Parse basic capabilities from content
                if "agent" in content.lower():
                    capabilities.append("general")
                if "orchestration" in content.lower():
                    capabilities.append("orchestration")
                if "quality" in content.lower():
                    capabilities.append("quality")
                if "integration" in content.lower():
                    capabilities.append("integration")
                if "documentation" in content.lower():
                    capabilities.append("documentation")
                if "intelligence" in content.lower():
                    capabilities.append("intelligence")
                    
                metadata["claude_md_size"] = len(content)
                metadata["config_updated"] = claude_md.stat().st_mtime
                
            except Exception as e:
                logger.warning(f"Could not read CLAUDE.md for {agent_name}: {e}")
            
            # Check for additional config files
            config_files = [
                agent_dir / "agent.yml",
                agent_dir / "agent.yaml",
                agent_dir / "config.json"
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    config_data = await self._parse_config_file(config_file)
                    if config_data:
                        capabilities.extend(config_data.get("capabilities", []))
                        metadata.update(config_data.get("metadata", {}))
            
            # Create agent instance
            agent = Agent(
                name=agent_name,
                capabilities=list(set(capabilities)),  # Remove duplicates
                status=AgentStatus.OFFLINE,
                worktree_path=str(agent_dir),
                metadata=metadata
            )
            
            return agent
            
        except Exception as e:
            logger.error(f"Error parsing agent config in {agent_dir}: {e}")
            return None
    
    async def _parse_config_file(self, config_file: Path) -> Optional[Dict]:
        """Parse agent configuration file."""
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix in ['.yml', '.yaml']:
                    return yaml.safe_load(f)
                elif config_file.suffix == '.json':
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not parse config file {config_file}: {e}")
        return None
    
    async def cleanup_stale_agents(self, timeout_minutes: int = 10) -> int:
        """Remove agents that haven't been seen recently."""
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stale_agents = []
        
        async with self._lock:
            for agent_id, agent in self.agents.items():
                if agent.last_seen < cutoff:
                    stale_agents.append(agent_id)
                    agent.status = AgentStatus.OFFLINE
            
            for agent_id in stale_agents:
                if self.agents[agent_id].status == AgentStatus.OFFLINE:
                    del self.agents[agent_id]
                    logger.info(f"Removed stale agent: {agent_id}")
        
        return len(stale_agents)
    
    async def get_agents_by_capability(self, capability: str) -> List[Agent]:
        """Get agents that have a specific capability."""
        return [
            agent for agent in self.agents.values()
            if capability in agent.capabilities and agent.is_online
        ]
    
    async def get_registry_stats(self) -> Dict:
        """Get registry statistics."""
        online_agents = await self.list_online_agents()
        total_agents = len(self.agents)
        
        capabilities_count = {}
        for agent in self.agents.values():
            for capability in agent.capabilities:
                capabilities_count[capability] = capabilities_count.get(capability, 0) + 1
        
        return {
            "total_agents": total_agents,
            "online_agents": len(online_agents),
            "offline_agents": total_agents - len(online_agents),
            "capabilities": capabilities_count,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def auto_discovery_loop(self, interval_seconds: int = 60):
        """Continuously discover new agents."""
        while True:
            try:
                discovered = await self.discover_agents()
                for agent in discovered:
                    existing = await self.get_agent_by_name(agent.name)
                    if not existing:
                        await self.register_agent(agent)
                        logger.info(f"Auto-discovered agent: {agent.name}")
                
                # Cleanup stale agents
                await self.cleanup_stale_agents()
                
            except Exception as e:
                logger.error(f"Error in auto-discovery loop: {e}")
            
            await asyncio.sleep(interval_seconds)