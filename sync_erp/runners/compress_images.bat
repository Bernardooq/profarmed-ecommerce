@echo off
set "logfile=%~dp0..\logs\compress_images.log"

:: Rotacion: Si el log supera 5 MB (5,242,880 bytes), renombra a .log.1 (borrando el .log.1 viejo)
if exist "%logfile%" (
    for %%F in ("%logfile%") do (
        if %%~zF GTR 5242880 (
            del /f /q "%logfile%.1" 2>nul
            move /y "%logfile%" "%logfile%.1" >nul 2>&1
        )
    )
)

call :main >> "%logfile%" 2>&1
exit /b

:main
echo [%date% %time%] Inicio Compresion de Imagenes
cd /d "%~dp0.."
echo ===================================================
echo Optimizando Imagenes a WebP
echo ===================================================

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else if exist "..\venv\Scripts\python.exe" (
    set "PY_EXE=..\venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" src\images\compress_images.py

echo.
echo Proceso finalizado.
echo [%date% %time%] Fin
echo ---------------------------------------------------
goto :eof

