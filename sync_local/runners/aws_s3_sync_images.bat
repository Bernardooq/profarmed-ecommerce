@echo off
set "logfile=%~dp0..\logs\aws_s3_sync_images.log"

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
echo [%date% %time%] Inicio de Sincronizacion
setlocal
cd /d "%~dp0.."

:: Credenciales de AWS (Para Task Scheduler)
set AWS_ACCESS_KEY_ID=PONER_AQUI_ACCESS_KEY
set AWS_SECRET_ACCESS_KEY=PONER_AQUI_SECRET_KEY
set AWS_DEFAULT_REGION=us-east-1

echo ===================================================
echo Sincronizacion de Imagenes a S3 (profarmed-imgs)
echo ===================================================

set LOCAL_DIR="C:\Users\berna\Downloads\CompressedImg"

echo Sincronizando: %LOCAL_DIR% -^> s3://profarmed-imgs
echo.

aws s3 sync %LOCAL_DIR% s3://profarmed-imgs

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Hubo un problema al sincronizar.
) else (
    echo.
    echo [EXITO] Sincronizacion completada con exito.
)

echo.
echo [%date% %time%] FIN
endlocal
echo ---------------------------------------------------
goto :eof
