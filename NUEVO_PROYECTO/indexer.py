# indexer.py
# ─────────────────────────────────────────────────────
# Escanea la carpeta local sincronizada por OneDrive,
# convierte cada ruta a su URL de SharePoint,
# y construye el índice semántico sobre los TÍTULOS.
#
# NO usa credenciales. La URL se construye por conversión
# de texto: ruta local → URL SharePoint.
# ─────────────────────────────────────────────────────
 
import os
import json
import pickle
import urllib.parse
from sentence_transformers import SentenceTransformer
from config import (
    PATH_LOCAL,
    SHAREPOINT_BASE_URL,
    SHAREPOINT_ROOT,
    EMBEDDING_MODEL,
    ALLOWED_EXTENSIONS,
    INDEX_FILE,
    METADATA_FILE,
)
 
 
# ── CONVERSIÓN DE RUTA LOCAL → URL DE SHAREPOINT ─────────────────────────────
 
def local_path_to_sharepoint_url(local_path: str) -> str:
    """
    Convierte una ruta de Windows a una URL directa de SharePoint.
 
    Ejemplo:
      Entrada:  C:\\Users\\arles\\COBRA PERU S.A\\BISA Team Site - SGI\\4. Manual Adm. y Finanzas\\Sistemas TI\\IN-SIT-MDA-01 Instructivo.pdf
      Salida:   https://cobraperusa.sharepoint.com/SGI/4.%20Manual%20Adm.%20y%20Finanzas/Sistemas%20TI/IN-SIT-MDA-01%20Instructivo.pdf?web=1
 
    El ?web=1 al final fuerza a SharePoint a abrir el visor de Office Online
    en lugar de descargar el archivo.
    """
    # 1. Obtener la parte relativa (quitar el prefijo local)
    rel = os.path.relpath(local_path, PATH_LOCAL)
 
    # 2. Cambiar separadores Windows a URL
    rel_url = rel.replace("\\", "/")
 
    # 3. Codificar caracteres especiales (espacios, puntos con significado, etc.)
    #    Usamos quote() pero preservando "/" como separador de carpetas
    encoded = urllib.parse.quote(rel_url, safe="/")
 
    # 4. Armar URL completa
    full_url = f"{SHAREPOINT_BASE_URL}{SHAREPOINT_ROOT}/{encoded}?web=1"
    return full_url
 
 
def local_path_to_folder_url(local_folder: str) -> str:
    rel = os.path.relpath(local_folder, PATH_LOCAL)
    if rel == ".":
        return f"{SHAREPOINT_BASE_URL}/SGI/Forms/AllItems.aspx"
    rel_url = rel.replace("\\", "/")
    # La ruta va en el parámetro ?id= con UN solo encode, sin codificar las /
    folder_server_path = f"{SHAREPOINT_ROOT}/{rel_url}"
    encoded_id = urllib.parse.quote(folder_server_path, safe="")
    return (
        f"{SHAREPOINT_BASE_URL}/SGI/Forms/AllItems.aspx"
        f"?id={encoded_id}"
        f"&viewid=10a56d31-cc0c-468d-8bc5-e1464871a437"
    )
 
 
def build_tree_path(rel_folder: str) -> list[str]:
    """
    Convierte 'Manual Adm. y Finanzas\\Sistemas TI' en una lista de partes:
    ['Manual Adm. y Finanzas', 'Sistemas TI']
    Para mostrar el árbol de carpetas en la UI.
    """
    if rel_folder == ".":
        return ["SGI"]
    parts = rel_folder.replace("\\", "/").split("/")
    return ["SGI"] + [p for p in parts if p]
 
 
# ── ESCANEO DE ARCHIVOS ───────────────────────────────────────────────────────
 
def build_index():
    print(f"\n{'='*55}")
    print(f"  📂 Buscador SGI — Indexando documentos")
    print(f"{'='*55}")
    print(f"\n  Ruta local : {PATH_LOCAL}")
    print(f"  SharePoint : {SHAREPOINT_BASE_URL}{SHAREPOINT_ROOT}\n")
 
    if not os.path.exists(PATH_LOCAL):
        print(f"❌ ERROR: La ruta local no existe:")
        print(f"   {PATH_LOCAL}")
        print(f"   Verifica que OneDrive haya sincronizado la carpeta SGI.")
        return
 
    files_data = []
 
    for root, dirs, files in os.walk(PATH_LOCAL):
        # Ignorar carpetas ocultas o del sistema
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "Forms"]
 
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
 
            full_path   = os.path.normpath(os.path.join(root, file))
            rel_folder  = os.path.relpath(root, PATH_LOCAL)
            name_no_ext = os.path.splitext(file)[0]
            tree_parts  = build_tree_path(rel_folder)
 
            # Construir URL directa a SharePoint (sin credenciales)
            sharepoint_url = local_path_to_sharepoint_url(full_path)
            folder_url     = local_path_to_folder_url(root)
 
            files_data.append({
                "name":         name_no_ext,       # "IN-SIT-MDA-01 Instructivo de atención"
                "full_name":    file,               # "IN-SIT-MDA-01 Instructivo de atención.pdf"
                "extension":    ext,                # ".pdf"
                "folder":       rel_folder,         # "4. Manual Adm. y Finanzas\Sistemas TI"
                "tree":         tree_parts,         # ["SGI", "4. Manual Adm. y Finanzas", "Sistemas TI"]
                "url":          sharepoint_url,     # URL directa al archivo en SharePoint
                "folder_url":   folder_url,         # URL de la carpeta en SharePoint
                "local_path":   full_path,          # Ruta local (para referencia)
            })
            print(f"  📄 {'/'.join(tree_parts[1:])} / {file}")
 
    if not files_data:
        print("\n⚠️  No se encontraron archivos.")
        print("    Verifica que OneDrive haya sincronizado la carpeta SGI.")
        return
 
    print(f"\n✅ Total archivos: {len(files_data)}")
    print(f"\n🧠 Cargando modelo: {EMBEDDING_MODEL}")
    print(f"   (La primera vez descarga ~1.1 GB — espera un momento...)\n")
 
    model = SentenceTransformer(EMBEDDING_MODEL)
 
    # El modelo E5 requiere el prefijo "passage:" para los documentos
    titles_to_embed = [f"passage: {f['name']}" for f in files_data]
 
    print("⚡ Generando embeddings...")
    embeddings = model.encode(
        titles_to_embed,
        show_progress_bar=True,
        normalize_embeddings=True,
        batch_size=32,
    )
 
    with open(INDEX_FILE, "wb") as fp:
        pickle.dump(embeddings, fp)
 
    with open(METADATA_FILE, "w", encoding="utf-8") as fp:
        json.dump(files_data, fp, ensure_ascii=False, indent=2)
 
    print(f"\n{'='*55}")
    print(f"  🚀 ¡Índice listo!")
    print(f"  📦 {INDEX_FILE}  —  {len(files_data)} vectores")
    print(f"  📋 {METADATA_FILE}")
    print(f"{'='*55}")
    print(f"\n  Ahora ejecuta:  python main.py")
    print(f"  Y abre Chrome:  http://localhost:8000\n")
 
 
if __name__ == "__main__":
    build_index()
 