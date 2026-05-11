"""
monitoring/langfuse_tracker.py
Langfuse tracing untuk setiap percakapan dan langkah agent.
Gratis: cloud.langfuse.com (50k event/bln) atau self-host Docker.
"""

import os
import time
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

_langfuse = None
_available = False


def _get_client():
    global _langfuse, _available
    if _langfuse is not None:
        return _langfuse

    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not pk or not sk or pk.startswith("pk-lf-xxx"):
        _available = False
        return None

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(public_key=pk, secret_key=sk, host=host)
        _available = True
        print("✅ Langfuse terhubung")
        return _langfuse
    except Exception as e:
        print(f"⚠️  Langfuse tidak tersedia: {e}")
        _available = False
        return None


def is_available() -> bool:
    return _available or (_get_client() is not None)


class ConversationTracer:
    """
    Tracer untuk satu sesi percakapan.
    Otomatis no-op jika Langfuse tidak dikonfigurasi.
    """

    def __init__(self, conv_id: str, user_name: str = "Pelanggan"):
        self.conv_id   = conv_id
        self.user_name = user_name
        self._trace    = None
        self._spans: dict[str, Any] = {}

        client = _get_client()
        if client:
            try:
                self._trace = client.trace(
                    id=conv_id,
                    name="customer_support_conversation",
                    user_id=user_name,
                    metadata={"store": os.getenv("STORE_NAME", "TechStore")},
                )
            except Exception:
                pass

    def span(self, name: str, input_text: str = "") -> "SpanContext":
        return SpanContext(self._trace, name, input_text)

    def log_retrieval(self, query: str, results: list, latency_ms: int = 0):
        if not self._trace:
            return
        try:
            self._trace.span(
                name="rag_retrieval",
                input={"query": query},
                output={"results_count": len(results), "results": results[:2]},
                metadata={"latency_ms": latency_ms},
            )
        except Exception:
            pass

    def log_llm_call(self, prompt: str, response: str,
                     model: str = "", tokens: int = 0, latency_ms: int = 0):
        if not self._trace:
            return
        try:
            self._trace.generation(
                name="llm_response",
                model=model,
                input=prompt[:2000],
                output=response[:2000],
                usage={"total_tokens": tokens},
                metadata={"latency_ms": latency_ms},
            )
        except Exception:
            pass

    def log_guardrail(self, check_type: str, passed: bool, reason: str):
        if not self._trace:
            return
        try:
            self._trace.span(
                name=f"guardrail_{check_type}",
                input={"check": check_type},
                output={"passed": passed, "reason": reason},
                level="DEFAULT" if passed else "WARNING",
            )
        except Exception:
            pass

    def log_escalation(self, reason: str):
        if not self._trace:
            return
        try:
            self._trace.event(
                name="hitl_escalation",
                input={"reason": reason},
                level="WARNING",
            )
        except Exception:
            pass

    def score(self, name: str, value: float, comment: str = ""):
        if not self._trace:
            return
        try:
            self._trace.score(name=name, value=value, comment=comment)
        except Exception:
            pass

    def end(self, output: str = "", metadata: dict = None):
        if not self._trace:
            return
        try:
            self._trace.update(
                output=output[:1000],
                metadata=metadata or {},
            )
            client = _get_client()
            if client:
                client.flush()
        except Exception:
            pass


class SpanContext:
    """Context manager untuk span Langfuse."""

    def __init__(self, trace, name: str, input_text: str):
        self._trace     = trace
        self._name      = name
        self._input     = input_text
        self._span      = None
        self._start     = time.time()

    def __enter__(self):
        if self._trace:
            try:
                self._span = self._trace.span(name=self._name, input=self._input[:500])
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._span:
            latency = int((time.time() - self._start) * 1000)
            try:
                self._span.end(metadata={"latency_ms": latency})
            except Exception:
                pass


def get_tracer(conv_id: str, user_name: str = "Pelanggan") -> ConversationTracer:
    return ConversationTracer(conv_id, user_name)
