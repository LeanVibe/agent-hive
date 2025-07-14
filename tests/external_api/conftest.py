"""
Pytest configuration for External API Integration tests.
"""

import pytest
import pytest_asyncio
import sys
from pathlib import Path

# Add project root to sys.path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import external API components for testing
from external_api.webhook_server import WebhookServer
from external_api.api_gateway import ApiGateway
from external_api.event_streaming import EventStreaming
from external_api.models import (
    WebhookConfig,
    ApiGatewayConfig,
    EventStreamConfig,
    WebhookEvent,
    ApiRequest,
    StreamEvent
)

# Add async marker to all test functions
pytest.mark.asyncio = pytest.mark.asyncio