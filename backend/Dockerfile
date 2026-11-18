FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema, psycopg2, Nginx y Cron
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    nginx \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Configurar Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/conf.d/profarmed.conf

# Configurar Cron
COPY profarmed-cron /etc/cron.d/profarmed-cron
RUN chmod 0644 /etc/cron.d/profarmed-cron

# Copiar e instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Dar permisos de ejecución al entrypoint
RUN chmod +x entrypoint.sh

# Configurar variables de entorno para que Python encuentre los módulos
ENV PYTHONPATH=/app:/app/profarmed_api
ENV PYTHONUNBUFFERED=1

# Exponer el puerto 80 para el proxy inverso de Nginx
EXPOSE 80

# Comando de arranque vía entrypoint
CMD ["./entrypoint.sh"]
