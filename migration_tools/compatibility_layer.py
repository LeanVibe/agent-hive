"""
Tmux-Message Queue Compatibility Layer

Provides zero-disruption migration from tmux to production message bus.
Ensures existing workflows continue working while agents gradually migrate.
"""

import asyncio
import subprocess
import logging
import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
import threading

# Import message bus components when available
try:
    from message_bus import MessageBus, MessageBusConfig, Message, MessageType, MessagePriority
    MESSAGE_BUS_AVAILABLE = True
except ImportError:
    MESSAGE_BUS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AgentConfiguration:
    """Configuration for agent during migration."""
    name: str
    mode: str  # "tmux", "hybrid", "message_bus"
    tmux_session: str = "agent-hive"
    tmux_window: Optional[str] = None
    capabilities: List[str] = None
    migration_priority: int = 1  # 1=high, 5=low
    fallback_enabled: bool = True
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.tmux_window is None:
            self.tmux_window = f"agent-{self.name}"


class TmuxMessageBridge:
    """
    Compatibility bridge between tmux and message bus.
    
    Provides transparent communication layer that works with both systems.
    Enables zero-disruption migration of agent communication.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize tmux-message bridge.
        
        Args:
            config: Bridge configuration
        """
        self.config = config or {}
        self.agents: Dict[str, AgentConfiguration] = {}
        self.message_bus: Optional[MessageBus] = None
        self.running = False
        
        # Migration state tracking
        self.migration_status = {
            "tmux_agents": set(),
            "hybrid_agents": set(), 
            "message_bus_agents": set(),
            "failed_agents": set()
        }
        
        # Communication statistics
        self.stats = {
            "tmux_messages": 0,
            "message_bus_messages": 0,
            "bridge_messages": 0,
            "failed_messages": 0
        }
        
        logger.info("TmuxMessageBridge initialized")
    
    async def start(self, enable_message_bus: bool = True) -> None:
        """
        Start the compatibility bridge.
        
        Args:
            enable_message_bus: Whether to start message bus component
        """
        if self.running:
            logger.warning("Bridge already running")
            return
        
        try:
            # Initialize message bus if available and requested
            if enable_message_bus and MESSAGE_BUS_AVAILABLE:
                bus_config = MessageBusConfig(
                    redis_url=self.config.get("redis_url", "redis://localhost:6379/0"),
                    heartbeat_interval=10
                )
                self.message_bus = MessageBus(bus_config)
                try:
                    await self.message_bus.start()
                    logger.info("Message bus component started")
                except Exception as e:
                    logger.warning(f"Message bus unavailable, continuing with tmux only: {e}")
                    self.message_bus = None
            
            # Discover existing tmux agents
            await self._discover_tmux_agents()
            
            self.running = True
            logger.info("TmuxMessageBridge started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start bridge: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the compatibility bridge."""
        if not self.running:
            return
        
        self.running = False
        
        if self.message_bus:
            await self.message_bus.stop()
        
        logger.info("TmuxMessageBridge stopped")
    
    async def send_message(self, target_agent: str, message: str, 
                          priority: str = "normal", force_mode: Optional[str] = None) -> bool:
        """
        Send message using appropriate transport.
        
        Args:
            target_agent: Target agent name
            message: Message content
            priority: Message priority
            force_mode: Force specific transport ("tmux" or "message_bus")
            
        Returns:
            True if message sent successfully
        """
        try:
            agent_config = self.agents.get(target_agent)
            if not agent_config:
                # Try to discover agent dynamically
                await self._discover_agent(target_agent)
                agent_config = self.agents.get(target_agent)
                
                if not agent_config:
                    logger.error(f"Agent {target_agent} not found")
                    return False
            
            # Determine transport method
            transport_mode = force_mode or agent_config.mode
            
            if transport_mode == "message_bus" and self.message_bus:
                success = await self._send_via_message_bus(target_agent, message, priority)
                if success:
                    self.stats["message_bus_messages"] += 1
                    return True
                elif agent_config.fallback_enabled:
                    logger.warning(f"Message bus failed for {target_agent}, falling back to tmux")
                    transport_mode = "tmux"
            
            if transport_mode in ["tmux", "hybrid"]:
                success = await self._send_via_tmux(agent_config, message)
                if success:
                    self.stats["tmux_messages"] += 1
                    return True
            
            self.stats["failed_messages"] += 1
            return False
            
        except Exception as e:
            logger.error(f"Failed to send message to {target_agent}: {e}")
            self.stats["failed_messages"] += 1
            return False
    
    async def migrate_agent(self, agent_name: str, target_mode: str) -> bool:
        """
        Migrate an agent to a different communication mode.
        
        Args:
            agent_name: Agent to migrate
            target_mode: Target mode ("tmux", "hybrid", "message_bus")
            
        Returns:
            True if migration successful
        """
        try:
            agent_config = self.agents.get(agent_name)
            if not agent_config:
                logger.error(f"Agent {agent_name} not found for migration")
                return False
            
            old_mode = agent_config.mode
            
            # Validate target mode
            if target_mode not in ["tmux", "hybrid", "message_bus"]:
                logger.error(f"Invalid target mode: {target_mode}")
                return False
            
            # Check if message bus is required but unavailable
            if target_mode in ["hybrid", "message_bus"] and not self.message_bus:
                logger.error(f"Cannot migrate to {target_mode}: message bus not available")
                return False
            
            # Test new mode before switching
            test_message = f"Migration test from {old_mode} to {target_mode}"
            test_success = await self.send_message(
                agent_name, 
                test_message, 
                force_mode=target_mode
            )
            
            if not test_success:
                logger.error(f"Migration test failed for {agent_name}")
                return False
            
            # Update agent configuration
            agent_config.mode = target_mode
            
            # Update migration status tracking
            self.migration_status[f"{old_mode}_agents"].discard(agent_name)
            self.migration_status[f"{target_mode}_agents"].add(agent_name)
            
            logger.info(f"Successfully migrated {agent_name} from {old_mode} to {target_mode}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate agent {agent_name}: {e}")
            return False
    
    async def get_agent_status(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get agent status across both communication systems.
        
        Args:
            agent_name: Specific agent or None for all agents
            
        Returns:
            Agent status information
        """
        try:
            if agent_name:
                agent_config = self.agents.get(agent_name)
                if not agent_config:
                    return {"error": f"Agent {agent_name} not found"}
                
                status = {
                    "name": agent_name,
                    "mode": agent_config.mode,
                    "capabilities": agent_config.capabilities,
                    "tmux_session": agent_config.tmux_session,
                    "tmux_window": agent_config.tmux_window,
                    "fallback_enabled": agent_config.fallback_enabled
                }
                
                # Check tmux availability
                status["tmux_available"] = await self._check_tmux_window(agent_config)
                
                # Check message bus availability
                if self.message_bus and agent_config.mode in ["hybrid", "message_bus"]:
                    mb_status = await self.message_bus.get_agent_status(agent_name)
                    status["message_bus_status"] = mb_status
                
                return status
            else:
                # Return all agents
                all_agents = {}
                for name in self.agents:
                    all_agents[name] = await self.get_agent_status(name)
                
                return {
                    "agents": all_agents,
                    "migration_status": dict(self.migration_status),
                    "statistics": self.stats
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _discover_tmux_agents(self) -> None:
        """Discover existing tmux agents."""
        try:
            # Get tmux session windows
            cmd = ["tmux", "list-windows", "-t", "agent-hive", "-F", "#{window_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                windows = result.stdout.strip().split('\n')
                for window in windows:
                    if window and window.startswith('agent-'):
                        agent_name = window.replace('agent-', '')
                        await self._discover_agent(agent_name)
                        
                logger.info(f"Discovered {len(self.agents)} tmux agents")
            else:
                logger.warning("No tmux session found or no agent windows")
                
        except Exception as e:
            logger.error(f"Failed to discover tmux agents: {e}")
    
    async def _discover_agent(self, agent_name: str) -> None:
        """Discover or register a specific agent."""
        if agent_name not in self.agents:
            # Create default configuration
            agent_config = AgentConfiguration(
                name=agent_name,
                mode="tmux",  # Start with tmux by default
                capabilities=self._infer_capabilities(agent_name)
            )
            
            self.agents[agent_name] = agent_config
            self.migration_status["tmux_agents"].add(agent_name)
            
            logger.info(f"Discovered agent: {agent_name}")
    
    def _infer_capabilities(self, agent_name: str) -> List[str]:
        """Infer agent capabilities from name."""
        # Map agent names to likely capabilities
        capability_map = {
            "integration-specialist": ["python", "testing", "fastapi", "integration"],
            "service-mesh": ["microservices", "kubernetes", "performance", "networking"],
            "frontend": ["react", "typescript", "ui/ux", "frontend"],
            "pm-agent": ["project-management", "coordination", "planning", "reporting"],
            "quality": ["testing", "validation", "quality-assurance"],
        }
        
        for pattern, capabilities in capability_map.items():
            if pattern in agent_name.lower():
                return capabilities
        
        return ["general"]  # Default capability
    
    async def _send_via_message_bus(self, target_agent: str, message: str, priority: str) -> bool:
        """Send message via message bus."""
        if not self.message_bus:
            return False
        
        try:
            # Map priority string to enum
            priority_map = {
                "low": MessagePriority.LOW,
                "normal": MessagePriority.NORMAL,
                "high": MessagePriority.HIGH,
                "urgent": MessagePriority.URGENT,
                "critical": MessagePriority.CRITICAL
            }
            
            msg_priority = priority_map.get(priority.lower(), MessagePriority.NORMAL)
            
            await self.message_bus.send_direct_message(
                target_agent=target_agent,
                message_type=MessageType.SYSTEM_COMMAND,
                payload={
                    "command": "execute",
                    "content": message,
                    "source": "bridge",
                    "timestamp": time.time()
                },
                priority=msg_priority
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Message bus send failed: {e}")
            return False
    
    async def _send_via_tmux(self, agent_config: AgentConfiguration, message: str) -> bool:
        """Send message via tmux."""
        try:
            # Use the existing tmux logic
            session_name = agent_config.tmux_session
            window_names_to_try = [
                agent_config.tmux_window,
                f"agent-{agent_config.name}",
                agent_config.name
            ]
            
            for window_name in window_names_to_try:
                if not window_name:
                    continue
                    
                try:
                    # Test if window exists
                    test_cmd = ["tmux", "list-windows", "-t", session_name, "-F", "#{window_name}"]
                    result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                    
                    if window_name not in result.stdout:
                        continue
                    
                    # Send message
                    subprocess.run(["tmux", "set-buffer", message], capture_output=True, text=True)
                    subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:{window_name}", "C-c"], capture_output=True)
                    await asyncio.sleep(0.1)
                    subprocess.run(["tmux", "paste-buffer", "-t", f"{session_name}:{window_name}"], capture_output=True, text=True)
                    await asyncio.sleep(0.1)
                    subprocess.run(["tmux", "send-keys", "-t", f"{session_name}:{window_name}", "Enter"], capture_output=True)
                    
                    return True
                    
                except Exception as e:
                    logger.debug(f"Failed to send via tmux window {window_name}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Tmux send failed: {e}")
            return False
    
    async def _check_tmux_window(self, agent_config: AgentConfiguration) -> bool:
        """Check if tmux window exists for agent."""
        try:
            cmd = ["tmux", "list-windows", "-t", agent_config.tmux_session, "-F", "#{window_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                windows = result.stdout.strip().split('\n')
                return agent_config.tmux_window in windows
            
            return False
            
        except Exception:
            return False


class DualModeOperator:
    """
    Dual-mode operation manager for gradual migration.
    
    Operates both tmux and message bus systems simultaneously,
    providing seamless migration capability.
    """
    
    def __init__(self, bridge: TmuxMessageBridge):
        """
        Initialize dual-mode operator.
        
        Args:
            bridge: Tmux-message bridge instance
        """
        self.bridge = bridge
        self.migration_plan: Dict[str, Dict[str, Any]] = {}
        self.active_migrations: Dict[str, datetime] = {}
        
    async def create_migration_plan(self, agents: List[str], strategy: str = "gradual") -> Dict[str, Any]:
        """
        Create migration plan for agents.
        
        Args:
            agents: List of agents to migrate
            strategy: Migration strategy ("gradual", "immediate", "canary")
            
        Returns:
            Migration plan
        """
        plan = {
            "strategy": strategy,
            "agents": [],
            "phases": [],
            "estimated_duration": 0,
            "rollback_points": []
        }
        
        if strategy == "gradual":
            # Migrate agents in priority order
            sorted_agents = await self._sort_agents_by_priority(agents)
            
            for i, agent in enumerate(sorted_agents):
                phase = {
                    "phase": i + 1,
                    "agent": agent,
                    "mode_sequence": ["tmux", "hybrid", "message_bus"],
                    "validation_steps": [
                        "test_tmux_communication",
                        "test_message_bus_communication", 
                        "test_dual_mode",
                        "validate_performance"
                    ],
                    "estimated_time": 10  # minutes per agent
                }
                plan["phases"].append(phase)
                plan["agents"].append(agent)
            
            plan["estimated_duration"] = len(agents) * 10
            
        elif strategy == "canary":
            # Migrate one canary agent first, then others
            if agents:
                canary_agent = agents[0]
                remaining_agents = agents[1:]
                
                # Canary phase
                plan["phases"].append({
                    "phase": 1,
                    "type": "canary",
                    "agent": canary_agent,
                    "mode_sequence": ["tmux", "hybrid", "message_bus"],
                    "validation_period": 30  # minutes
                })
                
                # Bulk migration phase
                if remaining_agents:
                    plan["phases"].append({
                        "phase": 2,
                        "type": "bulk",
                        "agents": remaining_agents,
                        "mode_sequence": ["hybrid", "message_bus"],
                        "estimated_time": 5  # minutes per agent
                    })
        
        self.migration_plan = plan
        return plan
    
    async def execute_migration(self, plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute migration plan.
        
        Args:
            plan: Migration plan (uses stored plan if None)
            
        Returns:
            Migration results
        """
        if plan:
            self.migration_plan = plan
        
        if not self.migration_plan:
            raise ValueError("No migration plan available")
        
        results = {
            "status": "in_progress",
            "completed_phases": [],
            "failed_phases": [],
            "current_phase": None,
            "start_time": datetime.now(),
            "errors": []
        }
        
        try:
            for phase in self.migration_plan["phases"]:
                results["current_phase"] = phase
                
                phase_result = await self._execute_phase(phase)
                
                if phase_result["success"]:
                    results["completed_phases"].append(phase_result)
                else:
                    results["failed_phases"].append(phase_result)
                    results["errors"].extend(phase_result.get("errors", []))
                    
                    # Stop on failure for safety
                    results["status"] = "failed"
                    break
            
            if results["status"] == "in_progress":
                results["status"] = "completed"
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(str(e))
        
        return results
    
    async def _sort_agents_by_priority(self, agents: List[str]) -> List[str]:
        """Sort agents by migration priority."""
        agent_priorities = []
        
        for agent in agents:
            config = self.bridge.agents.get(agent)
            priority = config.migration_priority if config else 5
            agent_priorities.append((priority, agent))
        
        # Sort by priority (lower number = higher priority)
        agent_priorities.sort(key=lambda x: x[0])
        
        return [agent for _, agent in agent_priorities]
    
    async def _execute_phase(self, phase: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single migration phase."""
        phase_result = {
            "phase": phase,
            "success": False,
            "start_time": datetime.now(),
            "errors": [],
            "validations": []
        }
        
        try:
            if phase.get("type") == "canary":
                # Canary migration
                agent = phase["agent"]
                success = await self._migrate_agent_sequence(agent, phase["mode_sequence"])
                phase_result["success"] = success
                
                if success:
                    # Wait for validation period
                    await asyncio.sleep(5)  # Shortened for testing
                    validation_result = await self._validate_agent_performance(agent)
                    phase_result["validations"].append(validation_result)
                    phase_result["success"] = validation_result["passed"]
                
            elif phase.get("type") == "bulk":
                # Bulk migration
                agents = phase["agents"]
                successes = 0
                
                for agent in agents:
                    success = await self._migrate_agent_sequence(agent, phase["mode_sequence"])
                    if success:
                        successes += 1
                    else:
                        phase_result["errors"].append(f"Failed to migrate {agent}")
                
                phase_result["success"] = successes == len(agents)
                
            else:
                # Single agent migration
                agent = phase["agent"]
                success = await self._migrate_agent_sequence(agent, phase["mode_sequence"])
                phase_result["success"] = success
        
        except Exception as e:
            phase_result["errors"].append(str(e))
        
        phase_result["end_time"] = datetime.now()
        return phase_result
    
    async def _migrate_agent_sequence(self, agent: str, mode_sequence: List[str]) -> bool:
        """Migrate agent through sequence of modes."""
        try:
            for mode in mode_sequence:
                success = await self.bridge.migrate_agent(agent, mode)
                if not success:
                    return False
                
                # Brief pause between mode changes
                await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration sequence failed for {agent}: {e}")
            return False
    
    async def _validate_agent_performance(self, agent: str) -> Dict[str, Any]:
        """Validate agent performance after migration."""
        validation = {
            "agent": agent,
            "passed": False,
            "tests": [],
            "timestamp": datetime.now()
        }
        
        try:
            # Test message sending
            test_message = f"Performance validation test for {agent}"
            send_success = await self.bridge.send_message(agent, test_message)
            
            validation["tests"].append({
                "test": "message_sending",
                "passed": send_success
            })
            
            # Test status retrieval
            status = await self.bridge.get_agent_status(agent)
            status_success = "error" not in status
            
            validation["tests"].append({
                "test": "status_retrieval", 
                "passed": status_success
            })
            
            # Overall validation
            validation["passed"] = all(test["passed"] for test in validation["tests"])
            
        except Exception as e:
            validation["tests"].append({
                "test": "validation_error",
                "passed": False,
                "error": str(e)
            })
        
        return validation