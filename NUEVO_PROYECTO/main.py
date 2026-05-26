# main.py  —  Servidor FastAPI
# Todos los endpoints son POST.
# Corre en http://localhost:8000

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from searcher import searcher
from indexer import build_index
from config import EMBEDDING_MODEL

app = FastAPI(
    title="Buscador SGI — COBRA PERU",
    description="Búsqueda híbrida semántica + keyword sobre documentos SharePoint",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def root():
    idx = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(idx):
        return FileResponse(idx)
    return {"message": "API SGI corriendo — abre /docs para ver los endpoints"}


# ── MODELOS ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int]   = 10
    alpha: Optional[float] = 0.6

class SearchResult(BaseModel):
    name:       str
    full_name:  str
    extension:  str
    tree:       list[str]   # ["SGI", "4. Manual Adm.", "Sistemas TI"]
    folder:     str
    url:        str
    folder_url: str
    score:      float

class SearchResponse(BaseModel):
    query:   str
    results: list[SearchResult]
    total:   int

class IndexRequest(BaseModel):
    confirm: bool = False

class IndexResponse(BaseModel):
    message: str
    status:  str


# ── ENDPOINTS POST ────────────────────────────────────────────────────────────

@app.post("/search", response_model=SearchResponse)
def search_documents(req: SearchRequest):
    """
    Busca documentos en el índice semántico.

    Body: { "query": "solicitud de personal", "top_k": 10, "alpha": 0.6 }
    """
    if not req.query.strip():
        raise HTTPException(400, "El campo 'query' no puede estar vacío.")

    results = searcher.search(req.query.strip(), req.top_k, req.alpha)
    return SearchResponse(query=req.query, results=results, total=len(results))


@app.post("/reindex", response_model=IndexResponse)
def reindex(req: IndexRequest):
    """
    Re-indexa la carpeta local sincronizada por OneDrive.

    Body: { "confirm": true }
    """
    if not req.confirm:
        return IndexResponse(message="Manda confirm=true para iniciar.", status="cancelled")
    try:
        build_index()
        searcher._load_index()
        return IndexResponse(message="Re-indexación completada.", status="success")
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/status")
def status():
    """Devuelve el estado del índice y cuántos documentos hay."""
    if searcher.metadata is None:
        return {"ready": False, "documents": 0,
                "message": "Sin índice. Ejecuta python indexer.py primero."}
    return {
        "ready":     True,
        "documents": len(searcher.metadata),
        "model":     EMBEDDING_MODEL,
        "message":   f"{len(searcher.metadata)} documentos indexados y listos.",
    }


# ── ARRANQUE ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n" + "═"*55)
    print("  🚀 Buscador SGI — COBRA PERU")
    print("  📍 http://localhost:8000")
    print("  📖 Swagger: http://localhost:8000/docs")
    print("═"*55 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
