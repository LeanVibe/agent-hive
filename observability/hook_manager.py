#!/usr/bin/env python3
"""
Hook Manager for LeanVibe Agent Hive Real-Time Observability System

Provides comprehensive hook management for Claude Code Hooks integration,
enabling real-time monitoring and observability of agent behavior.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import websockets
import aiohttp
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HookType(Enum):
    """Types of hooks supported by the system."""
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    NOTIFICATION = "notification"
    STOP = "stop"
    SUBAGENT_STOP = "subagent_stop"
    AGENT_SPAWN = "agent_spawn"
    AGENT_COMPLETE = "agent_complete"
    ERROR = "error"
    PERFORMANCE = "performance"


class EventPriority(Enum):
    """Priority levels for events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HookEvent:
    """Represents a hook event with full context."""
    event_id: str
    hook_type: HookType
    agent_id: str
    session_id: str
    timestamp: datetime
    priority: EventPriority
    context: Dict[str, Any]
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['hook_type'] = self.hook_type.value
        data['priority'] = self.priority.value
        return data


class EventStream:
    """Handles real-time event streaming via WebSocket and HTTP."""
    
    def __init__(self, websocket_port: int = 8765, http_port: int = 8766):
        self.websocket_port = websocket_port
        self.http_port = http_port
        self.websocket_clients = set()
        self.event_queue = queue.Queue()
        self.running = False
        self.websocket_server = None
        self.http_server = None
        
    async def start(self):
        """Start the event streaming servers."""
        self.running = True
        
        # Start WebSocket server
        self.websocket_server = await websockets.serve(
            self.handle_websocket_connection,
            "localhost",
            self.websocket_port
        )
        
        # Start HTTP server
        await self.start_http_server()
        
        logger.info(f"Event streaming started - WebSocket: {self.websocket_port}, HTTP: {self.http_port}")
    
    async def stop(self):
        """Stop the event streaming servers."""
        self.running = False
        
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        if self.http_server:
            await self.http_server.cleanup()
        
        logger.info("Event streaming stopped")
    
    async def handle_websocket_connection(self, websocket, path):
        """Handle WebSocket client connections."""
        self.websocket_clients.add(websocket)
        logger.info(f"WebSocket client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                # Handle client messages if needed
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.websocket_clients.remove(websocket)
            logger.info(f"WebSocket client disconnected: {websocket.remote_address}")
    
    async def start_http_server(self):
        """Start HTTP server for event streaming."""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/events', self.handle_http_event)
        app.router.add_get('/events/stream', self.handle_http_stream)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.http_port)
        await site.start()
        
        self.http_server = runner
    
    async def handle_http_event(self, request):
        """Handle HTTP event submission."""
        try:
            event_data = await request.json()
            await self.broadcast_event(event_data)
            return web.json_response({'status': 'success'})
        except Exception as e:
            logger.error(f"HTTP event handling error: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)
    
    async def handle_http_stream(self, request):
        """Handle HTTP Server-Sent Events streaming."""
        from aiohttp import web
        
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        
        await response.prepare(request)
        
        # Send keep-alive and handle client disconnection
        try:
            while self.running:
                await asyncio.sleep(1)
                await response.write(b'data: {"type":"ping"}\\n\\n')
        except Exception as e:
            logger.info(f"HTTP stream client disconnected: {e}")
        
        return response
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast event to all connected clients."""
        if not self.websocket_clients:
            return
        
        event_json = json.dumps(event_data)
        
        # Send to WebSocket clients
        disconnected_clients = []
        for client in self.websocket_clients:
            try:
                await client.send(event_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            self.websocket_clients.discard(client)


class AgentMonitor:
    """Monitors agent behavior and state changes."""
    
    def __init__(self):
        self.agent_states = {}
        self.behavior_patterns = {}
        self.performance_metrics = {}
        
    def track_agent_state(self, agent_id: str, state: Dict[str, Any]):
        """Track agent state changes."""
        previous_state = self.agent_states.get(agent_id)
        self.agent_states[agent_id] = {
            'state': state,
            'timestamp': datetime.now(),
            'previous_state': previous_state
        }
        
        # Analyze behavior patterns
        self.analyze_behavior_pattern(agent_id, state, previous_state)
    
    def analyze_behavior_pattern(self, agent_id: str, current_state: Dict[str, Any], 
                                previous_state: Optional[Dict[str, Any]]):
        """Analyze agent behavior patterns."""
        if agent_id not in self.behavior_patterns:
            self.behavior_patterns[agent_id] = {
                'tool_usage': {},
                'session_duration': [],
                'error_patterns': [],
                'performance_trends': []
            }
        
        patterns = self.behavior_patterns[agent_id]
        
        # Track tool usage
        if 'tool_name' in current_state:
            tool_name = current_state['tool_name']
            patterns['tool_usage'][tool_name] = patterns['tool_usage'].get(tool_name, 0) + 1
        
        # Track session duration
        if 'session_start' in current_state:
            session_duration = (datetime.now() - current_state['session_start']).total_seconds()
            patterns['session_duration'].append(session_duration)
        
        # Track error patterns
        if 'error' in current_state:
            patterns['error_patterns'].append({
                'error': current_state['error'],
                'timestamp': datetime.now(),
                'context': current_state.get('context', {})
            })
    
    def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive metrics for an agent."""
        if agent_id not in self.agent_states:
            return {}
        
        patterns = self.behavior_patterns.get(agent_id, {})
        
        return {
            'current_state': self.agent_states[agent_id]['state'],
            'last_update': self.agent_states[agent_id]['timestamp'].isoformat(),
            'tool_usage': patterns.get('tool_usage', {}),
            'avg_session_duration': sum(patterns.get('session_duration', [])) / max(len(patterns.get('session_duration', [])), 1),
            'error_count': len(patterns.get('error_patterns', [])),
            'performance_score': self.calculate_performance_score(agent_id)
        }
    
    def calculate_performance_score(self, agent_id: str) -> float:
        """Calculate performance score for an agent."""
        patterns = self.behavior_patterns.get(agent_id, {})
        
        # Basic performance scoring algorithm
        error_count = len(patterns.get('error_patterns', []))
        tool_usage = patterns.get('tool_usage', {})
        session_durations = patterns.get('session_duration', [])
        
        base_score = 100.0
        
        # Deduct points for errors
        base_score -= min(error_count * 5, 30)
        
        # Bonus for tool diversity
        tool_diversity = len(tool_usage)
        base_score += min(tool_diversity * 2, 20)
        
        # Adjust for session consistency
        if session_durations:
            avg_duration = sum(session_durations) / len(session_durations)
            if 300 <= avg_duration <= 1800:  # 5-30 minutes is optimal
                base_score += 10
        
        return max(0, min(100, base_score))


class HookManager:
    """Main hook manager for real-time observability."""
    
    def __init__(self, websocket_port: int = 8765, http_port: int = 8766):
        self.hooks: Dict[HookType, List[Callable]] = {hook_type: [] for hook_type in HookType}
        self.event_stream = EventStream(websocket_port, http_port)
        self.agent_monitor = AgentMonitor()
        self.running = False
        self.event_history = []
        self.max_history_size = 1000
        
    async def start(self):
        """Start the hook manager system."""
        await self.event_stream.start()
        self.running = True
        logger.info("Hook Manager started successfully")
    
    async def stop(self):
        """Stop the hook manager system."""
        self.running = False
        await self.event_stream.stop()
        logger.info("Hook Manager stopped")
    
    def register_hook(self, hook_type: HookType, callback: Callable):
        """Register a hook callback for specific lifecycle events."""
        self.hooks[hook_type].append(callback)
        logger.info(f"Hook registered: {hook_type.value}")
    
    def unregister_hook(self, hook_type: HookType, callback: Callable):
        """Unregister a hook callback."""
        if callback in self.hooks[hook_type]:
            self.hooks[hook_type].remove(callback)
            logger.info(f"Hook unregistered: {hook_type.value}")
    
    async def execute_hooks(self, event: HookEvent):
        """Execute all registered hooks for an event type."""
        start_time = time.time()
        
        # Execute registered hooks
        for callback in self.hooks[event.hook_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Hook execution error: {e}")
        
        # Update agent monitoring
        self.agent_monitor.track_agent_state(event.agent_id, event.context)
        
        # Stream event to clients
        await self.event_stream.broadcast_event(event.to_dict())
        
        # Store in history with size management
        self.event_history.append(event)
        while len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        # Log performance
        execution_time = time.time() - start_time
        if execution_time > 0.1:  # Log if execution takes more than 100ms
            logger.warning(f"Hook execution took {execution_time:.3f}s for {event.hook_type.value}")
    
    async def create_and_process_event(self, hook_type: HookType, agent_id: str, 
                                     session_id: str, context: Dict[str, Any],
                                     priority: EventPriority = EventPriority.MEDIUM,
                                     **kwargs):
        """Create and process a hook event."""
        event = HookEvent(
            event_id=f"{agent_id}_{session_id}_{int(time.time() * 1000)}",
            hook_type=hook_type,
            agent_id=agent_id,
            session_id=session_id,
            timestamp=datetime.now(),
            priority=priority,
            context=context,
            **kwargs
        )
        
        await self.execute_hooks(event)
        return event
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        return {
            'hook_manager': {
                'running': self.running,
                'event_history_size': len(self.event_history),
                'registered_hooks': {hook_type.value: len(callbacks) for hook_type, callbacks in self.hooks.items()}
            },
            'event_stream': {
                'websocket_clients': len(self.event_stream.websocket_clients),
                'websocket_port': self.event_stream.websocket_port,
                'http_port': self.event_stream.http_port
            },
            'agent_monitor': {
                'tracked_agents': len(self.agent_monitor.agent_states),
                'behavior_patterns': len(self.agent_monitor.behavior_patterns)
            }
        }
    
    def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get metrics for a specific agent."""
        return self.agent_monitor.get_agent_metrics(agent_id)
    
    def get_event_history(self, limit: int = 100, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get event history with optional filtering."""
        events = self.event_history
        
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        
        return [event.to_dict() for event in events[-limit:]]


# Global hook manager instance
hook_manager = HookManager()


# Convenience functions for common hook operations
async def start_observability_system():
    """Start the observability system."""
    await hook_manager.start()


async def stop_observability_system():
    """Stop the observability system."""
    await hook_manager.stop()


def register_pre_tool_use_hook(callback: Callable):
    """Register a pre-tool-use hook."""
    hook_manager.register_hook(HookType.PRE_TOOL_USE, callback)


def register_post_tool_use_hook(callback: Callable):
    """Register a post-tool-use hook."""
    hook_manager.register_hook(HookType.POST_TOOL_USE, callback)


def register_notification_hook(callback: Callable):
    """Register a notification hook."""
    hook_manager.register_hook(HookType.NOTIFICATION, callback)


async def track_tool_use(agent_id: str, session_id: str, tool_name: str, 
                        tool_args: Dict[str, Any], is_pre_use: bool = True):
    """Track tool usage event."""
    hook_type = HookType.PRE_TOOL_USE if is_pre_use else HookType.POST_TOOL_USE
    
    await hook_manager.create_and_process_event(
        hook_type=hook_type,
        agent_id=agent_id,
        session_id=session_id,
        context={'tool_name': tool_name, 'tool_args': tool_args},
        tool_name=tool_name,
        tool_args=tool_args,
        priority=EventPriority.MEDIUM
    )


async def track_agent_error(agent_id: str, session_id: str, error_message: str, 
                           context: Dict[str, Any]):
    """Track agent error event."""
    await hook_manager.create_and_process_event(
        hook_type=HookType.ERROR,
        agent_id=agent_id,
        session_id=session_id,
        context=context,
        error_message=error_message,
        priority=EventPriority.HIGH
    )


async def track_performance_metrics(agent_id: str, session_id: str, 
                                   metrics: Dict[str, float]):
    """Track performance metrics."""
    await hook_manager.create_and_process_event(
        hook_type=HookType.PERFORMANCE,
        agent_id=agent_id,
        session_id=session_id,
        context={'metrics': metrics},
        performance_metrics=metrics,
        priority=EventPriority.LOW
    )


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        # Start the observability system
        await start_observability_system()
        
        # Register some example hooks
        def example_pre_tool_hook(event: HookEvent):
            print(f"Pre-tool hook: {event.tool_name} for agent {event.agent_id}")
        
        def example_post_tool_hook(event: HookEvent):
            print(f"Post-tool hook: {event.tool_name} completed for agent {event.agent_id}")
        
        register_pre_tool_use_hook(example_pre_tool_hook)
        register_post_tool_use_hook(example_post_tool_hook)
        
        # Simulate some events
        await track_tool_use("agent_001", "session_001", "bash", {"command": "ls -la"})
        await track_tool_use("agent_001", "session_001", "bash", {"command": "ls -la"}, is_pre_use=False)
        
        await track_performance_metrics("agent_001", "session_001", {
            "response_time": 0.25,
            "memory_usage": 128.5,
            "cpu_usage": 15.2
        })
        
        # Print system metrics
        print("System Metrics:", hook_manager.get_system_metrics())
        print("Agent Metrics:", hook_manager.get_agent_metrics("agent_001"))
        
        # Keep running for demonstration
        await asyncio.sleep(2)
        
        # Stop the system
        await stop_observability_system()
    
    # Run the example
    asyncio.run(main())