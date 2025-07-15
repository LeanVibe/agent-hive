#!/usr/bin/env python3
"""
LeanVibe Agent Hive Dashboard Server

Real-time dashboard backend with FastAPI and WebSocket support for monitoring
agent activities, system health, and providing live updates to the frontend.
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SPAWNING = "spawning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class AgentInfo:
    """Agent information structure"""
    name: str
    status: AgentStatus
    window_name: str
    path: str
    last_activity: Optional[datetime] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    task_count: int = 0
    uptime: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        if self.last_activity:
            data['last_activity'] = self.last_activity.isoformat()
        data['status'] = self.status.value
        return data


@dataclass
class SystemMetrics:
    """System metrics structure"""
    total_agents: int
    active_agents: int
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_usage: float
    uptime: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class DashboardServer:
    """Dashboard server with real-time monitoring capabilities"""
    
    def __init__(self, session_name: str = "agent-hive", base_dir: str = "."):
        self.session_name = session_name
        self.base_dir = Path(base_dir)
        self.worktrees_dir = self.base_dir / "worktrees"
        self.app = FastAPI(title="LeanVibe Agent Hive Dashboard", version="1.0.0")
        self.websocket_connections: List[WebSocket] = []
        self.agents: Dict[str, AgentInfo] = {}
        self.system_metrics = SystemMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0)
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
        self._setup_periodic_updates()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_page():
            """Serve the dashboard HTML page"""
            return await self._get_dashboard_html()
        
        @self.app.get("/api/agents")
        async def get_agents():
            """Get all agents information"""
            return {"agents": [agent.to_dict() for agent in self.agents.values()]}
        
        @self.app.get("/api/agents/{agent_name}")
        async def get_agent(agent_name: str):
            """Get specific agent information"""
            if agent_name not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
            return {"agent": self.agents[agent_name].to_dict()}
        
        @self.app.get("/api/system/metrics")
        async def get_system_metrics():
            """Get system metrics"""
            return {"metrics": self.system_metrics.to_dict()}
        
        @self.app.post("/api/agents/{agent_name}/spawn")
        async def spawn_agent(agent_name: str):
            """Spawn a specific agent"""
            success = await self._spawn_agent(agent_name)
            if success:
                return {"message": f"Agent {agent_name} spawned successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to spawn agent")
        
        @self.app.post("/api/agents/{agent_name}/kill")
        async def kill_agent(agent_name: str):
            """Kill a specific agent"""
            success = await self._kill_agent(agent_name)
            if success:
                return {"message": f"Agent {agent_name} killed successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to kill agent")
        
        @self.app.post("/api/agents/spawn-all")
        async def spawn_all_agents():
            """Spawn all agents"""
            results = await self._spawn_all_agents()
            return {"results": results}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await self._handle_websocket(websocket)
    
    def _setup_periodic_updates(self):
        """Setup periodic updates for monitoring"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """Start periodic monitoring tasks"""
            asyncio.create_task(self._monitor_agents())
            asyncio.create_task(self._monitor_system())
            asyncio.create_task(self._broadcast_updates())
    
    async def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LeanVibe Agent Hive Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
                .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .metric-title { font-size: 14px; color: #666; margin-bottom: 8px; }
                .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
                .agents { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .agent-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .agent-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                .agent-name { font-size: 18px; font-weight: bold; }
                .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
                .status.active { background: #d4edda; color: #155724; }
                .status.inactive { background: #f8d7da; color: #721c24; }
                .status.spawning { background: #fff3cd; color: #856404; }
                .agent-info { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px; }
                .controls { margin-top: 15px; }
                .btn { padding: 8px 16px; margin-right: 8px; border: none; border-radius: 4px; cursor: pointer; }
                .btn-primary { background: #007bff; color: white; }
                .btn-danger { background: #dc3545; color: white; }
                .btn-success { background: #28a745; color: white; }
                #connection-status { float: right; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
                .connected { background: #d4edda; color: #155724; }
                .disconnected { background: #f8d7da; color: #721c24; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 LeanVibe Agent Hive Dashboard</h1>
                    <div id="connection-status" class="disconnected">Disconnected</div>
                </div>
                
                <div class="metrics" id="metrics">
                    <!-- Metrics will be populated by JavaScript -->
                </div>
                
                <div class="agents" id="agents">
                    <!-- Agents will be populated by JavaScript -->
                </div>
            </div>
            
            <script>
                let ws = null;
                let reconnectAttempts = 0;
                const maxReconnectAttempts = 5;
                
                function connectWebSocket() {
                    ws = new WebSocket('ws://localhost:8000/ws');
                    
                    ws.onopen = function() {
                        console.log('WebSocket connected');
                        document.getElementById('connection-status').textContent = 'Connected';
                        document.getElementById('connection-status').className = 'connected';
                        reconnectAttempts = 0;
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        if (data.type === 'agents_update') {
                            updateAgents(data.agents);
                        } else if (data.type === 'metrics_update') {
                            updateMetrics(data.metrics);
                        }
                    };
                    
                    ws.onclose = function() {
                        console.log('WebSocket disconnected');
                        document.getElementById('connection-status').textContent = 'Disconnected';
                        document.getElementById('connection-status').className = 'disconnected';
                        
                        if (reconnectAttempts < maxReconnectAttempts) {
                            reconnectAttempts++;
                            setTimeout(connectWebSocket, 2000 * reconnectAttempts);
                        }
                    };
                    
                    ws.onerror = function(error) {
                        console.error('WebSocket error:', error);
                    };
                }
                
                function updateMetrics(metrics) {
                    const metricsDiv = document.getElementById('metrics');
                    metricsDiv.innerHTML = `
                        <div class="metric-card">
                            <div class="metric-title">Total Agents</div>
                            <div class="metric-value">${metrics.total_agents}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Active Agents</div>
                            <div class="metric-value">${metrics.active_agents}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">CPU Usage</div>
                            <div class="metric-value">${metrics.cpu_usage.toFixed(1)}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Memory Usage</div>
                            <div class="metric-value">${metrics.memory_usage.toFixed(1)}%</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-title">Uptime</div>
                            <div class="metric-value">${Math.floor(metrics.uptime / 60)}m</div>
                        </div>
                    `;
                }
                
                function updateAgents(agents) {
                    const agentsDiv = document.getElementById('agents');
                    agentsDiv.innerHTML = agents.map(agent => `
                        <div class="agent-card">
                            <div class="agent-header">
                                <div class="agent-name">${agent.name}</div>
                                <div class="status ${agent.status}">${agent.status.toUpperCase()}</div>
                            </div>
                            <div class="agent-info">
                                <div>Window: ${agent.window_name}</div>
                                <div>Tasks: ${agent.task_count}</div>
                                <div>CPU: ${agent.cpu_usage.toFixed(1)}%</div>
                                <div>Memory: ${agent.memory_usage.toFixed(1)}%</div>
                                <div>Uptime: ${Math.floor(agent.uptime / 60)}m</div>
                                <div>Last Activity: ${agent.last_activity ? new Date(agent.last_activity).toLocaleTimeString() : 'Unknown'}</div>
                            </div>
                            <div class="controls">
                                <button class="btn btn-primary" onclick="spawnAgent('${agent.name}')">Spawn</button>
                                <button class="btn btn-danger" onclick="killAgent('${agent.name}')">Kill</button>
                            </div>
                        </div>
                    `).join('');
                }
                
                function spawnAgent(agentName) {
                    fetch(`/api/agents/${agentName}/spawn`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => console.log('Agent spawned:', data))
                        .catch(error => console.error('Error spawning agent:', error));
                }
                
                function killAgent(agentName) {
                    fetch(`/api/agents/${agentName}/kill`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => console.log('Agent killed:', data))
                        .catch(error => console.error('Error killing agent:', error));
                }
                
                // Initialize
                connectWebSocket();
                
                // Load initial data
                fetch('/api/agents')
                    .then(response => response.json())
                    .then(data => updateAgents(data.agents))
                    .catch(error => console.error('Error loading agents:', error));
                
                fetch('/api/system/metrics')
                    .then(response => response.json())
                    .then(data => updateMetrics(data.metrics))
                    .catch(error => console.error('Error loading metrics:', error));
            </script>
        </body>
        </html>
        """
    
    async def _handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections"""
        await websocket.accept()
        self.websocket_connections.append(websocket)
        
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            self.websocket_connections.remove(websocket)
    
    async def _monitor_agents(self):
        """Monitor agent status periodically"""
        while True:
            try:
                # Discover agents
                agents = await self._discover_agents()
                
                # Update agent status
                for agent_name, agent_info in agents.items():
                    if agent_name not in self.agents:
                        self.agents[agent_name] = agent_info
                    else:
                        # Update existing agent info
                        self.agents[agent_name].status = agent_info.status
                        self.agents[agent_name].last_activity = agent_info.last_activity
                
                # Update system metrics
                self.system_metrics.total_agents = len(self.agents)
                self.system_metrics.active_agents = len([a for a in self.agents.values() if a.status == AgentStatus.ACTIVE])
                
                logger.info(f"Monitored {len(self.agents)} agents, {self.system_metrics.active_agents} active")
                
            except Exception as e:
                logger.error(f"Error monitoring agents: {e}")
            
            await asyncio.sleep(2)  # Monitor every 2 seconds
    
    async def _monitor_system(self):
        """Monitor system metrics periodically"""
        while True:
            try:
                # Update system metrics (placeholder for now)
                self.system_metrics.cpu_usage = await self._get_cpu_usage()
                self.system_metrics.memory_usage = await self._get_memory_usage()
                self.system_metrics.uptime += 5
                
            except Exception as e:
                logger.error(f"Error monitoring system: {e}")
            
            await asyncio.sleep(5)  # Monitor every 5 seconds
    
    async def _broadcast_updates(self):
        """Broadcast updates to all WebSocket connections"""
        while True:
            try:
                if self.websocket_connections:
                    # Send agents update
                    agents_data = {
                        "type": "agents_update",
                        "agents": [agent.to_dict() for agent in self.agents.values()]
                    }
                    
                    # Send metrics update
                    metrics_data = {
                        "type": "metrics_update",
                        "metrics": self.system_metrics.to_dict()
                    }
                    
                    # Broadcast to all connections
                    disconnected = []
                    for ws in self.websocket_connections:
                        try:
                            await ws.send_text(json.dumps(agents_data))
                            await ws.send_text(json.dumps(metrics_data))
                        except Exception:
                            disconnected.append(ws)
                    
                    # Remove disconnected connections
                    for ws in disconnected:
                        self.websocket_connections.remove(ws)
                
            except Exception as e:
                logger.error(f"Error broadcasting updates: {e}")
            
            await asyncio.sleep(1)  # Broadcast every second
    
    async def _discover_agents(self) -> Dict[str, AgentInfo]:
        """Discover all agents from worktrees"""
        agents = {}
        
        if not self.worktrees_dir.exists():
            return agents
        
        for worktree_dir in self.worktrees_dir.iterdir():
            if worktree_dir.is_dir():
                agent_name = worktree_dir.name
                claude_file = worktree_dir / "CLAUDE.md"
                
                if claude_file.exists():
                    status = await self._get_agent_status(agent_name)
                    last_activity = await self._get_last_activity(worktree_dir)
                    
                    agents[agent_name] = AgentInfo(
                        name=agent_name,
                        status=status,
                        window_name=f"agent-{agent_name}",
                        path=str(worktree_dir),
                        last_activity=last_activity
                    )
        
        return agents
    
    async def _get_agent_status(self, agent_name: str) -> AgentStatus:
        """Get agent status from tmux"""
        try:
            window_name = f"agent-{agent_name}"
            result = await self._run_command([
                "tmux", "list-windows", "-t", self.session_name, "-F", "#{window_name}:#{window_active}"
            ])
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith(window_name + ":"):
                        return AgentStatus.ACTIVE if line.endswith(":1") else AgentStatus.INACTIVE
            
            return AgentStatus.INACTIVE
            
        except Exception:
            return AgentStatus.UNKNOWN
    
    async def _get_last_activity(self, worktree_dir: Path) -> Optional[datetime]:
        """Get last git activity in worktree"""
        try:
            result = await self._run_command([
                "git", "log", "-1", "--format=%ct"
            ], cwd=worktree_dir)
            
            if result.returncode == 0 and result.stdout.strip():
                timestamp = int(result.stdout.strip())
                return datetime.fromtimestamp(timestamp)
        except Exception:
            pass
        
        return None
    
    async def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            result = await self._run_command(["top", "-l", "1", "-n", "0"])
            if result.returncode == 0:
                # Parse CPU usage from top output (placeholder)
                return 25.0
        except Exception:
            pass
        return 0.0
    
    async def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            result = await self._run_command(["vm_stat"])
            if result.returncode == 0:
                # Parse memory usage from vm_stat output (placeholder)
                return 35.0
        except Exception:
            pass
        return 0.0
    
    async def _spawn_agent(self, agent_name: str) -> bool:
        """Spawn an agent"""
        try:
            result = await self._run_command([
                "python", "scripts/agent_manager.py", "--spawn", agent_name, "--force"
            ])
            return result.returncode == 0
        except Exception:
            return False
    
    async def _kill_agent(self, agent_name: str) -> bool:
        """Kill an agent"""
        try:
            result = await self._run_command([
                "python", "scripts/agent_manager.py", "--kill", agent_name
            ])
            return result.returncode == 0
        except Exception:
            return False
    
    async def _spawn_all_agents(self) -> Dict[str, bool]:
        """Spawn all agents"""
        results = {}
        for agent_name in self.agents:
            results[agent_name] = await self._spawn_agent(agent_name)
        return results
    
    async def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            cmd, process.returncode, stdout.decode(), stderr.decode()
        )


def main():
    """Main function to run the dashboard server"""
    server = DashboardServer()
    
    logger.info("Starting LeanVibe Agent Hive Dashboard Server")
    logger.info("Dashboard available at: http://localhost:8000")
    
    uvicorn.run(server.app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()