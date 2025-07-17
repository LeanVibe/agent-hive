"""
Message Broker for intelligent routing, load balancing, and persistence.
Handles complex routing logic and ensures message delivery guarantees.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import asdict
import json
import re

from .models import (
    Message,
    MessagePriority,
    MessageStatus,
    Agent,
    AgentStatus,
    BroadcastMessage,
    DeliveryReceipt
)
from .queue_service import MessageQueueService
from .agent_registry import AgentRegistry


logger = logging.getLogger(__name__)


class RoutingRule:
    """Defines routing rules for message delivery."""

    def __init__(self,
                 name: str,
                 condition: str,
                 target_capability: Optional[str] = None,
                 target_agents: Optional[List[str]] = None,
                 load_balance: bool = False,
                 priority_boost: Optional[MessagePriority] = None):
        self.name = name
        self.condition = condition  # Python expression or regex pattern
        self.target_capability = target_capability
        self.target_agents = target_agents or []
        self.load_balance = load_balance
        self.priority_boost = priority_boost

    def matches(self, message: Message) -> bool:
        """Check if message matches this routing rule."""
        try:
            # Simple keyword matching for now
            content_lower = message.content.lower()
            sender_lower = message.sender.lower()

            # Check for specific patterns
            if "urgent" in content_lower or "critical" in content_lower:
                return self.name == "urgent_routing"
            elif "quality" in content_lower or "test" in content_lower:
                return self.name == "quality_routing"
            elif "orchestrat" in content_lower or "coordinat" in content_lower:
                return self.name == "orchestration_routing"
            elif "document" in content_lower or "readme" in content_lower:
                return self.name == "documentation_routing"
            elif "integrat" in content_lower or "deploy" in content_lower:
                return self.name == "integration_routing"
            elif "intelligence" in content_lower or "analysis" in content_lower:
                return self.name == "intelligence_routing"

            return False

        except Exception as e:
            logger.error(f"Error evaluating routing rule {self.name}: {e}")
            return False


class LoadBalancer:
    """Load balancer for distributing messages across agents."""

    def __init__(self):
        self.agent_load: Dict[str, int] = {}
        self.last_assigned: Dict[str, str] = {}  # capability -> agent_id

    def select_agent(self, agents: List[Agent], strategy: str = "round_robin") -> Optional[Agent]:
        """Select best agent based on load balancing strategy."""
        if not agents:
            return None

        if strategy == "round_robin":
            return self._round_robin_selection(agents)
        elif strategy == "least_loaded":
            return self._least_loaded_selection(agents)
        elif strategy == "capability_based":
            return self._capability_based_selection(agents)
        else:
            return agents[0]  # Default to first available

    def _round_robin_selection(self, agents: List[Agent]) -> Agent:
        """Round-robin agent selection."""
        if len(agents) == 1:
            return agents[0]

        # Simple round-robin based on last assignment
        agent_ids = [agent.id for agent in agents]

        # Find next agent in rotation
        try:
            last_index = agent_ids.index(self.last_assigned.get("general", ""))
            next_index = (last_index + 1) % len(agents)
        except ValueError:
            next_index = 0

        selected_agent = agents[next_index]
        self.last_assigned["general"] = selected_agent.id
        return selected_agent

    def _least_loaded_selection(self, agents: List[Agent]) -> Agent:
        """Select agent with least current load."""
        min_load = float('inf')
        selected_agent = agents[0]

        for agent in agents:
            load = self.agent_load.get(agent.id, 0)
            if load < min_load:
                min_load = load
                selected_agent = agent

        return selected_agent

    def _capability_based_selection(self, agents: List[Agent]) -> Agent:
        """Select agent based on capabilities match."""
        # For now, just return first agent
        # Could be enhanced to match specific capabilities
        return agents[0]

    def record_assignment(self, agent_id: str):
        """Record message assignment to agent."""
        self.agent_load[agent_id] = self.agent_load.get(agent_id, 0) + 1

    def record_completion(self, agent_id: str):
        """Record message completion by agent."""
        if agent_id in self.agent_load:
            self.agent_load[agent_id] = max(0, self.agent_load[agent_id] - 1)


class MessageBroker:
    """
    Intelligent message broker for routing, load balancing, and persistence.
    Coordinates between the message queue and agent registry.
    """

    def __init__(self,
                 queue_service: MessageQueueService,
                 agent_registry: AgentRegistry):
        self.queue_service = queue_service
        self.agent_registry = agent_registry
        self.routing_rules: List[RoutingRule] = []
        self.load_balancer = LoadBalancer()
        self.message_callbacks: Dict[str, List[Callable]] = {}
        self.is_running = False
        self._broker_tasks: List[asyncio.Task] = []

        # Performance metrics
        self.messages_routed = 0
        self.routing_failures = 0
        self.average_routing_time = 0.0

        self._setup_default_routing_rules()

    def _setup_default_routing_rules(self):
        """Setup default routing rules based on message content."""
        self.routing_rules = [
            RoutingRule(
                name="urgent_routing",
                condition="priority == 'critical' or 'urgent' in content.lower()",
                target_capability="orchestration",
                priority_boost=MessagePriority.CRITICAL
            ),
            RoutingRule(
                name="quality_routing",
                condition="'quality' in content.lower() or 'test' in content.lower()",
                target_capability="quality",
                load_balance=True
            ),
            RoutingRule(
                name="orchestration_routing",
                condition="'orchestrat' in content.lower() or 'coordinat' in content.lower()",
                target_capability="orchestration"
            ),
            RoutingRule(
                name="documentation_routing",
                condition="'document' in content.lower() or 'readme' in content.lower()",
                target_capability="documentation"
            ),
            RoutingRule(
                name="integration_routing",
                condition="'integrat' in content.lower() or 'deploy' in content.lower()",
                target_capability="integration"
            ),
            RoutingRule(
                name="intelligence_routing",
                condition="'intelligence' in content.lower() or 'analysis' in content.lower()",
                target_capability="intelligence"
            )
        ]

    async def start(self):
        """Start the message broker."""
        self.is_running = True

        # Start background tasks
        self._broker_tasks = [
            asyncio.create_task(self._route_messages_loop()),
            asyncio.create_task(self._monitor_agent_health()),
            asyncio.create_task(self._optimize_routing())
        ]

        logger.info("Message broker started")

    async def stop(self):
        """Stop the message broker."""
        self.is_running = False

        # Cancel background tasks
        for task in self._broker_tasks:
            task.cancel()

        if self._broker_tasks:
            await asyncio.gather(*self._broker_tasks, return_exceptions=True)

        logger.info("Message broker stopped")

    async def route_message(self, message: Message) -> bool:
        """Route a single message using intelligent routing."""
        start_time = datetime.utcnow()

        try:
            # Apply routing rules
            target_agents = await self._apply_routing_rules(message)

            if not target_agents:
                # Fallback to any available agent
                target_agents = await self.agent_registry.list_online_agents()

            if not target_agents:
                logger.warning(f"No available agents for message {message.id}")
                return False

            # Load balance if multiple agents available
            selected_agent = self.load_balancer.select_agent(target_agents, "least_loaded")

            if not selected_agent:
                return False

            # Update message recipient to selected agent
            message.recipient = selected_agent.id

            # Apply priority boost if rule specifies
            for rule in self.routing_rules:
                if rule.matches(message) and rule.priority_boost:
                    message.priority = rule.priority_boost
                    break

            # Send message
            success = await self.queue_service.send_message(message)

            if success:
                self.load_balancer.record_assignment(selected_agent.id)
                self.messages_routed += 1

                # Calculate routing time
                routing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.average_routing_time = (
                    (self.average_routing_time * (self.messages_routed - 1) + routing_time)
                    / self.messages_routed
                )

                logger.debug(f"Routed message {message.id} to agent {selected_agent.name}")
                return True
            else:
                self.routing_failures += 1
                return False

        except Exception as e:
            logger.error(f"Error routing message {message.id}: {e}")
            self.routing_failures += 1
            return False

    async def route_broadcast(self, broadcast: BroadcastMessage) -> int:
        """Route a broadcast message to multiple agents."""
        try:
            # Get target agents
            if broadcast.recipients:
                target_agents = []
                for recipient_id in broadcast.recipients:
                    agent = await self.agent_registry.get_agent(recipient_id)
                    if agent and agent.is_online:
                        target_agents.append(agent)
            else:
                # Broadcast to all online agents
                target_agents = await self.agent_registry.list_online_agents()

            if not target_agents:
                logger.warning(f"No target agents for broadcast {broadcast.id}")
                return 0

            # Convert to individual messages
            individual_messages = broadcast.to_individual_messages([a.id for a in target_agents])

            # Route each message
            sent_count = 0
            for message in individual_messages:
                if await self.route_message(message):
                    sent_count += 1

            logger.info(f"Routed broadcast {broadcast.id} to {sent_count}/{len(individual_messages)} agents")
            return sent_count

        except Exception as e:
            logger.error(f"Error routing broadcast {broadcast.id}: {e}")
            return 0

    async def _apply_routing_rules(self, message: Message) -> List[Agent]:
        """Apply routing rules to find target agents."""
        target_agents = []

        for rule in self.routing_rules:
            if rule.matches(message):
                if rule.target_capability:
                    # Find agents with specific capability
                    capability_agents = await self.agent_registry.get_agents_by_capability(
                        rule.target_capability
                    )
                    target_agents.extend(capability_agents)

                if rule.target_agents:
                    # Find specific target agents
                    for agent_id in rule.target_agents:
                        agent = await self.agent_registry.get_agent(agent_id)
                        if agent and agent.is_online:
                            target_agents.append(agent)

                # If rule matches, we found our routing
                break

        # Remove duplicates
        unique_agents = []
        seen_ids = set()
        for agent in target_agents:
            if agent.id not in seen_ids:
                unique_agents.append(agent)
                seen_ids.add(agent.id)

        return unique_agents

    async def add_routing_rule(self, rule: RoutingRule):
        """Add a new routing rule."""
        self.routing_rules.append(rule)
        logger.info(f"Added routing rule: {rule.name}")

    async def remove_routing_rule(self, rule_name: str) -> bool:
        """Remove a routing rule by name."""
        for i, rule in enumerate(self.routing_rules):
            if rule.name == rule_name:
                del self.routing_rules[i]
                logger.info(f"Removed routing rule: {rule_name}")
                return True
        return False

    async def register_message_callback(self, event_type: str, callback: Callable):
        """Register callback for message events."""
        if event_type not in self.message_callbacks:
            self.message_callbacks[event_type] = []
        self.message_callbacks[event_type].append(callback)

    async def _trigger_callbacks(self, event_type: str, data: Any):
        """Trigger registered callbacks for an event."""
        if event_type in self.message_callbacks:
            for callback in self.message_callbacks[event_type]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error in callback for {event_type}: {e}")

    async def _route_messages_loop(self):
        """Background task to continuously route messages."""
        while self.is_running:
            try:
                # This would integrate with the queue service
                # For now, we'll just sleep
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in routing loop: {e}")
                await asyncio.sleep(5)

    async def _monitor_agent_health(self):
        """Monitor agent health and adjust routing accordingly."""
        while self.is_running:
            try:
                # Check agent health
                agents = await self.agent_registry.list_agents()

                for agent in agents:
                    # Check if agent is responsive
                    if not agent.is_online:
                        # Remove from load balancer
                        if agent.id in self.load_balancer.agent_load:
                            del self.load_balancer.agent_load[agent.id]

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)

    async def _optimize_routing(self):
        """Optimize routing rules based on performance metrics."""
        while self.is_running:
            try:
                # Analyze routing performance
                if self.messages_routed > 100:  # Only optimize after some data
                    success_rate = (self.messages_routed - self.routing_failures) / self.messages_routed

                    if success_rate < 0.95:  # Less than 95% success rate
                        logger.warning(f"Low routing success rate: {success_rate:.2%}")
                        # Could implement automatic rule adjustment here

                await asyncio.sleep(300)  # Optimize every 5 minutes

            except Exception as e:
                logger.error(f"Error in routing optimization: {e}")
                await asyncio.sleep(600)

    async def get_broker_stats(self) -> Dict:
        """Get broker performance statistics."""
        return {
            "messages_routed": self.messages_routed,
            "routing_failures": self.routing_failures,
            "success_rate": (
                (self.messages_routed - self.routing_failures) / max(self.messages_routed, 1)
            ),
            "average_routing_time_ms": self.average_routing_time,
            "active_routing_rules": len(self.routing_rules),
            "agent_load": dict(self.load_balancer.agent_load),
            "is_running": self.is_running
        }

    async def smart_route_by_content(self, content: str) -> List[str]:
        """Intelligently suggest agents based on message content."""
        suggestions = []

        content_lower = content.lower()

        # Analyze content for keywords
        if any(word in content_lower for word in ["quality", "test", "bug", "error"]):
            quality_agents = await self.agent_registry.get_agents_by_capability("quality")
            suggestions.extend([agent.id for agent in quality_agents])

        if any(word in content_lower for word in ["orchestrat", "coordinat", "manage"]):
            orchestration_agents = await self.agent_registry.get_agents_by_capability("orchestration")
            suggestions.extend([agent.id for agent in orchestration_agents])

        if any(word in content_lower for word in ["document", "readme", "guide"]):
            doc_agents = await self.agent_registry.get_agents_by_capability("documentation")
            suggestions.extend([agent.id for agent in doc_agents])

        if any(word in content_lower for word in ["deploy", "integrat", "production"]):
            integration_agents = await self.agent_registry.get_agents_by_capability("integration")
            suggestions.extend([agent.id for agent in integration_agents])

        if any(word in content_lower for word in ["analyz", "intelligence", "insight"]):
            intelligence_agents = await self.agent_registry.get_agents_by_capability("intelligence")
            suggestions.extend([agent.id for agent in intelligence_agents])

        # Remove duplicates while preserving order
        unique_suggestions = []
        seen = set()
        for agent_id in suggestions:
            if agent_id not in seen:
                unique_suggestions.append(agent_id)
                seen.add(agent_id)

        return unique_suggestions[:5]  # Return top 5 suggestions
