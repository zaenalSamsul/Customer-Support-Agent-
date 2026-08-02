# 🎧 Customer Support Agent

Production-grade customer support agent dengan LangGraph, RAG, Guardrails, HITL, dan Langfuse monitoring. **100% gratis** menggunakan Ollama (lokal) atau Groq (free tier).

---

## 🏗️ Arsitektur

```
customer_support_agent/
├── app.py                        # Streamlit Dashboard
├── graph/
│   └── agent.py                  # LangGraph agent (6 nodes)
├── rag/
│   └── knowledge_base.py         # ChromaDB + sentence-transformers
├── guardrails/
│   └── rules.py                  # Custom input/output validation
├── monitoring/
│   ├── langfuse_tracker.py       # Langfuse tracing
│   └── evaluator.py              # LLM-as-judge evaluator
├── utils/
│   ├── database.py               # SQLite (tiket, evaluasi, log)
│   └── telegram_hitl.py          # HITL notifikasi admin
├── data/
│   ├── products/catalog.txt      # Produk catalog (edit sesuai toko)
│   └── faq/faq.txt               # FAQ (edit sesuai bisnis)
└── requirements.txt
```

## 🔄 LangGraph Flow

```
Input → [input_guard] → [retrieve] → [generate] → [output_guard] → [evaluate] → [hitl_check] → Output
              ↓                                          ↓                            ↓
          BLOCKED                                   OVERRIDE                     ESCALATE
       (guardrail hit)                          (unsafe output)            (Telegram + Tiket)
```

---

## 🚀 Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Konfigurasi
cp .env.example .env

# 3. Pilih LLM:
#    A) Ollama (lokal, gratis sepenuhnya):
ollama serve && ollama pull qwen2.5:7b

#    B) Groq (cloud, free tier):
#    Isi GROQ_API_KEY di .env, set LLM_PROVIDER=groq

# 4. Jalankan
streamlit run app.py
```

---

## 💡 Fitur 

| Fitur | Implementasi |
|---|---|
| **LangGraph** | 6-node graph: guard→retrieve→generate→guard→eval→hitl |
| **RAG** | ChromaDB + sentence-transformers multilingual (gratis lokal) |
| **Guardrails** | Prompt injection, toxic, off-topic, output validation |
| **Monitoring** | Langfuse tracing per node, token usage, latency |
| **LLM-as-judge** | Evaluasi 5 metrik: relevance, accuracy, helpfulness, tone, overall |
| **HITL** | Telegram notifikasi admin saat ada komplain level tinggi |
| **Production patterns** | SQLite persistence, ticket system, analytics dashboard |
