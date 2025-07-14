# .claude/agents/base_agent.py
"""BaseAgent abstract class for LeanVibe orchestration system."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class AgentStatus(Enum):
    """Agent status enumeration."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class Task:
    """Task data structure for agent execution."""
    id: str
    type: str
    description: str
    priority: int
    data: Dict[str, Any]
    created_at: datetime
    deadline: Optional[datetime] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class Result:
    """Result data structure from agent execution."""
    task_id: str
    status: str  # "success", "failure", "partial"
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: Optional[float] = None
    confidence: float = 0.0
    
    
@dataclass
class AgentInfo:
    """Agent information and status."""
    id: str
    status: AgentStatus
    capabilities: List[str]
    current_task: Optional[str] = None
    last_activity: Optional[datetime] = None
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.resource_usage is None:
            self.resource_usage = {}


class BaseAgent(ABC):
    """Abstract base class for all agents in the LeanVibe system."""
    
    def __init__(self, agent_id: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.status = AgentStatus.INITIALIZING
        self.current_task: Optional[Task] = None
        self.last_activity: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.resource_usage: Dict[str, Any] = {}
        
    @abstractmethod
    async def execute_task(self, task: Task) -> Result:
        """Execute a task and return results.
        
        Args:
            task: Task to execute
            
        Returns:
            Result object with execution details
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> AgentInfo:
        """Get current agent status.
        
        Returns:
            AgentInfo object with current status
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities.
        
        Returns:
            List of capability strings
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if agent is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent.
        
        This method should clean up resources, terminate subprocesses,
        and prepare the agent for termination.
        """
        pass
    
    # Common implementation methods
    def can_handle_task(self, task: Task) -> bool:
        """Check if agent can handle a specific task type.
        
        Args:
            task: Task to check
            
        Returns:
            True if agent can handle the task, False otherwise
        """
        return task.type in self.capabilities
    
    def update_status(self, status: AgentStatus, error_message: Optional[str] = None):
        """Update agent status.
        
        Args:
            status: New status
            error_message: Optional error message
        """
        self.status = status
        self.error_message = error_message
        self.last_activity = datetime.now()
    
    def start_task(self, task: Task):
        """Mark task as started.
        
        Args:
            task: Task being started
        """
        self.current_task = task
        self.update_status(AgentStatus.BUSY)
    
    def complete_task(self):
        """Mark current task as completed."""
        self.current_task = None
        self.update_status(AgentStatus.IDLE)
    
    def get_basic_info(self) -> AgentInfo:
        """Get basic agent information.
        
        Returns:
            AgentInfo with current state
        """
        return AgentInfo(
            id=self.agent_id,
            status=self.status,
            capabilities=self.capabilities,
            current_task=self.current_task.id if self.current_task else None,
            last_activity=self.last_activity,
            error_message=self.error_message,
            resource_usage=self.resource_usage
        )