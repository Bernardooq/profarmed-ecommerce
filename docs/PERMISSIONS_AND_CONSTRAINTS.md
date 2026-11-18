# 📋 Catálogo Maestro de Permisos, Restricciones y Políticas (RBAC / PBAC)

> **Documento Vivo de Especificación de Permisos del Sistema**  
> **Proyecto:** FarmaCruz / FSFarma (`profarmed_api` / React)  
> **Estado:** Implementado & Activo en Producción (Full-Stack PBAC / RBAC Dinámico)  

---

## 1. Arquitectura de Permisos y Restricciones (Constraints)

Cada acción en el sistema se desglosa en:
1. **Código de Permiso (`permission_code`)**: El identificador unívoco O(1) evaluado en Backend y Frontend.
2. **Dependencia Jerárquica (`depends_on`)**: Permiso padre requerido (ej. *para crear o editar, forzosamente debes poder ver*).
3. **Restricción Operativa (Constraint)**: Regla de negocio que limita el alcance del permiso según la identidad del usuario, grupo asignado, o estado del recurso (Scope / Ownership).

> [!NOTE]
> ### 🛍️ Distinción Crítica: Endpoints Exclusivos de Clientes (Storefront) vs PBAC Administrativo
> Los endpoints del Storefront de clientes B2B están protegidos por **identidad y sesión directa (`customer_id` via `get_current_user`)**, no por la matriz PBAC de personal interno:
> - **Carrito y Checkout**: `GET/POST/PUT/DELETE /orders/cart`, `POST /orders/cart/import-excel`, `POST /orders/checkout`. El acceso se restringe automáticamente a la canasta activa del cliente autenticado.
> - **Mis Pedidos**: `GET /orders/` consulta exclusivamente el historial de compras del cliente en sesión (a diferencia de `GET /orders/all` que usa PBAC con `orders.view`).
> - **Favoritos**: `GET/POST/PUT/DELETE /favorites/` están aislados por `customer_id`.
> 
> Debido a este aislamiento por sesión, códigos como `cart.manage` o `storefront.favorites` **no forman parte del sistema PBAC**. El personal interno (Admin, Vendedores, Marketing) que genera órdenes a nombre de un cliente utiliza `POST /orders/create-for-customer` bajo el permiso PBAC `orders.create`.

---

## 2. Módulo: Autenticación, Sesión y Payload PBAC (`auth.py`)

Basado en el análisis de [`backend/profarmed_api/routes/auth.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/auth.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `POST /auth/login` | *Público / Autenticación* | **Constraint de Doble Entidad & Estado:**<br>1. Resuelve credenciales primero contra tabla `Customer`; si no existe, contra tabla `User`.<br>2. Valida obligatoriamente `is_active == True` del usuario. Si está inactivo, rechaza con HTTP 400.<br>3. **Constraint de Rol Activo:** Para usuarios internos (`User`), valida que su rol asignado esté activo (`role.is_active == True`). Si el rol está inactivo, rechaza con HTTP 403 Forbidden.<br>4. **Integración PBAC:** El token JWT generado debe incluir `permissions: List[str]` y `role_name: str` resueltos desde el rol asignado en base de datos. | *Ninguna* |
| `POST /auth/register` | `users.create` | Registro de nuevo usuario interno. Requiere privilegios administrativos (`current_admin`). Valida unicidad de `username` y `email`. | `users.view` |
| `POST /auth/login/sync` | `system.admin` | **Constraint de Superadmin & Token Efímero:** Exclusivo para administradores del sistema. Genera un token JWT de corta duración (5 minutos) para pipelines de sincronización. | *Ninguna* |
| `POST /auth/logout` | *Autenticado* | **Constraint de Invalidez Inmediata:** Agrega el identificador unívoco del token (`jti`) a la lista negra en memoria/Redis (`token_blacklist`) con su timestamp `exp` para auto-pruning. | *Ninguna* |
| `GET /auth/me` | *Autenticado* | **Constraint de Identidad:** Retorna los datos del usuario actual y su matriz de capacidades resueltas (`role_name`, `role_id`, y lista de permisos `permissions`) para hidratar el contexto del frontend sin recargar la sesión. | *Ninguna* |

---

## 3. Módulo: Usuarios y Administración Central (`admin.py`)

Basado en el análisis de [`backend/profarmed_api/routes/admin.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/admin.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /users` | `users.view` / `orders.view` / `groups.view` / `customers.assign` | **Consulta Unificada de Usuarios y Filtrado Dinámico por Rol (RBAC / PBAC):**<br>• **Con `users.view` (Admin o supervisores):** Consulta cualquier rol dinámico (`?role={slug}`) o toda la plantilla de usuarios sin restricciones de grupo.<br>• **Sin `users.view` (usuarios operativos con `orders.view`, `groups.view`, `customers.assign`):** Visibilidad estrictamente acotada a los miembros de sus grupos comerciales asignados (`GroupUser`) y a sí mismo (`allowed_user_ids`). El filtrado por `?role={slug}` resuelve dinámicamente cualquier rol en la base de datos sin nombres de rol fijos en el código. | `users.view` (opcional si posee permiso operativo) |
| `GET /admin/users` | `users.view` | Solo lista usuarios internos del sistema (`admin`, `marketing`, `seller`, `warehouse`). Los clientes pertenecen a `customers.view`. | *Ninguna* |
| `POST /admin/users` | `users.create` | No se puede crear un usuario con rol `admin` si quien lo crea no tiene `system.admin`. Valida unicidad de `username`. | `users.view` |
| `GET /admin/users/{id}` | `users.view` | Permite consultar la ficha y datos de perfil de cualquier usuario interno. | *Ninguna* |
| `PUT /admin/users/{id}` | `users.edit` | **Constraint de Inmutabilidad:** Ningún usuario puede degradar o modificar a un superadministrador (`is_system = true`) salvo otro superadministrador. | `users.view` |
| `DELETE /admin/users/{id}` | `users.delete` | **Constraint Crítica:** Jamás se puede eliminar al usuario admin principal del sistema. Si el usuario tiene pedidos o splits asignados, solo soft-delete o bloqueo (`is_active = false`). | `users.view` |
| `PUT /admin/users/{id}/role` | `roles.assign` | **Constraint Operativa:** No se puede promover a `admin` por este endpoint. Solo transiciona entre roles operativos (`seller`, `marketing`, `warehouse`).<br>• Si pasa a `warehouse`: libera membresías de grupos comerciales.<br>• Si pasa a `seller`: auto-crea o asegura su grupo de ventas. | `users.edit` |
| `GET /admin/export-xlsx` | `reports.export` | **Constraint por Tipo:**<br>• `type in ['vendedores', 'marketing', 'almacen']` requiere `users.view`.<br>• `type == 'clientes'` requiere `customers.view`.<br>• `type == 'productos'` requiere `catalog.view`.<br>• `type == 'grupos'` requiere `customers.groups`. | `reports.view` |

---

## 3.1 Módulo: Gestión Dinámica de Roles y Permisos (`roles.py`)

Basado en el análisis de [`backend/profarmed_api/routes/roles.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/roles.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /permissions` | `users.view` / `roles.view` / `system.admin` | **Catálogo Maestro de Permisos (Sólo Lectura):** Retorna el catálogo plano de los 66 permisos canónicos del sistema con sus dependencias y descripciones para alimentar la matriz UI. | `users.view` |
| `GET /roles` | `roles.view` / `users.view` / `system.admin` | **Directorio Dinámico de Roles:** Lista todos los roles existentes en base de datos con conteo de usuarios y conteo de permisos asignados. | `users.view` |
| `GET /roles/{id}` | `roles.view` / `users.view` / `system.admin` | **Detalle de Rol:** Consulta la definición de un rol y su lista completa de códigos de permisos asignados (`permissions: List[str]`). | `roles.view` |
| `POST /roles` | `roles.assign` / `system.admin` | **Creación de Rol Dinámico:** Alta de nuevos roles personalizados. Exige `name` y `slug` unívoco en minúsculas y sin espacios. Solo Admin puede crear roles. | `users.view` |
| `PUT /roles/{id}` | `roles.assign` / `system.admin` | **Actualización y Asignación de Permisos:** Modificación de nombre, descripción, estatus y matriz de permisos. **Protección Crítica:** Solo un usuario con slug `admin` o `system.admin` puede editar los permisos del rol Administrador General. | `roles.assign` |
| `DELETE /roles/{id}` | `roles.assign` / `system.admin` | **Eliminación Segura con Cascada en Permisos:** Elimina el rol y sus asociaciones en `role_permissions` en cascada. **Constraint Inviolable:** Jamás se puede eliminar el rol `admin` (`is_system = true`), ni roles con usuarios actualmente asignados (`users_count > 0`). | `roles.assign` |
| `POST /roles/{id}/permissions` | `roles.assign` / `system.admin` | **Reemplazo Atómico de Matriz de Permisos:** Sustituye íntegramente los permisos asignados a un rol validando que todos los códigos existan en `permissions`. | `roles.assign` |

---

## 4. Módulo: Anuncios, Historias y Promociones (`announcement.py` y `public_announcement.py`)

Basado en el análisis de [`backend/profarmed_api/routes/announcement.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/announcement.py) y [`backend/profarmed_api/routes/public_announcement.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/public_announcement.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /public-announcements/popup` | *Público* | **Popup Promocional Dinámico:** No requiere autenticación. Retorna un modal emergente activo al azar dentro de su vigencia temporal. | *Ninguna* |
| `GET /public-announcements/footer` | *Público* | **Banner Inferior Dinámico:** No requiere autenticación. Retorna un banner de pie de página activo al azar dentro de su vigencia temporal. | *Ninguna* |
| `GET /public-announcements/stories` | *Autenticado* | **Historias B2B Activas:** Requiere cualquier sesión válida (cliente, vendedor, admin). Retorna hasta 100 historias vigentes ordenadas cronológicamente para el carrusel de la tienda. | *Ninguna* |
| `GET /announcements/` | `announcements.view` | Lectura del catálogo de comunicados, historias y pop-ups. Desactiva en background los expirados (`_deactivate_expired_bg`). | *Ninguna* |
| `POST /announcements/` | `announcements.create` | Creación de nuevos anuncios o historias con vigencia temporal (`start_date`, `end_date`). | `announcements.view` |
| `PUT /announcements/{id}` | `announcements.edit` | **Constraint de Limpieza S3:** Si se actualiza el banner (`img`), debe purgar la imagen anterior en AWS S3 para evitar costos de almacenamiento huérfano. | `announcements.view` |
| `DELETE /announcements/{id}` | `announcements.delete` | **Constraint de Purgado Completo:** Borrado en cascada del registro y de su archivo `.webp` asociado en el bucket S3 (`BUCKET_PROMOS`). | `announcements.view` |
| `POST /announcements/upload-image` | `announcements.upload` | **Constraint de Formato y Peso:** Valida tipo MIME imagen, convierte a WEBP de alta calidad, redimensiona si el ancho supera 1920px y sube con clave UUIDv7 a S3. | `announcements.view` |
| `POST /announcements/{id}/send` | `announcements.broadcast` | **Constraint de Difusión Masiva:** Solo envía emails a clientes con `notificate == True`. Limita duplicados y despacha en `BackgroundTasks` vía conexión SMTP persistente. Actualiza `last_send`. | `announcements.view` |
| `GET /promo-ads/active` | *Autenticado* | **Publicidad de Inicio (Inicio B2B):** Retorna secciones vigentes (1 a 4 columnas) con carruseles e imágenes responsivas (`desktop`, `tablet`, `mobile`). | *Ninguna* |
| `GET /promo-ads/` | `promo_ads.view` | Lista todas las secciones y anuncios publicitarios para administración. | *Ninguna* |
| `POST /promo-ads/sections` / `items` | `promo_ads.create` | Crea secciones (`layout_type` 1..4) y anuncios por `slot` validando `1 <= slot <= layout_type`. | `promo_ads.view` |
| `PUT /promo-ads/sections/*` / `items/*` | `promo_ads.edit` | Actualiza orden, vigencia, estado o imágenes; incrementa `img_version` y purga imágenes reemplazadas en S3. | `promo_ads.view` |
| `DELETE /promo-ads/sections/*` / `items/*` | `promo_ads.delete` | Elimina sección (en cascada) o anuncio y purga sus archivos WebP en `BUCKET_PROMOS`. | `promo_ads.view` |
| `POST /promo-ads/upload-image` / `DELETE /promo-ads/image` | `promo_ads.upload` | Convierte a WebP redimensionando según variante (`desktop` 1920px, `tablet` 1280px, `mobile` 900px) y sube/limpia en `BUCKET_PROMOS` bajo `promo-ads/`. | `promo_ads.view` |

---

## 4. Módulo: Carrito, Pedidos y Ciclo de Venta (`orders.py`)

Basado en el análisis de [`backend/profarmed_api/routes/orders.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/orders.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /orders/cart` | *Exclusivo Cliente (Sesión)* | **Constraint de Aislamiento de Carrito:** Consulta del carrito activo exclusivamente para el `customer_id` en sesión. No requiere PBAC administrativo. | *Ninguna* |
| `POST /orders/cart` | *Exclusivo Cliente (Sesión)* | Añadir producto al carrito. Valida existencia de producto y cantidad mínima. | *Ninguna* |
| `POST /orders/cart/import-excel` | *Exclusivo Cliente (Sesión)* | **Carga Masiva B2B:** Importación masiva de pedidos desde hoja Excel (`.xlsx`, `.xls`). Valida códigos de barras y existencias para el cliente en sesión. | *Ninguna* |
| `PUT /orders/cart/{id}` | *Exclusivo Cliente (Sesión)* | Actualización de piezas. Si `quantity <= 0`, purga el item del carrito automáticamente. | *Ninguna* |
| `DELETE /orders/cart/{id}` | *Exclusivo Cliente (Sesión)* | Quitar partida individual del carrito. | *Ninguna* |
| `DELETE /orders/cart` | *Exclusivo Cliente (Sesión)* | Vaciar carrito completo del cliente autenticado. | *Ninguna* |
| `POST /orders/checkout` | *Exclusivo Cliente (Sesión)* | **Conversión Carrito $\rightarrow$ Pedido:** Congela precios personalizados, calcula desglose de impuestos, genera folio único e inicializa estado en `pending_validation`. Costo de envío por defecto $0.0 MXN para clientes. Requiere sesión activa de cliente. | *Ninguna* |
| `POST /orders/create-for-customer` | `orders.create` | **Levantamiento Directo en Campo:** Vendedor/Marketing crea pedido a nombre de un cliente.<br>• **Constraint de Grupo:** Marketing y Seller solo pueden levantar órdenes a clientes de sus grupos comerciales (`sales_group_id in user_groups`).<br>• Permite fijar costo de envío personalizado y notas de asignación logística. | `orders.view` |
| `GET /orders/` | *Exclusivo Cliente (Sesión)* | **Mis Pedidos:** Historial de compras del cliente autenticado con paginación lookahead. Filtra campos de costo (`_strip_admin_fields`). | *Ninguna* |
| `GET /orders/all` | `orders.view` | **Jerarquía PBAC de 3 Niveles en Cobertura de Pedidos (`get_orders_for_user_groups`):**<br>• **1. Bandeja Personal (`orders.view` base):** Si el colaborador solo cuenta con `orders.view` (sin `orders.group_view` ni `orders.view_all`), su visibilidad se acota estrictamente a los pedidos asignados directamente a su usuario asesor (`assigned_user_id == user.user_id`), garantizando privacidad entre vendedores.<br>• **2. Cartera de Sucursal/Equipo (`orders.group_view`):** Si cuenta con este permiso, accede a todos los pedidos de los clientes pertenecientes a sus grupos de venta asignados (`sales_group_id in user_groups`) O asignados a él directamente. Depende de `orders.view`.<br>• **3. Cobertura Global Nacional (`orders.view_all` / `system.admin`):** Consulta global irrestricta de todos los pedidos a nivel nacional sin limitación de grupo ni asesor. Depende de `orders.view`.<br>• **Visibilidad de Utilidades y Márgenes:** Oculta márgenes confidenciales (`order_profit`, `base_price`, precios sin IVA) a usuarios no autorizados (`_strip_admin_fields`). Para ver la utilidad de un pedido se requiere `system.admin` O la suite completa de auditoría financiera: `reports.view`, `reports.financial`, `reports.sales`, `reports.export`, `orders.view` y `orders.view_all`. | *Ninguna* |
| `PUT /orders/{id}/status` | `orders.status` / `orders.approve` / `orders.ship` / `orders.deliver` / `orders.cancel` | **Matriz Dinámica y Estricta de Transiciones de Estatus (RBAC / PBAC):**<br>• **Inmutabilidad Terminal:** Nadie puede modificar pedidos `cancelled` o `delivered`.<br>• **Permiso Maestro (`orders.status`):** Concede **Control Total de Estados**, permitiendo ejecutar cualquier transición válida en la máquina de estados (aprobar, despachar, entregar y cancelar en cualquier fase). Exclusivo de administración o roles de supervisión general (no asignado a vendedores operativos).<br>• **Permisos Granulares Seriados (para roles sin `orders.status`):**<br>  - `orders.approve`: Autorización y validación comercial (`pending_validation` $\rightarrow$ `approved`).<br>  - `orders.ship`: Despacho logístico físico (`approved` $\rightarrow$ `shipped`). Si una orden está en `pending_validation`, no se permite su despacho hasta que sea aprobada previamente (la máquina de estados se respeta estrictamente).<br>  - `orders.deliver`: Confirmación de entrega al cliente (`shipped` $\rightarrow$ `delivered`).<br>  - `orders.cancel`: Cancelación justificada antes de despacho. Solo Admin o supervisores con permiso maestro pueden cancelar pedidos que ya se encuentren en ruta (`shipped`).<br>• **Scope Comercial / Asignación:** Usuarios sin facultad de aprobación/supervisión (`orders.status` / `orders.approve`) solo pueden avanzar la logística de pedidos asignados a ellos dentro de sus grupos de venta (o a nivel global si cuentan con `orders.view_all`). Despacha notificaciones por correo en background. | `orders.view` |
| `POST /orders/{id}/assign` | `orders.assign` | **Constraint de Asignación Logística/Comercial:**<br>• Solo permite asignar a usuarios con rol operativo (`seller` o `marketing`).<br>• El vendedor asignado debe pertenecer obligatoriamente al mismo grupo de venta del cliente (`seller_groups == customer_group_id`).<br>• No permite reasignar pedidos cancelados o entregados. | `orders.view` |
| `POST /orders/{id}/cancel` | `orders.cancel` | **Constraint de Ventana de Cancelación:**<br>• Cliente: Solo puede cancelar si está en `pending_validation`.<br>• Seller: Bloqueado por regla de negocio.<br>• Marketing: Puede cancelar antes de `shipped`.<br>• Admin: Puede cancelar hasta antes de `delivered`. | `orders.view` |
| `PUT /orders/{id}/edit` | `orders.edit` | **Edición de Partidas Pre-Fulfillment:** Permite recalcular cantidades, cambiar tipo de comprobante fiscal (`invoice_type`) o notas de entrega. Solo ejecutable si el cliente pertenece a sus grupos (o si cuenta con `orders.view_all`). | `orders.view` |
| `GET /orders/{id}/download-txt` | `orders.export` | **Generador TXT ERP:** Exportación de pedidos para ERP administrativo. Soporta particionado (`items_per_file`) empaquetando múltiples archivos `.txt` en un archivo `.zip`. Valida acceso comercial al cliente (o si cuenta con `orders.view_all`). | `orders.view` |
| *Alcance Grupal Pedidos* | `orders.group_view` | **Visibilidad por Grupos Comerciales:** Concede acceso a los pedidos de clientes pertenecientes a sus grupos de venta asignados (cartera de equipo o sucursal). Permite a líderes o integrantes de grupo supervisar pedidos compartidos. | `orders.view` |
| *Transversal Pedidos* | `orders.view_all` | **Visibilidad Global Nacional:** Otorga alcance irrestricto transversal sobre pedidos de todos los grupos comerciales a nivel global para consultas, monitoreo y gestión (respetando facultades operativas asignadas). | `orders.view` |

---

## 5. Módulo: Almacén, Surtido y Auditoría Forense (`warehouse.py`)

Basado en el análisis de [`backend/profarmed_api/routes/warehouse.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/warehouse.py) y el nuevo modelo modular de alto rendimiento (Splits concurrentes, Canastas QR reutilizables `warehouse_containers`, Partidas granulares `warehouse_items` y Bitácora de eventos `warehouse_scan_events`):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `POST /warehouse/orders/{id}/send-to-warehouse` | `warehouse.send` / `warehouse.supervisor` / `warehouse.manage` | **Envío a Surtido:** Transiciona el pedido aprobado formalmente a bodega, fragmentándolo en `total_splits` concurrentes y configurando `show_details` (surtido ciego vs detallado). Exige contar con `warehouse.send`, facultades de supervisión/jefatura (`warehouse.supervisor`, `warehouse.manage`) o Administrador Global (`system.admin`). Poseer únicamente `orders.approve` no confiere acceso. | `warehouse.view` |
| `PATCH /warehouse/orders/{id}/visibility` | `warehouse.supervisor` | **Alternar Surtido Ciego:** Modifica `warehouse_show_details`. En modo ciego, los almacenistas no pueden ver la lista de productos hasta que los escanean físicamente. | `warehouse.supervisor` |
| `POST /warehouse/orders/{id}/cancel-warehouse` | `warehouse.supervisor` | **Cancelación de Asignación:** Revoca la orden de bodega y cancela los splits activos si aún no han sido completados. | `warehouse.supervisor` |
| `GET /warehouse/queue` | `warehouse.view` | **Cola FIFO Operativa:** Listado de órdenes en bodega con paginación lookahead, filtros por estado (`warehouse_status`), asignados a mí (`assigned_to_me`), etapa y dictamen forense. | *Ninguna* |
| `GET /warehouse/orders/history` | `warehouse.view` | Consulta del histórico de pedidos procesados y despachados en bodega. | `warehouse.view` |
| `GET /warehouse/stats` | `warehouse.view` | **KPIs Operativos en Tiempo Real:** Métricas de velocidad de recolección, piezas por hora, splits pendientes, discrepancias activas y disponibilidad de canastas QR. | `warehouse.view` |
| `GET /warehouse/splits/by-code/{code}` | `warehouse.operator` / `warehouse.checker` | Consulta de split por código legible de barras (ej. `105-1`) para terminales y pistolas láser de 1er o 2do filtro. | `warehouse.view` |
| `GET /warehouse/splits/{id}` | `warehouse.operator` / `warehouse.checker` | Consulta detallada de partidas asignadas a un split específico, canastas QR asociadas y progreso de conteo. | `warehouse.view` |
| `POST /warehouse/splits/{id}/claim` (Picker) | `warehouse.operator` | **Autoasignación 1er Filtro (Surtidor/Picker):** Reclamo de lote de surtido en piso. Candado de concurrencia. | `warehouse.view` |
| `POST /warehouse/splits/{id}/claim` (Checker) | `warehouse.checker` | **Autoasignación 2do Filtro (Revisión/Control de Calidad):** Reclamo de lote en mesa de revisión y control de calidad. Candado de concurrencia. **Regla PBAC Dinámica:** Un mismo usuario puede actuar como surtidor y revisor (`picker_id == checker_id`) siempre que cuente con los permisos requeridos (`warehouse.checker` junto con `warehouse.operator`, o facultades de supervisión/jefatura `warehouse.supervisor`, `warehouse.manage` o `system.admin`). La fase operativa solicitada se evalúa por capacidades en $O(1)$, con independencia del nombre o slug del rol asignado en la base de datos. | `warehouse.view` |
| `GET /warehouse/operators` | `warehouse.supervisor` | Directorio de personal de bodega activo para asignaciones de supervisión (filtrable por `role_type`: picker o checker). | `warehouse.view` |
| `POST /warehouse/splits/{id}/reassign` | `warehouse.supervisor` | **Reasignación Forzada de Supervisor:** Transfiere un split a otro operador/revisor calificado si el turno terminó o el operador está bloqueado. | `warehouse.view` |
| `POST /warehouse/splits/{id}/scan-barcode` | `warehouse.operator` / `warehouse.checker` | **Escaneo Láser en Piso:** Registra una pieza física verificando contra el código de barras (`codebar`) del producto. Actualiza de forma atómica `warehouse_items` y asocia a la canasta activa. | `warehouse.operator` / `warehouse.checker` |
| `POST /warehouse/splits/{id}/add-boxes` | `warehouse.operator` / `warehouse.checker` | **Empaque por Cajas Maestras:** Multiplica cajas completas (`boxes * units_per_box`) con unidades dinámicas ingresadas por el almacenista. | `warehouse.operator` / `warehouse.checker` |
| `POST /warehouse/splits/{id}/add-manual` | `warehouse.operator` / `warehouse.checker` | **Validación Manual con Justificación:** Permite agregar piezas sin código de barras legible; exige obligatoriamente motivo pericial (`reason`) para auditoría. | `warehouse.operator` / `warehouse.checker` |
| `POST /warehouse/splits/{id}/advance-status` | `warehouse.filter2_send` / `warehouse.seal_direct` / `warehouse.checker` / `warehouse.manage` | **Cierre y Sellado Inviolable / Bifurcación de Piso:**<br>• **Enviar a 2do Filtro (`ready_for_check`):** Requiere `warehouse.filter2_send` o facultades de supervisión/jefatura (`warehouse.supervisor`, `warehouse.manage`, `system.admin`). Valida que el 1er filtro cubra el 100%.<br>• **Sellar y Finalizar Directo en Piso (`completed` desde picking):** Requiere `warehouse.seal_direct` o facultades de supervisión/jefatura (`warehouse.supervisor`, `warehouse.manage`, `system.admin`). Exige folio inviolable.<br>• **Sellar desde 2do Filtro (`completed` desde checking):** Requiere `warehouse.checker` o `warehouse.manage` / `system.admin`. | `warehouse.view` |
| `POST /warehouse/splits/{id}/set-container-mode` | `warehouse.mode_direct` / `warehouse.mode_containers` | **Alternar Modalidad Operativa (Canastas QR vs Surtido Directo):**<br>• **Activar Canastas QR (`uses_containers = true`):** Requiere `warehouse.mode_containers` o facultades de supervisión/jefatura (`warehouse.supervisor`, `warehouse.manage`, `system.admin`).<br>• **Activar Surtido Directo (`uses_containers = false`):** Requiere `warehouse.mode_direct` o facultades de supervisión/jefatura (`warehouse.supervisor`, `warehouse.manage`, `system.admin`). | `warehouse.view` |
| `POST /warehouse/splits/{id}/checker-fast-track` | `warehouse.supervisor` | **Aprobación Rápida de 2do Filtro:** Permite a un supervisor aprobar el split confiando en el surtido previo si está libre de alertas. | `warehouse.supervisor` |
| `GET /warehouse/orders/{id}/audit-breakdown` | `warehouse.audit` / `warehouse.manage` | **Constraint de Dictamen Pericial Forense (Sin acceso para Supervisor):**<br>• Exclusivo de Auditoría de Calidad, Jefatura y Administrador Global.<br>• El Supervisor de Bodega (`warehouse.supervisor`) **NO** tiene acceso a peritajes de discrepancias entre surtidor y revisor para garantizar imparcialidad.<br>• Genera análisis comparativo pieza por pieza entre Surtidor y Revisor calculando `has_forensic_discrepancy`, `discrepancy_note` y `audit_verdict`. | `warehouse.view` |
| `PATCH /warehouse/order-items/{id}/manual-reason` | `warehouse.audit` / `warehouse.manage` | Permite actualizar o corregir la justificación pericial de una partida verificada manualmente. | `warehouse.audit` |
| `PATCH /warehouse/splits/{id}/admin-override` | `warehouse.manage` / `system.admin` | **Constraint de Anulación Administrativa:** Exclusivo de Jefatura y Admin. Permite forzar o resetear el estado de un split y limpiar o reasignar sellos de seguridad violados. | `warehouse.manage` |
| `PATCH /warehouse/order-items/{id}/admin-override-counts` | `warehouse.manage` / `system.admin` | **Corrección Pericial de Conteos:** Exclusivo de Jefatura y Admin. Sobrescribe directamente conteos de 1er filtro (`scanned`, `boxes`, `manual`) y 2do filtro (`checker_*`) con recálculo forense inmediato. | `warehouse.manage` |
| `[PROPOSAL] GET /warehouse/containers` | `warehouse.containers` / `warehouse.view` | **Catálogo de Canastas QR:** Consulta de parque físico de canastas con filtro por estado (`available`, `in_use`, `damaged`, `maintenance`) y splits vinculados. | `warehouse.view` |
| `[PROPOSAL] POST /warehouse/containers` | `warehouse.containers` / `warehouse.manage` | **Alta de Canasta QR:** Enrolamiento de una nueva canasta física garantizando unicidad estricta del código QR (`qr_code`). | `warehouse.containers` |
| `[PROPOSAL] PUT /warehouse/containers/{id}` | `warehouse.containers` / `warehouse.manage` | **Mantenimiento Físico de Canasta:** Permite retirar canastas rotas (`damaged`), poner en mantenimiento o reactivar (`available`). | `warehouse.containers` |
| `[PROPOSAL] POST /warehouse/splits/{id}/bind-container` | `warehouse.operator` / `warehouse.checker` | **Vinculación de Canasta a Split:** Asocia una canasta física mediante escaneo de su QR al split en proceso de surtido/revisión. Valida que la canasta esté `available` o ya asignada a este split. | `warehouse.operator` / `warehouse.checker` |
| `[PROPOSAL] POST /warehouse/containers/{id}/release` | `warehouse.operator` / `warehouse.checker` / `warehouse.supervisor` | **Liberación de Canasta:** Desvincula la canasta del split completado o despachado y la regresa al estado `available` en el área de inicio de surtido. | `warehouse.view` |
| `[PROPOSAL] POST /warehouse/splits/{id}/fast-scan` | `warehouse.operator` / `warehouse.checker` | **Escaneo Láser Atómico de Alto Rendimiento:** Registra evento en `warehouse_scan_events`, incrementa de forma atómica la partida en `warehouse_items` y asocia a la canasta QR activa en $O(1)$. | `warehouse.operator` / `warehouse.checker` |
| `[PROPOSAL] GET /warehouse/splits/{id}/events` | `warehouse.events` / `warehouse.audit` / `warehouse.manage` | **Bitácora Atómica de Split (Event Ledger):** Historial inmutable append-only de todos los escaneos láser, cajas y excepciones manuales ordenados cronológicamente con usuario responsable y timestamp. | `warehouse.view` |
| `[PROPOSAL] GET /warehouse/items/{id}/events` | `warehouse.events` / `warehouse.audit` / `warehouse.manage` | **Trazabilidad Pericial por Partida:** Registro detallado de cada incremento o modificación pericial aplicada a una partida física específica. | `warehouse.view` |

---

## 6. Módulo: Catálogo y Precios Personalizados B2B (`catalog.py`)

Basado en el análisis de [`backend/profarmed_api/routes/catalog.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/catalog.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /catalog/products` | `catalog.view` / `catalog.customer_view` / `orders.create` | **Constraint de Ocultamiento de Costo Base:** Los clientes y vendedores ven el producto con su precio final personalizado (`(base * markup) + iva`). Nunca se expone el `base_price` neto de proveedor en el payload JSON. Accesible para clientes y usuarios internos con `catalog.view`, `catalog.customer_view`, `orders.create` o `system.admin`. | *Ninguna* |
| `GET /catalog/products/{id}` | `catalog.view` / `catalog.customer_view` / `orders.create` | Detalle técnico del producto y cálculo en tiempo real con la lista de precios asignada al comprador. | *Ninguna* |
| `GET /catalog/products/export` | `catalog.export` | **Constraint de Formato por Perfil:**<br>• Si es **Admin**: Requiere `catalog.prices`. Exporta columnas confidenciales: `Precio Base`, `Markup %`, `IVA %`, `IVA $`, `Precio Final`, `Stock`. Permite filtrar por cualquier `price_list_id`.<br>• Si es **Cliente**: Solo exporta sus precios asignados y empaque (`Piezas por caja`), sin costos base. | `catalog.view` |
| `GET /catalog/customer/{id}/products` | `catalog.customer_view` | **Constraint de Pertenencia a Grupo Comercial:**<br>• Si es Admin: Acceso irrestricto a cualquier cliente.<br>• Si es Seller o Marketing: Valida mediante `user_can_manage_order` que el usuario pertenezca al mismo grupo de ventas (`sales_group_id`) del cliente.<br>• Depende jerárquicamente de `orders.create` (Módulo Pedidos y Ventas). | `orders.create` |
| `GET /catalog/customer/{id}/products/{pid}/similar` | `catalog.customer_view` | Sugerencias de productos similares basadas en embeddings/categoría, calculando precios con la `price_list_id` del cliente especificado. Valida `user_can_manage_order`. | `orders.create` |

---

## 7. Módulo: Categorías de Productos (`categories.py`)

Basado en el análisis de [`backend/profarmed_api/routes/categories.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/categories.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /categories/` | *Público / Autenticado* | Lectura de taxonomía y familias de productos para navegación en tienda y filtros. | *Ninguna* |
| `GET /categories/{id}` | *Público / Autenticado* | Detalle de categoría específica y descripción. | *Ninguna* |
| `POST /categories/` | `catalog.categories` | **Constraint de Unicidad de Nombre:** No permite crear categorías duplicadas (`get_category_by_name`). Requiere rol con facultades de catálogo. | `catalog.view` |
| `PUT /categories/{id}` | `catalog.categories` | **Constraint de Conflicto de Nombre:** Valida que el nuevo nombre no colisione con otra categoría existente diferente a la editada. | `catalog.view` |
| `DELETE /categories/{id}` | `catalog.categories` | **Constraint de Integridad Referencial:** Bloquea la eliminación si existen productos vinculados (`count_products_in_category > 0`). Exige reasignar o desasociar productos antes de borrar. | `catalog.view` |

---

## 8. Módulo: Descuentos y Promociones de Productos (`discounts.py`)

Basado en el análisis de [`backend/profarmed_api/routes/discounts.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/discounts.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /discounts/active/{product_id}` | `catalog.view` | **Cálculo en Tiempo Real de Descuento Vigente:** Consulta abierta para cualquier comprador/vendedor autenticado.<br>• **Regla de Prioridad de Negocio:**<br>1. Descuento específico asignado a la lista de precios del cliente (`price_list_id`).<br>2. Descuento general del producto (`price_list_id IS NULL`).<br>3. Sin descuento (precio normal). | *Ninguna* |
| `GET /discounts/` | `catalog.discounts` | **Listado Administrativo de Descuentos:** Consulta con filtros por producto, lista de precios, activo y vigente (`only_current`). | *Ninguna* |
| `GET /discounts/stats` | `catalog.discounts` | **Métricas de Promociones:** Conteo de descuentos activos, productos con descuento y ahorro promedio. | *Ninguna* |
| `GET /discounts/{id}` | `catalog.discounts` | Consulta detallada de una regla de descuento (porcentaje, vigencia de fechas, lista asociada). | *Ninguna* |
| `POST /discounts/` | `catalog.discounts` | **Constraint de Registro:** Alta de descuento asociando obligatoriamente el usuario creador (`created_by_user_id`). | *Ninguna* |
| `PUT /discounts/{id}` | `catalog.discounts` | Actualización de porcentaje, vigencia temporal o activación/desactivación del descuento. | *Ninguna* |
---

## 9. Módulo: Listas de Precios y Markups B2B (`price_lists.py`)

Basado en el análisis de [`backend/profarmed_api/routes/price_lists.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/price_lists.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /price-lists` | `catalog.prices` | **Consulta Maestra de Listas:** Listado de todas las listas de precios activas e inactivas. Exclusivo para administradores y dirección comercial. | *Ninguna* |
| `GET /price-lists/{id}` | `catalog.prices` | Detalle de la lista y todos sus `PriceListItems` asociados (markup por producto). | `catalog.prices` |
| `POST /price-lists` | `catalog.prices` | Creación de una nueva lista de precios para asignación a clientes o grupos. | `catalog.prices` |
| `PUT /price-lists/{id}` | `catalog.prices` | Modificación de metadatos de la lista (nombre, descripción, estatus activo/inactivo). | `catalog.prices` |
| `DELETE /price-lists/{id}` | `catalog.prices` | **Constraint de Integridad Referencial:** Eliminación de lista (`HTTP 204 No Content`). No debe permitirse si hay clientes activos asignados en `CustomerInfo`. | `catalog.prices` |
| `GET /price-lists/{id}/items` | `catalog.prices` | Consulta de partidas de markup por producto dentro de la lista. | `catalog.prices` |
| `POST /price-lists/{id}/items` | `catalog.prices` | Crear o actualizar markup porcentual individual para un producto específico. | `catalog.prices` |
| `POST /price-lists/{id}/items/bulk` | `catalog.prices` | **Actualización Masiva de Márgenes:** Inserción y actualización atómica por lote de múltiples markups (`PriceListItemsBulkUpdate`). | `catalog.prices` |
| `PUT /price-lists/{id}/items/{pid}`| `catalog.prices` | Edición de margen porcentual para un producto individual. | `catalog.prices` |
| `DELETE /price-lists/{id}/items/{pid}`| `catalog.prices` | Quitar regla de markup específico de la lista (el producto vuelve a precio base o lista general). | `catalog.prices` |
| `GET /price-lists/{id}/available-products` | `catalog.prices` | **Filtro de Exclusión UI:** Productos de la base de datos que aún no han sido añadidos a esta lista de precios. | `catalog.prices` |
| `GET /price-lists/{id}/items-with-details` | `catalog.prices` | Consulta enriquecida combinando `PriceListItem` con foto, descripción y stock del `Product`. | `catalog.prices` |

---

## 10. Módulo: Listas de Favoritos y Reorden B2B (`favorites.py`)

Basado en el análisis de [`backend/profarmed_api/routes/favorites.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/favorites.py):

> [!NOTE]
> **Endpoints Exclusivos del Cliente (Storefront B2B — Favoritos):**
> La gestión de listas de favoritos (`/favorites/`) es exclusiva del cliente y está gobernada por identidad de sesión (`customer_id`), no por permisos administrativos PBAC configurables.

| Endpoint / Operación | Código de Permiso / Acceso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /favorites/` | *Exclusivo Cliente (Sesión)* | **Constraint de Aislamiento de Propiedad (Ownership):** Lista únicamente las plantillas y listas de compra creadas por el cliente autenticado (`customer_id`). | *Ninguna* |
| `POST /favorites/` | *Exclusivo Cliente (Sesión)* | Creación de nuevas listas de compra frecuentes o pedidos recurrentes. | *Ninguna* |
| `GET /favorites/{id}` | *Exclusivo Cliente (Sesión)* | Detalle de la lista con productos enriquecidos y precios calculados según la lista de precios del cliente. | *Ninguna* |
| `PUT /favorites/{id}` | *Exclusivo Cliente (Sesión)* | Renombrar lista de favoritos del cliente. Valida propiedad (`customer_id`). | *Ninguna* |
| `DELETE /favorites/{id}` | *Exclusivo Cliente (Sesión)* | Eliminación de lista y sus partidas asociadas. Valida propiedad. | *Ninguna* |
| `POST /favorites/{id}/items` | *Exclusivo Cliente (Sesión)* | Añadir o actualizar cantidades de productos dentro de la lista. | *Ninguna* |
| `DELETE /favorites/{id}/items/{pid}` | *Exclusivo Cliente (Sesión)* | Quitar un producto específico de la lista de favoritos. | *Ninguna* |
| `POST /favorites/{id}/load-to-cart` | *Exclusivo Cliente (Sesión)* | **Carga Masiva al Carrito:** Convierte todos los productos de la lista en items activos del carrito de compras actual en una sola transacción. | *Ninguna* |

---

## 11. Módulo: Cartera de Clientes B2B (`customers.py`)

Basado en el análisis de [`backend/profarmed_api/routes/customers.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/customers.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /customers` | `customers.view` | **Constraint de Alcance (Scope de Cartera & Cobertura Global):**<br>• Si es **Admin o posee `customers.view_all`**: Consulta la cartera global completa de clientes de todos los grupos comerciales.<br>• Si tiene solo **`customers.view`**: El backend filtra automáticamente por pertenencia a sus grupos de venta asignados (`sales_group_id in user_groups`). | *Ninguna* |
| `GET /customers/{id}` | `customers.view` | Consulta detallada del perfil de cliente y su información comercial (`CustomerWithInfo`). Si no es admin ni posee `customers.view_all`, exige pertenecer al grupo comercial del cliente. | *Ninguna* |
| `POST /customers` | `customers.create` | **Constraint de Unicidad B2B:** Valida que el `username` no exista previamente ni en la tabla `customers` ni en la tabla `users` internas para evitar colisiones de login. | `customers.view` |
| `PUT /customers/{id}` | `customers.edit` | Actualización de datos generales del cliente (nombre completo, email, estatus activo/inactivo). Valida unicidad de `username`. | `customers.view` |
| `DELETE /customers/{id}` | `customers.delete` | **Constraint de Integridad Transaccional:** Bloquea terminantemente el borrado si el cliente tiene pedidos históricos (`get_order_count_by_customer > 0`). Exige desactivación lógica (`is_active = False`) para preservar trazabilidad fiscal. | `customers.view` |
| `GET /customers/{id}/info` | `customers.view` | **Constraint de Cartera Comercial:** Marketing y Seller solo pueden ver `CustomerInfo` (razón social, RFC, direcciones, teléfonos) si el cliente pertenece a sus grupos (salvo que cuenten con `customers.view_all` o sean administradores). | `customers.view` |
| `PUT /customers/{id}/info` | `customers.edit` | Creación y actualización de datos comerciales y asignaciones maestras (asignar `sales_group_id`, `price_list_id`, agente comercial responsable). | `customers.view` |
| `PUT /customers/{id}/addresses` | `customers.addresses_edit` | **Constraint de Sucursales Operativas:** Permite modificar exclusivamente direcciones secundarias de entrega (`address_2`, `address_3`). Marketing solo puede editar clientes de sus grupos asignados. | `customers.view` |
| *Transversal Clientes* | `customers.view_all` | **Visibilidad Global:** Otorga alcance irrestricto transversal sobre clientes de todos los grupos comerciales a nivel global para consultas y prospección. | `customers.view` |

---

## 12. Módulo: Prospectos y Solicitudes "Quiero ser Cliente" (`client_request.py`)

Basado en el análisis de [`backend/profarmed_api/routes/client_request.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/client_request.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `POST /client-requests/` | *Público* | **Formulario de Registro Público:** No requiere autenticación ni permisos.<br>• **Constraint de Validación Documental:** Obligatorio 4 archivos PDF (INE, Licencia Sanitaria, Comprobante de Domicilio, Constancia Fiscal).<br>• Máximo 5MB por archivo.<br>• Maneja colisiones de clave S3 con sufijo incremental en bucket `BUCKET_DOCS`. | *Ninguna* |
| `GET /client-requests/admin/all` | `customers.requests_view` | **Auditoría de Prospectos:** Consulta de solicitudes B2B pendientes de aprobación. Permite filtrar por estatus (`pending`, `approved`, `rejected`) y búsqueda por razón social o correo. | `customers.view` |
| `GET /client-requests/admin/{id}/download/{type}` | `customers.requests_download` | **Constraint de URL Prefirmada Temporal:** Genera enlace temporal presignado de AWS S3 con expiración estricta de 300 segundos (5 min) para evitar divulgación permanente de documentos sensibles. | `customers.requests_view` |
| `PATCH /client-requests/admin/{id}/status` | `customers.requests_manage` | **Transición de Estatus:** Cambia el estado del expediente (`pending` $\rightarrow$ `approved` / `rejected`). | `customers.requests_view` |
| `DELETE /client-requests/admin/{id}` | `customers.requests_manage` | **Constraint de Limpieza Documental S3:** Elimina físicamente en lote los 4 archivos PDF en S3 (`delete_objects`) antes de purgar el registro en base de datos. | `customers.requests_view` |

---

## 13. Módulo: Mensajes de Contacto Web (`contact.py`)

Basado en el análisis de [`backend/profarmed_api/routes/contact.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/contact.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `POST /contact/send` | *Público* | **Buzón Público de Contacto:** Sin autenticación ni permisos.<br>• **Constraints de Seguridad:** Longitud máxima de mensaje (5,000 caracteres), validación estricta de email y sanitización.<br>• Manejo de fallback para CAPTCHA Cloudflare Turnstile.<br>• Encolado SMTP en segundo plano vía `BackgroundTasks`. | *Ninguna* |
| `GET /contact/admin/all` | `contact.view` | **Bandeja de Entrada de Mensajes:** Lectura de mensajes de contacto entrantes con filtros por estado (`pending`, `reviewed`, `responded`, `discarded`) y paginación. | *Ninguna* |
| `PATCH /contact/{id}` | `contact.manage` | **Gestión de Seguimiento:** Actualización de estado del mensaje (`status`) y notas de seguimiento interno. | `contact.view` |
| `DELETE /contact/{id}` | `contact.manage` | **Eliminación Definitiva:** Borrado físico del mensaje de contacto en base de datos. | `contact.view` |

---

## 14. Módulo: Métricas, Dashboards y Reportes de Rendimiento (`dashboards.py`)

Basado en el análisis de [`backend/profarmed_api/routes/dashboards.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/dashboards.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /admindash/dashboard/finance` | `reports.financial` | **Métricas Financieras Consolidadas:** Ingresos brutos anuales (`total_revenue`), utilidad neta estimada (`total_profit`) y tendencias del periodo actual. Exclusivo para perfiles financieros, directivos o administración general. Bloqueado para roles con solo `reports.view`. | `reports.view` |
| `GET /admindash/dashboard/orders` | `orders.view` / `orders.view_all` | **Embudo Operativo de Pedidos (Scope Comercial Dinámico):**<br>• **Con `orders.view_all` (o `system.admin`):** Computa el universo total de pedidos de la empresa a nivel nacional (`pending_validation`, `approved`, `shipped`, `delivered`, `cancelled`).<br>• **Con solo `orders.view`:** Acota los conteos estrictamente a las órdenes pertenecientes a los grupos de ventas asignados al colaborador (`sales_group_id in user_groups`). | `orders.view` |
| `GET /admindash/dashboard/users-customers` | `users.view` / `customers.view` / `customers.view_all` | **Personal y Clientes Registrados (Aislamiento RBAC/PBAC):**<br>• **Clientes:** Con `customers.view_all` (o admin) calcula el total nacional; con `customers.view` acota a los clientes de sus grupos de venta asignados.<br>• **Personal:** Con `users.view` desglosa todos los usuarios del sistema por rol (`roles_breakdown`). Sin `users.view`, calcula únicamente a los integrantes de sus grupos comerciales y a sí mismo. | *Ninguna* |
| `GET /admindash/dashboard/inventory` | `catalog.view` | **Salud de Catálogo e Inventario:** Retorna el total de productos activos en catálogo, productos con bajo inventario (< 10 pz) y productos agotados (0 pz). | *Ninguna* |
| `GET /admindash/dashboard` | `reports.view` | **Métricas Consolidadas (Agregador Global):** Endpoint unificado que provee las métricas globales del negocio para administradores corporativos. | *Ninguna* |
| `GET /admindash/dashboard/operational` | `orders.view` | **Métricas Operativas por Grupo:** Resumen de pedidos asignados y conteo de productos para colaboradores de campo vinculados a grupos de venta. | *Ninguna* |
| `GET /admindash/reports/sales` | `reports.sales` / `reports.financial` / `reports.view` | **Informe Financiero Histórico y Gráficas de Tendencia:** Desglose analítico de ventas por rango de fechas (`start_date`, `end_date`) con ingresos, margen de ganancia por markup, IVA y desglose por pedido. | `reports.view` |
| `GET /admindash/dashboard/top-products` | `reports.view` | **Consulta Analítica $O(1)$ de Productos Destacados:** Top de productos por año (`orders`, `units`, `profit`, `revenue`).<br>• **Protección Confidencial de Utilidades:** La columna de ganancia neta (`total_profit`) y el ordenamiento por mayor utilidad requieren obligatoriamente `reports.financial` (o `system.admin`). Si el usuario solo tiene `reports.view`, el sistema enmascara `total_profit = 0.0` y solo muestra volumen de pedidos y unidades vendidas. | `reports.view` |

---

## 15. Módulo: Soporte e Incidencias (`tickets.py`)

Basado en el análisis de [`backend/profarmed_api/routes/tickets.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/tickets.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /tickets/` | `support.view` | **Constraint de Alcance según Entidad y Rol:**<br>• `admin`: Visibilidad completa de todos los tickets en el sistema.<br>• `marketing`: Tickets creados por él, asignados a él, o vinculados a clientes/pedidos pertenecientes a sus grupos de ventas asignados.<br>• `seller`, `warehouse` o `cliente`: Filtrado estricto por pertenencia de autor (`creator_id == current_user.id`). | *Ninguna* |
| `POST /tickets/` | `support.create` | **Constraint de Autorización sobre el Pedido (`order_id`):**<br>• Si se vincula a una orden, se verifica que la orden exista.<br>• `admin`: Puede vincular incidencias a cualquier pedido.<br>• `warehouse`: Requiere haber participado activamente en el pedido (tener al menos un split asignado como `picker_id` o `checker_id`).<br>• `marketing`: El pedido debe pertenecer a un cliente de sus grupos comerciales (`user_can_manage_order`).<br>• `seller`: El pedido debe estar asignado a él o a clientes de su grupo comercial.<br>• `cliente`: El pedido debe pertenecer estrictamente a su cuenta (`customer_id`). | `support.view` |
| `GET /tickets/{id}` | `support.view` | **Constraint de Propiedad y Scope:**<br>• `seller`, `warehouse`, `cliente`: Solo pueden ver el detalle si son los creadores del ticket.<br>• `marketing`: Solo si es propio, está asignado a él, o el ticket/pedido pertenece a un cliente de sus grupos asignados.<br>• `admin`: Acceso irrestricto. | `support.view` |
| `POST /tickets/{id}/messages` | `support.reply` | **Conversación de Soporte:** Permite agregar un mensaje al hilo. Detecta automáticamente tipo de remitente (`user` o `customer`). Valida acceso al ticket. | `support.view` |
| `PUT /tickets/{id}/status` | `support.manage` | **Transición de Estado:** Solo permitido para `admin` y `marketing`. Modifica el estatus del ticket (`open`, `in_progress`, `closed`, `escalated`). | `support.view` |
| `PUT /tickets/{id}/escalate` | `support.manage` | **Escalamiento a Nivel Superior:** Solo permitido para `admin` y `marketing`. Transiciona el ticket directamente a `escalated`. | `support.view` |
| `PUT /tickets/{id}/de-escalate` | `support.deescalate` | **Constraint de Supervisión Ejecutiva:** **Exclusivo para `admin`**. Solo permite desescalar tickets en estado `escalated` devolviéndolos a `in_progress`. | `support.manage` |
| `PUT /tickets/{id}/assign` | `support.manage` | **Toma de Ticket:** Admin o marketing se asignan la titularidad del ticket (`assigned_to = current_user.user_id`). Si el ticket estaba en `open`, avanza automáticamente a `in_progress`. | `support.view` |

---

## 16. Módulo: Catálogo de Productos y Existencias (`products.py`)

Basado en el análisis de [`backend/profarmed_api/routes/products.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/products.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /products/` | `catalog.view` (base), `products.cost` (costos) | **Constraint de Acceso y Ocultamiento Sensible PBAC:**<br>• **Acceso al Catálogo:** Usuarios internos requieren obligatoriamente `catalog.view` (o facultades de almacén `warehouse.view` / `warehouse.operator` / `system.admin`). Si carecen de este permiso, el endpoint rechaza con **`HTTP 403 Forbidden`**.<br>• `location` (ubicación en bodega): Visible solo para personal interno con permisos de catálogo o almacén (`catalog.view`, `warehouse.view`, `warehouse.operator` o `system.admin`). Oculto/vacío para clientes y usuarios sin permiso.<br>• `base_price` (costo base de compra): Visible exclusivamente para usuarios con permiso granular `products.cost` o `system.admin`. Forzado a `None` para cualquier otro usuario o rol.<br>• Paginación eficiente con lookahead (`items` y `lookahead_pages`). | *Ninguna* (requiere `catalog.view` para `products.cost`) |
| `GET /products/{id}` | `catalog.view` (base), `products.cost` (costos) | Consulta individual de producto. Valida `HTTP 403 Forbidden` si el usuario interno no cuenta con `catalog.view` (o almacén). Aplica las mismas restricciones de visibilidad de `location` y `base_price` gobernado por `products.cost`. | *Ninguna* |
| `GET /products/codebar/{codebar}` | `catalog.view` (base), `products.cost` (costos) | Búsqueda directa por código de barras único para lectores y terminales. Valida `HTTP 403 Forbidden` si el usuario interno no cuenta con `catalog.view` (o almacén). Mismas restricciones de visibilidad por rol y permiso `products.cost`. | *Ninguna* |
| `GET /products/{id}/similar` | `catalog.view` | Algoritmo de similitud de Jaccard sobre componentes activos en `descripcion_2`. Si el usuario es cliente, enriquece precios con su `price_list_id`. | *Ninguna* |
| `POST /products/` | `products.create` / `products.manage` | **Constraints de Validación Financiera e Integridad:**<br>• `base_price` > 0 estricto.<br>• `iva_percentage` entre 0 y 100.<br>• `stock_count` >= 0.<br>• Unicidad estricta de `codebar` en base de datos. | `catalog.view` |
| `PUT /products/{id}` | `products.edit` / `products.manage` | Actualización de datos generales, IVA, precios base y metadatos. Valida rangos de precios e IVA. | `catalog.view` |
| `DELETE /products/{id}` | `products.delete` | **Constraints de Integridad Referencial y Limpieza S3:**<br>• Bloquea eliminación (`HTTP 400`) si el producto forma parte de una o más órdenes (`IntegrityError`).<br>• Purga física de la imagen en el bucket `BUCKET_IMGS` de AWS S3 si está alojada en CloudFront.<br>• Soft delete en base de datos. | `products.manage` |
| `PATCH /products/{id}/stock` | `products.stock` | **Constraint de Existencias Físicas:** Ajuste manual de inventario (positivo o negativo). Bloquea si la resta genera stock negativo (`new_stock < 0`). | `catalog.view` |
| `POST /products/upload-image` | `products.images` | **Pipeline de Optimización y Compresión de Imagen:**<br>• Validación MIME `image/*`.<br>• Conversión automática de modos `RGBA/LA/P` a fondo blanco `RGB`.<br>• Compresión iterativa WebP (hasta 6 intentos) para objetivo < 50KB y max 1200px con resampling Lanczos.<br>• Subida directa a S3 con cabecera `CacheControl: max-age=2592000`.<br>• Incremento atómico de `image_version` y purga de caché por querystring `?v=`. | `products.manage` |
| `PATCH /products/{id}/image` | `products.images` | Actualización manual de la URL absoluta de imagen. | `products.images` |
| `PATCH /products/{id}/image-version` | `products.images` | Forzado de refresco de CDN incrementando `image_version` del producto. | `products.images` |

---

## 17. Módulo: Grupos de Ventas y Asignaciones N:M (`sales_groups.py`)

Basado en el análisis de [`backend/profarmed_api/routes/sales_groups.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/sales_groups.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /sales-groups/my-groups` | `groups.view` | **Constraint de Aislamiento de Cartera Comercial:** Retorna únicamente los grupos a los que pertenece el usuario autenticado (`seller` o `marketing`) con sus conteos de miembros. | *Ninguna* |
| `GET /sales-groups/` | `groups.manage` / `users.view` | **Supervisión Global de Estructura de Ventas:** Consulta de todos los grupos del sistema con conteos de miembros (`sellers`, `marketing_managers`, `customers`). Con `users.view` o `system.admin` se permite lectura completa para visibilidad transversal de equipo. | `groups.view` |
| `GET /sales-groups/{id}` | `groups.manage` / `users.view` | Detalle específico de un grupo de ventas por ID con totales y métricas (lectura transversal con `users.view`). | `groups.view` |
| `POST /sales-groups/` | `groups.manage` | Creación de una nueva unidad comercial / grupo de ventas. Exclusivo de gestión. | `groups.manage` |
| `PUT /sales-groups/{id}` | `groups.manage` | Edición del nombre, descripción y estatus del grupo de ventas. Exclusivo de gestión. | `groups.manage` |
| `DELETE /sales-groups/{id}` | `groups.manage` | **Constraint en Cascada:** Eliminación de grupo. Remueve membresías vinculadas. | `groups.manage` |
| `GET /sales-groups/{id}/marketing` | `groups.view` / `users.view` | **Constraint de Membresía:** Admin o usuarios con `users.view` ven todos; usuarios operativos solo pueden listar miembros si pertenecen al grupo (`user_belongs_to_group`). | `groups.view` |
| `GET /sales-groups/{id}/sellers` | `groups.view` / `users.view` | **Constraint de Membresía:** Admin o usuarios con `users.view` ven todos; usuarios operativos solo pueden listar miembros si pertenecen al grupo (`user_belongs_to_group`). | `groups.view` |
| `GET /sales-groups/{id}/agents` | `groups.view` / `users.view` | **Constraint de Membresía:** Lista agentes combinados (`sellers` + `marketing`) del grupo para asignación de pedidos. Valida `user_belongs_to_group` o lectura global con `users.view`. | `groups.view` |
| `GET /sales-groups/{id}/customers` | `groups.view` / `customers.view` / `groups.manage` | **Constraint de Membresía (solo lectura):** Quien posea `groups.manage`, `customers.view_all` o `system.admin` ve cualquier grupo; el resto (ej. `seller` con `groups.view`) únicamente los clientes de grupos a los que pertenece (`user_belongs_to_group`), sin requerir `customers.view` global. | `groups.view` |
| `GET /sales-groups/{id}/members` | `groups.manage` / `users.view` | Lista combinada de marketing managers y vendedores del grupo (lectura con `users.view`). | `groups.view` |
| `GET /sales-groups/{id}/available-marketing` | `groups.manage` | Gestor UI: Usuarios de marketing que aún no forman parte del grupo. | `groups.manage` |
| `GET /sales-groups/{id}/available-sellers` | `groups.manage` | Gestor UI: Vendedores que aún no forman parte del grupo. | `groups.manage` |
| `GET /sales-groups/{id}/available-customers` | `groups.manage` | Gestor UI: Clientes B2B sin grupo asignado o disponibles para vincular. | `groups.manage` |
| `POST /sales-groups/{id}/marketing` | `groups.manage` | Asignación N:M de un gestor de marketing al grupo. | `groups.manage` |
| `DELETE /sales-groups/{id}/marketing/{uid}` | `groups.manage` | Desvinculación de un gestor de marketing del grupo. | `groups.manage` |
| `POST /sales-groups/{id}/sellers` | `groups.manage` | Asignación N:M de un vendedor al grupo. | `groups.manage` |
| `DELETE /sales-groups/{id}/sellers/{uid}` | `groups.manage` | Desvinculación de un vendedor del grupo. | `groups.manage` |
| `POST /sales-groups/{id}/customers/{cid}` | `groups.manage` | **Constraint N:1:** Asigna un cliente al grupo (un cliente pertenece a un único grupo). | `groups.manage` |
| `DELETE /sales-groups/{id}/customers/{cid}` | `groups.manage` | Remueve la asignación de grupo al cliente (vuelve a grupo nulo/general). | `groups.manage` |
| `GET /sales-groups/users/{uid}/groups` | `groups.manage` | Consulta los IDs de todos los grupos asignados a un usuario específico. | `groups.view` |
| `PUT /sales-groups/users/{uid}/groups` | `groups.manage` | **Asignación Masiva Atómica:** Reemplaza transaccionalmente todos los grupos asignados a un usuario (`bulk_assign_user_groups`). | `groups.manage` |

---

---

## 18. Módulo: Sincronización DBF e Ingesta Masiva (`sync_dbf.py` y `sync_dbf_upload.py`)

Basado en el análisis de [`backend/profarmed_api/routes/sync_dbf.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/sync_dbf.py) y [`backend/profarmed_api/routes/sync_dbf_upload.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/sync_dbf_upload.py):

> [!IMPORTANT]
> **Alcance Estricto: Administrador Maestro o Pipeline Automático (`get_current_admin_user` / `system.sync`):**
> Estos endpoints manejan la ingesta masiva y sincronización periódica desde FoxPro/DBF hacia la base de datos PostgreSQL. Debido a su alto impacto operativo e infraestructura (escrituras masivas, bloqueo de tablas, desactivaciones en lote y encolado en `ThreadPoolExecutor`), **dependen de `get_current_admin_user`**, la cual autoriza a:
> 1. Superusuarios o administradores con permiso `system.admin` (o slug de rol `admin`).
> 2. Cuentas o tokens automatizados con el permiso granular `system.sync` (generados mediante `POST /auth/login/sync`).
>
> **Compatibilidad Plena con Esquema PBAC (`database/seeds/01_roles_permissions.sql`):**
> Tras la eliminación física de la columna estática `users.role` y la adopción de `users.role_id` (FK a `roles.role_id` NOT NULL), los pipelines de vendedores resuelven dinámicamente el `role_id` del rol `seller` en la base de datos (`Role.slug == 'seller'`) e insertan/actualizan los registros en `users` sin dependencias de cadenas estáticas ni fallos de constraint.

| Endpoint / Operación | Alcance / Guardia | Restricción / Constraint (Regla de Negocio) | Dependencia |
| :--- | :--- | :--- | :--- |
| `POST /sync/price-lists` | `get_current_admin_user` | Sincronización incremental o creación de cabeceras de listas de precios con validación de timestamps (`updated_at`). | *Admin / Sync* |
| `POST /sync/categories` | `get_current_admin_user` | Creación y actualización en bloque de categorías del catálogo. | *Admin / Sync* |
| `POST /sync/products` | `get_current_admin_user` | **Bulk Upsert de Productos:** Normaliza campos, IVA, stock y precios base en lotes transaccionales optimizados. | *Admin / Sync* |
| `POST /sync/price-list-items` | `get_current_admin_user` | **Bulk Upsert de Markups:** Inserción y actualización atómica de relaciones producto-lista con precios finales calculados. | *Admin / Sync* |
| `POST /sync/customers` | `get_current_admin_user` | Sincronización masiva de clientes, razones sociales, RFC y asignaciones comerciales maestras (`agent_id`, `price_list_id`). Auto-vincula clientes con `agent_id` a los grupos comerciales del vendedor correspondiente. | *Admin / Sync* |
| `POST /sync/sellers` | `get_current_admin_user` | **Bulk Upsert de Agentes de Ventas Internos (Sellers):**<br>• Resuelve dinámicamente `role_id` desde `roles` donde `slug = 'seller'`.<br>• Inserta o actualiza en tabla `users` asignando `role_id`, nombres, emails y hash de contraseñas optimizado.<br>• **Aseguramiento de Grupos:** Ejecuta automáticamente `bulk_ensure_seller_groups` para auto-crear la unidad comercial de cada vendedor importado en `salesgroups` y su membresía en `group_users`. | *Admin / Sync* |
| `POST /sync/cleanup` | `get_current_admin_user` | **Constraint de Seguridad contra Borrado Masivo:** Desactiva entidades no sincronizadas tras una fecha de corte (`last_sync`). Si la cantidad de productos a desactivar supera el umbral de seguridad, aborta la operación salvo que se envíe explícitamente `force=true`. | *Admin / Sync* |
| `POST /sync-upload/productos-json` | `get_current_admin_user` | **Procesamiento Asíncrono en ThreadPool Dedicada:** Descomprime payloads `gzip` al vuelo y encola la ingesta masiva en `ThreadPoolExecutor(max_workers=1)` respondiendo `202 Accepted` de inmediato para no saturar los workers HTTP de Uvicorn. | *Admin / Sync* |
| `POST /sync-upload/listas-precios-json` | `get_current_admin_user` | Encolado asíncrono para ingesta de cabeceras de listas de precios en hilo background. | *Admin / Sync* |
| `POST /sync-upload/items-precios-json` | `get_current_admin_user` | Encolado asíncrono de relaciones de listas de precios e items con alertas por umbrales de tiempo >10s. | *Admin / Sync* |
| `POST /sync-upload/sellers-json` | `get_current_admin_user` | **Encolado Asíncrono de Sellers en Hilo Dedicado:**<br>• Descomprime payload JSON gzipped y procesa en segundo plano.<br>• Resuelve `role_id` para rol dinámico `seller`.<br>• Realiza UPSERT en `users` con contraseñas hasheadas de forma única y garantiza la creación de grupos de ventas comerciales para cada vendedor (`bulk_ensure_seller_groups`). | *Admin / Sync* |
| `POST /sync-upload/customers-json` | `get_current_admin_user` | Encolado asíncrono en hilo dedicado para procesamiento masivo de clientes y vinculación comercial a grupos. | *Admin / Sync* |

---

## 19. Módulo: Perfil Propio y Utilidades de Usuario (`users.py`)

Basado en el análisis de [`backend/profarmed_api/routes/users.py`](file:///c:/Users/berna/Documents/GitProjects/profarmed-ecommerce/backend/profarmed_api/routes/users.py):

| Endpoint / Operación | Código de Permiso | Restricción / Constraint (Regla de Negocio) | Dependencia (`depends_on`) |
| :--- | :--- | :--- | :--- |
| `GET /users/me` | *Autenticado* | **Consulta de Perfil Propio:** Abierto a cualquier usuario autenticado (`Customer` o `User`). Retorna datos del perfil y rol activo. | *Ninguna* |
| `PUT /users/me` | *Autenticado* | **Constraint de Auto-Edición Segura:**<br>• Si es **Cliente**: Solo puede modificar contraseña (`password`) y preferencia de boletines (`notificate`). Cualquier otro campo lanza `HTTP 403 Forbidden`. Requiere enviar al menos un campo.<br>• Si es **User Interno No-Admin** (`seller`, `marketing`, `warehouse`): Solo puede modificar su contraseña (`password`). Intentar cambiar email o username lanza `HTTP 403`.<br>• Si es **Admin**: Puede modificar campos adicionales de su propio perfil. | *Ninguna* |
| `GET /users/me/customer-info` | *Autenticado (Cliente)* | **Exclusividad para Clientes B2B:** Solo accesible por instancias de `Customer` (`HTTP 403` para usuarios internos). Retorna razón social, RFC, direcciones y datos comerciales de su expediente. | *Ninguna* |
| `GET /users` | `users.view` / `orders.view` / `groups.view` / `customers.assign` | **Consulta Unificada de Usuarios y Filtrado Dinámico por Rol (RBAC):**<br>• Si tiene `users.view` (Admin o supervisores con permiso): Consulta cualquier rol dinámico (`?role={slug}`) o toda la plantilla de usuarios sin restricciones.<br>• Si no tiene `users.view` (usuarios operativos con `orders.view`/`groups.view`/`customers.assign`): Su visibilidad se acota estrictamente a los miembros de sus grupos comerciales asignados (y a sí mismo). El filtrado por `?role={slug}` resuelve dinámicamente cualquier rol en la base de datos sin nombres de rol fijos en el código. | *Ninguna* |

---

## 20. Matriz Canónica de Roles Activos en Base de Datos

El sistema opera con **4 roles canónicos base** persistidos en la base de datos (`roles` y `role_permissions`). El rol `warehouse` asume tanto las funciones de 1er filtro (operador de surtido) como de 2do filtro y supervisión/auditoría de almacén.

Cualquier rol adicional (ej. auditores dedicados, supervisores de línea o agentes de soporte) puede crearse y personalizarse dinámicamente desde el módulo **Gestión de Roles y Permisos** en el Panel Administrativo sin requerir despliegues ni cambios de código.

| Código de Permiso | `admin` | `marketing` | `seller` | `warehouse` |
| :--- | :---: | :---: | :---: | :---: |
| `system.admin` | ✅ | ❌ | ❌ | ❌ |
| `system.sync` | ✅ | ❌ | ❌ | ❌ |
| `users.view` | ✅ | ❌ | ❌ | ❌ |
| `users.create` | ✅ | ❌ | ❌ | ❌ |
| `users.edit` | ✅ | ❌ | ❌ | ❌ |
| `users.delete` | ✅ | ❌ | ❌ | ❌ |
| `roles.assign` | ✅ | ❌ | ❌ | ❌ |
| `roles.view` | ✅ | ❌ | ❌ | ❌ |
| `announcements.view` | ✅ | ❌ | ❌ | ❌ |
| `announcements.create` | ✅ | ❌ | ❌ | ❌ |
| `announcements.edit` | ✅ | ❌ | ❌ | ❌ |
| `announcements.delete` | ✅ | ❌ | ❌ | ❌ |
| `announcements.upload` | ✅ | ❌ | ❌ | ❌ |
| `announcements.broadcast` | ✅ | ❌ | ❌ | ❌ |
| `promo_ads.view` | ✅ | ❌ | ❌ | ❌ |
| `promo_ads.create` | ✅ | ❌ | ❌ | ❌ |
| `promo_ads.edit` | ✅ | ❌ | ❌ | ❌ |
| `promo_ads.delete` | ✅ | ❌ | ❌ | ❌ |
| `promo_ads.upload` | ✅ | ❌ | ❌ | ❌ |
| `orders.view` | ✅ | ✅ | ✅ | ❌ |
| `orders.group_view` | ✅ | ✅ | ❌ | ❌ |
| `orders.view_all` | ✅ | ❌ | ❌ | ❌ |
| `orders.create` | ✅ | ✅ | ✅ | ❌ |
| `orders.edit` | ✅ | ❌ | ❌ | ❌ |
| `orders.assign` | ✅ | ❌ | ❌ | ❌ |
| `orders.status` | ✅ | ✅ | ✅ | ❌ |
| `orders.approve` | ✅ | ✅ | ❌ | ❌ |
| `orders.ship` | ✅ | ❌ | ❌ | ❌ |
| `orders.deliver` | ✅ | ❌ | ❌ | ❌ |
| `orders.cancel` | ✅ | ❌ | ❌ | ❌ |
| `orders.export` | ✅ | ❌ | ❌ | ❌ |
| `warehouse.view` | ✅ | ✅ | ❌ | ✅ |
| `warehouse.operator` | ✅ | ❌ | ❌ | ✅ |
| `warehouse.checker` | ✅ | ❌ | ❌ | ✅ |
| `warehouse.send` | ✅ | ✅ | ❌ | ❌ |
| `warehouse.supervisor`| ✅ | ✅ | ❌ | ❌ |
| `warehouse.audit` | ✅ | ✅ | ❌ | ❌ |
| `warehouse.manage` | ✅ | ❌ | ❌ | ❌ |
| `warehouse.containers` [PROPOSAL] | ✅ | ❌ | ❌ | ✅ |
| `warehouse.events` [PROPOSAL] | ✅ | ✅ | ❌ | ✅ |
| `catalog.view` | ✅ | ✅ | ❌ | ❌ |
| `catalog.customer_view` | ✅ | ✅ | ✅ | ❌ |
| `catalog.export` | ✅ | ❌ | ❌ | ❌ |
| `catalog.categories` | ✅ | ❌ | ❌ | ❌ |
| `catalog.prices` | ✅ | ❌ | ❌ | ❌ |
| `catalog.prices_public` | ✅ | ❌ | ✅ | ❌ |
| `catalog.discounts` | ✅ | ❌ | ❌ | ❌ |
| `products.create` | ✅ | ❌ | ❌ | ❌ |
| `products.edit` | ✅ | ❌ | ❌ | ❌ |
| `products.cost` | ✅ | ❌ | ❌ | ❌ |
| `products.manage` | ✅ | ❌ | ❌ | ❌ |
| `products.delete` | ✅ | ❌ | ❌ | ❌ |
| `products.stock` | ✅ | ❌ | ❌ | ❌ |
| `products.images` | ✅ | ❌ | ❌ | ❌ |
| `customers.view` | ✅ | ✅ | ✅ | ❌ |
| `customers.view_all` | ✅ | ❌ | ❌ | ❌ |
| `customers.create` | ✅ | ❌ | ❌ | ❌ |
| `customers.edit` | ✅ | ❌ | ❌ | ❌ |
| `customers.delete` | ✅ | ❌ | ❌ | ❌ |
| `customers.addresses_edit` | ✅ | ❌ | ❌ | ❌ |
| `customers.requests_view` | ✅ | ❌ | ❌ | ❌ |
| `customers.requests_download` | ✅ | ❌ | ❌ | ❌ |
| `customers.requests_manage` | ✅ | ❌ | ❌ | ❌ |
| `customers.assign` | ✅ | ❌ | ❌ | ❌ |
| `groups.view` | ✅ | ✅ | ✅ | ❌ |
| `groups.manage` | ✅ | ❌ | ❌ | ❌ |
| `contact.view` | ✅ | ❌ | ❌ | ❌ |
| `contact.manage` | ✅ | ❌ | ❌ | ❌ |
| `support.view` | ✅ | ✅ | ✅ | ✅ |
| `support.create` | ✅ | ✅ | ✅ | ✅ |
| `support.reply` | ✅ | ✅ | ❌ | ❌ |
| `support.manage` | ✅ | ✅ | ❌ | ❌ |
| `support.deescalate` | ✅ | ❌ | ❌ | ❌ |
| `reports.view` | ✅ | ✅ | ✅ | ❌ |
| `reports.financial` | ✅ | ❌ | ❌ | ❌ |
| `reports.sales` | ✅ | ❌ | ❌ | ❌ |
| `reports.export` | ✅ | ❌ | ❌ | ❌ |
