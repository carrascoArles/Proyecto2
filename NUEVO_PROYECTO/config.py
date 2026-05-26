# config.py
# ─────────────────────────────────────────────────────
# CONFIGURACIÓN DEL BUSCADOR SGI — COBRA PERU
# ─────────────────────────────────────────────────────
 
# ── RUTA LOCAL (OneDrive sincronizado en tu PC) ───────
# Esta es la carpeta que OneDrive sincroniza en tu disco.
# Es la fuente de verdad para escanear archivos.
PATH_LOCAL = r"C:\Users\arles\COBRA PERU S.A\BISA Team Site - SGI"
 
# ── MAPEO A SHAREPOINT URL ────────────────────────────
# Analizando tus URLs reales:
#   https://cobraperusa.sharepoint.com/SGI/Forms/AllItems.aspx?...
#   id=%2FSGI%2F4%2E%20Manual%20Adm...
# La raíz en SharePoint es simplemente /SGI/
# El dominio base para abrir archivos directamente:
SHAREPOINT_BASE_URL = "https://cobraperusa.sharepoint.com"
SHAREPOINT_ROOT     = "/SGI"   # Raíz de la biblioteca en el servidor
 
# ── MODELO MULTILINGÜE LOCAL ──────────────────────────
# multilingual-e5-large: el mejor para español + inglés + códigos técnicos
# Se descarga solo la primera vez (~1.1 GB). Corre 100% en tu PC.
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
 
# ── EXTENSIONES PERMITIDAS ────────────────────────────
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls"]
 
# ── ARCHIVOS DE ÍNDICE ────────────────────────────────
INDEX_FILE    = "index.pkl"
METADATA_FILE = "metadata.json"
 