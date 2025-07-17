"""
Trigger Manager for automated system triggers and rules.

This module provides a trigger system that can respond to various events
and conditions in the agent hive system.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum


class TriggerType(Enum):
    """Types of triggers supported by the system."""
    TASK_COMPLETION = "task_completion"
    AGENT_STATUS_CHANGE = "agent_status_change"
    SYSTEM_METRIC_THRESHOLD = "system_metric_threshold"
    TIME_BASED = "time_based"
    GIT_EVENT = "git_event"
    CUSTOM = "custom"


class TriggerStatus(Enum):
    """Status of a trigger rule."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    SUSPENDED = "suspended"


@dataclass
class TriggerRule:
    """A trigger rule definition."""
    id: str
    name: str
    type: TriggerType
    condition: Dict[str, Any]
    action: Dict[str, Any]
    status: TriggerStatus = TriggerStatus.ENABLED
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    cooldown_seconds: int = 0
    max_triggers: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerEvent:
    """An event that can trigger rules."""
    id: str
    type: TriggerType
    source: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


class TriggerManager:
    """Manages automated triggers and rules for the agent hive system."""
    
    def __init__(self, state_manager=None, git_manager=None):
        """
        Initialize the TriggerManager.
        
        Args:
            state_manager: State manager for system state
            git_manager: Git manager for git-related triggers
        """
        self.logger = logging.getLogger(__name__)
        self.state_manager = state_manager
        self.git_manager = git_manager
        
        # Rule storage
        self.rules: Dict[str, TriggerRule] = {}
        self.event_handlers: Dict[TriggerType, List[Callable]] = {
            trigger_type: [] for trigger_type in TriggerType
        }
        
        # Statistics
        self.stats = {
            "total_rules": 0,
            "enabled_rules": 0,
            "disabled_rules": 0,
            "suspended_rules": 0,
            "total_triggers": 0,
            "successful_triggers": 0,
            "failed_triggers": 0,
            "last_trigger_time": None
        }
        
        # Initialize default rules
        self._initialize_default_rules()
        
        self.logger.info("TriggerManager initialized")
    
    def _initialize_default_rules(self):
        """Initialize default trigger rules."""
        # Task completion trigger
        self.add_rule(TriggerRule(
            id="task_completion_notification",
            name="Task Completion Notification",
            type=TriggerType.TASK_COMPLETION,
            condition={"status": "completed"},
            action={"type": "notify", "channels": ["log", "metrics"]}
        ))
        
        # Agent status change trigger
        self.add_rule(TriggerRule(
            id="agent_status_monitor",
            name="Agent Status Monitor",
            type=TriggerType.AGENT_STATUS_CHANGE,
            condition={"status": "unhealthy"},
            action={"type": "alert", "level": "warning"}
        ))
        
        # System metric threshold trigger
        self.add_rule(TriggerRule(
            id="high_memory_usage",
            name="High Memory Usage Alert",
            type=TriggerType.SYSTEM_METRIC_THRESHOLD,
            condition={"metric": "memory_usage", "threshold": 85, "operator": ">="},
            action={"type": "alert", "level": "critical"}
        ))
    
    def add_rule(self, rule: TriggerRule) -> bool:
        """
        Add a new trigger rule.
        
        Args:
            rule: The trigger rule to add
            
        Returns:
            bool: True if rule was added successfully
        """
        try:
            self.rules[rule.id] = rule
            self._update_stats()
            self.logger.info(f"Added trigger rule: {rule.name} ({rule.id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add trigger rule {rule.id}: {e}")
            return False
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a trigger rule.
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            bool: True if rule was removed successfully
        """
        try:
            if rule_id in self.rules:
                del self.rules[rule_id]
                self._update_stats()
                self.logger.info(f"Removed trigger rule: {rule_id}")
                return True
            else:
                self.logger.warning(f"Rule not found: {rule_id}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove trigger rule {rule_id}: {e}")
            return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """
        Enable a trigger rule.
        
        Args:
            rule_id: ID of the rule to enable
            
        Returns:
            bool: True if rule was enabled successfully
        """
        try:
            if rule_id in self.rules:
                self.rules[rule_id].status = TriggerStatus.ENABLED
                self._update_stats()
                self.logger.info(f"Enabled trigger rule: {rule_id}")
                return True
            else:
                self.logger.warning(f"Rule not found: {rule_id}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to enable trigger rule {rule_id}: {e}")
            return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """
        Disable a trigger rule.
        
        Args:
            rule_id: ID of the rule to disable
            
        Returns:
            bool: True if rule was disabled successfully
        """
        try:
            if rule_id in self.rules:
                self.rules[rule_id].status = TriggerStatus.DISABLED
                self._update_stats()
                self.logger.info(f"Disabled trigger rule: {rule_id}")
                return True
            else:
                self.logger.warning(f"Rule not found: {rule_id}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to disable trigger rule {rule_id}: {e}")
            return False
    
    def trigger_event(self, event: TriggerEvent) -> List[str]:
        """
        Process a trigger event against all rules.
        
        Args:
            event: The trigger event to process
            
        Returns:
            List[str]: List of rule IDs that were triggered
        """
        triggered_rules = []
        
        try:
            for rule_id, rule in self.rules.items():
                if self._should_trigger_rule(rule, event):
                    if self._execute_rule_action(rule, event):
                        triggered_rules.append(rule_id)
                        rule.last_triggered = datetime.now()
                        rule.trigger_count += 1
                        self.stats["successful_triggers"] += 1
                    else:
                        self.stats["failed_triggers"] += 1
            
            self.stats["total_triggers"] += 1
            self.stats["last_trigger_time"] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error processing trigger event: {e}")
        
        return triggered_rules
    
    def _should_trigger_rule(self, rule: TriggerRule, event: TriggerEvent) -> bool:
        """
        Check if a rule should be triggered for an event.
        
        Args:
            rule: The rule to check
            event: The event to check against
            
        Returns:
            bool: True if rule should be triggered
        """
        # Check if rule is enabled
        if rule.status != TriggerStatus.ENABLED:
            return False
        
        # Check if rule type matches event type
        if rule.type != event.type:
            return False
        
        # Check cooldown period
        if rule.cooldown_seconds > 0 and rule.last_triggered:
            cooldown_end = rule.last_triggered + timedelta(seconds=rule.cooldown_seconds)
            if datetime.now() < cooldown_end:
                return False
        
        # Check max triggers limit
        if rule.max_triggers and rule.trigger_count >= rule.max_triggers:
            return False
        
        # Check rule condition
        return self._evaluate_condition(rule.condition, event.data)
    
    def _evaluate_condition(self, condition: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """
        Evaluate a rule condition against event data.
        
        Args:
            condition: The condition to evaluate
            event_data: The event data to evaluate against
            
        Returns:
            bool: True if condition is met
        """
        try:
            # Simple condition evaluation
            for key, expected_value in condition.items():
                if key == "operator":
                    continue
                    
                if key not in event_data:
                    return False
                
                actual_value = event_data[key]
                
                # Handle threshold conditions
                if "threshold" in condition and "operator" in condition:
                    threshold = condition["threshold"]
                    operator = condition["operator"]
                    
                    if operator == ">=":
                        return actual_value >= threshold
                    elif operator == "<=":
                        return actual_value <= threshold
                    elif operator == ">":
                        return actual_value > threshold
                    elif operator == "<":
                        return actual_value < threshold
                    elif operator == "==":
                        return actual_value == threshold
                    elif operator == "!=":
                        return actual_value != threshold
                else:
                    # Simple equality check
                    if actual_value != expected_value:
                        return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _execute_rule_action(self, rule: TriggerRule, event: TriggerEvent) -> bool:
        """
        Execute a rule action.
        
        Args:
            rule: The rule whose action to execute
            event: The event that triggered the rule
            
        Returns:
            bool: True if action was executed successfully
        """
        try:
            action = rule.action
            action_type = action.get("type", "log")
            
            if action_type == "log":
                self.logger.info(f"Trigger rule '{rule.name}' activated by event {event.id}")
                
            elif action_type == "notify":
                channels = action.get("channels", ["log"])
                for channel in channels:
                    if channel == "log":
                        self.logger.info(f"Notification: {rule.name} triggered")
                    elif channel == "metrics":
                        # Update metrics
                        pass
                        
            elif action_type == "alert":
                level = action.get("level", "info")
                message = f"Alert ({level}): {rule.name} triggered by {event.source}"
                
                if level == "critical":
                    self.logger.critical(message)
                elif level == "warning":
                    self.logger.warning(message)
                else:
                    self.logger.info(message)
                    
            elif action_type == "custom":
                # Execute custom action
                custom_function = action.get("function")
                if custom_function and callable(custom_function):
                    custom_function(rule, event)
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing rule action for {rule.id}: {e}")
            return False
    
    def _update_stats(self):
        """Update trigger statistics."""
        self.stats["total_rules"] = len(self.rules)
        self.stats["enabled_rules"] = len([r for r in self.rules.values() if r.status == TriggerStatus.ENABLED])
        self.stats["disabled_rules"] = len([r for r in self.rules.values() if r.status == TriggerStatus.DISABLED])
        self.stats["suspended_rules"] = len([r for r in self.rules.values() if r.status == TriggerStatus.SUSPENDED])
    
    def get_trigger_statistics(self) -> Dict[str, Any]:
        """
        Get trigger system statistics.
        
        Returns:
            Dict[str, Any]: Statistics about the trigger system
        """
        self._update_stats()
        return self.stats.copy()
    
    def get_rule(self, rule_id: str) -> Optional[TriggerRule]:
        """
        Get a specific trigger rule.
        
        Args:
            rule_id: ID of the rule to get
            
        Returns:
            Optional[TriggerRule]: The rule if found, None otherwise
        """
        return self.rules.get(rule_id)
    
    def list_rules(self, status: Optional[TriggerStatus] = None) -> List[TriggerRule]:
        """
        List all trigger rules, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List[TriggerRule]: List of rules matching the filter
        """
        if status:
            return [rule for rule in self.rules.values() if rule.status == status]
        return list(self.rules.values())
    
    def add_event_handler(self, trigger_type: TriggerType, handler: Callable):
        """
        Add an event handler for a specific trigger type.
        
        Args:
            trigger_type: Type of trigger to handle
            handler: Function to handle the trigger
        """
        if trigger_type in self.event_handlers:
            self.event_handlers[trigger_type].append(handler)
            self.logger.info(f"Added event handler for {trigger_type.value}")
    
    def remove_event_handler(self, trigger_type: TriggerType, handler: Callable):
        """
        Remove an event handler for a specific trigger type.
        
        Args:
            trigger_type: Type of trigger to handle
            handler: Function to remove
        """
        if trigger_type in self.event_handlers and handler in self.event_handlers[trigger_type]:
            self.event_handlers[trigger_type].remove(handler)
            self.logger.info(f"Removed event handler for {trigger_type.value}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the trigger system.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        return {
            "status": "healthy",
            "rules_count": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.status == TriggerStatus.ENABLED]),
            "last_trigger": self.stats.get("last_trigger_time"),
            "success_rate": (
                self.stats["successful_triggers"] / max(1, self.stats["total_triggers"])
                if self.stats["total_triggers"] > 0 else 1.0
            )
        }