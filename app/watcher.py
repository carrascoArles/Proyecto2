# watcher.py
# ─────────────────────────────────────────────────────
# Monitorea la carpeta de OneDrive en tiempo real.
# Cuando detecta cualquier cambio (archivo nuevo,
# modificado o borrado) espera unos segundos y
# dispara el re-indexado automáticamente.
#
# Usa watchdog — monitoreo a nivel del sistema operativo,
# no polling. Windows notifica al proceso cuando algo cambia.
#
# Cómo correrlo:
#   python watcher.py
#
# Se puede dejar corriendo en segundo plano o
# configurarlo como servicio de Windows.
# ─────────────────────────────────────────────────────
 
import time
import threading
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.indexer2 import build_index
from app.searcher import searcher
from app.config import PATH_LOCAL, ALLOWED_EXTENSIONS
 
# ── Logging ───────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("watcher")
 
# ── Configuración ─────────────────────────────────────
# Segundos de espera antes de re-indexar tras detectar un cambio.
# Sirve para agrupar múltiples cambios en un solo re-indexado.
# Ejemplo: si suben 10 archivos a la vez, espera a que terminen
# todos y re-indexa una sola vez en vez de 10 veces.
DEBOUNCE_SECONDS = 15
 
 
class SGIEventHandler(FileSystemEventHandler):
    """
    Escucha eventos del sistema de archivos en la carpeta SGI.
    Cuando detecta algo relevante, programa un re-indexado.
    """
 
    def __init__(self):
        super().__init__()
        self._timer: threading.Timer | None = None
        self._lock  = threading.Lock()
 
    def _is_relevant(self, path: str) -> bool:
        """Solo reaccionar a extensiones que indexamos."""
        return any(path.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
 
    def _schedule_reindex(self, reason: str):
        """
        Programa un re-indexado con debounce.
        Si llegan más eventos antes de que expire el timer,
        cancela el anterior y reinicia la cuenta.
        """
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
 
            log.info(f"📝 Cambio detectado: {reason}")
            log.info(f"⏳ Re-indexando en {DEBOUNCE_SECONDS}s "
                     f"(se agrupa si hay más cambios)...")
 
            self._timer = threading.Timer(
                DEBOUNCE_SECONDS,
                self._run_reindex,
            )
            self._timer.daemon = True
            self._timer.start()
 
    def _run_reindex(self):
        """Ejecuta el re-indexado y recarga el searcher."""
        log.info("🔄 Iniciando re-indexado...")
        try:
            build_index(force=False)   # force=False → solo si el hash cambió
            searcher._load_index()     # recarga el índice en el servidor
            log.info("✅ Índice actualizado y listo.")
        except Exception as e:
            log.error(f"❌ Error durante re-indexado: {e}")
 
    # ── Eventos que escuchamos ────────────────────────
 
    def on_created(self, event):
        if not event.is_directory and self._is_relevant(event.src_path):
            self._schedule_reindex(f"nuevo archivo → {event.src_path}")
 
    def on_modified(self, event):
        if not event.is_directory and self._is_relevant(event.src_path):
            self._schedule_reindex(f"modificado → {event.src_path}")
 
    def on_deleted(self, event):
        if not event.is_directory and self._is_relevant(event.src_path):
            self._schedule_reindex(f"eliminado → {event.src_path}")
 
    def on_moved(self, event):
        # Renombrar o mover también es un cambio relevante
        if not event.is_directory and (
            self._is_relevant(event.src_path) or
            self._is_relevant(event.dest_path)
        ):
            self._schedule_reindex(
                f"movido → {event.src_path} → {event.dest_path}"
            )
 
 
def start_watcher():
    log.info("═" * 50)
    log.info("  👁  Watcher SGI — Monitoreo en tiempo real")
    log.info(f"  📂 {PATH_LOCAL}")
    log.info(f"  ⏱  Debounce: {DEBOUNCE_SECONDS}s")
    log.info("═" * 50)
 
    handler  = SGIEventHandler()
    observer = Observer()
 
    # recursive=True → monitorea todas las subcarpetas también
    observer.schedule(handler, path=PATH_LOCAL, recursive=True)
    observer.start()
 
    log.info("✅ Watcher activo. Esperando cambios...")
    log.info("   (Ctrl+C para detener)\n")
 
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\n🛑 Deteniendo watcher...")
        observer.stop()
 
    observer.join()
    log.info("👋 Watcher detenido.")
 
 
if __name__ == "__main__":
    start_watcher()