@echo off
set "logfile=%~dp0..\logs\upload_users.log"

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
echo [%date% %time%] Inicio
cd /d "%~dp0.."
echo ===================================================
echo Sincronizando Usuarios (Clientes y Agentes) ERP
echo ===================================================

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else if exist "..\venv\Scripts\python.exe" (
    set "PY_EXE=..\venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" src\uploader\sync_users.py

echo.
echo Proceso finalizado.
echo [%date% %time%] Fin
echo ---------------------------------------------------
goto :eof

