@echo off
chcp 65001 >nul
title Compilando Buscador SGI con Nuitka
cls

echo.
echo  ╔════════════════════════════════════════════╗
echo  ║     Compilando launcher.exe con Nuitka     ║
echo  ╚════════════════════════════════════════════╝
echo.
echo  Este proceso tarda 3-8 minutos.
echo  No cierres esta ventana.
echo.

REM ── Verificar que Nuitka está instalado ───────────────
python -c "import nuitka" 2>nul
if errorlevel 1 (
    echo  Instalando Nuitka...
    pip install nuitka zstandard ordered-set
)

REM ── Verificar que gcc está disponible ─────────────────
gcc --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] No se encontro el compilador gcc.
    echo  Instala MinGW-w64 desde: https://winlibs.com
    echo  y agrega C:\mingw64\bin al PATH de Windows.
    echo.
    pause
    exit /b 1
)

echo  [OK] gcc encontrado.
echo  [OK] Nuitka listo.
echo.
echo  Compilando...
echo.

REM ── Compilar con Nuitka ───────────────────────────────
python -m nuitka ^
    --onefile ^
    --windows-disable-console ^
    --windows-icon-from-ico=app\frontend\favicon.ico ^
    --output-filename=BuscadorSGI.exe ^
    --output-dir=dist ^
    --enable-plugin=tk-inter ^
    --assume-yes-for-downloads ^
    --company-name="COBRA PERU S.A" ^
    --product-name="Buscador SGI" ^
    --file-version=1.0.0.0 ^
    --product-version=1.0.0.0 ^
    --file-description="Buscador de Documentos SGI" ^
    --copyright="COBRA PERU S.A / BISA" ^
    launcher.py

if errorlevel 1 (
    echo.
    echo  [ERROR] La compilacion fallo.
    echo  Revisa los mensajes de error arriba.
    pause
    exit /b 1
)

echo.
echo  ╔════════════════════════════════════════════╗
echo  ║   Compilacion exitosa                      ║
echo  ║   Archivo: dist\BuscadorSGI.exe            ║
echo  ╚════════════════════════════════════════════╝
echo.
echo  Copia dist\BuscadorSGI.exe a la raiz del proyecto
echo  junto con las carpetas: python\ modelo\ app\ data\
echo.
pause