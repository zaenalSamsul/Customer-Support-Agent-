"""
utils/telegram_hitl.py
Human-in-the-Loop via Telegram.
Kirim notifikasi ke admin jika ada komplain level tinggi.
"""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
STORE     = os.getenv("STORE_NAME", "TechStore Indonesia")


def is_configured() -> bool:
    return bool(
        BOT_TOKEN and CHAT_ID
        and not BOT_TOKEN.startswith("7412893")
    )


async def _send(text: str) -> bool:
    if not is_configured():
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={
                "chat_id":    CHAT_ID,
                "text":       text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
            return r.status_code == 200
    except Exception:
        return False


def send_sync(text: str) -> bool:
    """Wrapper synchronous untuk dipakai dari non-async context."""
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _send(text)).result(timeout=12)
        except RuntimeError:
            return asyncio.run(_send(text))
    except Exception:
        return False


def notify_escalation(
    conv_id: str,
    user_name: str,
    reason: str,
    last_message: str,
    ticket_id: int = None,
    priority: str = "normal",
) -> bool:
    """Kirim notifikasi eskalasi ke admin Telegram."""
    ts = datetime.now().strftime("%d %b %Y %H:%M")
    priority_icon = "🔴" if priority == "high" else "🟡"

    msg = (
        f"{priority_icon} <b>ESKALASI KE ADMIN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏪 <b>{STORE}</b>\n"
        f"🕐 {ts}\n\n"
        f"👤 <b>Pelanggan:</b> {user_name}\n"
        f"🆔 <b>Konversasi:</b> <code>{conv_id[:12]}...</code>\n"
        f"🎫 <b>Tiket:</b> #{ticket_id or 'N/A'}\n"
        f"⚠️ <b>Alasan:</b> {reason}\n\n"
        f"💬 <b>Pesan terakhir:</b>\n"
        f"<i>{last_message[:300]}{'...' if len(last_message) > 300 else ''}</i>\n\n"
        f"<b>Tindakan:</b> Buka dashboard untuk merespons → "
        f"<code>localhost:8501</code>"
    )
    return send_sync(msg)


def notify_new_ticket(ticket_id: int, ticket_type: str,
                       description: str, user_name: str) -> bool:
    """Notifikasi tiket baru."""
    ts = datetime.now().strftime("%d %b %Y %H:%M")
    msg = (
        f"🎫 <b>TIKET BARU #{ticket_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏪 {STORE} — {ts}\n\n"
        f"👤 Pelanggan: {user_name}\n"
        f"📋 Tipe: <b>{ticket_type}</b>\n"
        f"📝 {description[:400]}"
    )
    return send_sync(msg)


def notify_daily_summary(stats: dict) -> bool:
    """Ringkasan harian CS agent."""
    ts = datetime.now().strftime("%d %b %Y")
    msg = (
        f"📊 <b>Ringkasan Harian CS Agent</b>\n"
        f"📅 {ts} — {STORE}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 Total percakapan: <b>{stats.get('total_conversations', 0)}</b>\n"
        f"✅ Terselesaikan: <b>{stats.get('resolution_rate', 0):.0f}%</b>\n"
        f"⚡ Eskalasi ke admin: <b>{stats.get('escalated', 0)}</b>\n"
        f"🎫 Tiket terbuka: <b>{stats.get('open_tickets', 0)}</b>\n"
        f"⭐ CSAT rata-rata: <b>{stats.get('avg_csat', 0):.1f}/5</b>\n"
        f"🔰 Guardrail dipicu: <b>{stats.get('guardrail_triggers', 0)}x</b>"
    )
    return send_sync(msg)
