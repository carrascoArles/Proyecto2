# searcher.py
# ─────────────────────────────────────────────────────
# Motor de búsqueda HÍBRIDO:
#   1. Semántico (E5 multilingual) → sinónimos e intención
#   2. BM25 keyword → exacto para códigos "PO-GAF-COI-05"
# ─────────────────────────────────────────────────────

import json
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from config import EMBEDDING_MODEL, INDEX_FILE, METADATA_FILE


class HybridSearcher:
    def __init__(self):
        print(f"🧠 Cargando modelo: {EMBEDDING_MODEL}")
        self.model      = SentenceTransformer(EMBEDDING_MODEL)
        self.embeddings = None
        self.metadata   = None
        self.bm25       = None
        self._load_index()

    def _load_index(self):
        try:
            with open(INDEX_FILE, "rb") as fp:
                self.embeddings = pickle.load(fp)
            with open(METADATA_FILE, "r", encoding="utf-8") as fp:
                self.metadata = json.load(fp)
            tokenized  = [doc["name"].lower().split() for doc in self.metadata]
            self.bm25  = BM25Okapi(tokenized)
            print(f"✅ Índice cargado: {len(self.metadata)} documentos.")
        except FileNotFoundError:
            print("⚠️  index.pkl / metadata.json no encontrados.")
            print("    Ejecuta primero:  python indexer.py")

    def search(self, query: str, top_k: int = 10, alpha: float = 0.6) -> list[dict]:
        if self.embeddings is None or self.metadata is None:
            return []

        # ── Semántico (E5 requiere prefijo "query:") ──────────────────────────
        query_vec       = self.model.encode(
            [f"query: {query}"], normalize_embeddings=True
        )[0]
        sem_scores      = np.dot(self.embeddings, query_vec)
        s_min, s_max    = sem_scores.min(), sem_scores.max()
        if s_max > s_min:
            sem_scores = (sem_scores - s_min) / (s_max - s_min)

        # ── BM25 keyword ──────────────────────────────────────────────────────
        bm25_scores     = np.array(self.bm25.get_scores(query.lower().split()))
        b_min, b_max    = bm25_scores.min(), bm25_scores.max()
        if b_max > b_min:
            bm25_scores = (bm25_scores - b_min) / (b_max - b_min)

        # ── Score final ───────────────────────────────────────────────────────
        final           = alpha * sem_scores + (1 - alpha) * bm25_scores
        top_indices     = np.argsort(final)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc = self.metadata[idx]
            results.append({
                "name":       doc["name"],
                "full_name":  doc["full_name"],
                "extension":  doc.get("extension", ""),
                "tree":       doc.get("tree", ["SGI"]),
                "folder":     doc.get("folder", ""),
                "url":        doc["url"],
                "folder_url": doc.get("folder_url", ""),
                "score":      round(float(final[idx]), 4),
            })
        return results


searcher = HybridSearcher()
