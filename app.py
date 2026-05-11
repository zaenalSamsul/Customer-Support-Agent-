"""
app.py
Customer Support Agent — Streamlit Dashboard (Fase 3)
Jalankan: streamlit run app.py
"""

import os
import sys
import uuid
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="CS Agent — TechStore",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: #FFFFFF !important;
    color: #0A0A0A !important;
}
.main { background: #FFFFFF !important; }
.main .block-container { padding: 1.5rem 2rem 3rem !important; max-width: 1300px !important; }

/* Header */
.app-header {
    background: #0A0A0A; border-radius: 14px;
    padding: 1.2rem 1.8rem; margin-bottom: 1.8rem;
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.app-title { font-size: 17px; font-weight: 700; color: #FFFFFF; letter-spacing: -.2px; }
.app-sub   { font-size: 11px; color: #888; margin-top: 3px; }
.app-badge {
    font-size: 10px; font-family: 'JetBrains Mono', monospace;
    background: #1A1A1A; color: #FFFFFF; border: 1px solid #333;
    padding: 5px 12px; border-radius: 20px; white-space: nowrap;
}

/* KPI */
.kpi-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; margin-bottom: 1.5rem; }
.kpi { background: #FFFFFF; border: 1.5px solid #E8E8E8; border-radius: 12px; padding: 14px 16px; transition: border-color .15s; }
.kpi:hover { border-color: #0A0A0A; }
.kpi-label { font-size: 10px; font-weight: 500; color: #888; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 5px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #0A0A0A; line-height: 1; }
.kpi-sub   { font-size: 11px; color: #555; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }
.kpi-green { color: #16A34A !important; }
.kpi-red   { color: #DC2626 !important; }

/* Chat bubbles */
.chat-wrap { max-height: 460px; overflow-y: auto; padding: 4px 0; }
.bubble-user {
    display: flex; justify-content: flex-end; margin: 8px 0;
}
.bubble-bot {
    display: flex; justify-content: flex-start; margin: 8px 0;
}
.bubble-user .msg {
    background: #0A0A0A; color: #FFFFFF;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 16px; max-width: 72%; font-size: 13px; line-height: 1.6;
}
.bubble-bot .msg {
    background: #F5F5F5; color: #0A0A0A;
    border-radius: 18px 18px 18px 4px;
    padding: 10px 16px; max-width: 80%; font-size: 13px; line-height: 1.6;
}
.bubble-meta { font-size: 10px; color: #AAAAAA; margin-top: 3px; padding: 0 6px; }
.badge-esc  { font-size: 10px; background: #FEF2F2; color: #991B1B; border: .5px solid #FECACA; padding: 2px 8px; border-radius: 10px; margin-left: 6px; }
.badge-blk  { font-size: 10px; background: #FEF9C3; color: #854D0E; border: .5px solid #FEF08A; padding: 2px 8px; border-radius: 10px; margin-left: 6px; }
.badge-ok   { font-size: 10px; background: #DCFCE7; color: #15803D; border: .5px solid #BBF7D0; padding: 2px 8px; border-radius: 10px; margin-left: 6px; }

/* Score bar */
.score-row  { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 12px; }
.score-lbl  { width: 90px; color: #555; flex-shrink: 0; }
.score-bar  { flex: 1; height: 5px; background: #F0F0F0; border-radius: 3px; overflow: hidden; }
.score-fill { height: 5px; border-radius: 3px; background: #0A0A0A; }
.score-num  { width: 28px; text-align: right; font-family: 'JetBrains Mono', monospace; color: #0A0A0A; font-size: 11px; font-weight: 500; }

/* Ticket cards */
.ticket {
    background: #FFFFFF; border: 1.5px solid #E8E8E8; border-radius: 10px;
    padding: 14px 16px; margin-bottom: 8px; transition: border-color .15s;
}
.ticket:hover { border-color: #0A0A0A; }
.ticket-title { font-size: 13px; font-weight: 600; color: #0A0A0A; }
.ticket-meta  { font-size: 11px; color: #888; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }
.chip { display: inline-block; font-size: 10px; font-weight: 500; padding: 2px 8px; border-radius: 6px; }
.chip-open   { background: #FEF2F2; color: #991B1B; border: .5px solid #FECACA; }
.chip-done   { background: #DCFCE7; color: #15803D; border: .5px solid #BBF7D0; }
.chip-high   { background: #FEF2F2; color: #991B1B; }
.chip-normal { background: #F5F5F5; color: #555; }

/* Info boxes */
.info-box    { background:#F8F8F8; border:1.5px solid #E8E8E8; border-left:4px solid #0A0A0A; border-radius:0 10px 10px 0; padding:10px 14px; font-size:13px; color:#333; line-height:1.6; margin:.6rem 0; }
.success-box { background:#F0FDF4; border:1.5px solid #BBF7D0; border-left:4px solid #16A34A; border-radius:0 10px 10px 0; padding:10px 14px; font-size:13px; color:#14532D; line-height:1.6; margin:.6rem 0; }
.warn-box    { background:#FFFBEB; border:1.5px solid #FDE68A; border-left:4px solid #F59E0B; border-radius:0 10px 10px 0; padding:10px 14px; font-size:13px; color:#854D0E; line-height:1.6; margin:.6rem 0; }

/* Inputs */
.stTextInput input, .stTextArea textarea {
    background:#FFFFFF !important; border:1.5px solid #E0E0E0 !important;
    border-radius:8px !important; color:#0A0A0A !important;
    font-family:'Inter',sans-serif !important; font-size:14px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color:#0A0A0A !important; box-shadow:0 0 0 3px rgba(10,10,10,.07) !important;
}

/* Buttons */
.stButton > button {
    background:#0A0A0A !important; color:#FFFFFF !important; border:none !important;
    border-radius:8px !important; font-family:'Inter',sans-serif !important;
    font-size:13px !important; font-weight:500 !important; padding:8px 18px !important; transition:background .15s !important;
}
.stButton > button:hover { background:#333 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background:#F5F5F5 !important; border-radius:10px !important; padding:4px !important; border:1px solid #E8E8E8 !important; }
.stTabs [data-baseweb="tab"] { font-family:'Inter',sans-serif !important; font-size:13px !important; font-weight:500 !important; border-radius:7px !important; color:#666 !important; padding:6px 14px !important; }
.stTabs [aria-selected="true"] { background:#FFFFFF !important; color:#0A0A0A !important; font-weight:600 !important; box-shadow:0 1px 4px rgba(0,0,0,.10) !important; }

/* Sidebar */
section[data-testid="stSidebar"] { background:#F8F8F8 !important; border-right:1.5px solid #E8E8E8 !important; }
section[data-testid="stSidebar"] .block-container { padding:1.5rem 1rem !important; }

hr { border-color:#EEEEEE !important; margin: 1rem 0 !important; }

.stMetricValue { font-family:'JetBrains Mono',monospace !important; font-size:22px !important; font-weight:700 !important; color:#0A0A0A !important; }
.stMetricLabel { font-size:12px !important; color:#666 !important; }
.stAlert       { border-radius:8px !important; }
.section-heading { font-size:14px; font-weight:600; color:#0A0A0A; margin:0 0 .8rem; padding-bottom:8px; border-bottom:1.5px solid #E8E8E8; }
code { background:#F5F5F5 !important; color:#0A0A0A !important; font-family:'JetBrains Mono',monospace !important; font-size:12px !important; padding:2px 5px !important; border-radius:4px !important; border:0.5px solid #E0E0E0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Imports ───────────────────────────────────────────────────────────────────
import utils.database as db
from graph.agent import chat
from monitoring.langfuse_tracker import is_available as langfuse_ok
from utils.telegram_hitl import is_configured as tg_ok, notify_daily_summary

# ── State ─────────────────────────────────────────────────────────────────────
if "conv_id"   not in st.session_state: st.session_state.conv_id   = str(uuid.uuid4())
if "messages"  not in st.session_state: st.session_state.messages  = []
if "user_name" not in st.session_state: st.session_state.user_name = "Pelanggan"
if "thinking"  not in st.session_state: st.session_state.thinking  = False
if "last_eval" not in st.session_state: st.session_state.last_eval = {}
if "escalated" not in st.session_state: st.session_state.escalated = False

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_time(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%d %b %H:%M")
    except Exception:
        return ts[:16].replace("T"," ")

def score_color(s: float) -> str:
    if s >= 4: return "#16A34A"
    if s >= 3: return "#D97706"
    return "#DC2626"

def render_score_bar(label: str, score: float):
    pct  = (score / 5) * 100
    col  = score_color(score)
    st.markdown(f"""
    <div class="score-row">
        <div class="score-lbl">{label}</div>
        <div class="score-bar"><div class="score-fill" style="width:{pct}%;background:{col}"></div></div>
        <div class="score-num">{score:.1f}</div>
    </div>
    """, unsafe_allow_html=True)

def new_conversation():
    st.session_state.conv_id   = str(uuid.uuid4())
    st.session_state.messages  = []
    st.session_state.last_eval = {}
    st.session_state.escalated = False

# ── Header ────────────────────────────────────────────────────────────────────
lf_status = "✓ Langfuse" if langfuse_ok() else "○ Langfuse (nonaktif)"
tg_status = "✓ Telegram" if tg_ok() else "○ Telegram (nonaktif)"
st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-title">🎧 Customer Support Agent</div>
        <div class="app-sub">LangGraph · RAG · Guardrails · HITL · Langfuse Monitoring</div>
    </div>
    <div class="app-badge">Fase 3 — {lf_status} &nbsp;|&nbsp; {tg_status}</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-heading">⚙️ Konfigurasi</div>', unsafe_allow_html=True)

    provider = st.selectbox("LLM Provider", ["ollama","groq"], index=0 if os.getenv("LLM_PROVIDER","ollama")=="ollama" else 1)
    os.environ["LLM_PROVIDER"] = provider

    if provider == "ollama":
        model_ol = st.text_input("Ollama Model", value=os.getenv("OLLAMA_MODEL","qwen2.5:7b"))
        os.environ["OLLAMA_MODEL"] = model_ol
        st.caption("Install: `ollama pull qwen2.5:7b`")
    else:
        groq_key = st.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY",""))
        if groq_key: os.environ["GROQ_API_KEY"] = groq_key

    st.divider()
    st.markdown('<div class="section-heading">📊 Langfuse</div>', unsafe_allow_html=True)
    lf_pk = st.text_input("Public Key", type="password", value=os.getenv("LANGFUSE_PUBLIC_KEY",""), placeholder="pk-lf-xxx")
    lf_sk = st.text_input("Secret Key", type="password", value=os.getenv("LANGFUSE_SECRET_KEY",""), placeholder="sk-lf-xxx")
    if lf_pk: os.environ["LANGFUSE_PUBLIC_KEY"] = lf_pk
    if lf_sk: os.environ["LANGFUSE_SECRET_KEY"] = lf_sk
    if langfuse_ok():
        st.markdown('<div class="success-box" style="padding:8px 12px;font-size:12px">✓ Langfuse terhubung</div>', unsafe_allow_html=True)
    else:
        st.caption("Daftar gratis: cloud.langfuse.com")

    st.divider()
    st.markdown('<div class="section-heading">📱 Telegram HITL</div>', unsafe_allow_html=True)
    tg_tok  = st.text_input("Bot Token", type="password", value=os.getenv("TELEGRAM_BOT_TOKEN",""))
    tg_cid  = st.text_input("Admin Chat ID",              value=os.getenv("TELEGRAM_ADMIN_CHAT_ID",""))
    if tg_tok: os.environ["TELEGRAM_BOT_TOKEN"]    = tg_tok
    if tg_cid: os.environ["TELEGRAM_ADMIN_CHAT_ID"] = tg_cid
    if tg_ok():
        if st.button("📤 Kirim Ringkasan ke Telegram", use_container_width=True):
            notify_daily_summary(db.get_analytics())
            st.success("Terkirim!")

    st.divider()
    store = st.text_input("Nama Toko", value=os.getenv("STORE_NAME","TechStore Indonesia"))
    if store: os.environ["STORE_NAME"] = store

    if st.button("🔁 Re-index Knowledge Base", use_container_width=True):
        from rag.knowledge_base import get_kb
        with st.spinner("Re-indexing..."):
            get_kb().reindex()
        st.success("Selesai!")

# ── Analytics KPI ─────────────────────────────────────────────────────────────
stats = db.get_analytics()
avg_scores = db.get_avg_scores()
overall_avg = avg_scores.get("overall", {}).get("avg", 0)

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi">
        <div class="kpi-label">Total Percakapan</div>
        <div class="kpi-value">{stats['total_conversations']}</div>
        <div class="kpi-sub">💬 semua waktu</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Resolution Rate</div>
        <div class="kpi-value">{stats['resolution_rate']:.0f}%</div>
        <div class="kpi-sub {'kpi-green' if stats['resolution_rate'] >= 70 else 'kpi-red'}">
            {"✓ baik" if stats['resolution_rate'] >= 70 else "↓ perlu perbaikan"}
        </div>
    </div>
    <div class="kpi">
        <div class="kpi-label">CSAT Rata-rata</div>
        <div class="kpi-value">{stats['avg_csat'] or "—"}</div>
        <div class="kpi-sub">⭐ /5.0</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Tiket Terbuka</div>
        <div class="kpi-value {'kpi-red' if stats['open_tickets'] > 0 else ''}">{stats['open_tickets']}</div>
        <div class="kpi-sub">🎫 butuh admin</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Quality Score</div>
        <div class="kpi-value">{overall_avg or "—"}</div>
        <div class="kpi-sub">🤖 LLM-as-judge</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chat, tab_tickets, tab_history, tab_eval, tab_guard, tab_setup = st.tabs([
    "💬 Chat", "🎫 Tiket", "📋 Riwayat", "📊 Evaluasi", "🛡️ Guardrails", "🚀 Setup"
])

# ─── TAB CHAT ─────────────────────────────────────────────────────────────────
with tab_chat:
    c_chat, c_panel = st.columns([3, 1], gap="large")

    with c_chat:
        # Header chat
        ch1, ch2, ch3 = st.columns([3, 2, 1])
        with ch1:
            st.session_state.user_name = st.text_input(
                "Nama pelanggan", value=st.session_state.user_name,
                label_visibility="collapsed", placeholder="Nama pelanggan..."
            )
        with ch2:
            st.markdown(f'<div style="font-size:11px;color:#888;padding:10px 0;font-family:monospace">ID: {st.session_state.conv_id[:16]}...</div>', unsafe_allow_html=True)
        with ch3:
            if st.button("🆕 Baru", use_container_width=True):
                new_conversation()
                st.rerun()

        # Render riwayat chat
        chat_html = '<div class="chat-wrap" id="chat-container">'
        if not st.session_state.messages:
            chat_html += """
            <div style="text-align:center;padding:48px 20px;color:#AAAAAA">
                <div style="font-size:36px;margin-bottom:10px">🎧</div>
                <div style="font-size:14px;font-weight:500;color:#555">Halo! Ada yang bisa kami bantu?</div>
                <div style="font-size:12px;margin-top:6px">Tanyakan tentang produk, pesanan, garansi, dll.</div>
            </div>"""
        else:
            for m in st.session_state.messages:
                role = m["role"]
                content = m["content"].replace("\n","<br>")
                ts = m.get("ts", datetime.now().strftime("%H:%M"))
                if role == "user":
                    chat_html += f"""
                    <div class="bubble-user">
                        <div>
                            <div class="msg">{content}</div>
                            <div class="bubble-meta" style="text-align:right">{ts}</div>
                        </div>
                    </div>"""
                else:
                    esc_badge = '<span class="badge-esc">⚡ Dieskalasi</span>' if m.get("escalated") else ""
                    blk_badge = '<span class="badge-blk">🛡️ Guardrail</span>' if m.get("blocked") else ""
                    chat_html += f"""
                    <div class="bubble-bot">
                        <div>
                            <div class="msg">{content}{esc_badge}{blk_badge}</div>
                            <div class="bubble-meta">{ts}</div>
                        </div>
                    </div>"""
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        # Input
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        inp_col, btn_col = st.columns([5, 1])
        with inp_col:
            user_input = st.text_input(
                "Pesan", placeholder="Tulis pesanmu di sini...",
                label_visibility="collapsed", key="chat_input"
            )
        with btn_col:
            send = st.button("Kirim ➤", use_container_width=True)

        # Contoh pertanyaan
        st.markdown('<div style="font-size:11px;color:#AAA;margin-bottom:5px">💡 Coba:</div>', unsafe_allow_html=True)
        examples = [
            "Berapa harga iPhone 16 Pro Max?",
            "Bagaimana cara klaim garansi?",
            "Ada cicilan 0%?",
            "Pengiriman ke Surabaya berapa hari?",
            "Apakah ROG Strix G16 masih ada stok?",
        ]
        ex_cols = st.columns(len(examples))
        for i, ex in enumerate(examples):
            with ex_cols[i]:
                if st.button(ex[:25]+"…", key=f"ex_{i}", use_container_width=True):
                    user_input = ex
                    send = True

        # Proses pesan
        if send and user_input and user_input.strip():
            ts = datetime.now().strftime("%H:%M")
            with st.spinner("Agent sedang memproses..."):
                result = chat(
                    user_input=user_input,
                    conv_id=st.session_state.conv_id,
                    user_name=st.session_state.user_name,
                    message_history=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                )

            st.session_state.messages.append({
                "role": "user", "content": user_input, "ts": ts
            })
            st.session_state.messages.append({
                "role":      "assistant",
                "content":   result["response"],
                "ts":        ts,
                "escalated": result.get("escalated", False),
                "blocked":   result.get("blocked", False),
            })
            st.session_state.last_eval  = result.get("eval_scores", {})
            st.session_state.escalated  = result.get("escalated", False)
            st.rerun()

    with c_panel:
        st.markdown('<div class="section-heading">📊 Eval Terakhir</div>', unsafe_allow_html=True)
        ev = st.session_state.last_eval
        if ev:
            for metric, label in [
                ("relevance","Relevansi"),("accuracy","Akurasi"),
                ("helpfulness","Helpfulness"),("tone","Tone"),("overall","Overall"),
            ]:
                if metric in ev:
                    render_score_bar(label, float(ev[metric]))
            if ev.get("summary"):
                st.markdown(f'<div class="info-box" style="margin-top:.5rem;font-size:12px">{ev["summary"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px;color:#AAA;padding:12px 0">Kirim pesan untuk melihat evaluasi real-time</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown('<div class="section-heading">🔧 Status Agent</div>', unsafe_allow_html=True)
        provider_display = os.getenv("LLM_PROVIDER","ollama").upper()
        model_display    = os.getenv("OLLAMA_MODEL","qwen2.5:7b") if provider_display == "OLLAMA" else os.getenv("GROQ_MODEL","llama-3.3-70b")
        items = [
            ("LLM", f"{provider_display} / {model_display}"),
            ("RAG", "ChromaDB + MiniLM"),
            ("Guard", "Custom Rules"),
            ("Monitor", "Langfuse" if langfuse_ok() else "Nonaktif"),
            ("HITL", "Telegram" if tg_ok() else "Nonaktif"),
        ]
        for k, v in items:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;font-size:12px;padding:5px 0;'
                f'border-bottom:.5px solid #F0F0F0"><span style="color:#555">{k}</span>'
                f'<span style="font-family:monospace;font-size:11px;color:#0A0A0A">{v}</span></div>',
                unsafe_allow_html=True
            )

        if st.session_state.escalated:
            st.markdown('<div class="warn-box" style="margin-top:.75rem;font-size:12px">⚡ Percakapan ini telah dieskalasi ke admin</div>', unsafe_allow_html=True)

# ─── TAB TIKET ───────────────────────────────────────────────────────────────
with tab_tickets:
    open_tickets = db.get_open_tickets()
    all_tickets  = db.get_all_tickets(limit=30)
    h1, h2 = st.columns([4,1])
    with h1:
        st.markdown(f'<div class="section-heading">🎫 Tiket Terbuka ({len(open_tickets)})</div>', unsafe_allow_html=True)
    with h2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    if not open_tickets:
        st.markdown('<div class="info-box">✅ Tidak ada tiket terbuka saat ini.</div>', unsafe_allow_html=True)
    else:
        for t in open_tickets:
            prio_chip = f'<span class="chip chip-{t["priority"]}">{t["priority"].upper()}</span>'
            st.markdown(f"""
            <div class="ticket">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <div class="ticket-title">Tiket #{t['id']} — {t.get('user_name','?')} {prio_chip}</div>
                        <div class="ticket-meta">📋 {t['type']} &nbsp;·&nbsp; 🕐 {fmt_time(t['created_at'])}</div>
                        <div style="font-size:12px;color:#333;margin-top:6px;line-height:1.5">{t.get('description','')[:200]}</div>
                    </div>
                    <span class="chip chip-open">OPEN</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"✅ Selesaikan Tiket #{t['id']}", key=f"res_{t['id']}", use_container_width=False):
                db.resolve_ticket(t["id"])
                st.success(f"Tiket #{t['id']} diselesaikan!")
                st.rerun()

    st.divider()
    st.markdown('<div class="section-heading">📋 Semua Tiket (30 terakhir)</div>', unsafe_allow_html=True)
    if all_tickets:
        df = pd.DataFrame(all_tickets)
        df = df[["id","user_name","type","priority","status","created_at"]].rename(columns={
            "id":"#","user_name":"Pelanggan","type":"Tipe","priority":"Prioritas","status":"Status","created_at":"Dibuat"
        })
        df["Dibuat"] = df["Dibuat"].apply(fmt_time)
        st.dataframe(df, use_container_width=True, hide_index=True)

# ─── TAB RIWAYAT ─────────────────────────────────────────────────────────────
with tab_history:
    st.markdown('<div class="section-heading">📋 Riwayat Percakapan</div>', unsafe_allow_html=True)
    convs = db.get_all_conversations(limit=30)
    if not convs:
        st.info("Belum ada percakapan. Mulai chat di tab 💬 Chat.")
    else:
        for c in convs:
            esc_badge = '<span class="badge-esc">Eskalasi</span>' if c.get("escalated") else '<span class="badge-ok">Normal</span>'
            st.markdown(f"""
            <div class="ticket">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div>
                        <div class="ticket-title">{c.get('user_name','?')} &nbsp; {esc_badge}</div>
                        <div class="ticket-meta">
                            🆔 {c['id'][:16]}... &nbsp;·&nbsp;
                            💬 {c['total_turns']} giliran &nbsp;·&nbsp;
                            🕐 {fmt_time(c['updated_at'])} &nbsp;·&nbsp;
                            ⭐ CSAT: {c['csat_score'] or '—'}
                        </div>
                    </div>
                    <span class="chip {'chip-open' if c['status']=='open' else 'chip-done'}">{c['status'].upper()}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ─── TAB EVALUASI ─────────────────────────────────────────────────────────────
with tab_eval:
    st.markdown('<div class="section-heading">📊 Dashboard Evaluasi Kualitas</div>', unsafe_allow_html=True)
    avg_scores = db.get_avg_scores()

    if not avg_scores:
        st.info("Belum ada data evaluasi. Mulai chat untuk menghasilkan evaluasi otomatis.")
    else:
        # Radar chart
        metrics = ["relevance","accuracy","helpfulness","tone","overall"]
        labels  = ["Relevansi","Akurasi","Helpfulness","Tone","Overall"]
        values  = [avg_scores.get(m,{}).get("avg",0) for m in metrics]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]], theta=labels + [labels[0]],
            fill='toself', fillcolor='rgba(10,10,10,0.07)',
            line=dict(color='#0A0A0A', width=2),
            marker=dict(size=6, color='#0A0A0A'),
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,5], tickfont=dict(size=10))),
            showlegend=False, paper_bgcolor='white',
            margin=dict(l=40,r=40,t=20,b=20), height=300,
            font=dict(family="Inter"),
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4, c5 = st.columns(5)
        for col, m, lbl in zip([c1,c2,c3,c4,c5], metrics, labels):
            v = avg_scores.get(m,{}).get("avg",0)
            n = avg_scores.get(m,{}).get("total",0)
            col.metric(lbl, f"{v:.1f}/5", f"n={n}")

    st.divider()
    st.markdown('<div class="section-heading">Detail Evaluasi Per Percakapan</div>', unsafe_allow_html=True)
    convs = db.get_all_conversations(limit=10)
    if convs:
        selected = st.selectbox("Pilih percakapan", [f"{c['user_name']} — {c['id'][:16]}" for c in convs])
        idx = [f"{c['user_name']} — {c['id'][:16]}" for c in convs].index(selected)
        evals = db.get_evaluations(convs[idx]["id"])
        if evals:
            df_e = pd.DataFrame(evals)[["metric","score","reason","evaluated_at"]].rename(
                columns={"metric":"Metrik","score":"Skor","reason":"Alasan","evaluated_at":"Waktu"}
            )
            df_e["Waktu"] = df_e["Waktu"].apply(fmt_time)
            st.dataframe(df_e, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada evaluasi untuk percakapan ini.")

# ─── TAB GUARDRAILS ───────────────────────────────────────────────────────────
with tab_guard:
    logs = db.get_guardrail_logs(limit=50)
    st.markdown(f'<div class="section-heading">🛡️ Guardrail Log ({len(logs)} entri)</div>', unsafe_allow_html=True)

    if not logs:
        st.info("Belum ada guardrail yang dipicu.")
    else:
        action_counts = {}
        for l in logs:
            a = l.get("action","?")
            action_counts[a] = action_counts.get(a, 0) + 1

        # Summary bar
        cols = st.columns(len(action_counts))
        for i, (action, count) in enumerate(action_counts.items()):
            cols[i].metric(action.upper(), count)

        st.divider()
        df_g = pd.DataFrame(logs)[["created_at","rule_triggered","action","input_text"]].rename(
            columns={"created_at":"Waktu","rule_triggered":"Rule","action":"Aksi","input_text":"Input"}
        )
        df_g["Waktu"] = df_g["Waktu"].apply(fmt_time)
        df_g["Input"] = df_g["Input"].str[:60] + "..."
        st.dataframe(df_g, use_container_width=True, hide_index=True)

# ─── TAB SETUP ─────────────────────────────────────────────────────────────────
with tab_setup:
    st.markdown('<div class="section-heading">🚀 Panduan Setup</div>', unsafe_allow_html=True)

    with st.expander("1️⃣ Install & jalankan (wajib)", expanded=True):
        st.code("""# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Edit .env: isi GROQ_API_KEY atau pastikan Ollama berjalan

# 3. Jalankan Ollama (jika pakai Ollama)
ollama serve
ollama pull qwen2.5:7b

# 4. Jalankan dashboard
streamlit run app.py""", language="bash")

    with st.expander("2️⃣ Setup Langfuse monitoring (opsional)"):
        st.markdown("""
**Opsi A — Cloud gratis (50k event/bulan):**
1. Daftar di [cloud.langfuse.com](https://cloud.langfuse.com)
2. Buat project → salin Public Key & Secret Key
3. Isi di sidebar atau `.env`

**Opsi B — Self-host dengan Docker (unlimited):**
```bash
git clone https://github.com/langfuse/langfuse
cd langfuse
docker compose up -d
# Buka http://localhost:3000
# Set LANGFUSE_HOST=http://localhost:3000 di .env
```""")

    with st.expander("3️⃣ Setup Telegram HITL admin"):
        st.markdown("""
1. Chat @BotFather → `/newbot` → salin token
2. Start chat ke bot kamu
3. Buka: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Ambil `result[0].message.chat.id` → isi sebagai `TELEGRAM_ADMIN_CHAT_ID`
5. Isi token & chat ID di sidebar

Notifikasi otomatis dikirim ke HP saat ada:
- 🔴 Komplain level tinggi (kata kunci: refund, penipuan, dll)
- ⚡ Percakapan melebihi 6 giliran tanpa resolusi
- 🎫 Tiket baru dibuat
""")

    with st.expander("4️⃣ Tambah produk ke knowledge base"):
        st.markdown("""
Edit file `data/products/catalog.txt` dan `data/faq/faq.txt`.
Format tiap entry dipisah dengan baris `---`

Setelah edit, klik **"🔁 Re-index Knowledge Base"** di sidebar untuk memperbarui vector store.
""")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style='text-align:center;font-size:11px;color:#AAAAAA;padding:4px 0;font-family:"JetBrains Mono",monospace'>
    Customer Support Agent v1.0 &nbsp;·&nbsp; LangGraph + RAG + Guardrails + HITL + Langfuse &nbsp;·&nbsp; Portofolio Fase 3 Agentic AI
</div>
""", unsafe_allow_html=True)
