"""
utils/database.py
Database layer — SQLite untuk tiket support, percakapan, dan evaluasi.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
from contextlib import contextmanager
import os

DB_PATH = os.getenv("DB_PATH", "./data/support.db")


def get_db_path():
    p = os.getenv("DB_PATH", DB_PATH)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def get_conn():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          TEXT PRIMARY KEY,
            user_name   TEXT DEFAULT 'Pelanggan',
            status      TEXT DEFAULT 'open',
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime')),
            resolved_at TEXT,
            total_turns INTEGER DEFAULT 0,
            escalated   INTEGER DEFAULT 0,
            csat_score  REAL,
            summary     TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            tokens_used     INTEGER DEFAULT 0,
            latency_ms      INTEGER DEFAULT 0,
            tool_calls      TEXT,
            eval_score      REAL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            type            TEXT NOT NULL,
            priority        TEXT DEFAULT 'normal',
            description     TEXT,
            status          TEXT DEFAULT 'open',
            assigned_to     TEXT DEFAULT 'admin',
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            resolved_at     TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            message_id      INTEGER,
            metric          TEXT NOT NULL,
            score           REAL NOT NULL,
            reason          TEXT,
            evaluated_at    TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS guardrail_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            input_text      TEXT,
            rule_triggered  TEXT,
            action          TEXT,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
        CREATE INDEX IF NOT EXISTS idx_evals_conv ON evaluations(conversation_id);
        """)


# ── Conversations ──────────────────────────────────────────────────────────────

def create_conversation(conv_id: str, user_name: str = "Pelanggan") -> str:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, user_name) VALUES (?,?)",
            (conv_id, user_name)
        )
    return conv_id


def get_conversation(conv_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id=?", (conv_id,)
        ).fetchone()
        return dict(row) if row else None


def update_conversation(conv_id: str, **kwargs):
    allowed = {"status","total_turns","escalated","csat_score","summary","resolved_at"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sets = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [conv_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE conversations SET {sets} WHERE id=?", vals)


def get_all_conversations(limit: int = 100) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()]


# ── Messages ───────────────────────────────────────────────────────────────────

def add_message(conv_id: str, role: str, content: str,
                tokens: int = 0, latency_ms: int = 0,
                tool_calls: list = None, eval_score: float = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO messages
               (conversation_id, role, content, tokens_used, latency_ms, tool_calls, eval_score)
               VALUES (?,?,?,?,?,?,?)""",
            (conv_id, role, content, tokens, latency_ms,
             json.dumps(tool_calls or []), eval_score)
        )
        conn.execute(
            "UPDATE conversations SET total_turns=total_turns+1, updated_at=datetime('now','localtime') WHERE id=?",
            (conv_id,)
        )
        return cur.lastrowid


def get_messages(conv_id: str) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
            (conv_id,)
        ).fetchall()]


def get_chat_history(conv_id: str) -> list[dict]:
    """Return format LangChain messages."""
    msgs = get_messages(conv_id)
    return [{"role": m["role"], "content": m["content"]} for m in msgs]


# ── Tickets ────────────────────────────────────────────────────────────────────

def create_ticket(conv_id: str, ticket_type: str, description: str,
                  priority: str = "normal") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (conversation_id, type, description, priority) VALUES (?,?,?,?)",
            (conv_id, ticket_type, description, priority)
        )
        conn.execute(
            "UPDATE conversations SET escalated=1 WHERE id=?", (conv_id,)
        )
        return cur.lastrowid


def get_open_tickets() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT t.*, c.user_name FROM tickets t
               JOIN conversations c ON t.conversation_id = c.id
               WHERE t.status='open' ORDER BY
               CASE t.priority WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
               t.created_at ASC"""
        ).fetchall()]


def resolve_ticket(ticket_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE tickets SET status='resolved', resolved_at=datetime('now','localtime') WHERE id=?",
            (ticket_id,)
        )


def get_all_tickets(limit: int = 50) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT t.*, c.user_name FROM tickets t
               JOIN conversations c ON t.conversation_id = c.id
               ORDER BY t.created_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()]


# ── Evaluations ────────────────────────────────────────────────────────────────

def add_evaluation(conv_id: str, metric: str, score: float,
                   reason: str = None, message_id: int = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO evaluations (conversation_id, message_id, metric, score, reason) VALUES (?,?,?,?,?)",
            (conv_id, message_id, metric, score, reason)
        )


def get_evaluations(conv_id: str) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM evaluations WHERE conversation_id=? ORDER BY evaluated_at DESC",
            (conv_id,)
        ).fetchall()]


def get_avg_scores() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT metric, AVG(score) as avg, COUNT(*) as total FROM evaluations GROUP BY metric"
        ).fetchall()
        return {r["metric"]: {"avg": round(r["avg"], 2), "total": r["total"]} for r in rows}


# ── Guardrail Logs ─────────────────────────────────────────────────────────────

def log_guardrail(conv_id: str, input_text: str, rule: str, action: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO guardrail_logs (conversation_id, input_text, rule_triggered, action) VALUES (?,?,?,?)",
            (conv_id, input_text[:500], rule, action)
        )


def get_guardrail_logs(limit: int = 50) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM guardrail_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_analytics() -> dict:
    with get_conn() as conn:
        total  = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        open_  = conn.execute("SELECT COUNT(*) FROM conversations WHERE status='open'").fetchone()[0]
        esc    = conn.execute("SELECT COUNT(*) FROM conversations WHERE escalated=1").fetchone()[0]
        avg_cs = conn.execute("SELECT AVG(csat_score) FROM conversations WHERE csat_score IS NOT NULL").fetchone()[0]
        avg_t  = conn.execute("SELECT AVG(total_turns) FROM conversations").fetchone()[0]
        open_t = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
        g_logs = conn.execute("SELECT COUNT(*) FROM guardrail_logs").fetchone()[0]
        return {
            "total_conversations": total,
            "open_conversations":  open_,
            "escalated":           esc,
            "avg_csat":            round(avg_cs, 1) if avg_cs else 0,
            "avg_turns":           round(avg_t, 1) if avg_t else 0,
            "open_tickets":        open_t,
            "guardrail_triggers":  g_logs,
            "resolution_rate":     round((total - open_) / total * 100, 1) if total > 0 else 0,
        }


init_db()
