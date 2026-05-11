"""
graph/agent.py
LangGraph Customer Support Agent.
Nodes: input_guard → retrieve → generate → output_guard → evaluate → [hitl?]
"""

import os
import time
import uuid
from typing import TypedDict, Annotated, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

import utils.database as db
from rag.knowledge_base import get_kb
from guardrails.rules import check_input, check_output, assess_escalation_need
from monitoring.langfuse_tracker import get_tracer
from monitoring.evaluator import evaluate_response
from utils.telegram_hitl import notify_escalation, notify_new_ticket

STORE = os.getenv("STORE_NAME", "TechStore Indonesia")
STORE_PHONE = os.getenv("STORE_PHONE", "0800-123-4567")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "8"))


# ── State ──────────────────────────────────────────────────────────────────────
class SupportState(TypedDict):
    conv_id:      str
    user_name:    str
    user_input:   str
    context:      str          # RAG context
    response:     str          # Final response to user
    messages:     list         # Full chat history
    turn_count:   int
    escalated:    bool
    blocked:      bool
    block_msg:    str
    eval_scores:  dict
    tracer:       object       # Langfuse tracer (not serializable, handled carefully)


# ── LLM Factory ───────────────────────────────────────────────────────────────
def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                temperature=0.3,
            )
            # Test koneksi
            llm.invoke("test")
            return llm
        except Exception as e:
            print(f"⚠️  Ollama tidak tersedia ({e}), fallback ke Groq...")

    # Fallback: Groq
    from langchain_groq import ChatGroq
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.3,
    )


SYSTEM_PROMPT = f"""Kamu adalah {STORE} Virtual Assistant — agen customer support profesional.

KEPRIBADIAN:
- Ramah, sopan, dan empatik
- Fokus membantu pelanggan menyelesaikan masalah
- Jujur dan transparan soal keterbatasan
- Gunakan Bahasa Indonesia yang natural dan mudah dipahami

TUGAS UTAMA:
1. Jawab pertanyaan tentang produk, harga, stok, dan spesifikasi
2. Bantu proses pemesanan, pengiriman, dan pembayaran
3. Tangani keluhan dengan empati dan solusi konkret
4. Arahkan ke garansi dan prosedur return jika diperlukan

PANDUAN MENJAWAB:
- Selalu gunakan informasi dari konteks yang diberikan
- Jika informasi tidak ada di konteks, katakan jujur dan sarankan hubungi CS langsung
- Jangan pernah mengarang fakta, harga, atau kebijakan
- Untuk masalah kompleks yang butuh verifikasi data order, minta pelanggan hubungi {STORE_PHONE}
- Selalu akhiri dengan tawaran bantuan lanjutan

BATASAN:
- Tidak bisa akses sistem order/pembayaran secara langsung
- Tidak bisa proses refund langsung (arahkan ke prosedur)
- Tidak bisa jawab di luar topik produk dan layanan toko
"""


# ── Node 1: Input Guardrail ────────────────────────────────────────────────────
def node_input_guard(state: SupportState) -> SupportState:
    user_input = state["user_input"]
    conv_id    = state["conv_id"]
    tracer     = state.get("tracer")

    result = check_input(user_input, conv_id)

    if tracer:
        try:
            tracer.log_guardrail("input", result.passed, result.reason)
        except Exception:
            pass

    db.log_guardrail(conv_id, user_input, result.reason, result.action)

    if result.action == "block":
        return {**state, "blocked": True, "block_msg": result.response}

    if result.action == "warn":
        return {**state, "blocked": True, "block_msg": result.response}

    # Jika action == "escalate", tetap proses tapi tandai untuk eskalasi
    return {**state, "blocked": False, "block_msg": ""}


# ── Node 2: RAG Retrieval ──────────────────────────────────────────────────────
def node_retrieve(state: SupportState) -> SupportState:
    if state.get("blocked"):
        return state

    start  = time.time()
    kb     = get_kb()
    tracer = state.get("tracer")

    context = kb.search_all(state["user_input"], n=3)
    latency = int((time.time() - start) * 1000)

    if tracer:
        try:
            tracer.log_retrieval(state["user_input"], [context[:200]], latency)
        except Exception:
            pass

    return {**state, "context": context}


# ── Node 3: Generate Response ──────────────────────────────────────────────────
def node_generate(state: SupportState) -> SupportState:
    if state.get("blocked"):
        return state

    start    = time.time()
    llm      = get_llm()
    tracer   = state.get("tracer")
    conv_id  = state["conv_id"]
    messages = state.get("messages", [])

    # Susun prompt dengan konteks RAG
    context_block = (
        f"\n\nKONTEKS INFORMASI (gunakan ini untuk menjawab):\n{state['context']}"
        if state.get("context")
        else ""
    )

    # Susun history percakapan untuk LLM
    lc_messages = [SystemMessage(content=SYSTEM_PROMPT + context_block)]
    for m in messages[-8:]:   # Max 8 pesan terakhir untuk context window
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
    lc_messages.append(HumanMessage(content=state["user_input"]))

    try:
        resp    = llm.invoke(lc_messages)
        response = resp.content
        latency  = int((time.time() - start) * 1000)
        tokens   = getattr(resp, "usage_metadata", {})
        total_t  = tokens.get("total_tokens", 0) if isinstance(tokens, dict) else 0

        if tracer:
            try:
                tracer.log_llm_call(
                    prompt=state["user_input"],
                    response=response,
                    model=os.getenv("OLLAMA_MODEL", os.getenv("GROQ_MODEL", "")),
                    tokens=total_t,
                    latency_ms=latency,
                )
            except Exception:
                pass

        # Simpan pesan ke DB
        db.add_message(conv_id, "user", state["user_input"])
        db.add_message(conv_id, "assistant", response, tokens=total_t, latency_ms=latency)

    except Exception as e:
        response = (
            f"Maaf, terjadi kendala teknis saat memproses pesanmu. "
            f"Silakan coba lagi atau hubungi CS kami di {STORE_PHONE}. 🙏"
        )
        db.add_message(conv_id, "user", state["user_input"])
        db.add_message(conv_id, "assistant", response)

    # Update messages history
    new_messages = messages + [
        {"role": "user",      "content": state["user_input"]},
        {"role": "assistant", "content": response},
    ]

    return {
        **state,
        "response": response,
        "messages": new_messages,
        "turn_count": state.get("turn_count", 0) + 1,
    }


# ── Node 4: Output Guardrail ───────────────────────────────────────────────────
def node_output_guard(state: SupportState) -> SupportState:
    if state.get("blocked"):
        return state

    result = check_output(state.get("response", ""))
    tracer = state.get("tracer")

    if tracer:
        try:
            tracer.log_guardrail("output", result.passed, result.reason)
        except Exception:
            pass

    if not result.passed:
        override = result.response
        db.add_message(state["conv_id"], "assistant", override)
        return {**state, "response": override}

    return state


# ── Node 5: Evaluate Response ──────────────────────────────────────────────────
def node_evaluate(state: SupportState) -> SupportState:
    if state.get("blocked"):
        return state

    scores = evaluate_response(
        user_query=state["user_input"],
        agent_response=state.get("response", ""),
        context=state.get("context", ""),
        conv_id=state["conv_id"],
    )

    tracer = state.get("tracer")
    if tracer:
        try:
            tracer.score("overall_quality", scores.get("overall", 3) / 5)
            tracer.score("helpfulness", scores.get("helpfulness", 3) / 5)
        except Exception:
            pass

    # Simpan evaluasi ke DB
    for metric in ["relevance", "accuracy", "helpfulness", "tone", "overall"]:
        if metric in scores:
            db.add_evaluation(state["conv_id"], metric, scores[metric])

    return {**state, "eval_scores": scores}


# ── Node 6: HITL Check ────────────────────────────────────────────────────────
def node_hitl_check(state: SupportState) -> SupportState:
    if state.get("blocked") or state.get("escalated"):
        return state

    should_esc, reason = assess_escalation_need(
        user_msg=state["user_input"],
        ai_response=state.get("response", ""),
        turn_count=state.get("turn_count", 0),
    )

    # Juga cek dari input guardrail (keyword eskalasi)
    guardrail_check = check_input(state["user_input"])
    if guardrail_check.action == "escalate":
        should_esc = True
        reason = guardrail_check.reason

    if should_esc:
        conv_id   = state["conv_id"]
        user_name = state["user_name"]
        tracer    = state.get("tracer")

        if tracer:
            try:
                tracer.log_escalation(reason)
            except Exception:
                pass

        # Buat tiket
        ticket_id = db.create_ticket(
            conv_id=conv_id,
            ticket_type="escalation",
            description=f"Alasan: {reason}\nPesan: {state['user_input'][:300]}",
            priority="high" if "penipuan" in reason.lower() else "normal",
        )

        db.update_conversation(conv_id, escalated=1)

        # Kirim notifikasi ke Telegram admin
        notify_escalation(
            conv_id=conv_id,
            user_name=user_name,
            reason=reason,
            last_message=state["user_input"],
            ticket_id=ticket_id,
            priority="high",
        )

        # Tambahkan pesan ke respons bahwa akan diteruskan ke admin
        escalation_note = (
            "\n\n---\n"
            "⚡ **Permintaanmu telah kami eskalasikan ke tim admin kami.** "
            "Tim kami akan menghubungimu dalam 1x24 jam kerja. "
            f"Untuk hal mendesak, hubungi langsung: **{STORE_PHONE}**"
        )
        new_response = state.get("response", "") + escalation_note

        return {**state, "escalated": True, "response": new_response}

    return state


# ── Conditional Edge ──────────────────────────────────────────────────────────
def should_continue(state: SupportState) -> str:
    if state.get("blocked"):
        return "blocked"
    return "continue"


# ── Build Graph ───────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(SupportState)

    graph.add_node("input_guard",  node_input_guard)
    graph.add_node("retrieve",     node_retrieve)
    graph.add_node("generate",     node_generate)
    graph.add_node("output_guard", node_output_guard)
    graph.add_node("evaluate",     node_evaluate)
    graph.add_node("hitl_check",   node_hitl_check)

    graph.set_entry_point("input_guard")

    graph.add_conditional_edges(
        "input_guard",
        should_continue,
        {"blocked": END, "continue": "retrieve"}
    )
    graph.add_edge("retrieve",     "generate")
    graph.add_edge("generate",     "output_guard")
    graph.add_edge("output_guard", "evaluate")
    graph.add_edge("evaluate",     "hitl_check")
    graph.add_edge("hitl_check",   END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# Singleton graph
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Public API ─────────────────────────────────────────────────────────────────
def chat(
    user_input: str,
    conv_id: str,
    user_name: str = "Pelanggan",
    message_history: list = None,
) -> dict:
    """
    Kirim pesan ke agent dan dapatkan respons.

    Returns:
        {
            "response": str,
            "blocked": bool,
            "escalated": bool,
            "eval_scores": dict,
            "turn_count": int,
        }
    """
    graph   = get_graph()
    tracer  = get_tracer(conv_id, user_name)

    # Pastikan konversasi ada di DB
    db.create_conversation(conv_id, user_name)

    # Ambil history dari DB jika tidak diberikan
    if message_history is None:
        message_history = db.get_chat_history(conv_id)

    state: SupportState = {
        "conv_id":     conv_id,
        "user_name":   user_name,
        "user_input":  user_input,
        "context":     "",
        "response":    "",
        "messages":    message_history,
        "turn_count":  len(message_history) // 2,
        "escalated":   False,
        "blocked":     False,
        "block_msg":   "",
        "eval_scores": {},
        "tracer":      tracer,
    }

    config = {"configurable": {"thread_id": conv_id}}
    result = graph.invoke(state, config=config)

    # Tentukan response final
    if result.get("blocked"):
        final_response = result.get("block_msg", "Maaf, tidak dapat memproses permintaan ini.")
    else:
        final_response = result.get("response", "")

    tracer.end(output=final_response[:500])

    return {
        "response":    final_response,
        "blocked":     result.get("blocked", False),
        "escalated":   result.get("escalated", False),
        "eval_scores": result.get("eval_scores", {}),
        "turn_count":  result.get("turn_count", 0),
    }
