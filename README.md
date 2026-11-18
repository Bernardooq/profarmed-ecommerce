# Profarmed — Entorno Demo & Showroom E-Commerce B2B & WMS

![Profarmed Demo](https://img.shields.io/badge/Environment-Demo%20%2F%20Sandbox-indigo)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2015-336791?logo=postgresql&logoColor=white)
![PBAC](https://img.shields.io/badge/Security-Dynamic%20PBAC%20(66%20Perms)-purple)
![Docker Turnkey](https://img.shields.io/badge/Docker-100%25%20Turnkey-blue?logo=docker&logoColor=white)

Entorno de demostración, pruebas y showroom de la plataforma B2B farmacéutica y sistema de gestión de almacenes (WMS) bajo la marca **Profarmed**. Este repositorio proporciona un ambiente autosuficiente y aislado para demostraciones en vivo a clientes potenciales, validación de nuevas características y auditoría funcional sin dependencias de infraestructura productiva.

---

## 🧩 Módulos Principales de la Plataforma

1. **🛒 Storefront B2B & Pedidos Mayoristas**:
   - Catálogo de alto volumen con búsqueda difusa (`pg_trgm`), listas de precios dinámicas por cliente, descuentos escalonados, listas de favoritos e importación masiva de carritos vía Excel (`.xlsx`).
   - Levantamiento de pedidos en campo por vendedores asignados (`POST /orders/create-for-customer`) con aislamiento por grupos comerciales (`SalesGroups`).
2. **🏭 Gestión de Almacén (WMS) & Surtido por Escáner Láser**:
   - División automática y manual de pedidos en **Order Splits** por zonas/operadores.
   - **Estación de Escaneo Láser (`WarehouseLaserStation`)** y terminales dedicadas para surtidores (`operator`) y verificadores (`checker`) con validación de códigos de barras, piezas faltantes y trazabilidad de auditoría.
3. **🛡️ RBAC / PBAC Dinámico en Tiempo Real**:
   - Matriz completa de **66 permisos canónicos** evaluados en $O(1)$ tanto en FastAPI (`require_permission`) como en React (`usePermissions`).
   - Creación de roles personalizados al vuelo, dependencias jerárquicas automáticas y revocación instantánea de sesión si un rol es desactivado.
4. **📊 Unified Dashboard (`/dashboard`) & Inteligencia Comercial**:
   - Panel administrativo unificado que adapta sus módulos según los permisos del usuario activo.
   - Reportes financieros, rentabilidad de órdenes (protegida con `_strip_admin_fields`), KPIs de ventas y exportación a Excel.
5. **🎫 Mesa de Ayuda B2B (Tickets) & Marketing Omnicanal**:
   - Sistema de tickets de soporte con hilos de conversación, evidencias en AWS S3 y flujos de escalamiento/desescalamiento.
   - Historias interactivas estilo redes sociales (`StoriesBar`), pop-ups promocionales, banners inferiores y difusión masiva por correo (`BackgroundTasks` SMTP).
6. **⚡ Sincronización Híbrida con ERP FoxPro (`.dbf`)**:
   - Sincronización multihilo desde demonios locales (`sync_local/` y `sync_alpha/`) o **carga directa de archivos DBF desde el navegador** en el panel de administración (`SyncPanel`).

---

## ✨ Características Especiales del Entorno Demo

1. **Despliegue 100% Turnkey**:
   - Al ejecutar `docker compose up --build`, el stack completo (PostgreSQL 15, FastAPI, React 19 + Vite) se levanta automáticamente.
   - Siembra automatizada de roles PBAC, los 66 permisos del sistema y usuarios de prueba mediante `create_initial_admins.py`.
2. **Bypass de Cloudflare Turnstile**:
   - Los formularios de login, registro y contacto tienen el captcha desactivado en local/sandbox para permitir demostraciones y pruebas automatizadas fluidas.
3. **Poblado Inmediato de Catálogo**:
   - Los scripts de sincronización (`sync_local/servicios/`) y el cargador web permiten poblar el catálogo a partir de archivos DBF reales incluidos en `backend/dbfs/`.
   - Las imágenes de productos apuntan de forma predeterminada al CDN de Profarmed (`https://img.profarmed.com.mx/{id}.webp`), brindando una experiencia visual idéntica a producción sin clonar gigabytes de imágenes.
4. **Cargas de Prueba en Vivo (Sandbox S3)**:
   - Las cargas manuales de banners promocionales, adjuntos de tickets y fotos de productos se ejecutan en los buckets sandbox (`profarmed-promos`, `profarmed-imgs`) servidos por CloudFront.
5. **Identidad Visual Profarmed**:
   - **Tipografía**: Plus Jakarta Sans.
   - **Paleta de Colores**: Royal Indigo (`#4F46E5`), Sky Cyan (`#0EA5E9`), Vibrant Coral (`#F97316`) y modo oscuro Obsidian (`#0B0F19`).

---

## 🚀 Puesta en Marcha en 1 Minuto

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Bernardooq/profarmed-ecommerce.git
cd profarmed-ecommerce
```

### 2. Iniciar con Docker Compose
```bash
docker compose up --build
```

El sistema estará listo en:
- **Tienda y Panel Unificado (`/dashboard`)**: [http://localhost:3000](http://localhost:3000)
- **API REST Backend**: [http://localhost:8000](http://localhost:8000)
- **Documentación OpenAPI / Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Base de Datos PostgreSQL**: `localhost:5432` (Base de datos: `profarmed_db`)

---

## 🔑 Credenciales de Prueba Predeterminadas

El script `create_initial_admins.py` siembra automáticamente las siguientes cuentas al iniciar el contenedor backend:

| Rol | Usuario | Contraseña | Propósito |
|---|---|---|---|
| **Super Administrador** | `admin.demo` | `demoAdmin2026!` | Acceso total al Panel Unificado (`/dashboard`), gestión de roles PBAC, almacén, catálogo, clientes y reportes |
| **Admin de Sincronización** | `syncadminssuser2026` | `SyncProfarmed2026!Key` | Cuenta de servicio con token efímero para pipelines de sincronización DBF |

---

## 📦 Sincronización y Poblado de Datos Demo

Puedes poblar productos, precios, descuentos y clientes desde la interfaz web en **`/dashboard` → Sincronización DBF**, o ejecutando desde terminal los scripts sobre los DBFs incluidos en `backend/dbfs/`:

```bash
# Sincronizar catálogo de productos, categorías, precios y existencias
python sync_local/servicios/sync_multithread/sync_dbf_to_backend.py

# Sincronizar clientes de prueba
python sync_local/servicios/sync_multithread/sync_users_dbf.py
```

---

## 📚 Documentación Técnica & Arquitectura

La documentación del proyecto está organizada por dominios especializados:

### 🤖 Desarrollo Agéntico & Arquitectura
- [🤖 Guía Maestra para Agentes IA (`AGENTS.md`)](AGENTS.md) — Mapa vertical $O(1)$ de archivos, reglas de oro arquitectónicas y flujo de trabajo Full-Stack.
- [🧭 Grafo de Arquitectura e Inventario RAG (`docs/file_inventory.md`)](docs/file_inventory.md) — Índice semántico por dominios verticales para navegación rápida y consultas IA.
- [📋 Catálogo Maestro de Permisos, Restricciones y PBAC (`docs/PERMISSIONS_AND_CONSTRAINTS.md`)](docs/PERMISSIONS_AND_CONSTRAINTS.md) — Especificación de los **66 permisos**, dependencias jerárquicas y reglas de aislamiento por grupo comercial.
- [🏭 Especificación de Arquitectura de Almacén & WMS (`docs/WAREHOUSE_ARCHITECTURE_SPEC.md`)](docs/WAREHOUSE_ARCHITECTURE_SPEC.md) — Flujo de surtido láser, *Order Splits*, terminales de chequeo y permisos de almacén.

### 🗄️ Base de Datos & Entorno Local
- [🚀 Guía de Despliegue y Ejecución de Base de Datos (`database/README.md`)](database/README.md) — Orden de ejecución de scripts SQL (`schema/01_init.sql`, `migrations/001_consolidated.sql` y seeds PBAC).
- [🗄️ Guía de Aislamiento y Gestión Multi-Tenant (`docs/MULTITENANT_DB_GUIDE.md`)](docs/MULTITENANT_DB_GUIDE.md) — Estrategias de particionamiento y multitenencia para distribuidoras farmacéuticas.
- [📖 Guía Rápida de Docker Turnkey (`docs/DOCKER_QUICKSTART.md`)](docs/DOCKER_QUICKSTART.md) — Arranque inmediato del stack de desarrollo local con Docker Compose.

### ☁️ Infraestructura AWS & CloudFormation
- [☁️ Guía de Arquitectura y Despliegue en AWS (`docs/DEPLOY_GUIDE.md`)](docs/DEPLOY_GUIDE.md) — Manual de despliegue en EC2, ASG, ALB, S3, CloudFront y pipelines CI/CD.
- [🏗️ Ficha de Requerimientos CloudFormation (`aws/cloudformation/CLOUDFORMATION_REQUIREMENTS.md`)](aws/cloudformation/CLOUDFORMATION_REQUIREMENTS.md) — Parámetros exactos para el stack IaC de producción.
- [🔒 Políticas IAM de Mínimo Privilegio (`aws/policies/README.md`)](aws/policies/README.md) — Políticas de despliegue y roles de instancia EC2/S3/ECR/SSM.

### 📄 Propuestas Técnicas & RFCs
- [🛡️ RFC: Migración a RBAC / PBAC Dinámico (`docs/proposals/PROPOSAL_DYNAMIC_ROLES_PERMISSIONS.md`)](docs/proposals/PROPOSAL_DYNAMIC_ROLES_PERMISSIONS.md) — Especificación arquitectónica de la migración a roles y permisos dinámicos.
- [💼 Propuesta Técnica & Discovery para Clientes (`docs/proposals/PROPOSAL_DISCOVERY_NEW_CLIENTS.md`)](docs/proposals/PROPOSAL_DISCOVERY_NEW_CLIENTS.md) — Alcance funcional, integraciones ERP y propuesta comercial para nuevos prospectos.
