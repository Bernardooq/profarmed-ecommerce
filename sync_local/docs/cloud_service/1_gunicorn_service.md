# Instalación de Servicio Uvicorn en EC2 (Amazon Linux)

## Arquitectura
- **t3.micro**: 1 vCPU, 1GB RAM
- **Gunicorn+Uvicorn**: 4 workers (configuración robusta)
- **ThreadPoolExecutor**: Maneja sync tasks en background (max_workers=2)

## 1. Crear el archivo del servicio
```bash
sudo nano /etc/systemd/system/profarmed-api.service
```

## 2. Contenido del servicio
```ini
[Unit]
Description=Profarmed FastAPI Backend (Gunicorn + Uvicorn)
After=network.target

[Service]
Type=simple
User=ec2-user
Group=nginx
WorkingDirectory=/home/ec2-user/profarmed-ecomerce/backend
Environment="PATH=/home/ec2-user/profarmed-ecomerce/backend/venv/bin"
Environment="PYTHONPATH=/home/ec2-user/profarmed-ecomerce/backend"

ExecStart=/home/ec2-user/profarmed-ecomerce/backend/venv/bin/gunicorn \
    profarmed_api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 120

# Restart automático
Restart=always
RestartSec=3

# Límites de recursos
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
```

## 3. Crear directorio de logs
```bash
sudo mkdir -p /var/log/profarmed
sudo chown ec2-user:nginx /var/log/profarmed
```

## 4. Activar el servicio
```bash
sudo systemctl daemon-reload
sudo systemctl enable profarmed-api
sudo systemctl start profarmed-api
```

## 5. Verificar estado
```bash
# Ver estado
sudo systemctl status profarmed-api

# Ver logs en tiempo real
sudo journalctl -u profarmed-api -f

# Ver últimos 50 logs
sudo journalctl -u profarmed-api -n 50 --no-pager
```

## 6. Comandos útiles
```bash
# Reiniciar después de cambios en código
sudo systemctl restart profarmed-api

# Detener servicio
sudo systemctl stop profarmed-api

# Ver logs de errores
sudo journalctl -u profarmed-api -p err
```

## Notas
- **1 worker** es suficiente para t3.micro (1 vCPU)
- **ThreadPoolExecutor** en el código maneja tareas pesadas (sync DBF)
- Logs van a `journalctl` (systemd), no a archivos separados
