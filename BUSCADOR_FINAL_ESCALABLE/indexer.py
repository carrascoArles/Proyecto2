# indexer.py
# ─────────────────────────────────────────────────────
# Escanea OneDrive local, detecta cambios con hash,
# y guarda todo en ChromaDB (vectores + metadatos juntos).
#
# ChromaDB reemplaza completamente:
#   - index.pkl     (vectores numpy)
#   - metadata.json (metadatos JSON)
#   - sgi.db        (SQLite)
#   - sgi.faiss     (índice FAISS)
# Todo queda en una sola carpeta: ./chroma_db/
# ─────────────────────────────────────────────────────

import os
import json
import hashlib
import urllib.parse
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from config import (
    PATH_LOCAL,
    SHAREPOINT_BASE_URL,
    SHAREPOINT_ROOT,
    EMBEDDING_MODEL,
    ALLOWED_EXTENSIONS,
    CHROMA_PATH,
    CHROMA_COLLECTION,
    HASH_FILE,
)


# ── UTILIDADES DE RUTA ────────────────────────────────────────────────────────

def file_hash(path: str) -> str:
    """
    Hash basado en tamaño + fecha de modificación.
    No lee el contenido del archivo — es instantáneo.
    Detecta si el archivo fue modificado, renombrado o borrado.
    """
    stat = os.stat(path)
    raw  = f"{path}|{stat.st_size}|{stat.st_mtime}"
    return hashlib.md5(raw.encode()).hexdigest()


def all_files_hash(files: list[dict]) -> str:
    """
    Hash global de todos los archivos.
    Si este hash no cambió desde la última indexación
    → no hay nada nuevo que hacer.
    """
    combined = "|".join(sorted(f["file_hash"] for f in files))
    return hashlib.md5(combined.encode()).hexdigest()


def local_to_sharepoint_url(local_path: str) -> str:
    """
    Convierte ruta local → URL directa de SharePoint.
    El ?web=1 fuerza apertura en el visor de Office Online.
    """
    rel     = os.path.relpath(local_path, PATH_LOCAL)
    rel_url = rel.replace("\\", "/")
    encoded = urllib.parse.quote(rel_url, safe="/")
    return f"{SHAREPOINT_BASE_URL}{SHAREPOINT_ROOT}/{encoded}?web=1"


def local_to_folder_url(local_folder: str) -> str:
    """URL de la carpeta contenedora en SharePoint."""
    rel = os.path.relpath(local_folder, PATH_LOCAL)
    if rel == ".":
        return f"{SHAREPOINT_BASE_URL}{SHAREPOINT_ROOT}/Forms/AllItems.aspx"
    rel_url    = rel.replace("\\", "/")
    server_path = f"{SHAREPOINT_ROOT}/{rel_url}"
    encoded_id  = urllib.parse.quote(server_path, safe="")
    return (
        f"{SHAREPOINT_BASE_URL}{SHAREPOINT_ROOT}/Forms/AllItems.aspx"
        f"?id={encoded_id}&viewid=10a56d31-cc0c-468d-8bc5-e1464871a437"
    )


def build_tree(rel_folder: str) -> list[str]:
    """
    Convierte ruta relativa en árbol de carpetas.
    "4. Manual Adm\\Sistemas TI" → ["SGI", "4. Manual Adm", "Sistemas TI"]
    """
    if rel_folder == ".":
        return ["SGI"]
    parts = rel_folder.replace("\\", "/").split("/")
    return ["SGI"] + [p for p in parts if p]


# ── CHROMADB ──────────────────────────────────────────────────────────────────

def get_chroma_collection():
    """
    Devuelve la colección de ChromaDB.
    persist_directory: guarda todo en disco (no se pierde al reiniciar).
    
    Para producción: cambiar a chromadb.HttpClient(host="...", port=8001)
    — el resto del código no cambia nada.
    """
    client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},  # cosine similarity para E5
    )
    return collection


# ── ESCANEO ───────────────────────────────────────────────────────────────────

def scan_local_files() -> list[dict]:
    """
    Recorre OneDrive recursivamente con os.walk().
    Devuelve lista de archivos con todos sus metadatos.
    """
    found = []
    for root, dirs, files in os.walk(PATH_LOCAL):
        # Ignorar carpetas del sistema
        dirs[:] = [d for d in dirs
                   if not d.startswith(".") and d not in ("Forms", "~recycle")]

        for file in sorted(files):
            ext = os.path.splitext(file)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            full_path  = os.path.normpath(os.path.join(root, file))
            rel_folder = os.path.relpath(root, PATH_LOCAL)
            tree       = build_tree(rel_folder)

            found.append({
                "id":         hashlib.md5(full_path.encode()).hexdigest(),
                "name":       os.path.splitext(file)[0],
                "full_name":  file,
                "extension":  ext,
                "folder":     rel_folder,
                "tree":       json.dumps(tree, ensure_ascii=False),
                "url":        local_to_sharepoint_url(full_path),
                "folder_url": local_to_folder_url(root),
                "file_hash":  file_hash(full_path),
            })

    return found


# ── INDEXACIÓN INTELIGENTE ────────────────────────────────────────────────────

def build_index(force: bool = False):
    """
    Construye o actualiza el índice en ChromaDB.

    Lógica de cambios:
    - Calcula hash global de todos los archivos
    - Si no cambió nada y force=False → no hace nada
    - Si hubo cambios:
        → Inserta documentos nuevos
        → Actualiza documentos modificados
        → Elimina documentos borrados
    Solo genera embeddings para lo que realmente cambió.
    """
    print(f"\n{'='*55}")
    print(f"  📂 Buscador SGI v3 — Indexando")
    print(f"  Ruta: {PATH_LOCAL}")
    print(f"{'='*55}\n")

    # 1. Escanear archivos locales
    print("  🔍 Escaneando archivos en OneDrive...")
    files = scan_local_files()
    if not files:
        print("  ⚠️  No se encontraron archivos.")
        return

    print(f"  ✅ {len(files)} archivos encontrados")

    # 2. Verificar si hubo cambios
    current_hash = all_files_hash(files)
    if not force and os.path.exists(HASH_FILE):
        with open(HASH_FILE) as f:
            last_hash = f.read().strip()
        if last_hash == current_hash:
            print("  ⏭️  Sin cambios detectados — índice actualizado.")
            return

    # 3. Conectar a ChromaDB
    print("\n  💾 Conectando a ChromaDB...")
    collection = get_chroma_collection()

    # 4. Obtener estado actual de ChromaDB
    existing    = collection.get(include=["metadatas"])
    existing_ids = set(existing["ids"])
    current_ids  = {f["id"] for f in files}

    # 5. Calcular qué cambió
    to_add     = []   # nuevos
    to_update  = []   # modificados
    to_delete  = list(existing_ids - current_ids)  # borrados de disco

    existing_hashes = {
        meta["id"]: meta.get("file_hash", "")
        for meta in existing["metadatas"]
    } if existing["metadatas"] else {}

    for f in files:
        if f["id"] not in existing_ids:
            to_add.append(f)
        elif existing_hashes.get(f["id"]) != f["file_hash"]:
            to_update.append(f)

    print(f"\n  📊 Cambios detectados:")
    print(f"     Nuevos:       {len(to_add)}")
    print(f"     Modificados:  {len(to_update)}")
    print(f"     Eliminados:   {len(to_delete)}")
    print(f"     Sin cambios:  {len(files) - len(to_add) - len(to_update)}")

    # 6. Eliminar borrados
    if to_delete:
        collection.delete(ids=to_delete)
        print(f"  🗑️  Eliminados: {len(to_delete)}")

    # 7. Procesar nuevos + modificados
    to_process = to_add + to_update
    if to_process:
        print(f"\n  🧠 Cargando modelo: {EMBEDDING_MODEL}")
        model = SentenceTransformer(EMBEDDING_MODEL)

        # Eliminar los modificados antes de re-insertar
        if to_update:
            collection.delete(ids=[f["id"] for f in to_update])

        # Generar embeddings SOLO para lo que cambió
        print(f"  ⚡ Generando embeddings para {len(to_process)} documentos...")
        titles     = [f"passage: {f['name']}" for f in to_process]
        embeddings = model.encode(
            titles,
            show_progress_bar=True,
            normalize_embeddings=True,
            batch_size=32,
        ).tolist()

        # Insertar en ChromaDB (vectores + metadatos juntos)
        collection.add(
            ids        = [f["id"]        for f in to_process],
            embeddings = embeddings,
            documents  = [f["name"]      for f in to_process],
            metadatas  = [
                {
                    "id":         f["id"],
                    "name":       f["name"],
                    "full_name":  f["full_name"],
                    "extension":  f["extension"],
                    "folder":     f["folder"],
                    "tree":       f["tree"],
                    "url":        f["url"],
                    "folder_url": f["folder_url"],
                    "file_hash":  f["file_hash"],
                }
                for f in to_process
            ],
        )

    # 8. Guardar hash del estado actual
    with open(HASH_FILE, "w") as f:
        f.write(current_hash)

    total = collection.count()
    print(f"\n{'='*55}")
    print(f"  🚀 ¡Índice listo! {total} documentos en ChromaDB")
    print(f"  📁 {CHROMA_PATH}/")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    build_index(force=True)
