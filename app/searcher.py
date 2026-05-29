# searcher.py
# ─────────────────────────────────────────────────────
# Motor de búsqueda híbrido:
#   1. ChromaDB HNSW  → semántico (rápido, escalable)
#   2. BM25           → keywords exactos (códigos técnicos)
#
# ChromaDB usa HNSW internamente — más rápido que IVF
# de FAISS para la mayoría de casos, y no necesita
# entrenar el índice (FAISS IVF sí necesitaba training).
# ─────────────────────────────────────────────────────

import json
import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import chromadb
from chromadb.config import Settings
from app.config import (
    EMBEDDING_MODEL,
    CHROMA_PATH,
    CHROMA_COLLECTION,
)


class HybridSearcher:
    def __init__(self):
        print(f"🧠 Cargando modelo: {EMBEDDING_MODEL}")
        self.model      = SentenceTransformer(EMBEDDING_MODEL)
        self.collection = None
        self.all_docs   = []    # cache de metadatos para BM25
        self.bm25       = None
        self._load_index()

    def _load_index(self):
        """
        Carga ChromaDB y construye el índice BM25 en memoria.
        ChromaDB maneja sus propios vectores en disco — no carga
        todo en RAM como hacía pickle/numpy.
        """
        try:
            client = chromadb.PersistentClient(
                path=CHROMA_PATH,
                settings=Settings(anonymized_telemetry=False),
            )
            self.collection = client.get_or_create_collection(
                name=CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )

            total = self.collection.count()
            if total == 0:
                print("⚠️  ChromaDB vacío. Ejecuta python indexer.py")
                return

            # Cargar todos los metadatos para BM25
            # Solo metadatos, no vectores — liviano en RAM
            result          = self.collection.get(include=["metadatas"])
            self.all_docs   = result["metadatas"]
            self.all_ids    = result["ids"]

            # BM25 sobre los títulos
            tokenized  = [d["name"].lower().split() for d in self.all_docs]
            self.bm25  = BM25Okapi(tokenized)

            print(f"✅ ChromaDB cargado: {total} documentos.")

        except Exception as e:
            print(f"⚠️  Error cargando ChromaDB: {e}")
            print("    Ejecuta primero: python indexer.py")

    def search(
        self,
        query:  str,
        top_k:  int   = 10,
        alpha:  float = 0.6,
    ) -> list[dict]:
        """
        Búsqueda híbrida ChromaDB + BM25.

        alpha = 0.0 → solo BM25  (mejor para códigos exactos: "PO-GAF-COI-05")
        alpha = 1.0 → solo ChromaDB (mejor para lenguaje natural: "solicitud personal")
        alpha = 0.6 → balance óptimo para tu caso
        """
        if not self.collection or not self.all_docs:
            return []

        # Candidatos a revisar (más de top_k para re-rankear bien)
        k = min(top_k * 4, self.collection.count())

        # ── A. ChromaDB semántico (HNSW interno) ──────────────────────────────
        query_vec = self.model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
        ).tolist()

        chroma_results = self.collection.query(
            query_embeddings=query_vec,
            n_results=k,
            include=["metadatas", "distances"],
        )

        # distances en ChromaDB con cosine: 0 = idéntico, 2 = opuesto
        # Convertir a similitud [0, 1]
        distances  = chroma_results["distances"][0]
        meta_list  = chroma_results["metadatas"][0]
        ids_chroma = chroma_results["ids"][0]

        sem_scores = [1 - (d / 2) for d in distances]  # similitud coseno real

        # Normalizar a [0, 1]
        if sem_scores:
            s_min = min(sem_scores)
            s_max = max(sem_scores)
            if s_max > s_min:
                sem_scores = [(s - s_min) / (s_max - s_min) for s in sem_scores]

        sem_map = {
            chroma_id: score
            for chroma_id, score in zip(ids_chroma, sem_scores)
        }

        # ── B. BM25 keyword ───────────────────────────────────────────────────
        bm25_raw = np.array(self.bm25.get_scores(query.lower().split()))
        if bm25_raw.max() > bm25_raw.min():
            bm25_raw = (bm25_raw - bm25_raw.min()) / (bm25_raw.max() - bm25_raw.min())

        # Top BM25 candidatos
        top_bm25_pos = np.argsort(bm25_raw)[::-1][:top_k * 2]
        bm25_map = {
            self.all_ids[i]: float(bm25_raw[i])
            for i in top_bm25_pos
        }

        # ── C. Score combinado ────────────────────────────────────────────────
        candidates = set(sem_map.keys()) | set(bm25_map.keys())

        scored = []
        for doc_id in candidates:
            sem   = sem_map.get(doc_id, 0.0)
            bm25  = bm25_map.get(doc_id, 0.0)
            final = alpha * sem + (1 - alpha) * bm25
            scored.append((doc_id, final))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_scored = scored[:top_k]

        # ── D. Construir resultados ───────────────────────────────────────────
        # Mapear id → metadata del resultado
        id_to_meta = {
            chroma_id: meta
            for chroma_id, meta in zip(ids_chroma, meta_list)
        }
        # Para candidatos BM25 que no estaban en chroma_results
        # buscarlos en el cache local
        id_to_meta_local = {
            self.all_ids[i]: self.all_docs[i]
            for i in range(len(self.all_ids))
        }

        results = []
        for doc_id, score in top_scored:
            meta = id_to_meta.get(doc_id) or id_to_meta_local.get(doc_id)
            if not meta:
                continue
            results.append({
                "name":       meta["name"],
                "full_name":  meta["full_name"],
                "extension":  meta["extension"],
                "tree":       json.loads(meta["tree"]),
                "folder":     meta["folder"],
                "url":        meta["url"],
                "folder_url": meta["folder_url"],
                "score":      round(score, 4),
            })

        return results


# Instancia global — se carga una vez al arrancar el servidor
searcher = HybridSearcher()
