# 🤖 AGENTS.md — Guía Maestra de Arquitectura para Desarrollo Agéntico (AI Agent Playbook)

> **Proyecto:** Profarmed / Profarmed B2B E-Commerce & Warehouse Management System  
> **Propósito:** Proporcionar a los agentes de IA (Antigravity / Gemini / Copilots) y desarrolladores un mapa O(1) de ubicación de archivos, patrones arquitectónicos y reglas de oro para ejecutar cambios con máxima velocidad, consistencia y cero regresiones.

---

## 1. 🗺️ Mapa de Dominio Vertical (Vertical Slice Directory)

Utiliza esta tabla para ubicar de inmediato los archivos involucrados en cualquier funcionalidad sin necesidad de escanear directorios:

| Dominio Funcional | Backend Route (`routes/`) | Backend CRUD (`crud/`) | Pydantic Schema (`schemas/`) | Frontend Service (`services/`) | UI Components / Pages (`src/`) | Permisos Clave (PBAC) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **🔐 Autenticación & Sesión** | `auth.py` | — | `auth.py` | `authService.js` | `components/users/LoginForm.jsx` | Público / `auth/me` |
| **👥 Usuarios Internos** | `admin.py`, `users.py` | `crud_user.py` | `user.py` | `userService.js` | `components/users/UserFormModal.jsx` | `users.view`, `users.create`, `users.edit`, `users.delete` |
| **🛡️ Roles & PBAC Dinámico** | `roles.py` | `crud_role.py` | `role.py` | `adminService.js` | `components/admin/RolesManagement.jsx`, `RoleFormModal.jsx` | `roles.view`, `roles.assign`, `system.admin` |
| **🛒 Carrito & Favoritos B2B** | `orders.py`, `favorites.py` | `crud_cart.py`, `crud_favorite.py` | `order.py`, `favorite.py` | `favoriteService.js`, `CartContext.jsx` | `pages/Cart.jsx`, `pages/FavoriteLists.jsx`, `FavoriteListDetails.jsx` | *Exclusivo Cliente (Sesión `customer_id`)* |
| **📦 Pedidos & Fulfillment** | `orders.py` | `crud_order.py`, `crud_order_edit.py` | `order.py` | `orderService.js` | `components/orders/AllOrders.jsx`, `OrderRowAdmin.jsx`, `pages/Orders.jsx` | `orders.view`, `orders.group_view`, `orders.view_all`, `orders.create`, `orders.status`, `orders.approve`, `orders.ship`, `orders.deliver`, `orders.cancel`, `orders.export` |
| **🏭 Almacén & Terminal Splits** | `warehouse.py` | `crud_warehouse*.py` | `warehouse.py` | `adminService.js` | `components/warehouse/WarehouseAdminSection.jsx`, `WarehouseLaserStation.jsx`, `terminal/` | `warehouse.view`, `warehouse.operator`, `warehouse.checker`, `warehouse.send`, `warehouse.supervisor`, `warehouse.audit`, `warehouse.manage` |
| **🏷️ Catálogo, Listas & Descuentos** | `catalog.py`, `price_lists.py`, `discounts.py` | `crud_catalog.py`, `crud_price_list.py`, `crud_discount.py` | `price_list.py`, `discount.py` | `catalogService.js`, `priceListService.js` | `components/products/InventoryManager.jsx`, `DiscountsManager.jsx`, `PriceListManager.jsx` | `catalog.view`, `catalog.customer_view`, `catalog.prices`, `catalog.discounts`, `catalog.export` |
| **💊 Productos & Stock Físico** | `products.py`, `categories.py` | `crud_product.py`, `crud_category.py` | `product.py`, `category.py` | `catalogService.js` | `components/products/ProductCard.jsx`, `ProductCardAdmin.jsx`, `CategoryManagement.jsx` | `products.create`, `products.edit`, `products.cost`, `products.stock`, `products.images`, `products.delete` |
| **🏢 Clientes B2B & Solicitudes** | `customers.py`, `client_request.py` | `crud_customer.py`, `crud_contact_client.py` | `customer.py`, `client_request.py` | `customerService.js` | `components/admin/ClientManagement.jsx`, `ModalAssignUser.jsx`, `pages/BeClient.jsx` | `customers.view`, `customers.view_all`, `customers.create`, `customers.edit`, `customers.assign`, `customers.requests_view` |
| **🤝 Grupos Comerciales** | `commercial_groups.py` | `crud_commercial_group.py` | `sales_group.py` | `salesGroupService.js` | `components/admin/SalesTeamManagement.jsx`, `GroupDetailsModal.jsx` | `groups.view`, `groups.manage` |
| **📢 Anuncios & Marketing** | `announcement.py`, `public_announcement.py` | `crud_announcement.py` | `announcement.py` | `announcementService.js` | `components/admin/AnnouncementsPanel.jsx`, `announcements/StoriesBar.jsx`, `FooterBanner.jsx` | `announcements.view`, `announcements.create`, `announcements.edit`, `announcements.upload`, `announcements.broadcast` |
| **🎫 Tickets & Soporte B2B** | `tickets.py` | `crud_ticket.py` | `ticket.py` | `ticketService.js` | `components/tickets/TicketDashboard.jsx`, `TicketThread.jsx`, `MyTickets.jsx` | `support.view`, `support.create`, `support.reply`, `support.manage`, `support.deescalate` |
| **✉️ Mensajes de Contacto** | `contact.py` | `crud_contact_client.py` | `contact.py` | `contactService.js` | `components/admin/ContactClientPanel.jsx`, `pages/Contact.jsx` | `contact.view`, `contact.manage` |
| **📊 Reportes & Dashboards** | `dashboards.py` | `crud_dashboard.py`, `crud_order_stats.py` | `dashboards.py` | `dashboardService.js` | `components/sales/SalesReport.jsx`, `SummaryCards.jsx`, `pages/UnifiedDashboard.jsx` | `reports.view`, `reports.financial`, `reports.sales`, `reports.export` |
| **⚡ Sync DBF / ERP FoxPro** | `sync_batch.py`, `sync_upload.py` | `crud_sync_batch.py`, `crud_sync_upload.py` | `sync.py` | `syncService.js` | `components/admin/SyncPanel.jsx` | `system.admin`, `system.sync` |

---

## 2. 🏛️ Reglas de Oro Arquitectónicas (Golden Rules for AI Agents)

### Regla 1: Aislamiento Estricto Storefront vs PBAC Interno
- **NUNCA** crees ni utilices permisos PBAC como `cart.manage` o `storefront.favorites`.
- El carrito (`/orders/cart*`), checkout de comprador (`POST /orders/checkout`) y favoritos (`/favorites*`) son **exclusivos de la sesión del cliente (`Customer`)** mediante aislamiento por `customer_id`.
- Los usuarios internos que levantan pedidos en campo utilizan **`POST /orders/create-for-customer`** bajo el permiso `orders.create` y validaciones de grupo comercial asignado (`sales_groups`).

### Regla 2: Full-Stack PBAC / RBAC Dinámico
- El backend evalúa permisos en $O(1)$ mediante el decorator `require_permission("code.name")`.
- En el frontend React, se evalúa mediante el hook universal:
  ```javascript
  const { can, hasRole, isAdmin } = usePermissions();
  if (can(PERMISSIONS.ORDERS_APPROVE)) { ... }
  ```
- Si agregas o modificas un código de permiso, debes actualizar **simultáneamente**:
  1. [`docs/PERMISSIONS_AND_CONSTRAINTS.md`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/docs/PERMISSIONS_AND_CONSTRAINTS.md) (Catálogo Maestro)
  2. [`react/src/config/permissions.js`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/react/src/config/permissions.js) (Catálogo Frontend)
  3. [`database/schema/01_init.sql`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/database/schema/01_init.sql) y [`database/migrations/001_consolidated.sql`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/database/migrations/001_consolidated.sql)
- **Constraint de Rol Activo:** Si el rol asignado a un usuario interno tiene `is_active == False`, el login es rechazado y cualquier token existente es revocado en tiempo real con HTTP 403 Forbidden.

### Regla 3: Aislamiento por Grupo Comercial (Sales Group Scope)
- Vendedores (`seller`) y Marketing (`marketing`) **únicamente** pueden ver pedidos, clientes y estadísticas vinculados a clientes de sus grupos de venta asignados (`sales_group_id in user_groups`).
- Usuarios con alcance global (`admin`, `system.admin` o roles personalizados con permisos transversales `orders.view_all` / `customers.view_all`) tienen visibilidad sobre todos los pedidos y clientes sin restricción de grupo comercial.
- Métricas confidenciales (`order_profit`, `base_price`, márgenes) deben ser filtradas para usuarios no administradores con la función `_strip_admin_fields()`.

### Regla 4: Paginación Lookahead
- Para listados de alto volumen (pedidos, productos, auditoría), usa siempre el helper `get_lookahead_pagination()`.
- Evita queries con `COUNT(*)` sobre millones de filas; el lookahead optimizado evalúa si existe página siguiente de forma eficiente.

### Regla 5: Estilizado SCSS Modular & BEM
- Usar Vanilla CSS / SCSS modular estructurado en:
  - `react/src/styles/atoms/`
  - `react/src/styles/molecules/`
  - `react/src/styles/organisms/`
- Respetar la metodología BEM (`.block__element--modifier`).
- **NO usar clases ad-hoc de TailwindCSS** a menos que sea explícitamente solicitado.
- Preservar variables del design token (`var(--color-primary)`, `var(--space-*)`, `var(--radius-*)`).

---

## 3. 🔄 Checklist de Modificación para Agentes (Agent Workflow Checklist)

Al implementar una nueva característica o refactorización:

1. **[ ] Esquema y Base de Datos:**
   - Si cambia la estructura, actualizar [`backend/profarmed_api/db/base.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/db/base.py) y [`database/migrations/001_consolidated.sql`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/database/migrations/001_consolidated.sql).
   - Crear o modificar esquemas Pydantic en `backend/profarmed_api/schemas/`.
2. **[ ] Lógica Backend:**
   - Modificar las funciones en `backend/profarmed_api/crud/crud_<dominio>.py`.
   - Exponer y securizar endpoints en `backend/profarmed_api/routes/<dominio>.py` con `require_permission`.
3. **[ ] Servicios Frontend:**
   - Actualizar o agregar llamadas Axios en `react/src/services/<dominio>Service.js`.
4. **[ ] Interfaz de Usuario:**
   - Actualizar vistas en `react/src/components/<dominio>/` o `react/src/pages/`.
   - Proteger acciones sensibles con `usePermissions()` o `<RoleGate />`.
5. **[ ] Smoke Test Automatizado:**
   - Ejecutar `npm run build` en `react/` para asegurar 0 errores de compilación o imports rotos.
   - Ejecutar `python scripts/build_obsidian_inventory.py` para mantener sincronizada la base de conocimiento RAG.

---

## 4. 🛠️ Comandos de Terminal Habituales

```powershell
# Levantar entorno Docker completo
docker compose up -d

# Compilar y validar el frontend React
cd react ; npm run build

# Actualizar el inventario de conocimiento Obsidian / RAG
python scripts/build_obsidian_inventory.py

# Crear administradores iniciales del sistema
python backend/create_initial_admins.py
```
