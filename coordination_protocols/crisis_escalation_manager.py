#!/usr/bin/env python3
"""
Crisis Escalation Manager for Multi-Agent Coordination
Foundation Epic Phase 1 Completion Integration

Handles real-time COORDINATION_CRISIS and DEADLINE_WARNING events with
escalation patterns for red-level crises and automated response protocols.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Import event bus infrastructure
from .event_bus import EventBus, EventType, EventPriority, EventMessage

logger = logging.getLogger(__name__)


class CrisisLevel(Enum):
    """Crisis severity levels for escalation."""
    GREEN = "green"      # Normal operations
    YELLOW = "yellow"    # Warning level  
    ORANGE = "orange"    # High attention required
    RED = "red"          # Critical - immediate action
    BLACK = "black"      # Emergency - human intervention


class EscalationAction(Enum):
    """Available escalation actions."""
    LOG_ALERT = "log_alert"
    NOTIFY_AGENTS = "notify_agents"
    ESCALATE_TO_PM = "escalate_to_pm"
    TRIGGER_EMERGENCY = "trigger_emergency"
    HUMAN_INTERVENTION = "human_intervention"
    AUTO_REASSIGN = "auto_reassign"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass
class CrisisEvent:
    """Crisis event with escalation metadata."""
    crisis_id: str
    crisis_level: CrisisLevel
    event_type: EventType
    source_agent: str
    description: str
    timestamp: datetime
    escalation_actions: List[EscalationAction]
    context: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class EscalationRule:
    """Rule for crisis escalation."""
    rule_id: str
    event_types: List[EventType]
    conditions: Dict[str, Any]  # Conditions to match
    crisis_level: CrisisLevel
    actions: List[EscalationAction]
    cooldown_minutes: int = 5
    active: bool = True


class CrisisEscalationManager:
    """
    Crisis Escalation Manager for Foundation Epic coordination.
    
    Integrates with EventBus to handle COORDINATION_CRISIS and DEADLINE_WARNING
    events with automated escalation patterns and response protocols.
    """
    
    def __init__(self, config_path: str = ".claude/crisis_config.json"):
        """Initialize crisis escalation manager."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Event bus integration
        self.event_bus: Optional[EventBus] = None
        
        # Crisis tracking
        self.active_crises: Dict[str, CrisisEvent] = {}
        self.escalation_rules: Dict[str, EscalationRule] = {}
        self.escalation_history: List[CrisisEvent] = []
        self.last_escalation: Dict[str, datetime] = {}
        
        # Response handlers
        self.response_handlers: Dict[EscalationAction, Callable] = {}
        
        # Statistics
        self.stats = {
            "crises_detected": 0,
            "crises_resolved": 0,
            "escalations_triggered": 0,
            "human_interventions": 0,
            "auto_resolutions": 0
        }
        
        # Initialize default escalation rules
        self._initialize_escalation_rules()
        self._initialize_response_handlers()
        
        logger.info("CrisisEscalationManager initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load crisis escalation configuration."""
        default_config = {
            "crisis_retention_hours": 168,  # 1 week
            "max_concurrent_crises": 10,
            "escalation_cooldown_minutes": 5,
            "auto_resolution_timeout_minutes": 60,
            "red_crisis_immediate_escalation": True,
            "foundation_epic_integration": {
                "pr_failure_threshold": 3,
                "deadline_warning_threshold_hours": 2,
                "coordination_crisis_auto_escalate": True
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.error(f"Failed to load crisis config: {e}")
        
        return default_config
    
    def _initialize_escalation_rules(self) -> None:
        """Initialize default escalation rules for Foundation Epic."""
        
        # RED-level crisis rules (immediate escalation)
        red_coordination_crisis = EscalationRule(
            rule_id="red_coordination_crisis",
            event_types=[EventType.COORDINATION_CRISIS],
            conditions={"priority": "critical", "crisis_level": "red"},
            crisis_level=CrisisLevel.RED,
            actions=[
                EscalationAction.LOG_ALERT,
                EscalationAction.NOTIFY_AGENTS,
                EscalationAction.ESCALATE_TO_PM,
                EscalationAction.HUMAN_INTERVENTION
            ],
            cooldown_minutes=0  # No cooldown for red-level
        )
        
        # ORANGE-level deadline warnings
        orange_deadline_warning = EscalationRule(
            rule_id="orange_deadline_warning",
            event_types=[EventType.DEADLINE_WARNING],
            conditions={"hours_remaining": {"lt": 2}},
            crisis_level=CrisisLevel.ORANGE,
            actions=[
                EscalationAction.LOG_ALERT,
                EscalationAction.NOTIFY_AGENTS,
                EscalationAction.ESCALATE_TO_PM
            ],
            cooldown_minutes=30
        )
        
        # Foundation Epic specific rules
        epic_failure_rule = EscalationRule(
            rule_id="foundation_epic_failure",
            event_types=[EventType.QUALITY_GATE_FAILURE, EventType.PR_MERGE_EVENT],
            conditions={"epic": "foundation", "failure_count": {"gte": 3}},
            crisis_level=CrisisLevel.RED,
            actions=[
                EscalationAction.LOG_ALERT,
                EscalationAction.TRIGGER_EMERGENCY,
                EscalationAction.HUMAN_INTERVENTION
            ],
            cooldown_minutes=0
        )
        
        # Task escalation rule
        task_escalation_rule = EscalationRule(
            rule_id="task_escalation_auto",
            event_types=[EventType.TASK_ESCALATION],
            conditions={"escalation_level": "emergency"},
            crisis_level=CrisisLevel.ORANGE,
            actions=[
                EscalationAction.LOG_ALERT,
                EscalationAction.AUTO_REASSIGN,
                EscalationAction.NOTIFY_AGENTS
            ],
            cooldown_minutes=15
        )
        
        # Add rules to manager
        for rule in [red_coordination_crisis, orange_deadline_warning, epic_failure_rule, task_escalation_rule]:
            self.escalation_rules[rule.rule_id] = rule
            
        logger.info(f"Initialized {len(self.escalation_rules)} escalation rules")
    
    def _initialize_response_handlers(self) -> None:
        """Initialize response handlers for escalation actions."""
        
        async def log_alert_handler(crisis: CrisisEvent) -> None:
            """Log crisis alert."""
            level_emoji = {
                CrisisLevel.RED: "🚨",
                CrisisLevel.ORANGE: "⚠️",
                CrisisLevel.YELLOW: "💛",
                CrisisLevel.GREEN: "✅",
                CrisisLevel.BLACK: "💀"
            }
            
            emoji = level_emoji.get(crisis.crisis_level, "❓")
            
            logger.critical(
                f"{emoji} CRISIS ALERT [{crisis.crisis_level.value.upper()}] "
                f"{crisis.event_type.value} from {crisis.source_agent}: {crisis.description}"
            )
        
        async def notify_agents_handler(crisis: CrisisEvent) -> None:
            """Notify other agents of crisis."""
            notification_data = {
                "crisis_id": crisis.crisis_id,
                "crisis_level": crisis.crisis_level.value,
                "event_type": crisis.event_type.value,
                "source_agent": crisis.source_agent,
                "description": crisis.description,
                "timestamp": crisis.timestamp.isoformat(),
                "requires_attention": crisis.crisis_level in [CrisisLevel.RED, CrisisLevel.ORANGE]
            }
            
            # Publish notification event via event bus
            if self.event_bus:
                await self.event_bus.publish_event(
                    event_type=EventType.SYSTEM_ALERT,
                    payload=notification_data,
                    source_agent="crisis_manager",
                    priority=EventPriority.HIGH,
                    tags={"crisis_notification": "true", "crisis_level": crisis.crisis_level.value}
                )
            
            logger.info(f"Notified agents of crisis: {crisis.crisis_id}")
        
        async def escalate_to_pm_handler(crisis: CrisisEvent) -> None:
            """Escalate crisis to PM agent."""
            pm_escalation = {
                "crisis_id": crisis.crisis_id,
                "crisis_level": crisis.crisis_level.value,
                "requires_immediate_attention": crisis.crisis_level == CrisisLevel.RED,
                "context": crisis.context,
                "recommended_actions": [action.value for action in crisis.escalation_actions],
                "escalated_at": datetime.now().isoformat()
            }
            
            # Send to PM agent coordination channel
            if self.event_bus:
                await self.event_bus.publish_event(
                    event_type=EventType.COORDINATION_CRISIS,
                    payload=pm_escalation,
                    source_agent="crisis_manager",
                    priority=EventPriority.CRITICAL if crisis.crisis_level == CrisisLevel.RED else EventPriority.HIGH,
                    tags={"pm_escalation": "true", "crisis_level": crisis.crisis_level.value}
                )
            
            logger.warning(f"Escalated crisis to PM: {crisis.crisis_id}")
        
        async def trigger_emergency_handler(crisis: CrisisEvent) -> None:
            """Trigger emergency protocols."""
            emergency_data = {
                "crisis_id": crisis.crisis_id,
                "emergency_level": "foundation_epic_critical",
                "immediate_actions_required": True,
                "context": crisis.context,
                "triggered_at": datetime.now().isoformat()
            }
            
            # Write emergency file for external monitoring
            emergency_file = Path(".claude/emergency_alert.json")
            emergency_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(emergency_file, 'w') as f:
                json.dump(emergency_data, f, indent=2, default=str)
            
            logger.critical(f"EMERGENCY TRIGGERED: {crisis.crisis_id} - {crisis.description}")
        
        async def human_intervention_handler(crisis: CrisisEvent) -> None:
            """Request human intervention."""
            intervention_data = {
                "crisis_id": crisis.crisis_id,
                "crisis_level": crisis.crisis_level.value,
                "human_action_required": True,
                "description": crisis.description,
                "context": crisis.context,
                "requested_at": datetime.now().isoformat()
            }
            
            # Write human intervention request
            intervention_file = Path(".claude/human_intervention_required.json")
            intervention_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(intervention_file, 'w') as f:
                json.dump(intervention_data, f, indent=2, default=str)
            
            self.stats["human_interventions"] += 1
            
            logger.critical(f"HUMAN INTERVENTION REQUIRED: {crisis.crisis_id}")
        
        async def auto_reassign_handler(crisis: CrisisEvent) -> None:
            """Automatically reassign failed tasks."""
            reassignment_data = {
                "crisis_id": crisis.crisis_id,
                "original_agent": crisis.source_agent,
                "reassignment_reason": crisis.description,
                "auto_reassigned": True,
                "reassigned_at": datetime.now().isoformat()
            }
            
            if self.event_bus:
                await self.event_bus.publish_event(
                    event_type=EventType.AGENT_STATUS_CHANGE,
                    payload=reassignment_data,
                    source_agent="crisis_manager",
                    priority=EventPriority.HIGH,
                    tags={"auto_reassignment": "true"}
                )
            
            logger.info(f"Auto-reassigned task from crisis: {crisis.crisis_id}")
        
        # Register handlers
        self.response_handlers = {
            EscalationAction.LOG_ALERT: log_alert_handler,
            EscalationAction.NOTIFY_AGENTS: notify_agents_handler,
            EscalationAction.ESCALATE_TO_PM: escalate_to_pm_handler,
            EscalationAction.TRIGGER_EMERGENCY: trigger_emergency_handler,
            EscalationAction.HUMAN_INTERVENTION: human_intervention_handler,
            EscalationAction.AUTO_REASSIGN: auto_reassign_handler
        }
        
        logger.info(f"Initialized {len(self.response_handlers)} response handlers")
    
    async def integrate_with_event_bus(self, event_bus: EventBus) -> None:
        """Integrate with event bus for crisis monitoring."""
        self.event_bus = event_bus
        
        # Register crisis event handler
        async def crisis_event_handler(event: EventMessage) -> None:
            await self.handle_crisis_event(event)
        
        # Register for crisis-related events
        event_bus.register_handler(
            "crisis_manager",
            crisis_event_handler,
            [EventType.COORDINATION_CRISIS, EventType.DEADLINE_WARNING, 
             EventType.TASK_ESCALATION, EventType.QUALITY_GATE_FAILURE],
            [EventPriority.CRITICAL, EventPriority.HIGH]
        )
        
        logger.info("Integrated with event bus for crisis monitoring")
    
    async def handle_crisis_event(self, event: EventMessage) -> None:
        """Handle incoming crisis event."""
        try:
            logger.info(f"Handling crisis event: {event.event_type.value} from {event.source_agent}")
            
            # Find matching escalation rules
            matching_rules = self._find_matching_rules(event)
            
            if not matching_rules:
                logger.debug(f"No escalation rules matched for event: {event.event_id}")
                return
            
            # Process each matching rule
            for rule in matching_rules:
                await self._process_escalation_rule(event, rule)
            
            self.stats["crises_detected"] += 1
            
        except Exception as e:
            logger.error(f"Error handling crisis event {event.event_id}: {e}")
    
    def _find_matching_rules(self, event: EventMessage) -> List[EscalationRule]:
        """Find escalation rules that match the event."""
        matching_rules = []
        
        for rule in self.escalation_rules.values():
            if not rule.active:
                continue
            
            # Check event type match
            if event.event_type not in rule.event_types:
                continue
            
            # Check cooldown
            if self._is_rule_in_cooldown(rule):
                continue
            
            # Check conditions
            if self._check_rule_conditions(event, rule):
                matching_rules.append(rule)
        
        return matching_rules
    
    def _is_rule_in_cooldown(self, rule: EscalationRule) -> bool:
        """Check if rule is in cooldown period."""
        if rule.cooldown_minutes <= 0:
            return False
        
        last_execution = self.last_escalation.get(rule.rule_id)
        if not last_execution:
            return False
        
        cooldown_threshold = last_execution + timedelta(minutes=rule.cooldown_minutes)
        return datetime.now() < cooldown_threshold
    
    def _check_rule_conditions(self, event: EventMessage, rule: EscalationRule) -> bool:
        """Check if event matches rule conditions."""
        try:
            payload = event.payload
            
            for condition_key, condition_value in rule.conditions.items():
                
                # Handle nested condition checks
                if condition_key in payload:
                    actual_value = payload[condition_key]
                    
                    # Handle comparison operators
                    if isinstance(condition_value, dict):
                        for operator, expected in condition_value.items():
                            if operator == "lt" and not (actual_value < expected):
                                return False
                            elif operator == "gte" and not (actual_value >= expected):
                                return False
                            elif operator == "eq" and not (actual_value == expected):
                                return False
                    else:
                        # Direct value comparison
                        if actual_value != condition_value:
                            return False
                
                # Special handling for priority
                elif condition_key == "priority":
                    if event.priority.value != condition_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rule conditions: {e}")
            return False
    
    async def _process_escalation_rule(self, event: EventMessage, rule: EscalationRule) -> None:
        """Process escalation rule for event."""
        try:
            # Create crisis event
            crisis = CrisisEvent(
                crisis_id=f"crisis_{int(datetime.now().timestamp()*1000)}",
                crisis_level=rule.crisis_level,
                event_type=event.event_type,
                source_agent=event.source_agent,
                description=event.payload.get("message", f"Crisis: {event.event_type.value}"),
                timestamp=datetime.now(),
                escalation_actions=rule.actions.copy(),
                context=event.payload.copy()
            )
            
            # Add to active crises
            self.active_crises[crisis.crisis_id] = crisis
            
            # Execute escalation actions
            for action in rule.actions:
                if action in self.response_handlers:
                    try:
                        await self.response_handlers[action](crisis)
                        logger.debug(f"Executed escalation action: {action.value}")
                    except Exception as e:
                        logger.error(f"Failed to execute action {action.value}: {e}")
            
            # Update rule execution time
            self.last_escalation[rule.rule_id] = datetime.now()
            self.stats["escalations_triggered"] += 1
            
            # Add to history
            self.escalation_history.append(crisis)
            
            logger.info(f"Processed escalation: {crisis.crisis_id} [{rule.crisis_level.value}]")
            
        except Exception as e:
            logger.error(f"Error processing escalation rule {rule.rule_id}: {e}")
    
    async def resolve_crisis(self, crisis_id: str, resolution_note: str = "") -> bool:
        """Manually resolve a crisis."""
        if crisis_id not in self.active_crises:
            return False
        
        crisis = self.active_crises[crisis_id]
        crisis.resolved = True
        crisis.resolution_time = datetime.now()
        
        # Remove from active crises
        del self.active_crises[crisis_id]
        
        self.stats["crises_resolved"] += 1
        
        logger.info(f"Crisis resolved: {crisis_id} - {resolution_note}")
        return True
    
    def get_crisis_status(self) -> Dict[str, Any]:
        """Get crisis manager status."""
        return {
            "active_crises": len(self.active_crises),
            "escalation_rules": len(self.escalation_rules),
            "response_handlers": len(self.response_handlers),
            "statistics": self.stats.copy(),
            "crisis_levels": {
                level.value: len([c for c in self.active_crises.values() 
                                if c.crisis_level == level])
                for level in CrisisLevel
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_active_crises(self) -> List[Dict[str, Any]]:
        """Get list of active crises."""
        return [asdict(crisis) for crisis in self.active_crises.values()]


# Foundation Epic Integration
async def setup_foundation_epic_crisis_management(event_bus: EventBus) -> CrisisEscalationManager:
    """Setup crisis management for Foundation Epic Phase 1 completion."""
    crisis_manager = CrisisEscalationManager()
    await crisis_manager.integrate_with_event_bus(event_bus)
    
    logger.info("Foundation Epic crisis management setup complete")
    return crisis_manager


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Crisis Escalation Manager")
    parser.add_argument("--start", action="store_true", help="Start crisis management")
    parser.add_argument("--status", action="store_true", help="Show crisis status") 
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    async def main():
        crisis_manager = CrisisEscalationManager(args.config or ".claude/crisis_config.json")
        
        if args.start:
            # Setup event bus integration
            from .event_bus import EventBus
            event_bus = EventBus()
            await event_bus.start_event_bus()
            await crisis_manager.integrate_with_event_bus(event_bus)
            
            print("Crisis escalation manager started. Press Ctrl+C to stop...")
            
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await event_bus.stop_event_bus()
                print("Crisis escalation manager stopped")
        
        elif args.status:
            status = crisis_manager.get_crisis_status()
            print(json.dumps(status, indent=2, default=str))
        
        else:
            print("Crisis Escalation Manager - Foundation Epic Integration")
            print("Real-time COORDINATION_CRISIS and DEADLINE_WARNING handling")
            print("")
            print("Crisis Levels: GREEN → YELLOW → ORANGE → RED → BLACK")
            print("Actions: LOG_ALERT, NOTIFY_AGENTS, ESCALATE_TO_PM, HUMAN_INTERVENTION")
    
    asyncio.run(main())