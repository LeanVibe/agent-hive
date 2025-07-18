"""
Pytest configuration for External API Integration tests.
"""

import sys
from pathlib import Path

import pytest

# Add project root to sys.path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import external API components for testing

# Add async marker to all test functions
pytest.mark.asyncio = pytest.mark.asyncio
