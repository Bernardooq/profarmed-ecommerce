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
echo [%date% %time%] Inicio Sincronizacion S3
setlocal
cd /d "%~dp0.."

:: Credenciales de AWS (Opcional si AWS CLI ya esta configurado globalmente)
:: set AWS_ACCESS_KEY_ID=
:: set AWS_SECRET_ACCESS_KEY=
set AWS_DEFAULT_REGION=us-east-1

set "LOCAL_DIR=C:\Users\berna\Downloads\CompressedImg"
set "S3_BUCKET=profarmed-imgs"

if exist "%~dp0..\.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0..\.env") do (
        if /i "%%A"=="IMAGES_FOLDER_OUTPUT" if not "%%B"=="" set "LOCAL_DIR=%%~B"
        if /i "%%A"=="S3_BUCKET" if not "%%B"=="" set "S3_BUCKET=%%~B"
    )
)

echo ===================================================
echo Sincronizacion Recursiva de Imagenes a S3 (%S3_BUCKET%)
echo ===================================================

echo Sincronizando: "%LOCAL_DIR%" -^> s3://%S3_BUCKET%
echo.

aws s3 sync "%LOCAL_DIR%" s3://%S3_BUCKET%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Hubo un problema al sincronizar con S3.
) else (
    echo.
    echo [EXITO] Sincronizacion S3 completada con exito.
)

echo.
echo [%date% %time%] FIN
endlocal
echo ---------------------------------------------------
goto :eof

