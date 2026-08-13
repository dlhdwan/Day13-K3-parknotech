from __future__ import annotations

import os
from collections import Counter
from statistics import mean

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter as PromCounter, Gauge as PromGauge, Histogram as PromHistogram, generate_latest

    PROMETHEUS_AVAILABLE = True

    PROM_REQUESTS_TOTAL = PromCounter(
        "ai_requests_total",
        "Total number of AI requests received",
        ["feature", "model", "env"],
    )
    PROM_ERRORS_TOTAL = PromCounter(
        "ai_requests_failed_total",
        "Total number of failed AI requests",
        ["error_type"],
    )
    PROM_LATENCY_HISTOGRAM = PromHistogram(
        "ai_request_latency_seconds",
        "Request latency distribution in seconds",
        ["feature"],
        buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 2.5, 3.0, 5.0, 10.0),
    )
    PROM_TOKENS_TOTAL = PromCounter(
        "ai_tokens_total",
        "Total tokens processed by type and model",
        ["type", "model"],
    )
    PROM_COST_TOTAL = PromCounter(
        "ai_cost_usd_total",
        "Total estimated cost in USD",
        ["model"],
    )
    PROM_QUALITY_GAUGE = PromGauge(
        "ai_quality_score",
        "Latest response quality score proxy (0 to 1)",
        ["feature"],
    )
except ImportError:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

REQUEST_LATENCIES: list[int] = []
REQUEST_COSTS: list[float] = []
REQUEST_TOKENS_IN: list[int] = []
REQUEST_TOKENS_OUT: list[int] = []
ERRORS: Counter[str] = Counter()
TRAFFIC: int = 0
QUALITY_SCORES: list[float] = []


def record_request(
    latency_ms: int,
    cost_usd: float,
    tokens_in: int,
    tokens_out: int,
    quality_score: float,
    feature: str = "general",
    model: str = "claude-sonnet-4-5",
    env: str | None = None,
) -> None:
    global TRAFFIC
    TRAFFIC += 1
    REQUEST_LATENCIES.append(latency_ms)
    REQUEST_COSTS.append(cost_usd)
    REQUEST_TOKENS_IN.append(tokens_in)
    REQUEST_TOKENS_OUT.append(tokens_out)
    QUALITY_SCORES.append(quality_score)

    if PROMETHEUS_AVAILABLE:
        app_env = env or os.getenv("APP_ENV", "dev")
        PROM_REQUESTS_TOTAL.labels(feature=feature, model=model, env=app_env).inc()
        PROM_LATENCY_HISTOGRAM.labels(feature=feature).observe(latency_ms / 1000.0)
        PROM_TOKENS_TOTAL.labels(type="input", model=model).inc(tokens_in)
        PROM_TOKENS_TOTAL.labels(type="output", model=model).inc(tokens_out)
        PROM_COST_TOTAL.labels(model=model).inc(cost_usd)
        PROM_QUALITY_GAUGE.labels(feature=feature).set(quality_score)


def record_error(error_type: str) -> None:
    ERRORS[error_type] += 1
    if PROMETHEUS_AVAILABLE:
        PROM_ERRORS_TOTAL.labels(error_type=error_type).inc()


def get_prometheus_metrics() -> tuple[bytes, str]:
    if PROMETHEUS_AVAILABLE:
        return generate_latest(), CONTENT_TYPE_LATEST
    return b"", "text/plain"


def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def snapshot() -> dict:
    total_errors = sum(ERRORS.values())
    total_requests = TRAFFIC + total_errors
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0

    return {
        "traffic": TRAFFIC,
        "latency_p50": percentile(REQUEST_LATENCIES, 50),
        "latency_p95": percentile(REQUEST_LATENCIES, 95),
        "latency_p99": percentile(REQUEST_LATENCIES, 99),
        "avg_cost_usd": round(mean(REQUEST_COSTS), 4) if REQUEST_COSTS else 0.0,
        "total_cost_usd": round(sum(REQUEST_COSTS), 4),
        "tokens_in_total": sum(REQUEST_TOKENS_IN),
        "tokens_out_total": sum(REQUEST_TOKENS_OUT),
        "error_rate_pct": round(error_rate, 2),
        "error_breakdown": dict(ERRORS),
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
    }
