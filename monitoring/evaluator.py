"""
monitoring/evaluator.py
LLM-as-Judge evaluator — nilai kualitas jawaban agent secara otomatis.
Pakai model ringan (Groq gratis) sebagai hakim.
"""

import os
import re
import json
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

STORE_NAME = os.getenv("STORE_NAME", "TechStore Indonesia")


def _get_judge_llm():
    """Dapatkan LLM untuk evaluasi (selalu pakai Groq agar cepat & gratis)."""
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant",  # Model kecil cukup untuk evaluasi
            temperature=0,
        )
    except Exception:
        return None


def evaluate_response(
    user_query: str,
    agent_response: str,
    context: str = "",
    conv_id: str = "",
) -> dict:
    """
    Evaluasi kualitas jawaban agent dengan LLM-as-judge.

    Metrik yang dinilai (skala 1-5):
    - relevance:    Seberapa relevan jawaban dengan pertanyaan
    - accuracy:     Seberapa akurat informasi yang diberikan
    - helpfulness:  Seberapa membantu jawaban bagi pelanggan
    - tone:         Apakah tone sopan dan profesional

    Return dict dengan scores dan overall.
    """
    llm = _get_judge_llm()
    if not llm:
        return _fallback_eval(agent_response)

    judge_prompt = f"""Kamu adalah evaluator kualitas Customer Support untuk {STORE_NAME}.
Nilailah jawaban berikut dengan OBJEKTIF dan KETAT.

PERTANYAAN PELANGGAN:
{user_query}

JAWABAN AGENT:
{agent_response}

{f"KONTEKS YANG TERSEDIA:{chr(10)}{context[:500]}" if context else ""}

Berikan penilaian dalam format JSON berikut (tanpa markdown, JSON saja):
{{
  "relevance": <1-5>,
  "accuracy": <1-5>,
  "helpfulness": <1-5>,
  "tone": <1-5>,
  "overall": <1-5>,
  "strengths": "<satu kalimat kelebihan>",
  "improvements": "<satu kalimat yang bisa diperbaiki>",
  "summary": "<satu kalimat ringkasan>"
}}

Panduan nilai:
5 = Sempurna
4 = Baik, ada sedikit ruang perbaikan
3 = Cukup, ada kekurangan nyata
2 = Buruk, banyak kekurangan
1 = Sangat buruk / tidak relevan sama sekali

PENTING: Kembalikan HANYA JSON, tidak ada teks lain."""

    try:
        start = time.time()
        resp = llm.invoke(judge_prompt)
        latency = int((time.time() - start) * 1000)

        raw = resp.content.strip()
        # Bersihkan markdown jika ada
        raw = re.sub(r'```json\s*|\s*```', '', raw).strip()

        scores = json.loads(raw)
        scores["latency_ms"] = latency
        scores["evaluated"] = True
        return scores

    except Exception as e:
        return _fallback_eval(agent_response, error=str(e))


def _fallback_eval(response: str, error: str = "") -> dict:
    """Evaluasi sederhana tanpa LLM jika judge tidak tersedia."""
    length = len(response)
    has_greeting = any(w in response.lower() for w in ["halo", "hai", "selamat", "terima kasih"])
    has_action   = any(w in response.lower() for w in ["silakan", "mohon", "bisa", "kami"])

    base = 3
    if length < 50:   base = 2
    if length > 200:  base = 4
    if has_greeting:  base = min(5, base + 0.5)
    if has_action:    base = min(5, base + 0.5)

    score = round(base)
    return {
        "relevance":    score,
        "accuracy":     score,
        "helpfulness":  score,
        "tone":         score,
        "overall":      score,
        "strengths":    "Evaluasi otomatis tidak tersedia",
        "improvements": "Aktifkan GROQ_API_KEY untuk evaluasi detail",
        "summary":      f"Skor estimasi: {score}/5",
        "evaluated":    False,
        "error":        error,
    }


def evaluate_conversation_summary(conv_id: str, messages: list) -> dict:
    """
    Evaluasi keseluruhan percakapan setelah selesai.
    Hitung CSAT prediksi dan quality score.
    """
    llm = _get_judge_llm()
    if not llm or not messages:
        return {"csat_predicted": 3.0, "quality": 3.0, "evaluated": False}

    # Ambil 10 pesan terakhir saja
    recent = messages[-10:]
    dialogue = "\n".join(
        f"{'Pelanggan' if m['role'] == 'user' else 'Agent'}: {m['content'][:200]}"
        for m in recent
    )

    prompt = f"""Evaluasi percakapan customer support berikut dari {STORE_NAME}.

PERCAKAPAN:
{dialogue}

Berikan penilaian JSON (tanpa markdown):
{{
  "csat_predicted": <1-5 prediksi kepuasan pelanggan>,
  "resolution": <true/false apakah masalah terselesaikan>,
  "quality": <1-5 kualitas keseluruhan pelayanan>,
  "summary": "<ringkasan percakapan dalam satu kalimat>"
}}

HANYA JSON."""

    try:
        resp = llm.invoke(prompt)
        raw  = re.sub(r'```json\s*|\s*```', '', resp.content.strip()).strip()
        result = json.loads(raw)
        result["evaluated"] = True
        return result
    except Exception:
        return {"csat_predicted": 3.0, "quality": 3.0, "evaluated": False}
