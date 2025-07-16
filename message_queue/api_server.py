"""
Communication API Server with REST and WebSocket endpoints.
Provides the interface for agents to send/receive messages.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .models import Message, MessagePriority, Agent, AgentStatus, BroadcastMessage
from .queue_service import MessageQueueService
from .agent_registry import AgentRegistry


logger = logging.getLogger(__name__)


# Pydantic models for API
class MessageRequest(BaseModel):
    recipient: str = Field(..., description="Target agent ID or name")
    content: str = Field(..., description="Message content")
    priority: MessagePriority = Field(MessagePriority.MEDIUM, description="Message priority")
    expires_in_hours: Optional[int] = Field(24, description="Message expiration in hours")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class BroadcastRequest(BaseModel):
    recipients: List[str] = Field(default_factory=list, description="Target agent IDs (empty = all)")
    content: str = Field(..., description="Broadcast content")
    priority: MessagePriority = Field(MessagePriority.MEDIUM, description="Message priority")
    expires_in_hours: Optional[int] = Field(24, description="Message expiration in hours")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class AgentRegistrationRequest(BaseModel):
    name: str = Field(..., description="Agent name")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    endpoint: Optional[str] = Field(None, description="Agent endpoint URL")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    priority: str
    created_at: str
    metadata: Dict


class AgentResponse(BaseModel):
    id: str
    name: str
    status: str
    capabilities: List[str]
    last_seen: str


class WebSocketConnection:
    """Manages WebSocket connections for real-time communication."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.agent_connections: Dict[str, str] = {}  # agent_id -> connection_id
    
    async def connect(self, websocket: WebSocket, agent_id: str) -> str:
        """Connect an agent via WebSocket."""
        await websocket.accept()
        connection_id = f"ws_{agent_id}_{datetime.utcnow().timestamp()}"
        self.connections[connection_id] = websocket
        self.agent_connections[agent_id] = connection_id
        logger.info(f"WebSocket connected for agent {agent_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str, agent_id: str):
        """Disconnect a WebSocket."""
        if connection_id in self.connections:
            del self.connections[connection_id]
        if agent_id in self.agent_connections:
            del self.agent_connections[agent_id]
        logger.info(f"WebSocket disconnected for agent {agent_id}")
    
    async def send_message(self, agent_id: str, message: dict):
        """Send message to agent via WebSocket."""
        if agent_id in self.agent_connections:
            connection_id = self.agent_connections[agent_id]
            if connection_id in self.connections:
                try:
                    websocket = self.connections[connection_id]
                    await websocket.send_json(message)
                    return True
                except Exception as e:
                    logger.error(f"Failed to send WebSocket message to {agent_id}: {e}")
                    await self.disconnect(connection_id, agent_id)
        return False
    
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """Broadcast message to all connected agents."""
        exclude = exclude or set()
        sent_count = 0
        
        for agent_id, connection_id in self.agent_connections.items():
            if agent_id not in exclude:
                if await self.send_message(agent_id, message):
                    sent_count += 1
        
        return sent_count


class CommunicationAPI:
    """Main Communication API class."""
    
    def __init__(self, 
                 queue_service: MessageQueueService,
                 agent_registry: AgentRegistry,
                 host: str = "localhost",
                 port: int = 8080):
        self.queue_service = queue_service
        self.agent_registry = agent_registry
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="Agent Communication API",
            description="Production-grade message queue API for agent communication",
            version="1.0.0"
        )
        self.websocket_manager = WebSocketConnection()
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        
        @self.app.post("/api/v1/messages", response_model=dict)
        async def send_message(message_req: MessageRequest, sender: str = "system"):
            """Send a message to an agent."""
            try:
                # Resolve recipient (could be agent name or ID)
                recipient_agent = await self.agent_registry.get_agent_by_name(message_req.recipient)
                if not recipient_agent:
                    recipient_agent = await self.agent_registry.get_agent(message_req.recipient)
                
                if not recipient_agent:
                    raise HTTPException(status_code=404, detail=f"Agent not found: {message_req.recipient}")
                
                # Create message
                message = Message(
                    sender=sender,
                    recipient=recipient_agent.id,
                    content=message_req.content,
                    priority=message_req.priority,
                    metadata=message_req.metadata
                )
                
                # Set expiration if provided
                if message_req.expires_in_hours:
                    from datetime import timedelta
                    message.expires_at = message.created_at + timedelta(hours=message_req.expires_in_hours)
                
                # Send message
                success = await self.queue_service.send_message(message)
                
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to send message")
                
                # Try to deliver via WebSocket for real-time delivery
                ws_message = {
                    "type": "message",
                    "id": message.id,
                    "sender": message.sender,
                    "content": message.content,
                    "priority": message.priority.value,
                    "created_at": message.created_at.isoformat(),
                    "metadata": message.metadata
                }
                await self.websocket_manager.send_message(recipient_agent.id, ws_message)
                
                return {
                    "message_id": message.id,
                    "status": "sent",
                    "recipient": recipient_agent.name
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/broadcast", response_model=dict)
        async def send_broadcast(broadcast_req: BroadcastRequest, sender: str = "system"):
            """Send a broadcast message to multiple agents."""
            try:
                # Get target agents
                if broadcast_req.recipients:
                    target_agents = []
                    for recipient in broadcast_req.recipients:
                        agent = await self.agent_registry.get_agent_by_name(recipient)
                        if not agent:
                            agent = await self.agent_registry.get_agent(recipient)
                        if agent:
                            target_agents.append(agent)
                else:
                    # Broadcast to all online agents
                    target_agents = await self.agent_registry.list_online_agents()
                
                if not target_agents:
                    raise HTTPException(status_code=404, detail="No target agents found")
                
                # Create broadcast message
                broadcast = BroadcastMessage(
                    sender=sender,
                    recipients=[agent.id for agent in target_agents],
                    content=broadcast_req.content,
                    priority=broadcast_req.priority,
                    metadata=broadcast_req.metadata
                )
                
                # Set expiration if provided
                if broadcast_req.expires_in_hours:
                    from datetime import timedelta
                    broadcast.expires_at = broadcast.created_at + timedelta(hours=broadcast_req.expires_in_hours)
                
                # Send broadcast
                agent_ids = [agent.id for agent in target_agents]
                sent_count = await self.queue_service.send_broadcast(broadcast, agent_ids)
                
                # Send via WebSocket for real-time delivery
                ws_message = {
                    "type": "broadcast",
                    "id": broadcast.id,
                    "sender": broadcast.sender,
                    "content": broadcast.content,
                    "priority": broadcast.priority.value,
                    "created_at": broadcast.created_at.isoformat(),
                    "metadata": broadcast.metadata
                }
                ws_sent = await self.websocket_manager.broadcast(
                    ws_message, 
                    exclude={sender}  # Don't send back to sender
                )
                
                return {
                    "broadcast_id": broadcast.id,
                    "messages_sent": sent_count,
                    "websocket_sent": ws_sent,
                    "target_agents": len(target_agents)
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error sending broadcast: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/messages/{agent_id}", response_model=List[MessageResponse])
        async def get_messages(agent_id: str, limit: int = 10):
            """Get pending messages for an agent."""
            try:
                # Resolve agent ID if name provided
                agent = await self.agent_registry.get_agent_by_name(agent_id)
                if not agent:
                    agent = await self.agent_registry.get_agent(agent_id)
                
                if not agent:
                    raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
                
                messages = await self.queue_service.get_messages_for_agent(agent.id, limit)
                
                return [
                    MessageResponse(
                        id=msg.id,
                        sender=msg.sender,
                        content=msg.content,
                        priority=msg.priority.value,
                        created_at=msg.created_at.isoformat(),
                        metadata=msg.metadata
                    )
                    for msg in messages
                ]
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting messages: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/messages/{message_id}/ack")
        async def acknowledge_message(message_id: str, agent_id: str):
            """Acknowledge message delivery."""
            try:
                success = await self.queue_service.acknowledge_message(message_id, agent_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail="Message not found or already acknowledged")
                
                return {"status": "acknowledged", "message_id": message_id}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error acknowledging message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/agents/register", response_model=dict)
        async def register_agent(agent_req: AgentRegistrationRequest):
            """Register a new agent."""
            try:
                agent = Agent(
                    name=agent_req.name,
                    capabilities=agent_req.capabilities,
                    status=AgentStatus.ONLINE,
                    endpoint=agent_req.endpoint,
                    metadata=agent_req.metadata
                )
                
                success = await self.agent_registry.register_agent(agent)
                
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to register agent")
                
                return {
                    "agent_id": agent.id,
                    "status": "registered",
                    "name": agent.name
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error registering agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/agents", response_model=List[AgentResponse])
        async def list_agents(status: Optional[str] = None):
            """List all registered agents."""
            try:
                status_filter = None
                if status:
                    status_filter = AgentStatus(status)
                
                agents = await self.agent_registry.list_agents(status_filter)
                
                return [
                    AgentResponse(
                        id=agent.id,
                        name=agent.name,
                        status=agent.status.value,
                        capabilities=agent.capabilities,
                        last_seen=agent.last_seen.isoformat()
                    )
                    for agent in agents
                ]
                
            except Exception as e:
                logger.error(f"Error listing agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/agents/{agent_id}/heartbeat")
        async def agent_heartbeat(agent_id: str):
            """Record agent heartbeat."""
            try:
                success = await self.agent_registry.heartbeat(agent_id)
                
                if not success:
                    raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
                
                return {"status": "heartbeat_recorded"}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error recording heartbeat: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/stats")
        async def get_stats():
            """Get system statistics."""
            try:
                queue_stats = await self.queue_service.get_queue_stats()
                registry_stats = await self.agent_registry.get_registry_stats()
                
                return {
                    "queue": {
                        "total_messages": queue_stats.total_messages,
                        "pending_messages": queue_stats.pending_messages,
                        "delivered_messages": queue_stats.delivered_messages,
                        "queue_size": queue_stats.queue_size,
                        "average_delivery_time": queue_stats.average_delivery_time
                    },
                    "agents": registry_stats,
                    "websockets": {
                        "active_connections": len(self.websocket_manager.connections),
                        "agent_connections": len(self.websocket_manager.agent_connections)
                    }
                }
                
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws/{agent_id}")
        async def websocket_endpoint(websocket: WebSocket, agent_id: str):
            """WebSocket endpoint for real-time communication."""
            connection_id = None
            try:
                # Verify agent exists
                agent = await self.agent_registry.get_agent_by_name(agent_id)
                if not agent:
                    agent = await self.agent_registry.get_agent(agent_id)
                
                if not agent:
                    await websocket.close(code=4004, reason="Agent not found")
                    return
                
                # Connect WebSocket
                connection_id = await self.websocket_manager.connect(websocket, agent.id)
                
                # Update agent status to online
                await self.agent_registry.update_agent_status(agent.id, AgentStatus.ONLINE)
                
                # Send pending messages
                pending_messages = await self.queue_service.get_messages_for_agent(agent.id)
                for message in pending_messages:
                    ws_message = {
                        "type": "message",
                        "id": message.id,
                        "sender": message.sender,
                        "content": message.content,
                        "priority": message.priority.value,
                        "created_at": message.created_at.isoformat(),
                        "metadata": message.metadata
                    }
                    await websocket.send_json(ws_message)
                
                # Keep connection alive and handle incoming messages
                while True:
                    data = await websocket.receive_json()
                    
                    # Handle different message types
                    if data.get("type") == "heartbeat":
                        await self.agent_registry.heartbeat(agent.id)
                        await websocket.send_json({"type": "heartbeat_ack"})
                    
                    elif data.get("type") == "ack":
                        message_id = data.get("message_id")
                        if message_id:
                            await self.queue_service.acknowledge_message(message_id, agent.id)
                    
                    elif data.get("type") == "send_message":
                        # Agent sending a message via WebSocket
                        recipient = data.get("recipient")
                        content = data.get("content")
                        if recipient and content:
                            message = Message(
                                sender=agent.id,
                                recipient=recipient,
                                content=content,
                                priority=MessagePriority(data.get("priority", "medium"))
                            )
                            await self.queue_service.send_message(message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for agent {agent_id}")
            except Exception as e:
                logger.error(f"WebSocket error for agent {agent_id}: {e}")
            finally:
                if connection_id:
                    await self.websocket_manager.disconnect(connection_id, agent_id)
                
                # Update agent status
                if agent:
                    await self.agent_registry.update_agent_status(agent.id, AgentStatus.OFFLINE)
    
    async def start(self):
        """Start the API server."""
        logger.info(f"Starting Communication API server on {self.host}:{self.port}")
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


# Factory function for easy initialization
async def create_communication_api(
    redis_url: str = "redis://localhost:6379",
    host: str = "localhost",
    port: int = 8080
) -> CommunicationAPI:
    """Create and initialize communication API."""
    
    # Initialize services
    queue_service = MessageQueueService(redis_url=redis_url)
    agent_registry = AgentRegistry()
    
    # Start services
    await queue_service.start()
    
    # Discover existing agents
    discovered_agents = await agent_registry.discover_agents()
    for agent in discovered_agents:
        await agent_registry.register_agent(agent)
    
    # Start auto-discovery loop
    asyncio.create_task(agent_registry.auto_discovery_loop())
    
    # Create API
    api = CommunicationAPI(queue_service, agent_registry, host, port)
    
    return api