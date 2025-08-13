import asyncio
from typing import Any, Dict, Optional

class MockAiohttpResponse:
    def __init__(self, status: int = 200, body: str = "OK", headers: Optional[Dict[str, str]] = None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    async def text(self) -> str:
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

class MockAiohttpSession:
    """
    Minimal aiohttp.ClientSession mock that supports both awaited-request and
    async-context-managed response patterns used in tests.

    Example usage:
      session = MockAiohttpSession(response=MockAiohttpResponse(status=200))
      pending = session.get("http://host/health")
      # Either:
      async with pending as resp:
          assert 200 <= resp.status < 300
      # Or:
      resp = await pending
          assert 200 <= resp.status < 300
    """

    def __init__(self, response: Optional[MockAiohttpResponse] = None):
        self._response = response or MockAiohttpResponse()
        self.closed = False

    # Simulate aiohttp.ClientSession.request
    def request(self, method: str, url: str, **kwargs: Any):
        return self._response

    # Convenience shorthands
    def get(self, url: str, **kwargs: Any):
        return self._response

    def post(self, url: str, **kwargs: Any):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.closed = True
        return False
