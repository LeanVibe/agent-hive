"""
Cross-Agent Coordination Protocols for Multi-Agent Development.

This module implements communication and coordination protocols between different
agents to ensure synchronized development workflows and quality maintenance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..feedback_loops import FeedbackSignal, FeedbackType, FeedbackPriority, RealTimeFeedbackEngine


class AgentRole(Enum):
    """Roles of agents in the coordination system."""
    ORCHESTRATOR = "orchestrator"
    INTEGRATION = "integration"
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"
    QUALITY = "quality"
    ARCHIVE = "archive"
    PM = "pm"
    INTELLIGENCE = "intelligence"


class CoordinationMessageType(Enum):
    """Types of coordination messages between agents."""
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    QUALITY_GATE_REQUEST = "quality_gate_request"
    QUALITY_GATE_RESPONSE = "quality_gate_response"
    DEPENDENCY_NOTIFICATION = "dependency_notification"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_ALLOCATION = "resource_allocation"
    ESCALATION = "escalation"
    COMPLETION_NOTIFICATION = "completion_notification"
    COORDINATION_ALERT = "coordination_alert"
    WORKFLOW_SYNC = "workflow_sync"


class MessagePriority(Enum):
    """Priority levels for coordination messages."""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class CoordinationMessage:
    """Message for inter-agent coordination."""
    id: str
    type: CoordinationMessageType
    priority: MessagePriority
    sender: AgentRole
    recipient: AgentRole
    subject: str
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    expires_at: Optional[datetime] = None
    requires_response: bool = False
    response_timeout: Optional[timedelta] = None
    delivered: bool = False
    processed: bool = False
    response: Optional[Dict[str, Any]] = None


@dataclass
class CoordinationProtocol:
    """Protocol definition for agent coordination."""
    id: str
    name: str
    description: str
    participating_agents: List[AgentRole]
    message_flow: List[Dict[str, Any]]
    quality_gates: List[str]
    success_criteria: List[str]
    failure_conditions: List[str]
    timeout_handling: Dict[str, Any]
    escalation_procedures: List[str]


@dataclass
class AgentCapability:
    """Capability definition for an agent."""
    agent_role: AgentRole
    capabilities: List[str]
    capacity: int  # Max concurrent tasks
    availability: float  # 0.0 to 1.0
    specializations: List[str]
    quality_standards: Dict[str, Any]
    response_time_sla: timedelta
    escalation_threshold: int


class CrossAgentCoordinator:
    """Coordinator for cross-agent communication and workflows."""

    def __init__(self, feedback_engine: Optional[RealTimeFeedbackEngine] = None):
        self.logger = logging.getLogger(__name__)
        self.feedback_engine = feedback_engine

        # Message handling
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[CoordinationMessageType, Callable] = {}
        self.pending_messages: Dict[str, CoordinationMessage] = {}
        self.message_history: List[CoordinationMessage] = []

        # Agent management
        self.registered_agents: Dict[AgentRole, AgentCapability] = {}
        self.agent_status: Dict[AgentRole, Dict[str, Any]] = {}
        self.agent_workloads: Dict[AgentRole, int] = {}

        # Coordination protocols
        self.active_protocols: Dict[str, CoordinationProtocol] = {}
        self.protocol_instances: Dict[str, Dict[str, Any]] = {}

        # Workflow synchronization
        self.sync_points: Dict[str, Dict[str, Any]] = {}
        self.dependency_graph: Dict[str, List[str]] = {}

        # Performance tracking
        self.coordination_metrics: Dict[str, float] = {
            "average_response_time": 0.0,
            "message_delivery_rate": 1.0,
            "protocol_success_rate": 1.0,
            "agent_utilization": 0.0
        }

        # Initialize message handlers
        self._initialize_message_handlers()

        # Initialize coordination protocols
        self._initialize_coordination_protocols()

        self.logger.info("CrossAgentCoordinator initialized")

    def _initialize_message_handlers(self) -> None:
        """Initialize message type handlers."""
        self.message_handlers = {
            CoordinationMessageType.TASK_ASSIGNMENT: self._handle_task_assignment,
            CoordinationMessageType.STATUS_UPDATE: self._handle_status_update,
            CoordinationMessageType.QUALITY_GATE_REQUEST: self._handle_quality_gate_request,
            CoordinationMessageType.QUALITY_GATE_RESPONSE: self._handle_quality_gate_response,
            CoordinationMessageType.DEPENDENCY_NOTIFICATION: self._handle_dependency_notification,
            CoordinationMessageType.RESOURCE_REQUEST: self._handle_resource_request,
            CoordinationMessageType.RESOURCE_ALLOCATION: self._handle_resource_allocation,
            CoordinationMessageType.ESCALATION: self._handle_escalation,
            CoordinationMessageType.COMPLETION_NOTIFICATION: self._handle_completion_notification,
            CoordinationMessageType.COORDINATION_ALERT: self._handle_coordination_alert,
            CoordinationMessageType.WORKFLOW_SYNC: self._handle_workflow_sync
        }

    def _initialize_coordination_protocols(self) -> None:
        """Initialize standard coordination protocols."""

        # PR Breakdown Protocol
        pr_breakdown_protocol = CoordinationProtocol(
            id="pr_breakdown",
            name="PR Breakdown Coordination Protocol",
            description="Protocol for coordinating large PR breakdowns across agents",
            participating_agents=[AgentRole.ORCHESTRATOR, AgentRole.INTEGRATION, AgentRole.QUALITY],
            message_flow=[
                {"step": 1, "sender": "orchestrator", "recipient": "integration", "type": "task_assignment"},
                {"step": 2, "sender": "integration", "recipient": "orchestrator", "type": "status_update"},
                {"step": 3, "sender": "orchestrator", "recipient": "quality", "type": "quality_gate_request"},
                {"step": 4, "sender": "quality", "recipient": "orchestrator", "type": "quality_gate_response"},
                {"step": 5, "sender": "orchestrator", "recipient": "integration", "type": "completion_notification"}
            ],
            quality_gates=["code_quality", "test_coverage", "documentation"],
            success_criteria=[
                "All components within size limits",
                "Quality gates passed",
                "Documentation complete",
                "Tests passing"
            ],
            failure_conditions=[
                "Component exceeds size limit",
                "Quality gate failure",
                "Missing documentation",
                "Test failures"
            ],
            timeout_handling={
                "task_assignment": 3600,  # 1 hour
                "status_update": 1800,    # 30 minutes
                "quality_gate": 7200      # 2 hours
            },
            escalation_procedures=[
                "Notify PM agent if delays exceed 4 hours",
                "Escalate to human if quality gates fail repeatedly",
                "Alert all agents if protocol timeout"
            ]
        )

        self.active_protocols[pr_breakdown_protocol.id] = pr_breakdown_protocol

        # Quality Gate Protocol
        quality_gate_protocol = CoordinationProtocol(
            id="quality_gate",
            name="Quality Gate Validation Protocol",
            description="Protocol for coordinating quality gate validations",
            participating_agents=[AgentRole.ORCHESTRATOR, AgentRole.QUALITY, AgentRole.INTEGRATION],
            message_flow=[
                {"step": 1, "sender": "orchestrator", "recipient": "quality", "type": "quality_gate_request"},
                {"step": 2, "sender": "quality", "recipient": "integration", "type": "dependency_notification"},
                {"step": 3, "sender": "integration", "recipient": "quality", "type": "status_update"},
                {"step": 4, "sender": "quality", "recipient": "orchestrator", "type": "quality_gate_response"}
            ],
            quality_gates=["automated_tests", "manual_review", "integration_tests"],
            success_criteria=[
                "All automated tests pass",
                "Manual review approved",
                "Integration tests successful"
            ],
            failure_conditions=[
                "Automated test failures",
                "Manual review rejection",
                "Integration test failures"
            ],
            timeout_handling={
                "quality_gate_request": 1800,
                "manual_review": 7200,
                "integration_tests": 3600
            },
            escalation_procedures=[
                "Notify orchestrator if quality gate fails",
                "Escalate to PM if repeated failures",
                "Alert team if critical quality issue"
            ]
        )

        self.active_protocols[quality_gate_protocol.id] = quality_gate_protocol

    def register_agent(self, agent_role: AgentRole, capability: AgentCapability) -> None:
        """Register an agent with the coordination system."""
        self.registered_agents[agent_role] = capability
        self.agent_status[agent_role] = {
            "status": "active",
            "last_seen": datetime.now(),
            "current_tasks": 0,
            "health_score": 1.0
        }
        self.agent_workloads[agent_role] = 0

        self.logger.info(f"Registered agent: {agent_role.value} with capacity {capability.capacity}")

    async def send_message(self, message: CoordinationMessage) -> bool:
        """Send a coordination message to an agent."""
        # Validate recipient
        if message.recipient not in self.registered_agents:
            self.logger.error(f"Unknown recipient: {message.recipient}")
            return False

        # Check agent availability
        if not self._is_agent_available(message.recipient):
            self.logger.warning(f"Agent {message.recipient} is not available")
            # Queue for later delivery if not urgent
            if message.priority != MessagePriority.URGENT:
                await self.message_queue.put(message)
                return True
            return False

        # Set expiration if not set
        if message.expires_at is None:
            message.expires_at = datetime.now() + timedelta(hours=1)

        # Store in pending messages if response required
        if message.requires_response:
            self.pending_messages[message.id] = message

        # Queue for processing
        await self.message_queue.put(message)

        # Track message
        self.message_history.append(message)

        # Generate feedback signal if feedback engine available
        if self.feedback_engine:
            feedback_signal = FeedbackSignal(
                id=f"coordination_message_{message.id}",
                type=FeedbackType.COORDINATION_FEEDBACK,
                priority=FeedbackPriority.MEDIUM,
                source=message.sender.value,
                timestamp=datetime.now(),
                data={
                    "message_type": message.type.value,
                    "recipient": message.recipient.value,
                    "coordination_efficiency": self._calculate_coordination_efficiency()
                }
            )
            await self.feedback_engine.submit_feedback(feedback_signal)

        return True

    async def start_protocol(self, protocol_id: str, context: Dict[str, Any]) -> str:
        """Start a coordination protocol instance."""
        if protocol_id not in self.active_protocols:
            raise ValueError(f"Unknown protocol: {protocol_id}")

        protocol = self.active_protocols[protocol_id]
        instance_id = f"{protocol_id}_{uuid.uuid4().hex[:8]}"

        # Create protocol instance
        instance = {
            "id": instance_id,
            "protocol_id": protocol_id,
            "context": context,
            "status": "initiated",
            "current_step": 0,
            "started_at": datetime.now(),
            "participants": {role: "pending" for role in protocol.participating_agents},
            "messages": [],
            "quality_gates": {gate: "pending" for gate in protocol.quality_gates},
            "escalations": []
        }

        self.protocol_instances[instance_id] = instance

        # Start protocol execution
        await self._execute_protocol_step(instance_id)

        self.logger.info(f"Started protocol instance: {instance_id}")
        return instance_id

    async def _execute_protocol_step(self, instance_id: str) -> None:
        """Execute the next step in a protocol instance."""
        instance = self.protocol_instances[instance_id]
        protocol = self.active_protocols[instance["protocol_id"]]

        current_step = instance["current_step"]

        if current_step >= len(protocol.message_flow):
            # Protocol completed
            instance["status"] = "completed"
            instance["completed_at"] = datetime.now()
            self.logger.info(f"Protocol instance completed: {instance_id}")
            return

        # Get next message to send
        message_spec = protocol.message_flow[current_step]

        # Create and send message
        message = CoordinationMessage(
            id=f"{instance_id}_step_{current_step}",
            type=CoordinationMessageType(message_spec["type"]),
            priority=MessagePriority.HIGH,
            sender=AgentRole(message_spec["sender"]),
            recipient=AgentRole(message_spec["recipient"]),
            subject=f"Protocol {protocol.name} - Step {current_step + 1}",
            content={
                "protocol_id": protocol.id,
                "instance_id": instance_id,
                "step": current_step,
                "context": instance["context"]
            },
            correlation_id=instance_id,
            requires_response=True,
            response_timeout=timedelta(seconds=protocol.timeout_handling.get(message_spec["type"], 3600))
        )

        # Send message
        success = await self.send_message(message)

        if success:
            instance["messages"].append(message.id)
            instance["current_step"] += 1

            # Set timeout for response
            asyncio.create_task(self._handle_protocol_timeout(instance_id, message.id))
        else:
            # Handle send failure
            await self._handle_protocol_failure(instance_id, f"Failed to send message at step {current_step}")

    async def _handle_protocol_timeout(self, instance_id: str, message_id: str) -> None:
        """Handle protocol message timeout."""
        instance = self.protocol_instances.get(instance_id)
        if not instance or instance["status"] != "active":
            return

        message = self.pending_messages.get(message_id)
        if not message:
            return

        # Wait for response timeout
        if message.response_timeout:
            await asyncio.sleep(message.response_timeout.total_seconds())

        # Check if response received
        if message.processed:
            return

        # Handle timeout
        protocol = self.active_protocols[instance["protocol_id"]]

        # Execute escalation procedures
        for escalation in protocol.escalation_procedures:
            await self._execute_escalation(instance_id, escalation, f"Timeout for message {message_id}")

        # Mark instance as failed
        await self._handle_protocol_failure(instance_id, f"Timeout waiting for response to {message_id}")

    async def _handle_protocol_failure(self, instance_id: str, reason: str) -> None:
        """Handle protocol instance failure."""
        instance = self.protocol_instances[instance_id]
        instance["status"] = "failed"
        instance["failed_at"] = datetime.now()
        instance["failure_reason"] = reason

        # Notify participants
        protocol = self.active_protocols[instance["protocol_id"]]
        for agent_role in protocol.participating_agents:
            failure_message = CoordinationMessage(
                id=f"{instance_id}_failure_{uuid.uuid4().hex[:8]}",
                type=CoordinationMessageType.ESCALATION,
                priority=MessagePriority.URGENT,
                sender=AgentRole.ORCHESTRATOR,
                recipient=agent_role,
                subject=f"Protocol Failure: {protocol.name}",
                content={
                    "protocol_id": protocol.id,
                    "instance_id": instance_id,
                    "failure_reason": reason,
                    "timestamp": datetime.now().isoformat()
                }
            )
            await self.send_message(failure_message)

        self.logger.error(f"Protocol instance failed: {instance_id} - {reason}")

    async def _execute_escalation(self, instance_id: str, escalation_procedure: str, context: str) -> None:
        """Execute escalation procedure."""
        instance = self.protocol_instances[instance_id]

        escalation_record = {
            "procedure": escalation_procedure,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        instance["escalations"].append(escalation_record)

        # Parse escalation procedure and execute
        if "notify pm" in escalation_procedure.lower():
            if AgentRole.PM in self.registered_agents:
                escalation_message = CoordinationMessage(
                    id=f"{instance_id}_escalation_{uuid.uuid4().hex[:8]}",
                    type=CoordinationMessageType.ESCALATION,
                    priority=MessagePriority.URGENT,
                    sender=AgentRole.ORCHESTRATOR,
                    recipient=AgentRole.PM,
                    subject=f"Escalation: {escalation_procedure}",
                    content={
                        "instance_id": instance_id,
                        "escalation_procedure": escalation_procedure,
                        "context": context
                    }
                )
                await self.send_message(escalation_message)

        elif "alert all agents" in escalation_procedure.lower():
            for agent_role in self.registered_agents:
                alert_message = CoordinationMessage(
                    id=f"{instance_id}_alert_{agent_role.value}_{uuid.uuid4().hex[:8]}",
                    type=CoordinationMessageType.COORDINATION_ALERT,
                    priority=MessagePriority.HIGH,
                    sender=AgentRole.ORCHESTRATOR,
                    recipient=agent_role,
                    subject=f"Coordination Alert: {escalation_procedure}",
                    content={
                        "instance_id": instance_id,
                        "alert_type": "protocol_escalation",
                        "context": context
                    }
                )
                await self.send_message(alert_message)

        self.logger.warning(f"Escalation executed: {escalation_procedure} for {instance_id}")

    def _is_agent_available(self, agent_role: AgentRole) -> bool:
        """Check if an agent is available for coordination."""
        if agent_role not in self.agent_status:
            return False

        status = self.agent_status[agent_role]

        # Check if agent is active
        if status["status"] != "active":
            return False

        # Check if agent is responsive (last seen within 5 minutes)
        if datetime.now() - status["last_seen"] > timedelta(minutes=5):
            return False

        # Check agent capacity
        capability = self.registered_agents[agent_role]
        current_workload = self.agent_workloads[agent_role]

        if current_workload >= capability.capacity:
            return False

        return True

    def _calculate_coordination_efficiency(self) -> float:
        """Calculate current coordination efficiency."""
        if not self.message_history:
            return 1.0

        # Calculate based on response times and success rates
        recent_messages = [m for m in self.message_history if m.timestamp > datetime.now() - timedelta(hours=1)]

        if not recent_messages:
            return 1.0

        # Calculate response time efficiency
        response_times = []
        for message in recent_messages:
            if message.processed and message.requires_response:
                # This would need to be tracked properly
                response_times.append(1.0)  # Placeholder

        avg_response_efficiency = sum(response_times) / len(response_times) if response_times else 1.0

        # Calculate delivery success rate
        delivery_success = len([m for m in recent_messages if m.delivered]) / len(recent_messages)

        # Overall efficiency
        efficiency = (avg_response_efficiency + delivery_success) / 2

        return min(1.0, max(0.0, efficiency))

    # Message handlers
    async def _handle_task_assignment(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle task assignment message."""
        self.logger.info(f"Handling task assignment: {message.subject}")

        # Update agent workload
        self.agent_workloads[message.recipient] += 1

        # Update agent status
        self.agent_status[message.recipient]["current_tasks"] += 1

        return {
            "status": "accepted",
            "assigned_to": message.recipient.value,
            "estimated_completion": (datetime.now() + timedelta(hours=2)).isoformat()
        }

    async def _handle_status_update(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle status update message."""
        self.logger.info(f"Handling status update: {message.subject}")

        # Update agent status
        status_data = message.content.get("status", {})
        if message.sender in self.agent_status:
            self.agent_status[message.sender].update(status_data)
            self.agent_status[message.sender]["last_seen"] = datetime.now()

        return {"status": "acknowledged"}

    async def _handle_quality_gate_request(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle quality gate request message."""
        self.logger.info(f"Handling quality gate request: {message.subject}")

        # This would integrate with actual quality gate validation
        # For now, simulate the process
        gate_type = message.content.get("gate_type", "unknown")

        return {
            "status": "initiated",
            "gate_type": gate_type,
            "estimated_completion": (datetime.now() + timedelta(hours=1)).isoformat()
        }

    async def _handle_quality_gate_response(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle quality gate response message."""
        self.logger.info(f"Handling quality gate response: {message.subject}")

        gate_result = message.content.get("result", "unknown")

        # Update protocol instance if applicable
        protocol_id = message.content.get("protocol_id")
        instance_id = message.content.get("instance_id")

        if instance_id and instance_id in self.protocol_instances:
            instance = self.protocol_instances[instance_id]
            gate_type = message.content.get("gate_type", "unknown")
            instance["quality_gates"][gate_type] = gate_result

            # Continue protocol if gate passed
            if gate_result == "passed":
                await self._execute_protocol_step(instance_id)

        return {"status": "processed", "result": gate_result}

    async def _handle_dependency_notification(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle dependency notification message."""
        self.logger.info(f"Handling dependency notification: {message.subject}")

        dependency_info = message.content.get("dependency", {})

        return {"status": "acknowledged", "dependency": dependency_info}

    async def _handle_resource_request(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle resource request message."""
        self.logger.info(f"Handling resource request: {message.subject}")

        resource_type = message.content.get("resource_type")
        amount = message.content.get("amount", 1)

        # Simple resource allocation logic
        allocated = min(amount, 5)  # Max 5 resources

        return {
            "status": "allocated",
            "resource_type": resource_type,
            "allocated_amount": allocated,
            "allocation_id": f"alloc_{uuid.uuid4().hex[:8]}"
        }

    async def _handle_resource_allocation(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle resource allocation message."""
        self.logger.info(f"Handling resource allocation: {message.subject}")

        allocation_id = message.content.get("allocation_id")

        return {"status": "acknowledged", "allocation_id": allocation_id}

    async def _handle_escalation(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle escalation message."""
        self.logger.warning(f"Handling escalation: {message.subject}")

        escalation_type = message.content.get("escalation_type", "unknown")

        return {
            "status": "escalated",
            "escalation_type": escalation_type,
            "escalation_id": f"esc_{uuid.uuid4().hex[:8]}"
        }

    async def _handle_completion_notification(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle completion notification message."""
        self.logger.info(f"Handling completion notification: {message.subject}")

        # Update agent workload
        if message.sender in self.agent_workloads:
            self.agent_workloads[message.sender] = max(0, self.agent_workloads[message.sender] - 1)

        # Update agent status
        if message.sender in self.agent_status:
            self.agent_status[message.sender]["current_tasks"] = max(0, self.agent_status[message.sender]["current_tasks"] - 1)

        return {"status": "acknowledged"}

    async def _handle_coordination_alert(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle coordination alert message."""
        self.logger.warning(f"Handling coordination alert: {message.subject}")

        alert_type = message.content.get("alert_type", "unknown")

        return {
            "status": "alert_processed",
            "alert_type": alert_type,
            "response_actions": ["acknowledged", "monitoring"]
        }

    async def _handle_workflow_sync(self, message: CoordinationMessage) -> Dict[str, Any]:
        """Handle workflow synchronization message."""
        self.logger.info(f"Handling workflow sync: {message.subject}")

        sync_point = message.content.get("sync_point")

        return {
            "status": "synchronized",
            "sync_point": sync_point,
            "timestamp": datetime.now().isoformat()
        }

    def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination system status."""
        return {
            "registered_agents": len(self.registered_agents),
            "active_protocols": len([p for p in self.protocol_instances.values() if p["status"] == "active"]),
            "pending_messages": len(self.pending_messages),
            "message_queue_size": self.message_queue.qsize(),
            "coordination_metrics": self.coordination_metrics,
            "agent_status": {
                agent.value: {
                    "status": status["status"],
                    "workload": self.agent_workloads.get(agent, 0),
                    "capacity": self.registered_agents[agent].capacity,
                    "utilization": self.agent_workloads.get(agent, 0) / self.registered_agents[agent].capacity
                }
                for agent, status in self.agent_status.items()
            }
        }
