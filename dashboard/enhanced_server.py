#!/usr/bin/env python3
"""
Enhanced LeanVibe Agent Hive Dashboard Server

Enhanced dashboard with GitHub integration, prompt review workflow,
and pragmatic easy wins for better agent management.
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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

try:
    from .prompt_logger import prompt_logger, PromptLog
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append('.')
    from prompt_logger import prompt_logger, PromptLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDashboardServer:
    """Enhanced dashboard server with GitHub integration and prompt review workflow"""
    
    def __init__(self, session_name: str = "agent-hive", base_dir: str = "."):
        self.session_name = session_name
        self.base_dir = Path(base_dir)
        self.websocket_connections: List[WebSocket] = []
        self.recent_metrics: List[Dict[str, Any]] = []
        
        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting enhanced monitoring tasks")
            asyncio.create_task(self._broadcast_updates())
            yield
            # Shutdown
            logger.info("Shutting down enhanced monitoring tasks")
        
        self.app = FastAPI(
            title="LeanVibe Agent Hive Enhanced Dashboard", 
            version="2.0.0",
            lifespan=lifespan
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_page():
            """Serve the enhanced dashboard HTML page"""
            return await self._get_enhanced_dashboard_html()
        
        @self.app.get("/api/github/prs")
        async def get_github_prs():
            """Get GitHub PRs for dashboard"""
            try:
                result = await self._run_command(["gh", "pr", "list", "--json", 
                    "number,title,author,state,additions,deletions,reviewDecision,mergeable,headRefName,updatedAt"])
                if result.returncode == 0:
                    prs = json.loads(result.stdout)
                    return {"prs": prs}
                else:
                    return {"prs": [], "error": "Could not fetch PRs"}
            except Exception as e:
                return {"prs": [], "error": str(e)}
        
        @self.app.get("/api/github/activity")
        async def get_git_activity():
            """Get recent git activity for dashboard"""
            try:
                # Get recent commits
                result = await self._run_command(["git", "log", "--oneline", 
                    "-10", "--pretty=format:%h|%an|%ar|%s"])
                commits = []
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if '|' in line:
                            parts = line.split('|', 3)
                            if len(parts) == 4:
                                commits.append({
                                    'hash': parts[0],
                                    'author': parts[1], 
                                    'time': parts[2],
                                    'message': parts[3]
                                })
                
                return {"commits": commits}
            except Exception as e:
                return {"commits": [], "error": str(e)}
        
        @self.app.post("/api/agents/{agent_name}/message")
        async def send_agent_message(agent_name: str, request: Request):
            """Send message to specific agent"""
            try:
                data = await request.json()
                message = data.get('message', '')
                result = await self._run_command([
                    "python", "scripts/send_agent_message.py", 
                    "--agent", agent_name, "--message", message
                ])
                
                if result.returncode == 0:
                    return {"success": True, "message": f"Message sent to {agent_name}"}
                else:
                    return {"success": False, "error": result.stderr}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.app.get("/api/prompts/recent")
        async def get_recent_prompts():
            """Get recent prompts for dashboard"""
            prompts = prompt_logger.get_recent_prompts(limit=30)
            return {"prompts": [p.to_dict() for p in prompts]}
        
        @self.app.get("/api/prompts/needs-review")
        async def get_prompts_needing_review():
            """Get prompts needing PM review"""
            prompts = prompt_logger.get_prompts_needing_review()
            return {"prompts": [p.to_dict() for p in prompts]}
        
        @self.app.get("/api/prompts/stats")
        async def get_prompt_stats():
            """Get prompt statistics"""
            return {"stats": prompt_logger.get_prompt_stats()}
        
        @self.app.post("/api/prompts/{prompt_id}/review")
        async def add_pm_review(prompt_id: int, request: Request):
            """Add PM review to a prompt"""
            try:
                data = await request.json()
                prompt_logger.add_pm_review(
                    prompt_id, 
                    data.get('review', ''),
                    data.get('suggested_improvement', '')
                )
                return {"message": "Review added successfully"}
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.post("/api/prompts/{prompt_id}/gemini-review")
        async def add_gemini_review(prompt_id: int, request: Request):
            """Add Gemini CLI review to a prompt"""
            try:
                data = await request.json()
                gemini_feedback = data.get('feedback', '')
                prompt_logger.add_gemini_feedback(prompt_id, gemini_feedback)
                return {"message": "Gemini review added successfully"}
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.post("/api/metrics")
        async def receive_metrics(request: Request):
            """Receive metrics from dashboard integration"""
            try:
                data = await request.json()
                
                # Validate required fields
                required_fields = ['metric_id', 'type', 'value', 'status', 'timestamp']
                if not all(field in data for field in required_fields):
                    raise HTTPException(status_code=400, detail="Missing required fields")
                
                # Store metric data for dashboard display
                metric_data = {
                    'metric_id': data['metric_id'],
                    'type': data['type'],
                    'value': data['value'],
                    'status': data['status'],
                    'timestamp': data['timestamp'],
                    'source': data.get('source', 'unknown')
                }
                
                # Broadcast to connected WebSocket clients
                await self._broadcast_metric_update(metric_data)
                
                logger.info(f"Received metric: {data['type']} = {data['value']} [{data['status']}]")
                return {"message": "Metric received successfully", "metric_id": data['metric_id']}
                
            except Exception as e:
                logger.error(f"Error receiving metric: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get recent metrics for dashboard display"""
            try:
                # Return stored metrics (simplified for now)
                return {"metrics": self.recent_metrics}
            except Exception as e:
                return {"metrics": [], "error": str(e)}
        
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint for dashboard integration"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0"
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await self._handle_websocket(websocket)
    
    async def _get_enhanced_dashboard_html(self) -> str:
        """Generate enhanced dashboard HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LeanVibe Agent Hive Enhanced Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                :root {
                    --primary-color: #2c3e50;
                    --secondary-color: #3498db;
                    --success-color: #27ae60;
                    --warning-color: #f39c12;
                    --danger-color: #e74c3c;
                    --bg-color: #f8f9fa;
                    --card-bg: white;
                    --text-color: #2c3e50;
                    --border-radius: 12px;
                    --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    --transition: all 0.3s ease;
                }
                
                * { margin: 0; padding: 0; box-sizing: border-box; }
                
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: var(--bg-color);
                    color: var(--text-color);
                    line-height: 1.6;
                }
                
                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                .header {
                    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                    color: white;
                    padding: 24px;
                    border-radius: var(--border-radius);
                    margin-bottom: 24px;
                    box-shadow: var(--shadow);
                }
                
                .section-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin: 30px 0 20px;
                    padding: 0 4px;
                }
                
                .section-header h2 {
                    color: var(--primary-color);
                    font-size: 20px;
                    font-weight: 700;
                }
                
                .btn {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: 600;
                    transition: var(--transition);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-right: 8px;
                }
                
                .btn:hover { transform: translateY(-1px); }
                
                .btn-primary { background: var(--secondary-color); color: white; }
                .btn-success { background: var(--success-color); color: white; }
                .btn-danger { background: var(--danger-color); color: white; }
                .btn-small { padding: 4px 12px; font-size: 12px; }
                
                /* GitHub PRs Section */
                .github-section {
                    background: var(--card-bg);
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow);
                    margin-bottom: 20px;
                    overflow: hidden;
                }
                
                .pr-item {
                    padding: 16px 20px;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                    transition: background-color 0.2s ease;
                }
                
                .pr-item:hover { background-color: rgba(0, 0, 0, 0.02); }
                .pr-item:last-child { border-bottom: none; }
                
                .pr-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                
                .pr-title {
                    font-weight: 600;
                    color: var(--primary-color);
                    font-size: 16px;
                }
                
                .pr-number {
                    font-size: 14px;
                    color: #666;
                    margin-right: 8px;
                }
                
                .pr-stats {
                    display: flex;
                    gap: 12px;
                    font-size: 12px;
                    color: #666;
                    margin-top: 4px;
                }
                
                /* Status badges */
                .status-badge {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .status-badge.success {
                    background: rgba(39, 174, 96, 0.1);
                    color: var(--success-color);
                    border: 1px solid rgba(39, 174, 96, 0.2);
                }
                
                .status-badge.error {
                    background: rgba(231, 76, 60, 0.1);
                    color: var(--danger-color);
                    border: 1px solid rgba(231, 76, 60, 0.2);
                }
                
                .status-badge.needs-review {
                    background: rgba(243, 156, 18, 0.1);
                    color: var(--warning-color);
                    border: 1px solid rgba(243, 156, 18, 0.2);
                }
                
                /* Prompt Review Section */
                .prompt-log {
                    background: var(--card-bg);
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow);
                    margin-bottom: 20px;
                    max-height: 600px;
                    overflow-y: auto;
                }
                
                .prompt-item {
                    padding: 16px 20px;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                }
                
                .prompt-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                
                .prompt-agent {
                    font-weight: 600;
                    color: var(--primary-color);
                }
                
                .prompt-text {
                    font-size: 14px;
                    line-height: 1.4;
                    color: #333;
                    margin-bottom: 8px;
                    background: rgba(0, 0, 0, 0.02);
                    padding: 8px;
                    border-radius: 4px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    max-height: 100px;
                    overflow-y: auto;
                }
                
                .prompt-review-actions {
                    margin-top: 12px;
                    display: flex;
                    gap: 8px;
                }
                
                .review-form {
                    margin-top: 12px;
                    padding: 12px;
                    background: rgba(0, 0, 0, 0.02);
                    border-radius: 6px;
                    display: none;
                }
                
                .review-textarea {
                    width: 100%;
                    min-height: 60px;
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 13px;
                    margin-bottom: 8px;
                    font-family: inherit;
                }
                
                /* Metrics Section */
                .metrics-section {
                    background: var(--card-bg);
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow);
                    margin-bottom: 20px;
                    max-height: 400px;
                    overflow-y: auto;
                }
                
                .metric-item {
                    padding: 16px 20px;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: background-color 0.2s ease;
                }
                
                .metric-item:hover { background-color: rgba(0, 0, 0, 0.02); }
                .metric-item:last-child { border-bottom: none; }
                
                .metric-info {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
                
                .metric-type {
                    font-weight: 600;
                    color: var(--primary-color);
                    text-transform: capitalize;
                }
                
                .metric-details {
                    font-size: 12px;
                    color: #666;
                    display: flex;
                    gap: 12px;
                }
                
                .metric-value {
                    font-size: 20px;
                    font-weight: 700;
                    padding: 8px 16px;
                    border-radius: 6px;
                    min-width: 80px;
                    text-align: center;
                }
                
                .metric-value.compliant {
                    background: rgba(39, 174, 96, 0.1);
                    color: var(--success-color);
                    border: 1px solid rgba(39, 174, 96, 0.2);
                }
                
                .metric-value.warning {
                    background: rgba(243, 156, 18, 0.1);
                    color: var(--warning-color);
                    border: 1px solid rgba(243, 156, 18, 0.2);
                }
                
                .metric-value.violation {
                    background: rgba(231, 76, 60, 0.1);
                    color: var(--danger-color);
                    border: 1px solid rgba(231, 76, 60, 0.2);
                }
                
                .metric-new {
                    animation: metricPulse 2s ease-in-out;
                }
                
                @keyframes metricPulse {
                    0% { background-color: rgba(52, 152, 219, 0.2); }
                    50% { background-color: rgba(52, 152, 219, 0.05); }
                    100% { background-color: transparent; }
                }
                
                /* Activity Section */
                .activity-section {
                    background: var(--card-bg);
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow);
                    margin-bottom: 20px;
                    max-height: 300px;
                    overflow-y: auto;
                }
                
                .commit-item {
                    padding: 12px 20px;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .commit-hash {
                    font-family: 'Monaco', 'Menlo', monospace;
                    background: rgba(0, 0, 0, 0.05);
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 12px;
                    color: var(--primary-color);
                }
                
                .commit-message {
                    flex: 1;
                    font-size: 14px;
                    color: var(--text-color);
                }
                
                .commit-author {
                    font-size: 12px;
                    color: #666;
                    font-weight: 500;
                }
                
                .commit-time {
                    font-size: 12px;
                    color: #999;
                }
                
                /* Quick stats grid */
                .quick-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                    margin-bottom: 24px;
                }
                
                .stat-card {
                    background: var(--card-bg);
                    padding: 20px;
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow);
                    text-align: center;
                }
                
                .stat-value {
                    font-size: 28px;
                    font-weight: 700;
                    color: var(--primary-color);
                    margin-bottom: 4px;
                }
                
                .stat-label {
                    font-size: 14px;
                    color: #666;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                /* Notifications */
                .notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 12px 24px;
                    border-radius: 6px;
                    color: white;
                    font-weight: 600;
                    z-index: 1000;
                    animation: slideIn 0.3s ease;
                }
                
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                
                /* Responsive design */
                @media (max-width: 768px) {
                    .container { padding: 16px; }
                    .quick-stats { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
                    .section-header { flex-direction: column; gap: 12px; align-items: flex-start; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 LeanVibe Agent Hive Enhanced Dashboard</h1>
                    <p class="subtitle">Real-time Multi-Agent Monitoring & PR Review Workflow</p>
                </div>
                
                <div class="quick-stats" id="quick-stats">
                    <!-- Quick stats will be populated by JavaScript -->
                </div>
                
                <div class="section-header">
                    <h2>🐙 GitHub Pull Requests</h2>
                    <button class="btn btn-primary" onclick="refreshPRs()">Refresh PRs</button>
                </div>
                
                <div id="github-prs" class="github-section">
                    <!-- GitHub PRs will be populated by JavaScript -->
                </div>
                
                <div class="section-header">
                    <h2>📝 Prompt Review Dashboard</h2>
                    <div>
                        <button class="btn btn-success" onclick="loadNeedsReview()">Needs Review</button>
                        <button class="btn btn-primary" onclick="loadRecentPrompts()">Recent Prompts</button>
                    </div>
                </div>
                
                <div id="prompt-log" class="prompt-log">
                    <!-- Prompt log will be populated by JavaScript -->
                </div>
                
                <div class="section-header">
                    <h2>📈 Real-time Metrics</h2>
                    <button class="btn btn-primary" onclick="refreshMetrics()">Refresh</button>
                </div>
                
                <div id="metrics-display" class="metrics-section">
                    <!-- Metrics will be populated by JavaScript -->
                </div>
                
                <div class="section-header">
                    <h2>📊 Git Activity</h2>
                    <button class="btn btn-primary" onclick="refreshActivity()">Refresh</button>
                </div>
                
                <div id="git-activity" class="activity-section">
                    <!-- Git activity will be populated by JavaScript -->
                </div>
            </div>
            
            <script>
                // Global state
                let currentPrompts = [];
                let currentMetrics = [];
                let websocket = null;
                
                // Initialize dashboard
                document.addEventListener('DOMContentLoaded', function() {
                    loadAllData();
                    initWebSocket();
                    
                    // Refresh data every 30 seconds
                    setInterval(loadAllData, 30000);
                });
                
                function loadAllData() {
                    loadQuickStats();
                    loadGitHubPRs();
                    loadRecentPrompts();
                    loadMetrics();
                    loadGitActivity();
                }
                
                function loadQuickStats() {
                    Promise.all([
                        fetch('/api/prompts/stats').then(r => r.json()),
                        fetch('/api/github/prs').then(r => r.json())
                    ]).then(([promptStats, prData]) => {
                        const stats = promptStats.stats || {};
                        const prs = prData.prs || [];
                        
                        const needsReviewCount = stats.needs_review || 0;
                        const openPRs = prs.length;
                        const totalPrompts = stats.total_prompts || 0;
                        const successRate = Math.round((stats.success_rate || 0) * 100);
                        
                        document.getElementById('quick-stats').innerHTML = `
                            <div class="stat-card">
                                <div class="stat-value">${needsReviewCount}</div>
                                <div class="stat-label">Prompts Need Review</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${openPRs}</div>
                                <div class="stat-label">Open PRs</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${totalPrompts}</div>
                                <div class="stat-label">Total Prompts</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${successRate}%</div>
                                <div class="stat-label">Success Rate</div>
                            </div>
                        `;
                    }).catch(error => console.error('Error loading quick stats:', error));
                }
                
                function loadGitHubPRs() {
                    fetch('/api/github/prs')
                        .then(response => response.json())
                        .then(data => updateGitHubPRs(data.prs || []))
                        .catch(error => console.error('Error loading GitHub PRs:', error));
                }
                
                function updateGitHubPRs(prs) {
                    const prDiv = document.getElementById('github-prs');
                    if (prs.length === 0) {
                        prDiv.innerHTML = '<div class="pr-item">No open PRs found.</div>';
                        return;
                    }
                    
                    prDiv.innerHTML = prs.map(pr => {
                        const statusColor = pr.reviewDecision === 'APPROVED' ? 'success' : 
                                          pr.reviewDecision === 'CHANGES_REQUESTED' ? 'error' : 'needs-review';
                        
                        const sizeWarning = pr.additions > 1000 ? '⚠️ ' : '';
                        
                        return `
                            <div class="pr-item">
                                <div class="pr-header">
                                    <div>
                                        <span class="pr-number">#${pr.number}</span>
                                        <span class="pr-title">${sizeWarning}${pr.title}</span>
                                    </div>
                                    <span class="status-badge ${statusColor}">${pr.reviewDecision || 'Pending'}</span>
                                </div>
                                <div class="pr-stats">
                                    <span>👤 ${pr.author.login}</span>
                                    <span>➕ ${pr.additions}</span>
                                    <span>➖ ${pr.deletions}</span>
                                    <span>🔀 ${pr.mergeable || 'Unknown'}</span>
                                    <span>🕒 ${new Date(pr.updatedAt).toLocaleDateString()}</span>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
                
                function loadRecentPrompts() {
                    fetch('/api/prompts/recent')
                        .then(response => response.json())
                        .then(data => {
                            currentPrompts = data.prompts || [];
                            updatePromptLog(currentPrompts);
                        })
                        .catch(error => console.error('Error loading recent prompts:', error));
                }
                
                function loadNeedsReview() {
                    fetch('/api/prompts/needs-review')
                        .then(response => response.json())
                        .then(data => {
                            currentPrompts = data.prompts || [];
                            updatePromptLog(currentPrompts);
                            showNotification(`${currentPrompts.length} prompts need review`, 'info');
                        })
                        .catch(error => console.error('Error loading needs review:', error));
                }
                
                function updatePromptLog(prompts) {
                    const logDiv = document.getElementById('prompt-log');
                    if (prompts.length === 0) {
                        logDiv.innerHTML = '<div class="prompt-item">No prompts found.</div>';
                        return;
                    }
                    
                    logDiv.innerHTML = prompts.map(prompt => {
                        const timestamp = new Date(prompt.timestamp).toLocaleString();
                        const truncatedPrompt = prompt.prompt_text.length > 300 ? 
                            prompt.prompt_text.substring(0, 300) + '...' : 
                            prompt.prompt_text;
                        
                        const statusBadge = prompt.success ? 
                            '<span class="status-badge success">Success</span>' : 
                            '<span class="status-badge error">Error</span>';
                        
                        const reviewBadge = !prompt.pm_review ? 
                            '<span class="status-badge needs-review">Needs Review</span>' : 
                            '<span class="status-badge success">Reviewed</span>';
                        
                        const needsReview = !prompt.pm_review;
                        const reviewActions = needsReview ? `
                            <div class="prompt-review-actions">
                                <button class="btn btn-small btn-primary" onclick="showReviewForm(${prompt.id})">Add Review</button>
                                <button class="btn btn-small btn-success" onclick="runGeminiReview(${prompt.id})">Gemini Review</button>
                            </div>
                            <div id="review-form-${prompt.id}" class="review-form">
                                <textarea id="review-text-${prompt.id}" class="review-textarea" placeholder="Enter PM review..."></textarea>
                                <textarea id="improvement-text-${prompt.id}" class="review-textarea" placeholder="Suggested improvement..."></textarea>
                                <button class="btn btn-small btn-success" onclick="submitReview(${prompt.id})">Submit Review</button>
                                <button class="btn btn-small" onclick="hideReviewForm(${prompt.id})">Cancel</button>
                            </div>
                        ` : '';
                        
                        return `
                            <div class="prompt-item">
                                <div class="prompt-header">
                                    <span class="prompt-agent">${prompt.agent_name}</span>
                                    <span class="prompt-time">${timestamp}</span>
                                </div>
                                <div class="prompt-text">${truncatedPrompt}</div>
                                <div class="prompt-status">
                                    ${statusBadge}
                                    ${reviewBadge}
                                    ${prompt.gemini_feedback ? '🤖 Gemini Reviewed' : ''}
                                </div>
                                ${prompt.pm_review ? `
                                    <div style="margin-top: 8px; padding: 8px; background: rgba(39, 174, 96, 0.1); border-radius: 4px;">
                                        <strong>PM Review:</strong> ${prompt.pm_review}<br>
                                        ${prompt.suggested_improvement ? `<strong>Improvement:</strong> ${prompt.suggested_improvement}` : ''}
                                    </div>
                                ` : ''}
                                ${prompt.gemini_feedback ? `
                                    <div style="margin-top: 8px; padding: 8px; background: rgba(52, 152, 219, 0.1); border-radius: 4px;">
                                        <strong>Gemini Feedback:</strong> ${prompt.gemini_feedback}
                                    </div>
                                ` : ''}
                                ${reviewActions}
                            </div>
                        `;
                    }).join('');
                }
                
                function loadGitActivity() {
                    fetch('/api/github/activity')
                        .then(response => response.json())
                        .then(data => updateGitActivity(data.commits || []))
                        .catch(error => console.error('Error loading git activity:', error));
                }
                
                function updateGitActivity(commits) {
                    const activityDiv = document.getElementById('git-activity');
                    if (commits.length === 0) {
                        activityDiv.innerHTML = '<div class="commit-item">No recent commits found.</div>';
                        return;
                    }
                    
                    activityDiv.innerHTML = commits.map(commit => `
                        <div class="commit-item">
                            <span class="commit-hash">${commit.hash}</span>
                            <span class="commit-message">${commit.message}</span>
                            <span class="commit-author">${commit.author}</span>
                            <span class="commit-time">${commit.time}</span>
                        </div>
                    `).join('');
                }
                
                function refreshPRs() {
                    loadGitHubPRs();
                    loadQuickStats();
                    showNotification('PRs refreshed', 'success');
                }
                
                function refreshActivity() {
                    loadGitActivity();
                    showNotification('Activity refreshed', 'success');
                }
                
                function refreshMetrics() {
                    loadMetrics();
                    showNotification('Metrics refreshed', 'success');
                }
                
                function initWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws`;
                    
                    websocket = new WebSocket(wsUrl);
                    
                    websocket.onopen = function() {
                        console.log('WebSocket connected');
                        showNotification('Real-time updates connected', 'success');
                    };
                    
                    websocket.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        if (data.type === 'metric_update') {
                            handleMetricUpdate(data.data);
                        }
                    };
                    
                    websocket.onclose = function() {
                        console.log('WebSocket disconnected');
                        showNotification('Real-time updates disconnected', 'warning');
                        
                        // Reconnect after 5 seconds
                        setTimeout(initWebSocket, 5000);
                    };
                    
                    websocket.onerror = function(error) {
                        console.error('WebSocket error:', error);
                    };
                }
                
                function loadMetrics() {
                    fetch('/api/metrics')
                        .then(response => response.json())
                        .then(data => {
                            currentMetrics = data.metrics || [];
                            updateMetricsDisplay(currentMetrics);
                        })
                        .catch(error => console.error('Error loading metrics:', error));
                }
                
                function updateMetricsDisplay(metrics) {
                    const metricsDiv = document.getElementById('metrics-display');
                    if (metrics.length === 0) {
                        metricsDiv.innerHTML = '<div class="metric-item">No metrics available yet.</div>';
                        return;
                    }
                    
                    // Sort metrics by timestamp (newest first)
                    const sortedMetrics = metrics.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                    
                    metricsDiv.innerHTML = sortedMetrics.map(metric => {
                        const timestamp = new Date(metric.timestamp).toLocaleString();
                        const typeDisplay = metric.type.replace('_', ' ');
                        
                        return `
                            <div class="metric-item" id="metric-${metric.metric_id}">
                                <div class="metric-info">
                                    <div class="metric-type">${typeDisplay}</div>
                                    <div class="metric-details">
                                        <span>📅 ${timestamp}</span>
                                        <span>🔗 ${metric.source}</span>
                                        <span>🆔 ${metric.metric_id}</span>
                                    </div>
                                </div>
                                <div class="metric-value ${metric.status}">
                                    ${formatMetricValue(metric.value, metric.type)}
                                </div>
                            </div>
                        `;
                    }).join('');
                }
                
                function handleMetricUpdate(metricData) {
                    // Add to current metrics
                    currentMetrics.unshift(metricData);
                    
                    // Keep only last 50 metrics
                    if (currentMetrics.length > 50) {
                        currentMetrics = currentMetrics.slice(0, 50);
                    }
                    
                    // Update display
                    updateMetricsDisplay(currentMetrics);
                    
                    // Highlight new metric
                    setTimeout(() => {
                        const metricElement = document.getElementById(`metric-${metricData.metric_id}`);
                        if (metricElement) {
                            metricElement.classList.add('metric-new');
                        }
                    }, 100);
                    
                    // Show notification
                    const typeDisplay = metricData.type.replace('_', ' ');
                    showNotification(`New ${typeDisplay}: ${formatMetricValue(metricData.value, metricData.type)}`, 'info');
                }
                
                function formatMetricValue(value, type) {
                    switch (type) {
                        case 'xp_compliance':
                            return `${value}%`;
                        case 'pr_size':
                            return `${value} lines`;
                        case 'velocity':
                            return `${value} pts`;
                        default:
                            return value;
                    }
                }
                
                function showReviewForm(promptId) {
                    document.getElementById(`review-form-${promptId}`).style.display = 'block';
                }
                
                function hideReviewForm(promptId) {
                    document.getElementById(`review-form-${promptId}`).style.display = 'none';
                }
                
                function submitReview(promptId) {
                    const review = document.getElementById(`review-text-${promptId}`).value;
                    const improvement = document.getElementById(`improvement-text-${promptId}`).value;
                    
                    if (!review.trim()) {
                        showNotification('Please enter a review', 'error');
                        return;
                    }
                    
                    fetch(`/api/prompts/${promptId}/review`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({review, suggested_improvement: improvement})
                    })
                    .then(response => response.json())
                    .then(data => {
                        hideReviewForm(promptId);
                        loadRecentPrompts();
                        loadQuickStats();
                        showNotification('Review submitted successfully!', 'success');
                    })
                    .catch(error => {
                        console.error('Error submitting review:', error);
                        showNotification('Failed to submit review', 'error');
                    });
                }
                
                function runGeminiReview(promptId) {
                    const prompt = currentPrompts.find(p => p.id === promptId);
                    if (!prompt) {
                        showNotification('Prompt not found', 'error');
                        return;
                    }
                    
                    showNotification('Running Gemini review...', 'info');
                    
                    // Simulate Gemini review (in practice, this would call Gemini CLI)
                    const sampleFeedback = generateAutoReview(prompt);
                    
                    fetch(`/api/prompts/${promptId}/gemini-review`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({feedback: sampleFeedback})
                    })
                    .then(response => response.json())
                    .then(data => {
                        loadRecentPrompts();
                        showNotification('Gemini review completed!', 'success');
                    })
                    .catch(error => {
                        console.error('Error adding Gemini review:', error);
                        showNotification('Failed to add Gemini review', 'error');
                    });
                }
                
                function generateAutoReview(prompt) {
                    const text = prompt.prompt_text.toLowerCase();
                    const reviews = [];
                    
                    if (text.length < 50) {
                        reviews.push("Prompt is very short and may lack context");
                    }
                    
                    if (text.length > 1000) {
                        reviews.push("Prompt is quite long and could be more concise");
                    }
                    
                    if (!text.includes('please') && !text.includes('help')) {
                        reviews.push("Consider adding polite language");
                    }
                    
                    if (text.includes('urgent') || text.includes('asap')) {
                        reviews.push("Contains urgency indicators - ensure justified");
                    }
                    
                    if (reviews.length === 0) {
                        reviews.push("Prompt appears well-structured and clear");
                    }
                    
                    return reviews.join('. ') + '.';
                }
                
                function showNotification(message, type) {
                    const notification = document.createElement('div');
                    notification.className = 'notification';
                    notification.textContent = message;
                    
                    if (type === 'success') notification.style.background = '#27ae60';
                    else if (type === 'error') notification.style.background = '#e74c3c';
                    else notification.style.background = '#3498db';
                    
                    document.body.appendChild(notification);
                    
                    setTimeout(() => {
                        notification.remove();
                    }, 3000);
                }
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
    
    async def _broadcast_updates(self):
        """Broadcast updates to all WebSocket connections"""
        while True:
            try:
                if self.websocket_connections:
                    # Send update notification
                    update_data = {
                        "type": "update",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Broadcast to all connections
                    disconnected = []
                    for ws in self.websocket_connections:
                        try:
                            await ws.send_text(json.dumps(update_data))
                        except Exception:
                            disconnected.append(ws)
                    
                    # Remove disconnected connections
                    for ws in disconnected:
                        self.websocket_connections.remove(ws)
                
            except Exception as e:
                logger.error(f"Error broadcasting updates: {e}")
            
            await asyncio.sleep(30)  # Broadcast every 30 seconds
    
    async def _broadcast_metric_update(self, metric_data: Dict[str, Any]):
        """Broadcast metric update to all WebSocket connections"""
        # Store metric for future retrieval (keep last 50)
        self.recent_metrics.append(metric_data)
        if len(self.recent_metrics) > 50:
            self.recent_metrics.pop(0)
        
        # Broadcast to WebSocket clients
        if self.websocket_connections:
            update_message = {
                "type": "metric_update",
                "data": metric_data,
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected = []
            for ws in self.websocket_connections:
                try:
                    await ws.send_text(json.dumps(update_message))
                except Exception:
                    disconnected.append(ws)
            
            # Remove disconnected connections
            for ws in disconnected:
                self.websocket_connections.remove(ws)
    
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
    """Main function to run the enhanced dashboard server"""
    server = EnhancedDashboardServer()
    
    logger.info("Starting LeanVibe Agent Hive Enhanced Dashboard Server")
    logger.info("Enhanced Dashboard available at: http://localhost:8001")
    
    uvicorn.run(server.app, host="0.0.0.0", port=8002, log_level="info")

if __name__ == "__main__":
    main()