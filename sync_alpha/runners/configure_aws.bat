@echo off
echo ===================================================
echo Configuracion de Perfil AWS (s3-sync-profarmed)
echo ===================================================
echo.
echo Por favor, Access Key ID y Secret Access Key.
echo.
echo Configurando perfil 's3-sync-profarmed'...
echo.

aws configure --profile s3-sync-profarmed

echo.
echo ===================================================
echo Configuracion completada.
echo Ahora puedes ejecutar 'aws_s3_sync_images.bat'
echo ===================================================
