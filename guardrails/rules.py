"""
guardrails/rules.py
Custom Guardrails ringan — tanpa library eksternal berat.
Validasi input user dan output agent sebelum dikirim.
"""

import os
import re
from dataclasses import dataclass
from typing import Tuple
from dotenv import load_dotenv

load_dotenv()

STORE_NAME = os.getenv("STORE_NAME", "TechStore Indonesia")

# ── Kata-kata sensitif ─────────────────────────────────────────────────────────
ESCALATION_KEYWORDS = [
    kw.strip().lower()
    for kw in os.getenv(
        "HITL_KEYWORDS",
        "refund,kembalikan uang,penipuan,lapor,bodoh,brengsek,minta ganti,tipu,menipu,complaint,complain"
    ).split(",")
]

OFF_TOPIC_PATTERNS = [
    # Politik & isu sensitif
    r'\b(politik|pilpres|pilkada|pemilu|capres|prabowo|jokowi|anies|ganjar)\b',
    # Konten dewasa
    r'\b(pornografi|xxx|bokep|dewasa|18\+)\b',
    # Kompetitor (jangan jelek-jelekkan)
    r'\b(jelekkan|jelek-jelekkan|lebih buruk dari|hancurkan kompetitor)\b',
    # SARA
    r'\b(agama|suku|ras|diskriminasi|rasis)\b',
]

TOXIC_PATTERNS = [
    r'\b(anjing|babi|bangsat|bajingan|sialan|kontol|memek|goblok|tolol|idiot|stupid)\b',
]

PROMPT_INJECTION_PATTERNS = [
    r'ignore (previous|all) instructions?',
    r'forget (everything|all|your|the) (previous|instructions?|rules?)',
    r'you are now',
    r'act as (a |an )?(different|new|unrestricted)',
    r'jailbreak',
    r'pretend (you|to) (are|be|have no)',
    r'bypass (your )?(rules?|restrictions?|guidelines?)',
    r'system prompt',
    r'new instructions?:',
]

STORE_TOPICS = [
    "produk", "harga", "beli", "pesan", "order", "pengiriman", "kirim",
    "garansi", "klaim", "retur", "return", "bayar", "pembayaran", "cicilan",
    "laptop", "hp", "handphone", "smartphone", "tablet", "aksesoris",
    "headphone", "earphone", "monitor", "ssd", "mouse", "keyboard",
    "samsung", "apple", "iphone", "asus", "sony", "logitech", "lg",
    "toko", "cs", "customer", "service", "komplain", "keluhan", "bantuan",
    "stok", "tersedia", "cod", "ongkir", "ekspres", "reguler", "resi",
    "invoice", "faktur", "nota", "diskon", "promo", "flash sale",
]


@dataclass
class GuardrailResult:
    passed:   bool
    reason:   str
    action:   str       # "allow" | "block" | "warn" | "escalate"
    response: str = ""  # Respon override jika blocked


def check_input(text: str, conv_id: str = "") -> GuardrailResult:
    """
    Validasi input user sebelum diproses agent.
    Return GuardrailResult dengan instruksi apa yang harus dilakukan.
    """
    lower = text.lower().strip()

    # 1. Cek prompt injection
    for pat in PROMPT_INJECTION_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return GuardrailResult(
                passed=False, reason="prompt_injection", action="block",
                response=(
                    "Maaf, saya tidak bisa memproses permintaan tersebut. "
                    "Saya hanya bisa membantu pertanyaan seputar produk dan layanan "
                    f"{STORE_NAME}. Ada yang bisa saya bantu? 😊"
                )
            )

    # 2. Cek konten toxic/kasar
    for pat in TOXIC_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return GuardrailResult(
                passed=False, reason="toxic_content", action="warn",
                response=(
                    "Hei, kami ingin membantu kamu dengan sebaik mungkin! "
                    "Mohon gunakan bahasa yang sopan agar kami bisa melayanimu lebih baik. 🙏\n\n"
                    "Ada keluhan atau pertanyaan yang ingin kamu sampaikan?"
                )
            )

    # 3. Cek kata kunci eskalasi (langsung ke admin)
    matched_kw = [kw for kw in ESCALATION_KEYWORDS if kw in lower]
    if matched_kw:
        return GuardrailResult(
            passed=True,
            reason=f"escalation_keyword:{','.join(matched_kw)}",
            action="escalate",
        )

    # 4. Cek off-topic (topik tidak relevan dengan toko)
    is_off_topic = all(
        pat and re.search(pat, lower, re.IGNORECASE)
        for pat in OFF_TOPIC_PATTERNS[:1]  # Cek hanya pattern pertama yang paling relevan
    )

    # Lebih akurat: cek apakah ada kata kunci toko
    has_store_topic = any(kw in lower for kw in STORE_TOPICS)

    # Hanya block jika pesan panjang dan sama sekali tidak ada topik toko
    if len(lower) > 50 and not has_store_topic:
        for pat in OFF_TOPIC_PATTERNS:
            if re.search(pat, lower, re.IGNORECASE):
                return GuardrailResult(
                    passed=False, reason="off_topic", action="block",
                    response=(
                        f"Maaf, sebagai asisten {STORE_NAME}, saya hanya bisa membantu "
                        "pertanyaan seputar produk elektronik, pemesanan, pengiriman, "
                        "garansi, dan layanan toko kami.\n\n"
                        "Ada yang ingin kamu tanyakan tentang produk kami? 😊"
                    )
                )

    # 5. Pesan terlalu pendek / tidak jelas
    if len(lower) < 3:
        return GuardrailResult(
            passed=False, reason="too_short", action="warn",
            response="Halo! 👋 Ada yang bisa kami bantu? Silakan ceritakan pertanyaan atau keluhanmu."
        )

    return GuardrailResult(passed=True, reason="ok", action="allow")


def check_output(text: str) -> GuardrailResult:
    """
    Validasi output agent sebelum dikirim ke user.
    Cegah hallusinasi atau informasi sensitif bocor.
    """
    lower = text.lower()

    # Cek apakah agent mengklaim hal-hal yang tidak seharusnya
    dangerous_claims = [
        r'(kata sandi|password|pin|nomor kartu|cvv)',
        r'(diskon|gratis|promo) \d+%.*garant',
        r'saya (adalah|ialah) manusia',
        r'saya bisa (hack|bobol|akses sistem)',
    ]
    for pat in dangerous_claims:
        if re.search(pat, lower, re.IGNORECASE):
            return GuardrailResult(
                passed=False, reason="dangerous_output", action="block",
                response=(
                    "Maaf, terjadi kesalahan dalam memproses jawaban. "
                    "Tim kami akan segera menghubungi kamu. "
                    "Untuk bantuan mendesak, hubungi " + os.getenv("STORE_PHONE", "CS kami") + "."
                )
            )

    # Respons terlalu pendek (kemungkinan error)
    if len(text.strip()) < 10:
        return GuardrailResult(
            passed=False, reason="output_too_short", action="warn",
            response=(
                "Maaf, ada kendala teknis saat memproses pesanmu. "
                "Bisakah kamu ulangi pertanyaannya? Atau hubungi CS kami langsung."
            )
        )

    return GuardrailResult(passed=True, reason="ok", action="allow")


def assess_escalation_need(user_msg: str, ai_response: str,
                            turn_count: int) -> Tuple[bool, str]:
    """
    Tentukan apakah percakapan perlu dieskalasi ke admin manusia.
    Return (should_escalate, reason).
    """
    lower_user = user_msg.lower()

    # Cek kata kunci eskalasi langsung
    matched = [kw for kw in ESCALATION_KEYWORDS if kw in lower_user]
    if matched:
        return True, f"Kata kunci eskalasi: {', '.join(matched)}"

    # Percakapan terlalu panjang tanpa resolusi
    if turn_count >= 6:
        return True, "Percakapan melebihi 6 giliran tanpa resolusi"

    # Cek indikasi kemarahan dalam teks
    anger_patterns = [
        r'tidak (puas|senang|terima|mau)',
        r'sangat (kecewa|marah|kesal)',
        r'sudah (lama|berulang|berkali)',
        r'minta (bicara|hubungi|telepon).*(manusia|orang|supervisor|manager)',
    ]
    for pat in anger_patterns:
        if re.search(pat, lower_user, re.IGNORECASE):
            return True, f"Indikasi ketidakpuasan tinggi: pattern '{pat}'"

    return False, ""
