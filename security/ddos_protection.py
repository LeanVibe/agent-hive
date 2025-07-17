"""
DDoS Protection System
=====================

Advanced DDoS protection with traffic analysis, request pattern detection,
IP reputation scoring, and automated mitigation strategies.
"""

import asyncio
import json
import time
import logging
import hashlib
import statistics
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import ipaddress
import re

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackType(Enum):
    """Types of detected attacks"""
    VOLUMETRIC = "volumetric"
    PROTOCOL = "protocol"
    APPLICATION = "application"
    SLOW_LORIS = "slow_loris"
    HTTP_FLOOD = "http_flood"
    DISTRIBUTED = "distributed"


class MitigationAction(Enum):
    """Mitigation actions"""
    MONITOR = "monitor"
    CHALLENGE = "challenge"
    RATE_LIMIT = "rate_limit"
    BLOCK_IP = "block_ip"
    BLOCK_SUBNET = "block_subnet"
    CAPTCHA = "captcha"


@dataclass
class TrafficPattern:
    """Traffic pattern analysis data"""
    ip_address: str
    request_count: int = 0
    bytes_sent: int = 0
    user_agents: Set[str] = field(default_factory=set)
    referrers: Set[str] = field(default_factory=set)
    endpoints: Set[str] = field(default_factory=set)
    request_intervals: deque = field(default_factory=lambda: deque(maxlen=100))
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    geolocation: Optional[Dict] = None
    reputation_score: float = 0.0
    threat_level: ThreatLevel = ThreatLevel.LOW


@dataclass
class DDoSAlert:
    """DDoS attack alert"""
    attack_type: AttackType
    threat_level: ThreatLevel
    source_ips: List[str]
    target_endpoints: List[str]
    attack_volume: int
    start_time: float
    detection_time: float
    mitigation_actions: List[MitigationAction]
    confidence_score: float
    additional_data: Dict[str, Any] = field(default_factory=dict)


class DDoSDetectionEngine:
    """Advanced DDoS detection engine with multiple algorithms"""
    
    def __init__(self, redis_client: redis.Redis, config: Dict[str, Any]):
        self.redis = redis_client
        self.config = config
        self.traffic_patterns: Dict[str, TrafficPattern] = {}
        self.suspicious_ips: Set[str] = set()
        self.blocked_ips: Set[str] = set()
        self.attack_signatures = self._load_attack_signatures()
        
        # Detection thresholds
        self.volume_threshold = config.get('volume_threshold', 1000)  # requests/minute
        self.connection_threshold = config.get('connection_threshold', 100)  # concurrent connections
        self.request_size_threshold = config.get('request_size_threshold', 1024 * 1024)  # 1MB
        self.pattern_anomaly_threshold = config.get('pattern_anomaly_threshold', 0.8)
        
        # Time windows
        self.analysis_window = config.get('analysis_window', 300)  # 5 minutes
        self.pattern_window = config.get('pattern_window', 60)  # 1 minute
        
    def _load_attack_signatures(self) -> Dict[str, Any]:
        """Load known attack signatures and patterns"""
        return {
            'bot_user_agents': [
                'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
                'python-requests', 'apache-httpclient', 'java/'
            ],
            'suspicious_headers': [
                'X-Forwarded-For: 127.0.0.1',
                'X-Real-IP: localhost',
                'User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
            ],
            'attack_patterns': [
                r'\.\./',  # Path traversal
                r'<script',  # XSS attempts
                r'union\s+select',  # SQL injection
                r'eval\s*\(',  # Code injection
            ]
        }
    
    async def analyze_request(self, request_data: Dict[str, Any]) -> Optional[DDoSAlert]:
        """Analyze incoming request for DDoS patterns"""
        ip = request_data.get('ip')
        if not ip:
            return None
        
        current_time = time.time()
        
        # Update traffic pattern
        pattern = self._update_traffic_pattern(ip, request_data, current_time)
        
        # Run detection algorithms
        alerts = []
        
        # Volume-based detection
        volume_alert = await self._detect_volume_attack(pattern, current_time)
        if volume_alert:
            alerts.append(volume_alert)
        
        # Pattern-based detection
        pattern_alert = await self._detect_pattern_anomaly(pattern, request_data)
        if pattern_alert:
            alerts.append(pattern_alert)
        
        # Distributed attack detection
        distributed_alert = await self._detect_distributed_attack(current_time)
        if distributed_alert:
            alerts.append(distributed_alert)
        
        # Application layer attack detection
        app_alert = await self._detect_application_attack(request_data)
        if app_alert:
            alerts.append(app_alert)
        
        # Return highest severity alert
        if alerts:
            return max(alerts, key=lambda x: x.threat_level.value)
        
        return None
    
    def _update_traffic_pattern(self, ip: str, request_data: Dict[str, Any], 
                               current_time: float) -> TrafficPattern:
        """Update traffic pattern for IP address"""
        if ip not in self.traffic_patterns:
            self.traffic_patterns[ip] = TrafficPattern(ip_address=ip)
        
        pattern = self.traffic_patterns[ip]
        pattern.request_count += 1
        pattern.bytes_sent += request_data.get('content_length', 0)
        pattern.last_seen = current_time
        
        # Update request intervals
        if pattern.request_intervals:
            interval = current_time - pattern.request_intervals[-1]
            pattern.request_intervals.append(interval)
        else:
            pattern.request_intervals.append(0)
        
        # Update metadata
        if 'user_agent' in request_data:
            pattern.user_agents.add(request_data['user_agent'])
        
        if 'referrer' in request_data:
            pattern.referrers.add(request_data['referrer'])
        
        if 'endpoint' in request_data:
            pattern.endpoints.add(request_data['endpoint'])
        
        return pattern
    
    async def _detect_volume_attack(self, pattern: TrafficPattern, 
                                   current_time: float) -> Optional[DDoSAlert]:
        """Detect volumetric attacks based on request rates"""
        # Calculate requests per minute
        time_window = min(self.analysis_window, current_time - pattern.first_seen)
        if time_window < 60:  # Need at least 1 minute of data
            return None
        
        requests_per_minute = (pattern.request_count / time_window) * 60
        
        if requests_per_minute > self.volume_threshold:
            threat_level = ThreatLevel.HIGH if requests_per_minute > self.volume_threshold * 2 else ThreatLevel.MEDIUM
            
            return DDoSAlert(
                attack_type=AttackType.VOLUMETRIC,
                threat_level=threat_level,
                source_ips=[pattern.ip_address],
                target_endpoints=list(pattern.endpoints),
                attack_volume=int(requests_per_minute),
                start_time=pattern.first_seen,
                detection_time=current_time,
                mitigation_actions=[MitigationAction.RATE_LIMIT, MitigationAction.CHALLENGE],
                confidence_score=0.8,
                additional_data={'requests_per_minute': requests_per_minute}
            )
        
        return None
    
    async def _detect_pattern_anomaly(self, pattern: TrafficPattern, 
                                     request_data: Dict[str, Any]) -> Optional[DDoSAlert]:
        """Detect pattern anomalies in request behavior"""
        anomaly_score = 0.0
        
        # Check for bot-like user agents
        user_agent = request_data.get('user_agent', '').lower()
        if any(bot in user_agent for bot in self.attack_signatures['bot_user_agents']):
            anomaly_score += 0.3
        
        # Check for suspicious headers
        headers = request_data.get('headers', {})
        for header, value in headers.items():
            header_str = f"{header}: {value}"
            if any(sus in header_str for sus in self.attack_signatures['suspicious_headers']):
                anomaly_score += 0.2
        
        # Check request intervals for bot-like behavior
        if len(pattern.request_intervals) > 10:
            intervals = list(pattern.request_intervals)[-10:]
            if intervals:
                std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
                # Very regular intervals suggest bot behavior
                if std_dev < 0.1:
                    anomaly_score += 0.3
        
        # Check for single user agent across many requests
        if len(pattern.user_agents) == 1 and pattern.request_count > 50:
            anomaly_score += 0.2
        
        # Check for attack patterns in request data
        request_content = json.dumps(request_data).lower()
        for pattern_regex in self.attack_signatures['attack_patterns']:
            if re.search(pattern_regex, request_content):
                anomaly_score += 0.4
        
        if anomaly_score > self.pattern_anomaly_threshold:
            threat_level = ThreatLevel.HIGH if anomaly_score > 0.9 else ThreatLevel.MEDIUM
            
            return DDoSAlert(
                attack_type=AttackType.APPLICATION,
                threat_level=threat_level,
                source_ips=[pattern.ip_address],
                target_endpoints=list(pattern.endpoints),
                attack_volume=pattern.request_count,
                start_time=pattern.first_seen,
                detection_time=time.time(),
                mitigation_actions=[MitigationAction.CHALLENGE, MitigationAction.CAPTCHA],
                confidence_score=anomaly_score,
                additional_data={'anomaly_score': anomaly_score}
            )
        
        return None
    
    async def _detect_distributed_attack(self, current_time: float) -> Optional[DDoSAlert]:
        """Detect distributed attacks across multiple IPs"""
        # Analyze patterns across all IPs in the time window
        recent_patterns = [
            pattern for pattern in self.traffic_patterns.values()
            if current_time - pattern.last_seen < self.analysis_window
        ]
        
        if len(recent_patterns) < 10:  # Need multiple IPs for distributed detection
            return None
        
        # Calculate total request volume
        total_requests = sum(pattern.request_count for pattern in recent_patterns)
        total_rate = total_requests / (self.analysis_window / 60)  # requests per minute
        
        # Check for coordinated attack patterns
        coordination_score = 0.0
        
        # Similar user agents across IPs
        all_user_agents = set()
        for pattern in recent_patterns:
            all_user_agents.update(pattern.user_agents)
        
        if len(all_user_agents) < len(recent_patterns) * 0.3:  # Too few unique user agents
            coordination_score += 0.3
        
        # Similar timing patterns
        if len(recent_patterns) > 5:
            start_times = [pattern.first_seen for pattern in recent_patterns]
            if max(start_times) - min(start_times) < 300:  # All started within 5 minutes
                coordination_score += 0.4
        
        # Similar target endpoints
        common_endpoints = set.intersection(*[pattern.endpoints for pattern in recent_patterns])
        if len(common_endpoints) > 0:
            coordination_score += 0.3
        
        if coordination_score > 0.6 and total_rate > self.volume_threshold * 5:
            return DDoSAlert(
                attack_type=AttackType.DISTRIBUTED,
                threat_level=ThreatLevel.CRITICAL,
                source_ips=[pattern.ip_address for pattern in recent_patterns],
                target_endpoints=list(common_endpoints),
                attack_volume=int(total_rate),
                start_time=min(pattern.first_seen for pattern in recent_patterns),
                detection_time=current_time,
                mitigation_actions=[MitigationAction.BLOCK_SUBNET, MitigationAction.RATE_LIMIT],
                confidence_score=coordination_score,
                additional_data={
                    'participating_ips': len(recent_patterns),
                    'coordination_score': coordination_score
                }
            )
        
        return None
    
    async def _detect_application_attack(self, request_data: Dict[str, Any]) -> Optional[DDoSAlert]:
        """Detect application-layer attacks"""
        # Slow Loris detection
        if request_data.get('connection_time', 0) > 30:  # Long connection time
            return DDoSAlert(
                attack_type=AttackType.SLOW_LORIS,
                threat_level=ThreatLevel.MEDIUM,
                source_ips=[request_data.get('ip')],
                target_endpoints=[request_data.get('endpoint')],
                attack_volume=1,
                start_time=time.time(),
                detection_time=time.time(),
                mitigation_actions=[MitigationAction.BLOCK_IP],
                confidence_score=0.7
            )
        
        # HTTP flood detection (handled by volume detection)
        # Add more application-specific detections here
        
        return None
    
    async def get_threat_intelligence(self, ip: str) -> Dict[str, Any]:
        """Get threat intelligence for an IP address"""
        # Check internal reputation
        pattern = self.traffic_patterns.get(ip)
        if not pattern:
            return {'reputation_score': 0.0, 'threat_level': ThreatLevel.LOW.value}
        
        # Calculate reputation score
        reputation_score = pattern.reputation_score
        
        # Factor in recent behavior
        current_time = time.time()
        if current_time - pattern.last_seen < 3600:  # Active in last hour
            if pattern.request_count > 1000:
                reputation_score -= 0.3
            if len(pattern.user_agents) == 1:
                reputation_score -= 0.2
        
        # Determine threat level
        if reputation_score < -0.5:
            threat_level = ThreatLevel.HIGH
        elif reputation_score < -0.2:
            threat_level = ThreatLevel.MEDIUM
        else:
            threat_level = ThreatLevel.LOW
        
        return {
            'ip_address': ip,
            'reputation_score': reputation_score,
            'threat_level': threat_level.value,
            'first_seen': pattern.first_seen,
            'last_seen': pattern.last_seen,
            'request_count': pattern.request_count,
            'user_agents': list(pattern.user_agents),
            'endpoints': list(pattern.endpoints),
            'is_suspicious': ip in self.suspicious_ips,
            'is_blocked': ip in self.blocked_ips
        }
    
    async def cleanup_old_patterns(self, max_age: int = 3600):
        """Clean up old traffic patterns to prevent memory leaks"""
        current_time = time.time()
        old_ips = [
            ip for ip, pattern in self.traffic_patterns.items()
            if current_time - pattern.last_seen > max_age
        ]
        
        for ip in old_ips:
            del self.traffic_patterns[ip]
        
        logger.info(f"Cleaned up {len(old_ips)} old traffic patterns")


class DDoSMitigationEngine:
    """DDoS mitigation engine with automated response capabilities"""
    
    def __init__(self, redis_client: redis.Redis, config: Dict[str, Any]):
        self.redis = redis_client
        self.config = config
        self.active_mitigations: Dict[str, List[MitigationAction]] = {}
        
    async def apply_mitigation(self, alert: DDoSAlert) -> bool:
        """Apply mitigation actions based on alert"""
        try:
            results = []
            
            for action in alert.mitigation_actions:
                if action == MitigationAction.BLOCK_IP:
                    result = await self._block_ips(alert.source_ips, duration=3600)
                elif action == MitigationAction.RATE_LIMIT:
                    result = await self._apply_rate_limiting(alert.source_ips, alert.attack_volume)
                elif action == MitigationAction.CHALLENGE:
                    result = await self._apply_challenge(alert.source_ips)
                elif action == MitigationAction.CAPTCHA:
                    result = await self._apply_captcha(alert.source_ips)
                elif action == MitigationAction.BLOCK_SUBNET:
                    result = await self._block_subnets(alert.source_ips)
                else:
                    result = True  # MONITOR action
                
                results.append(result)
            
            # Log mitigation
            await self._log_mitigation(alert, results)
            
            return all(results)
            
        except Exception as e:
            logger.error(f"Failed to apply mitigation: {e}")
            return False
    
    async def _block_ips(self, ips: List[str], duration: int = 3600) -> bool:
        """Block IP addresses for specified duration"""
        try:
            expiry_time = time.time() + duration
            
            for ip in ips:
                await self.redis.setex(f"blocked_ip:{ip}", duration, expiry_time)
                self.active_mitigations[ip] = [MitigationAction.BLOCK_IP]
            
            logger.info(f"Blocked {len(ips)} IPs for {duration} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Failed to block IPs: {e}")
            return False
    
    async def _apply_rate_limiting(self, ips: List[str], attack_volume: int) -> bool:
        """Apply enhanced rate limiting to IPs"""
        try:
            # Reduce rate limits based on attack volume
            limit_factor = max(0.1, 1.0 - (attack_volume / 1000))
            
            for ip in ips:
                await self.redis.setex(
                    f"rate_limit_override:{ip}",
                    3600,
                    json.dumps({'factor': limit_factor, 'reason': 'ddos_mitigation'})
                )
                
                current_mitigations = self.active_mitigations.get(ip, [])
                current_mitigations.append(MitigationAction.RATE_LIMIT)
                self.active_mitigations[ip] = current_mitigations
            
            logger.info(f"Applied enhanced rate limiting to {len(ips)} IPs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply rate limiting: {e}")
            return False
    
    async def _apply_challenge(self, ips: List[str]) -> bool:
        """Apply challenge-response to IPs"""
        try:
            for ip in ips:
                await self.redis.setex(f"challenge_required:{ip}", 1800, "true")
                
                current_mitigations = self.active_mitigations.get(ip, [])
                current_mitigations.append(MitigationAction.CHALLENGE)
                self.active_mitigations[ip] = current_mitigations
            
            logger.info(f"Applied challenge requirement to {len(ips)} IPs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply challenge: {e}")
            return False
    
    async def _apply_captcha(self, ips: List[str]) -> bool:
        """Apply CAPTCHA requirement to IPs"""
        try:
            for ip in ips:
                await self.redis.setex(f"captcha_required:{ip}", 1800, "true")
                
                current_mitigations = self.active_mitigations.get(ip, [])
                current_mitigations.append(MitigationAction.CAPTCHA)
                self.active_mitigations[ip] = current_mitigations
            
            logger.info(f"Applied CAPTCHA requirement to {len(ips)} IPs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply CAPTCHA: {e}")
            return False
    
    async def _block_subnets(self, ips: List[str]) -> bool:
        """Block entire subnets for distributed attacks"""
        try:
            # Group IPs by /24 subnet
            subnets = defaultdict(list)
            for ip in ips:
                try:
                    network = ipaddress.ip_network(f"{ip}/24", strict=False)
                    subnets[str(network)].append(ip)
                except ipaddress.AddressValueError:
                    continue
            
            # Block subnets with multiple attacking IPs
            blocked_subnets = []
            for subnet, subnet_ips in subnets.items():
                if len(subnet_ips) > 5:  # Threshold for subnet blocking
                    await self.redis.setex(f"blocked_subnet:{subnet}", 7200, "true")
                    blocked_subnets.append(subnet)
            
            logger.info(f"Blocked {len(blocked_subnets)} subnets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to block subnets: {e}")
            return False
    
    async def _log_mitigation(self, alert: DDoSAlert, results: List[bool]):
        """Log mitigation actions"""
        mitigation_log = {
            'timestamp': time.time(),
            'alert_id': hashlib.md5(f"{alert.start_time}{alert.source_ips[0]}".encode()).hexdigest(),
            'attack_type': alert.attack_type.value,
            'threat_level': alert.threat_level.value,
            'source_ips': alert.source_ips,
            'mitigation_actions': [action.value for action in alert.mitigation_actions],
            'results': results,
            'success': all(results)
        }
        
        await self.redis.lpush("ddos_mitigation_log", json.dumps(mitigation_log))
        await self.redis.ltrim("ddos_mitigation_log", 0, 999)  # Keep last 1000 entries
    
    async def check_mitigation_status(self, ip: str) -> Dict[str, Any]:
        """Check current mitigation status for an IP"""
        status = {
            'ip_address': ip,
            'is_blocked': bool(await self.redis.get(f"blocked_ip:{ip}")),
            'rate_limited': bool(await self.redis.get(f"rate_limit_override:{ip}")),
            'challenge_required': bool(await self.redis.get(f"challenge_required:{ip}")),
            'captcha_required': bool(await self.redis.get(f"captcha_required:{ip}")),
            'active_mitigations': self.active_mitigations.get(ip, [])
        }
        
        return status
    
    async def remove_mitigation(self, ip: str, action: MitigationAction) -> bool:
        """Remove specific mitigation for an IP"""
        try:
            if action == MitigationAction.BLOCK_IP:
                await self.redis.delete(f"blocked_ip:{ip}")
            elif action == MitigationAction.RATE_LIMIT:
                await self.redis.delete(f"rate_limit_override:{ip}")
            elif action == MitigationAction.CHALLENGE:
                await self.redis.delete(f"challenge_required:{ip}")
            elif action == MitigationAction.CAPTCHA:
                await self.redis.delete(f"captcha_required:{ip}")
            
            # Update active mitigations
            if ip in self.active_mitigations:
                self.active_mitigations[ip] = [
                    a for a in self.active_mitigations[ip] if a != action
                ]
                if not self.active_mitigations[ip]:
                    del self.active_mitigations[ip]
            
            logger.info(f"Removed {action.value} mitigation for IP {ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove mitigation: {e}")
            return False


# Example configuration
DEFAULT_DDOS_CONFIG = {
    'volume_threshold': 1000,
    'connection_threshold': 100,
    'request_size_threshold': 1024 * 1024,
    'pattern_anomaly_threshold': 0.8,
    'analysis_window': 300,
    'pattern_window': 60,
    'mitigation_duration': 3600,
    'auto_mitigation': True,
    'alert_webhook': None
}