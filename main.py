#!/usr/bin/env python3
"""
LeanVibe Agent Hive - Production FastAPI Application
Main entry point for the AI orchestration system
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 LeanVibe Agent Hive starting up...")
    yield
    # Shutdown
    logger.info("🛑 LeanVibe Agent Hive shutting down...")

# Create FastAPI application
app = FastAPI(
    title="LeanVibe Agent Hive",
    description="AI orchestration system for autonomous development",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "leanvibe-agent-hive",
        "version": "1.0.0",
        "environment": os.getenv("LEANVIBE_ENVIRONMENT", "development")
    }

# Metrics endpoint (basic implementation)
@app.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Basic metrics endpoint for Prometheus"""
    return {
        "active_agents": 0,
        "task_queue_size": 0,
        "response_time_ms": 0,
        "memory_usage_mb": 0
    }

# Root endpoint
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {
        "message": "Welcome to LeanVibe Agent Hive",
        "status": "operational",
        "docs": "/docs"
    }

# API status endpoint
@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """System status endpoint"""
    return {
        "system": "LeanVibe Agent Hive",
        "status": "operational",
        "services": {
            "api": "running",
            "webhook": "running",
            "gateway": "running"
        },
        "environment": os.getenv("LEANVIBE_ENVIRONMENT", "development")
    }

# Agent coordination endpoints (stubs for now)
@app.get("/api/agents")
async def list_agents() -> Dict[str, Any]:
    """List active agents"""
    return {
        "agents": [],
        "count": 0
    }

@app.post("/api/agents/{agent_id}/tasks")
async def assign_task(agent_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assign task to agent"""
    return {
        "task_id": f"task_{agent_id}",
        "status": "assigned",
        "agent_id": agent_id
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "message": str(exc)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "Please try again later"}
    )

def main():
    """Main entry point for development"""
    print("🚀 Starting LeanVibe Agent Hive...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
