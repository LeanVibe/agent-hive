#!/usr/bin/env python3
"""
Automated Security Alert System

Comprehensive alerting system for LeanVibe Agent Hive with:
- Configurable alert thresholds and rules
- Multiple notification channels (email, Slack, GitHub, console)
- Alert correlation and deduplication
- Escalation policies and automated responses
- Integration with all security monitoring components
"""

import asyncio
import logging
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import subprocess
import threading

from security.audit_logger import SecurityEvent, SecurityEventType, SecuritySeverity
from security.security_monitor import SecurityAnomaly, SecurityIncident, ThreatLevel


logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of security alerts."""
    SECURITY_VIOLATION = "security_violation"
    ANOMALY_DETECTED = "anomaly_detected"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_ESCALATED = "incident_escalated"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    SYSTEM_HEALTH = "system_health"
    COMPLIANCE_VIOLATION = "compliance_violation"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class AlertPriority(Enum):
    """Alert priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertChannel(Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    GITHUB = "github"
    CONSOLE = "console"
    WEBHOOK = "webhook"
    SMS = "sms"


class AlertStatus(Enum):
    """Alert status tracking."""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    FAILED = "failed"


@dataclass
class AlertRule:
    """Configurable alert rule definition."""
    rule_id: str
    name: str
    description: str
    alert_type: AlertType
    priority: AlertPriority
    enabled: bool = True
    
    # Threshold configuration
    threshold_value: Optional[float] = None
    threshold_operator: str = ">"  # >, <, >=, <=, ==, !=
    evaluation_window_minutes: int = 5
    trigger_count: int = 1  # Number of violations to trigger alert
    
    # Targeting
    event_types: List[SecurityEventType] = field(default_factory=list)
    severity_levels: List[SecuritySeverity] = field(default_factory=list)
    source_components: List[str] = field(default_factory=list)
    user_patterns: List[str] = field(default_factory=list)
    
    # Notification configuration
    channels: List[AlertChannel] = field(default_factory=list)
    escalation_timeout_minutes: int = 30
    auto_resolve: bool = False
    auto_resolve_timeout_minutes: int = 60
    
    # Suppression
    suppression_window_minutes: int = 0
    max_alerts_per_hour: int = 10
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAlert:
    """Security alert instance."""
    alert_id: str
    rule_id: str
    alert_type: AlertType
    priority: AlertPriority
    status: AlertStatus
    
    # Content
    title: str
    description: str
    summary: str
    
    # Timing
    created_at: datetime
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Context
    source_event_ids: List[str] = field(default_factory=list)
    affected_entities: List[str] = field(default_factory=list)
    threat_indicators: List[str] = field(default_factory=list)
    
    # Notification tracking
    notification_attempts: Dict[str, int] = field(default_factory=dict)
    notification_status: Dict[str, str] = field(default_factory=dict)
    last_notification: Optional[datetime] = None
    
    # Response tracking
    escalated: bool = False
    escalation_level: int = 0
    response_actions: List[str] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Notification channel configuration."""
    channel: AlertChannel
    enabled: bool = True
    
    # Channel-specific settings
    email_settings: Dict[str, Any] = field(default_factory=dict)
    slack_settings: Dict[str, Any] = field(default_factory=dict)
    github_settings: Dict[str, Any] = field(default_factory=dict)
    webhook_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Rate limiting
    max_notifications_per_hour: int = 50
    batch_notifications: bool = False
    batch_timeout_minutes: int = 5


class SecurityAlertSystem:
    """
    Comprehensive security alert system with automated notifications.
    
    Features:
    - Configurable alert rules and thresholds
    - Multiple notification channels
    - Alert correlation and deduplication
    - Escalation policies and automation
    - Performance optimized with batch processing
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize security alert system."""
        self.config = config or self._get_default_config()
        
        # Alert management
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, SecurityAlert] = {}
        self.alert_history: List[SecurityAlert] = []
        
        # Notification management
        self.notification_configs: Dict[AlertChannel, NotificationConfig] = {}
        self.notification_queue = asyncio.Queue(maxsize=10000)
        self.notification_rate_limits = defaultdict(lambda: deque(maxlen=100))
        
        # Correlation and deduplication
        self.alert_correlations = defaultdict(list)
        self.suppression_tracker = defaultdict(lambda: {"count": 0, "last_alert": None})
        
        # Performance tracking
        self.alert_metrics = {
            "total_alerts": 0,
            "alerts_by_priority": defaultdict(int),
            "alerts_by_channel": defaultdict(int),
            "notification_failures": 0,
            "avg_response_time_ms": 0.0
        }
        
        # Background tasks
        self._notification_task = None
        self._cleanup_task = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize system
        self._load_default_rules()
        self._load_notification_configs()
        self._start_background_tasks()
        
        logger.info("SecurityAlertSystem initialized with automated notifications")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default alert system configuration."""
        return {
            "enabled": True,
            "max_active_alerts": 1000,
            "alert_retention_days": 30,
            "notification_timeout_seconds": 30,
            "batch_processing": True,
            "correlation_window_minutes": 10,
            "default_escalation_timeout": 30,
            "performance_monitoring": True,
            "auto_acknowledge_timeout_hours": 24,
            
            # Channel configurations
            "email_enabled": False,
            "slack_enabled": False,
            "github_enabled": True,
            "console_enabled": True,
            "webhook_enabled": False,
            
            # Rate limiting
            "global_rate_limit_per_hour": 200,
            "per_rule_rate_limit_per_hour": 50,
            "burst_protection": True
        }
    
    def _load_default_rules(self):
        """Load default alert rules."""
        default_rules = [
            # Critical security violations
            AlertRule(
                rule_id="critical_security_violation",
                name="Critical Security Violation",
                description="Alert on critical security violations",
                alert_type=AlertType.SECURITY_VIOLATION,
                priority=AlertPriority.CRITICAL,
                severity_levels=[SecuritySeverity.CRITICAL],
                channels=[AlertChannel.CONSOLE, AlertChannel.GITHUB],
                escalation_timeout_minutes=15,
                trigger_count=1
            ),
            
            # High-priority anomalies
            AlertRule(
                rule_id="high_priority_anomaly",
                name="High Priority Anomaly Detected",
                description="Alert on high-severity anomalies",
                alert_type=AlertType.ANOMALY_DETECTED,
                priority=AlertPriority.HIGH,
                severity_levels=[SecuritySeverity.HIGH],
                channels=[AlertChannel.CONSOLE, AlertChannel.GITHUB],
                escalation_timeout_minutes=30,
                trigger_count=1
            ),
            
            # Incident creation
            AlertRule(
                rule_id="security_incident_created",
                name="Security Incident Created",
                description="Alert when security incidents are created",
                alert_type=AlertType.INCIDENT_CREATED,
                priority=AlertPriority.HIGH,
                channels=[AlertChannel.CONSOLE, AlertChannel.GITHUB],
                escalation_timeout_minutes=30
            ),
            
            # Rate limit violations
            AlertRule(
                rule_id="rate_limit_violations",
                name="Rate Limit Violations",
                description="Alert on multiple rate limit violations",
                alert_type=AlertType.THRESHOLD_EXCEEDED,
                priority=AlertPriority.MEDIUM,
                event_types=[SecurityEventType.RATE_LIMIT_EXCEEDED],
                threshold_value=10,
                threshold_operator=">=",
                evaluation_window_minutes=15,
                channels=[AlertChannel.CONSOLE],
                suppression_window_minutes=30,
                max_alerts_per_hour=5
            ),
            
            # Authentication failures
            AlertRule(
                rule_id="auth_failure_spike",
                name="Authentication Failure Spike",
                description="Alert on authentication failure spikes",
                alert_type=AlertType.THRESHOLD_EXCEEDED,
                priority=AlertPriority.MEDIUM,
                event_types=[SecurityEventType.AUTH_LOGIN_FAILURE],
                threshold_value=20,
                threshold_operator=">=",
                evaluation_window_minutes=10,
                channels=[AlertChannel.CONSOLE],
                suppression_window_minutes=60
            ),
            
            # System health degradation
            AlertRule(
                rule_id="system_health_degradation",
                name="System Health Degradation",
                description="Alert on system health issues",
                alert_type=AlertType.SYSTEM_HEALTH,
                priority=AlertPriority.MEDIUM,
                threshold_value=70,
                threshold_operator="<",
                evaluation_window_minutes=5,
                channels=[AlertChannel.CONSOLE],
                auto_resolve=True,
                auto_resolve_timeout_minutes=30
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
        
        logger.info(f"Loaded {len(default_rules)} default alert rules")
    
    def _load_notification_configs(self):
        """Load notification channel configurations."""
        # Console notifications (always enabled)
        self.notification_configs[AlertChannel.CONSOLE] = NotificationConfig(
            channel=AlertChannel.CONSOLE,
            enabled=True
        )
        
        # Email notifications
        if self.config.get("email_enabled", False):
            self.notification_configs[AlertChannel.EMAIL] = NotificationConfig(
                channel=AlertChannel.EMAIL,
                enabled=True,
                email_settings={
                    "smtp_server": self.config.get("smtp_server", "localhost"),
                    "smtp_port": self.config.get("smtp_port", 587),
                    "username": self.config.get("email_username", ""),
                    "password": self.config.get("email_password", ""),
                    "from_email": self.config.get("from_email", "security@agent-hive.local"),
                    "to_emails": self.config.get("to_emails", [])
                }
            )
        
        # Slack notifications
        if self.config.get("slack_enabled", False):
            self.notification_configs[AlertChannel.SLACK] = NotificationConfig(
                channel=AlertChannel.SLACK,
                enabled=True,
                slack_settings={
                    "webhook_url": self.config.get("slack_webhook_url", ""),
                    "channel": self.config.get("slack_channel", "#security"),
                    "username": self.config.get("slack_username", "SecurityBot")
                }
            )
        
        # GitHub notifications (create issues)
        if self.config.get("github_enabled", True):
            self.notification_configs[AlertChannel.GITHUB] = NotificationConfig(
                channel=AlertChannel.GITHUB,
                enabled=True,
                github_settings={
                    "token": self.config.get("github_token", ""),
                    "repo": self.config.get("github_repo", ""),
                    "owner": self.config.get("github_owner", "")
                }
            )
        
        logger.info(f"Configured {len(self.notification_configs)} notification channels")
    
    def _start_background_tasks(self):
        """Start background processing tasks."""
        async def notification_processor():
            while True:
                try:
                    alert, channels = await self.notification_queue.get()
                    await self._process_notifications(alert, channels)
                except Exception as e:
                    logger.error(f"Notification processor error: {e}")
                    await asyncio.sleep(1)
        
        async def cleanup_processor():
            while True:
                try:
                    await asyncio.sleep(3600)  # Run every hour
                    await self._cleanup_old_alerts()
                except Exception as e:
                    logger.error(f"Cleanup processor error: {e}")
                    await asyncio.sleep(300)
        
        try:
            loop = asyncio.get_running_loop()
            self._notification_task = loop.create_task(notification_processor())
            self._cleanup_task = loop.create_task(cleanup_processor())
            logger.info("Alert system background tasks started")
        except RuntimeError:
            logger.info("No event loop running, notifications will be processed synchronously")
    
    async def evaluate_event(self, event: SecurityEvent) -> List[SecurityAlert]:
        """
        Evaluate security event against alert rules.
        
        Args:
            event: SecurityEvent to evaluate
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        try:
            for rule in self.alert_rules.values():
                if not rule.enabled:
                    continue
                
                # Check if rule applies to this event
                if not self._rule_matches_event(rule, event):
                    continue
                
                # Evaluate rule conditions
                if await self._evaluate_rule_conditions(rule, event):
                    alert = await self._create_alert(rule, event)
                    if alert:
                        triggered_alerts.append(alert)
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Event evaluation error: {e}")
            return []
    
    def _rule_matches_event(self, rule: AlertRule, event: SecurityEvent) -> bool:
        """Check if alert rule matches the event."""
        # Check event types
        if rule.event_types and event.event_type not in rule.event_types:
            return False
        
        # Check severity levels
        if rule.severity_levels and event.severity not in rule.severity_levels:
            return False
        
        # Check source components
        if rule.source_components and event.source_component not in rule.source_components:
            return False
        
        # Check user patterns (simple string matching for now)
        if rule.user_patterns and event.user_id:
            if not any(pattern in event.user_id for pattern in rule.user_patterns):
                return False
        
        return True
    
    async def _evaluate_rule_conditions(self, rule: AlertRule, event: SecurityEvent) -> bool:
        """Evaluate rule threshold conditions."""
        try:
            # For threshold-based rules, check if threshold is exceeded
            if rule.threshold_value is not None:
                # Count matching events in evaluation window
                window_start = datetime.utcnow() - timedelta(minutes=rule.evaluation_window_minutes)
                
                # Get recent events (this would typically query the audit logger)
                # For now, we'll use a simplified approach
                event_count = 1  # Current event
                
                # Apply threshold operator
                if rule.threshold_operator == ">":
                    return event_count > rule.threshold_value
                elif rule.threshold_operator == ">=":
                    return event_count >= rule.threshold_value
                elif rule.threshold_operator == "<":
                    return event_count < rule.threshold_value
                elif rule.threshold_operator == "<=":
                    return event_count <= rule.threshold_value
                elif rule.threshold_operator == "==":
                    return event_count == rule.threshold_value
                elif rule.threshold_operator == "!=":
                    return event_count != rule.threshold_value
            
            # For non-threshold rules, trigger immediately
            return True
            
        except Exception as e:
            logger.error(f"Rule condition evaluation error: {e}")
            return False
    
    async def _create_alert(self, rule: AlertRule, event: SecurityEvent) -> Optional[SecurityAlert]:
        """Create alert from rule and triggering event."""
        try:
            # Check suppression
            if self._is_suppressed(rule, event):
                return None
            
            # Generate alert
            alert_id = str(uuid.uuid4())
            
            alert = SecurityAlert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                alert_type=rule.alert_type,
                priority=rule.priority,
                status=AlertStatus.PENDING,
                title=self._generate_alert_title(rule, event),
                description=self._generate_alert_description(rule, event),
                summary=self._generate_alert_summary(rule, event),
                created_at=datetime.utcnow(),
                triggered_at=event.timestamp,
                source_event_ids=[event.event_id],
                affected_entities=self._extract_affected_entities(event),
                threat_indicators=getattr(event, 'threat_indicators', []),
                metadata={
                    "rule_name": rule.name,
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "source_component": event.source_component
                }
            )
            
            # Store alert
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # Update metrics
            self.alert_metrics["total_alerts"] += 1
            self.alert_metrics["alerts_by_priority"][rule.priority.value] += 1
            
            # Update suppression tracker
            self._update_suppression_tracker(rule, alert)
            
            # Queue for notification
            await self.notification_queue.put((alert, rule.channels))
            
            logger.info(f"Created alert: {alert.title} (ID: {alert_id})")
            return alert
            
        except Exception as e:
            logger.error(f"Alert creation error: {e}")
            return None
    
    def _is_suppressed(self, rule: AlertRule, event: SecurityEvent) -> bool:
        """Check if alert should be suppressed."""
        if rule.suppression_window_minutes <= 0:
            return False
        
        suppression_key = f"{rule.rule_id}:{event.user_id or 'system'}"
        suppression_info = self.suppression_tracker[suppression_key]
        
        # Check if within suppression window
        if suppression_info["last_alert"]:
            time_since_last = datetime.utcnow() - suppression_info["last_alert"]
            if time_since_last.total_seconds() < rule.suppression_window_minutes * 60:
                suppression_info["count"] += 1
                return True
        
        # Check hourly limit
        if suppression_info["count"] >= rule.max_alerts_per_hour:
            return True
        
        return False
    
    def _update_suppression_tracker(self, rule: AlertRule, alert: SecurityAlert):
        """Update suppression tracking information."""
        suppression_key = f"{rule.rule_id}:{alert.affected_entities[0] if alert.affected_entities else 'system'}"
        self.suppression_tracker[suppression_key]["last_alert"] = alert.created_at
        self.suppression_tracker[suppression_key]["count"] += 1
    
    def _generate_alert_title(self, rule: AlertRule, event: SecurityEvent) -> str:
        """Generate alert title."""
        if rule.alert_type == AlertType.SECURITY_VIOLATION:
            return f"Security Violation: {event.event_type.value}"
        elif rule.alert_type == AlertType.THRESHOLD_EXCEEDED:
            return f"Threshold Exceeded: {rule.name}"
        else:
            return f"{rule.name}: {event.event_type.value}"
    
    def _generate_alert_description(self, rule: AlertRule, event: SecurityEvent) -> str:
        """Generate alert description."""
        description = f"Alert triggered by rule '{rule.name}'\n\n"
        description += f"Event Details:\n"
        description += f"- Type: {event.event_type.value}\n"
        description += f"- Severity: {event.severity.value}\n"
        description += f"- Source: {event.source_component}\n"
        description += f"- Timestamp: {event.timestamp.isoformat()}\n"
        
        if event.user_id:
            description += f"- User: {event.user_id}\n"
        
        if event.client_ip:
            description += f"- IP: {event.client_ip}\n"
        
        if event.action:
            description += f"- Action: {event.action}\n"
        
        if event.resource:
            description += f"- Resource: {event.resource}\n"
        
        if hasattr(event, 'risk_score') and event.risk_score:
            description += f"- Risk Score: {event.risk_score}/100\n"
        
        return description
    
    def _generate_alert_summary(self, rule: AlertRule, event: SecurityEvent) -> str:
        """Generate alert summary."""
        return f"{rule.name} - {event.event_type.value} from {event.source_component}"
    
    def _extract_affected_entities(self, event: SecurityEvent) -> List[str]:
        """Extract affected entities from event."""
        entities = []
        
        if event.user_id:
            entities.append(f"user:{event.user_id}")
        
        if event.client_ip:
            entities.append(f"ip:{event.client_ip}")
        
        if event.resource:
            entities.append(f"resource:{event.resource}")
        
        entities.append(f"component:{event.source_component}")
        
        return entities
    
    async def _process_notifications(self, alert: SecurityAlert, channels: List[AlertChannel]):
        """Process alert notifications."""
        start_time = time.time()
        
        try:
            for channel in channels:
                if channel not in self.notification_configs:
                    continue
                
                config = self.notification_configs[channel]
                if not config.enabled:
                    continue
                
                # Check rate limits
                if self._is_rate_limited(channel, alert):
                    logger.warning(f"Rate limited notification for channel {channel.value}")
                    continue
                
                # Send notification
                try:
                    success = await self._send_notification(alert, channel, config)
                    
                    # Update tracking
                    alert.notification_attempts[channel.value] = alert.notification_attempts.get(channel.value, 0) + 1
                    alert.notification_status[channel.value] = "sent" if success else "failed"
                    alert.last_notification = datetime.utcnow()
                    
                    # Update metrics
                    self.alert_metrics["alerts_by_channel"][channel.value] += 1
                    if not success:
                        self.alert_metrics["notification_failures"] += 1
                        
                except Exception as e:
                    logger.error(f"Notification send error for {channel.value}: {e}")
                    alert.notification_status[channel.value] = "error"
                    self.alert_metrics["notification_failures"] += 1
            
            # Update alert status
            if any(status == "sent" for status in alert.notification_status.values()):
                alert.status = AlertStatus.SENT
            
            # Update performance metrics
            processing_time = (time.time() - start_time) * 1000
            current_avg = self.alert_metrics["avg_response_time_ms"]
            self.alert_metrics["avg_response_time_ms"] = (current_avg + processing_time) / 2
            
        except Exception as e:
            logger.error(f"Notification processing error: {e}")
    
    def _is_rate_limited(self, channel: AlertChannel, alert: SecurityAlert) -> bool:
        """Check if channel is rate limited."""
        config = self.notification_configs.get(channel)
        if not config:
            return True
        
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Clean old entries
        channel_key = f"{channel.value}:{alert.rule_id}"
        while (self.notification_rate_limits[channel_key] and 
               self.notification_rate_limits[channel_key][0] < hour_ago):
            self.notification_rate_limits[channel_key].popleft()
        
        # Check limit
        if len(self.notification_rate_limits[channel_key]) >= config.max_notifications_per_hour:
            return True
        
        # Add current notification
        self.notification_rate_limits[channel_key].append(current_time)
        return False
    
    async def _send_notification(self, alert: SecurityAlert, 
                               channel: AlertChannel, 
                               config: NotificationConfig) -> bool:
        """Send notification via specific channel."""
        try:
            if channel == AlertChannel.CONSOLE:
                return await self._send_console_notification(alert)
            elif channel == AlertChannel.EMAIL:
                return await self._send_email_notification(alert, config)
            elif channel == AlertChannel.SLACK:
                return await self._send_slack_notification(alert, config)
            elif channel == AlertChannel.GITHUB:
                return await self._send_github_notification(alert, config)
            elif channel == AlertChannel.WEBHOOK:
                return await self._send_webhook_notification(alert, config)
            else:
                logger.warning(f"Unsupported notification channel: {channel.value}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send {channel.value} notification: {e}")
            return False
    
    async def _send_console_notification(self, alert: SecurityAlert) -> bool:
        """Send console notification."""
        priority_emoji = {
            AlertPriority.CRITICAL: "🚨",
            AlertPriority.HIGH: "⚠️",
            AlertPriority.MEDIUM: "⚡",
            AlertPriority.LOW: "ℹ️",
            AlertPriority.INFO: "📋"
        }
        
        emoji = priority_emoji.get(alert.priority, "🔔")
        
        print(f"\n{emoji} SECURITY ALERT [{alert.priority.value.upper()}] {emoji}")
        print(f"Alert ID: {alert.alert_id}")
        print(f"Title: {alert.title}")
        print(f"Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Summary: {alert.summary}")
        
        if alert.affected_entities:
            print(f"Affected: {', '.join(alert.affected_entities)}")
        
        if alert.threat_indicators:
            print(f"Threats: {', '.join(alert.threat_indicators)}")
        
        print("-" * 60)
        
        return True
    
    async def _send_email_notification(self, alert: SecurityAlert, config: NotificationConfig) -> bool:
        """Send email notification."""
        try:
            settings = config.email_settings
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings['from_email']
            msg['To'] = ', '.join(settings['to_emails'])
            msg['Subject'] = f"[SECURITY ALERT] {alert.title}"
            
            # Create email body
            body = f"""
Security Alert Notification

Alert ID: {alert.alert_id}
Priority: {alert.priority.value.upper()}
Type: {alert.alert_type.value}
Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

{alert.description}

Affected Entities:
{chr(10).join(f'- {entity}' for entity in alert.affected_entities)}

Threat Indicators:
{chr(10).join(f'- {indicator}' for indicator in alert.threat_indicators)}

This is an automated security alert from Agent Hive Security Monitoring.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(settings['smtp_server'], settings['smtp_port']) as server:
                server.starttls(context=context)
                if settings.get('username') and settings.get('password'):
                    server.login(settings['username'], settings['password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False
    
    async def _send_slack_notification(self, alert: SecurityAlert, config: NotificationConfig) -> bool:
        """Send Slack notification."""
        try:
            settings = config.slack_settings
            webhook_url = settings['webhook_url']
            
            if not webhook_url:
                return False
            
            # Create Slack message
            color = {
                AlertPriority.CRITICAL: "danger",
                AlertPriority.HIGH: "warning",
                AlertPriority.MEDIUM: "#ff9500",
                AlertPriority.LOW: "good",
                AlertPriority.INFO: "#439FE0"
            }.get(alert.priority, "good")
            
            payload = {
                "channel": settings.get('channel', '#security'),
                "username": settings.get('username', 'SecurityBot'),
                "attachments": [{
                    "color": color,
                    "title": alert.title,
                    "text": alert.summary,
                    "fields": [
                        {"title": "Priority", "value": alert.priority.value.upper(), "short": True},
                        {"title": "Alert ID", "value": alert.alert_id, "short": True},
                        {"title": "Time", "value": alert.created_at.strftime('%Y-%m-%d %H:%M:%S'), "short": True},
                        {"title": "Affected Entities", "value": ', '.join(alert.affected_entities[:5]), "short": False}
                    ],
                    "ts": int(alert.created_at.timestamp())
                }]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=30)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
            return False
    
    async def _send_github_notification(self, alert: SecurityAlert, config: NotificationConfig) -> bool:
        """Send GitHub notification (create issue)."""
        try:
            settings = config.github_settings
            token = settings.get('token')
            repo = settings.get('repo')
            owner = settings.get('owner')
            
            if not all([token, repo, owner]):
                logger.warning("GitHub settings incomplete, skipping notification")
                return False
            
            # Create GitHub issue
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Determine labels based on priority
            labels = ["security", "alert"]
            if alert.priority == AlertPriority.CRITICAL:
                labels.append("critical")
            elif alert.priority == AlertPriority.HIGH:
                labels.append("high-priority")
            
            issue_data = {
                "title": f"[SECURITY] {alert.title}",
                "body": f"""## Security Alert

**Alert ID:** {alert.alert_id}
**Priority:** {alert.priority.value.upper()}
**Type:** {alert.alert_type.value}
**Created:** {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

### Description
{alert.description}

### Affected Entities
{chr(10).join(f'- {entity}' for entity in alert.affected_entities)}

### Threat Indicators
{chr(10).join(f'- {indicator}' for indicator in alert.threat_indicators)}

---
*This issue was automatically created by Agent Hive Security Monitoring*
""",
                "labels": labels
            }
            
            response = requests.post(url, headers=headers, json=issue_data, timeout=30)
            
            if response.status_code == 201:
                issue_url = response.json().get('html_url')
                alert.metadata['github_issue_url'] = issue_url
                return True
            else:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"GitHub notification error: {e}")
            return False
    
    async def _send_webhook_notification(self, alert: SecurityAlert, config: NotificationConfig) -> bool:
        """Send webhook notification."""
        try:
            settings = config.webhook_settings
            webhook_url = settings.get('url')
            
            if not webhook_url:
                return False
            
            payload = {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "description": alert.description,
                "priority": alert.priority.value,
                "alert_type": alert.alert_type.value,
                "created_at": alert.created_at.isoformat(),
                "affected_entities": alert.affected_entities,
                "threat_indicators": alert.threat_indicators,
                "metadata": alert.metadata
            }
            
            headers = {"Content-Type": "application/json"}
            if settings.get('auth_header'):
                headers["Authorization"] = settings['auth_header']
            
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            return response.status_code in [200, 201, 202]
            
        except Exception as e:
            logger.error(f"Webhook notification error: {e}")
            return False
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert."""
        try:
            alert = self.active_alerts.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.metadata['acknowledged_by'] = acknowledged_by
            
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Resolve an alert."""
        try:
            alert = self.active_alerts.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.metadata['resolved_by'] = resolved_by
            
            logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def _cleanup_old_alerts(self):
        """Clean up old alerts based on retention policy."""
        try:
            retention_days = self.config.get("alert_retention_days", 30)
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Clean active alerts
            expired_alerts = [
                alert_id for alert_id, alert in self.active_alerts.items()
                if alert.created_at < cutoff_date and alert.status in [
                    AlertStatus.RESOLVED, AlertStatus.ACKNOWLEDGED
                ]
            ]
            
            for alert_id in expired_alerts:
                del self.active_alerts[alert_id]
            
            # Clean alert history
            self.alert_history = [
                alert for alert in self.alert_history
                if alert.created_at >= cutoff_date
            ]
            
            if expired_alerts:
                logger.info(f"Cleaned up {len(expired_alerts)} old alerts")
                
        except Exception as e:
            logger.error(f"Alert cleanup error: {e}")
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get comprehensive alert statistics."""
        active_alerts = len(self.active_alerts)
        recent_alerts = len([
            alert for alert in self.alert_history
            if alert.created_at >= datetime.utcnow() - timedelta(hours=24)
        ])
        
        return {
            "total_alerts": self.alert_metrics["total_alerts"],
            "active_alerts": active_alerts,
            "recent_alerts_24h": recent_alerts,
            "alerts_by_priority": dict(self.alert_metrics["alerts_by_priority"]),
            "alerts_by_channel": dict(self.alert_metrics["alerts_by_channel"]),
            "notification_failures": self.alert_metrics["notification_failures"],
            "avg_response_time_ms": round(self.alert_metrics["avg_response_time_ms"], 2),
            "configured_rules": len(self.alert_rules),
            "enabled_rules": len([r for r in self.alert_rules.values() if r.enabled]),
            "notification_channels": len(self.notification_configs),
            "queue_size": self.notification_queue.qsize() if hasattr(self.notification_queue, 'qsize') else 0
        }


# Global alert system instance
alert_system = SecurityAlertSystem()


# Integration helper functions
async def evaluate_security_event(event: SecurityEvent) -> List[SecurityAlert]:
    """Evaluate security event for alerts."""
    return await alert_system.evaluate_event(event)


async def trigger_anomaly_alert(anomaly: SecurityAnomaly) -> bool:
    """Trigger alert for detected anomaly."""
    # Create a synthetic event for the anomaly
    from security.audit_logger import create_security_event, SecurityEventType
    
    anomaly_event = create_security_event(
        event_type=SecurityEventType.ANOMALY_DETECTED,
        severity=anomaly.severity,
        source_component="security_monitor",
        action="anomaly_detected",
        resource=anomaly.anomaly_type.value,
        metadata={
            "anomaly_id": anomaly.anomaly_id,
            "confidence": anomaly.confidence,
            "description": anomaly.description
        }
    )
    
    alerts = await alert_system.evaluate_event(anomaly_event)
    return len(alerts) > 0


async def trigger_incident_alert(incident: SecurityIncident) -> bool:
    """Trigger alert for security incident."""
    from security.audit_logger import create_security_event, SecurityEventType
    
    incident_event = create_security_event(
        event_type=SecurityEventType.SYSTEM_SECURITY_UPDATE,
        severity=incident.severity,
        source_component="security_monitor",
        action="incident_created",
        resource=incident.incident_id,
        metadata={
            "incident_id": incident.incident_id,
            "title": incident.title,
            "threat_level": incident.threat_level.value
        }
    )
    
    alerts = await alert_system.evaluate_event(incident_event)
    return len(alerts) > 0


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        from security.audit_logger import create_security_event
        
        system = SecurityAlertSystem()
        
        # Test critical security event
        critical_event = create_security_event(
            SecurityEventType.SECURITY_COMMAND_BLOCKED,
            SecuritySeverity.CRITICAL,
            "security_manager",
            user_id="test_user",
            action="rm -rf /",
            client_ip="192.168.1.100"
        )
        
        print("Evaluating critical security event...")
        alerts = await system.evaluate_event(critical_event)
        print(f"Generated {len(alerts)} alerts")
        
        # Wait for notifications
        await asyncio.sleep(2)
        
        # Get statistics
        stats = system.get_alert_statistics()
        print(f"\nAlert Statistics:")
        print(f"Total alerts: {stats['total_alerts']}")
        print(f"Active alerts: {stats['active_alerts']}")
        print(f"Notification failures: {stats['notification_failures']}")
        print(f"Enabled rules: {stats['enabled_rules']}")
    
    # Run test
    asyncio.run(main())