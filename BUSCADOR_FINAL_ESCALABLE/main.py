# main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import os

from indexer import build_index, get_chroma_collection
from searcher import searcher
from config import EMBEDDING_MODEL, CHROMA_PATH


def index_exists() -> bool:
    try:
        col = get_chroma_collection()
        return col.count() > 0
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not index_exists():
        print("📋 Sin índice. Construyendo desde OneDrive...")
        build_index(force=True)
        searcher._load_index()
    yield


app = FastAPI(
    title="Buscador SGI — COBRA PERU",
    version="3.0.0",
    lifespan=lifespan,
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
    return {"message": "Buscador SGI v3 corriendo"}


# ── Modelos ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int]   = 10
    alpha: Optional[float] = 0.6

class SearchResult(BaseModel):
    name:       str
    full_name:  str
    extension:  str
    tree:       list[str]
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
    force:   bool = False

class IndexResponse(BaseModel):
    message: str
    status:  str
    total:   int = 0


# ── Endpoints POST ────────────────────────────────────────────────────────────

@app.post("/search", response_model=SearchResponse)
def search_documents(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "El campo 'query' no puede estar vacío.")
    results = searcher.search(req.query.strip(), req.top_k, req.alpha)
    return SearchResponse(query=req.query, results=results, total=len(results))


@app.post("/reindex", response_model=IndexResponse)
def reindex(req: IndexRequest):
    if not req.confirm:
        return IndexResponse(
            message="Manda confirm=true para iniciar.",
            status="cancelled"
        )
    try:
        build_index(force=req.force)
        searcher._load_index()
        total = get_chroma_collection().count()
        return IndexResponse(
            message=f"Indexación completada. {total} documentos.",
            status="success",
            total=total,
        )
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/status")
def status():
    try:
        col   = get_chroma_collection()
        total = col.count()
        if total == 0:
            return {
                "ready":    False,
                "documents": 0,
                "message":  "Sin documentos. Ejecuta python indexer.py",
            }
        return {
            "ready":     True,
            "documents": total,
            "model":     EMBEDDING_MODEL,
            "storage":   CHROMA_PATH,
            "message":   f"{total} documentos listos.",
        }
    except Exception:
        return {
            "ready":    False,
            "documents": 0,
            "message":  "ChromaDB no inicializado.",
        }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("  🚀 Buscador SGI v3 — ChromaDB")
    print("  📍 http://localhost:8000")
    print("  📖 http://localhost:8000/docs")
    print("="*50 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
