@echo off
chcp 65001 >nul
title Empaquetando BuscadorSGI
cls

echo.
echo  ╔════════════════════════════════════════════╗
echo  ║        Empaquetando BuscadorSGI            ║
echo  ╚════════════════════════════════════════════╝
echo.

REM ── Verificar que existe el .exe compilado ────────────
if not exist "%~dp0dist\BuscadorSGI.exe" (
    echo  [ERROR] No se encontro dist\BuscadorSGI.exe
    echo  Ejecuta primero: compilar_exe.bat
    pause
    exit /b 1
)

REM ── Crear carpeta de distribución ────────────────────
set DIST_DIR=%~dp0BuscadorSGI_FINAL
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

echo  Copiando archivos...

REM ── Copiar el .exe ────────────────────────────────────
copy "%~dp0dist\BuscadorSGI.exe" "%DIST_DIR%\" >nul

REM ── Copiar Python embebido ────────────────────────────
if exist "%~dp0python" (
    xcopy "%~dp0python" "%DIST_DIR%\python\" /e /i /q >nul
    echo  [OK] Python embebido copiado.
) else (
    echo  [AVISO] Carpeta python\ no encontrada.
    echo  El usuario necesitara ejecutar setup.bat.
)

REM ── Copiar modelo de IA ───────────────────────────────
if exist "%~dp0modelo" (
    xcopy "%~dp0modelo" "%DIST_DIR%\modelo\" /e /i /q >nul
    echo  [OK] Modelo de IA copiado.
) else (
    echo  [AVISO] Carpeta modelo\ no encontrada.
    echo  El usuario necesitara ejecutar descargar_modelo.bat.
)

REM ── Copiar código de la app ───────────────────────────
xcopy "%~dp0app" "%DIST_DIR%\app\" /e /i /q >nul
echo  [OK] App copiada.

REM ── Copiar archivos de soporte ────────────────────────
copy "%~dp0setup.bat"            "%DIST_DIR%\" >nul
copy "%~dp0descargar_modelo.bat" "%DIST_DIR%\" >nul
copy "%~dp0README.txt"           "%DIST_DIR%\" >nul
echo  [OK] Archivos de soporte copiados.

REM ── Crear carpeta data vacía ──────────────────────────
mkdir "%DIST_DIR%\data" >nul

echo.
echo  ╔════════════════════════════════════════════╗
echo  ║   Paquete listo en: BuscadorSGI_FINAL\     ║
echo  ║                                            ║
echo  ║   Contenido:                               ║
echo  ║   ├── BuscadorSGI.exe  ← doble click       ║
echo  ║   ├── python\                              ║
echo  ║   ├── modelo\                              ║
echo  ║   ├── app\                                 ║
echo  ║   ├── data\                                ║
echo  ║   ├── setup.bat                            ║
echo  ║   ├── descargar_modelo.bat                 ║
echo  ║   └── README.txt                           ║
echo  ╚════════════════════════════════════════════╝
echo.
echo  Comprime BuscadorSGI_FINAL\ en .zip y distribuyelo.
echo.
pause