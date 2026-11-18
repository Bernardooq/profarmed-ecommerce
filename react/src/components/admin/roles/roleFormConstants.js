import {
  faShieldAlt, faBoxesStacked, faShoppingCart, faUsers, faUserTie,
  faChartLine, faCog, faLayerGroup, faHeadset, faEnvelope
} from '@fortawesome/free-solid-svg-icons';

/**
 * Orden canónico de módulos sincronizado 1:1 con PERMISSIONS_AND_CONSTRAINTS.md
 */
export const CANONICAL_MODULE_ORDER = [
  'users',          // 1. Usuarios y Administración Central
  'orders',         // 2. Pedidos y Ciclo de Venta
  'warehouse',      // 3. Almacén, Surtido y Bodega
  'products',       // 4. Inventario y Catálogo Físico
  'pricing',        // 5. Precios y Descuentos
  'customers',      // 6. Clientes B2B y Cartera
  'groups',         // 7. Grupos Comerciales de Venta
  'announcements',  // 8. Anuncios y Promociones
  'promo_ads',        // 8.1 Publicidad de Inicio
  'reports',        // 9. Reportes y Analítica
  'support',        // 10. Tickets y Soporte
  'contact',        // 11. Mensajes de Contacto
  'system'          // 12. Sistema Central y ERP
];

/**
 * Orden canónico jerárquico de permisos dentro de cada módulo (según PERMISSIONS_AND_CONSTRAINTS.md)
 */
export const CANONICAL_PERMISSION_ORDER = [
  // 1. Usuarios
  'users.view', 'users.create', 'users.edit', 'users.delete', 'roles.assign', 'roles.view',
  // 2. Pedidos y Ventas
  'orders.view', 'orders.group_view', 'orders.view_all', 'orders.create', 'catalog.customer_view', 'orders.edit', 'orders.assign', 'orders.status', 'orders.approve', 'orders.ship', 'orders.deliver', 'orders.cancel', 'orders.export',
  // 3. Almacén
  'warehouse.view', 'warehouse.operator', 'warehouse.checker', 'warehouse.send', 'warehouse.supervisor', 'warehouse.audit', 'warehouse.manage', 'warehouse.containers', 'warehouse.events', 'warehouse.filter2_send', 'warehouse.seal_direct', 'warehouse.mode_direct', 'warehouse.mode_containers',
  // 4. Inventario y Catálogo Físico
  'catalog.view', 'products.create', 'products.edit', 'products.stock', 'products.cost', 'catalog.categories', 'catalog.export', 'products.manage', 'products.delete', 'products.images',
  // 5. Precios y Descuentos
  'catalog.prices', 'catalog.prices_public', 'catalog.discounts',
  // 6. Clientes B2B
  'customers.view', 'customers.create', 'customers.edit', 'customers.delete', 'customers.addresses_edit', 'customers.requests_view', 'customers.requests_download', 'customers.requests_manage', 'customers.assign', 'customers.view_all',
  // 7. Grupos Comerciales
  'groups.view', 'groups.manage',
  // 8. Anuncios
  'announcements.view', 'announcements.create', 'announcements.edit', 'announcements.delete', 'announcements.upload', 'announcements.broadcast',
  // 8.1 Publicidad de Inicio
  'promo_ads.view', 'promo_ads.create', 'promo_ads.edit', 'promo_ads.delete', 'promo_ads.upload',
  // 9. Reportes
  'reports.view', 'reports.financial', 'reports.sales', 'reports.export',
  // 10. Tickets
  'support.view', 'support.create', 'support.reply', 'support.manage', 'support.deescalate',
  // 11. Contacto
  'contact.view', 'contact.manage',
  // 12. Sistema Central
  'system.admin', 'system.sync'
];

/**
 * Mapeo canónico O(1) de permisos a módulos para garantizar integridad visual en los paneles
 */
export const PERMISSION_TO_MODULE = {
  // 1. Usuarios y Equipo
  'users.view': 'users', 'users.create': 'users', 'users.edit': 'users', 'users.delete': 'users', 'roles.assign': 'users', 'roles.view': 'users',
  // 2. Pedidos y Ventas
  'orders.view': 'orders', 'orders.group_view': 'orders', 'orders.view_all': 'orders', 'orders.create': 'orders', 'catalog.customer_view': 'orders', 'orders.edit': 'orders', 'orders.assign': 'orders', 'orders.status': 'orders', 'orders.approve': 'orders', 'orders.ship': 'orders', 'orders.deliver': 'orders', 'orders.cancel': 'orders', 'orders.export': 'orders',
  // 3. Almacén y Surtido
  'warehouse.view': 'warehouse', 'warehouse.operator': 'warehouse', 'warehouse.checker': 'warehouse', 'warehouse.send': 'warehouse', 'warehouse.supervisor': 'warehouse', 'warehouse.audit': 'warehouse', 'warehouse.manage': 'warehouse', 'warehouse.containers': 'warehouse', 'warehouse.events': 'warehouse', 'warehouse.filter2_send': 'warehouse', 'warehouse.seal_direct': 'warehouse', 'warehouse.mode_direct': 'warehouse', 'warehouse.mode_containers': 'warehouse',
  // 4. Inventario y Catálogo
  'catalog.view': 'products', 'products.create': 'products', 'products.edit': 'products', 'products.stock': 'products', 'products.cost': 'products', 'catalog.categories': 'products', 'catalog.export': 'products', 'products.manage': 'products', 'products.delete': 'products', 'products.images': 'products',
  // 5. Precios y Descuentos
  'catalog.prices': 'pricing', 'catalog.prices_public': 'pricing', 'catalog.discounts': 'pricing',
  // 6. Clientes B2B
  'customers.view': 'customers', 'customers.create': 'customers', 'customers.edit': 'customers', 'customers.delete': 'customers', 'customers.addresses_edit': 'customers', 'customers.requests_view': 'customers', 'customers.requests_download': 'customers', 'customers.requests_manage': 'customers', 'customers.assign': 'customers', 'customers.view_all': 'customers',
  // 7. Grupos Comerciales
  'groups.view': 'groups', 'groups.manage': 'groups',
  // 8. Anuncios y Promociones
  'announcements.view': 'announcements', 'announcements.create': 'announcements', 'announcements.edit': 'announcements', 'announcements.delete': 'announcements', 'announcements.upload': 'announcements', 'announcements.broadcast': 'announcements',
  // 8.1 Publicidad de Inicio
  'promo_ads.view': 'promo_ads', 'promo_ads.create': 'promo_ads', 'promo_ads.edit': 'promo_ads', 'promo_ads.delete': 'promo_ads', 'promo_ads.upload': 'promo_ads',
  // 9. Reportes y Analítica
  'reports.view': 'reports', 'reports.financial': 'reports', 'reports.sales': 'reports', 'reports.export': 'reports',
  // 10. Tickets y Soporte
  'support.view': 'support', 'support.create': 'support', 'support.reply': 'support', 'support.manage': 'support', 'support.deescalate': 'support',
  // 11. Mensajes de Contacto
  'contact.view': 'contact', 'contact.manage': 'contact',
  // 12. Sistema Central
  'system.admin': 'system', 'system.sync': 'system'
};

export const MODULE_CONFIG = {
  users: { label: 'Usuarios y Equipo', icon: faUserTie, description: 'Directorio de colaboradores, roles dinámicos y cuentas internas' },
  orders: { label: 'Pedidos y Ventas', icon: faShoppingCart, description: 'Creación B2B, cotización por cliente, matriz de estados y despacho' },
  warehouse: { label: 'Almacén y Surtido', icon: faBoxesStacked, description: 'Operación física de bodega, terminal láser y auditoría' },
  products: { label: 'Inventario y Catálogo', icon: faBoxesStacked, description: 'Gestión física de productos, stock, anaquel, costos confidenciales y categorías' },
  pricing: { label: 'Precios y Descuentos', icon: faBoxesStacked, description: 'Listas de precios mayoristas, markups porcentuales y promociones' },
  customers: { label: 'Clientes B2B', icon: faUsers, description: 'Cartera de clientes comerciales, asignación de vendedor y sucursales' },
  groups: { label: 'Grupos Comerciales', icon: faLayerGroup, description: 'Unidades comerciales de venta y membresías colaborativas' },
  announcements: { label: 'Anuncios y Promociones', icon: faEnvelope, description: 'Banners, historias, promociones y difusión masiva' },
  promo_ads: { label: 'Publicidad de Inicio', icon: faLayerGroup, description: 'Secciones de 1 a 4 columnas, carruseles e imágenes responsivas de inicio' },
  reports: { label: 'Reportes y Analítica', icon: faChartLine, description: 'Métricas de venta, balances financieros e inteligencia de negocio' },
  support: { label: 'Tickets y Soporte', icon: faHeadset, description: 'Mesa de ayuda, tickets de clientes y resolución de incidencias' },
  contact: { label: 'Mensajes de Contacto', icon: faEnvelope, description: 'Bandeja de entrada de prospectos y mensajes del sitio web' },
  system: { label: 'Sistema Central', icon: faCog, description: 'Superadministración, configuración global y sincronización FoxPro/ERP' },
};
