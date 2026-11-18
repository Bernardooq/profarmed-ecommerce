# Base de Conocimiento y Grafo de Arquitectura (RAG & Fast Navigation)

> **Propósito**: Índice semántico de navegación ultrarrápida para IA y desarrolladores. Permite localizar de inmediato las capas de código (Database -> ORM -> Schema -> CRUD -> Router -> Service -> Component -> View) involucradas en cualquier cambio, sin necesidad de escanear o leer archivos uno por uno.

## 🧭 Matriz de Navegación por Dominio (Full-Stack Vertical Slices)

### 📦 Dominio 1: Carrito, Checkout y Pedidos (Orders & Cart)
*Flujo completo de pedidos desde la adición al carrito temporal (`cartcache`), checkout cliente/interno (`orders`, `orderitems`), cálculo de impuestos/descuentos, edición administrativa y auditoría.*

| Capa Arquitectónica | Archivos Wiki-Link | Responsabilidad Clave |
|---|---|---|
| **🗄️ Database / DDL** | [[database/schema/01_init.sql]]<br>[[database/migrations/001_consolidated.sql]]<br>[[database/schema/legacy_init.sql]] | Esquema base histórico/legacy de producción previo a la introducción de splits, promociones e invoice_type |
| **🧱 ORM Models** | [[backend/profarmed_api/db/base.py]] <br>*(c: TicketStatus, TicketPriority, CreatorType)* | Modelos ORM declarativos de SQLAlchemy (User, Customer, Order, OrderItem, Product, WarehouseSplit, etc.) |
| **📋 Pydantic DTOs** | [[backend/profarmed_api/schemas/order.py]] <br>*(c: OrderUser, OrderItemBase, OrderItemCreate)*<br>[[backend/profarmed_api/schemas/order_direct.py]] <br>*(c: DirectOrderItemCreate, DirectOrderCreate)*<br>[[backend/profarmed_api/schemas/order_edit.py]] <br>*(c: OrderItemEdit, OrderEditRequest)*<br>[[backend/profarmed_api/schemas/cart.py]] <br>*(c: CartItemBase, CartItem)* | Esquemas Pydantic (Request/Response DTOs) para cart |
| **⚙️ CRUD / Lógica BD** | [[backend/profarmed_api/crud/crud_order.py]] <br>*(f: get_order, get_orders_by_customer, get_orders, create_order_from_cart)*<br>[[backend/profarmed_api/crud/crud_order_edit.py]] <br>*(f: edit_order_items)*<br>[[backend/profarmed_api/crud/crud_cart.py]] <br>*(f: get_cart, add_to_cart, update_cart_item, remove_from_cart)*<br>[[backend/profarmed_api/crud/crud_order_stats.py]] <br>*(f: sync_order_on_create, sync_order_on_status_change, sync_order_on_delete, sync_customer_group_change)* | Capa CRUD de acceso a datos y lógica transaccional para order_stats |
| **🌐 API Routes (FastAPI)** | [[backend/profarmed_api/routes/orders.py]] <br>*(f: _user_can_view_order_profit, _strip_admin_fields, read_cart, add_item_to_cart)* | Endpoints REST FastAPI para /orders |
| **🧠 State Context** | [[react/src/context/CartContext.jsx]] <br>*(sym: CartProvider, loadCart, addToCart, updateQuantity)* | Contexto de React y proveedor de estado para CartContext |
| **📡 API Clients** | [[react/src/services/orderService.js]] <br>*(sym: getCart, addToCart, updateCartItem, removeCartItem)*<br>[[react/src/services/cartService.js]] | Cliente API y llamadas HTTP para cartService |
| **🖥️ Views / Pages** | [[react/src/pages/Cart.jsx]] <br>*(sym: Cart, loadCustomerInfo, handleQuantityChange, handleRemove)*<br>[[react/src/pages/Orders.jsx]] <br>*(sym: Orders, loadOrders, handleCancelOrder, handleOpenTicketForOrder)*<br>[[react/src/pages/AllOrders.jsx]] | Vista SPA de página completa para AllOrders |
| **🧩 UI Components** | [[react/src/components/orders/OrderModal.jsx]] <br>*(sym: OrderModal, handleDownloadPDF)*<br>[[react/src/components/modals/orders/ModalCreateOrder.jsx]] <br>*(sym: ModalCreateOrder, handleQuantityChange, doSet, handleRemoveItem)*<br>[[react/src/components/modals/orders/ModalEditOrder.jsx]] <br>*(sym: ModalEditOrder, handleQuantityChange, doSet, handleRemoveItem)*<br>[[react/src/components/modals/orders/ModalOrderDetails.jsx]] <br>*(sym: ModalOrderDetails, getCleanSubline, formatDate, getStatusLabel)*<br>[[react/src/components/orders/OrderHistory.jsx]] <br>*(sym: OrderHistory)*<br>[[react/src/components/cart/CartItemList.jsx]] <br>*(sym: CartItemList)*<br>[[react/src/components/cart/CartSummary.jsx]] <br>*(sym: CartSummary, handleCheckout)* | Componente UI (cart): CartSummary |

### 🏭 Dominio 2: Almacén, Splits y Surtido (Warehouse Fulfillment)
*Módulo de bodegas y surtido: división de órdenes en splits (`warehouse_splits`), verificación de doble filtro (`order_item_split_fulfillment`: Picker & Checker), sellos de seguridad y veredictos forenses (`audit_verdict`).*

| Capa Arquitectónica | Archivos Wiki-Link | Responsabilidad Clave |
|---|---|---|
| **🗄️ Database / DDL** | [[database/schema/01_init.sql]]<br>[[database/migrations/001_consolidated.sql]] | Migración consolidada e idempotente (splits, group_users, product_yearly_stats, order_stock_holds, roles y is_synced) |
| **🧱 ORM Models** | [[backend/profarmed_api/db/base.py]] <br>*(c: TicketStatus, TicketPriority, CreatorType)* | Modelos ORM declarativos de SQLAlchemy (User, Customer, Order, OrderItem, Product, WarehouseSplit, etc.) |
| **📋 Pydantic DTOs** | [[backend/profarmed_api/schemas/warehouse.py]] <br>*(c: WarehouseContainerBase, WarehouseContainerCreate, WarehouseContainerUpdate)* | Esquemas Pydantic (Request/Response DTOs) para warehouse |
| **⚙️ CRUD / Lógica BD** | [[backend/profarmed_api/crud/crud_warehouse.py]]<br>[[backend/profarmed_api/crud/crud_warehouse_orders.py]] <br>*(f: send_order_to_warehouse, toggle_order_warehouse_visibility, cleanup_warehouse_for_order, cancel_order_warehouse)*<br>[[backend/profarmed_api/crud/crud_warehouse_operations.py]]<br>[[backend/profarmed_api/crud/crud_warehouse_audit.py]] <br>*(f: get_order_warehouse_audit, get_warehouse_stats, update_order_item_manual_reason, admin_override_split)*<br>[[backend/profarmed_api/crud/crud_warehouse_status.py]] <br>*(f: advance_split_status, fast_track_approve_second_filter, sync_warehouse_on_order_edit, _recalculate_order_warehouse_status)* | Capa CRUD de acceso a datos y lógica transaccional para warehouse_status |
| **🌐 API Routes (FastAPI)** | [[backend/profarmed_api/routes/warehouse.py]] | Endpoints REST FastAPI para /warehouse |
| **📡 API Clients** | [[react/src/services/warehouseService.js]] <br>*(sym: getQueue, getOrdersHistory, getStats, getSplit)* | Cliente API y llamadas HTTP para warehouseService |
| **🖥️ Views / Pages** | [[react/src/pages/UnifiedDashboard.jsx]] <br>*(sym: UnifiedDashboard, handleTabChange, loadPendingCounts, loadDashboardData)*<br>[[react/src/pages/WarehouseOrders.jsx]] | Vista SPA de página completa para WarehouseOrders |
| **🧩 UI Components** | [[react/src/components/warehouse/ModalReassignSplit.jsx]] <br>*(sym: ModalReassignSplit, handleRoleChange, fetchOperators, handleSubmit)*<br>[[react/src/components/warehouse/ModalScanSplit.jsx]]<br>[[react/src/components/warehouse/ModalWarehouseAudit.jsx]] <br>*(sym: ModalWarehouseAudit, loadAudit, getStatusBadge, handleOpenEditReason)*<br>[[react/src/components/warehouse/SplitDetailModal.jsx]]<br>[[react/src/components/warehouse/WarehouseFIFOQueue.jsx]]<br>[[react/src/components/warehouse/WarehouseStatsCards.jsx]] | Componente UI (warehouse): WarehouseStatsCards |

### 🏷️ Dominio 3: Catálogo, Precios, Descuentos y Recomendaciones
*Gestión de productos (`products`, `location`), categorías, listas de precios con markups (`pricelists`, `pricelistitems`), promociones vigentes (`product_discounts`), estadísticas anuales (`product_yearly_stats`) y productos similares.*

| Capa Arquitectónica | Archivos Wiki-Link | Responsabilidad Clave |
|---|---|---|
| **🗄️ Database / DDL** | [[database/schema/01_init.sql]]<br>[[database/migrations/001_consolidated.sql]] | Migración consolidada e idempotente (splits, group_users, product_yearly_stats, order_stock_holds, roles y is_synced) |
| **🧱 ORM Models** | [[backend/profarmed_api/db/base.py]] <br>*(c: TicketStatus, TicketPriority, CreatorType)* | Modelos ORM declarativos de SQLAlchemy (User, Customer, Order, OrderItem, Product, WarehouseSplit, etc.) |
| **📋 Pydantic DTOs** | [[backend/profarmed_api/schemas/product.py]] <br>*(c: CategoryInProduct, ProductBase, ProductCreate)*<br>[[backend/profarmed_api/schemas/category.py]] <br>*(c: CategoryBase, CategoryCreate, CategoryUpdate)*<br>[[backend/profarmed_api/schemas/price_list.py]] <br>*(c: PriceListBase, PriceListCreate, PriceListUpdate)*<br>[[backend/profarmed_api/schemas/discount.py]] <br>*(c: ProductDiscountBase, ProductDiscountCreate, ProductDiscountUpdate)* | Esquemas Pydantic (Request/Response DTOs) para discount |
| **⚙️ CRUD / Lógica BD** | [[backend/profarmed_api/crud/crud_catalog.py]] <br>*(f: _get_customer_price_list, _query_catalog_by_price_list, get_catalog_products, get_catalog_product)*<br>[[backend/profarmed_api/crud/crud_product.py]] <br>*(f: get_product, get_product_by_codebar, is_catalog_priority_enabled, get_products_query)*<br>[[backend/profarmed_api/crud/crud_category.py]] <br>*(f: get_category, get_category_by_name, get_categories, search_categories)*<br>[[backend/profarmed_api/crud/crud_price_list.py]] <br>*(f: get_price_list, get_price_lists, create_price_list, update_price_list)*<br>[[backend/profarmed_api/crud/crud_discount.py]] <br>*(f: get_active_discount_for_product, get_active_discounts_for_products, get_discount, get_discounts)*<br>[[backend/profarmed_api/crud/crud_product_yearly_stats.py]] <br>*(f: get_order_year, sync_order_products_on_approve, sync_order_products_on_cancel, sync_order_products_on_edit)* | Capa CRUD de acceso a datos y lógica transaccional para product_yearly_stats |
| **🌐 API Routes (FastAPI)** | [[backend/profarmed_api/routes/catalog.py]] <br>*(f: check_catalog_access, get_catalog_products, export_catalog_xlsx, get_catalog_product)*<br>[[backend/profarmed_api/routes/categories.py]] <br>*(f: read_categories, read_category, create_new_category, update_existing_category)*<br>[[backend/profarmed_api/routes/products.py]] <br>*(f: read_products, read_product, read_product_by_codebar, create_new_product)*<br>[[backend/profarmed_api/routes/price_lists.py]] <br>*(f: get_price_lists, get_price_list, create_price_list, update_price_list)*<br>[[backend/profarmed_api/routes/discounts.py]] <br>*(f: check_active_discount_access, create_discount, get_discounts, get_active_product_discount)* | Endpoints REST FastAPI para /discounts |
| **📡 API Clients** | [[react/src/services/catalogService.js]] <br>*(sym: getProducts, getCatalogProducts, getProduct, getCustomerCatalogProducts)*<br>[[react/src/services/priceListService.js]] <br>*(sym: getPriceLists, getPriceList, createPriceList, updatePriceList)*<br>[[react/src/services/discountService.js]] <br>*(sym: getDiscounts, getDiscountStats, getDiscount, getActiveDiscount)* | Cliente API y llamadas HTTP para discountService |
| **🖥️ Views / Pages** | [[react/src/pages/Catalog.jsx]]<br>[[react/src/pages/ProductDetail.jsx]] | Vista SPA de página completa para ProductDetail |
| **🧩 UI Components** | [[react/src/components/products/ProductCard.jsx]] <br>*(sym: ProductCard, extractCaja, handleQuantityChange, handleInputChange)*<br>[[react/src/components/products/ProductGrid.jsx]] <br>*(sym: ProductGrid)*<br>[[react/src/components/products/InventoryManager.jsx]] <br>*(sym: InventoryManager, loadCategories, loadProducts, handleAddProduct)*<br>[[react/src/components/admin/DiscountsManager.jsx]] <br>*(sym: DiscountsManager, loadPriceLists, loadStats, loadDiscounts)*<br>[[react/src/components/admin/PriceListManager.jsx]] <br>*(sym: PriceListManager, loadPriceLists, handleCreate, handleEdit)* | Componente UI (admin): PriceListManager |

### 👥 Dominio 4: Usuarios, Clientes, Vendedores y Grupos de Venta (RBAC / PBAC)
*Estructura comercial y permisos: administración de staff interno (`users`, `roles`, `permissions`, `role_permissions`), clientes con RFC y múltiples direcciones (`customers`, `customerinfo`), y asignación grupal (`salesgroups`, `groupsellers`, `groupmarketingmanagers`).*

| Capa Arquitectónica | Archivos Wiki-Link | Responsabilidad Clave |
|---|---|---|
| **🗄️ Database / DDL** | [[database/schema/01_init.sql]]<br>[[database/seeds/01_roles_permissions.sql]]<br>[[database/schema/legacy_init.sql]] | Esquema base histórico/legacy de producción previo a la introducción de splits, promociones e invoice_type |
| **🧱 ORM Models** | [[backend/profarmed_api/db/base.py]] <br>*(c: TicketStatus, TicketPriority, CreatorType)* | Modelos ORM declarativos de SQLAlchemy (User, Customer, Order, OrderItem, Product, WarehouseSplit, etc.) |
| **📋 Pydantic DTOs** | [[backend/profarmed_api/schemas/user.py]] <br>*(c: UserBase, UserCreate, UserUpdate)*<br>[[backend/profarmed_api/schemas/role.py]] <br>*(c: PermissionBase, PermissionResponse, RoleBase)*<br>[[backend/profarmed_api/schemas/customer.py]] <br>*(c: CustomerBase, CustomerCreate, CustomerUpdate)*<br>[[backend/profarmed_api/schemas/sales_group.py]] <br>*(c: SalesGroupBase, SalesGroupCreate, SalesGroupUpdate)*<br>[[backend/profarmed_api/schemas/auth.py]] | Esquemas Pydantic (Request/Response DTOs) para auth |
| **⚙️ CRUD / Lógica BD** | [[backend/profarmed_api/crud/crud_user.py]] <br>*(f: get_user, get_user_by_username, get_user_by_email, get_users)*<br>[[backend/profarmed_api/crud/crud_role.py]] <br>*(f: get_permissions, get_roles, get_role_by_id, get_role_by_slug)*<br>[[backend/profarmed_api/crud/crud_customer.py]] <br>*(f: get_customer, get_customer_by_username, get_customer_by_email, get_customers)*<br>[[backend/profarmed_api/crud/crud_commercial_group.py]] <br>*(f: create_sales_group, get_sales_group, get_sales_groups, update_sales_group)* | Capa CRUD de acceso a datos y lógica transaccional para commercial_group |
| **🌐 API Routes (FastAPI)** | [[backend/profarmed_api/routes/auth.py]] <br>*(f: register, login, login_sync, logout)*<br>[[backend/profarmed_api/routes/admin.py]] <br>*(f: read_all_users, create_new_user, read_user_by_id, update_user_info)*<br>[[backend/profarmed_api/routes/users.py]] <br>*(f: read_current_user_profile, update_current_user_profile, read_current_user_customer_info, get_users_list)*<br>[[backend/profarmed_api/routes/roles.py]] <br>*(f: read_all_permissions, read_all_roles, read_role_detail, create_new_role)*<br>[[backend/profarmed_api/routes/commercial_groups.py]] <br>*(f: get_groups_for_user, bulk_assign_user_groups, read_sales_groups, read_my_sales_groups)*<br>[[backend/profarmed_api/routes/customers.py]] <br>*(f: get_customers, get_customer, create_customer, update_customer)*<br>[[backend/profarmed_api/routes/dashboards.py]] <br>*(f: get_dashboard_finance_stats_route, get_dashboard_order_stats_route, get_dashboard_users_customers_stats_route, get_dashboard_inventory_stats_route)* | Endpoints REST FastAPI para /dashboards |
| **🧠 State Context** | [[react/src/context/AuthContext.jsx]] <br>*(sym: AuthProvider, checkAuth, login, logout)*<br>[[react/src/hooks/usePermissions.js]] <br>*(sym: usePermissions, hasRole, getDashboardPath, can)*<br>[[react/src/config/permissions.js]] | Recurso frontend (permissions.js) |
| **📡 API Clients** | [[react/src/services/authService.js]] <br>*(sym: login, register, getCurrentUser, logout)*<br>[[react/src/services/adminService.js]] <br>*(sym: getTopProducts, getDashboardStats, getDashboardFinanceStats, getDashboardOrderStats)*<br>[[react/src/services/userService.js]] <br>*(sym: getCurrentUser, updateCurrentUser, getCurrentUserCustomerInfo, getUserCustomerInfo)*<br>[[react/src/services/salesGroupService.js]] <br>*(sym: getSalesGroups, getSalesGroup, createSalesGroup, updateSalesGroup)*<br>[[react/src/services/customerService.js]] <br>*(sym: getCustomers, getCustomer, createCustomer, updateCustomer)*<br>[[react/src/services/dashboardService.js]] <br>*(sym: getOperationalStats, getOrderStats, getInventoryStats, getFinanceStats)* | Cliente API y llamadas HTTP para dashboardService |
| **🖥️ Views / Pages** | [[react/src/pages/Login.jsx]] <br>*(sym: Login, getHeading)*<br>[[react/src/pages/UnifiedDashboard.jsx]] <br>*(sym: UnifiedDashboard, handleTabChange, loadPendingCounts, loadDashboardData)* | Vista SPA de página completa para UnifiedDashboard |
| **🧩 UI Components** | [[react/src/components/admin/ClientManagement.jsx]] <br>*(sym: ClientManagement, loadClients, loadPriceLists, loadAssignedUsers)*<br>[[react/src/components/admin/RolesManagement.jsx]] <br>*(sym: RolesManagement, getRoleIcon, loadRoles, openAddRoleModal)*<br>[[react/src/components/admin/RoleFormModal.jsx]] <br>*(sym: RoleFormModal, loadData, handleNameChange, handleSlugChange)*<br>[[react/src/components/admin/SalesTeamManagement.jsx]] <br>*(sym: SalesTeamManagement, isExcludedRole, fetchAvailableRoles, loadData)*<br>[[react/src/components/common/RoleGate.jsx]] <br>*(sym: RoleGate)* | Componente UI (common): RoleGate |

### 🎫 Dominio 5: Soporte (Tickets), Anuncios y Mensajería
*Módulos transversales de interacción: sistema de tickets con hilos de chat y vinculación a órdenes (`tickets`, `ticket_messages`), banners emergentes e historias (`announcements`), solicitudes fiscales (`client_requests`) y contacto (`contact_messages`).*

| Capa Arquitectónica | Archivos Wiki-Link | Responsabilidad Clave |
|---|---|---|
| **🗄️ Database / DDL** | [[database/schema/01_init.sql]] | Script DDL PostgreSQL maestro v2 (esquema completo, índices GIN pg_trgm, FKs en cascada) |
| **🧱 ORM Models** | [[backend/profarmed_api/db/base.py]] <br>*(c: TicketStatus, TicketPriority, CreatorType)* | Modelos ORM declarativos de SQLAlchemy (User, Customer, Order, OrderItem, Product, WarehouseSplit, etc.) |
| **📋 Pydantic DTOs** | [[backend/profarmed_api/schemas/ticket.py]] <br>*(c: TicketMessageBase, TicketMessageCreate, TicketMessageResponse)*<br>[[backend/profarmed_api/schemas/announcement.py]] <br>*(c: AnnouncementBase, AnnouncementCreate, AnnouncementUpdate)* | Esquemas Pydantic (Request/Response DTOs) para announcement |
| **⚙️ CRUD / Lógica BD** | [[backend/profarmed_api/crud/crud_ticket.py]] <br>*(f: create_ticket, attach_names_to_tickets, attach_names_to_ticket_messages, get_ticket)*<br>[[backend/profarmed_api/crud/crud_announcement.py]] <br>*(f: get_announcements, get_announcement_by_id, create_announcement, update_announcement)*<br>[[backend/profarmed_api/crud/crud_contact_client.py]] <br>*(f: create_contact_message, get_contact_message, get_contact_messages, update_contact_status)* | Capa CRUD de acceso a datos y lógica transaccional para contact_client |
| **🌐 API Routes (FastAPI)** | [[backend/profarmed_api/routes/tickets.py]] <br>*(f: get_sender_info, read_tickets, create_new_ticket, read_ticket_detail)*<br>[[backend/profarmed_api/routes/announcement.py]] <br>*(f: _deactivate_expired_bg, api_get_announcements, api_create_announcement, api_update_announcement)*<br>[[backend/profarmed_api/routes/public_announcement.py]] <br>*(f: api_get_random_popup, api_get_random_footer, api_get_active_stories)*<br>[[backend/profarmed_api/routes/contact.py]] <br>*(f: api_get_contact_messages, send_contact_email, api_update_contact_status, api_delete_contact_message)*<br>[[backend/profarmed_api/routes/client_request.py]] <br>*(f: api_get_client_requests, generate_presigned_url, api_create_client_request, download_client_doc)* | Endpoints REST FastAPI para /client_request |
| **📡 API Clients** | [[react/src/services/ticketService.js]] <br>*(sym: getTickets, getTicket, createTicket, addMessage)*<br>[[react/src/services/announcementService.js]] | Cliente API y llamadas HTTP para announcementService |
| **🖥️ Views / Pages** | [[react/src/pages/Support.jsx]] <br>*(sym: Support)* | Vista SPA de página completa para Support |
| **🧩 UI Components** | [[react/src/components/tickets/TicketCreateModal.jsx]]<br>[[react/src/components/tickets/TicketDashboard.jsx]] <br>*(sym: TicketDashboard, loadTickets, handleTicketClick, handleCloseThread)*<br>[[react/src/components/tickets/TicketThread.jsx]] <br>*(sym: TicketThread, loadTicket, handleSendMessage, handleUpdateStatus)*<br>[[react/src/components/announcements/StoriesBar.jsx]] <br>*(sym: StoriesBar, fetchStories)*<br>[[react/src/components/announcements/PopupBanner.jsx]] <br>*(sym: PopupBanner, fetchPopup, handleClose)*<br>[[react/src/components/announcements/FooterBanner.jsx]] <br>*(sym: FooterBanner, fetchFooter)* | Componente UI (announcements): FooterBanner |

### 🔄 Dominio 6: Sincronización ERP (DBF Files & Background Sync)
*Scripts y servicios de sincronización multihilo para importar archivos `.DBF` de catálogo, usuarios y listas de precios desde sistemas contables locales hacia la API.*

| Capa Arquitectónica | Archivos Wiki-Link | Responsabilidad Clave |
|---|---|---|
| **🗄️ Database / DDL** | [[database/schema/01_init.sql]] | Script DDL PostgreSQL maestro v2 (esquema completo, índices GIN pg_trgm, FKs en cascada) |
| **⚙️ CRUD / Lógica BD** | [[backend/profarmed_api/crud/crud_sync_batch.py]] <br>*(f: _build_password_hashes, _resolve_target_role_id, save_or_update_category, check_if_price_list_exists)*<br>[[backend/profarmed_api/crud/crud_sync_upload.py]] <br>*(f: _get_locked_product_ids, _build_password_hashes, _resolve_target_role_id, _build_sync_summary)* | Capa CRUD de acceso a datos y lógica transaccional para sync_upload |
| **🌐 API Routes (FastAPI)** | [[backend/profarmed_api/routes/sync_batch.py]] <br>*(f: _commit_or_500, sync_price_lists, sync_categories, sync_products)*<br>[[backend/profarmed_api/routes/sync_upload.py]] <br>*(f: decompress_request, _run_sync_job, _process_products_thread, _process_price_lists_thread)* | Endpoints REST FastAPI para /sync_upload |
| **🔄 Sync Pipeline** | [[sync_local/src/uploader/sync_all_batch.py]]<br>[[sync_local/src/uploader/sync_all_zip.py]]<br>[[sync_local/src/uploader/sync_products_zip.py]]<br>[[sync_alpha/src/uploader/sync_all_zip.py]] | Módulo (sync_all_zip.py) |

---

## 📚 Índice de Nodos del Proyecto (Directorio Completo)

### Database & Migraciones (8 archivos)

- [[database/diagnostics/sync_check.sql]] — **DB Verification**: Consultas de diagnóstico para validar consistencia de sincronización ERP y marcas temporales
- [[database/migrations/001_consolidated.sql]] — **Migration Pipeline**: Migración consolidada e idempotente (splits, group_users, product_yearly_stats, order_stock_holds, roles y is_synced)
- [[database/migrations/patches/001_backfill_group_users.sql]] — **Migration Patch**: Parche histórico/manual de migración (001_backfill_group_users.sql)
- [[database/migrations/patches/002_recalculate_yearly_stats.sql]] — **Migration Patch**: Parche histórico/manual de migración (002_recalculate_yearly_stats.sql)
- [[database/schema/01_init.sql]] — **DDL Init**: Script DDL PostgreSQL maestro v2 (esquema completo, índices GIN pg_trgm, FKs en cascada)
- [[database/schema/legacy_init.sql]] — **Legacy Reference**: Esquema base histórico/legacy de producción previo a la introducción de splits, promociones e invoice_type
- [[database/seeds/01_roles_permissions.sql]] — **PBAC Seed**: Catálogo maestro de 75 permisos PBAC y matriz inicial de 4 roles (admin, seller, marketing, warehouse)
- [[database/seeds/02_system_configs.sql]] — **Config Seed**: Semilla idempotente de banderas globales operativas en system_configs

### Backend (FastAPI, SQLAlchemy, Pydantic) (110 archivos)

- [[backend/create_initial_admins.py]] — **Backend Utility**: Módulo backend de soporte (create_initial_admins.py) `[create_admin_users, verify_database_connection, main]`
- [[backend/profarmed_api/__init__.py]] — **Backend Utility**: Módulo backend de soporte (__init__.py)
- [[backend/profarmed_api/auto_deliver_old_orders.py]] — **Backend Utility**: Módulo backend de soporte (auto_deliver_old_orders.py) `[auto_deliver_old_orders, main]`
- [[backend/profarmed_api/core/__init__.py]] — **Core System**: Módulo core (__init__.py): configuración, seguridad JWT o blacklist de tokens
- [[backend/profarmed_api/core/config.py]] — **Core System**: Módulo core (config.py): configuración, seguridad JWT o blacklist de tokens `[Settings]`
- [[backend/profarmed_api/core/security.py]] — **Core System**: Módulo core (security.py): configuración, seguridad JWT o blacklist de tokens `[get_password_hash, verify_password, create_access_token, decode_access_token]`
- [[backend/profarmed_api/core/token_blacklist.py]] — **Core System**: Módulo core (token_blacklist.py): configuración, seguridad JWT o blacklist de tokens `[_prune, add, contains, size]`
- [[backend/profarmed_api/crud/__init__.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para __init__
- [[backend/profarmed_api/crud/crud_announcement.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para announcement `[get_announcements, get_announcement_by_id, create_announcement, update_announcement, delete_announcement]`
- [[backend/profarmed_api/crud/crud_cart.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para cart `[get_cart, add_to_cart, update_cart_item, remove_from_cart, clear_cart]`
- [[backend/profarmed_api/crud/crud_catalog.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para catalog `[_get_customer_price_list, _query_catalog_by_price_list, get_catalog_products, get_catalog_product, get_customer_catalog_products]`
- [[backend/profarmed_api/crud/crud_category.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para category `[get_category, get_category_by_name, get_categories, search_categories, create_category]`
- [[backend/profarmed_api/crud/crud_commercial_group.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para commercial_group `[create_sales_group, get_sales_group, get_sales_groups, update_sales_group, delete_sales_group]`
- [[backend/profarmed_api/crud/crud_contact_client.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para contact_client `[create_contact_message, get_contact_message, get_contact_messages, update_contact_status, delete_contact_message]`
- [[backend/profarmed_api/crud/crud_customer.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para customer `[get_customer, get_customer_by_username, get_customer_by_email, get_customers, create_customer]`
- [[backend/profarmed_api/crud/crud_dashboard.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para dashboard `[get_dashboard_finance_stats, get_dashboard_order_stats, get_dashboard_users_customers_stats, get_dashboard_inventory_stats, get_admin_dashboard_stats]`
- [[backend/profarmed_api/crud/crud_discount.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para discount `[get_active_discount_for_product, get_active_discounts_for_products, get_discount, get_discounts, create_discount]`
- [[backend/profarmed_api/crud/crud_favorite.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para favorite `[get_favorite_lists, _enrich_favorite_item, get_favorite_list, get_favorite_list_details, create_favorite_list]`
- [[backend/profarmed_api/crud/crud_order.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para order `[get_order, get_orders_by_customer, get_orders, create_order_from_cart, create_order_direct]`
- [[backend/profarmed_api/crud/crud_order_edit.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para order_edit `[edit_order_items]`
- [[backend/profarmed_api/crud/crud_order_stats.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para order_stats `[sync_order_on_create, sync_order_on_status_change, sync_order_on_delete, sync_customer_group_change, sync_group_delete]`
- [[backend/profarmed_api/crud/crud_password_reset.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para password_reset `[generate_numeric_code, mask_single_email, mask_email_list, build_password_reset_email_html, request_password_reset_code]`
- [[backend/profarmed_api/crud/crud_price_list.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para price_list `[get_price_list, get_price_lists, create_price_list, update_price_list, delete_price_list]`
- [[backend/profarmed_api/crud/crud_product.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para product `[get_product, get_product_by_codebar, is_catalog_priority_enabled, get_products_query, get_products]`
- [[backend/profarmed_api/crud/crud_product_yearly_stats.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para product_yearly_stats `[get_order_year, sync_order_products_on_approve, sync_order_products_on_cancel, sync_order_products_on_edit, recalculate_all_yearly_stats]`
- [[backend/profarmed_api/crud/crud_role.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para role `[get_permissions, get_roles, get_role_by_id, get_role_by_slug, resolve_permission_dependencies]`
- [[backend/profarmed_api/crud/crud_sync_batch.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para sync_batch `[_build_password_hashes, _resolve_target_role_id, save_or_update_category, check_if_price_list_exists, save_or_update_price_list]`
- [[backend/profarmed_api/crud/crud_sync_upload.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para sync_upload `[_get_locked_product_ids, _build_password_hashes, _resolve_target_role_id, _build_sync_summary, process_products_from_json]`
- [[backend/profarmed_api/crud/crud_system_config.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para system_config `[get_system_configs, get_system_config_by_id, update_system_config_active]`
- [[backend/profarmed_api/crud/crud_ticket.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para ticket `[create_ticket, attach_names_to_tickets, attach_names_to_ticket_messages, get_ticket, get_tickets_for_admin]`
- [[backend/profarmed_api/crud/crud_user.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para user `[get_user, get_user_by_username, get_user_by_email, get_users, create_user]`
- [[backend/profarmed_api/crud/crud_warehouse.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse
- [[backend/profarmed_api/crud/crud_warehouse_audit.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse_audit `[get_order_warehouse_audit, get_warehouse_stats, update_order_item_manual_reason, admin_override_split, admin_override_order_item_counts]`
- [[backend/profarmed_api/crud/crud_warehouse_containers.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse_containers `[list_warehouse_containers, get_warehouse_containers_stats, _parse_container_id, get_warehouse_container_by_id, get_warehouse_container_by_qr]`
- [[backend/profarmed_api/crud/crud_warehouse_operations.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse_operations
- [[backend/profarmed_api/crud/crud_warehouse_orders.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse_orders `[send_order_to_warehouse, toggle_order_warehouse_visibility, cleanup_warehouse_for_order, cancel_order_warehouse, _build_warehouse_search_filter]`
- [[backend/profarmed_api/crud/crud_warehouse_scanning.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse_scanning `[scan_barcode_laser, add_boxes_master, add_manual_verification]`
- [[backend/profarmed_api/crud/crud_warehouse_splits.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse_splits `[_get_split_model, get_split_by_id, get_split_by_code, claim_split, set_split_container_mode]`
- [[backend/profarmed_api/crud/crud_warehouse_status.py]] — **CRUD Engine**: Capa CRUD de acceso a datos y lógica transaccional para warehouse_status `[advance_split_status, fast_track_approve_second_filter, sync_warehouse_on_order_edit, _recalculate_order_warehouse_status]`
- [[backend/profarmed_api/db/__init__.py]] — **Backend Utility**: Módulo backend de soporte (__init__.py)
- [[backend/profarmed_api/db/base.py]] — **ORM Models**: Modelos ORM declarativos de SQLAlchemy (User, Customer, Order, OrderItem, Product, WarehouseSplit, etc.) `[TicketStatus, TicketPriority, CreatorType]`
- [[backend/profarmed_api/db/session.py]] — **DB Engine**: Motor de base de datos SQLAlchemy, pool de conexiones y generador get_db()
- [[backend/profarmed_api/dependencies.py]] — **Backend Utility**: Módulo backend de soporte (dependencies.py) `[get_db, get_current_user, get_current_active_user, get_current_admin_user, get_current_internal_user]`
- [[backend/profarmed_api/main.py]] — **Backend Utility**: Módulo backend de soporte (main.py) `[global_exception_handler, health_check, robots_txt, read_root]`
- [[backend/profarmed_api/recalculate_order_stats.py]] — **Backend Utility**: Módulo backend de soporte (recalculate_order_stats.py) `[recalculate]`
- [[backend/profarmed_api/routes/__init__.py]] — **API Router**: Endpoints REST FastAPI para /__init__
- [[backend/profarmed_api/routes/admin.py]] — **API Router**: Endpoints REST FastAPI para /admin `[read_all_users, create_new_user, read_user_by_id, update_user_info, delete_user_account]`
- [[backend/profarmed_api/routes/announcement.py]] — **API Router**: Endpoints REST FastAPI para /announcement `[_deactivate_expired_bg, api_get_announcements, api_create_announcement, api_update_announcement, api_delete_announcement]`
- [[backend/profarmed_api/routes/auth.py]] — **API Router**: Endpoints REST FastAPI para /auth `[register, login, login_sync, logout, read_users_me, Token, TokenData]`
- [[backend/profarmed_api/routes/catalog.py]] — **API Router**: Endpoints REST FastAPI para /catalog `[check_catalog_access, get_catalog_products, export_catalog_xlsx, get_catalog_product, get_customer_catalog_products]`
- [[backend/profarmed_api/routes/categories.py]] — **API Router**: Endpoints REST FastAPI para /categories `[read_categories, read_category, create_new_category, update_existing_category, delete_existing_category]`
- [[backend/profarmed_api/routes/client_request.py]] — **API Router**: Endpoints REST FastAPI para /client_request `[api_get_client_requests, generate_presigned_url, api_create_client_request, download_client_doc, api_delete_client_request]`
- [[backend/profarmed_api/routes/commercial_groups.py]] — **API Router**: Endpoints REST FastAPI para /commercial_groups `[get_groups_for_user, bulk_assign_user_groups, read_sales_groups, read_my_sales_groups, read_sales_group, BulkGroupAssign]`
- [[backend/profarmed_api/routes/contact.py]] — **API Router**: Endpoints REST FastAPI para /contact `[api_get_contact_messages, send_contact_email, api_update_contact_status, api_delete_contact_message, ContactMessage]`
- [[backend/profarmed_api/routes/customers.py]] — **API Router**: Endpoints REST FastAPI para /customers `[get_customers, get_customer, create_customer, update_customer, delete_customer]`
- [[backend/profarmed_api/routes/dashboards.py]] — **API Router**: Endpoints REST FastAPI para /dashboards `[get_dashboard_finance_stats_route, get_dashboard_order_stats_route, get_dashboard_users_customers_stats_route, get_dashboard_inventory_stats_route, get_dashboard_stats]`
- [[backend/profarmed_api/routes/discounts.py]] — **API Router**: Endpoints REST FastAPI para /discounts `[check_active_discount_access, create_discount, get_discounts, get_active_product_discount, get_discount_stats]`
- [[backend/profarmed_api/routes/favorites.py]] — **API Router**: Endpoints REST FastAPI para /favorites `[get_customer_id, list_favorites, create_favorite, get_favorite, update_favorite]`
- [[backend/profarmed_api/routes/orders.py]] — **API Router**: Endpoints REST FastAPI para /orders `[_user_can_view_order_profit, _strip_admin_fields, read_cart, add_item_to_cart, import_excel_to_cart, CartItemAdd, CartItemUpdate, CheckoutRequest]`
- [[backend/profarmed_api/routes/password_reset.py]] — **API Router**: Endpoints REST FastAPI para /password_reset `[send_reset_code, resend_reset_code, verify_code, reset_password]`
- [[backend/profarmed_api/routes/price_lists.py]] — **API Router**: Endpoints REST FastAPI para /price_lists `[get_price_lists, get_price_list, create_price_list, update_price_list, delete_price_list]`
- [[backend/profarmed_api/routes/products.py]] — **API Router**: Endpoints REST FastAPI para /products `[read_products, read_product, read_product_by_codebar, create_new_product, update_existing_product, StockUpdate, ProductLookaheadResponse, ImageUrlUpdate]`
- [[backend/profarmed_api/routes/public_announcement.py]] — **API Router**: Endpoints REST FastAPI para /public_announcement `[api_get_random_popup, api_get_random_footer, api_get_active_stories]`
- [[backend/profarmed_api/routes/roles.py]] — **API Router**: Endpoints REST FastAPI para /roles `[read_all_permissions, read_all_roles, read_role_detail, create_new_role, update_role_info]`
- [[backend/profarmed_api/routes/router.py]] — **API Router**: Endpoints REST FastAPI para /router
- [[backend/profarmed_api/routes/sync_batch.py]] — **API Router**: Endpoints REST FastAPI para /sync_batch `[_commit_or_500, sync_price_lists, sync_categories, sync_products, sync_price_list_items, CleanupSchema, SyncResult]`
- [[backend/profarmed_api/routes/sync_upload.py]] — **API Router**: Endpoints REST FastAPI para /sync_upload `[decompress_request, _run_sync_job, _process_products_thread, _process_price_lists_thread, _process_price_items_thread, SyncResult, OrderSyncStatusUpdate]`
- [[backend/profarmed_api/routes/system_configs.py]] — **API Router**: Endpoints REST FastAPI para /system_configs `[list_configs, update_config_status]`
- [[backend/profarmed_api/routes/tickets.py]] — **API Router**: Endpoints REST FastAPI para /tickets `[get_sender_info, read_tickets, create_new_ticket, read_ticket_detail, add_message, TicketStatusUpdate]`
- [[backend/profarmed_api/routes/users.py]] — **API Router**: Endpoints REST FastAPI para /users `[read_current_user_profile, update_current_user_profile, read_current_user_customer_info, get_users_list]`
- [[backend/profarmed_api/routes/warehouse/__init__.py]] — **API Router**: Endpoints REST FastAPI para /__init__
- [[backend/profarmed_api/routes/warehouse/audit.py]] — **API Router**: Endpoints REST FastAPI para /audit `[get_split_containers_summary_route, get_split_container_items_route, get_split_events_route, get_order_audit_breakdown_route, update_order_item_manual_reason_route]`
- [[backend/profarmed_api/routes/warehouse/containers.py]] — **API Router**: Endpoints REST FastAPI para /containers `[get_containers_stats_route, list_containers_route, get_container_by_id_route, get_container_by_qr_route, create_container_route]`
- [[backend/profarmed_api/routes/warehouse/dispatch.py]] — **API Router**: Endpoints REST FastAPI para /dispatch `[send_order_route, toggle_order_warehouse_visibility_route, cancel_order_warehouse_route]`
- [[backend/profarmed_api/routes/warehouse/operations.py]] — **API Router**: Endpoints REST FastAPI para /operations `[scan_barcode_route, add_boxes_route, add_manual_route]`
- [[backend/profarmed_api/routes/warehouse/queue.py]] — **API Router**: Endpoints REST FastAPI para /queue `[get_warehouse_queue_route, get_warehouse_history_route, get_warehouse_stats_route, get_warehouse_operators_route]`
- [[backend/profarmed_api/routes/warehouse/splits.py]] — **API Router**: Endpoints REST FastAPI para /splits `[get_split_by_code_route, get_split_detail_route, claim_split_route, set_split_container_mode_route, reassign_split_route]`
- [[backend/profarmed_api/schemas/__init__.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para __init__
- [[backend/profarmed_api/schemas/announcement.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para announcement `[AnnouncementBase, AnnouncementCreate, AnnouncementUpdate]`
- [[backend/profarmed_api/schemas/cart.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para cart `[CartItemBase, CartItem]`
- [[backend/profarmed_api/schemas/category.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para category `[CategoryBase, CategoryCreate, CategoryUpdate]`
- [[backend/profarmed_api/schemas/contact_client.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para contact_client `[ContactMessageCreate, ContactMessageUpdateStatus, ContactMessageResponse]`
- [[backend/profarmed_api/schemas/customer.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para customer `[CustomerBase, CustomerCreate, CustomerUpdate]`
- [[backend/profarmed_api/schemas/customer_info.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para customer_info `[CustomerInfoBase, CustomerInfoCreate, CustomerInfoUpdate]`
- [[backend/profarmed_api/schemas/dashboards.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para dashboards `[RoleBreakdownItem, DashboardFinanceStats, DashboardOrderStats]`
- [[backend/profarmed_api/schemas/discount.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para discount `[ProductDiscountBase, ProductDiscountCreate, ProductDiscountUpdate]`
- [[backend/profarmed_api/schemas/favorite.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para favorite `[FavoriteListItemBase, FavoriteListItemCreate, FavoriteListItemUpdate]`
- [[backend/profarmed_api/schemas/order.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para order `[OrderUser, OrderItemBase, OrderItemCreate]`
- [[backend/profarmed_api/schemas/order_direct.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para order_direct `[DirectOrderItemCreate, DirectOrderCreate]`
- [[backend/profarmed_api/schemas/order_edit.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para order_edit `[OrderItemEdit, OrderEditRequest]`
- [[backend/profarmed_api/schemas/price_list.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para price_list `[PriceListBase, PriceListCreate, PriceListUpdate]`
- [[backend/profarmed_api/schemas/product.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para product `[CategoryInProduct, ProductBase, ProductCreate]`
- [[backend/profarmed_api/schemas/role.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para role `[PermissionBase, PermissionResponse, RoleBase]`
- [[backend/profarmed_api/schemas/sales_group.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para sales_group `[SalesGroupBase, SalesGroupCreate, SalesGroupUpdate]`
- [[backend/profarmed_api/schemas/system_config.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para system_config `[SystemConfigBase, SystemConfigUpdate, SystemConfigResponse]`
- [[backend/profarmed_api/schemas/ticket.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para ticket `[TicketMessageBase, TicketMessageCreate, TicketMessageResponse]`
- [[backend/profarmed_api/schemas/user.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para user `[UserBase, UserCreate, UserUpdate]`
- [[backend/profarmed_api/schemas/warehouse.py]] — **Data Contract**: Esquemas Pydantic (Request/Response DTOs) para warehouse `[WarehouseContainerBase, WarehouseContainerCreate, WarehouseContainerUpdate]`
- [[backend/profarmed_api/scripts/generate_test_excel.py]] — **Backend Utility**: Módulo backend de soporte (generate_test_excel.py) `[generate_excel]`
- [[backend/profarmed_api/scripts/restore_products.py]] — **Backend Utility**: Módulo backend de soporte (restore_products.py) `[restore]`
- [[backend/profarmed_api/shuffle_catalog.py]] — **Backend Utility**: Módulo backend de soporte (shuffle_catalog.py) `[main]`
- [[backend/profarmed_api/utils/email_utils.py]] — **Backend Utility**: Módulo backend de soporte (email_utils.py) `[parse_recipient_emails, send_email_background, send_order_shipped_email, send_order_delivered_email, send_announcement_email]`
- [[backend/profarmed_api/utils/pagination.py]] — **Backend Utility**: Módulo backend de soporte (pagination.py) `[get_lookahead_pagination]`
- [[backend/profarmed_api/utils/price_utils.py]] — **Backend Utility**: Módulo backend de soporte (price_utils.py) `[calculate_final_price_with_markup, apply_iva, calculate_product_price_breakdown, get_product_final_price, format_price_info]`
- [[backend/profarmed_api/utils/product_similarity.py]] — **Backend Utility**: Módulo backend de soporte (product_similarity.py) `[normalize_text, extract_active_components, calculate_similarity_score, find_similar_products_indices, bulk_update_recommendations]`
- [[backend/profarmed_api/utils/sales_group_utils.py]] — **Backend Utility**: Módulo backend de soporte (sales_group_utils.py) `[is_auto_create_sales_group_enabled, is_auto_assign_agent_group_enabled, bulk_ensure_user_groups, auto_crear_grupo_usuario, assign_customer_to_agent_group]`
- [[backend/profarmed_api/utils/stock_rules_utils.py]] — **Backend Utility**: Módulo backend de soporte (stock_rules_utils.py) `[is_config_active, get_active_stock_configs, validate_and_process_order_stock_rules, release_order_stock_holds, restore_cancelled_order_stock]`
- [[backend/reset_password.py]] — **Backend Utility**: Módulo backend de soporte (reset_password.py) `[reset_user_password, main]`
- [[backend/tests/test_db_connection.py]] — **Backend Utility**: Módulo backend de soporte (test_db_connection.py) `[test_connection]`
- [[backend/tests/test_dbf_traductor.py]] — **Backend Utility**: Módulo backend de soporte (test_dbf_traductor.py) `[leer_y_traducir_dbf]`

### Frontend (React, Vite, Estilos) (265 archivos)

- [[react/compress-to-webp.js]] — **Frontend Resource**: Recurso frontend (compress-to-webp.js) `[main, prompt]`
- [[react/eslint.config.js]] — **Frontend Resource**: Recurso frontend (eslint.config.js)
- [[react/generate-pwa-icons.js]] — **Frontend Resource**: Recurso frontend (generate-pwa-icons.js) `[generateIcons]`
- [[react/gulpfile.js]] — **Frontend Resource**: Recurso frontend (gulpfile.js) `[styles, watchFiles]`
- [[react/index.html]] — **Frontend Resource**: Recurso frontend (index.html) `[gtag]`
- [[react/public/offline.html]] — **Frontend Resource**: Recurso frontend (offline.html)
- [[react/src/App.css]] — **Frontend Resource**: Recurso frontend (App.css)
- [[react/src/App.jsx]] — **Frontend Resource**: Recurso frontend (App.jsx) `[App]`
- [[react/src/components/admin/AnnouncementsPanel.jsx]] — **UI Component (admin)**: Componente UI (admin): AnnouncementsPanel `[AnnouncementsPanel, loadData, handleSearch, handleDelete, handleSendEmail]`
- [[react/src/components/admin/ClientManagement.jsx]] — **UI Component (admin)**: Componente UI (admin): ClientManagement `[ClientManagement, loadClients, loadPriceLists, loadAssignedUsers, handleSearch]`
- [[react/src/components/admin/ContactClientPanel.jsx]] — **UI Component (admin)**: Componente UI (admin): ContactClientPanel `[ContactClientPanel, loadData, handleSearch, handleUpdateContactStatus, handleUpdateClientRequestStatus]`
- [[react/src/components/admin/DiscountsManager.jsx]] — **UI Component (admin)**: Componente UI (admin): DiscountsManager `[DiscountsManager, loadPriceLists, loadStats, loadDiscounts, openCreateModal]`
- [[react/src/components/admin/PriceListManager.jsx]] — **UI Component (admin)**: Componente UI (admin): PriceListManager `[PriceListManager, loadPriceLists, handleCreate, handleEdit, handleManageItems]`
- [[react/src/components/admin/RoleFormModal.jsx]] — **UI Component (admin)**: Componente UI (admin): RoleFormModal `[RoleFormModal, loadData, handleNameChange, handleSlugChange, togglePermission]`
- [[react/src/components/admin/RolesManagement.jsx]] — **UI Component (admin)**: Componente UI (admin): RolesManagement `[RolesManagement, getRoleIcon, loadRoles, openAddRoleModal, openEditRoleModal]`
- [[react/src/components/admin/SalesTeamManagement.jsx]] — **UI Component (admin)**: Componente UI (admin): SalesTeamManagement `[SalesTeamManagement, isExcludedRole, fetchAvailableRoles, loadData, loadUsersForRole]`
- [[react/src/components/admin/SystemConfigsModal.jsx]] — **UI Component (admin)**: Componente UI (admin): SystemConfigsModal `[SystemConfigsModal, loadConfigs, handleSearchSubmit, handleClearSearch, handleToggle]`
- [[react/src/components/admin/discounts/DiscountFormModal.jsx]] — **UI Component (admin)**: Componente UI (admin): DiscountFormModal `[DiscountFormModal]`
- [[react/src/components/admin/discounts/DiscountsFilterBar.jsx]] — **UI Component (admin)**: Componente UI (admin): DiscountsFilterBar `[DiscountsFilterBar]`
- [[react/src/components/admin/discounts/DiscountsSummaryCards.jsx]] — **UI Component (admin)**: Componente UI (admin): DiscountsSummaryCards `[DiscountsSummaryCards]`
- [[react/src/components/admin/discounts/DiscountsTable.jsx]] — **UI Component (admin)**: Componente UI (admin): DiscountsTable `[DiscountsTable]`
- [[react/src/components/admin/roles/RoleMetaFields.jsx]] — **UI Component (admin)**: Componente UI (admin): RoleMetaFields `[RoleMetaFields]`
- [[react/src/components/admin/roles/RoleModulesNav.jsx]] — **UI Component (admin)**: Componente UI (admin): RoleModulesNav `[RoleModulesNav]`
- [[react/src/components/admin/roles/RolePermissionsTree.jsx]] — **UI Component (admin)**: Componente UI (admin): RolePermissionsTree `[RolePermissionsTree, renderChildBranch]`
- [[react/src/components/admin/roles/roleFormConstants.js]] — **UI Component (admin)**: Componente UI (admin): roleFormConstants
- [[react/src/components/announcements/FooterBanner.jsx]] — **UI Component (announcements)**: Componente UI (announcements): FooterBanner `[FooterBanner, fetchFooter]`
- [[react/src/components/announcements/PopupBanner.jsx]] — **UI Component (announcements)**: Componente UI (announcements): PopupBanner `[PopupBanner, fetchPopup, handleClose]`
- [[react/src/components/announcements/StoriesBar.jsx]] — **UI Component (announcements)**: Componente UI (announcements): StoriesBar `[StoriesBar, fetchStories]`
- [[react/src/components/announcements/StoryViewerModal.jsx]] — **UI Component (announcements)**: Componente UI (announcements): StoryViewerModal `[StoryViewerModal, handleKeyDown, handleCardClick, setProgress]`
- [[react/src/components/cart/CartItem.jsx]] — **UI Component (cart)**: Componente UI (cart): CartItem `[CartItem, handleInputChange, handleInputBlur, handleIncrement, handleDecrement]`
- [[react/src/components/cart/CartItemList.jsx]] — **UI Component (cart)**: Componente UI (cart): CartItemList `[CartItemList]`
- [[react/src/components/cart/CartSummary.jsx]] — **UI Component (cart)**: Componente UI (cart): CartSummary `[CartSummary, handleCheckout]`
- [[react/src/components/common/BaseModal.jsx]] — **UI Component (common)**: Componente UI (common): BaseModal `[BaseModal, handleKeyDown]`
- [[react/src/components/common/ErrorMessage.jsx]] — **UI Component (common)**: Componente UI (common): ErrorMessage `[ErrorMessage]`
- [[react/src/components/common/HelpGuide.jsx]] — **UI Component (common)**: Componente UI (common): HelpGuide `[HelpGuide, toggleGuide]`
- [[react/src/components/common/IOSInstallPrompt.css]] — **UI Component (common)**: Componente UI (common): IOSInstallPrompt
- [[react/src/components/common/IOSInstallPrompt.jsx]] — **UI Component (common)**: Componente UI (common): IOSInstallPrompt `[IOSInstallPrompt]`
- [[react/src/components/common/ItemsPerPageSelector.jsx]] — **UI Component (common)**: Componente UI (common): ItemsPerPageSelector `[ItemsPerPageSelector]`
- [[react/src/components/common/Labs.jsx]] — **UI Component (common)**: Componente UI (common): Labs `[Labs]`
- [[react/src/components/common/LoadingSpinner.jsx]] — **UI Component (common)**: Componente UI (common): LoadingSpinner `[LoadingSpinner]`
- [[react/src/components/common/PaginationButtons.jsx]] — **UI Component (common)**: Componente UI (common): PaginationButtons `[PaginationButtons, handlePageClick]`
- [[react/src/components/common/RoleGate.jsx]] — **UI Component (common)**: Componente UI (common): RoleGate `[RoleGate]`
- [[react/src/components/common/SEO.jsx]] — **UI Component (common)**: Componente UI (common): SEO `[SEO]`
- [[react/src/components/common/ScrollToTop.jsx]] — **UI Component (common)**: Componente UI (common): ScrollToTop `[ScrollToTop]`
- [[react/src/components/hero/Advantages.jsx]] — **UI Component (hero)**: Componente UI (hero): Advantages `[Advantages]`
- [[react/src/components/hero/Featured.jsx]] — **UI Component (hero)**: Componente UI (hero): Featured `[Featured]`
- [[react/src/components/hero/Hero.jsx]] — **UI Component (hero)**: Componente UI (hero): Hero `[Hero]`
- [[react/src/components/hero/IntroText.jsx]] — **UI Component (hero)**: Componente UI (hero): IntroText `[IntroText]`
- [[react/src/components/layout/Footer.jsx]] — **UI Component (layout)**: Componente UI (layout): Footer `[Footer]`
- [[react/src/components/layout/Header.jsx]] — **UI Component (layout)**: Componente UI (layout): Header `[Header, handleLogout]`
- [[react/src/components/layout/Header2.jsx]] — **UI Component (layout)**: Componente UI (layout): Header2 `[Header2, handleLogout, getDashboardLink, getDashboardLabel]`
- [[react/src/components/layout/ProductModal.jsx]] — **UI Component (layout)**: Componente UI (layout): ProductModal `[ProductModal, handleChange, handleSubmit, handleClose]`
- [[react/src/components/layout/SearchBar.jsx]] — **UI Component (layout)**: Componente UI (layout): SearchBar `[SearchBar, handleLogout, handleSearch]`
- [[react/src/components/layout/SidebarDrawer.jsx]] — **UI Component (layout)**: Componente UI (layout): SidebarDrawer `[SidebarDrawer, handleKeyDown, loadCounts, handleLogout, handleNav]`
- [[react/src/components/modals/clients/ModalAssignUser.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalAssignUser `[ModalAssignUser, handleSearch, handleSubmit]`
- [[react/src/components/modals/groups/GroupDetailsModal.jsx]] — **UI Component (modals)**: Componente UI (modals): GroupDetailsModal `[GroupDetailsModal, loadAvailableUsers, loadInGroupUsers, handleAddMember, handleRemoveMember]`
- [[react/src/components/modals/groups/GroupFormModal.jsx]] — **UI Component (modals)**: Componente UI (modals): GroupFormModal `[GroupFormModal, handleChange, handleSubmit]`
- [[react/src/components/modals/orders/CustomerSelector.jsx]] — **UI Component (modals)**: Componente UI (modals): CustomerSelector `[CustomerSelector, loadAssignedGroups, loadAssignedGroupCustomers, loadCustomers, handleCustomerSearch]`
- [[react/src/components/modals/orders/ModalCreateOrder.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalCreateOrder `[ModalCreateOrder, handleQuantityChange, doSet, handleRemoveItem, handleQuantityBlur]`
- [[react/src/components/modals/orders/ModalDownloadTxtOptions.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalDownloadTxtOptions `[ModalDownloadTxtOptions, handleSubmit]`
- [[react/src/components/modals/orders/ModalEditOrder.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalEditOrder `[ModalEditOrder, handleQuantityChange, doSet, handleRemoveItem, handleQuantityBlur]`
- [[react/src/components/modals/orders/ModalOrderDetails.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalOrderDetails `[ModalOrderDetails, getCleanSubline, formatDate, getStatusLabel, getWarehouseStatusLabel]`
- [[react/src/components/modals/orders/OrderItemsTable.jsx]] — **UI Component (modals)**: Componente UI (modals): OrderItemsTable `[OrderItemsTable, calculateTotal]`
- [[react/src/components/modals/orders/ProductSearchGrid.jsx]] — **UI Component (modals)**: Componente UI (modals): ProductSearchGrid `[ProductSearchGrid, loadAvailableProducts, handleProductSearch]`
- [[react/src/components/modals/orders/SimilarProductsModal.jsx]] — **UI Component (modals)**: Componente UI (modals): SimilarProductsModal `[SimilarProductsModal, loadSimilarProducts]`
- [[react/src/components/modals/orders/StockConflictBanner.jsx]] — **UI Component (modals)**: Componente UI (modals): StockConflictBanner `[StockConflictBanner]`
- [[react/src/components/modals/priceLists/ModalPriceListForm.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalPriceListForm `[ModalPriceListForm, handleChange, handleSubmit]`
- [[react/src/components/modals/priceLists/ModalPriceListItems.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalPriceListItems `[ModalPriceListItems, handleAvailableSearch, handleListSearch, loadListItems, loadAvailableProducts]`
- [[react/src/components/modals/products/ModalAddFavorite.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalAddFavorite `[ModalAddFavorite, loadLists, handleAdd]`
- [[react/src/components/modals/products/ModalAddProduct.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalAddProduct `[ModalAddProduct, loadCategories, handleChange, handleUploadImage, handleSubmit]`
- [[react/src/components/modals/products/ModalEditProduct.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalEditProduct `[ModalEditProduct, loadCategories, handleUploadImage, handleChange, handleSubmit]`
- [[react/src/components/modals/products/ModalProductDetails.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalProductDetails `[ModalProductDetails, handleAddToCart, handleQuantityChange, handleInputChange, handleInputBlur]`
- [[react/src/components/modals/products/ModalProductStockHolds.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalProductStockHolds `[ModalProductStockHolds, handleDeleteHold]`
- [[react/src/components/modals/products/ModalUpdateStock.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalUpdateStock `[ModalUpdateStock, handleSubmit]`
- [[react/src/components/modals/products/ModalViewProduct.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalViewProduct `[ModalViewProduct]`
- [[react/src/components/modals/tickets/TicketCreateModal.jsx]] — **UI Component (modals)**: Componente UI (modals): TicketCreateModal `[TicketCreateModal, handleSubmit]`
- [[react/src/components/modals/users/ModalAssignGroups.jsx]] — **UI Component (modals)**: Componente UI (modals): ModalAssignGroups `[ModalAssignGroups, loadInitialData, loadGroupsPage, handleToggleGroup, handleSave]`
- [[react/src/components/orders/AllOrders.jsx]] — **UI Component (orders)**: Componente UI (orders): AllOrders `[AllOrders, OrderRowAllOrders, loadOrders, handleSearch, handleStatusChange]`
- [[react/src/components/orders/OrderHistory.jsx]] — **UI Component (orders)**: Componente UI (orders): OrderHistory `[OrderHistory]`
- [[react/src/components/orders/OrderModal.jsx]] — **UI Component (orders)**: Componente UI (orders): OrderModal `[OrderModal, handleDownloadPDF]`
- [[react/src/components/orders/OrderRow.jsx]] — **UI Component (orders)**: Componente UI (orders): OrderRow `[OrderRow]`
- [[react/src/components/orders/OrderRowAdmin.jsx]] — **UI Component (orders)**: Componente UI (orders): OrderRowAdmin `[OrderRowAdmin, formatDate]`
- [[react/src/components/products/CategoryManagement.jsx]] — **UI Component (products)**: Componente UI (products): CategoryManagement `[CategoryManagement, loadCategories, openAddModal, openEditModal, closeModal]`
- [[react/src/components/products/ColumnPickerModal.jsx]] — **UI Component (products)**: Componente UI (products): ColumnPickerModal `[ColumnPickerModal]`
- [[react/src/components/products/FiltersBar.jsx]] — **UI Component (products)**: Componente UI (products): FiltersBar `[FiltersBar]`
- [[react/src/components/products/InventoryManager.jsx]] — **UI Component (products)**: Componente UI (products): InventoryManager `[InventoryManager, loadCategories, loadProducts, handleAddProduct, handleEditProduct]`
- [[react/src/components/products/PosCatalogView.jsx]] — **UI Component (products)**: Componente UI (products): PosCatalogView `[PosCatalogView, showToast, getQty, setQty, handleBlur]`
- [[react/src/components/products/ProductCard.jsx]] — **UI Component (products)**: Componente UI (products): ProductCard `[ProductCard, extractCaja, handleQuantityChange, handleInputChange, handleInputBlur]`
- [[react/src/components/products/ProductCardAdmin.jsx]] — **UI Component (products)**: Componente UI (products): ProductCardAdmin `[ProductCardAdmin, handleQuantityChange, handleInputChange, handleInputBlur]`
- [[react/src/components/products/ProductGrid.jsx]] — **UI Component (products)**: Componente UI (products): ProductGrid `[ProductGrid]`
- [[react/src/components/products/ProductRow.jsx]] — **UI Component (products)**: Componente UI (products): ProductRow `[ProductRow, getStockClass]`
- [[react/src/components/products/SimilarProducts.jsx]] — **UI Component (products)**: Componente UI (products): SimilarProducts `[SimilarProductActions, SimilarProducts, showMsg, handleChange, handleInput]`
- [[react/src/components/sales/SalesAnalysis.jsx]] — **UI Component (sales)**: Componente UI (sales): SalesAnalysis `[SalesAnalysis, handleFilter]`
- [[react/src/components/sales/SalesReport.jsx]] — **UI Component (sales)**: Componente UI (sales): SalesReport `[SalesReport, getInitialDates, getChartColors, get, handleGenerateReport]`
- [[react/src/components/sales/SummaryCards.jsx]] — **UI Component (sales)**: Componente UI (sales): SummaryCards `[SummaryCards, fetchTop, fetchMiniSales, get, CustomTooltip]`
- [[react/src/components/sales/summary/InventoryStatSection.jsx]] — **UI Component (sales)**: Componente UI (sales): InventoryStatSection `[InventoryStatSection]`
- [[react/src/components/sales/summary/OrdersStatSection.jsx]] — **UI Component (sales)**: Componente UI (sales): OrdersStatSection `[OrdersStatSection]`
- [[react/src/components/sales/summary/SalesTrendChart.jsx]] — **UI Component (sales)**: Componente UI (sales): SalesTrendChart `[SalesTrendChart]`
- [[react/src/components/sales/summary/StaffCustomersSection.jsx]] — **UI Component (sales)**: Componente UI (sales): StaffCustomersSection `[StaffCustomersSection, getRoleStatIcon]`
- [[react/src/components/sales/summary/TopAnnualProducts.jsx]] — **UI Component (sales)**: Componente UI (sales): TopAnnualProducts `[TopAnnualProducts, handleClickOutside]`
- [[react/src/components/tickets/MyTickets.jsx]] — **UI Component (tickets)**: Componente UI (tickets): MyTickets `[MyTickets, loadTickets, handleTicketClick, handleCloseThread, handleTicketCreated]`
- [[react/src/components/tickets/TicketDashboard.jsx]] — **UI Component (tickets)**: Componente UI (tickets): TicketDashboard `[TicketDashboard, loadTickets, handleTicketClick, handleCloseThread, renderStatusBadge]`
- [[react/src/components/tickets/TicketThread.jsx]] — **UI Component (tickets)**: Componente UI (tickets): TicketThread `[TicketThread, loadTicket, handleSendMessage, handleUpdateStatus, handleEscalate]`
- [[react/src/components/users/LoginForm.jsx]] — **UI Component (users)**: Componente UI (users): LoginForm `[LoginForm, setView, handleLoginSubmit, handleRequestCode, handleResendCode]`
- [[react/src/components/users/ModalChangePassword.jsx]] — **UI Component (users)**: Componente UI (users): ModalChangePassword `[ModalChangePassword, handleChange, handleSubmit]`
- [[react/src/components/users/ModalEditProfile.jsx]] — **UI Component (users)**: Componente UI (users): ModalEditProfile `[ModalEditProfile, loadProfile, handleProfileChange, handlePasswordChange, handleProfileSubmit]`
- [[react/src/components/users/ProfileCard.jsx]] — **UI Component (users)**: Componente UI (users): ProfileCard `[ProfileCard]`
- [[react/src/components/users/UserFormModal.jsx]] — **UI Component (users)**: Componente UI (users): UserFormModal `[UserFormModal, fetchRoles, handleChange, handleSubmit, getRoleLabel]`
- [[react/src/components/warehouse/ModalContainerQR.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalContainerQR `[ModalContainerQR, handleCopyImageToClipboard, handleDownloadPng, handlePrintLabel, handleCopyText]`
- [[react/src/components/warehouse/ModalOrderSplitsDetail.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalOrderSplitsDetail `[ModalOrderSplitsDetail, getStatusBadge]`
- [[react/src/components/warehouse/ModalReassignSplit.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalReassignSplit `[ModalReassignSplit, handleRoleChange, fetchOperators, handleSubmit]`
- [[react/src/components/warehouse/ModalSendToWarehouse.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalSendToWarehouse `[ModalSendToWarehouse, handleSplitsBlur, handleSubmit]`
- [[react/src/components/warehouse/ModalWarehouseAudit.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalWarehouseAudit `[ModalWarehouseAudit, loadAudit, getStatusBadge, handleOpenEditReason, handleOpenAdminModal]`
- [[react/src/components/warehouse/ModalWarehouseEventsLedger.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalWarehouseEventsLedger `[ModalWarehouseEventsLedger, loadData]`
- [[react/src/components/warehouse/WarehouseAdminSection.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseAdminSection `[WarehouseAdminSection, loadStats, loadOrders, handleSearchSubmit, handleToggleVisibility]`
- [[react/src/components/warehouse/WarehouseContainersManagement.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseContainersManagement `[WarehouseContainersManagement, loadStats, loadContainers, handleCopyText, handleCreate]`
- [[react/src/components/warehouse/WarehouseFilterControls.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseFilterControls `[WarehouseFilterControls, handleQuickSplitSubmit]`
- [[react/src/components/warehouse/WarehouseLaserStation.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseLaserStation `[WarehouseLaserStation, handleCopySplitId, isTouchDeviceOrTablet, loadSplit, handleClaimSplitInStation]`
- [[react/src/components/warehouse/WarehouseOperatorSection.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseOperatorSection `[WarehouseOperatorSection, loadStats, handleClaimSplit, loadWarehouseOrders, handleSearchSubmit]`
- [[react/src/components/warehouse/WarehouseSplitsPillList.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseSplitsPillList `[WarehouseSplitsPillList]`
- [[react/src/components/warehouse/WarehouseStatsGrid.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseStatsGrid `[WarehouseStatsGrid]`
- [[react/src/components/warehouse/WarehouseStatusBadge.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): WarehouseStatusBadge `[WarehouseStatusBadge]`
- [[react/src/components/warehouse/audioUtils.js]] — **UI Component (warehouse)**: Componente UI (warehouse): audioUtils `[getAudioContext, playScanSuccessSound, playSplitCompletedSound, playScanErrorSound]`
- [[react/src/components/warehouse/audit/AuditKpiGrid.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): AuditKpiGrid `[AuditKpiGrid]`
- [[react/src/components/warehouse/audit/AuditSplitCard.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): AuditSplitCard `[AuditSplitCard, formatCurrency, formatDateTime, toggleItemExpand, toggleExpandAll]`
- [[react/src/components/warehouse/audit/LedgerContainersTab.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): LedgerContainersTab `[LedgerContainersTab]`
- [[react/src/components/warehouse/audit/LedgerItemsTab.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): LedgerItemsTab `[LedgerItemsTab]`
- [[react/src/components/warehouse/audit/LedgerTimelineTab.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): LedgerTimelineTab `[LedgerTimelineTab]`
- [[react/src/components/warehouse/audit/ModalAuditAdminCounts.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalAuditAdminCounts `[ModalAuditAdminCounts, handleSave]`
- [[react/src/components/warehouse/audit/ModalAuditAdminSplit.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalAuditAdminSplit `[ModalAuditAdminSplit, handleGenerateSealFolio, handleSave]`
- [[react/src/components/warehouse/audit/ModalAuditEditReason.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalAuditEditReason `[ModalAuditEditReason, handleSave]`
- [[react/src/components/warehouse/containers/ContainersFilterControls.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ContainersFilterControls `[ContainersFilterControls]`
- [[react/src/components/warehouse/containers/ContainersStatsGrid.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ContainersStatsGrid `[ContainersStatsGrid]`
- [[react/src/components/warehouse/containers/ContainersTable.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ContainersTable `[ContainersTable]`
- [[react/src/components/warehouse/containers/ModalCreateContainer.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalCreateContainer `[ModalCreateContainer, handleSubmit]`
- [[react/src/components/warehouse/containers/ModalDeleteContainer.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalDeleteContainer `[ModalDeleteContainer]`
- [[react/src/components/warehouse/terminal/LaserStationHeader.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): LaserStationHeader `[LaserStationHeader]`
- [[react/src/components/warehouse/terminal/LaserStationItemsList.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): LaserStationItemsList `[LaserStationItemsList]`
- [[react/src/components/warehouse/terminal/LaserStationModeBar.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): LaserStationModeBar `[LaserStationModeBar]`
- [[react/src/components/warehouse/terminal/LaserStationScannerHUD.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): LaserStationScannerHUD `[LaserStationScannerHUD]`
- [[react/src/components/warehouse/terminal/ModalLaserBoxes.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalLaserBoxes `[ModalLaserBoxes]`
- [[react/src/components/warehouse/terminal/ModalLaserCameraScanner.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalLaserCameraScanner `[ModalLaserCameraScanner, startCamera, stopCamera, toggleTorch, startDetectionLoop]`
- [[react/src/components/warehouse/terminal/ModalLaserFastTrack.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalLaserFastTrack `[ModalLaserFastTrack]`
- [[react/src/components/warehouse/terminal/ModalLaserManual.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalLaserManual `[ModalLaserManual]`
- [[react/src/components/warehouse/terminal/ModalLaserReturn.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalLaserReturn `[ModalLaserReturn]`
- [[react/src/components/warehouse/terminal/ModalLaserSeal.jsx]] — **UI Component (warehouse)**: Componente UI (warehouse): ModalLaserSeal `[ModalLaserSeal]`
- [[react/src/config/api.js]] — **Frontend Resource**: Recurso frontend (api.js) `[buildUrl, getAuthHeaders]`
- [[react/src/config/brand.js]] — **Frontend Resource**: Recurso frontend (brand.js)
- [[react/src/config/navigationModules.js]] — **Frontend Resource**: Recurso frontend (navigationModules.js) `[getAvailableModules]`
- [[react/src/config/permissionMetadata.js]] — **Frontend Resource**: Recurso frontend (permissionMetadata.js)
- [[react/src/config/permissions.js]] — **Frontend Resource**: Recurso frontend (permissions.js)
- [[react/src/context/AuthContext.jsx]] — **State Context**: Contexto de React y proveedor de estado para AuthContext `[AuthProvider, checkAuth, login, logout, useAuth]`
- [[react/src/context/CartContext.jsx]] — **State Context**: Contexto de React y proveedor de estado para CartContext `[CartProvider, loadCart, addToCart, updateQuantity, removeItem]`
- [[react/src/context/PaginationLimitContext.jsx]] — **State Context**: Contexto de React y proveedor de estado para PaginationLimitContext `[PaginationLimitProvider, changeLimit, usePaginationLimit]`
- [[react/src/hooks/useCatalogSettings.js]] — **Frontend Resource**: Recurso frontend (useCatalogSettings.js) `[useCatalogSettings, setViewMode, setVisibleColumns, toggleColumn, resetColumns]`
- [[react/src/hooks/useIOSInstallPrompt.js]] — **Frontend Resource**: Recurso frontend (useIOSInstallPrompt.js) `[useIOSInstallPrompt, dismissPrompt]`
- [[react/src/hooks/usePermissions.js]] — **Frontend Resource**: Recurso frontend (usePermissions.js) `[usePermissions, hasRole, getDashboardPath, can, canAny]`
- [[react/src/hooks/useSidebar.js]] — **Frontend Resource**: Recurso frontend (useSidebar.js) `[useSidebar, handleStorage, handleCustomSync, handleResize, setIsSidebarOpen]`
- [[react/src/hooks/useTheme.js]] — **Frontend Resource**: Recurso frontend (useTheme.js) `[useTheme, toggleTheme]`
- [[react/src/index.css]] — **Frontend Resource**: Recurso frontend (index.css)
- [[react/src/main.jsx]] — **Frontend Resource**: Recurso frontend (main.jsx)
- [[react/src/pages/AboutUs.jsx]] — **View Page**: Vista SPA de página completa para AboutUs `[AboutUs, renderHeader]`
- [[react/src/pages/BeClient.jsx]] — **View Page**: Vista SPA de página completa para BeClient `[BeClient, clearFile, renderFileField, resetTurnstile, handleChange]`
- [[react/src/pages/Cart.jsx]] — **View Page**: Vista SPA de página completa para Cart `[Cart, loadCustomerInfo, handleQuantityChange, handleRemove, handleClearCart]`
- [[react/src/pages/Contact.jsx]] — **View Page**: Vista SPA de página completa para Contact `[Contact, getTurnstileToken, resetTurnstile, handleChange, handleSubmit]`
- [[react/src/pages/FavoriteListDetails.jsx]] — **View Page**: Vista SPA de página completa para FavoriteListDetails `[FavoriteListDetails, fetchListDetails, handleUpdateQuantity, handleTempQuantityChange, handleQuantityBlur]`
- [[react/src/pages/FavoriteLists.jsx]] — **View Page**: Vista SPA de página completa para FavoriteLists `[FavoriteLists, fetchLists, handleCreateList, handleUpdateName, startEditing]`
- [[react/src/pages/Home.jsx]] — **View Page**: Vista SPA de página completa para Home `[Home, renderHeader]`
- [[react/src/pages/Login.jsx]] — **View Page**: Vista SPA de página completa para Login `[Login, getHeading]`
- [[react/src/pages/Orders.jsx]] — **View Page**: Vista SPA de página completa para Orders `[Orders, loadOrders, handleCancelOrder, handleOpenTicketForOrder]`
- [[react/src/pages/PrivacyPolicy.jsx]] — **View Page**: Vista SPA de página completa para PrivacyPolicy `[PrivacyPolicy, renderHeader]`
- [[react/src/pages/Products.jsx]] — **View Page**: Vista SPA de página completa para Products `[Products, loadCategories, loadProducts, handleCategoryChange, handleSortChange]`
- [[react/src/pages/Profile.jsx]] — **View Page**: Vista SPA de página completa para Profile `[Profile, loadProfileData, handleToggleNotification]`
- [[react/src/pages/Promos.jsx]] — **View Page**: Vista SPA de página completa para Promos `[Promos, loadCategories, loadPromotions, handleProductClick]`
- [[react/src/pages/PublicCatalog.jsx]] — **View Page**: Vista SPA de página completa para PublicCatalog `[PublicCatalog, loadCategories, loadPublicPriceLists, loadProducts, handlePriceListChange]`
- [[react/src/pages/Support.jsx]] — **View Page**: Vista SPA de página completa para Support `[Support]`
- [[react/src/pages/TermsAndConditions.jsx]] — **View Page**: Vista SPA de página completa para TermsAndConditions `[TermsAndConditions, renderHeader]`
- [[react/src/pages/UnifiedDashboard.jsx]] — **View Page**: Vista SPA de página completa para UnifiedDashboard `[UnifiedDashboard, handleTabChange, loadPendingCounts, loadDashboardData, renderTabContent]`
- [[react/src/routes/ProtectedRoute.jsx]] — **Frontend Resource**: Recurso frontend (ProtectedRoute.jsx) `[ProtectedRoute]`
- [[react/src/services/adminService.js]] — **API Client**: Cliente API y llamadas HTTP para adminService `[getTopProducts, getDashboardStats, getDashboardFinanceStats, getDashboardOrderStats, getDashboardUsersCustomersStats]`
- [[react/src/services/announcementService.js]] — **API Client**: Cliente API y llamadas HTTP para announcementService
- [[react/src/services/apiService.js]] — **API Client**: Cliente API y llamadas HTTP para apiService `[constructor, getHeaders, request, get, post]`
- [[react/src/services/authService.js]] — **API Client**: Cliente API y llamadas HTTP para authService `[login, register, getCurrentUser, logout, requestPasswordResetCode]`
- [[react/src/services/catalogService.js]] — **API Client**: Cliente API y llamadas HTTP para catalogService `[getProducts, getCatalogProducts, getProduct, getCustomerCatalogProducts, getCustomerRecommendations]`
- [[react/src/services/categoryService.js]] — **API Client**: Cliente API y llamadas HTTP para categoryService `[getCategories, getCategoryById, createCategory, updateCategory, deleteCategory]`
- [[react/src/services/contactClientService.js]] — **API Client**: Cliente API y llamadas HTTP para contactClientService `[getContactMessages, updateContactStatus, deleteContactMessage, getClientRequests, getClientRequestDocUrl]`
- [[react/src/services/customerService.js]] — **API Client**: Cliente API y llamadas HTTP para customerService `[getCustomers, getCustomer, createCustomer, updateCustomer, deleteCustomer]`
- [[react/src/services/dashboardService.js]] — **API Client**: Cliente API y llamadas HTTP para dashboardService `[getOperationalStats, getOrderStats, getInventoryStats, getFinanceStats, getUsersCustomersStats]`
- [[react/src/services/discountService.js]] — **API Client**: Cliente API y llamadas HTTP para discountService `[getDiscounts, getDiscountStats, getDiscount, getActiveDiscount, createDiscount]`
- [[react/src/services/favoriteService.js]] — **API Client**: Cliente API y llamadas HTTP para favoriteService
- [[react/src/services/index.js]] — **API Client**: Cliente API y llamadas HTTP para index
- [[react/src/services/orderService.js]] — **API Client**: Cliente API y llamadas HTTP para orderService `[getCart, addToCart, updateCartItem, removeCartItem, clearCart]`
- [[react/src/services/priceListService.js]] — **API Client**: Cliente API y llamadas HTTP para priceListService `[getPriceLists, getPriceList, createPriceList, updatePriceList, deletePriceList]`
- [[react/src/services/productService.js]] — **API Client**: Cliente API y llamadas HTTP para productService `[getProducts, getProductById, getProductBycodebar, createProduct, updateProduct]`
- [[react/src/services/salesGroupService.js]] — **API Client**: Cliente API y llamadas HTTP para salesGroupService `[getSalesGroups, getSalesGroup, createSalesGroup, updateSalesGroup, deleteSalesGroup]`
- [[react/src/services/ticketService.js]] — **API Client**: Cliente API y llamadas HTTP para ticketService `[getTickets, getTicket, createTicket, addMessage, updateStatus]`
- [[react/src/services/userService.js]] — **API Client**: Cliente API y llamadas HTTP para userService `[getCurrentUser, updateCurrentUser, getCurrentUserCustomerInfo, getUserCustomerInfo, updateUserCustomerInfo]`
- [[react/src/services/warehouseService.js]] — **API Client**: Cliente API y llamadas HTTP para warehouseService `[getQueue, getOrdersHistory, getStats, getSplit, getSplitByCode]`
- [[react/src/styles/atoms/_badges.scss]] — **Frontend Resource**: Recurso frontend (_badges.scss)
- [[react/src/styles/atoms/_buttons.scss]] — **Frontend Resource**: Recurso frontend (_buttons.scss)
- [[react/src/styles/atoms/_index.scss]] — **Frontend Resource**: Recurso frontend (_index.scss)
- [[react/src/styles/atoms/_inputs.scss]] — **Frontend Resource**: Recurso frontend (_inputs.scss)
- [[react/src/styles/atoms/_labels.scss]] — **Frontend Resource**: Recurso frontend (_labels.scss)
- [[react/src/styles/atoms/_spinners.scss]] — **Frontend Resource**: Recurso frontend (_spinners.scss)
- [[react/src/styles/main.scss]] — **Frontend Resource**: Recurso frontend (main.scss)
- [[react/src/styles/molecules/_favorite-list-card.scss]] — **Frontend Resource**: Recurso frontend (_favorite-list-card.scss)
- [[react/src/styles/molecules/_file-upload.scss]] — **Frontend Resource**: Recurso frontend (_file-upload.scss)
- [[react/src/styles/molecules/_filter-group.scss]] — **Frontend Resource**: Recurso frontend (_filter-group.scss)
- [[react/src/styles/molecules/_form-group.scss]] — **Frontend Resource**: Recurso frontend (_form-group.scss)
- [[react/src/styles/molecules/_group-card.scss]] — **Frontend Resource**: Recurso frontend (_group-card.scss)
- [[react/src/styles/molecules/_help-guide.scss]] — **Frontend Resource**: Recurso frontend (_help-guide.scss)
- [[react/src/styles/molecules/_index.scss]] — **Frontend Resource**: Recurso frontend (_index.scss)
- [[react/src/styles/molecules/_order-stats.scss]] — **Frontend Resource**: Recurso frontend (_order-stats.scss)
- [[react/src/styles/molecules/_pagination.scss]] — **Frontend Resource**: Recurso frontend (_pagination.scss)
- [[react/src/styles/molecules/_product-card.scss]] — **Frontend Resource**: Recurso frontend (_product-card.scss)
- [[react/src/styles/molecules/_search-bar.scss]] — **Frontend Resource**: Recurso frontend (_search-bar.scss)
- [[react/src/styles/molecules/_stat-card.scss]] — **Frontend Resource**: Recurso frontend (_stat-card.scss)
- [[react/src/styles/molecules/_status-badge.scss]] — **Frontend Resource**: Recurso frontend (_status-badge.scss)
- [[react/src/styles/molecules/_stock-badge.scss]] — **Frontend Resource**: Recurso frontend (_stock-badge.scss)
- [[react/src/styles/molecules/_stock-conflict-banner.scss]] — **Frontend Resource**: Recurso frontend (_stock-conflict-banner.scss)
- [[react/src/styles/organisms/_announcements.scss]] — **Frontend Resource**: Recurso frontend (_announcements.scss)
- [[react/src/styles/organisms/_cart.scss]] — **Frontend Resource**: Recurso frontend (_cart.scss)
- [[react/src/styles/organisms/_charts.scss]] — **Frontend Resource**: Recurso frontend (_charts.scss)
- [[react/src/styles/organisms/_dashboard-section.scss]] — **Frontend Resource**: Recurso frontend (_dashboard-section.scss)
- [[react/src/styles/organisms/_data-table.scss]] — **Frontend Resource**: Recurso frontend (_data-table.scss)
- [[react/src/styles/organisms/_discounts-manager.scss]] — **Frontend Resource**: Recurso frontend (_discounts-manager.scss)
- [[react/src/styles/organisms/_footer.scss]] — **Frontend Resource**: Recurso frontend (_footer.scss)
- [[react/src/styles/organisms/_header.scss]] — **Frontend Resource**: Recurso frontend (_header.scss)
- [[react/src/styles/organisms/_hero.scss]] — **Frontend Resource**: Recurso frontend (_hero.scss)
- [[react/src/styles/organisms/_index.scss]] — **Frontend Resource**: Recurso frontend (_index.scss)
- [[react/src/styles/organisms/_modal-split-view.scss]] — **Frontend Resource**: Recurso frontend (_modal-split-view.scss)
- [[react/src/styles/organisms/_modal.scss]] — **Frontend Resource**: Recurso frontend (_modal.scss)
- [[react/src/styles/organisms/_order-details.scss]] — **Frontend Resource**: Recurso frontend (_order-details.scss)
- [[react/src/styles/organisms/_pos-view.scss]] — **Frontend Resource**: Recurso frontend (_pos-view.scss)
- [[react/src/styles/organisms/_product-details.scss]] — **Frontend Resource**: Recurso frontend (_product-details.scss)
- [[react/src/styles/organisms/_product-grid.scss]] — **Frontend Resource**: Recurso frontend (_product-grid.scss)
- [[react/src/styles/organisms/_role-form-modal.scss]] — **Frontend Resource**: Recurso frontend (_role-form-modal.scss)
- [[react/src/styles/organisms/_sidebar-drawer.scss]] — **Frontend Resource**: Recurso frontend (_sidebar-drawer.scss)
- [[react/src/styles/organisms/_tickets.scss]] — **Frontend Resource**: Recurso frontend (_tickets.scss)
- [[react/src/styles/organisms/_warehouse-manager.scss]] — **Frontend Resource**: Recurso frontend (_warehouse-manager.scss)
- [[react/src/styles/templates/_auth-layout.scss]] — **Frontend Resource**: Recurso frontend (_auth-layout.scss)
- [[react/src/styles/templates/_dashboard-layout.scss]] — **Frontend Resource**: Recurso frontend (_dashboard-layout.scss)
- [[react/src/styles/templates/_index.scss]] — **Frontend Resource**: Recurso frontend (_index.scss)
- [[react/src/styles/templates/_page-layout.scss]] — **Frontend Resource**: Recurso frontend (_page-layout.scss)
- [[react/src/styles/templates/_promos.scss]] — **Frontend Resource**: Recurso frontend (_promos.scss)
- [[react/src/styles/templates/_storefront-layout.scss]] — **Frontend Resource**: Recurso frontend (_storefront-layout.scss)
- [[react/src/styles/tokens/_borders.scss]] — **Frontend Resource**: Recurso frontend (_borders.scss)
- [[react/src/styles/tokens/_breakpoints.scss]] — **Frontend Resource**: Recurso frontend (_breakpoints.scss)
- [[react/src/styles/tokens/_colors.scss]] — **Frontend Resource**: Recurso frontend (_colors.scss)
- [[react/src/styles/tokens/_index.scss]] — **Frontend Resource**: Recurso frontend (_index.scss)
- [[react/src/styles/tokens/_shadows.scss]] — **Frontend Resource**: Recurso frontend (_shadows.scss)
- [[react/src/styles/tokens/_spacing.scss]] — **Frontend Resource**: Recurso frontend (_spacing.scss)
- [[react/src/styles/tokens/_typography.scss]] — **Frontend Resource**: Recurso frontend (_typography.scss)
- [[react/src/styles/utilities/_flex.scss]] — **Frontend Resource**: Recurso frontend (_flex.scss)
- [[react/src/styles/utilities/_grid.scss]] — **Frontend Resource**: Recurso frontend (_grid.scss)
- [[react/src/styles/utilities/_index.scss]] — **Frontend Resource**: Recurso frontend (_index.scss)
- [[react/src/styles/utilities/_spacing.scss]] — **Frontend Resource**: Recurso frontend (_spacing.scss)
- [[react/src/styles/utilities/_text.scss]] — **Frontend Resource**: Recurso frontend (_text.scss)
- [[react/src/styles/utilities/_visibility.scss]] — **Frontend Resource**: Recurso frontend (_visibility.scss)
- [[react/src/styles/vendor/_normalize.scss]] — **Frontend Resource**: Recurso frontend (_normalize.scss)
- [[react/src/utils/formatUtils.js]] — **Helper Utility**: Funciones utilitarias y helpers (formatUtils.js) `[formatCurrency, formatNumber, formatMexicoDateTime, formatMexicoDate, toDateTimeLocalString]`
- [[react/src/utils/imageUtils.js]] — **Helper Utility**: Funciones utilitarias y helpers (imageUtils.js) `[getProductImageUrl]`
- [[react/src/utils/registerSW.js]] — **Helper Utility**: Funciones utilitarias y helpers (registerSW.js) `[registerServiceWorker, unregisterServiceWorker]`
- [[react/src/utils/schemas.js]] — **Helper Utility**: Funciones utilitarias y helpers (schemas.js) `[createBreadcrumbSchema]`
- [[react/vite.config.js]] — **Frontend Resource**: Recurso frontend (vite.config.js) `[transformIndexHtml]`

### Scripts & Sincronización ERP (67 archivos)

- [[scripts/build_obsidian_inventory.py]] — **General Module**: Módulo (build_obsidian_inventory.py)
- [[scripts/deploy.sh]] — **General Module**: Módulo (deploy.sh)
- [[scripts/replace_names.py]] — **General Module**: Módulo (replace_names.py)
- [[scripts/rosario/descargar_imagenes_rosario.py]] — **General Module**: Módulo (descargar_imagenes_rosario.py)
- [[scripts/setup_client_assets.py]] — **General Module**: Módulo (setup_client_assets.py)
- [[sync_alpha/runners/aws_s3_sync_images.bat]] — **General Module**: Módulo (aws_s3_sync_images.bat)
- [[sync_alpha/runners/compress_images.bat]] — **General Module**: Módulo (compress_images.bat)
- [[sync_alpha/runners/configure_aws.bat]] — **General Module**: Módulo (configure_aws.bat)
- [[sync_alpha/runners/run_daily_images.bat]] — **General Module**: Módulo (run_daily_images.bat)
- [[sync_alpha/runners/sync_all_batch.bat]] — **General Module**: Módulo (sync_all_batch.bat)
- [[sync_alpha/runners/sync_products_batch.bat]] — **General Module**: Módulo (sync_products_batch.bat)
- [[sync_alpha/runners/sync_users_batch.bat]] — **General Module**: Módulo (sync_users_batch.bat)
- [[sync_alpha/runners/upload_all_zip.bat]] — **General Module**: Módulo (upload_all_zip.bat)
- [[sync_alpha/runners/upload_products_zip.bat]] — **General Module**: Módulo (upload_products_zip.bat)
- [[sync_alpha/runners/upload_users_zip.bat]] — **General Module**: Módulo (upload_users_zip.bat)
- [[sync_alpha/src/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_alpha/src/config.py]] — **General Module**: Módulo (config.py)
- [[sync_alpha/src/extractors/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_alpha/src/extractors/dbf_reader.py]] — **General Module**: Módulo (dbf_reader.py)
- [[sync_alpha/src/extractors/prices_extractor.py]] — **General Module**: Módulo (prices_extractor.py)
- [[sync_alpha/src/extractors/products_extractor.py]] — **General Module**: Módulo (products_extractor.py)
- [[sync_alpha/src/extractors/users_extractor.py]] — **General Module**: Módulo (users_extractor.py)
- [[sync_alpha/src/images/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_alpha/src/images/compress_images.py]] — **General Module**: Módulo (compress_images.py)
- [[sync_alpha/src/images/list_files_by_size.py]] — **General Module**: Módulo (list_files_by_size.py)
- [[sync_alpha/src/transformers/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_alpha/src/transformers/builders.py]] — **General Module**: Módulo (builders.py)
- [[sync_alpha/src/transformers/data_cleaning.py]] — **General Module**: Módulo (data_cleaning.py)
- [[sync_alpha/src/uploader/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_alpha/src/uploader/api_client.py]] — **General Module**: Módulo (api_client.py)
- [[sync_alpha/src/uploader/sync_all_batch.py]] — **General Module**: Módulo (sync_all_batch.py)
- [[sync_alpha/src/uploader/sync_all_zip.py]] — **General Module**: Módulo (sync_all_zip.py)
- [[sync_alpha/src/uploader/sync_products_batch.py]] — **General Module**: Módulo (sync_products_batch.py)
- [[sync_alpha/src/uploader/sync_products_zip.py]] — **General Module**: Módulo (sync_products_zip.py)
- [[sync_alpha/src/uploader/sync_users_batch.py]] — **General Module**: Módulo (sync_users_batch.py)
- [[sync_alpha/src/uploader/sync_users_zip.py]] — **General Module**: Módulo (sync_users_zip.py)
- [[sync_local/runners/aws_s3_sync_images.bat]] — **General Module**: Módulo (aws_s3_sync_images.bat)
- [[sync_local/runners/compress_images.bat]] — **General Module**: Módulo (compress_images.bat)
- [[sync_local/runners/configure_aws.bat]] — **General Module**: Módulo (configure_aws.bat)
- [[sync_local/runners/run_daily_images.bat]] — **General Module**: Módulo (run_daily_images.bat)
- [[sync_local/runners/sync_all_batch.bat]] — **General Module**: Módulo (sync_all_batch.bat)
- [[sync_local/runners/sync_products_batch.bat]] — **General Module**: Módulo (sync_products_batch.bat)
- [[sync_local/runners/sync_users_batch.bat]] — **General Module**: Módulo (sync_users_batch.bat)
- [[sync_local/runners/upload_all_zip.bat]] — **General Module**: Módulo (upload_all_zip.bat)
- [[sync_local/runners/upload_products_zip.bat]] — **General Module**: Módulo (upload_products_zip.bat)
- [[sync_local/runners/upload_users_zip.bat]] — **General Module**: Módulo (upload_users_zip.bat)
- [[sync_local/src/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_local/src/config.py]] — **General Module**: Módulo (config.py)
- [[sync_local/src/extractors/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_local/src/extractors/dbf_reader.py]] — **General Module**: Módulo (dbf_reader.py)
- [[sync_local/src/extractors/prices_extractor.py]] — **General Module**: Módulo (prices_extractor.py)
- [[sync_local/src/extractors/products_extractor.py]] — **General Module**: Módulo (products_extractor.py)
- [[sync_local/src/extractors/users_extractor.py]] — **General Module**: Módulo (users_extractor.py)
- [[sync_local/src/images/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_local/src/images/compress_images.py]] — **General Module**: Módulo (compress_images.py)
- [[sync_local/src/images/list_files_by_size.py]] — **General Module**: Módulo (list_files_by_size.py)
- [[sync_local/src/transformers/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_local/src/transformers/builders.py]] — **General Module**: Módulo (builders.py)
- [[sync_local/src/transformers/data_cleaning.py]] — **General Module**: Módulo (data_cleaning.py)
- [[sync_local/src/uploader/__init__.py]] — **General Module**: Módulo (__init__.py)
- [[sync_local/src/uploader/api_client.py]] — **General Module**: Módulo (api_client.py)
- [[sync_local/src/uploader/sync_all_batch.py]] — **General Module**: Módulo (sync_all_batch.py)
- [[sync_local/src/uploader/sync_all_zip.py]] — **General Module**: Módulo (sync_all_zip.py)
- [[sync_local/src/uploader/sync_products_batch.py]] — **General Module**: Módulo (sync_products_batch.py)
- [[sync_local/src/uploader/sync_products_zip.py]] — **General Module**: Módulo (sync_products_zip.py)
- [[sync_local/src/uploader/sync_users_batch.py]] — **General Module**: Módulo (sync_users_batch.py)
- [[sync_local/src/uploader/sync_users_zip.py]] — **General Module**: Módulo (sync_users_zip.py)
