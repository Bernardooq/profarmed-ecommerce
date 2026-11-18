# Profarmed — Base de Datos PostgreSQL

Esquema relacional sobre **PostgreSQL 15+** con extensión `pg_trgm` (búsqueda difusa de catálogo), soporte PBAC dinámico (`roles`, `permissions`, `role_permissions`), grupos comerciales N:M (`group_users`), logística de almacén (`warehouse_splits`), estadísticas anuales precalculadas (`product_yearly_stats`) y control transaccional de stock (`order_stock_holds`).

---

## 📁 Estructura de la Carpeta `database/`

```text
database/
├── Dockerfile                                    # Imagen PostgreSQL 15 Alpine para entorno Docker
├── README.md                                     # Guía unificada de arquitectura y despliegue SQL
├── schema/
│   ├── 01_init.sql                               # Esquema DDL maestro v2 (instalaciones nuevas en frío)
│   └── legacy_init.sql                           # Referencia histórica del esquema legacy previo a PBAC/splits
├── migrations/
│   ├── 001_consolidated.sql                      # Migración consolidada idempotente para BD existentes
│   └── patches/
│       ├── 001_backfill_group_users.sql          # Respaldo histórico (ya incluido en 001_consolidated.sql)
│       └── 002_recalculate_yearly_stats.sql      # Recálculo / backfill manual de product_yearly_stats
├── seeds/
│   ├── 01_roles_permissions.sql                  # Roles base, catálogo de 75 permisos PBAC y matriz role_permissions
│   └── 02_system_configs.sql                     # Feature flags operativos iniciales en system_configs
└── diagnostics/
    └── sync_check.sql                            # Consultas rápidas de diagnóstico y últimos registros por tabla
```

---

## 📌 Resumen de Scripts

| Script | Propósito | ¿Cuándo ejecutarlo? |
| :--- | :--- | :--- |
| [`migrations/001_consolidated.sql`](migrations/001_consolidated.sql) | Migración estructural idempotente: splits de almacén, `group_users`, `product_yearly_stats`, `order_stock_holds`, `is_synced` y migración de `users.role` $\rightarrow$ `users.role_id`. | **Paso 1** en bases de datos existentes con datos previos. |
| [`seeds/01_roles_permissions.sql`](seeds/01_roles_permissions.sql) | Crea/actualiza roles del sistema, **75 permisos canónicos** (`depends_on`) y matriz inicial `role_permissions`. | **Paso 2** tras migrar o en cold install tras `01_init.sql`. |
| [`seeds/02_system_configs.sql`](seeds/02_system_configs.sql) | Inserta/actualiza banderas globales en `system_configs` (`order.apartar`, `order.discount`, `catalog.order_by_priority`, `catalog.weekly_rotation`, etc.). | **Paso 3** (idempotente). |
| [`schema/01_init.sql`](schema/01_init.sql) | DDL completo v2 (tablas, tipos, índices GIN/trigramas, secuencias). | **Solo instalaciones nuevas en frío** (o Docker initdb). |

---

## 🛠️ ESCENARIO A: Producción con Base de Datos Existente

Ejecuta los scripts en este orden estricto para actualizar sin pérdida de datos:

```bash
# 1. Aplicar migración estructural consolidada
psql -h localhost -U profarmed_user -d profarmed_db -f database/migrations/001_consolidated.sql

# 2. Poblar / sincronizar catálogo de roles y permisos PBAC
psql -h localhost -U profarmed_user -d profarmed_db -f database/seeds/01_roles_permissions.sql

# 3. Poblar / actualizar banderas globales del sistema
psql -h localhost -U profarmed_user -d profarmed_db -f database/seeds/02_system_configs.sql
```

> [!NOTE]
> No necesitas correr por separado [`migrations/patches/001_backfill_group_users.sql`](migrations/patches/001_backfill_group_users.sql) ni [`migrations/patches/002_recalculate_yearly_stats.sql`](migrations/patches/002_recalculate_yearly_stats.sql): ambos pasos ya vienen incluidos dentro de [`migrations/001_consolidated.sql`](migrations/001_consolidated.sql). Se conservan en `migrations/patches/` como respaldo y para recálculos manuales puntuales.

---

## ❄️ ESCENARIO B: Instalación Limpia en Frío (Nueva Base de Datos)

```bash
# 1. Crear esquema maestro completo
psql -h localhost -U profarmed_user -d profarmed_db -f database/schema/01_init.sql

# 2. Poblar roles base y los 75 permisos PBAC
psql -h localhost -U profarmed_user -d profarmed_db -f database/seeds/01_roles_permissions.sql

# 3. Poblar banderas iniciales en system_configs
psql -h localhost -U profarmed_user -d profarmed_db -f database/seeds/02_system_configs.sql
```

*(En Docker local, [`database/Dockerfile`](Dockerfile) y `docker-compose.yaml` montan automáticamente [`schema/01_init.sql`](schema/01_init.sql) en `/docker-entrypoint-initdb.d/01-init.sql`).*

---

## ✅ Verificación Post-Despliegue

```sql
-- 1. Verificar uso de role_id en users
SELECT user_id, username, role_id FROM users LIMIT 5;

-- 2. Verificar roles del sistema
SELECT role_id, slug, name FROM roles ORDER BY role_id;

-- 3. Verificar catálogo completo de permisos PBAC (75 permisos actuales)
SELECT count(*) AS total_permisos FROM permissions;

-- 4. Verificar permisos asignados por rol
SELECT r.slug, count(rp.permission_code) AS permisos_asignados
FROM roles r
LEFT JOIN role_permissions rp ON r.role_id = rp.role_id
GROUP BY r.slug;
```

Para inspeccionar rápidamente los últimos registros sincronizados desde el ERP:

```bash
psql -h localhost -U profarmed_user -d profarmed_db -f database/diagnostics/sync_check.sql
```
