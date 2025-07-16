"""
Global pytest configuration for async test support.
"""

import pytest

# Configure pytest-asyncio globally
pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope='session')
def event_loop_policy():
    """Set event loop policy for async tests."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()