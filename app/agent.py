from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .otel_tracing import flush_otel, trace_span
from .pii import hash_user_id, summarize_text
from .prompt_management import resolve_prompt
from .tracing import get_langfuse_client, observe, score_trace, tracing_enabled

from structlog.contextvars import get_contextvars


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(as_type="generation", capture_input=False, capture_output=False)
    def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        started = time.perf_counter()
        user_hash = hash_user_id(user_id)
        cid = get_contextvars().get("correlation_id", "unknown")
        env = os.getenv("APP_ENV", "dev")

        with trace_span("chat_pipeline", {
            "user_id_hash": user_hash,
            "session_id": session_id,
            "feature": feature,
            "correlation_id": cid,
            "app.env": env,
        }) as root_span:
            with trace_span("rag_retrieval", {"feature": feature, "query": summarize_text(message)}) as span:
                docs = retrieve(message)
                if span:
                    span.set_attribute("doc_count", len(docs))

            langfuse_client = get_langfuse_client()
            prompt = resolve_prompt(
                langfuse_client,
                feature=feature,
                docs=docs,
                message=message,
                enabled=tracing_enabled(),
            )

            with trace_span("llm_generate", {
                "gen_ai.system": "anthropic",
                "gen_ai.request.model": self.model,
                "prompt.name": prompt.name,
                "prompt.version": str(prompt.version),
                "prompt.label": prompt.label,
                "prompt.source": prompt.source,
            }) as span:
                response = self.llm.generate(prompt.text)
                if span:
                    span.set_attribute("gen_ai.usage.input_tokens", response.usage.input_tokens)
                    span.set_attribute("gen_ai.usage.output_tokens", response.usage.output_tokens)
                    span.set_attribute("tokens_in", response.usage.input_tokens)
                    span.set_attribute("tokens_out", response.usage.output_tokens)

            quality_score = self._heuristic_quality(message, response.text, docs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

            if root_span:
                root_span.set_attribute("llm.quality_score", quality_score)
                root_span.set_attribute("llm.cost_usd", cost_usd)
                root_span.set_attribute("latency_ms", latency_ms)
                root_span.set_attribute("prompt.version", str(prompt.version))
                root_span.set_attribute("prompt.label", prompt.label)

        trace_metadata = {
            "prompt_name": prompt.name,
            "prompt_label": prompt.label,
            "prompt_version": prompt.version,
            "prompt_source": prompt.source,
        }
        cid = get_contextvars().get("correlation_id")
        if cid:
            trace_metadata["correlation_id"] = cid

        env = os.getenv("APP_ENV", "dev")
        tags = ["lab", feature, self.model]
        if env:
            tags.append(env)

        langfuse_client.update_current_trace(
            name="chat-pipeline",
            input={"message": summarize_text(message)},
            output={"answer": summarize_text(response.text)},
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=tags,
            metadata=trace_metadata,
        )
        langfuse_client.update_current_generation(
            name="llm-generation",
            model=self.model,
            input={"prompt": prompt.text},
            output={"text": response.text},
            metadata={
                "doc_count": len(docs),
                "query_preview": summarize_text(message),
                "prompt_name": prompt.name,
                "prompt_label": prompt.label,
                "prompt_version": prompt.version,
                "prompt_source": prompt.source,
                "prompt_fetch_error": prompt.fetch_error,
            },
            usage_details={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
                "total": response.usage.input_tokens + response.usage.output_tokens,
            },
            cost_details={"total": cost_usd},
            prompt=prompt.managed_prompt,
        )

        score_trace(
            name="heuristic_quality",
            value=quality_score,
            comment=f"Heuristic quality evaluation score for {feature}",
        )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
            feature=feature,
            model=self.model,
            env=env,
        )

        flush_otel()

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)

