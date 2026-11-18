/**
 * navigationModules.js
 * ====================
 * Catálogo Maestro Unificado de Módulos Operativos y Administrativos B2B.
 * 
 * Fuente única de verdad para el orden prioritario, iconos, etiquetas y
 * descubrimiento de capacidades (PBAC / RBAC) en:
 * - SidebarDrawer.jsx (Menú lateral global)
 * - UnifiedDashboard.jsx (Navegación de pestañas del panel de control)
 */

import { PERMISSIONS } from './permissions';

export const NAVIGATION_MODULES = [
  // 1. Visión Estratégica & Analítica
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: '📊',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.REPORTS_VIEW) ||
      can(PERMISSIONS.REPORTS_FINANCIAL)
  },
  {
    id: 'reportes',
    label: 'Reportes',
    icon: '📈',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.REPORTS_SALES) ||
      can(PERMISSIONS.REPORTS_FINANCIAL)
  },

  // 2. Fulfillment y Cadena de Suministro Operativa
  {
    id: 'pedidos',
    label: 'Pedidos',
    icon: '📦',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.ORDERS_VIEW) ||
      can(PERMISSIONS.ORDERS_CREATE) ||
      can(PERMISSIONS.ORDERS_APPROVE)
  },
  {
    id: 'almacen',
    label: 'Almacén',
    icon: '🏭',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.WAREHOUSE_VIEW) ||
      can(PERMISSIONS.WAREHOUSE_OPERATOR) ||
      can(PERMISSIONS.WAREHOUSE_CHECKER) ||
      can(PERMISSIONS.WAREHOUSE_SUPERVISOR) ||
      can(PERMISSIONS.WAREHOUSE_MANAGE) ||
      can(PERMISSIONS.WAREHOUSE_AUDIT)
  },
  {
    id: 'inventario',
    label: 'Inventario',
    icon: '💊',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.CATALOG_VIEW)
  },

  // 3. Relaciones Comerciales y Fuerza de Ventas
  {
    id: 'clientes',
    label: 'Clientes',
    icon: '👥',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.CUSTOMERS_VIEW) ||
      can(PERMISSIONS.CUSTOMERS_VIEW_ALL)
  },
  {
    id: 'equipo',
    label: 'Equipo',
    icon: '💼',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.USERS_VIEW) ||
      can(PERMISSIONS.GROUPS_VIEW) ||
      can(PERMISSIONS.GROUPS_MANAGE)
  },

  // 4. Estrategia de Precios & Promociones
  {
    id: 'precios',
    label: 'Precios',
    icon: '📋',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.CATALOG_PRICES) ||
      can(PERMISSIONS.CATALOG_PRICES_PUBLIC)
  },
  {
    id: 'descuentos',
    label: 'Descuentos',
    icon: '🏷️',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.CATALOG_DISCOUNTS)
  },

  // 5. Soporte, Contacto & Marketing
  {
    id: 'soporte',
    label: 'Soporte',
    icon: '🎫',
    badgeType: 'support',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.SUPPORT_VIEW) ||
      can(PERMISSIONS.SUPPORT_CREATE) ||
      can(PERMISSIONS.SUPPORT_MANAGE)
  },
  {
    id: 'contacto',
    label: 'Contacto',
    icon: '📩',
    badgeType: 'contact',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.CONTACT_VIEW) ||
      can(PERMISSIONS.CUSTOMERS_REQUESTS_VIEW) ||
      can(PERMISSIONS.CONTACT_MANAGE)
  },
  {
    id: 'anuncios',
    label: 'Anuncios',
    icon: '📢',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.ANNOUNCEMENTS_VIEW)
  },
  {
    id: 'promo_ads',
    label: 'Publicidad',
    icon: '🖼️',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.PROMO_ADS_VIEW)
  },

  // 6. Seguridad & Gobernanza del Sistema
  {
    id: 'roles',
    label: 'Roles',
    icon: '🛡️',
    isVisible: (can, isAdmin) =>
      isAdmin ||
      can(PERMISSIONS.ROLES_VIEW) ||
      can(PERMISSIONS.ROLES_ASSIGN) ||
      can(PERMISSIONS.SYSTEM_ADMIN) ||
      can(PERMISSIONS.USERS_CREATE) ||
      can(PERMISSIONS.USERS_EDIT)
  }
];

/**
 * Obtiene los módulos permitidos para el usuario actual según sus facultades PBAC.
 */
export function getAvailableModules(can, isAdmin) {
  return NAVIGATION_MODULES.filter(mod => mod.isVisible(can, isAdmin));
}
