# config.py
# ─────────────────────────────────────────────────────
# Configuración central del buscador SGI.
# Detecta OneDrive automáticamente en cualquier PC.
# ─────────────────────────────────────────────────────

import os
import glob


def find_sgi_path() -> str:
    """
    Detecta la carpeta SGI de OneDrive automáticamente.
    Funciona en cualquier PC sin cambiar nada.
    """
    username   = os.getenv("USERNAME") or os.getenv("USER", "user")
    candidates = [
        rf"C:\Users\{username}\COBRA PERU S.A\BISA Team Site - SGI",
        rf"C:\Users\{username}\OneDrive - COBRA PERU S.A\BISA Team Site - SGI",
        rf"C:\Users\{username}\OneDrive\BISA Team Site - SGI",
        rf"D:\Users\{username}\COBRA PERU S.A\BISA Team Site - SGI",
    ]
    for p in candidates:
        if os.path.exists(p):
            print(f"✅ OneDrive encontrado: {p}")
            return p

    # Búsqueda recursiva como último recurso
    matches = glob.glob(
        rf"C:\Users\{username}\**\BISA Team Site - SGI",
        recursive=True
    )
    if matches:
        print(f"✅ OneDrive encontrado: {matches[0]}")
        return matches[0]

    raise FileNotFoundError(
        "❌ No se encontró la carpeta SGI de OneDrive.\n"
        "   Verifica que OneDrive esté sincronizado en esta PC."
    )


# ── Rutas ─────────────────────────────────────────────
PATH_LOCAL          = find_sgi_path()
SHAREPOINT_BASE_URL = "https://cobraperusa.sharepoint.com"
SHAREPOINT_ROOT     = "/SGI"

# ── Modelo multilingüe ────────────────────────────────
# E5-large: el mejor balance calidad/velocidad para español
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIM   = 1024

# ── ChromaDB ──────────────────────────────────────────
# Carpeta donde ChromaDB guarda todos sus datos
# (vectores + metadatos + índices — todo en uno)
CHROMA_PATH       = "./chroma_db"
CHROMA_COLLECTION = "sgi_documentos"

# ── Control de cambios ────────────────────────────────
HASH_FILE = "last_hash.txt"

# ── Extensiones permitidas ────────────────────────────
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".mpp"]
