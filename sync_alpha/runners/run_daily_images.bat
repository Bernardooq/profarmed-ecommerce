@echo off
set "logfile=%~dp0..\logs\daily_images.log"

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
echo --- INICIANDO SERVICIO DE IMAGENES ---
date /t & time /t
cd /d "%~dp0.."

echo [1/2] Comprimiendo imagenes...
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else if exist "src\venv\Scripts\python.exe" (
    set "PY_EXE=src\venv\Scripts\python.exe"
) else if exist "services\venv\Scripts\python.exe" (
    set "PY_EXE=services\venv\Scripts\python.exe"
) else if exist "servicios\venv\Scripts\python.exe" (
    set "PY_EXE=servicios\venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" -m src.images.compress_images

echo [2/2] Sincronizando con AWS S3...
aws s3 sync "C:\ecommerce\compressedIMG" s3://profarmed-imgs --exclude "*" --include "*.webp" --cache-control "max-age=2592000"

echo --- FINALIZADO ---
goto :eof
