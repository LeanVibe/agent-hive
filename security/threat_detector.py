#!/usr/bin/env python3
"""
ML-Based Threat Detection System

Enterprise-grade threat detection with machine learning capabilities including
behavioral analysis, anomaly detection, pattern recognition, and real-time
threat scoring for LeanVibe Agent Hive.
"""

import asyncio
import json
import logging
import math
import statistics
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from security.security_manager import SecurityManager


logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatCategory(Enum):
    """Threat categories for classification."""
    BRUTE_FORCE = "brute_force"
    CREDENTIAL_STUFFING = "credential_stuffing"
    ACCOUNT_TAKEOVER = "account_takeover"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    SUSPICIOUS_ACCESS = "suspicious_access"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    RATE_LIMITING_VIOLATION = "rate_limiting_violation"
    GEO_ANOMALY = "geo_anomaly"
    TIME_ANOMALY = "time_anomaly"
    DEVICE_ANOMALY = "device_anomaly"
    API_ABUSE = "api_abuse"


class ThreatStatus(Enum):
    """Threat detection status."""
    ACTIVE = "active"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    SUPPRESSED = "suppressed"


@dataclass
class BehaviorPattern:
    """User behavior pattern for baseline establishment."""
    user_id: str
    pattern_type: str
    values: List[float]
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    sample_count: int
    last_updated: datetime
    confidence_score: float = 0.0


@dataclass
class ThreatEvent:
    """Individual threat event detection."""
    event_id: str
    threat_id: str
    user_id: Optional[str]
    category: ThreatCategory
    level: ThreatLevel
    score: float  # 0.0 to 1.0
    description: str
    evidence: Dict[str, Any]
    timestamp: datetime
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    raw_data: Dict[str, Any] = None


@dataclass
class ThreatAlert:
    """High-level threat alert aggregating multiple events."""
    alert_id: str
    category: ThreatCategory
    level: ThreatLevel
    title: str
    description: str
    first_seen: datetime
    last_seen: datetime
    event_count: int
    affected_users: Set[str]
    source_ips: Set[str]
    status: ThreatStatus = ThreatStatus.ACTIVE
    events: List[ThreatEvent] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
        if self.recommendations is None:
            self.recommendations = []


class MLThreatDetector:
    """
    Machine Learning-based threat detection system with advanced analytics.
    
    Features:
    - Behavioral baseline establishment
    - Anomaly detection using statistical methods
    - Pattern recognition for attack signatures
    - Real-time threat scoring
    - Adaptive learning from user behavior
    - Multiple detection algorithms
    - Alert correlation and aggregation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 security_manager: Optional[SecurityManager] = None):
        """Initialize ML threat detector."""
        self.config = config or self._get_default_config()
        self.security_manager = security_manager
        
        # Storage for ML models and data
        self.behavior_patterns: Dict[str, Dict[str, BehaviorPattern]] = defaultdict(dict)
        self.threat_events: Dict[str, ThreatEvent] = {}
        self.threat_alerts: Dict[str, ThreatAlert] = {}
        self.user_sessions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.ip_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self.detection_rules: Dict[str, Dict[str, Any]] = {}
        
        # Real-time tracking
        self.active_threats: Set[str] = set()
        self.suppressed_threats: Set[str] = set()
        self.learning_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Initialize detection rules
        self._initialize_detection_rules()
        
        # Start background processing
        self._start_background_tasks()
        
        logger.info("MLThreatDetector initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default threat detection configuration."""
        return {
            "anomaly_threshold": 2.5,  # Standard deviations
            "min_baseline_samples": 50,
            "learning_window_hours": 168,  # 1 week
            "threat_score_threshold": 0.7,
            "alert_correlation_window_minutes": 30,
            "max_events_per_alert": 1000,
            "behavioral_learning_enabled": True,
            "real_time_detection": True,
            "auto_suppression_enabled": True
        }
    
    def _initialize_detection_rules(self) -> None:
        """Initialize threat detection rules."""
        self.detection_rules = {
            "brute_force": {
                "max_failed_attempts": 5,
                "time_window_minutes": 15,
                "threshold_score": 0.8
            },
            "credential_stuffing": {
                "unique_usernames_threshold": 10,
                "time_window_minutes": 10,
                "threshold_score": 0.9
            },
            "geo_anomaly": {
                "max_distance_km": 1000,
                "time_window_hours": 4,
                "threshold_score": 0.7
            },
            "time_anomaly": {
                "unusual_hour_threshold": 3.0,  # std devs
                "threshold_score": 0.6
            },
            "rate_violation": {
                "requests_per_minute_threshold": 100,
                "burst_threshold": 200,
                "threshold_score": 0.8
            },
            "privilege_escalation": {
                "permission_increase_threshold": 5,
                "time_window_minutes": 60,
                "threshold_score": 0.9
            }
        }
    
    async def analyze_authentication_event(self, event_data: Dict[str, Any]) -> List[ThreatEvent]:
        """Analyze authentication event for threats."""
        threats = []
        
        try:
            user_id = event_data.get("user_id")
            ip_address = event_data.get("ip_address")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            event_type = event_data.get("event_type")
            success = event_data.get("success", False)
            
            # Track user session data
            if user_id:
                self.user_sessions[user_id].append({
                    "timestamp": timestamp,
                    "ip_address": ip_address,
                    "success": success,
                    "event_type": event_type
                })
            
            # Track IP activity
            if ip_address:
                self.ip_activity[ip_address].append({
                    "timestamp": timestamp,
                    "user_id": user_id,
                    "success": success,
                    "event_type": event_type
                })
            
            # Detect brute force attacks
            brute_force_threat = await self._detect_brute_force(event_data)
            if brute_force_threat:
                threats.append(brute_force_threat)
            
            # Detect credential stuffing
            credential_stuffing_threat = await self._detect_credential_stuffing(event_data)
            if credential_stuffing_threat:
                threats.append(credential_stuffing_threat)
            
            # Detect geographical anomalies
            if success and user_id:
                geo_threat = await self._detect_geographical_anomaly(event_data)
                if geo_threat:
                    threats.append(geo_threat)
            
            # Detect time-based anomalies
            if success and user_id:
                time_threat = await self._detect_time_anomaly(event_data)
                if time_threat:
                    threats.append(time_threat)
            
            # Update behavioral patterns
            if self.config.get("behavioral_learning_enabled", True) and user_id:
                await self._update_behavioral_patterns(user_id, event_data)
            
            # Store events for learning
            self.learning_data["authentication"].append(event_data)
            
        except Exception as e:
            logger.error(f"Failed to analyze authentication event: {e}")
        
        return threats
    
    async def analyze_api_access_event(self, event_data: Dict[str, Any]) -> List[ThreatEvent]:
        """Analyze API access event for threats."""
        threats = []
        
        try:
            user_id = event_data.get("user_id")
            ip_address = event_data.get("ip_address")
            endpoint = event_data.get("endpoint")
            method = event_data.get("method")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            status_code = event_data.get("status_code", 200)
            
            # Detect rate limiting violations
            rate_threat = await self._detect_rate_violation(event_data)
            if rate_threat:
                threats.append(rate_threat)
            
            # Detect API abuse patterns
            abuse_threat = await self._detect_api_abuse(event_data)
            if abuse_threat:
                threats.append(abuse_threat)
            
            # Detect privilege escalation attempts
            if user_id:
                privilege_threat = await self._detect_privilege_escalation(event_data)
                if privilege_threat:
                    threats.append(privilege_threat)
            
            # Store for learning
            self.learning_data["api_access"].append(event_data)
            
        except Exception as e:
            logger.error(f"Failed to analyze API access event: {e}")
        
        return threats
    
    async def analyze_user_behavior(self, user_id: str, activity_data: List[Dict[str, Any]]) -> List[ThreatEvent]:
        """Analyze user behavior patterns for anomalies."""
        threats = []
        
        try:
            if not activity_data:
                return threats
            
            # Detect anomalous behavior patterns
            behavior_threat = await self._detect_behavioral_anomalies(user_id, activity_data)
            if behavior_threat:
                threats.append(behavior_threat)
            
            # Detect device anomalies
            device_threat = await self._detect_device_anomalies(user_id, activity_data)
            if device_threat:
                threats.append(device_threat)
            
            # Update behavioral baselines
            await self._update_user_baseline(user_id, activity_data)
            
        except Exception as e:
            logger.error(f"Failed to analyze user behavior for {user_id}: {e}")
        
        return threats
    
    async def _detect_brute_force(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Detect brute force attacks."""
        try:
            ip_address = event_data.get("ip_address")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            success = event_data.get("success", False)
            
            if not ip_address or success:
                return None
            
            rule = self.detection_rules["brute_force"]
            time_window = timedelta(minutes=rule["time_window_minutes"])
            cutoff_time = timestamp - time_window
            
            # Count recent failed attempts from this IP
            recent_failures = sum(
                1 for activity in self.ip_activity[ip_address]
                if (activity["timestamp"] > cutoff_time and 
                    not activity["success"] and
                    activity["event_type"] == "login_failed")
            )
            
            if recent_failures >= rule["max_failed_attempts"]:
                threat_score = min(1.0, recent_failures / rule["max_failed_attempts"])
                
                return ThreatEvent(
                    event_id=str(uuid.uuid4()),
                    threat_id=f"brute_force_{ip_address}_{timestamp.strftime('%Y%m%d_%H%M')}",
                    user_id=event_data.get("user_id"),
                    category=ThreatCategory.BRUTE_FORCE,
                    level=ThreatLevel.HIGH if threat_score >= 0.8 else ThreatLevel.MEDIUM,
                    score=threat_score,
                    description=f"Brute force attack detected from IP {ip_address} with {recent_failures} failed attempts",
                    evidence={
                        "failed_attempts": recent_failures,
                        "time_window_minutes": rule["time_window_minutes"],
                        "source_ip": ip_address,
                        "attack_pattern": "brute_force"
                    },
                    timestamp=timestamp,
                    source_ip=ip_address,
                    raw_data=event_data
                )
        
        except Exception as e:
            logger.error(f"Failed to detect brute force: {e}")
        
        return None
    
    async def _detect_credential_stuffing(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Detect credential stuffing attacks."""
        try:
            ip_address = event_data.get("ip_address")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            
            if not ip_address:
                return None
            
            rule = self.detection_rules["credential_stuffing"]
            time_window = timedelta(minutes=rule["time_window_minutes"])
            cutoff_time = timestamp - time_window
            
            # Count unique usernames attempted from this IP
            unique_users = set()
            for activity in self.ip_activity[ip_address]:
                if (activity["timestamp"] > cutoff_time and 
                    not activity["success"] and
                    activity.get("user_id")):
                    unique_users.add(activity["user_id"])
            
            if len(unique_users) >= rule["unique_usernames_threshold"]:
                threat_score = min(1.0, len(unique_users) / (rule["unique_usernames_threshold"] * 2))
                
                return ThreatEvent(
                    event_id=str(uuid.uuid4()),
                    threat_id=f"credential_stuffing_{ip_address}_{timestamp.strftime('%Y%m%d_%H%M')}",
                    user_id=None,  # Multiple users targeted
                    category=ThreatCategory.CREDENTIAL_STUFFING,
                    level=ThreatLevel.HIGH,
                    score=threat_score,
                    description=f"Credential stuffing attack detected from IP {ip_address} targeting {len(unique_users)} different accounts",
                    evidence={
                        "unique_usernames_attempted": len(unique_users),
                        "time_window_minutes": rule["time_window_minutes"],
                        "source_ip": ip_address,
                        "attack_pattern": "credential_stuffing"
                    },
                    timestamp=timestamp,
                    source_ip=ip_address,
                    raw_data=event_data
                )
        
        except Exception as e:
            logger.error(f"Failed to detect credential stuffing: {e}")
        
        return None
    
    async def _detect_geographical_anomaly(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Detect geographical anomalies in user access."""
        try:
            user_id = event_data.get("user_id")
            ip_address = event_data.get("ip_address")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            
            if not user_id or not ip_address:
                return None
            
            # Get user's recent access locations (this would integrate with IP geolocation service)
            # For now, we'll use a simplified approach based on IP patterns
            user_activities = list(self.user_sessions[user_id])
            if len(user_activities) < 10:  # Need baseline data
                return None
            
            # Simple heuristic: detect if IP subnet changes dramatically
            current_ip_prefix = ".".join(ip_address.split(".")[:2])
            recent_ip_prefixes = set()
            
            rule = self.detection_rules["geo_anomaly"]
            time_window = timedelta(hours=rule["time_window_hours"])
            cutoff_time = timestamp - time_window
            
            for activity in user_activities[-50:]:  # Check last 50 activities
                if activity["timestamp"] > cutoff_time and activity.get("ip_address"):
                    recent_prefix = ".".join(activity["ip_address"].split(".")[:2])
                    recent_ip_prefixes.add(recent_prefix)
            
            # If current IP prefix is completely new, it might be suspicious
            if recent_ip_prefixes and current_ip_prefix not in recent_ip_prefixes:
                threat_score = 0.7  # Base score for new location
                
                return ThreatEvent(
                    event_id=str(uuid.uuid4()),
                    threat_id=f"geo_anomaly_{user_id}_{timestamp.strftime('%Y%m%d_%H%M')}",
                    user_id=user_id,
                    category=ThreatCategory.GEO_ANOMALY,
                    level=ThreatLevel.MEDIUM,
                    score=threat_score,
                    description=f"Geographical anomaly detected for user {user_id} accessing from new IP range {current_ip_prefix}.x.x",
                    evidence={
                        "new_ip_prefix": current_ip_prefix,
                        "recent_ip_prefixes": list(recent_ip_prefixes),
                        "time_window_hours": rule["time_window_hours"]
                    },
                    timestamp=timestamp,
                    source_ip=ip_address,
                    raw_data=event_data
                )
        
        except Exception as e:
            logger.error(f"Failed to detect geographical anomaly: {e}")
        
        return None
    
    async def _detect_time_anomaly(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Detect time-based access anomalies."""
        try:
            user_id = event_data.get("user_id")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            
            if not user_id:
                return None
            
            # Get user's historical access patterns
            pattern_key = f"{user_id}_access_hour"
            if pattern_key not in self.behavior_patterns[user_id]:
                return None  # No baseline established
            
            pattern = self.behavior_patterns[user_id][pattern_key]
            current_hour = timestamp.hour
            
            # Calculate z-score for current access hour
            if pattern.std_dev > 0:
                z_score = abs(current_hour - pattern.mean) / pattern.std_dev
                
                rule = self.detection_rules["time_anomaly"]
                if z_score > rule["unusual_hour_threshold"]:
                    threat_score = min(1.0, z_score / (rule["unusual_hour_threshold"] * 2))
                    
                    return ThreatEvent(
                        event_id=str(uuid.uuid4()),
                        threat_id=f"time_anomaly_{user_id}_{timestamp.strftime('%Y%m%d_%H%M')}",
                        user_id=user_id,
                        category=ThreatCategory.TIME_ANOMALY,
                        level=ThreatLevel.LOW if threat_score < 0.7 else ThreatLevel.MEDIUM,
                        score=threat_score,
                        description=f"Unusual access time detected for user {user_id} at hour {current_hour} (z-score: {z_score:.2f})",
                        evidence={
                            "access_hour": current_hour,
                            "expected_mean": pattern.mean,
                            "z_score": z_score,
                            "threshold": rule["unusual_hour_threshold"]
                        },
                        timestamp=timestamp,
                        raw_data=event_data
                    )
        
        except Exception as e:
            logger.error(f"Failed to detect time anomaly: {e}")
        
        return None
    
    async def _detect_rate_violation(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Detect rate limiting violations."""
        try:
            ip_address = event_data.get("ip_address")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            
            if not ip_address:
                return None
            
            rule = self.detection_rules["rate_violation"]
            time_window = timedelta(minutes=1)
            cutoff_time = timestamp - time_window
            
            # Count requests in the last minute
            recent_requests = sum(
                1 for activity in self.ip_activity[ip_address]
                if activity["timestamp"] > cutoff_time
            )
            
            if recent_requests > rule["requests_per_minute_threshold"]:
                threat_score = min(1.0, recent_requests / rule["burst_threshold"])
                
                return ThreatEvent(
                    event_id=str(uuid.uuid4()),
                    threat_id=f"rate_violation_{ip_address}_{timestamp.strftime('%Y%m%d_%H%M')}",
                    user_id=event_data.get("user_id"),
                    category=ThreatCategory.RATE_LIMITING_VIOLATION,
                    level=ThreatLevel.MEDIUM,
                    score=threat_score,
                    description=f"Rate limiting violation detected from IP {ip_address} with {recent_requests} requests/minute",
                    evidence={
                        "requests_per_minute": recent_requests,
                        "threshold": rule["requests_per_minute_threshold"],
                        "source_ip": ip_address
                    },
                    timestamp=timestamp,
                    source_ip=ip_address,
                    raw_data=event_data
                )
        
        except Exception as e:
            logger.error(f"Failed to detect rate violation: {e}")
        
        return None
    
    async def _detect_api_abuse(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Detect API abuse patterns."""
        try:
            endpoint = event_data.get("endpoint")
            user_id = event_data.get("user_id")
            status_code = event_data.get("status_code", 200)
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            
            if not endpoint or not user_id:
                return None
            
            # Look for patterns of API abuse (e.g., excessive 4xx errors, data scraping patterns)
            time_window = timedelta(minutes=10)
            cutoff_time = timestamp - time_window
            
            # Count recent API calls by this user
            recent_calls = 0
            error_calls = 0
            
            for data_point in self.learning_data["api_access"]:
                if (data_point.get("user_id") == user_id and
                    datetime.fromisoformat(data_point.get("timestamp", "1970-01-01")) > cutoff_time):
                    recent_calls += 1
                    if data_point.get("status_code", 200) >= 400:
                        error_calls += 1
            
            # Check for suspicious patterns
            if recent_calls > 200:  # High volume
                error_rate = error_calls / recent_calls if recent_calls > 0 else 0
                
                if error_rate > 0.5:  # High error rate suggests automated abuse
                    threat_score = min(1.0, (recent_calls / 500) + error_rate)
                    
                    return ThreatEvent(
                        event_id=str(uuid.uuid4()),
                        threat_id=f"api_abuse_{user_id}_{timestamp.strftime('%Y%m%d_%H%M')}",
                        user_id=user_id,
                        category=ThreatCategory.API_ABUSE,
                        level=ThreatLevel.MEDIUM,
                        score=threat_score,
                        description=f"API abuse detected for user {user_id} with {recent_calls} calls and {error_rate:.1%} error rate",
                        evidence={
                            "recent_api_calls": recent_calls,
                            "error_rate": error_rate,
                            "time_window_minutes": 10,
                            "endpoint": endpoint
                        },
                        timestamp=timestamp,
                        endpoint=endpoint,
                        raw_data=event_data
                    )
        
        except Exception as e:
            logger.error(f"Failed to detect API abuse: {e}")
        
        return None
    
    async def _detect_privilege_escalation(self, event_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """Detect privilege escalation attempts."""
        try:
            user_id = event_data.get("user_id")
            endpoint = event_data.get("endpoint", "")
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            
            if not user_id:
                return None
            
            # Look for access to admin endpoints or privilege-related operations
            admin_keywords = ["admin", "privilege", "role", "permission", "sudo", "escalate"]
            
            if any(keyword in endpoint.lower() for keyword in admin_keywords):
                # Check if user has recently increased permissions or accessed admin functions
                threat_score = 0.6  # Base score for admin endpoint access
                
                return ThreatEvent(
                    event_id=str(uuid.uuid4()),
                    threat_id=f"privilege_escalation_{user_id}_{timestamp.strftime('%Y%m%d_%H%M')}",
                    user_id=user_id,
                    category=ThreatCategory.PRIVILEGE_ESCALATION,
                    level=ThreatLevel.MEDIUM,
                    score=threat_score,
                    description=f"Potential privilege escalation detected for user {user_id} accessing {endpoint}",
                    evidence={
                        "admin_endpoint": endpoint,
                        "admin_keywords_matched": [kw for kw in admin_keywords if kw in endpoint.lower()]
                    },
                    timestamp=timestamp,
                    endpoint=endpoint,
                    raw_data=event_data
                )
        
        except Exception as e:
            logger.error(f"Failed to detect privilege escalation: {e}")
        
        return None
    
    async def _detect_behavioral_anomalies(self, user_id: str, activity_data: List[Dict[str, Any]]) -> Optional[ThreatEvent]:
        """Detect behavioral anomalies using statistical analysis."""
        try:
            if len(activity_data) < 10:
                return None
            
            # Analyze various behavioral metrics
            metrics = self._extract_behavioral_metrics(activity_data)
            
            # Check against established baselines
            anomalies = []
            for metric_name, metric_value in metrics.items():
                pattern_key = f"{user_id}_{metric_name}"
                if pattern_key in self.behavior_patterns[user_id]:
                    pattern = self.behavior_patterns[user_id][pattern_key]
                    
                    if pattern.std_dev > 0:
                        z_score = abs(metric_value - pattern.mean) / pattern.std_dev
                        
                        if z_score > self.config.get("anomaly_threshold", 2.5):
                            anomalies.append({
                                "metric": metric_name,
                                "value": metric_value,
                                "expected": pattern.mean,
                                "z_score": z_score
                            })
            
            if anomalies:
                avg_z_score = statistics.mean([a["z_score"] for a in anomalies])
                threat_score = min(1.0, avg_z_score / 5.0)  # Normalize to 0-1
                
                return ThreatEvent(
                    event_id=str(uuid.uuid4()),
                    threat_id=f"behavioral_anomaly_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                    user_id=user_id,
                    category=ThreatCategory.ANOMALOUS_BEHAVIOR,
                    level=ThreatLevel.MEDIUM if threat_score >= 0.7 else ThreatLevel.LOW,
                    score=threat_score,
                    description=f"Behavioral anomaly detected for user {user_id} with {len(anomalies)} unusual metrics",
                    evidence={
                        "anomalies": anomalies,
                        "avg_z_score": avg_z_score,
                        "threshold": self.config.get("anomaly_threshold", 2.5)
                    },
                    timestamp=datetime.utcnow(),
                    raw_data={"activity_count": len(activity_data)}
                )
        
        except Exception as e:
            logger.error(f"Failed to detect behavioral anomalies for {user_id}: {e}")
        
        return None
    
    async def _detect_device_anomalies(self, user_id: str, activity_data: List[Dict[str, Any]]) -> Optional[ThreatEvent]:
        """Detect device-based anomalies."""
        try:
            # Extract device fingerprints and user agents
            devices = set()
            user_agents = set()
            
            for activity in activity_data:
                if activity.get("device_fingerprint"):
                    devices.add(activity["device_fingerprint"])
                if activity.get("user_agent"):
                    user_agents.add(activity["user_agent"])
            
            # Check for suspicious device patterns
            if len(devices) > 5 or len(user_agents) > 10:  # Too many different devices/browsers
                threat_score = min(1.0, (len(devices) + len(user_agents)) / 20)
                
                return ThreatEvent(
                    event_id=str(uuid.uuid4()),
                    threat_id=f"device_anomaly_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                    user_id=user_id,
                    category=ThreatCategory.DEVICE_ANOMALY,
                    level=ThreatLevel.LOW,
                    score=threat_score,
                    description=f"Device anomaly detected for user {user_id} with {len(devices)} devices and {len(user_agents)} user agents",
                    evidence={
                        "unique_devices": len(devices),
                        "unique_user_agents": len(user_agents),
                        "device_threshold": 5,
                        "user_agent_threshold": 10
                    },
                    timestamp=datetime.utcnow(),
                    raw_data={"activity_count": len(activity_data)}
                )
        
        except Exception as e:
            logger.error(f"Failed to detect device anomalies for {user_id}: {e}")
        
        return None
    
    def _extract_behavioral_metrics(self, activity_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract behavioral metrics from activity data."""
        metrics = {}
        
        try:
            # Session duration patterns
            timestamps = [datetime.fromisoformat(a["timestamp"]) for a in activity_data if a.get("timestamp")]
            if len(timestamps) >= 2:
                durations = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
                if durations:
                    metrics["avg_session_gap"] = statistics.mean(durations)
                    metrics["session_variance"] = statistics.variance(durations) if len(durations) > 1 else 0
            
            # Access frequency patterns
            metrics["activity_count"] = len(activity_data)
            
            # Time-based patterns
            hours = [datetime.fromisoformat(a["timestamp"]).hour for a in activity_data if a.get("timestamp")]
            if hours:
                metrics["avg_access_hour"] = statistics.mean(hours)
            
            # API endpoint diversity
            endpoints = set(a.get("endpoint", "") for a in activity_data)
            metrics["endpoint_diversity"] = len(endpoints)
            
            # Error rate patterns
            total_requests = len(activity_data)
            error_requests = sum(1 for a in activity_data if a.get("status_code", 200) >= 400)
            metrics["error_rate"] = error_requests / total_requests if total_requests > 0 else 0
            
        except Exception as e:
            logger.error(f"Failed to extract behavioral metrics: {e}")
        
        return metrics
    
    async def _update_behavioral_patterns(self, user_id: str, event_data: Dict[str, Any]) -> None:
        """Update behavioral patterns for a user."""
        try:
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))
            
            # Update access hour pattern
            hour_pattern_key = f"{user_id}_access_hour"
            await self._update_pattern(user_id, hour_pattern_key, float(timestamp.hour))
            
            # Update other patterns based on event data
            if event_data.get("response_time_ms"):
                response_time_key = f"{user_id}_response_time"
                await self._update_pattern(user_id, response_time_key, float(event_data["response_time_ms"]))
            
        except Exception as e:
            logger.error(f"Failed to update behavioral patterns for {user_id}: {e}")
    
    async def _update_pattern(self, user_id: str, pattern_key: str, value: float) -> None:
        """Update a specific behavioral pattern."""
        try:
            current_time = datetime.utcnow()
            
            if pattern_key not in self.behavior_patterns[user_id]:
                # Create new pattern
                self.behavior_patterns[user_id][pattern_key] = BehaviorPattern(
                    user_id=user_id,
                    pattern_type=pattern_key.split("_", 1)[1],
                    values=[value],
                    mean=value,
                    std_dev=0.0,
                    min_value=value,
                    max_value=value,
                    sample_count=1,
                    last_updated=current_time
                )
            else:
                # Update existing pattern
                pattern = self.behavior_patterns[user_id][pattern_key]
                pattern.values.append(value)
                
                # Keep only recent values (last 1000)
                if len(pattern.values) > 1000:
                    pattern.values = pattern.values[-500:]
                
                # Recalculate statistics
                pattern.mean = statistics.mean(pattern.values)
                pattern.std_dev = statistics.stdev(pattern.values) if len(pattern.values) > 1 else 0.0
                pattern.min_value = min(pattern.values)
                pattern.max_value = max(pattern.values)
                pattern.sample_count = len(pattern.values)
                pattern.last_updated = current_time
                
                # Calculate confidence score based on sample size
                pattern.confidence_score = min(1.0, len(pattern.values) / self.config.get("min_baseline_samples", 50))
        
        except Exception as e:
            logger.error(f"Failed to update pattern {pattern_key} for {user_id}: {e}")
    
    async def _update_user_baseline(self, user_id: str, activity_data: List[Dict[str, Any]]) -> None:
        """Update user behavioral baseline with new activity data."""
        try:
            metrics = self._extract_behavioral_metrics(activity_data)
            
            for metric_name, metric_value in metrics.items():
                pattern_key = f"{user_id}_{metric_name}"
                await self._update_pattern(user_id, pattern_key, metric_value)
        
        except Exception as e:
            logger.error(f"Failed to update user baseline for {user_id}: {e}")
    
    async def create_threat_alert(self, events: List[ThreatEvent]) -> Optional[ThreatAlert]:
        """Create a threat alert from related events."""
        try:
            if not events:
                return None
            
            # Group events by category and determine overall severity
            categories = set(event.category for event in events)
            if len(categories) == 1:
                category = list(categories)[0]
            else:
                category = ThreatCategory.ANOMALOUS_BEHAVIOR  # Mixed threat types
            
            # Determine alert level
            max_level = max(event.level for event in events)
            
            # Aggregate information
            affected_users = set(event.user_id for event in events if event.user_id)
            source_ips = set(event.source_ip for event in events if event.source_ip)
            
            first_seen = min(event.timestamp for event in events)
            last_seen = max(event.timestamp for event in events)
            
            # Generate alert
            alert = ThreatAlert(
                alert_id=str(uuid.uuid4()),
                category=category,
                level=max_level,
                title=f"{category.value.replace('_', ' ').title()} Alert",
                description=f"Security alert with {len(events)} related events",
                first_seen=first_seen,
                last_seen=last_seen,
                event_count=len(events),
                affected_users=affected_users,
                source_ips=source_ips,
                events=events,
                recommendations=self._generate_alert_recommendations(category, events)
            )
            
            # Store alert
            self.threat_alerts[alert.alert_id] = alert
            self.active_threats.add(alert.alert_id)
            
            return alert
        
        except Exception as e:
            logger.error(f"Failed to create threat alert: {e}")
            return None
    
    def _generate_alert_recommendations(self, category: ThreatCategory, events: List[ThreatEvent]) -> List[str]:
        """Generate recommendations for threat alert."""
        recommendations = []
        
        if category == ThreatCategory.BRUTE_FORCE:
            recommendations.extend([
                "Block or rate-limit the source IP address",
                "Review and strengthen password policies",
                "Consider implementing account lockout mechanisms",
                "Enable two-factor authentication for affected accounts"
            ])
        
        elif category == ThreatCategory.CREDENTIAL_STUFFING:
            recommendations.extend([
                "Block the attacking IP address",
                "Force password resets for targeted accounts",
                "Implement CAPTCHA for authentication",
                "Monitor for credential breaches"
            ])
        
        elif category == ThreatCategory.GEO_ANOMALY:
            recommendations.extend([
                "Verify user identity through secondary channels",
                "Review recent account activity",
                "Consider temporary account restriction",
                "Implement geo-fencing policies"
            ])
        
        elif category == ThreatCategory.API_ABUSE:
            recommendations.extend([
                "Implement stricter rate limiting",
                "Review API access permissions",
                "Consider temporary API key suspension",
                "Monitor for automated abuse patterns"
            ])
        
        elif category == ThreatCategory.PRIVILEGE_ESCALATION:
            recommendations.extend([
                "Review user permissions and roles",
                "Audit recent privilege changes",
                "Implement just-in-time access controls",
                "Monitor administrative activities"
            ])
        
        return recommendations
    
    def _start_background_tasks(self) -> None:
        """Start background processing tasks."""
        async def process_threat_correlation():
            """Correlate related threat events into alerts."""
            while True:
                try:
                    current_time = datetime.utcnow()
                    correlation_window = timedelta(minutes=self.config.get("alert_correlation_window_minutes", 30))
                    
                    # Group events by potential correlation keys
                    correlation_groups = defaultdict(list)
                    
                    for event in list(self.threat_events.values()):
                        if event.timestamp > current_time - correlation_window:
                            # Group by IP address
                            if event.source_ip:
                                correlation_groups[f"ip_{event.source_ip}"].append(event)
                            
                            # Group by user
                            if event.user_id:
                                correlation_groups[f"user_{event.user_id}"].append(event)
                            
                            # Group by category
                            correlation_groups[f"category_{event.category.value}"].append(event)
                    
                    # Create alerts for significant correlations
                    for group_key, group_events in correlation_groups.items():
                        if len(group_events) >= 3:  # Minimum threshold for correlation
                            existing_alert_ids = set()
                            for event in group_events:
                                for alert in self.threat_alerts.values():
                                    if event in alert.events:
                                        existing_alert_ids.add(alert.alert_id)
                            
                            # Only create new alert if events aren't already correlated
                            if not existing_alert_ids:
                                await self.create_threat_alert(group_events)
                    
                    await asyncio.sleep(300)  # Run every 5 minutes
                    
                except Exception as e:
                    logger.error(f"Threat correlation task error: {e}")
                    await asyncio.sleep(60)
        
        async def cleanup_old_data():
            """Clean up old threat data and patterns."""
            while True:
                try:
                    current_time = datetime.utcnow()
                    retention_period = timedelta(days=30)
                    
                    # Clean up old events
                    events_to_remove = [
                        event_id for event_id, event in self.threat_events.items()
                        if current_time - event.timestamp > retention_period
                    ]
                    
                    for event_id in events_to_remove:
                        del self.threat_events[event_id]
                    
                    # Clean up old learning data
                    for data_type in self.learning_data:
                        self.learning_data[data_type] = [
                            data for data in self.learning_data[data_type]
                            if current_time - datetime.fromisoformat(data.get("timestamp", "1970-01-01")) < retention_period
                        ]
                    
                    await asyncio.sleep(3600)  # Run every hour
                    
                except Exception as e:
                    logger.error(f"Data cleanup task error: {e}")
                    await asyncio.sleep(300)
        
        # Start background tasks if event loop is available
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(process_threat_correlation())
            loop.create_task(cleanup_old_data())
        except RuntimeError:
            logger.info("No event loop running, threat detection background tasks will be handled manually")
    
    async def get_threat_analytics(self) -> Dict[str, Any]:
        """Get comprehensive threat detection analytics."""
        try:
            current_time = datetime.utcnow()
            
            # Threat event statistics
            total_events = len(self.threat_events)
            active_alerts = len(self.active_threats)
            
            # Event distribution by category
            category_counts = defaultdict(int)
            level_counts = defaultdict(int)
            
            for event in self.threat_events.values():
                category_counts[event.category.value] += 1
                level_counts[event.level.value] += 1
            
            # Recent activity (last 24 hours)
            last_24h = current_time - timedelta(hours=24)
            recent_events = sum(
                1 for event in self.threat_events.values()
                if event.timestamp > last_24h
            )
            
            # User behavior analytics
            total_users_monitored = len(self.behavior_patterns)
            patterns_established = sum(
                1 for user_patterns in self.behavior_patterns.values()
                for pattern in user_patterns.values()
                if pattern.confidence_score >= 0.8
            )
            
            return {
                "overview": {
                    "total_threat_events": total_events,
                    "active_alerts": active_alerts,
                    "events_last_24h": recent_events,
                    "users_monitored": total_users_monitored,
                    "behavioral_patterns_established": patterns_established
                },
                "threat_distribution": {
                    "by_category": dict(category_counts),
                    "by_level": dict(level_counts)
                },
                "detection_rules": {
                    "total_rules": len(self.detection_rules),
                    "active_rules": list(self.detection_rules.keys())
                },
                "configuration": {
                    "anomaly_threshold": self.config.get("anomaly_threshold"),
                    "min_baseline_samples": self.config.get("min_baseline_samples"),
                    "behavioral_learning_enabled": self.config.get("behavioral_learning_enabled"),
                    "real_time_detection": self.config.get("real_time_detection")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get threat analytics: {e}")
            return {"error": f"Failed to get threat analytics: {e}"}