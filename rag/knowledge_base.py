"""
rag/knowledge_base.py
RAG Knowledge Base — ChromaDB + sentence-transformers (gratis, lokal)
Load produk catalog + FAQ ke vector store untuk retrieval kontekstual.
"""

import os
import re
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

CHROMA_PATH  = os.getenv("CHROMA_PATH", "./data/chroma_db")
CATALOG_PATH = Path("./data/products/catalog.txt")
FAQ_PATH     = Path("./data/faq/faq.txt")

# Model embedding ringan, jalan lokal tanpa biaya
EMBED_MODEL  = "paraphrase-multilingual-MiniLM-L12-v2"  # Support Bahasa Indonesia


class KnowledgeBase:
    def __init__(self):
        Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
        self.client     = chromadb.PersistentClient(path=CHROMA_PATH)
        self.embedder   = SentenceTransformer(EMBED_MODEL)
        self.products   = self.client.get_or_create_collection("products")
        self.faq        = self.client.get_or_create_collection("faq")
        self._load_data()

    # ── Embedding function compatible with ChromaDB ────────────────────────────
    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.encode(texts, show_progress_bar=False).tolist()

    # ── Load data ke ChromaDB ─────────────────────────────────────────────────
    def _load_data(self):
        """Load catalog & FAQ hanya jika belum ada di ChromaDB."""
        if self.products.count() == 0:
            self._index_products()
        if self.faq.count() == 0:
            self._index_faq()

    def _index_products(self):
        if not CATALOG_PATH.exists():
            return
        text = CATALOG_PATH.read_text(encoding="utf-8")
        chunks = [c.strip() for c in text.split("---") if c.strip()]

        docs, ids, metas = [], [], []
        for i, chunk in enumerate(chunks):
            # Ekstrak nama produk untuk metadata
            name_match = re.search(r"Produk:\s*(.+)", chunk)
            kode_match = re.search(r"Kode:\s*(.+)", chunk)
            name = name_match.group(1).strip() if name_match else f"Produk {i}"
            kode = kode_match.group(1).strip() if kode_match else f"PROD-{i}"
            docs.append(chunk)
            ids.append(f"prod_{i}")
            metas.append({"type": "product", "name": name, "kode": kode})

        self.products.add(
            documents=docs,
            embeddings=self._embed(docs),
            ids=ids,
            metadatas=metas,
        )
        print(f"✅ Indexed {len(docs)} produk ke ChromaDB")

    def _index_faq(self):
        if not FAQ_PATH.exists():
            return
        text = FAQ_PATH.read_text(encoding="utf-8")
        chunks = [c.strip() for c in text.split("---") if c.strip()]

        docs, ids, metas = [], [], []
        for i, chunk in enumerate(chunks):
            q_match = re.search(r"Pertanyaan:\s*(.+)", chunk)
            question = q_match.group(1).strip() if q_match else f"FAQ {i}"
            docs.append(chunk)
            ids.append(f"faq_{i}")
            metas.append({"type": "faq", "question": question})

        self.faq.add(
            documents=docs,
            embeddings=self._embed(docs),
            ids=ids,
            metadatas=metas,
        )
        print(f"✅ Indexed {len(docs)} FAQ ke ChromaDB")

    # ── Search ─────────────────────────────────────────────────────────────────
    def search_products(self, query: str, n: int = 3) -> list[dict]:
        if self.products.count() == 0:
            return []
        results = self.products.query(
            query_embeddings=self._embed([query]),
            n_results=min(n, self.products.count()),
        )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            out.append({
                "content":  doc,
                "metadata": results["metadatas"][0][i],
                "score":    1 - results["distances"][0][i],
            })
        return out

    def search_faq(self, query: str, n: int = 3) -> list[dict]:
        if self.faq.count() == 0:
            return []
        results = self.faq.query(
            query_embeddings=self._embed([query]),
            n_results=min(n, self.faq.count()),
        )
        out = []
        for i, doc in enumerate(results["documents"][0]):
            out.append({
                "content":  doc,
                "metadata": results["metadatas"][0][i],
                "score":    1 - results["distances"][0][i],
            })
        return out

    def search_all(self, query: str, n: int = 3) -> str:
        """Search produk + FAQ sekaligus, return formatted string untuk context LLM."""
        products = self.search_products(query, n=n)
        faqs     = self.search_faq(query, n=n)
        context  = ""

        if products:
            context += "### Informasi Produk Relevan:\n"
            for p in products:
                context += f"\n{p['content']}\n"

        if faqs:
            context += "\n### FAQ Relevan:\n"
            for f in faqs:
                context += f"\n{f['content']}\n"

        return context.strip() if context else "Tidak ada informasi relevan ditemukan."

    def reindex(self):
        """Hapus dan index ulang semua data."""
        try:
            self.client.delete_collection("products")
            self.client.delete_collection("faq")
        except Exception:
            pass
        self.products = self.client.get_or_create_collection("products")
        self.faq      = self.client.get_or_create_collection("faq")
        self._index_products()
        self._index_faq()


# Singleton
_kb: Optional[KnowledgeBase] = None

def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
