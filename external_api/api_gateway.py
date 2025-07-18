"""
API Gateway for External API Integration

Provides a unified API interface for external systems to interact with
the LeanVibe Agent Hive orchestration system.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import asdict

from .models import (
    ApiGatewayConfig,
    ApiRequest,
    ApiResponse
)
from .service_discovery import ServiceDiscovery, ServiceInstance
from .auth_middleware import AuthenticationMiddleware, AuthResult


logger = logging.getLogger(__name__)


class ApiGateway:
    """
    API Gateway for routing and managing external API requests.

    Provides authentication, rate limiting, request validation,
    and response formatting for the orchestration system.
    """