#!/bin/bash
set -e

# Exportar las variables de entorno de Docker para que cron las pueda leer
# (Esencial para que el script product_similarity.py tenga acceso a DATABASE_URL)
echo "Exportando variables de entorno para cron..."
printenv | grep -v "no_proxy" >> /etc/environment

# Arrancar el servicio de cron en background
echo "Iniciando Cron..."
service cron start

# Arrancar Nginx en background
echo "Iniciando Nginx..."
service nginx start

# Iniciar la aplicación FastAPI con Gunicorn (modo producción)
echo "Iniciando FastAPI Backend..."
exec gunicorn profarmed_api.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --log-level info
