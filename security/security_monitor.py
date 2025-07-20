#!/usr/bin/env python3
"""
Real-Time Security Monitor

Advanced security monitoring system for LeanVibe Agent Hive with:
- Real-time event processing and correlation
- Machine learning-based anomaly detection
- Behavioral analysis and threat intelligence
- Automated incident response and escalation
- Integration with all security components
"""

import asyncio
import logging
import time
import uuid
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque, Counter
import threading
from concurrent.futures import ThreadPoolExecutor
import math

from security.audit_logger import (
    SecurityEvent, SecurityEventType, SecuritySeverity, 
    audit_logger, create_security_event
)


logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classifications."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Security incident status."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class AnomalyType(Enum):
    """Types of security anomalies."""
    RATE_ANOMALY = "rate_anomaly"
    PATTERN_ANOMALY = "pattern_anomaly"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    TIME_ANOMALY = "time_anomaly"
    PRIVILEGE_ANOMALY = "privilege_anomaly"
    ACCESS_ANOMALY = "access_anomaly"


@dataclass
class SecurityAnomaly:
    """Detected security anomaly."""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: SecuritySeverity
    confidence: float  # 0.0 - 1.0
    detected_at: datetime
    
    # Anomaly details
    description: str
    affected_entities: List[str]
    detection_rules: List[str]
    baseline_data: Dict[str, Any]
    current_data: Dict[str, Any]
    
    # Context information
    related_events: List[str]  # Event IDs
    threat_indicators: List[str]
    risk_score: int  # 0-100
    
    # Response information
    auto_response_taken: bool = False
    response_actions: List[str] = field(default_factory=list)
    requires_human_review: bool = True
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityIncident:
    """Security incident tracking."""
    incident_id: str
    title: str
    description: str
    severity: SecuritySeverity
    status: IncidentStatus
    threat_level: ThreatLevel
    incident_type: str
    
    # Timing
    created_at: datetime
    first_seen: datetime
    last_seen: datetime
    
    # Optional fields with defaults
    resolved_at: Optional[datetime] = None
    attack_vector: Optional[str] = None
    affected_systems: List[str] = field(default_factory=list)
    affected_users: List[str] = field(default_factory=list)
    
    # Evidence
    related_events: List[str] = field(default_factory=list)
    related_anomalies: List[str] = field(default_factory=list)
    indicators_of_compromise: List[str] = field(default_factory=list)
    
    # Response
    response_actions: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    escalated: bool = False
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserBehaviorProfile:
    """User behavior profile for anomaly detection."""
    user_id: str
    created_at: datetime
    last_updated: datetime
    
    # Access patterns
    typical_login_hours: Set[int] = field(default_factory=set)
    typical_ip_ranges: Set[str] = field(default_factory=set)
    typical_user_agents: Set[str] = field(default_factory=set)
    typical_endpoints: Set[str] = field(default_factory=set)
    
    # Activity patterns
    avg_requests_per_hour: float = 0.0
    max_requests_per_hour: int = 0
    typical_session_duration_minutes: float = 0.0
    
    # Permission patterns
    typical_permissions: Set[str] = field(default_factory=set)
    typical_roles: Set[str] = field(default_factory=set)
    privilege_escalation_attempts: int = 0
    
    # Risk indicators
    security_violations: int = 0
    failed_auth_attempts: int = 0
    rate_limit_violations: int = 0
    
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityMonitor:
    """
    Real-time security monitoring system with advanced threat detection.
    
    Features:
    - Real-time event stream processing
    - Machine learning-based anomaly detection
    - User behavior profiling and analysis
    - Automated incident creation and tracking
    - Threat intelligence correlation
    - Automated response and escalation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize security monitor."""
        self.config = config or self._get_default_config()
        
        # Event processing
        self.event_stream = asyncio.Queue(maxsize=50000)
        self.processing_pool = ThreadPoolExecutor(max_workers=4)
        
        # Detection engines
        self.anomaly_detectors = []
        self.correlation_rules = []
        self.threat_indicators = set()
        
        # Tracking and state
        self.user_profiles: Dict[str, UserBehaviorProfile] = {}
        self.active_incidents: Dict[str, SecurityIncident] = {}
        self.detected_anomalies: Dict[str, SecurityAnomaly] = {}
        
        # Real-time metrics
        self.metrics = defaultdict(int)
        self.event_rates = defaultdict(lambda: deque(maxlen=60))  # Per minute
        self.baseline_stats = defaultdict(dict)
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
        self.incident_callbacks: List[Callable] = []
        
        # Performance tracking
        self.processing_times = deque(maxlen=1000)
        self.detection_accuracy = {"true_positives": 0, "false_positives": 0}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Background tasks
        self._monitor_task = None
        self._analytics_task = None
        
        # Initialize detection systems
        self._initialize_detection_engines()
        self._load_threat_intelligence()
        
        # Start monitoring
        self._start_monitoring_tasks()
        
        logger.info("SecurityMonitor initialized with advanced threat detection")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default monitor configuration."""
        return {
            "real_time_processing": True,
            "anomaly_detection_enabled": True,
            "behavioral_analysis_enabled": True,
            "auto_incident_creation": True,
            "auto_response_enabled": False,
            
            # Detection thresholds
            "anomaly_threshold": 0.7,
            "incident_auto_create_threshold": 0.8,
            "behavioral_deviation_threshold": 2.0,
            
            # Rate limiting
            "max_events_per_minute": 1000,
            "rate_spike_threshold": 5.0,
            
            # Behavioral analysis
            "user_profile_learning_period_days": 7,
            "behavioral_baseline_hours": 24,
            "min_events_for_profile": 50,
            
            # Incident management
            "auto_escalate_critical": True,
            "auto_escalate_threshold_minutes": 30,
            "incident_correlation_window_minutes": 15,
            
            # Performance
            "batch_size": 100,
            "processing_timeout_seconds": 30,
            "cleanup_interval_hours": 24,
            
            # Retention
            "incident_retention_days": 365,
            "anomaly_retention_days": 90,
            "profile_retention_days": 180
        }
    
    def _initialize_detection_engines(self):
        """Initialize anomaly detection engines."""
        # Rate-based anomaly detection
        self.anomaly_detectors.append(self._detect_rate_anomalies)
        
        # Pattern-based detection
        self.anomaly_detectors.append(self._detect_pattern_anomalies)
        
        # Behavioral anomaly detection
        self.anomaly_detectors.append(self._detect_behavioral_anomalies)
        
        # Geographic anomaly detection
        self.anomaly_detectors.append(self._detect_geographic_anomalies)
        
        # Time-based anomaly detection
        self.anomaly_detectors.append(self._detect_time_anomalies)
        
        # Privilege escalation detection
        self.anomaly_detectors.append(self._detect_privilege_anomalies)
        
        logger.info(f"Initialized {len(self.anomaly_detectors)} anomaly detection engines")
    
    def _load_threat_intelligence(self):
        """Load threat intelligence indicators."""
        # Known malicious patterns
        malicious_patterns = [
            "rm -rf",
            "DROP TABLE",
            "UNION SELECT",
            "<script>",
            "javascript:",
            "cmd.exe",
            "/etc/passwd",
            "../../../",
            "base64_decode",
            "eval(",
            "exec(",
            "system(",
            "shell_exec"
        ]
        
        self.threat_indicators.update(malicious_patterns)
        
        # Known attack vectors
        attack_vectors = [
            "sql_injection",
            "xss",
            "command_injection",
            "path_traversal",
            "privilege_escalation",
            "brute_force",
            "session_hijacking",
            "csrf"
        ]
        
        self.threat_indicators.update(attack_vectors)
        
        logger.info(f"Loaded {len(self.threat_indicators)} threat indicators")
    
    async def process_security_event(self, event: SecurityEvent) -> List[SecurityAnomaly]:
        """
        Process security event through all detection engines.
        
        Args:
            event: SecurityEvent to process
            
        Returns:
            List of detected anomalies
        """
        start_time = time.time()
        anomalies = []
        
        try:
            # Queue event for real-time processing
            await self.event_stream.put(event)
            
            # Update metrics
            self._update_metrics(event)
            
            # Update user profiles
            await self._update_user_profile(event)
            
            # Run anomaly detection
            for detector in self.anomaly_detectors:
                try:
                    detected = await detector(event)
                    if detected:
                        anomalies.extend(detected if isinstance(detected, list) else [detected])
                except Exception as e:
                    logger.error(f"Anomaly detector error: {e}")
            
            # Process detected anomalies
            for anomaly in anomalies:
                await self._handle_anomaly(anomaly)
            
            # Check for incident creation/update
            if anomalies:
                await self._correlate_and_create_incidents(event, anomalies)
            
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Event processing error: {e}")
            return []
    
    def _update_metrics(self, event: SecurityEvent):
        """Update real-time metrics."""
        with self._lock:
            # General metrics
            self.metrics["total_events"] += 1
            self.metrics[f"events_{event.event_type.value}"] += 1
            self.metrics[f"severity_{event.severity.value}"] += 1
            
            # Rate tracking (per minute)
            current_minute = int(time.time() // 60)
            self.event_rates["total"].append(current_minute)
            self.event_rates[event.event_type.value].append(current_minute)
            
            # User metrics
            if event.user_id:
                self.metrics[f"user_events_{event.user_id}"] += 1
            
            # Source metrics
            self.metrics[f"source_{event.source_component}"] += 1
            
            # IP metrics
            if event.client_ip:
                self.metrics[f"ip_events_{event.client_ip}"] += 1
    
    async def _update_user_profile(self, event: SecurityEvent):
        """Update user behavioral profile."""
        if not event.user_id or not self.config.get("behavioral_analysis_enabled", True):
            return
        
        user_id = event.user_id
        
        # Get or create profile
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserBehaviorProfile(
                user_id=user_id,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
        
        profile = self.user_profiles[user_id]
        profile.last_updated = datetime.utcnow()
        
        # Update access patterns
        if event.timestamp:
            profile.typical_login_hours.add(event.timestamp.hour)
        
        if event.client_ip:
            # Store IP subnet for pattern recognition
            ip_parts = event.client_ip.split('.')
            if len(ip_parts) >= 3:
                subnet = '.'.join(ip_parts[:3]) + '.0/24'
                profile.typical_ip_ranges.add(subnet)
        
        if event.user_agent:
            profile.typical_user_agents.add(event.user_agent[:100])  # Limit length
        
        if event.resource:
            profile.typical_endpoints.add(event.resource)
        
        # Update activity metrics
        self._update_profile_activity_metrics(profile, event)
        
        # Update security metrics
        if event.event_type in [
            SecurityEventType.AUTH_LOGIN_FAILURE,
            SecurityEventType.AUTHZ_PERMISSION_DENIED
        ]:
            profile.failed_auth_attempts += 1
        
        if event.event_type in [
            SecurityEventType.SECURITY_COMMAND_BLOCKED,
            SecurityEventType.SECURITY_INJECTION_ATTEMPT
        ]:
            profile.security_violations += 1
        
        if event.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
            profile.rate_limit_violations += 1
    
    def _update_profile_activity_metrics(self, profile: UserBehaviorProfile, event: SecurityEvent):
        """Update user activity metrics."""
        # Count events in the last hour
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        hour_events = sum(1 for e in self.event_rates.get(f"user_{profile.user_id}", [])
                         if e >= current_hour.timestamp() - 3600)
        
        # Update average
        if profile.avg_requests_per_hour == 0:
            profile.avg_requests_per_hour = hour_events
        else:
            # Exponential moving average
            alpha = 0.1
            profile.avg_requests_per_hour = (alpha * hour_events + 
                                           (1 - alpha) * profile.avg_requests_per_hour)
        
        profile.max_requests_per_hour = max(profile.max_requests_per_hour, hour_events)
    
    async def _detect_rate_anomalies(self, event: SecurityEvent) -> List[SecurityAnomaly]:
        """Detect rate-based anomalies."""
        anomalies = []
        
        try:
            current_minute = int(time.time() // 60)
            
            # Check global event rate
            global_rate = len([t for t in self.event_rates["total"] 
                              if t >= current_minute - 5])  # Last 5 minutes
            
            if global_rate > self.config.get("max_events_per_minute", 1000):
                anomaly = SecurityAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.RATE_ANOMALY,
                    severity=SecuritySeverity.HIGH,
                    confidence=0.9,
                    detected_at=datetime.utcnow(),
                    description=f"Global event rate spike: {global_rate} events/5min",
                    affected_entities=["system"],
                    detection_rules=["global_rate_limit"],
                    baseline_data={"normal_rate": 100},
                    current_data={"current_rate": global_rate},
                    related_events=[event.event_id],
                    threat_indicators=["dos_attack", "system_overload"],
                    risk_score=85
                )
                anomalies.append(anomaly)
            
            # Check user-specific rate
            if event.user_id:
                user_rate = len([t for t in self.event_rates.get(f"user_{event.user_id}", [])
                               if t >= current_minute - 5])
                
                profile = self.user_profiles.get(event.user_id)
                if profile and user_rate > profile.max_requests_per_hour * 1.5:
                    anomaly = SecurityAnomaly(
                        anomaly_id=str(uuid.uuid4()),
                        anomaly_type=AnomalyType.RATE_ANOMALY,
                        severity=SecuritySeverity.MEDIUM,
                        confidence=0.8,
                        detected_at=datetime.utcnow(),
                        description=f"User rate anomaly: {user_rate} events/5min",
                        affected_entities=[event.user_id],
                        detection_rules=["user_rate_anomaly"],
                        baseline_data={"normal_rate": profile.avg_requests_per_hour},
                        current_data={"current_rate": user_rate},
                        related_events=[event.event_id],
                        threat_indicators=["account_abuse"],
                        risk_score=60
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Rate anomaly detection error: {e}")
            return []
    
    async def _detect_pattern_anomalies(self, event: SecurityEvent) -> List[SecurityAnomaly]:
        """Detect pattern-based anomalies."""
        anomalies = []
        
        try:
            # Check for threat indicators in event data
            threat_matches = []
            event_text = f"{event.action or ''} {event.resource or ''} {event.metadata}"
            
            for indicator in self.threat_indicators:
                if indicator.lower() in event_text.lower():
                    threat_matches.append(indicator)
            
            if threat_matches:
                severity = SecuritySeverity.HIGH if len(threat_matches) > 2 else SecuritySeverity.MEDIUM
                
                anomaly = SecurityAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.PATTERN_ANOMALY,
                    severity=severity,
                    confidence=0.9,
                    detected_at=datetime.utcnow(),
                    description=f"Threat pattern detected: {', '.join(threat_matches)}",
                    affected_entities=[event.user_id or "unknown"],
                    detection_rules=["threat_indicator_match"],
                    baseline_data={"known_threats": list(self.threat_indicators)},
                    current_data={"matched_threats": threat_matches},
                    related_events=[event.event_id],
                    threat_indicators=threat_matches,
                    risk_score=80 if len(threat_matches) > 2 else 60
                )
                anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Pattern anomaly detection error: {e}")
            return []
    
    async def _detect_behavioral_anomalies(self, event: SecurityEvent) -> List[SecurityAnomaly]:
        """Detect behavioral anomalies based on user profiles."""
        anomalies = []
        
        try:
            if not event.user_id:
                return anomalies
            
            profile = self.user_profiles.get(event.user_id)
            if not profile:
                return anomalies
            
            # Check access time anomaly
            if (event.timestamp and 
                event.timestamp.hour not in profile.typical_login_hours and
                len(profile.typical_login_hours) > 5):
                
                anomaly = SecurityAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.BEHAVIORAL_ANOMALY,
                    severity=SecuritySeverity.MEDIUM,
                    confidence=0.7,
                    detected_at=datetime.utcnow(),
                    description=f"Unusual access time: {event.timestamp.hour}:00",
                    affected_entities=[event.user_id],
                    detection_rules=["unusual_access_time"],
                    baseline_data={"typical_hours": list(profile.typical_login_hours)},
                    current_data={"access_hour": event.timestamp.hour},
                    related_events=[event.event_id],
                    threat_indicators=["unusual_behavior"],
                    risk_score=40
                )
                anomalies.append(anomaly)
            
            # Check IP address anomaly
            if event.client_ip and profile.typical_ip_ranges:
                ip_parts = event.client_ip.split('.')
                if len(ip_parts) >= 3:
                    current_subnet = '.'.join(ip_parts[:3]) + '.0/24'
                    if current_subnet not in profile.typical_ip_ranges:
                        anomaly = SecurityAnomaly(
                            anomaly_id=str(uuid.uuid4()),
                            anomaly_type=AnomalyType.GEOGRAPHIC_ANOMALY,
                            severity=SecuritySeverity.MEDIUM,
                            confidence=0.8,
                            detected_at=datetime.utcnow(),
                            description=f"Access from unusual IP: {event.client_ip}",
                            affected_entities=[event.user_id],
                            detection_rules=["unusual_ip_access"],
                            baseline_data={"typical_subnets": list(profile.typical_ip_ranges)},
                            current_data={"current_ip": event.client_ip},
                            related_events=[event.event_id],
                            threat_indicators=["geographic_anomaly"],
                            risk_score=50
                        )
                        anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Behavioral anomaly detection error: {e}")
            return []
    
    async def _detect_geographic_anomalies(self, event: SecurityEvent) -> List[SecurityAnomaly]:
        """Detect geographic/location anomalies."""
        # Placeholder for geo-IP analysis
        # In production, would integrate with geo-IP database
        return []
    
    async def _detect_time_anomalies(self, event: SecurityEvent) -> List[SecurityAnomaly]:
        """Detect time-based anomalies."""
        anomalies = []
        
        try:
            # Check for off-hours activity
            if event.timestamp:
                hour = event.timestamp.hour
                
                # Define business hours (9 AM - 6 PM)
                if (hour < 9 or hour > 18) and event.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                    anomaly = SecurityAnomaly(
                        anomaly_id=str(uuid.uuid4()),
                        anomaly_type=AnomalyType.TIME_ANOMALY,
                        severity=SecuritySeverity.MEDIUM,
                        confidence=0.6,
                        detected_at=datetime.utcnow(),
                        description=f"High-severity event outside business hours: {hour}:00",
                        affected_entities=[event.user_id or "system"],
                        detection_rules=["off_hours_activity"],
                        baseline_data={"business_hours": "9-18"},
                        current_data={"event_hour": hour},
                        related_events=[event.event_id],
                        threat_indicators=["off_hours_activity"],
                        risk_score=35
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Time anomaly detection error: {e}")
            return []
    
    async def _detect_privilege_anomalies(self, event: SecurityEvent) -> List[SecurityAnomaly]:
        """Detect privilege escalation anomalies."""
        anomalies = []
        
        try:
            # Check for privilege escalation attempts
            if event.event_type == SecurityEventType.AUTHZ_PRIVILEGE_ESCALATION:
                anomaly = SecurityAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.PRIVILEGE_ANOMALY,
                    severity=SecuritySeverity.HIGH,
                    confidence=0.95,
                    detected_at=datetime.utcnow(),
                    description="Privilege escalation attempt detected",
                    affected_entities=[event.user_id or "unknown"],
                    detection_rules=["privilege_escalation"],
                    baseline_data={},
                    current_data={"event_type": event.event_type.value},
                    related_events=[event.event_id],
                    threat_indicators=["privilege_escalation"],
                    risk_score=90,
                    requires_human_review=True
                )
                anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Privilege anomaly detection error: {e}")
            return []
    
    async def _handle_anomaly(self, anomaly: SecurityAnomaly):
        """Handle detected anomaly."""
        try:
            # Store anomaly
            self.detected_anomalies[anomaly.anomaly_id] = anomaly
            
            # Log anomaly event
            anomaly_event = create_security_event(
                event_type=SecurityEventType.ANOMALY_DETECTED,
                severity=anomaly.severity,
                source_component="security_monitor",
                action="anomaly_detected",
                resource=anomaly.anomaly_type.value,
                result="detected",
                risk_score=anomaly.risk_score,
                threat_indicators=anomaly.threat_indicators,
                metadata={
                    "anomaly_id": anomaly.anomaly_id,
                    "confidence": anomaly.confidence,
                    "description": anomaly.description,
                    "affected_entities": anomaly.affected_entities
                }
            )
            await audit_logger.log_event(anomaly_event)
            
            # Auto-response if enabled and confidence is high
            if (self.config.get("auto_response_enabled", False) and 
                anomaly.confidence >= 0.9 and 
                anomaly.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]):
                
                await self._execute_auto_response(anomaly)
            
            # Trigger alerts
            await self._trigger_anomaly_alerts(anomaly)
            
        except Exception as e:
            logger.error(f"Failed to handle anomaly: {e}")
    
    async def _execute_auto_response(self, anomaly: SecurityAnomaly):
        """Execute automated response to anomaly."""
        try:
            response_actions = []
            
            # Rate limiting response
            if anomaly.anomaly_type == AnomalyType.RATE_ANOMALY:
                response_actions.append("rate_limit_tightened")
            
            # Privilege escalation response
            elif anomaly.anomaly_type == AnomalyType.PRIVILEGE_ANOMALY:
                response_actions.append("user_session_terminated")
                response_actions.append("security_team_notified")
            
            # Pattern-based threat response
            elif anomaly.anomaly_type == AnomalyType.PATTERN_ANOMALY:
                response_actions.append("command_execution_blocked")
                response_actions.append("enhanced_monitoring_enabled")
            
            anomaly.auto_response_taken = True
            anomaly.response_actions.extend(response_actions)
            
            # Log response actions
            response_event = create_security_event(
                event_type=SecurityEventType.SYSTEM_SECURITY_UPDATE,
                severity=SecuritySeverity.INFO,
                source_component="security_monitor",
                action="auto_response",
                result="executed",
                metadata={
                    "anomaly_id": anomaly.anomaly_id,
                    "response_actions": response_actions
                }
            )
            await audit_logger.log_event(response_event)
            
        except Exception as e:
            logger.error(f"Auto-response execution error: {e}")
    
    async def _correlate_and_create_incidents(self, event: SecurityEvent, anomalies: List[SecurityAnomaly]):
        """Correlate events and create incidents."""
        try:
            if not self.config.get("auto_incident_creation", True):
                return
            
            # Check if any anomaly meets incident creation threshold
            high_confidence_anomalies = [
                a for a in anomalies 
                if a.confidence >= self.config.get("incident_auto_create_threshold", 0.8)
            ]
            
            if not high_confidence_anomalies:
                return
            
            # Check for existing related incidents
            related_incident = None
            correlation_window = timedelta(
                minutes=self.config.get("incident_correlation_window_minutes", 15)
            )
            
            cutoff_time = datetime.utcnow() - correlation_window
            
            for incident in self.active_incidents.values():
                if (incident.status not in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE] and
                    incident.last_seen >= cutoff_time):
                    
                    # Check if this event correlates with existing incident
                    if (event.user_id in incident.affected_users or
                        event.client_ip in incident.metadata.get("related_ips", []) or
                        any(t in incident.indicators_of_compromise for t in anomalies[0].threat_indicators)):
                        
                        related_incident = incident
                        break
            
            if related_incident:
                # Update existing incident
                related_incident.last_seen = datetime.utcnow()
                related_incident.related_events.append(event.event_id)
                related_incident.related_anomalies.extend([a.anomaly_id for a in anomalies])
                
                # Escalate if severity increased
                max_anomaly_severity = max(a.severity for a in anomalies)
                if max_anomaly_severity.value > related_incident.severity.value:
                    related_incident.severity = max_anomaly_severity
                    await self._escalate_incident(related_incident)
            else:
                # Create new incident
                await self._create_incident(event, anomalies)
                
        except Exception as e:
            logger.error(f"Incident correlation error: {e}")
    
    async def _create_incident(self, event: SecurityEvent, anomalies: List[SecurityAnomaly]):
        """Create new security incident."""
        try:
            # Determine incident severity and type
            max_severity = max(a.severity for a in anomalies)
            primary_anomaly = anomalies[0]
            
            # Generate incident details
            incident_id = str(uuid.uuid4())
            title = f"{primary_anomaly.anomaly_type.value.replace('_', ' ').title()} - {primary_anomaly.description}"
            
            incident = SecurityIncident(
                incident_id=incident_id,
                title=title,
                description=f"Security incident created from {len(anomalies)} anomalies",
                severity=max_severity,
                status=IncidentStatus.OPEN,
                threat_level=self._calculate_threat_level(anomalies),
                created_at=datetime.utcnow(),
                first_seen=event.timestamp,
                last_seen=event.timestamp,
                incident_type=primary_anomaly.anomaly_type.value,
                affected_users=[event.user_id] if event.user_id else [],
                related_events=[event.event_id],
                related_anomalies=[a.anomaly_id for a in anomalies],
                indicators_of_compromise=[
                    indicator for anomaly in anomalies 
                    for indicator in anomaly.threat_indicators
                ],
                metadata={
                    "total_anomalies": len(anomalies),
                    "max_confidence": max(a.confidence for a in anomalies),
                    "related_ips": [event.client_ip] if event.client_ip else [],
                    "creation_reason": "automated_detection"
                }
            )
            
            # Store incident
            self.active_incidents[incident_id] = incident
            
            # Log incident creation
            incident_event = create_security_event(
                event_type=SecurityEventType.SYSTEM_SECURITY_UPDATE,
                severity=max_severity,
                source_component="security_monitor",
                action="incident_created",
                resource=incident_id,
                result="created",
                metadata={
                    "incident_id": incident_id,
                    "title": title,
                    "threat_level": incident.threat_level.value,
                    "anomaly_count": len(anomalies)
                }
            )
            await audit_logger.log_event(incident_event)
            
            # Auto-escalate critical incidents
            if (max_severity == SecuritySeverity.CRITICAL and 
                self.config.get("auto_escalate_critical", True)):
                await self._escalate_incident(incident)
            
            # Trigger incident callbacks
            await self._trigger_incident_alerts(incident)
            
        except Exception as e:
            logger.error(f"Failed to create incident: {e}")
    
    def _calculate_threat_level(self, anomalies: List[SecurityAnomaly]) -> ThreatLevel:
        """Calculate overall threat level from anomalies."""
        max_severity = max(a.severity for a in anomalies)
        max_confidence = max(a.confidence for a in anomalies)
        anomaly_count = len(anomalies)
        
        if max_severity == SecuritySeverity.CRITICAL and max_confidence >= 0.9:
            return ThreatLevel.CRITICAL
        elif max_severity == SecuritySeverity.HIGH and (max_confidence >= 0.8 or anomaly_count >= 3):
            return ThreatLevel.HIGH
        elif max_severity == SecuritySeverity.MEDIUM or anomaly_count >= 2:
            return ThreatLevel.MEDIUM
        elif max_severity == SecuritySeverity.LOW:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.NONE
    
    async def _escalate_incident(self, incident: SecurityIncident):
        """Escalate security incident."""
        try:
            incident.escalated = True
            incident.status = IncidentStatus.INVESTIGATING
            
            # Log escalation
            escalation_event = create_security_event(
                event_type=SecurityEventType.SYSTEM_SECURITY_UPDATE,
                severity=SecuritySeverity.HIGH,
                source_component="security_monitor",
                action="incident_escalated",
                resource=incident.incident_id,
                result="escalated",
                metadata={
                    "incident_id": incident.incident_id,
                    "title": incident.title,
                    "threat_level": incident.threat_level.value
                }
            )
            await audit_logger.log_event(escalation_event)
            
        except Exception as e:
            logger.error(f"Failed to escalate incident: {e}")
    
    async def _trigger_anomaly_alerts(self, anomaly: SecurityAnomaly):
        """Trigger alerts for detected anomaly."""
        for callback in self.alert_callbacks:
            try:
                await callback(anomaly)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    async def _trigger_incident_alerts(self, incident: SecurityIncident):
        """Trigger alerts for security incident."""
        for callback in self.incident_callbacks:
            try:
                await callback(incident)
            except Exception as e:
                logger.error(f"Incident callback error: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """Add anomaly alert callback."""
        self.alert_callbacks.append(callback)
    
    def add_incident_callback(self, callback: Callable):
        """Add incident alert callback."""
        self.incident_callbacks.append(callback)
    
    def _start_monitoring_tasks(self):
        """Start background monitoring tasks."""
        async def event_processor():
            while True:
                try:
                    event = await self.event_stream.get()
                    # Event processing is already handled in process_security_event
                    # This is just to keep the queue from blocking
                except Exception as e:
                    logger.error(f"Event processor error: {e}")
                    await asyncio.sleep(1)
        
        async def analytics_processor():
            while True:
                try:
                    await asyncio.sleep(300)  # Run every 5 minutes
                    await self._update_baseline_analytics()
                except Exception as e:
                    logger.error(f"Analytics processor error: {e}")
                    await asyncio.sleep(60)
        
        try:
            loop = asyncio.get_running_loop()
            self._monitor_task = loop.create_task(event_processor())
            self._analytics_task = loop.create_task(analytics_processor())
            logger.info("Security monitoring tasks started")
        except RuntimeError:
            logger.info("No event loop running, monitoring will be handled synchronously")
    
    async def _update_baseline_analytics(self):
        """Update baseline analytics for anomaly detection."""
        try:
            # Update global baselines
            current_hour = datetime.utcnow().hour
            
            # Calculate event rate baselines
            hourly_events = sum(1 for t in self.event_rates["total"] 
                              if t >= time.time() - 3600)
            
            if f"hour_{current_hour}" not in self.baseline_stats:
                self.baseline_stats[f"hour_{current_hour}"] = {"events": []}
            
            self.baseline_stats[f"hour_{current_hour}"]["events"].append(hourly_events)
            
            # Keep only last 30 days of data
            if len(self.baseline_stats[f"hour_{current_hour}"]["events"]) > 30:
                self.baseline_stats[f"hour_{current_hour}"]["events"] = \
                    self.baseline_stats[f"hour_{current_hour}"]["events"][-30:]
            
        except Exception as e:
            logger.error(f"Baseline analytics update error: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        current_time = datetime.utcnow()
        
        # Calculate average processing time
        avg_processing_time = (sum(self.processing_times) / len(self.processing_times) 
                             if self.processing_times else 0)
        
        # Count active incidents by severity
        incident_counts = defaultdict(int)
        for incident in self.active_incidents.values():
            if incident.status not in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE]:
                incident_counts[incident.severity.value] += 1
        
        # Count recent anomalies
        hour_ago = current_time - timedelta(hours=1)
        recent_anomalies = sum(1 for a in self.detected_anomalies.values() 
                             if a.detected_at >= hour_ago)
        
        return {
            "status": "active",
            "monitoring_since": current_time.isoformat(),
            "performance": {
                "events_processed": self.metrics.get("total_events", 0),
                "anomalies_detected": len(self.detected_anomalies),
                "incidents_created": len(self.active_incidents),
                "avg_processing_time_ms": round(avg_processing_time, 2),
                "queue_size": self.event_stream.qsize() if hasattr(self.event_stream, 'qsize') else 0
            },
            "detection_engines": {
                "total_detectors": len(self.anomaly_detectors),
                "threat_indicators": len(self.threat_indicators),
                "user_profiles": len(self.user_profiles)
            },
            "current_threats": {
                "active_incidents": dict(incident_counts),
                "recent_anomalies": recent_anomalies,
                "threat_level": self._get_current_threat_level()
            },
            "configuration": {
                "real_time_processing": self.config.get("real_time_processing", True),
                "anomaly_detection": self.config.get("anomaly_detection_enabled", True),
                "auto_incident_creation": self.config.get("auto_incident_creation", True),
                "auto_response": self.config.get("auto_response_enabled", False)
            }
        }
    
    def _get_current_threat_level(self) -> str:
        """Calculate current system threat level."""
        active_incidents = [i for i in self.active_incidents.values() 
                          if i.status not in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE]]
        
        if any(i.threat_level == ThreatLevel.CRITICAL for i in active_incidents):
            return "CRITICAL"
        elif any(i.threat_level == ThreatLevel.HIGH for i in active_incidents):
            return "HIGH"
        elif any(i.threat_level == ThreatLevel.MEDIUM for i in active_incidents):
            return "MEDIUM"
        else:
            return "LOW"


# Global security monitor instance
security_monitor = SecurityMonitor()


# Integration helper functions
async def monitor_security_event(event: SecurityEvent) -> List[SecurityAnomaly]:
    """Monitor a security event and return detected anomalies."""
    return await security_monitor.process_security_event(event)


def get_monitoring_status() -> Dict[str, Any]:
    """Get current monitoring status."""
    return security_monitor.get_monitoring_status()


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        monitor = SecurityMonitor()
        
        # Test events
        test_events = [
            create_security_event(
                SecurityEventType.AUTH_LOGIN_SUCCESS,
                SecuritySeverity.INFO,
                "auth_service",
                user_id="test_user",
                client_ip="192.168.1.100"
            ),
            create_security_event(
                SecurityEventType.SECURITY_COMMAND_BLOCKED,
                SecuritySeverity.HIGH,
                "security_manager",
                user_id="test_user",
                action="rm -rf /"
            ),
            create_security_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecuritySeverity.MEDIUM,
                "rate_limiter",
                client_ip="192.168.1.100"
            )
        ]
        
        print("Processing test events...")
        for event in test_events:
            anomalies = await monitor.process_security_event(event)
            print(f"Event {event.event_type.value}: {len(anomalies)} anomalies detected")
        
        await asyncio.sleep(2)  # Wait for processing
        
        # Get monitoring status
        status = monitor.get_monitoring_status()
        print(f"\nMonitoring Status:")
        print(f"Events processed: {status['performance']['events_processed']}")
        print(f"Anomalies detected: {status['performance']['anomalies_detected']}")
        print(f"Incidents created: {status['performance']['incidents_created']}")
        print(f"Current threat level: {status['current_threats']['threat_level']}")
    
    # Run test
    asyncio.run(main())