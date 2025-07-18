"""
Simple Service Discovery - Minimal implementation for service registration and lookup.

This module provides basic service discovery functionality with a focus on
simplicity and reliability.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class Service:
    """Service information."""
    service_id: str
    name: str
    host: str
    port: int
    status: str = "healthy"
    
    def endpoint(self) -> str:
        """Get service endpoint URL."""
        return f"http://{self.host}:{self.port}"


class SimpleServiceDiscovery:
    """
    Simple service discovery implementation.
    
    Provides basic service registration and lookup functionality.
    """
    
    def __init__(self):
        """Initialize service discovery."""
        self.services: Dict[str, Service] = {}
        self.registered_at: Dict[str, datetime] = {}
        logger.info("SimpleServiceDiscovery initialized")
    
    def register(self, service: Service) -> bool:
        """
        Register a service.
        
        Args:
            service: Service to register
            
        Returns:
            True if successful
        """
        try:
            self.services[service.service_id] = service
            self.registered_at[service.service_id] = datetime.now()
            logger.info(f"Registered service {service.service_id}: {service.endpoint()}")
            return True
        except Exception as e:
            logger.error(f"Failed to register service {service.service_id}: {e}")
            return False
    
    def unregister(self, service_id: str) -> bool:
        """
        Unregister a service.
        
        Args:
            service_id: ID of service to remove
            
        Returns:
            True if successful
        """
        try:
            if service_id in self.services:
                del self.services[service_id]
                del self.registered_at[service_id]
                logger.info(f"Unregistered service {service_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister service {service_id}: {e}")
            return False
    
    def find_by_name(self, name: str) -> List[Service]:
        """
        Find services by name.
        
        Args:
            name: Service name to search for
            
        Returns:
            List of matching services
        """
        return [
            service for service in self.services.values()
            if service.name == name and service.status == "healthy"
        ]
    
    def get_service(self, service_id: str) -> Optional[Service]:
        """
        Get service by ID.
        
        Args:
            service_id: Service ID to lookup
            
        Returns:
            Service if found, None otherwise
        """
        return self.services.get(service_id)
    
    def list_all(self) -> List[Service]:
        """
        List all registered services.
        
        Returns:
            List of all services
        """
        return list(self.services.values())
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get discovery statistics.
        
        Returns:
            Statistics dictionary
        """
        healthy = sum(1 for s in self.services.values() if s.status == "healthy")
        return {
            "total_services": len(self.services),
            "healthy_services": healthy,
            "unique_names": len(set(s.name for s in self.services.values()))
        }