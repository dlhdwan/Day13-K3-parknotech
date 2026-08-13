from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    OTEL_AVAILABLE = False
    trace = None  # type: ignore

_INITIALIZED = False
_PROVIDER: Optional[Any] = None


def is_otel_enabled() -> bool:
    return OTEL_AVAILABLE and os.getenv("OTEL_ENABLED", "false").lower() in ("true", "1", "yes")


def init_otel(service_name: Optional[str] = None, endpoint: Optional[str] = None) -> None:
    global _INITIALIZED, _PROVIDER
    if not OTEL_AVAILABLE or _INITIALIZED or not is_otel_enabled():
        return

    svc_name = service_name or os.getenv("OTEL_SERVICE_NAME", os.getenv("APP_NAME", "day13-observability-lab"))
    otlp_endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    resource = Resource.create({
        "service.name": svc_name,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("APP_ENV", "dev"),
    })
    provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        # Flush every 500ms or 64 spans for near-instant telemetry in Lab UI
        processor = BatchSpanProcessor(exporter, schedule_delay_millis=500, max_export_batch_size=64)
        provider.add_span_processor(processor)
    except Exception:  # pragma: no cover
        pass

    trace.set_tracer_provider(provider)
    _PROVIDER = provider
    _INITIALIZED = True


def get_tracer(name: str = "day13-ai-agent"):
    if not OTEL_AVAILABLE:
        return None
    if not _INITIALIZED and is_otel_enabled():
        init_otel()
    return trace.get_tracer(name)


def flush_otel(timeout_millis: int = 1500) -> None:
    if not is_otel_enabled() or not OTEL_AVAILABLE or _PROVIDER is None:
        return
    try:
        _PROVIDER.force_flush(timeout_millis=timeout_millis)
    except Exception:
        pass


@contextmanager
def trace_span(name: str, attributes: Optional[dict[str, Any]] = None) -> Generator[Any, None, None]:
    if not is_otel_enabled() or not OTEL_AVAILABLE:
        yield None
        return

    if not _INITIALIZED:
        init_otel()

    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                if v is not None:
                    span.set_attribute(k, str(v) if not isinstance(v, (int, float, bool, str)) else v)
        yield span
