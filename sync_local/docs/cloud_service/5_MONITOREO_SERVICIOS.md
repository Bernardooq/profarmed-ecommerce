# Guía de Monitoreo y Control - Servicios Systemd

## Comandos Esenciales de Servicios

### Ver Estado Actual
```bash
# Backend API
sudo systemctl status profarmed-api

# Nginx
sudo systemctl status nginx

# Todos los servicios activos
systemctl list-units --type=service --state=running
```

### Controlar Servicios

#### 🚀 Iniciar
```bash
sudo systemctl start profarmed-api
sudo systemctl start nginx
```

#### 🛑 Detener
```bash
sudo systemctl stop profarmed-api
sudo systemctl stop nginx
```

#### 🔄 Reiniciar (detiene y vuelve a iniciar)
```bash
sudo systemctl restart profarmed-api
sudo systemctl restart nginx
```

#### ⚡ Reload (sin downtime - solo config)
```bash
# Solo Nginx soporta reload
sudo systemctl reload nginx

# Para profarmed-api debes usar restart
sudo systemctl restart profarmed-api
```

### Habilitar/Deshabilitar Auto-Start

#### Habilitar (iniciar automáticamente en boot)
```bash
sudo systemctl enable profarmed-api
sudo systemctl enable nginx
```

#### Deshabilitar (NO iniciar en boot)
```bash
sudo systemctl disable profarmed-api
sudo systemctl disable nginx
```

#### Verificar si está habilitado
```bash
sudo systemctl is-enabled profarmed-api
sudo systemctl is-enabled nginx
```

---

## Logs y Monitoreo

### Ver Logs de Backend (journalctl)

#### Últimos logs
```bash
# Últimas 50 líneas
sudo journalctl -u profarmed-api -n 50

# Últimas 200 líneas sin paginado
sudo journalctl -u profarmed-api -n 200 --no-pager
```

#### Logs en tiempo real
```bash
# Modo "tail -f" (seguir logs)
sudo journalctl -u profarmed-api -f

# Presionar Ctrl+C para salir
```

#### Filtrar por tiempo
```bash
# Última hora
sudo journalctl -u profarmed-api --since "1 hour ago"

# Últimas 2 horas
sudo journalctl -u profarmed-api --since "2 hours ago"

# Desde hoy
sudo journalctl -u profarmed-api --since today

# Desde ayer
sudo journalctl -u profarmed-api --since yesterday

# Fecha específica
sudo journalctl -u profarmed-api --since "2026-02-08 10:00:00"
```

#### Filtrar por severidad
```bash
# Solo errores
sudo journalctl -u profarmed-api -p err

# Errores y warnings
sudo journalctl -u profarmed-api -p warning

# Todo excepto debug
sudo journalctl -u profarmed-api -p info
```

### Ver Logs de Nginx

#### Access logs (peticiones)
```bash
# En tiempo real
sudo tail -f /var/log/nginx/access.log

# Últimas 100 líneas
sudo tail -n 100 /var/log/nginx/access.log
```

#### Error logs
```bash
# En tiempo real
sudo tail -f /var/log/nginx/error.log

# Últimas 50 líneas
sudo tail -n 50 /var/log/nginx/error.log

# Buscar errores específicos
sudo grep "error" /var/log/nginx/error.log | tail -n 20
```

---

## Monitoreo de Recursos

### Verificar Puertos
```bash
# Ver qué proceso usa puerto 8000
sudo netstat -tlnp | grep :8000

# Ver todos los puertos en uso
sudo netstat -tlnp

# Alternativa moderna (si tienes ss)
sudo ss -tlnp | grep :8000
```

### Monitoreo de Procesos
```bash
# Procesos de Python (backend)
ps aux | grep python

# Procesos de Nginx
ps aux | grep nginx

# Ver árbol de procesos
pstree -p | grep profarmed
```

### Uso de Recursos
```bash
# Vista interactiva (CPU, RAM)
htop

# Presionar 'q' para salir

# Alternativa sin htop
top
```

### Memoria
```bash
# Vista human-readable
free -h

# Ver memoria en MB
free -m
```

### Disco
```bash
# Uso de disco
df -h

# Uso por directorio
du -sh ~/profarmed-ecomerce/*
```

---

## Verificaciones de Salud

### Test de Conexión Backend
```bash
# Test local
curl http://127.0.0.1:8000/api/v1/health

# Test desde fuera (si tienes endpoint health)
curl https://digheqbxnmxr3.cloudfront.net/api/v1/health
```

### Test de Conexión RDS
```bash
# Conectar a RDS
psql -h profarmed.xxxxx.us-east-1.rds.amazonaws.com \
     -U profarmed_user \
     -d profarmed_db

# Test rápido (ejecutar query)
psql -h profarmed.xxxxx.us-east-1.rds.amazonaws.com \
     -U profarmed_user \
     -d profarmed_db \
     -c "SELECT version();"
```

### Verificar Nginx Config
```bash
# Test de configuración (sin aplicar)
sudo nginx -t

# Si sale OK, aplicar cambios
sudo systemctl reload nginx
```

---

## Troubleshooting Rápido

### Backend crasheó
```bash
# 1. Ver últimos errores
sudo journalctl -u profarmed-api -n 100 --no-pager | tail -n 50

# 2. Verificar que RDS esté accesible
psql -h RDS_ENDPOINT -U profarmed_user -d profarmed_db -c "SELECT 1"

# 3. Reiniciar
sudo systemctl restart profarmed-api

# 4. Ver si arrancó
sudo systemctl status profarmed-api
```

### Nginx devuelve 502 Bad Gateway
```bash
# 1. Verificar backend activo
sudo systemctl status profarmed-api

# 2. Ver logs de nginx
sudo tail -f /var/log/nginx/error.log

# 3. Test directo al backend
curl http://127.0.0.1:8000/api/v1/health

# 4. Reiniciar ambos
sudo systemctl restart profarmed-api
sudo systemctl restart nginx
```

### Logs llenando disco
```bash
# Ver tamaño de logs
sudo journalctl --disk-usage

# Limpiar logs mayores a 7 días
sudo journalctl --vacuum-time=7d

# Limpiar manteniendo solo 500MB
sudo journalctl --vacuum-size=500M
```

---

## Comandos de Emergencia

### Reinicio Completo
```bash
# Reiniciar todos los servicios
sudo systemctl restart profarmed-api nginx

# Ver estado de todo
sudo systemctl status profarmed-api nginx
```

### Ver Todos los Errores Recientes
```bash
# Últimos 50 errores del sistema
sudo journalctl -p err -n 50 --no-pager

# Errores de hoy
sudo journalctl -p err --since today
```

### Recargar Configuración de Systemd
```bash
# Después de editar archivos .service
sudo systemctl daemon-reload
```

---

## Atajos Útiles

```bash
# Alias útil (agregar a ~/.bashrc)
alias logs-api='sudo journalctl -u profarmed-api -f'
alias logs-nginx='sudo tail -f /var/log/nginx/error.log'
alias status-all='sudo systemctl status profarmed-api nginx'
alias restart-all='sudo systemctl restart profarmed-api nginx'
```

**Aplicar aliases:**
```bash
echo "alias logs-api='sudo journalctl -u profarmed-api -f'" >> ~/.bashrc
echo "alias logs-nginx='sudo tail -f /var/log/nginx/error.log'" >> ~/.bashrc
source ~/.bashrc
```
