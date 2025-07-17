"""
TriggerManager - Event-driven trigger management system for LeanVibe Agent Hive.

Provides comprehensive trigger management for orchestrating agent behaviors,
task execution, and system events based on various conditions and thresholds.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of triggers supported by the system."""
    TIME_BASED = "time_based"
    CONDITION_BASED = "condition_based"
    EVENT_BASED = "event_based"
    THRESHOLD_BASED = "threshold_based"
    MANUAL = "manual"


class TriggerStatus(Enum):
    """Status of a trigger."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


@dataclass
class TriggerCondition:
    """Represents a trigger condition."""
    condition_id: str
    condition_type: TriggerType
    condition_data: Dict[str, Any]
    threshold: Optional[float] = None
    operator: str = "eq"  # eq, gt, lt, gte, lte, ne
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TriggerAction:
    """Represents an action to be taken when a trigger fires."""
    action_id: str
    action_type: str
    action_data: Dict[str, Any]
    priority: int = 5
    timeout: Optional[int] = None
    retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Trigger:
    """Represents a complete trigger with conditions and actions."""
    trigger_id: str
    name: str
    description: str
    conditions: List[TriggerCondition]
    actions: List[TriggerAction]
    status: TriggerStatus = TriggerStatus.ACTIVE
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TriggerManager:
    """Manages triggers for the LeanVibe Agent Hive system."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the TriggerManager."""
        self.config = config or {}
        self.triggers: Dict[str, Trigger] = {}
        self.active_monitors: Dict[str, asyncio.Task] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.running = False
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """Start the trigger manager."""
        self.running = True
        self.logger.info("TriggerManager started")
        
        # Start monitoring tasks for active triggers
        for trigger_id, trigger in self.triggers.items():
            if trigger.status == TriggerStatus.ACTIVE:
                await self._start_trigger_monitor(trigger_id)
    
    async def stop(self):
        """Stop the trigger manager."""
        self.running = False
        
        # Cancel all monitoring tasks
        for task in self.active_monitors.values():
            task.cancel()
        
        # Wait for all tasks to complete
        if self.active_monitors:
            await asyncio.gather(*self.active_monitors.values(), return_exceptions=True)
        
        self.active_monitors.clear()
        self.logger.info("TriggerManager stopped")
    
    async def add_trigger(self, trigger: Trigger) -> bool:
        """Add a new trigger to the system."""
        try:
            self.triggers[trigger.trigger_id] = trigger
            
            if trigger.status == TriggerStatus.ACTIVE and self.running:
                await self._start_trigger_monitor(trigger.trigger_id)
            
            self.logger.info(f"Added trigger: {trigger.trigger_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding trigger {trigger.trigger_id}: {e}")
            return False
    
    async def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a trigger from the system."""
        try:
            if trigger_id in self.active_monitors:
                self.active_monitors[trigger_id].cancel()
                del self.active_monitors[trigger_id]
            
            if trigger_id in self.triggers:
                del self.triggers[trigger_id]
                self.logger.info(f"Removed trigger: {trigger_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing trigger {trigger_id}: {e}")
            return False
    
    async def update_trigger_status(self, trigger_id: str, status: TriggerStatus) -> bool:
        """Update the status of a trigger."""
        try:
            if trigger_id not in self.triggers:
                return False
            
            old_status = self.triggers[trigger_id].status
            self.triggers[trigger_id].status = status
            
            # Handle status changes
            if old_status == TriggerStatus.ACTIVE and status != TriggerStatus.ACTIVE:
                # Stop monitoring
                if trigger_id in self.active_monitors:
                    self.active_monitors[trigger_id].cancel()
                    del self.active_monitors[trigger_id]
            
            elif old_status != TriggerStatus.ACTIVE and status == TriggerStatus.ACTIVE:
                # Start monitoring
                if self.running:
                    await self._start_trigger_monitor(trigger_id)
            
            self.logger.info(f"Updated trigger {trigger_id} status: {old_status} -> {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating trigger {trigger_id} status: {e}")
            return False
    
    async def fire_trigger(self, trigger_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Manually fire a trigger."""
        try:
            if trigger_id not in self.triggers:
                return False
            
            trigger = self.triggers[trigger_id]
            
            # Update trigger metadata
            trigger.last_triggered = datetime.now()
            trigger.trigger_count += 1
            trigger.status = TriggerStatus.TRIGGERED
            
            # Execute actions
            success = await self._execute_actions(trigger.actions, context or {})
            
            # Reset status to active if it was active before
            if success:
                trigger.status = TriggerStatus.ACTIVE
            
            self.logger.info(f"Fired trigger: {trigger_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error firing trigger {trigger_id}: {e}")
            return False
    
    async def evaluate_conditions(self, trigger_id: str, context: Dict[str, Any]) -> bool:
        """Evaluate if trigger conditions are met."""
        try:
            if trigger_id not in self.triggers:
                return False
            
            trigger = self.triggers[trigger_id]
            
            # All conditions must be met (AND logic)
            for condition in trigger.conditions:
                if not await self._evaluate_condition(condition, context):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating conditions for trigger {trigger_id}: {e}")
            return False
    
    async def get_trigger_status(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a trigger."""
        if trigger_id not in self.triggers:
            return None
        
        trigger = self.triggers[trigger_id]
        return {
            "trigger_id": trigger_id,
            "name": trigger.name,
            "status": trigger.status.value,
            "last_triggered": trigger.last_triggered.isoformat() if trigger.last_triggered else None,
            "trigger_count": trigger.trigger_count,
            "conditions_count": len(trigger.conditions),
            "actions_count": len(trigger.actions)
        }
    
    async def list_triggers(self) -> List[Dict[str, Any]]:
        """List all triggers."""
        return [
            await self.get_trigger_status(trigger_id)
            for trigger_id in self.triggers.keys()
        ]
    
    async def _start_trigger_monitor(self, trigger_id: str):
        """Start monitoring a trigger."""
        if trigger_id in self.active_monitors:
            return
        
        self.active_monitors[trigger_id] = asyncio.create_task(
            self._monitor_trigger(trigger_id)
        )
    
    async def _monitor_trigger(self, trigger_id: str):
        """Monitor a trigger for condition changes."""
        try:
            while self.running and trigger_id in self.triggers:
                trigger = self.triggers[trigger_id]
                
                if trigger.status != TriggerStatus.ACTIVE:
                    break
                
                # Check conditions
                context = await self._get_evaluation_context()
                if await self.evaluate_conditions(trigger_id, context):
                    await self.fire_trigger(trigger_id, context)
                
                # Wait before next check
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error monitoring trigger {trigger_id}: {e}")
    
    async def _evaluate_condition(self, condition: TriggerCondition, context: Dict[str, Any]) -> bool:
        """Evaluate a single condition."""
        try:
            if condition.condition_type == TriggerType.TIME_BASED:
                return await self._evaluate_time_condition(condition, context)
            elif condition.condition_type == TriggerType.CONDITION_BASED:
                return await self._evaluate_condition_based(condition, context)
            elif condition.condition_type == TriggerType.EVENT_BASED:
                return await self._evaluate_event_condition(condition, context)
            elif condition.condition_type == TriggerType.THRESHOLD_BASED:
                return await self._evaluate_threshold_condition(condition, context)
            elif condition.condition_type == TriggerType.MANUAL:
                return True
            else:
                return False
        
        except Exception as e:
            self.logger.error(f"Error evaluating condition {condition.condition_id}: {e}")
            return False
    
    async def _evaluate_time_condition(self, condition: TriggerCondition, context: Dict[str, Any]) -> bool:
        """Evaluate time-based condition."""
        # Simple time-based evaluation
        current_time = datetime.now()
        schedule = condition.condition_data.get("schedule")
        
        if schedule == "hourly":
            return current_time.minute == 0
        elif schedule == "daily":
            return current_time.hour == 0 and current_time.minute == 0
        
        return False
    
    async def _evaluate_condition_based(self, condition: TriggerCondition, context: Dict[str, Any]) -> bool:
        """Evaluate condition-based trigger."""
        field = condition.condition_data.get("field")
        expected_value = condition.condition_data.get("value")
        actual_value = context.get(field)
        
        if actual_value is None:
            return False
        
        operator = condition.operator
        if operator == "eq":
            return actual_value == expected_value
        elif operator == "gt":
            return actual_value > expected_value
        elif operator == "lt":
            return actual_value < expected_value
        elif operator == "gte":
            return actual_value >= expected_value
        elif operator == "lte":
            return actual_value <= expected_value
        elif operator == "ne":
            return actual_value != expected_value
        
        return False
    
    async def _evaluate_event_condition(self, condition: TriggerCondition, context: Dict[str, Any]) -> bool:
        """Evaluate event-based condition."""
        event_type = condition.condition_data.get("event_type")
        return context.get("event_type") == event_type
    
    async def _evaluate_threshold_condition(self, condition: TriggerCondition, context: Dict[str, Any]) -> bool:
        """Evaluate threshold-based condition."""
        field = condition.condition_data.get("field")
        threshold = condition.threshold
        actual_value = context.get(field)
        
        if actual_value is None or threshold is None:
            return False
        
        operator = condition.operator
        if operator == "gt":
            return actual_value > threshold
        elif operator == "lt":
            return actual_value < threshold
        elif operator == "gte":
            return actual_value >= threshold
        elif operator == "lte":
            return actual_value <= threshold
        
        return False
    
    async def _execute_actions(self, actions: List[TriggerAction], context: Dict[str, Any]) -> bool:
        """Execute trigger actions."""
        success = True
        
        for action in actions:
            try:
                await self._execute_action(action, context)
            except Exception as e:
                self.logger.error(f"Error executing action {action.action_id}: {e}")
                success = False
        
        return success
    
    async def _execute_action(self, action: TriggerAction, context: Dict[str, Any]):
        """Execute a single action."""
        # This is a placeholder - in a real implementation, this would
        # interface with the actual system components
        action_type = action.action_type
        action_data = action.action_data
        
        if action_type == "log":
            self.logger.info(f"Trigger action: {action_data.get('message', 'No message')}")
        elif action_type == "notify":
            # Would send notification
            pass
        elif action_type == "execute":
            # Would execute command or function
            pass
        elif action_type == "state_change":
            # Would change system state
            pass
    
    async def _get_evaluation_context(self) -> Dict[str, Any]:
        """Get context for condition evaluation."""
        # This would gather real system metrics and state
        return {
            "current_time": datetime.now(),
            "system_load": 0.5,
            "active_agents": 3,
            "pending_tasks": 5,
            "memory_usage": 0.4,
            "event_type": None
        }