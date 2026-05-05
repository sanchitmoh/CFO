"""
AI CFO — OpenTelemetry Setup (ADVANCE-001)
Instruments FastAPI, SQLAlchemy, httpx and OpenAI with distributed tracing.
Only active when OTEL_ENABLED=true in environment.

Provides:
  - Auto-instrumentation (FastAPI, SQLAlchemy, httpx)
  - `openai_traced()` context manager for custom OpenAI spans
  - `traced()` decorator for service functions
  - Traceparent middleware for frontend correlation
"""
import functools
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import settings

logger = logging.getLogger(__name__)

# ── Module-level tracer (lazy, returns no-op when OTel disabled) ──
_tracer = None


def _get_tracer():
    """Return the configured tracer, or None if OTel is disabled."""
    global _tracer
    if _tracer is not None:
        return _tracer
    if not settings.OTEL_ENABLED:
        return None
    try:
        from opentelemetry import trace
        _tracer = trace.get_tracer("ai-cfo", "1.0.0")
        return _tracer
    except ImportError:
        return None


# ═══════════════════════════════════════════════════════════════════
# Custom OpenAI tracing context manager
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def openai_traced(operation: str = "chat.completions", **attrs):
    """Wrap an OpenAI API call with a custom span.

    Usage:
        async with openai_traced(model="gpt-4o-mini", stream=True) as span:
            response = await client.chat.completions.create(...)
            if span:
                span.set_attribute("ai.tokens.total", response.usage.total_tokens)
    """
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry import trace

    with tracer.start_as_current_span(
        f"openai.{operation}",
        kind=trace.SpanKind.CLIENT,
    ) as span:
        span.set_attribute("ai.provider", "openai")
        span.set_attribute("ai.operation", operation)
        for k, v in attrs.items():
            span.set_attribute(f"ai.{k}", str(v))

        start = time.perf_counter()
        try:
            yield span
        except Exception as exc:
            span.set_attribute("ai.error", str(exc))
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise
        finally:
            span.set_attribute("ai.duration_ms", round((time.perf_counter() - start) * 1000, 1))


# ═══════════════════════════════════════════════════════════════════
# Decorator for service functions
# ═══════════════════════════════════════════════════════════════════

def traced(name: str | None = None, kind: str = "INTERNAL"):
    """Decorator to trace any async service function.

    Usage:
        @traced("forecast.compute")
        async def compute_forecast(db, workspace_id):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = _get_tracer()
            if tracer is None:
                return await func(*args, **kwargs)

            from opentelemetry import trace
            span_kind = getattr(trace.SpanKind, kind, trace.SpanKind.INTERNAL)
            span_name = name or f"{func.__module__}.{func.__qualname__}"

            with tracer.start_as_current_span(span_name, kind=span_kind) as span:
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as exc:
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise
                finally:
                    span.set_attribute("duration_ms", round((time.perf_counter() - start) * 1000, 1))

        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════
# Traceparent middleware — propagate trace ID to frontend
# ═══════════════════════════════════════════════════════════════════

class TraceparentMiddleware(BaseHTTPMiddleware):
    """Injects `traceparent` header in responses for frontend correlation."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if not settings.OTEL_ENABLED:
            return response

        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                traceparent = (
                    f"00-{format(ctx.trace_id, '032x')}"
                    f"-{format(ctx.span_id, '016x')}"
                    f"-{format(ctx.trace_flags, '02x')}"
                )
                response.headers["traceparent"] = traceparent
        except Exception:
            pass  # Never break a response for tracing

        return response


# ═══════════════════════════════════════════════════════════════════
# Setup — called once from main.py
# ═══════════════════════════════════════════════════════════════════

def setup_telemetry(app) -> None:
    """Instrument the FastAPI app + SQLAlchemy engine with OpenTelemetry.

    Does nothing if OTEL_ENABLED is False — zero overhead in dev.
    """
    # Always add the traceparent middleware (it's a no-op when OTel is off)
    app.add_middleware(TraceparentMiddleware)

    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        # ── Resource (service identity) ───────────────────────────
        resource = Resource.create({
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": "1.0.0",
            "deployment.environment": "production" if not settings.DEBUG else "development",
        })

        # ── Tracer provider + OTLP exporter ───────────────────────
        # HIGH-009: Use secure connections by default. Only allow insecure
        # connections when explicitly configured via OTEL_INSECURE=true.
        # This prevents trace data (SQL queries, user IDs, API calls) from
        # being transmitted over unencrypted gRPC on shared networks.
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=settings.OTEL_INSECURE,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # ── Auto-instrument frameworks ────────────────────────────
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/api/health",  # skip health check noise
        )

        # Instrument the async SQLAlchemy engine
        from database import engine
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,
            enable_commenter=True,
        )

        # Instrument httpx (used by Clerk JWKS, OpenAI, etc.)
        HTTPXClientInstrumentor().instrument()

        logger.info(
            "OpenTelemetry enabled → exporting to %s as '%s'",
            settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            settings.OTEL_SERVICE_NAME,
        )

    except ImportError as e:
        logger.warning(
            "OpenTelemetry packages not installed (%s). "
            "Install with: pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-instrumentation-fastapi "
            "opentelemetry-instrumentation-sqlalchemy "
            "opentelemetry-instrumentation-httpx "
            "opentelemetry-exporter-otlp-proto-grpc",
            e,
        )
