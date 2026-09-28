@echo off
echo ============================================
echo   Generando ejecutable de SignalLab
echo ============================================

REM --- Comprobar Python ---
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python no esta instalado o no esta en PATH
    pause
    exit /b 1
)

REM --- Comprobar PyInstaller ---
python -m PyInstaller --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo PyInstaller no esta instalado.
    echo Instalando PyInstaller...
    python -m pip install pyinstaller
)

REM --- Limpiar builds anteriores ---
echo Limpiando builds anteriores...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del SignalLab.spec 2>nul

REM --- Generar ejecutable ---
echo Generando SignalLab.exe con icono...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --icon assets\signallab.ico ^
    --name SignalLab ^
    --add-data "assets;assets" ^
    main.py

IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Fallo al generar el ejecutable.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Ejecutable generado correctamente
echo   Archivo: dist\SignalLab.exe
echo   Icono: senoide verde (minimalista)
echo ============================================

pause
