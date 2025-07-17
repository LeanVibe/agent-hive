"""
Production Agent Communicator

Replaces tmux-based communication with production message bus system.
Provides reliable, distributed agent communication with discovery and monitoring.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Set
import uuid

from .message_bus import MessageBus, MessageBusConfig
from .message_protocol import (
    Message, MessageType, MessagePriority,
    create_task_assignment, create_agent_heartbeat, create_system_command
)


logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Agent information for discovery service."""
    name: str
    status: str
    capabilities: List[str]
    current_task: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentRegistry:
    """
    Distributed agent registry using message bus.

    Tracks agent availability, capabilities, and health status.
    """

    def __init__(self, message_bus: MessageBus):
        """
        Initialize agent registry.

        Args:
            message_bus: Message bus instance
        """
        self.message_bus = message_bus
        self.local_agents: Dict[str, AgentInfo] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.discovery_interval = 30  # seconds

    async def start(self) -> None:
        """Start the agent registry."""
        # Start heartbeat monitoring
        self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        logger.info("Agent registry started")

    async def stop(self) -> None:
        """Stop the agent registry."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        logger.info("Agent registry stopped")

    async def register_agent(self, agent_name: str, capabilities: List[str],
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register an agent.

        Args:
            agent_name: Agent name
            capabilities: Agent capabilities
            metadata: Additional metadata
        """
        agent_info = AgentInfo(
            name=agent_name,
            status="active",
            capabilities=capabilities,
            last_heartbeat=datetime.now(),
            metadata=metadata or {}
        )

        self.local_agents[agent_name] = agent_info

        # Register in message bus
        await self.message_bus.register_agent(agent_name, {
            "capabilities": capabilities,
            "metadata": metadata or {}
        })

        logger.info(f"Registered agent: {agent_name} with capabilities: {capabilities}")

    async def unregister_agent(self, agent_name: str) -> None:
        """
        Unregister an agent.

        Args:
            agent_name: Agent name
        """
        if agent_name in self.local_agents:
            del self.local_agents[agent_name]

        # Send farewell message
        await self.message_bus.send_direct_message(
            target_agent="system",
            message_type=MessageType.AGENT_STATUS,
            payload={
                "agent_name": agent_name,
                "status": "disconnected",
                "timestamp": datetime.now().isoformat()
            }
        )

        logger.info(f"Unregistered agent: {agent_name}")

    async def update_agent_status(self, agent_name: str, status: str,
                                current_task: Optional[str] = None) -> None:
        """
        Update agent status.

        Args:
            agent_name: Agent name
            status: New status
            current_task: Current task ID
        """
        if agent_name in self.local_agents:
            self.local_agents[agent_name].status = status
            self.local_agents[agent_name].current_task = current_task
            self.local_agents[agent_name].last_heartbeat = datetime.now()

        # Update in message bus
        await self.message_bus.update_agent_heartbeat(agent_name, status, current_task)

        logger.debug(f"Updated agent {agent_name} status: {status}")

    async def find_capable_agents(self, required_capabilities: List[str]) -> List[AgentInfo]:
        """
        Find agents with required capabilities.

        Args:
            required_capabilities: Required capabilities

        Returns:
            List of capable agents
        """
        capable_agents = []

        # Get all active agents from message bus
        active_agents = await self.message_bus.get_active_agents()

        for agent_data in active_agents:
            agent_capabilities = agent_data.get("metadata", {}).get("capabilities", [])

            # Check if agent has all required capabilities
            if all(cap in agent_capabilities for cap in required_capabilities):
                agent_info = AgentInfo(
                    name=agent_data["name"],
                    status=agent_data["status"],
                    capabilities=agent_capabilities,
                    current_task=agent_data.get("current_task"),
                    last_heartbeat=datetime.fromisoformat(agent_data["last_heartbeat"]),
                    metadata=agent_data.get("metadata", {})
                )
                capable_agents.append(agent_info)

        # Sort by availability (idle agents first)
        capable_agents.sort(key=lambda a: (a.current_task is not None, a.last_heartbeat), reverse=True)

        return capable_agents

    async def get_agent_info(self, agent_name: str) -> Optional[AgentInfo]:
        """
        Get agent information.

        Args:
            agent_name: Agent name

        Returns:
            Agent info or None if not found
        """
        # Check local cache first
        if agent_name in self.local_agents:
            return self.local_agents[agent_name]

        # Query message bus
        agent_data = await self.message_bus.get_agent_status(agent_name)
        if agent_data:
            return AgentInfo(
                name=agent_data["name"],
                status=agent_data["status"],
                capabilities=agent_data.get("metadata", {}).get("capabilities", []),
                current_task=agent_data.get("current_task"),
                last_heartbeat=datetime.fromisoformat(agent_data["last_heartbeat"]),
                metadata=agent_data.get("metadata", {})
            )

        return None

    async def get_all_agents(self) -> List[AgentInfo]:
        """Get all registered agents."""
        active_agents = await self.message_bus.get_active_agents()

        agents = []
        for agent_data in active_agents:
            agent_info = AgentInfo(
                name=agent_data["name"],
                status=agent_data["status"],
                capabilities=agent_data.get("metadata", {}).get("capabilities", []),
                current_task=agent_data.get("current_task"),
                last_heartbeat=datetime.fromisoformat(agent_data["last_heartbeat"]),
                metadata=agent_data.get("metadata", {})
            )
            agents.append(agent_info)

        return agents

    async def _heartbeat_monitor(self) -> None:
        """Monitor agent heartbeats and update registry."""
        while True:
            try:
                current_time = datetime.now()

                # Send heartbeats for local agents
                for agent_name, agent_info in self.local_agents.items():
                    await self.update_agent_status(
                        agent_name,
                        agent_info.status,
                        agent_info.current_task
                    )

                # Sleep until next heartbeat
                await asyncio.sleep(self.discovery_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(5)


class AgentCommunicator:
    """
    Production agent communicator replacing tmux-based system.

    Provides reliable, distributed communication with:
    - Message persistence and acknowledgment
    - Agent discovery and capability matching
    - Load balancing and routing
    - Monitoring and metrics
    """

    def __init__(self, agent_name: str, capabilities: List[str],
                 config: Optional[MessageBusConfig] = None):
        """
        Initialize agent communicator.

        Args:
            agent_name: This agent's name
            capabilities: This agent's capabilities
            config: Message bus configuration
        """
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.config = config or MessageBusConfig()

        # Core components
        self.message_bus = MessageBus(self.config)
        self.registry = AgentRegistry(self.message_bus)

        # Message handling
        self.running = False
        self.handlers: Dict[MessageType, List[Callable]] = {}

        # Task management
        self.current_task: Optional[str] = None
        self.task_queue: List[Dict[str, Any]] = []

        # Performance tracking
        self.confidence_thresholds = {
            "low": 0.6,
            "medium": 0.75,
            "high": 0.9
        }

        logger.info(f"AgentCommunicator initialized for {agent_name}")

    async def start(self) -> None:
        """Start the agent communicator."""
        if self.running:
            logger.warning("Agent communicator already running")
            return

        try:
            # Start message bus
            await self.message_bus.start()

            # Start registry
            await self.registry.start()

            # Register this agent
            await self.registry.register_agent(
                self.agent_name,
                self.capabilities,
                {"started_at": datetime.now().isoformat()}
            )

            # Register default message handlers
            self._register_default_handlers()

            self.running = True
            logger.info(f"Agent communicator started for {self.agent_name}")

        except Exception as e:
            logger.error(f"Failed to start agent communicator: {e}")
            raise

    async def stop(self) -> None:
        """Stop the agent communicator."""
        if not self.running:
            return

        self.running = False

        # Unregister agent
        await self.registry.unregister_agent(self.agent_name)

        # Stop components
        await self.registry.stop()
        await self.message_bus.stop()

        logger.info(f"Agent communicator stopped for {self.agent_name}")

    async def send_message_to_agent(self, target_agent: str, message_type: MessageType,
                                   payload: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL,
                                   wait_for_response: bool = False, timeout: float = 30.0) -> Optional[Message]:
        """
        Send a message to a specific agent.

        Args:
            target_agent: Target agent name
            message_type: Message type
            payload: Message payload
            priority: Message priority
            wait_for_response: Wait for response
            timeout: Response timeout

        Returns:
            Response message if waiting for response
        """
        try:
            # Create message
            correlation_id = str(uuid.uuid4()) if wait_for_response else None
            reply_to = f"replies.{self.agent_name}" if wait_for_response else None

            message = Message.create(
                message_type=message_type,
                payload=payload,
                source_agent=self.agent_name,
                target_agent=target_agent,
                priority=priority,
                correlation_id=correlation_id,
                reply_to=reply_to,
                routing_key=f"agent.{target_agent}"
            )

            # Send message
            message_id = await self.message_bus.send_message(message)

            # Wait for response if requested
            if wait_for_response:
                return await self._wait_for_response(correlation_id, timeout)

            return None

        except Exception as e:
            logger.error(f"Failed to send message to {target_agent}: {e}")
            raise

    async def broadcast_message(self, message_type: MessageType, payload: Dict[str, Any],
                               target_group: str = "all", priority: MessagePriority = MessagePriority.NORMAL) -> str:
        """
        Broadcast a message to all agents in a group.

        Args:
            message_type: Message type
            payload: Message payload
            target_group: Target group
            priority: Message priority

        Returns:
            Message ID
        """
        return await self.message_bus.broadcast_message(message_type, payload, target_group, priority)

    async def assign_task_to_best_agent(self, task_description: str, required_skills: List[str],
                                       confidence_threshold: float = 0.75) -> Optional[str]:
        """
        Assign a task to the best available agent.

        Args:
            task_description: Task description
            required_skills: Required skills
            confidence_threshold: Minimum confidence threshold

        Returns:
            Assigned agent name or None if no suitable agent found
        """
        try:
            # Find capable agents
            capable_agents = await self.registry.find_capable_agents(required_skills)

            if not capable_agents:
                logger.warning(f"No agents found with required skills: {required_skills}")
                return None

            # Select best agent (first available)
            best_agent = capable_agents[0]

            # Create task assignment
            task_id = f"task_{int(datetime.now().timestamp())}"

            await self.send_message_to_agent(
                best_agent.name,
                MessageType.TASK_ASSIGNMENT,
                {
                    "task_id": task_id,
                    "description": task_description,
                    "required_skills": required_skills,
                    "confidence_threshold": confidence_threshold,
                    "assigned_by": self.agent_name,
                    "assigned_at": datetime.now().isoformat()
                },
                priority=MessagePriority.HIGH
            )

            logger.info(f"Assigned task {task_id} to agent {best_agent.name}")
            return best_agent.name

        except Exception as e:
            logger.error(f"Failed to assign task: {e}")
            return None

    async def update_status(self, status: str, current_task: Optional[str] = None) -> None:
        """
        Update this agent's status.

        Args:
            status: New status
            current_task: Current task ID
        """
        self.current_task = current_task
        await self.registry.update_agent_status(self.agent_name, status, current_task)

    def register_handler(self, message_type: MessageType, handler: Callable[[Message], Any]) -> None:
        """
        Register a message handler.

        Args:
            message_type: Message type to handle
            handler: Handler function
        """
        if message_type not in self.handlers:
            self.handlers[message_type] = []

        self.handlers[message_type].append(handler)
        self.message_bus.register_handler(message_type, handler)

    async def get_agent_statistics(self) -> Dict[str, Any]:
        """Get agent communication statistics."""
        bus_stats = await self.message_bus.get_statistics()

        return {
            "agent_name": self.agent_name,
            "capabilities": self.capabilities,
            "current_task": self.current_task,
            "task_queue_size": len(self.task_queue),
            "confidence_thresholds": self.confidence_thresholds,
            "message_bus": bus_stats,
            "uptime": "TODO"  # Calculate uptime
        }

    # Private methods

    def _register_default_handlers(self) -> None:
        """Register default message handlers."""

        async def handle_task_assignment(message: Message) -> None:
            """Handle task assignment."""
            task_data = message.payload
            task_id = task_data.get("task_id")

            logger.info(f"Received task assignment: {task_id}")

            # Add to task queue
            self.task_queue.append(task_data)

            # Send acknowledgment
            reply = message.create_reply({
                "status": "accepted",
                "task_id": task_id,
                "agent": self.agent_name,
                "queued_at": datetime.now().isoformat()
            })

            await self.message_bus.send_message(reply)

        async def handle_system_command(message: Message) -> None:
            """Handle system commands."""
            command_data = message.payload
            command = command_data.get("command")

            logger.info(f"Received system command: {command}")

            # Process common commands
            if command == "ping":
                reply = message.create_reply({
                    "status": "pong",
                    "agent": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                })
                await self.message_bus.send_message(reply)

            elif command == "status":
                stats = await self.get_agent_statistics()
                reply = message.create_reply(stats)
                await self.message_bus.send_message(reply)

        # Register handlers
        self.register_handler(MessageType.TASK_ASSIGNMENT, handle_task_assignment)
        self.register_handler(MessageType.SYSTEM_COMMAND, handle_system_command)

    async def _wait_for_response(self, correlation_id: str, timeout: float) -> Optional[Message]:
        """Wait for a response message."""
        # This is simplified - in production you'd use proper response tracking
        # For now, we'll just wait and return None
        await asyncio.sleep(min(timeout, 1.0))
        return None
