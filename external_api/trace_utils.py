"""
Lightweight tracing utilities with optional OpenTelemetry integration.

Provides a no-op tracer by default and a context manager interface that
exposes a hex trace_id and attribute/exception APIs. Safe to import even
when OpenTelemetry is not installed.
"""
from typing import Optional, Dict, Any
import uuid

class _NoopSpanCtx:
    def __init__(self) -> None:
        self._trace_id = uuid.uuid4().hex
    @property
    def trace_id(self) -> str:
        return self._trace_id
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def set_attribute(self, key: str, value: Any) -> None:
        pass
    def record_exception(self, exc: Exception) -> None:
        pass

class _OtelSpanCtx:
    def __init__(self, tracer, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self._tracer = tracer
        self._name = name
        self._attributes = attributes or {}
        self._span = None
        self._cm = None
        self._fallback_id = uuid.uuid4().hex
    def __enter__(self):
        self._cm = self._tracer.start_as_current_span(self._name)
        self._span = self._cm.__enter__()
        try:
            for k, v in self._attributes.items():
                self._span.set_attribute(k, v)
        except Exception:
            pass
        return self
    def __exit__(self, exc_type, exc, tb):
        try:
            if exc is not None:
                self.record_exception(exc)
        finally:
            try:
                self._cm.__exit__(exc_type, exc, tb)
            except Exception:
                pass
        return False
    @property
    def trace_id(self) -> str:
        try:
            ctx = self._span.get_span_context()
            if ctx and getattr(ctx, "trace_id", 0):
                return f"{ctx.trace_id:032x}"
        except Exception:
            pass
        return self._fallback_id
    def set_attribute(self, key: str, value: Any) -> None:
        try:
            self._span.set_attribute(key, value)
        except Exception:
            pass
    def record_exception(self, exc: Exception) -> None:
        try:
            self._span.record_exception(exc)
        except Exception:
            pass

class Tracer:
    def __init__(self, enabled: bool = False, service_name: str = "app") -> None:
        self._enabled = enabled
        self._otel_tracer = None
        if self._enabled:
            try:
                from opentelemetry import trace as _otel_trace  # type: ignore
                self._otel_tracer = _otel_trace.get_tracer(service_name)
            except Exception:
                self._otel_tracer = None
    def trace(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        if self._enabled and self._otel_tracer is not None:
            return _OtelSpanCtx(self._otel_tracer, name, attributes)
        return _NoopSpanCtx()

def get_tracer(service_name: str = "app", enabled: bool = False) -> Tracer:
    return Tracer(enabled=enabled, service_name=service_name)
