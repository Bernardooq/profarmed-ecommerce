# 🚀 Guía Rápida: Actualizar Docker sin perder datos ni reconstruir desde cero

En tu archivo [docker-compose.yaml](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/docker-compose.yaml), tanto el backend como el frontend ya tienen configurados **Volúmenes** y **Hot-Reload**:

- **Backend**: Corre con `uvicorn ... --reload` montando `./backend:/app`.
- **Frontend**: Corre con `vite --host 0.0.0.0` montando `./react/src:/app/src`.

---

## ⚡ 1. Los cambios normales de código (Python / JSX / SCSS)
👉 **¡No necesitas recompilar nada!** 
Al guardar cualquier archivo, `uvicorn` y `Vite` detectan los cambios automáticamente en vivo.

Si por alguna razón sientes que se trabó el hot-reload, solo reinicia el proceso del contenedor sin recrearlo:

```powershell
# Reiniciar backend al instante
docker compose restart backend

# Reiniciar frontend al instante
docker compose restart frontend

# O reiniciar ambos
docker compose restart backend frontend
```

---

## 🔄 2. Cuando agregas nuevas librerías (`requirements.txt` o `package.json`) o cambios en Dockerfile
Cuando instalas un nuevo paquete o cambias configuraciones de imagen, **sí requieres rebuild**, pero con cache de Docker:

```powershell
# Reconstruye solo lo que cambió usando cache y levanta en segundo plano
docker compose up -d --build backend frontend
```

> **Nota:** La base de datos (`db`) no se toca ni se borra porque sus datos viven en el volumen persistente `postgres_data`.

---

## 🗄️ 3. Si agregaste migraciones / tablas en SQL
Si creaste tablas nuevas en SQL o scripts de migración y necesitas aplicarlos a la BD sin tumbar el contenedor:

```powershell
# Ejecutar migración dentro del contenedor db
docker compose exec -T db psql -U profarmed_user -d profarmed_db < database/tu_migracion.sql
```

---

## 📋 Resumen de Comandos en 1 Línea

| Caso | Comando |
| :--- | :--- |
| **Código modificado (no tomó el reload)** | `docker compose restart backend frontend` |
| **Nuevas dependencias / Rebuild rápido** | `docker compose up -d --build` |
| **Ver logs en tiempo real** | `docker compose logs -f backend frontend` |
| **Estado de contenedores** | `docker compose ps` |
