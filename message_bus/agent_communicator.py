"""
Agent Communicator - Drop-in replacement for tmux-based communication

Provides simple interface for agents to send/receive messages via Redis message bus.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from contextlib import asynccontextmanager

from .message_bus import MessageBus, MessageBusConfig
from .message_protocol import AgentMessage, MessageType, MessagePriority, create_task_assignment


logger = logging.getLogger(__name__)


class AgentCommunicator:
    """
    Simple interface for agent-to-agent communication via message bus.
    
    Drop-in replacement for tmux-based scripts/agent_communicate.py
    """
    
    def __init__(self, agent_name: str, message_bus: Optional[MessageBus] = None):
        """
        Initialize agent communicator.
        
        Args:
            agent_name: Name of this agent
            message_bus: Message bus instance (creates new if None)
        """
        self.agent_name = agent_name
        self.message_bus = message_bus or MessageBus()
        self.message_handler: Optional[Callable] = None
        self.running = False
        
        logger.info(f"AgentCommunicator initialized for agent: {agent_name}")
    
    async def start(self) -> None:
        """Start the communicator and subscribe to messages."""
        if self.running:
            return
        
        await self.message_bus.start()
        await self.message_bus.subscribe_to_agent(self.agent_name, self._handle_incoming_message)
        self.running = True
        
        logger.info(f"Agent {self.agent_name} communicator started")
    
    async def stop(self) -> None:
        """Stop the communicator."""
        if not self.running:
            return
        
        await self.message_bus.unsubscribe_from_agent(self.agent_name)
        self.running = False
        
        logger.info(f"Agent {self.agent_name} communicator stopped")
    
    @asynccontextmanager
    async def lifespan(self):
        """Context manager for communicator lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
    
    def set_message_handler(self, handler: Callable[[AgentMessage], None]) -> None:
        """
        Set handler function for incoming messages.
        
        Args:
            handler: Async function to handle incoming messages
        """
        self.message_handler = handler
    
    async def send_message_to_agent(
        self,
        target_agent: str,
        message: str,
        message_type: MessageType = MessageType.INFORMATION_SHARE,
        priority: MessagePriority = MessagePriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a message to another agent.
        
        Args:
            target_agent: Name of target agent
            message: Message content
            message_type: Type of message
            priority: Message priority
            context: Additional context data
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            agent_message = AgentMessage(
                from_agent=self.agent_name,
                to_agent=target_agent,
                message_type=message_type,
                body={
                    "content": message,
                    "context": context or {}
                },
                priority=priority
            )
            
            success = await self.message_bus.publish_message(agent_message)
            
            if success:
                logger.info(f"Sent message to {target_agent}: {message[:50]}...")
            else:
                logger.error(f"Failed to send message to {target_agent}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending message to {target_agent}: {e}")
            return False
    
    async def send_task_assignment(
        self,
        target_agent: str,
        task_description: str,
        priority: MessagePriority = MessagePriority.MEDIUM,
        deadline: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a task assignment to another agent.
        
        Args:
            target_agent: Name of target agent
            task_description: Description of task to be performed
            priority: Task priority
            deadline: Optional deadline for task
            context: Additional context data
            
        Returns:
            bool: True if task assignment was sent successfully
        """
        try:
            task_message = create_task_assignment(
                from_agent=self.agent_name,
                to_agent=target_agent,
                task_description=task_description,
                priority=priority,
                deadline=deadline,
                context=context
            )
            
            success = await self.message_bus.publish_message(task_message)
            
            if success:
                logger.info(f"Assigned task to {target_agent}: {task_description[:50]}...")
            else:
                logger.error(f"Failed to assign task to {target_agent}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error assigning task to {target_agent}: {e}")
            return False
    
    async def broadcast_message(
        self,
        message: str,
        agents: Optional[list] = None,
        message_type: MessageType = MessageType.NOTIFICATION,
        priority: MessagePriority = MessagePriority.MEDIUM
    ) -> Dict[str, bool]:
        """
        Broadcast a message to multiple agents.
        
        Args:
            message: Message to broadcast
            agents: List of agent names (broadcasts to all if None)
            message_type: Type of message
            priority: Message priority
            
        Returns:
            Dict mapping agent names to success status
        """
        if agents is None:
            # Default agent list (could be configurable)
            agents = [
                "pm-agent",
                "frontend-agent", 
                "documentation-agent",
                "quality-agent",
                "integration-agent",
                "orchestration-agent"
            ]
        
        results = {}
        
        for agent in agents:
            if agent != self.agent_name:  # Don't send to self
                success = await self.send_message_to_agent(
                    target_agent=agent,
                    message=message,
                    message_type=message_type,
                    priority=priority
                )
                results[agent] = success
        
        successful_count = sum(results.values())
        logger.info(f"Broadcast message sent to {successful_count}/{len(results)} agents")
        
        return results
    
    async def reply_to_message(
        self,
        original_message: AgentMessage,
        reply_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a reply to a received message.
        
        Args:
            original_message: Original message to reply to
            reply_content: Content of reply
            context: Additional context data
            
        Returns:
            bool: True if reply was sent successfully
        """
        try:
            reply_message = original_message.create_reply(
                body={
                    "content": reply_content,
                    "context": context or {}
                }
            )
            
            success = await self.message_bus.publish_message(reply_message)
            
            if success:
                logger.info(f"Sent reply to {original_message.from_agent}")
            else:
                logger.error(f"Failed to send reply to {original_message.from_agent}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            return False
    
    async def get_pending_messages_count(self) -> int:
        """Get number of pending messages for this agent."""
        try:
            return await self.message_bus.get_agent_queue_size(self.agent_name)
        except Exception as e:
            logger.error(f"Error getting pending message count: {e}")
            return 0
    
    async def _handle_incoming_message(self, message: AgentMessage) -> None:
        """Internal handler for incoming messages."""
        try:
            logger.info(f"Received message from {message.from_agent}: {message.message_type.value}")
            
            # Call user-defined handler if set
            if self.message_handler:
                await self.message_handler(message)
            else:
                # Default handling - just log
                content = message.body.get('content', 'No content')
                logger.info(f"Message content: {content}")
            
        except Exception as e:
            logger.error(f"Error handling incoming message {message.message_id}: {e}")


# Utility functions for backward compatibility with tmux scripts

async def send_to_agent(target_agent: str, message: str, from_agent: str = "unknown") -> bool:
    """
    Drop-in replacement for tmux-based send_to_agent function.
    
    Args:
        target_agent: Name of target agent
        message: Message to send
        from_agent: Name of sending agent
        
    Returns:
        bool: True if message was sent successfully
    """
    config = MessageBusConfig()
    
    async with MessageBus(config).lifespan() as bus:
        communicator = AgentCommunicator(from_agent, bus)
        await communicator.start()
        
        success = await communicator.send_message_to_agent(
            target_agent=target_agent,
            message=message,
            message_type=MessageType.INFORMATION_SHARE,
            priority=MessagePriority.MEDIUM
        )
        
        await communicator.stop()
        return success


class SimpleAgentCommunicator:
    """
    Simplified interface for basic agent communication.
    
    Provides static methods for one-off message sending without managing
    persistent connections. Good for scripts and simple interactions.
    """
    
    @staticmethod
    async def send_message(
        from_agent: str,
        to_agent: str,
        message: str,
        priority: str = "medium"
    ) -> bool:
        """Send a simple message between agents."""
        
        priority_map = {
            "low": MessagePriority.LOW,
            "medium": MessagePriority.MEDIUM,
            "high": MessagePriority.HIGH,
            "urgent": MessagePriority.URGENT,
            "emergency": MessagePriority.EMERGENCY
        }
        
        msg_priority = priority_map.get(priority.lower(), MessagePriority.MEDIUM)
        
        return await send_to_agent(to_agent, message, from_agent)
    
    @staticmethod
    async def send_task(
        from_agent: str,
        to_agent: str,
        task_description: str,
        deadline: Optional[str] = None
    ) -> bool:
        """Send a task assignment between agents."""
        
        config = MessageBusConfig()
        
        async with MessageBus(config).lifespan() as bus:
            communicator = AgentCommunicator(from_agent, bus)
            await communicator.start()
            
            success = await communicator.send_task_assignment(
                target_agent=to_agent,
                task_description=task_description,
                deadline=deadline
            )
            
            await communicator.stop()
            return success