"""
Agent Coordination Protocols - Advanced Communication and Coordination

This module implements sophisticated protocols for agent communication,
coordination, and collaborative decision-making in the Agent Hive.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in agent communication."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"
    STATUS_UPDATE = "status_update"
    CAPABILITY_ANNOUNCEMENT = "capability_announcement"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_RESPONSE = "resource_response"
    COLLABORATION_INVITE = "collaboration_invite"
    COLLABORATION_ACCEPT = "collaboration_accept"
    COLLABORATION_DECLINE = "collaboration_decline"
    HEARTBEAT = "heartbeat"
    EMERGENCY = "emergency"


class Priority(Enum):
    """Message priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class CoordinationStrategy(Enum):
    """Coordination strategies for agent collaboration."""
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    CONSENSUS = "consensus"
    AUCTION = "auction"
    NEGOTIATION = "negotiation"
    VOTING = "voting"


@dataclass
class AgentMessage:
    """Represents a message between agents."""

    message_id: str
    sender_id: str
    recipient_id: str
    message_type: MessageType
    priority: Priority
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    requires_response: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'message_id': self.message_id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'message_type': self.message_type.value,
            'priority': self.priority.value,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'correlation_id': self.correlation_id,
            'requires_response': self.requires_response,
            'metadata': self.metadata
        }


@dataclass
class CoordinationSession:
    """Represents a coordination session between agents."""

    session_id: str
    participants: Set[str]
    coordinator_id: str
    strategy: CoordinationStrategy
    objective: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = "active"
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[AgentMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            'session_id': self.session_id,
            'participants': list(self.participants),
            'coordinator_id': self.coordinator_id,
            'strategy': self.strategy.value,
            'objective': self.objective,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'decisions': self.decisions,
            'message_count': len(self.messages),
            'metadata': self.metadata
        }


@dataclass
class AgentCapability:
    """Represents an agent's capability."""

    capability_id: str
    name: str
    description: str
    performance_score: float
    resource_requirements: Dict[str, Any]
    availability: float
    specializations: List[str]
    constraints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert capability to dictionary."""
        return {
            'capability_id': self.capability_id,
            'name': self.name,
            'description': self.description,
            'performance_score': self.performance_score,
            'resource_requirements': self.resource_requirements,
            'availability': self.availability,
            'specializations': self.specializations,
            'constraints': self.constraints
        }


@dataclass
class CollaborationProposal:
    """Represents a collaboration proposal between agents."""

    proposal_id: str
    initiator_id: str
    participants: Set[str]
    objective: str
    strategy: CoordinationStrategy
    resource_allocation: Dict[str, Any]
    timeline: Dict[str, Any]
    expected_outcome: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"
    responses: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert proposal to dictionary."""
        return {
            'proposal_id': self.proposal_id,
            'initiator_id': self.initiator_id,
            'participants': list(self.participants),
            'objective': self.objective,
            'strategy': self.strategy.value,
            'resource_allocation': self.resource_allocation,
            'timeline': self.timeline,
            'expected_outcome': self.expected_outcome,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'responses': self.responses
        }


class AgentCoordinationProtocols:
    """
    Advanced agent coordination protocols for intelligent collaboration.

    This class implements sophisticated coordination mechanisms that enable
    agents to communicate, collaborate, and make collective decisions.
    """

    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize coordination protocols for an agent."""
        self.agent_id = agent_id
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")

        # Communication infrastructure
        self.message_queue: deque = deque()
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.message_handlers: Dict[MessageType, Any] = {}

        # Coordination state
        self.active_sessions: Dict[str, CoordinationSession] = {}
        self.capabilities: Dict[str, AgentCapability] = {}
        self.collaboration_proposals: Dict[str, CollaborationProposal] = {}

        # Peer management
        self.known_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_capabilities: Dict[str, Dict[str, AgentCapability]] = {}
        self.trust_scores: Dict[str, float] = {}

        # Performance tracking
        self.coordination_metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'sessions_coordinated': 0,
            'successful_collaborations': 0,
            'failed_collaborations': 0,
            'average_response_time': 0.0
        }

        # Initialize message handlers
        self._initialize_message_handlers()

        # Communication channels
        self.communication_channels: Dict[str, asyncio.Queue] = {}

        self.logger.info(f"Agent coordination protocols initialized for {agent_id}")

    def _initialize_message_handlers(self) -> None:
        """Initialize message handlers for different message types."""
        self.message_handlers = {
            MessageType.TASK_REQUEST: self._handle_task_request,
            MessageType.TASK_RESPONSE: self._handle_task_response,
            MessageType.COORDINATION_REQUEST: self._handle_coordination_request,
            MessageType.COORDINATION_RESPONSE: self._handle_coordination_response,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.CAPABILITY_ANNOUNCEMENT: self._handle_capability_announcement,
            MessageType.RESOURCE_REQUEST: self._handle_resource_request,
            MessageType.RESOURCE_RESPONSE: self._handle_resource_response,
            MessageType.COLLABORATION_INVITE: self._handle_collaboration_invite,
            MessageType.COLLABORATION_ACCEPT: self._handle_collaboration_accept,
            MessageType.COLLABORATION_DECLINE: self._handle_collaboration_decline,
            MessageType.HEARTBEAT: self._handle_heartbeat,
            MessageType.EMERGENCY: self._handle_emergency
        }

    async def send_message(
        self,
        recipient_id: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: Priority = Priority.MEDIUM,
        requires_response: bool = False,
        timeout: float = 30.0
    ) -> Optional[AgentMessage]:
        """
        Send a message to another agent.

        Args:
            recipient_id: ID of the recipient agent
            message_type: Type of message to send
            content: Message content
            priority: Message priority
            requires_response: Whether a response is required
            timeout: Timeout for response (if required)

        Returns:
            Response message if requires_response is True, None otherwise
        """
        message_id = str(uuid.uuid4())

        # Create message
        message = AgentMessage(
            message_id=message_id,
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=message_type,
            priority=priority,
            content=content,
            requires_response=requires_response,
            expires_at=datetime.now() + timedelta(seconds=timeout) if requires_response else None
        )

        # Send message
        await self._deliver_message(message)

        # Update metrics
        self.coordination_metrics['messages_sent'] += 1

        # Wait for response if required
        if requires_response:
            future = asyncio.Future()
            self.pending_responses[message_id] = future

            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                self.logger.warning(f"Message {message_id} to {recipient_id} timed out")
                self.pending_responses.pop(message_id, None)
                return None
            except Exception as e:
                self.logger.error(f"Error waiting for response to {message_id}: {e}")
                self.pending_responses.pop(message_id, None)
                return None

        return None

    async def broadcast_message(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: Priority = Priority.MEDIUM,
        exclude_agents: Optional[Set[str]] = None
    ) -> None:
        """
        Broadcast a message to all known agents.

        Args:
            message_type: Type of message to broadcast
            content: Message content
            priority: Message priority
            exclude_agents: Agents to exclude from broadcast
        """
        exclude_agents = exclude_agents or set()

        # Send to all known agents except excluded ones
        for agent_id in self.known_agents:
            if agent_id not in exclude_agents and agent_id != self.agent_id:
                await self.send_message(
                    agent_id, message_type, content, priority, requires_response=False
                )

    async def initiate_coordination_session(
        self,
        participants: Set[str],
        objective: str,
        strategy: CoordinationStrategy = CoordinationStrategy.PEER_TO_PEER,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CoordinationSession:
        """
        Initiate a coordination session with other agents.

        Args:
            participants: Set of agent IDs to include in session
            objective: Objective of the coordination session
            strategy: Coordination strategy to use
            metadata: Additional metadata for the session

        Returns:
            CoordinationSession: The created coordination session
        """
        session_id = str(uuid.uuid4())

        # Create coordination session
        session = CoordinationSession(
            session_id=session_id,
            participants=participants | {self.agent_id},  # Include self
            coordinator_id=self.agent_id,
            strategy=strategy,
            objective=objective,
            metadata=metadata or {}
        )

        # Store session
        self.active_sessions[session_id] = session

        # Send coordination requests to participants
        for participant_id in participants:
            await self.send_message(
                participant_id,
                MessageType.COORDINATION_REQUEST,
                {
                    'session_id': session_id,
                    'objective': objective,
                    'strategy': strategy.value,
                    'coordinator_id': self.agent_id,
                    'participants': list(participants)
                },
                priority=Priority.HIGH,
                requires_response=True
            )

        # Update metrics
        self.coordination_metrics['sessions_coordinated'] += 1

        self.logger.info(f"Initiated coordination session {session_id} with {len(participants)} participants")
        return session

    async def propose_collaboration(
        self,
        participants: Set[str],
        objective: str,
        strategy: CoordinationStrategy,
        resource_allocation: Dict[str, Any],
        timeline: Dict[str, Any],
        expected_outcome: Dict[str, Any]
    ) -> CollaborationProposal:
        """
        Propose a collaboration to other agents.

        Args:
            participants: Set of agent IDs to collaborate with
            objective: Collaboration objective
            strategy: Coordination strategy
            resource_allocation: Resource allocation plan
            timeline: Timeline for collaboration
            expected_outcome: Expected outcomes

        Returns:
            CollaborationProposal: The created collaboration proposal
        """
        proposal_id = str(uuid.uuid4())

        # Create collaboration proposal
        proposal = CollaborationProposal(
            proposal_id=proposal_id,
            initiator_id=self.agent_id,
            participants=participants,
            objective=objective,
            strategy=strategy,
            resource_allocation=resource_allocation,
            timeline=timeline,
            expected_outcome=expected_outcome
        )

        # Store proposal
        self.collaboration_proposals[proposal_id] = proposal

        # Send collaboration invites
        for participant_id in participants:
            await self.send_message(
                participant_id,
                MessageType.COLLABORATION_INVITE,
                {
                    'proposal_id': proposal_id,
                    'objective': objective,
                    'strategy': strategy.value,
                    'resource_allocation': resource_allocation,
                    'timeline': timeline,
                    'expected_outcome': expected_outcome
                },
                priority=Priority.HIGH,
                requires_response=True
            )

        self.logger.info(f"Proposed collaboration {proposal_id} to {len(participants)} agents")
        return proposal

    async def register_capability(
        self,
        name: str,
        description: str,
        performance_score: float,
        resource_requirements: Dict[str, Any],
        availability: float = 1.0,
        specializations: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> AgentCapability:
        """
        Register a capability for this agent.

        Args:
            name: Capability name
            description: Capability description
            performance_score: Performance score (0-1)
            resource_requirements: Resource requirements
            availability: Availability (0-1)
            specializations: List of specializations
            constraints: Capability constraints

        Returns:
            AgentCapability: The registered capability
        """
        capability_id = str(uuid.uuid4())

        capability = AgentCapability(
            capability_id=capability_id,
            name=name,
            description=description,
            performance_score=performance_score,
            resource_requirements=resource_requirements,
            availability=availability,
            specializations=specializations or [],
            constraints=constraints or {}
        )

        # Store capability
        self.capabilities[capability_id] = capability

        # Announce capability to other agents
        await self.broadcast_message(
            MessageType.CAPABILITY_ANNOUNCEMENT,
            {
                'capability': capability.to_dict()
            },
            priority=Priority.MEDIUM
        )

        self.logger.info(f"Registered capability: {name}")
        return capability

    async def find_agents_with_capability(
        self,
        capability_name: str,
        min_performance: float = 0.5,
        min_availability: float = 0.5
    ) -> List[Tuple[str, AgentCapability]]:
        """
        Find agents with a specific capability.

        Args:
            capability_name: Name of the capability to search for
            min_performance: Minimum performance score
            min_availability: Minimum availability

        Returns:
            List of (agent_id, capability) tuples
        """
        matching_agents = []

        for agent_id, capabilities in self.agent_capabilities.items():
            for capability in capabilities.values():
                if (capability.name == capability_name and
                    capability.performance_score >= min_performance and
                    capability.availability >= min_availability):
                    matching_agents.append((agent_id, capability))

        # Sort by performance score (descending)
        matching_agents.sort(key=lambda x: x[1].performance_score, reverse=True)

        return matching_agents

    async def negotiate_resource_allocation(
        self,
        session_id: str,
        resource_requirements: Dict[str, Any],
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Negotiate resource allocation with other agents in a session.

        Args:
            session_id: ID of the coordination session
            resource_requirements: Required resources
            max_iterations: Maximum negotiation iterations

        Returns:
            Dict containing negotiated resource allocation
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        # Initial resource allocation proposal
        allocation_proposal = {
            'requester': self.agent_id,
            'resources': resource_requirements,
            'priority': Priority.MEDIUM.value,
            'deadline': (datetime.now() + timedelta(hours=1)).isoformat()
        }

        # Send resource requests to participants
        responses = []
        for participant_id in session.participants:
            if participant_id != self.agent_id:
                response = await self.send_message(
                    participant_id,
                    MessageType.RESOURCE_REQUEST,
                    allocation_proposal,
                    priority=Priority.HIGH,
                    requires_response=True
                )
                if response:
                    responses.append(response)

        # Process responses and negotiate
        negotiated_allocation = await self._process_resource_negotiation(
            session_id, allocation_proposal, responses, max_iterations
        )

        return negotiated_allocation

    async def vote_on_decision(
        self,
        session_id: str,
        decision_options: List[Dict[str, Any]],
        voting_method: str = "majority"
    ) -> Dict[str, Any]:
        """
        Conduct a vote on a decision within a coordination session.

        Args:
            session_id: ID of the coordination session
            decision_options: List of options to vote on
            voting_method: Voting method ("majority", "consensus", "weighted")

        Returns:
            Dict containing voting results and chosen option
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        # Send voting request to participants
        voting_request = {
            'session_id': session_id,
            'options': decision_options,
            'voting_method': voting_method,
            'deadline': (datetime.now() + timedelta(minutes=30)).isoformat()
        }

        votes = []
        for participant_id in session.participants:
            if participant_id != self.agent_id:
                response = await self.send_message(
                    participant_id,
                    MessageType.COORDINATION_REQUEST,
                    voting_request,
                    priority=Priority.HIGH,
                    requires_response=True
                )
                if response and response.content.get('vote'):
                    votes.append(response.content['vote'])

        # Process votes
        voting_results = await self._process_votes(decision_options, votes, voting_method)

        # Store decision in session
        session.decisions.append({
            'decision_type': 'voting',
            'options': decision_options,
            'votes': votes,
            'result': voting_results,
            'timestamp': datetime.now().isoformat()
        })

        return voting_results

    async def consensus_decision(
        self,
        session_id: str,
        proposal: Dict[str, Any],
        max_rounds: int = 5
    ) -> Dict[str, Any]:
        """
        Reach consensus on a decision through iterative discussion.

        Args:
            session_id: ID of the coordination session
            proposal: Initial proposal
            max_rounds: Maximum discussion rounds

        Returns:
            Dict containing consensus result
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]
        current_proposal = proposal.copy()

        for round_num in range(max_rounds):
            # Send current proposal to participants
            consensus_request = {
                'session_id': session_id,
                'proposal': current_proposal,
                'round': round_num + 1,
                'max_rounds': max_rounds
            }

            feedback = []
            for participant_id in session.participants:
                if participant_id != self.agent_id:
                    response = await self.send_message(
                        participant_id,
                        MessageType.COORDINATION_REQUEST,
                        consensus_request,
                        priority=Priority.HIGH,
                        requires_response=True
                    )
                    if response:
                        feedback.append(response.content)

            # Process feedback and update proposal
            consensus_result = await self._process_consensus_feedback(
                current_proposal, feedback, round_num + 1
            )

            if consensus_result['consensus_reached']:
                # Store decision
                session.decisions.append({
                    'decision_type': 'consensus',
                    'initial_proposal': proposal,
                    'final_proposal': consensus_result['proposal'],
                    'rounds': round_num + 1,
                    'timestamp': datetime.now().isoformat()
                })

                return consensus_result

            current_proposal = consensus_result['proposal']

        # Consensus not reached
        return {
            'consensus_reached': False,
            'proposal': current_proposal,
            'rounds': max_rounds,
            'reason': 'Maximum rounds exceeded'
        }

    async def process_messages(self) -> None:
        """Process incoming messages from the message queue."""
        while self.message_queue:
            message = self.message_queue.popleft()

            # Update metrics
            self.coordination_metrics['messages_received'] += 1

            # Check if message has expired
            if message.expires_at and datetime.now() > message.expires_at:
                self.logger.warning(f"Message {message.message_id} expired")
                continue

            # Handle message based on type
            handler = self.message_handlers.get(message.message_type)
            if handler:
                try:
                    await handler(message)
                except Exception as e:
                    self.logger.error(f"Error handling message {message.message_id}: {e}")
            else:
                self.logger.warning(f"No handler for message type {message.message_type}")

    async def _deliver_message(self, message: AgentMessage) -> None:
        """Deliver a message to the recipient agent."""
        # In a real implementation, this would use the actual communication infrastructure
        # For now, we'll simulate by adding to a communication channel

        recipient_id = message.recipient_id
        if recipient_id not in self.communication_channels:
            self.communication_channels[recipient_id] = asyncio.Queue()

        await self.communication_channels[recipient_id].put(message)

    async def _handle_task_request(self, message: AgentMessage) -> None:
        """Handle incoming task request."""
        task_info = message.content

        # Evaluate if we can handle the task
        can_handle = await self._evaluate_task_capability(task_info)

        response_content = {
            'task_id': task_info.get('task_id'),
            'can_handle': can_handle,
            'estimated_time': task_info.get('estimated_time', 0),
            'resource_requirements': task_info.get('resource_requirements', {}),
            'confidence': 0.8 if can_handle else 0.2
        }

        # Send response
        await self.send_message(
            message.sender_id,
            MessageType.TASK_RESPONSE,
            response_content,
            priority=Priority.HIGH
        )

    async def _handle_task_response(self, message: AgentMessage) -> None:
        """Handle task response."""
        # If this is a response to a pending request, complete the future
        if message.correlation_id and message.correlation_id in self.pending_responses:
            future = self.pending_responses.pop(message.correlation_id)
            if not future.done():
                future.set_result(message)

    async def _handle_coordination_request(self, message: AgentMessage) -> None:
        """Handle coordination request."""
        request_info = message.content

        if 'session_id' in request_info:
            # Join coordination session
            session_id = request_info['session_id']
            response = await self._evaluate_coordination_request(request_info)

            await self.send_message(
                message.sender_id,
                MessageType.COORDINATION_RESPONSE,
                response,
                priority=Priority.HIGH
            )

    async def _handle_coordination_response(self, message: AgentMessage) -> None:
        """Handle coordination response."""
        # Complete pending response if exists
        if message.correlation_id and message.correlation_id in self.pending_responses:
            future = self.pending_responses.pop(message.correlation_id)
            if not future.done():
                future.set_result(message)

    async def _handle_status_update(self, message: AgentMessage) -> None:
        """Handle status update from another agent."""
        agent_id = message.sender_id
        status_info = message.content

        # Update known agent information
        self.known_agents[agent_id] = {
            'last_update': datetime.now(),
            'status': status_info
        }

    async def _handle_capability_announcement(self, message: AgentMessage) -> None:
        """Handle capability announcement."""
        agent_id = message.sender_id
        capability_info = message.content.get('capability', {})

        # Store agent capability
        if agent_id not in self.agent_capabilities:
            self.agent_capabilities[agent_id] = {}

        capability = AgentCapability(
            capability_id=capability_info['capability_id'],
            name=capability_info['name'],
            description=capability_info['description'],
            performance_score=capability_info['performance_score'],
            resource_requirements=capability_info['resource_requirements'],
            availability=capability_info['availability'],
            specializations=capability_info['specializations'],
            constraints=capability_info.get('constraints', {})
        )

        self.agent_capabilities[agent_id][capability.capability_id] = capability

        self.logger.info(f"Learned capability {capability.name} from agent {agent_id}")

    async def _handle_resource_request(self, message: AgentMessage) -> None:
        """Handle resource request."""
        resource_info = message.content

        # Evaluate resource request
        can_provide = await self._evaluate_resource_request(resource_info)

        response_content = {
            'request_id': resource_info.get('request_id'),
            'can_provide': can_provide,
            'available_resources': self._get_available_resources(),
            'conditions': self._get_resource_conditions()
        }

        await self.send_message(
            message.sender_id,
            MessageType.RESOURCE_RESPONSE,
            response_content,
            priority=Priority.HIGH
        )

    async def _handle_resource_response(self, message: AgentMessage) -> None:
        """Handle resource response."""
        # Complete pending response if exists
        if message.correlation_id and message.correlation_id in self.pending_responses:
            future = self.pending_responses.pop(message.correlation_id)
            if not future.done():
                future.set_result(message)

    async def _handle_collaboration_invite(self, message: AgentMessage) -> None:
        """Handle collaboration invitation."""
        proposal_info = message.content

        # Evaluate collaboration proposal
        decision = await self._evaluate_collaboration_proposal(proposal_info)

        response_type = (MessageType.COLLABORATION_ACCEPT if decision['accept']
                        else MessageType.COLLABORATION_DECLINE)

        await self.send_message(
            message.sender_id,
            response_type,
            decision,
            priority=Priority.HIGH
        )

    async def _handle_collaboration_accept(self, message: AgentMessage) -> None:
        """Handle collaboration acceptance."""
        proposal_id = message.content.get('proposal_id')
        if proposal_id in self.collaboration_proposals:
            proposal = self.collaboration_proposals[proposal_id]
            proposal.responses[message.sender_id] = 'accepted'

            # Check if all participants have responded
            if len(proposal.responses) == len(proposal.participants):
                await self._finalize_collaboration(proposal)

    async def _handle_collaboration_decline(self, message: AgentMessage) -> None:
        """Handle collaboration decline."""
        proposal_id = message.content.get('proposal_id')
        if proposal_id in self.collaboration_proposals:
            proposal = self.collaboration_proposals[proposal_id]
            proposal.responses[message.sender_id] = 'declined'
            proposal.status = 'declined'

    async def _handle_heartbeat(self, message: AgentMessage) -> None:
        """Handle heartbeat message."""
        agent_id = message.sender_id

        # Update agent's last seen time
        if agent_id in self.known_agents:
            self.known_agents[agent_id]['last_heartbeat'] = datetime.now()
        else:
            self.known_agents[agent_id] = {
                'last_heartbeat': datetime.now(),
                'status': 'active'
            }

    async def _handle_emergency(self, message: AgentMessage) -> None:
        """Handle emergency message."""
        emergency_info = message.content

        self.logger.critical(f"Emergency from {message.sender_id}: {emergency_info}")

        # Broadcast emergency to other agents
        await self.broadcast_message(
            MessageType.EMERGENCY,
            emergency_info,
            priority=Priority.CRITICAL,
            exclude_agents={message.sender_id}
        )

    async def _evaluate_task_capability(self, task_info: Dict[str, Any]) -> bool:
        """Evaluate if this agent can handle a task."""
        # Check if we have capabilities matching the task requirements
        task_type = task_info.get('type')
        required_capabilities = task_info.get('required_capabilities', [])

        for capability in self.capabilities.values():
            if (capability.name == task_type or
                any(spec in required_capabilities for spec in capability.specializations)):
                return capability.availability > 0.5

        return False

    async def _evaluate_coordination_request(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a coordination request."""
        # Simple evaluation - accept if we're not overloaded
        return {
            'accept': len(self.active_sessions) < 5,
            'availability': 0.8,
            'estimated_participation': 'full'
        }

    async def _evaluate_resource_request(self, resource_info: Dict[str, Any]) -> bool:
        """Evaluate if we can provide requested resources."""
        # Simple evaluation - check if we have available resources
        return True  # Placeholder

    async def _evaluate_collaboration_proposal(self, proposal_info: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a collaboration proposal."""
        # Simple evaluation - accept if objective aligns with our capabilities
        return {
            'accept': True,
            'conditions': [],
            'estimated_contribution': 'medium'
        }

    async def _finalize_collaboration(self, proposal: CollaborationProposal) -> None:
        """Finalize a collaboration proposal."""
        # All participants accepted - start collaboration
        session_id = await self.initiate_coordination_session(
            proposal.participants,
            proposal.objective,
            proposal.strategy
        )

        proposal.status = 'active'
        proposal.metadata['session_id'] = session_id

        self.coordination_metrics['successful_collaborations'] += 1

        self.logger.info(f"Collaboration {proposal.proposal_id} started with session {session_id}")

    async def _process_resource_negotiation(
        self,
        session_id: str,
        proposal: Dict[str, Any],
        responses: List[AgentMessage],
        max_iterations: int
    ) -> Dict[str, Any]:
        """Process resource negotiation."""
        # Simple negotiation - aggregate responses
        allocation = {
            'status': 'negotiated',
            'resources': proposal['resources'],
            'providers': [],
            'conditions': []
        }

        for response in responses:
            if response.content.get('can_provide'):
                allocation['providers'].append(response.sender_id)
                allocation['conditions'].extend(response.content.get('conditions', []))

        return allocation

    async def _process_votes(
        self,
        options: List[Dict[str, Any]],
        votes: List[Dict[str, Any]],
        voting_method: str
    ) -> Dict[str, Any]:
        """Process votes and determine outcome."""
        if voting_method == "majority":
            # Simple majority voting
            vote_counts = defaultdict(int)
            for vote in votes:
                option_id = vote.get('option_id')
                if option_id:
                    vote_counts[option_id] += 1

            if vote_counts:
                winner = max(vote_counts, key=vote_counts.get)
                return {
                    'winner': winner,
                    'votes': dict(vote_counts),
                    'total_votes': len(votes)
                }

        return {
            'winner': None,
            'votes': {},
            'total_votes': len(votes)
        }

    async def _process_consensus_feedback(
        self,
        proposal: Dict[str, Any],
        feedback: List[Dict[str, Any]],
        round_num: int
    ) -> Dict[str, Any]:
        """Process consensus feedback."""
        # Simple consensus - check if all feedback is positive
        positive_feedback = sum(1 for f in feedback if f.get('support', False))

        if positive_feedback == len(feedback):
            return {
                'consensus_reached': True,
                'proposal': proposal,
                'round': round_num
            }

        # Modify proposal based on feedback
        modified_proposal = proposal.copy()
        for f in feedback:
            if f.get('suggestions'):
                # Apply suggestions to proposal
                modified_proposal.update(f['suggestions'])

        return {
            'consensus_reached': False,
            'proposal': modified_proposal,
            'round': round_num
        }

    def _get_available_resources(self) -> Dict[str, Any]:
        """Get available resources."""
        return {
            'cpu': 0.5,
            'memory': 0.3,
            'storage': 0.8,
            'network': 0.6
        }

    def _get_resource_conditions(self) -> List[str]:
        """Get conditions for resource sharing."""
        return [
            'max_duration_1hour',
            'priority_medium',
            'return_on_request'
        ]

    def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination status."""
        return {
            'agent_id': self.agent_id,
            'active_sessions': len(self.active_sessions),
            'known_agents': len(self.known_agents),
            'registered_capabilities': len(self.capabilities),
            'pending_responses': len(self.pending_responses),
            'collaboration_proposals': len(self.collaboration_proposals),
            'metrics': self.coordination_metrics,
            'trust_scores': self.trust_scores
        }

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a coordination session."""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        return session.to_dict()

    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired coordination sessions."""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            if session.status == 'active':
                # Check if session has been idle for too long
                if not session.messages or (current_time - session.messages[-1].timestamp).total_seconds() > 3600:
                    expired_sessions.append(session_id)

        for session_id in expired_sessions:
            session = self.active_sessions.pop(session_id)
            session.status = 'expired'
            session.end_time = current_time

            self.logger.info(f"Cleaned up expired session {session_id}")
