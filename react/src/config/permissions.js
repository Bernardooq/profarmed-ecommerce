/**
 * Catálogo Maestro de Permisos del Sistema (PBAC / RBAC)
 * Sincronizado 1:1 con PERMISSIONS_AND_CONSTRAINTS.md
 */

export const PERMISSIONS = {
  // 1. Administración Central y Sistema
  SYSTEM_ADMIN: 'system.admin',
  SYSTEM_SYNC: 'system.sync',
  
  // 2. Usuarios Internos
  USERS_VIEW: 'users.view',
  USERS_CREATE: 'users.create',
  USERS_EDIT: 'users.edit',
  USERS_DELETE: 'users.delete',
  ROLES_ASSIGN: 'roles.assign',
  ROLES_VIEW: 'roles.view',

  // 3. Anuncios y Marketing
  ANNOUNCEMENTS_VIEW: 'announcements.view',
  ANNOUNCEMENTS_CREATE: 'announcements.create',
  ANNOUNCEMENTS_EDIT: 'announcements.edit',
  ANNOUNCEMENTS_DELETE: 'announcements.delete',
  ANNOUNCEMENTS_UPLOAD: 'announcements.upload',
  ANNOUNCEMENTS_BROADCAST: 'announcements.broadcast',

  // 3.1 Publicidad de Inicio (Inicio B2B)
  PROMO_ADS_VIEW: 'promo_ads.view',
  PROMO_ADS_CREATE: 'promo_ads.create',
  PROMO_ADS_EDIT: 'promo_ads.edit',
  PROMO_ADS_DELETE: 'promo_ads.delete',
  PROMO_ADS_UPLOAD: 'promo_ads.upload',


  // 4. Gestión de Pedidos y Ventas B2B (Orders)
  ORDERS_VIEW: 'orders.view',
  ORDERS_GROUP_VIEW: 'orders.group_view',
  ORDERS_CREATE: 'orders.create',
  ORDERS_EDIT: 'orders.edit',
  ORDERS_ASSIGN: 'orders.assign',
  ORDERS_STATUS: 'orders.status',
  ORDERS_APPROVE: 'orders.approve',
  ORDERS_SHIP: 'orders.ship',
  ORDERS_DELIVER: 'orders.deliver',
  ORDERS_CANCEL: 'orders.cancel',
  ORDERS_EXPORT: 'orders.export',
  ORDERS_VIEW_ALL: 'orders.view_all',
  CATALOG_CUSTOMER_VIEW: 'catalog.customer_view', // Consulta precios B2B por cliente para cotizar y vender

  // 5. Almacén y Surtido (Warehouse)
  WAREHOUSE_VIEW: 'warehouse.view',
  WAREHOUSE_OPERATOR: 'warehouse.operator',
  WAREHOUSE_CHECKER: 'warehouse.checker',
  WAREHOUSE_SEND: 'warehouse.send',
  WAREHOUSE_SUPERVISOR: 'warehouse.supervisor',
  WAREHOUSE_AUDIT: 'warehouse.audit',
  WAREHOUSE_MANAGE: 'warehouse.manage',
  WAREHOUSE_CONTAINERS: 'warehouse.containers', // Gestión de canastas QR físicas
  WAREHOUSE_EVENTS: 'warehouse.events',         // Bitácora atómica de escaneos (Event Ledger)
  WAREHOUSE_FILTER2_SEND: 'warehouse.filter2_send', // Enviar split a segundo filtro de revisión
  WAREHOUSE_SEAL_DIRECT: 'warehouse.seal_direct',   // Sellar y finalizar split directo en piso (sin 2do filtro)
  WAREHOUSE_MODE_DIRECT: 'warehouse.mode_direct',   // Activar modalidad surtido directo por split
  WAREHOUSE_MODE_CONTAINERS: 'warehouse.mode_containers', // Activar modalidad con canastas QR

  // 6. Estrategia de Precios y Descuentos (Pricing)
  CATALOG_PRICES: 'catalog.prices',
  CATALOG_PRICES_PUBLIC: 'catalog.prices_public',
  CATALOG_DISCOUNTS: 'catalog.discounts',

  // 7. Inventario y Catálogo Físico (Products)
  CATALOG_VIEW: 'catalog.view',
  CATALOG_EXPORT: 'catalog.export',
  CATALOG_CATEGORIES: 'catalog.categories',
  PRODUCTS_CREATE: 'products.create',
  PRODUCTS_EDIT: 'products.edit',
  PRODUCTS_COST: 'products.cost',
  PRODUCTS_MANAGE: 'products.manage',
  PRODUCTS_DELETE: 'products.delete',
  PRODUCTS_STOCK: 'products.stock',
  PRODUCTS_IMAGES: 'products.images',

  // 9. Clientes B2B y Solicitudes
  CUSTOMERS_VIEW: 'customers.view',
  CUSTOMERS_CREATE: 'customers.create',
  CUSTOMERS_EDIT: 'customers.edit',
  CUSTOMERS_DELETE: 'customers.delete',
  CUSTOMERS_ADDRESSES_EDIT: 'customers.addresses_edit',
  CUSTOMERS_REQUESTS_VIEW: 'customers.requests_view',
  CUSTOMERS_REQUESTS_DOWNLOAD: 'customers.requests_download',
  CUSTOMERS_REQUESTS_MANAGE: 'customers.requests_manage',
  CUSTOMERS_ASSIGN: 'customers.assign',
  CUSTOMERS_VIEW_ALL: 'customers.view_all',

  // 10. Grupos de Ventas
  GROUPS_VIEW: 'groups.view',
  GROUPS_MANAGE: 'groups.manage',

  // 11. Mensajes de Contacto
  CONTACT_VIEW: 'contact.view',
  CONTACT_MANAGE: 'contact.manage',

  // 12. Tickets de Soporte
  SUPPORT_VIEW: 'support.view',
  SUPPORT_CREATE: 'support.create',
  SUPPORT_REPLY: 'support.reply',
  SUPPORT_MANAGE: 'support.manage',
  SUPPORT_DEESCALATE: 'support.deescalate',

  // 13. Reportes y Dashboards
  REPORTS_VIEW: 'reports.view',
  REPORTS_FINANCIAL: 'reports.financial',
  REPORTS_SALES: 'reports.sales',
  REPORTS_EXPORT: 'reports.export'
};

/**
 * Operaciones del Storefront B2B accesibles intrinsecamente para clientes
 * (Catalogo, Promociones/Ofertas, Sus Pedidos y Soporte)
 */
export const STOREFRONT_PERMISSIONS = [
  PERMISSIONS.CATALOG_VIEW,
  PERMISSIONS.ANNOUNCEMENTS_VIEW,
  PERMISSIONS.ORDERS_VIEW,
  PERMISSIONS.SUPPORT_VIEW,
  PERMISSIONS.SUPPORT_CREATE,
  PERMISSIONS.SUPPORT_REPLY,
];
