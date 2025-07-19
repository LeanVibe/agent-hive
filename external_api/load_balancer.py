"""
Advanced Load Balancer for Service Discovery System

Provides intelligent service load balancing with health-aware distribution,
circuit breaker integration, and multiple balancing algorithms.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from .service_discovery import ServiceDiscovery, ServiceInstance, ServiceStatus


logger = logging.getLogger(__name__)


class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"
    HEALTH_WEIGHTED = "health_weighted"


class HealthStatus(Enum):
    """Instance health status for load balancing."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class LoadBalancingMetrics:
    """Metrics for load balancing decisions."""
    total_requests: int = 0
    active_connections: int = 0
    avg_response_time_ms: float = 0.0
    success_rate: float = 100.0
    last_request_time: Optional[datetime] = None
    health_score: float = 100.0
    weight: float = 1.0
    
    def calculate_health_score(self) -> float:
        """Calculate overall health score from metrics."""
        # Base score on success rate
        health_score = self.success_rate
        
        # Penalty for high response times (>1000ms)
        if self.avg_response_time_ms > 1000:
            health_score *= 0.8
        elif self.avg_response_time_ms > 500:
            health_score *= 0.9
        
        # Penalty for high connection count (load)
        if self.active_connections > 100:
            health_score *= 0.7
        elif self.active_connections > 50:
            health_score *= 0.85
        
        self.health_score = max(0.0, min(100.0, health_score))
        return self.health_score


@dataclass
class LoadBalancerInstance:
    """Load balancer-aware service instance."""
    service_instance: ServiceInstance
    metrics: LoadBalancingMetrics = field(default_factory=LoadBalancingMetrics)
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    circuit_breaker_open: bool = False
    circuit_breaker_open_until: Optional[datetime] = None
    
    @property
    def is_available(self) -> bool:
        """Check if instance is available for requests."""
        if self.circuit_breaker_open:
            if self.circuit_breaker_open_until and datetime.utcnow() > self.circuit_breaker_open_until:
                self.circuit_breaker_open = False
                self.circuit_breaker_open_until = None
            else:
                return False
        
        return self.health_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    @property
    def effective_weight(self) -> float:
        """Calculate effective weight for load balancing."""
        base_weight = self.metrics.weight
        
        # Reduce weight based on health score
        health_factor = self.metrics.health_score / 100.0
        
        # Reduce weight if degraded
        if self.health_status == HealthStatus.DEGRADED:
            health_factor *= 0.5
        
        return base_weight * health_factor


class ServiceLoadBalancer:
    """
    Advanced load balancer for service discovery with health-aware distribution.
    
    Features:
    - Multiple load balancing algorithms
    - Health-aware request routing
    - Circuit breaker integration
    - Real-time metrics tracking
    - Weighted distribution
    - Sticky sessions support
    """
    
    def __init__(self, service_discovery: ServiceDiscovery, config: Dict[str, Any] = None):
        """Initialize service load balancer."""
        self.service_discovery = service_discovery
        self.config = config or {}
        
        # Load balancing configuration
        self.algorithm = LoadBalancingAlgorithm(
            self.config.get("algorithm", LoadBalancingAlgorithm.HEALTH_WEIGHTED.value)
        )
        self.health_check_interval = self.config.get("health_check_interval", 30)
        self.circuit_breaker_threshold = self.config.get("circuit_breaker_threshold", 5)
        self.circuit_breaker_timeout = self.config.get("circuit_breaker_timeout", 60)
        self.sticky_sessions_enabled = self.config.get("sticky_sessions", False)
        
        # Instance tracking
        self.instances: Dict[str, LoadBalancerInstance] = {}
        self.round_robin_counters: Dict[str, int] = {}
        self.sticky_sessions: Dict[str, str] = {}  # session_id -> instance_id
        
        # Health monitoring
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        
        # Request tracking for metrics
        self.request_history: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info(f"ServiceLoadBalancer initialized with algorithm: {self.algorithm.value}")
    
    async def start(self) -> None:
        """Start the load balancer."""
        if self._running:
            return
        
        self._running = True
        
        # Start health monitoring for existing instances
        for instance_id in self.instances:
            await self._start_health_monitoring(instance_id)
        
        logger.info("ServiceLoadBalancer started")
    
    async def stop(self) -> None:
        """Stop the load balancer."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all health check tasks
        for task in self._health_check_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._health_check_tasks.values(), return_exceptions=True)
        self._health_check_tasks.clear()
        
        logger.info("ServiceLoadBalancer stopped")
    
    async def add_instance(self, service_instance: ServiceInstance) -> bool:
        """Add service instance to load balancer."""
        try:
            lb_instance = LoadBalancerInstance(
                service_instance=service_instance,
                health_status=HealthStatus.UNKNOWN
            )
            
            self.instances[service_instance.service_id] = lb_instance
            self.request_history[service_instance.service_id] = []
            
            # Start health monitoring if running
            if self._running:
                await self._start_health_monitoring(service_instance.service_id)
            
            logger.info(f"Added instance {service_instance.service_id} to load balancer")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add instance {service_instance.service_id}: {e}")
            return False
    
    async def remove_instance(self, service_id: str) -> bool:
        """Remove service instance from load balancer."""
        try:
            if service_id not in self.instances:
                return False
            
            # Cancel health monitoring
            if service_id in self._health_check_tasks:
                self._health_check_tasks[service_id].cancel()
                del self._health_check_tasks[service_id]
            
            # Clean up data
            del self.instances[service_id]
            self.request_history.pop(service_id, None)
            self.round_robin_counters.pop(service_id, None)
            
            # Remove sticky sessions
            sessions_to_remove = [
                session_id for session_id, instance_id in self.sticky_sessions.items()
                if instance_id == service_id
            ]
            for session_id in sessions_to_remove:
                del self.sticky_sessions[session_id]
            
            logger.info(f"Removed instance {service_id} from load balancer")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove instance {service_id}: {e}")
            return False
    
    async def select_instance(self, service_name: str, session_id: Optional[str] = None,
                            request_metadata: Optional[Dict[str, Any]] = None) -> Optional[ServiceInstance]:
        """
        Select best service instance using configured load balancing algorithm.
        
        Args:
            service_name: Name of service to select instance for
            session_id: Optional session ID for sticky sessions
            request_metadata: Optional metadata for routing decisions
            
        Returns:
            Selected service instance or None if none available
        """
        try:
            # Get available instances for service
            available_instances = await self._get_available_instances(service_name)
            
            if not available_instances:
                logger.warning(f"No available instances for service {service_name}")
                return None
            
            # Check for sticky session
            if self.sticky_sessions_enabled and session_id:
                sticky_instance_id = self.sticky_sessions.get(session_id)
                if sticky_instance_id and sticky_instance_id in self.instances:
                    sticky_instance = self.instances[sticky_instance_id]
                    if sticky_instance.is_available and sticky_instance.service_instance.service_name == service_name:
                        logger.debug(f"Using sticky session for {session_id} -> {sticky_instance_id}")
                        return sticky_instance.service_instance
                    else:
                        # Remove invalid sticky session
                        del self.sticky_sessions[session_id]
            
            # Select instance using configured algorithm
            selected_instance = await self._select_by_algorithm(available_instances, request_metadata)
            
            if selected_instance and self.sticky_sessions_enabled and session_id:
                # Create sticky session
                self.sticky_sessions[session_id] = selected_instance.service_instance.service_id
            
            return selected_instance.service_instance if selected_instance else None
            
        except Exception as e:
            logger.error(f"Error selecting instance for {service_name}: {e}")
            return None
    
    async def record_request_result(self, instance_id: str, success: bool,
                                  response_time_ms: float, error: Optional[str] = None) -> None:
        """Record request result for metrics tracking."""
        try:
            if instance_id not in self.instances:
                return
            
            instance = self.instances[instance_id]
            metrics = instance.metrics
            
            # Update metrics
            metrics.total_requests += 1
            metrics.last_request_time = datetime.utcnow()
            
            # Update response time (exponential moving average)
            if metrics.avg_response_time_ms == 0:
                metrics.avg_response_time_ms = response_time_ms
            else:
                # Use 0.1 weight for new values (smoother averaging)
                metrics.avg_response_time_ms = (
                    0.9 * metrics.avg_response_time_ms + 0.1 * response_time_ms
                )
            
            # Track request in history
            request_record = {
                "timestamp": datetime.utcnow(),
                "success": success,
                "response_time_ms": response_time_ms,
                "error": error
            }
            
            self.request_history[instance_id].append(request_record)
            
            # Keep only last 100 requests for memory efficiency
            if len(self.request_history[instance_id]) > 100:
                self.request_history[instance_id] = self.request_history[instance_id][-50:]
            
            # Calculate success rate from recent requests
            recent_requests = self.request_history[instance_id][-20:]  # Last 20 requests
            if recent_requests:
                successes = sum(1 for r in recent_requests if r["success"])
                metrics.success_rate = (successes / len(recent_requests)) * 100
            
            # Update health score
            metrics.calculate_health_score()
            
            # Circuit breaker logic
            if not success:
                await self._check_circuit_breaker(instance_id)
            
            logger.debug(f"Recorded request result for {instance_id}: success={success}, "
                        f"response_time={response_time_ms}ms, health_score={metrics.health_score}")
            
        except Exception as e:
            logger.error(f"Error recording request result for {instance_id}: {e}")
    
    async def get_load_balancing_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancing statistics."""
        try:
            total_instances = len(self.instances)
            healthy_instances = sum(
                1 for instance in self.instances.values()
                if instance.health_status == HealthStatus.HEALTHY
            )
            degraded_instances = sum(
                1 for instance in self.instances.values()
                if instance.health_status == HealthStatus.DEGRADED
            )
            
            total_requests = sum(instance.metrics.total_requests for instance in self.instances.values())
            avg_response_time = 0.0
            if self.instances:
                avg_response_time = sum(
                    instance.metrics.avg_response_time_ms for instance in self.instances.values()
                ) / len(self.instances)
            
            circuit_breakers_open = sum(
                1 for instance in self.instances.values()
                if instance.circuit_breaker_open
            )
            
            # Instance details
            instance_stats = {}
            for instance_id, instance in self.instances.items():
                instance_stats[instance_id] = {
                    "service_name": instance.service_instance.service_name,
                    "host": instance.service_instance.host,
                    "port": instance.service_instance.port,
                    "health_status": instance.health_status.value,
                    "health_score": instance.metrics.health_score,
                    "total_requests": instance.metrics.total_requests,
                    "success_rate": instance.metrics.success_rate,
                    "avg_response_time_ms": instance.metrics.avg_response_time_ms,
                    "active_connections": instance.metrics.active_connections,
                    "circuit_breaker_open": instance.circuit_breaker_open,
                    "effective_weight": instance.effective_weight,
                    "is_available": instance.is_available
                }
            
            return {
                "algorithm": self.algorithm.value,
                "total_instances": total_instances,
                "healthy_instances": healthy_instances,
                "degraded_instances": degraded_instances,
                "unhealthy_instances": total_instances - healthy_instances - degraded_instances,
                "circuit_breakers_open": circuit_breakers_open,
                "total_requests": total_requests,
                "avg_response_time_ms": round(avg_response_time, 2),
                "sticky_sessions_enabled": self.sticky_sessions_enabled,
                "active_sticky_sessions": len(self.sticky_sessions),
                "instance_details": instance_stats,
                "configuration": {
                    "health_check_interval": self.health_check_interval,
                    "circuit_breaker_threshold": self.circuit_breaker_threshold,
                    "circuit_breaker_timeout": self.circuit_breaker_timeout
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting load balancing stats: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _get_available_instances(self, service_name: str) -> List[LoadBalancerInstance]:
        """Get available instances for a service."""
        available = []
        
        for instance in self.instances.values():
            if (instance.service_instance.service_name == service_name and 
                instance.is_available):
                available.append(instance)
        
        return available
    
    async def _select_by_algorithm(self, instances: List[LoadBalancerInstance],
                                 request_metadata: Optional[Dict[str, Any]] = None) -> Optional[LoadBalancerInstance]:
        """Select instance using configured algorithm."""
        if not instances:
            return None
        
        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return self._select_round_robin(instances)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return self._select_least_connections(instances)
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin(instances)
        elif self.algorithm == LoadBalancingAlgorithm.RANDOM:
            return self._select_random(instances)
        elif self.algorithm == LoadBalancingAlgorithm.CONSISTENT_HASH:
            return self._select_consistent_hash(instances, request_metadata)
        elif self.algorithm == LoadBalancingAlgorithm.HEALTH_WEIGHTED:
            return self._select_health_weighted(instances)
        else:
            # Default to health-weighted
            return self._select_health_weighted(instances)
    
    def _select_round_robin(self, instances: List[LoadBalancerInstance]) -> LoadBalancerInstance:
        """Round robin selection."""
        service_name = instances[0].service_instance.service_name
        
        if service_name not in self.round_robin_counters:
            self.round_robin_counters[service_name] = 0
        
        index = self.round_robin_counters[service_name] % len(instances)
        self.round_robin_counters[service_name] += 1
        
        return instances[index]
    
    def _select_least_connections(self, instances: List[LoadBalancerInstance]) -> LoadBalancerInstance:
        """Least connections selection."""
        return min(instances, key=lambda x: x.metrics.active_connections)
    
    def _select_weighted_round_robin(self, instances: List[LoadBalancerInstance]) -> LoadBalancerInstance:
        """Weighted round robin selection."""
        # Create weighted list based on effective weights
        weighted_instances = []
        for instance in instances:
            weight = max(1, int(instance.effective_weight * 10))  # Scale weight for selection
            weighted_instances.extend([instance] * weight)
        
        if not weighted_instances:
            return instances[0]
        
        service_name = instances[0].service_instance.service_name
        if service_name not in self.round_robin_counters:
            self.round_robin_counters[service_name] = 0
        
        index = self.round_robin_counters[service_name] % len(weighted_instances)
        self.round_robin_counters[service_name] += 1
        
        return weighted_instances[index]
    
    def _select_random(self, instances: List[LoadBalancerInstance]) -> LoadBalancerInstance:
        """Random selection."""
        return random.choice(instances)
    
    def _select_consistent_hash(self, instances: List[LoadBalancerInstance],
                              request_metadata: Optional[Dict[str, Any]] = None) -> LoadBalancerInstance:
        """Consistent hash selection."""
        # Use client IP or session ID for hashing
        hash_key = "default"
        if request_metadata:
            hash_key = request_metadata.get("client_ip", request_metadata.get("session_id", "default"))
        
        # Create hash
        hash_value = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
        index = hash_value % len(instances)
        
        return instances[index]
    
    def _select_health_weighted(self, instances: List[LoadBalancerInstance]) -> LoadBalancerInstance:
        """Health-weighted selection (recommended)."""
        # Calculate total weight
        total_weight = sum(instance.effective_weight for instance in instances)
        
        if total_weight == 0:
            return random.choice(instances)
        
        # Random selection based on weights
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for instance in instances:
            current_weight += instance.effective_weight
            if random_value <= current_weight:
                return instance
        
        # Fallback to last instance
        return instances[-1]
    
    async def _start_health_monitoring(self, instance_id: str) -> None:
        """Start health monitoring for an instance."""
        if instance_id in self._health_check_tasks:
            return
        
        self._health_check_tasks[instance_id] = asyncio.create_task(
            self._health_monitor_loop(instance_id)
        )
    
    async def _health_monitor_loop(self, instance_id: str) -> None:
        """Health monitoring loop for an instance."""
        while self._running and instance_id in self.instances:
            try:
                instance = self.instances[instance_id]
                
                # Perform health check
                is_healthy = await self._perform_health_check(instance.service_instance)
                
                # Update health status
                old_status = instance.health_status
                
                if is_healthy:
                    if instance.metrics.health_score > 80:
                        instance.health_status = HealthStatus.HEALTHY
                    elif instance.metrics.health_score > 50:
                        instance.health_status = HealthStatus.DEGRADED
                    else:
                        instance.health_status = HealthStatus.UNHEALTHY
                else:
                    instance.health_status = HealthStatus.UNHEALTHY
                
                instance.last_health_check = datetime.utcnow()
                
                # Log status changes
                if old_status != instance.health_status:
                    logger.info(f"Health status changed for {instance_id}: "
                              f"{old_status.value} -> {instance.health_status.value}")
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error for {instance_id}: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_check(self, service_instance: ServiceInstance) -> bool:
        """Perform health check on service instance."""
        # Delegate to service discovery's health check
        return await self.service_discovery._perform_health_check(service_instance)
    
    async def _check_circuit_breaker(self, instance_id: str) -> None:
        """Check if circuit breaker should be triggered."""
        if instance_id not in self.instances:
            return
        
        instance = self.instances[instance_id]
        
        # Get recent failures
        recent_requests = self.request_history[instance_id][-self.circuit_breaker_threshold:]
        recent_failures = [r for r in recent_requests if not r["success"]]
        
        # Check if we should open circuit breaker
        if (len(recent_requests) >= self.circuit_breaker_threshold and
            len(recent_failures) >= self.circuit_breaker_threshold):
            
            instance.circuit_breaker_open = True
            instance.circuit_breaker_open_until = (
                datetime.utcnow() + timedelta(seconds=self.circuit_breaker_timeout)
            )
            
            logger.warning(f"Circuit breaker opened for {instance_id} due to {len(recent_failures)} failures")