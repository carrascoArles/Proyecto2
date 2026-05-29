# auto_reindex.py
# Configurar en Windows Task Scheduler para correr cada noche.
# Solo re-indexa si hubo cambios — si no, termina en segundos.

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.indexer2 import build_index, get_chroma_collection

if __name__ == "__main__":
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Auto re-indexado SGI")
    build_index(force=False)
    try:
        col   = get_chroma_collection()
        total = col.count()
        print(f"📊 Total documentos en ChromaDB: {total}")
    except Exception as e:
        print(f"⚠️  {e}")
