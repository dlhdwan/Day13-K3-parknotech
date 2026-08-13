from __future__ import annotations

import os
from fastapi.testclient import TestClient

from app import metrics, otel_tracing
from app.main import app


def test_otel_tracing_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_ENABLED", "false")
    assert not otel_tracing.is_otel_enabled()
    with otel_tracing.trace_span("test_span", {"attr": "value"}) as span:
        assert span is None


def test_otel_tracing_enabled(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_ENABLED", "true")
    assert otel_tracing.is_otel_enabled()
    otel_tracing.init_otel(service_name="test-service", endpoint="http://localhost:4317")
    with otel_tracing.trace_span("test_span", {"key": "123"}) as span:
        if span:
            assert span.is_recording()


def test_prometheus_metrics_recording_and_endpoint() -> None:
    client = TestClient(app)

    # Trigger chat request to populate metrics
    res = client.post(
        "/chat",
        json={"user_id": "u_otel", "session_id": "s_otel", "feature": "qa", "message": "Testing OTel and Prometheus"},
    )
    assert res.status_code == 200

    # Test JSON snapshot response when Accept is default/json
    res_metrics = client.get("/metrics")
    assert res_metrics.status_code == 200
    assert "traffic" in res_metrics.json()

    # Test Prometheus exposition text endpoint /prometheus
    res_prom = client.get("/prometheus")
    assert res_prom.status_code == 200
    assert b"ai_requests_total" in res_prom.content
    assert b"ai_request_latency_seconds" in res_prom.content

    # Test /metrics with Accept: text/plain
    res_prom_accept = client.get("/metrics", headers={"Accept": "text/plain"})
    assert res_prom_accept.status_code == 200
    assert b"ai_tokens_total" in res_prom_accept.content
