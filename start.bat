@echo off
chcp 65001 > nul 2>&1
title 🏰 Servidor de Retratos de Hogwarts
color 0E

echo.
echo ========================================
echo   🏰  INICIANDO CASTILLO DE HOGWARTS
echo ========================================
echo.

REM Verificar Python
echo 🔍 Verificando Python...
py --version
if errorlevel 1 (
    echo.
    echo ❌ ERROR: Python no está instalado o no está en el PATH.
    echo    Descárgalo desde https://www.python.org/downloads/
    echo    ⚠️  IMPORTANTE: Al instalar, marca la casilla "Add Python to PATH"
    echo.
    goto :final
)

REM Crear entorno virtual si no existe
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo 🪄 Creando entorno virtual mágico...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Error al crear el entorno virtual.
        goto :final
    )
)

REM Activar entorno virtual
echo.
echo ✨ Activando entorno...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo.
echo 📦 Instalando/verificando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Error al instalar dependencias.
    goto :final
)

echo.
echo ========================================
echo   🏰  ¡EL CASTILLO ESTÁ ABIERTO!
echo ========================================
echo.
echo 🖼️  Galería Local:    http://localhost:5000/galeria
echo 📤 Página de Subida:  http://localhost:5000/
echo.
echo Presiona Ctrl+C para detener el servidor.
echo.

REM Ejecutar la aplicación
python app.py

:final
echo.
echo ========================================
echo   ⚠️  El servidor se detuvo.
echo ========================================
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause > nul