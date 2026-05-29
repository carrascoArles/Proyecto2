# launcher.py
# ─────────────────────────────────────────────────────
# Lanzador del Buscador SGI.
# Este archivo se compila con Nuitka a un .exe limpio.
#
# Lo que hace:
#   1. Verifica que todo esté en su lugar
#   2. Inicia el servidor FastAPI en segundo plano
#   3. Espera 4 segundos a que arranque
#   4. Abre el navegador en http://localhost:8000
#   5. Muestra una ventana de estado simple
# ─────────────────────────────────────────────────────
 
import subprocess
import os
import sys
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox
import threading
 
# ── Rutas base ────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(sys.argv[0]))
PYTHON  = os.path.join(BASE, "python", "python.exe")
MAIN    = os.path.join(BASE, "app", "main.py")
MODELO  = os.path.join(BASE, "modelo", "config.json")
LOG     = os.path.join(BASE, "data", "server.log")
 
# ── Verificaciones previas ────────────────────────────
 
def verificar():
    errores = []
    if not os.path.exists(PYTHON):
        errores.append("❌ Python embebido no encontrado.\n   Ejecuta setup.bat primero.")
    if not os.path.exists(MAIN):
        errores.append("❌ Archivo main.py no encontrado.\n   La carpeta app\\ está incompleta.")
    if not os.path.exists(MODELO):
        errores.append("❌ Modelo de IA no encontrado.\n   Ejecuta descargar_modelo.bat primero.")
    return errores
 
# ── Iniciar servidor ──────────────────────────────────
 
server_process = None
 
def iniciar_servidor():
    global server_process
    os.makedirs(os.path.join(BASE, "data"), exist_ok=True)
 
    with open(LOG, "w", encoding="utf-8") as log_file:
        server_process = subprocess.Popen(
            [PYTHON, MAIN],
            stdout=log_file,
            stderr=log_file,
            cwd=os.path.join(BASE, "app"),
            creationflags=subprocess.CREATE_NO_WINDOW,  # sin ventana de CMD
        )
 
def abrir_navegador():
    time.sleep(4)
    webbrowser.open("http://localhost:8000")
 
# ── Ventana de estado ─────────────────────────────────
 
def crear_ventana():
    root = tk.Tk()
    root.title("Buscador SGI — COBRA PERU")
    root.geometry("340x200")
    root.resizable(False, False)
    root.configure(bg="#0a0a0a")
 
    # Centrar ventana
    root.eval('tk::PlaceWindow . center')
 
    # Ícono (si existe)
    ico_path = os.path.join(BASE, "app", "frontend", "favicon.ico")
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass
 
    # Título
    tk.Label(
        root, text="Buscador SGI",
        bg="#0a0a0a", fg="#e9004c",
        font=("Segoe UI", 14, "bold")
    ).pack(pady=(20, 2))
 
    tk.Label(
        root, text="COBRA PERU / BISA",
        bg="#0a0a0a", fg="#555555",
        font=("Segoe UI", 9)
    ).pack()
 
    # Estado
    status_var = tk.StringVar(value="⏳ Iniciando servidor...")
    status_lbl = tk.Label(
        root, textvariable=status_var,
        bg="#0a0a0a", fg="#a1a1a1",
        font=("Segoe UI", 9)
    )
    status_lbl.pack(pady=12)
 
    # Actualizar estado después de 4 segundos
    def actualizar_estado():
        time.sleep(4)
        status_var.set("✅ Servidor activo en localhost:8000")
 
    threading.Thread(target=actualizar_estado, daemon=True).start()
 
    # Botón abrir navegador
    tk.Button(
        root,
        text="↗  Abrir en el navegador",
        bg="#e9004c", fg="white",
        font=("Segoe UI", 9, "bold"),
        relief="flat", cursor="hand2",
        padx=16, pady=6,
        command=lambda: webbrowser.open("http://localhost:8000")
    ).pack(pady=4)
 
    # Botón ver log
    tk.Button(
        root,
        text="📋  Ver registro",
        bg="#1a1a1a", fg="#a1a1a1",
        font=("Segoe UI", 9),
        relief="flat", cursor="hand2",
        padx=16, pady=4,
        command=lambda: os.startfile(LOG) if os.path.exists(LOG) else None
    ).pack()
 
    tk.Label(
        root,
        text="No cierres esta ventana mientras usas el buscador.",
        bg="#0a0a0a", fg="#333333",
        font=("Segoe UI", 8)
    ).pack(pady=(10, 0))
 
    # Al cerrar la ventana → detener el servidor
    def on_close():
        global server_process
        if server_process:
            server_process.terminate()
        root.destroy()
 
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
 
# ── MAIN ──────────────────────────────────────────────
 
if __name__ == "__main__":
    # 1. Verificar requisitos
    errores = verificar()
    if errores:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Buscador SGI — Error",
            "\n\n".join(errores)
        )
        root.destroy()
        sys.exit(1)
 
    # 2. Iniciar servidor en hilo separado
    t_server = threading.Thread(target=iniciar_servidor, daemon=True)
    t_server.start()
 
    # 3. Abrir navegador en hilo separado
    t_browser = threading.Thread(target=abrir_navegador, daemon=True)
    t_browser.start()
 
    # 4. Mostrar ventana de control (bloquea hasta que el usuario cierra)
    crear_ventana()