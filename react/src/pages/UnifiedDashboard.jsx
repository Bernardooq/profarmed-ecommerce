/**
 * UnifiedDashboard.jsx
 * ====================
 * Dashboard Modular Universal Dinámico basado en Capacidades y Permisos (PBAC / RBAC).
 * 
 * Funcionalidades:
 * - Sistema 100% dinámico: Las pestañas y submódulos se auto-descubren según `usePermissions().can(permiso)`.
 * - Compatible con todos los roles: Administrador, Ventas, Marketing, Almacén, Auditor o roles personalizados del backend.
 * - Elimina la duplicación de código en vistas separadas.
 */

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePermissions } from '../hooks/usePermissions';
import { PERMISSIONS } from '../config/permissions';
import { NAVIGATION_MODULES } from '../config/navigationModules';
import useSidebar from '../hooks/useSidebar';
import Header from '../components/layout/Header2';
import Footer from '../components/layout/Footer';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorMessage from '../components/common/ErrorMessage';
import HelpGuide from '../components/common/HelpGuide';
import RoleGate from '../components/common/RoleGate';
import ItemsPerPageSelector from '../components/common/ItemsPerPageSelector';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCog } from '@fortawesome/free-solid-svg-icons';
import SystemConfigsModal from '../components/admin/SystemConfigsModal';

// Servicios de datos
import { adminService } from '../services/adminService';
import dashboardService from '../services/dashboardService';
import contactClientService from '../services/contactClientService';
import { ticketService } from '../services/ticketService';

// Submódulos UI encapsulados
import SummaryCards from '../components/sales/SummaryCards';
import AllOrders from '../components/orders/AllOrders';
import SalesReport from '../components/sales/SalesReport';
import ClientManagement from '../components/admin/ClientManagement';
import SalesTeamManagement from '../components/admin/SalesTeamManagement';
import RolesManagement from '../components/admin/RolesManagement';
import InventoryManager from '../components/products/InventoryManager';
import CategoryManagement from '../components/products/CategoryManagement';
import PriceListManager from '../components/admin/PriceListManager';
import DiscountsManager from '../components/admin/DiscountsManager';
import TicketDashboard from '../components/tickets/TicketDashboard';
import MyTickets from '../components/tickets/MyTickets';
import ContactClientPanel from '../components/admin/ContactClientPanel';
import AnnouncementsPanel from '../components/admin/AnnouncementsPanel';
import PromoAdsPanel from '../components/admin/PromoAdsPanel';
import WarehouseAdminSection from '../components/warehouse/WarehouseAdminSection';
import WarehouseOperatorSection from '../components/warehouse/WarehouseOperatorSection';
import WarehouseLaserStation from '../components/warehouse/WarehouseLaserStation';

// Documentación de ayuda unificada por pestaña
const UNIFIED_HELP_CONTENT = {
  dashboard: {
    title: "Documentación: Dashboard Global",
    description: "Panel de control con indicadores críticos de negocio y métricas de venta.",
    items: [
      "Ventas: Gráfica de ingresos mensuales y comparativa de rendimientos.",
      "Pedidos: Conteo de pedidos pendientes, en camino y entregados.",
      "Inventario: Alerta de productos con stock bajo o agotados.",
      "Acceso Rápido: Indicadores visuales de estados operativos."
    ]
  },
  reportes: {
    title: "Documentación: Reportes de Ventas",
    description: "Herramienta de análisis detallado del rendimiento comercial.",
    items: [
      "Filtros: Consulta por rango de fechas específico.",
      "Métricas: Visualiza total de ventas y margen bruto.",
      "Exportación: Genera reportes en formato imprimible/PDF."
    ]
  },
  pedidos: {
    title: "Documentación: Control y Seguimiento de Pedidos",
    description: "Gestión del flujo completo de órdenes de compra.",
    items: [
      "Validación: Tu equipo es responsable de validar los pedidos una vez confirmado el pago.",
      "Visibilidad: Consulta pedidos según tu asignación o grupo de ventas.",
      "Estados: Filtra por pedidos pendientes, pagados o entregados.",
      "Logística: Asignación a vendedores o choferes para la entrega física."
    ]
  },
  almacen: {
    title: "Documentación: Módulo de Bodega & Logística",
    description: "Gestión de cola FIFO, surtido de splits, empaque y sellos inviolables.",
    items: [
      "Cola FIFO: Visualiza pedidos pendientes ordenados por tiempo de espera.",
      "Supervisión: Monitorea el progreso de recolección de cada split física.",
      "Auditoría Forense: Consulta el desglose pericial por partida con diferencias de inventario.",
      "Sellos: Revisa el folio inviolable asignado a cada split al momento del precintado."
    ]
  },
  inventario: {
    title: "Documentación: Inventario y Catálogo",
    description: "Gestión y consulta del catálogo maestro de productos y existencias.",
    items: [
      "Búsqueda: Localiza productos por ID, Nombre o Código de Barras.",
      "Stock: Monitorea existencias reales sincronizadas con el sistema base.",
      "Categorías: Organiza el catálogo para facilitar la navegación."
    ]
  },
  clientes: {
    title: "Documentación: Gestión de Clientes",
    description: "Administración centralizada de la base de datos de clientes.",
    items: [
      "Listado: Búsqueda y filtrado de clientes registrados.",
      "Grupos: Cada cliente pertenece a su respectivo grupo comercial.",
      "Precios: Asigna la lista de precios correspondiente a cada cliente."
    ]
  },
  equipo: {
    title: "Documentación: Equipo y Grupos Comerciales",
    description: "Gestión de colaboradores por rol operativo y estructura de grupos de venta.",
    items: [
      "Roles Dinámicos: Visualiza y filtra al personal según su asignación de rol.",
      "Grupos: Supervisa y administra grupos comerciales y asignación de miembros.",
      "Permisos: Las acciones de creación y edición se habilitan según tus facultades PBAC."
    ]
  },
  roles: {
    title: "Documentación: Roles y Permisos (RBAC / PBAC)",
    description: "Configuración centralizada de roles y asignación de capacidades del sistema.",
    items: [
      "Roles del Sistema: Roles nativos protegidos con facultades globales.",
      "Roles Personalizados: Crea perfiles operativos a la medida según las necesidades del negocio.",
      "Matriz Granular: Configura permisos específicos de pedidos, clientes, inventario y más."
    ]
  },
  precios: {
    title: "Documentación: Listas de Precios",
    description: "Configuración de márgenes de ganancia por perfil de cliente.",
    items: [
      "Markup: Define el % de ganancia sobre el precio base de costo.",
      "Listas: Crea diferentes perfiles (Mayoreo, Público, Especial, etc.)."
    ]
  },
  descuentos: {
    title: "Documentación: Descuentos y Promociones",
    description: "Configuración y control de descuentos por porcentaje aplicables al catálogo.",
    items: [
      "Ámbito General: Aplica directamente sobre el precio base.",
      "Por Lista: Aplica exclusivamente a clientes de una lista específica."
    ]
  },
  soporte: {
    title: "Documentación: Sistema de Soporte",
    description: "Canal de comunicación para reporte y resolución de incidencias.",
    items: [
      "Tickets: Visualiza problemas reportados por clientes o equipo de campo.",
      "Resolución: Responde y da seguimiento hasta el cierre del ticket."
    ]
  },
  contacto: {
    title: "Documentación: Contacto y Solicitudes",
    description: "Gestión de los mensajes directos y solicitudes de alta de clientes.",
    items: [
      "Mensajes: Revisa y gestiona mensajes de contacto web.",
      "Solicitudes: Descarga los PDF fiscales que suben los prospectos."
    ]
  },
  anuncios: {
    title: "Documentación: Anuncios y Promociones",
    description: "Gestión de material promocional y comunicados para la plataforma.",
    items: [
      "Tipos: Banners emergentes (pop-ups), stories e indicadores inferiores.",
      "Vigencia: Define cuándo se activan y expiran los anuncios automáticamente."
    ]
  },
  promo_ads: {
    title: "Documentación: Publicidad de Inicio",
    description: "Configuración de la página de inicio B2B por bloques (1 a 4 columnas) y carruseles.",
    items: [
      "Visibilidad Automática: Si hay secciones activas, el cliente entra aquí primero; si no hay, entra directo al Catálogo.",
      "Imágenes Responsivas: Sube variantes Desktop, Tablet y Móvil por anuncio con vista previa en vivo."
    ]
  }
};

export default function UnifiedDashboard() {
  const { user } = useAuth();
  const { can, isAdmin } = usePermissions();
  const { isSidebarOpen } = useSidebar();
  const [searchParams, setSearchParams] = useSearchParams();

  // Estados de datos
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Badges y conteos
  const [pendingContactCount, setPendingContactCount] = useState(0);
  const [pendingClientCount, setPendingClientCount] = useState(0);
  const [pendingTicketsCount, setPendingTicketsCount] = useState(0);
  const [isConfigsModalOpen, setIsConfigsModalOpen] = useState(false);

  // =========================================================
  // CATÁLOGO MAESTRO DE MÓDULOS DEL DASHBOARD DINÁMICO
  // Cada módulo declara su permiso padre para auto-descubrimiento
  // =========================================================
  // =========================================================
  // CATÁLOGO MAESTRO UNIFICADO DE MÓDULOS DEL DASHBOARD DINÁMICO
  // Auto-descubrimiento en O(1) sincronizado con el menú lateral
  // =========================================================
  const availableTabs = useMemo(() => {
    return NAVIGATION_MODULES.filter(mod => mod.isVisible(can, isAdmin));
  }, [can, isAdmin]);

  // Selección de pestaña activa inicial (soporta alias legacy como 'vendedores' y 'grupos')
  const requestedTabRaw = searchParams.get('tab');
  const requestedTab = requestedTabRaw === 'vendedores' || requestedTabRaw === 'grupos' ? 'equipo' : requestedTabRaw;
  const defaultTab = availableTabs[0]?.id || 'dashboard';
  const [activeTab, setActiveTab] = useState(() => {
    if (requestedTab && availableTabs.some(t => t.id === requestedTab)) {
      return requestedTab;
    }
    return defaultTab;
  });

  // Sincronizar tab desde URL si cambia
  useEffect(() => {
    const rawFromUrl = searchParams.get('tab');
    const tabFromUrl = rawFromUrl === 'vendedores' || rawFromUrl === 'grupos' ? 'equipo' : rawFromUrl;
    if (tabFromUrl && tabFromUrl !== activeTab && availableTabs.some(t => t.id === tabFromUrl)) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams, availableTabs, activeTab]);

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setSearchParams({ tab: tabId });
  };

  // Badges y conteos en segundo plano (no bloqueantes)
  useEffect(() => {
    if (user) {
      loadPendingCounts();
    }
  }, [user]);

  // Carga diferida de métricas del dashboard cuando la pestaña activa es 'dashboard' y cuenta con permisos
  useEffect(() => {
    if (user && activeTab === 'dashboard' && (isAdmin || can(PERMISSIONS.REPORTS_VIEW)) && !summary) {
      loadDashboardData();
    }
  }, [user, activeTab, summary, can, isAdmin]);

  const loadPendingCounts = async () => {
    try {
      const promises = [
        ticketService.getTickets({ status_filter: 'open', limit: 5 }).catch(() => ({ items: [] })),
        ticketService.getTickets({ status_filter: 'in_progress', limit: 5 }).catch(() => ({ items: [] })),
        ticketService.getTickets({ status_filter: 'escalated', limit: 5 }).catch(() => ({ items: [] }))
      ];

      if (can('customers.edit') || isAdmin) {
        promises.push(contactClientService.getContactMessages({ status_filter: 'pending', limit: 5 }).catch(() => []));
        promises.push(contactClientService.getClientRequests({ status: 'pending', limit: 5 }).catch(() => []));
      }

      const results = await Promise.all(promises);
      const [openTickets, inProgressTickets, escalatedTickets, contactMsgs, clientReqs] = results;

      const totalTickets = (openTickets?.items || []).length + (inProgressTickets?.items || []).length + (escalatedTickets?.items || []).length;
      setPendingTicketsCount(totalTickets >= 5 ? '5+' : totalTickets);

      if (contactMsgs) {
        setPendingContactCount(contactMsgs.length >= 5 ? '5+' : contactMsgs.length);
      }
      if (clientReqs) {
        setPendingClientCount(clientReqs.length >= 5 ? '5+' : clientReqs.length);
      }
    } catch (err) {
      console.error('Error loading pending notification counts:', err);
    }
  };

  const loadDashboardData = async () => {
    if (!isAdmin && !can(PERMISSIONS.REPORTS_VIEW)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Carga atómica y concurrente desacoplada por micro-capacidades PBAC
      const promises = [];

      // 1. Finanzas y Ventas (Exclusivo con permiso financiero o admin)
      if (isAdmin || can(PERMISSIONS.REPORTS_FINANCIAL)) {
        promises.push(adminService.getDashboardFinanceStats().catch(() => null));
      }

      // 2. Gestión de Pedidos (Global para admin/supervisor, grupal para operativo)
      if (isAdmin || can(PERMISSIONS.ORDERS_VIEW) || can(PERMISSIONS.ORDERS_GROUP_VIEW) || can(PERMISSIONS.ORDERS_VIEW_ALL)) {
        promises.push(adminService.getDashboardOrderStats().catch(() => null));
      }

      // 3. Personal y Clientes
      if (isAdmin || can(PERMISSIONS.USERS_VIEW) || can(PERMISSIONS.CUSTOMERS_VIEW) || can(PERMISSIONS.CUSTOMERS_VIEW_ALL)) {
        promises.push(adminService.getDashboardUsersCustomersStats().catch(() => null));
      }

      // 4. Inventario y Catálogo
      if (isAdmin || can(PERMISSIONS.CATALOG_VIEW)) {
        promises.push(adminService.getDashboardInventoryStats().catch(() => null));
      }

      const results = await Promise.allSettled(promises);
      const combined = {};

      results.forEach(res => {
        if (res.status === 'fulfilled' && res.value && typeof res.value === 'object') {
          Object.assign(combined, res.value);
        }
      });

      // Fallback para roles comerciales si la carga desacoplada no arrojó métricas y posee reports.view
      if (Object.keys(combined).length === 0 && (can(PERMISSIONS.ORDERS_VIEW) || can(PERMISSIONS.GROUPS_VIEW))) {
        const fallback = await dashboardService.getOperationalStats().catch(() => null);
        if (fallback) Object.assign(combined, fallback);
      }

      setSummary(combined);
    } catch (err) {
      setError('No se pudieron obtener las métricas del servidor. Intenta de nuevo.');
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // RENDERIZADO DINÁMICO DEL CONTENIDO POR PESTAÑA
  // =========================================================
  const renderTabContent = () => {
    switch (activeTab) {
      case 'dashboard':
        if (!isAdmin && !can(PERMISSIONS.REPORTS_VIEW)) {
          return (
            <div className="empty-state" style={{ padding: '3rem', textAlign: 'center' }}>
              <div className="empty-state__icon" style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</div>
              <h3 className="empty-state__title">Acceso Restringido</h3>
              <p className="empty-state__text">Tu rol no cuenta con el permiso 'reports.view' para consultar el panel de control o analítica.</p>
            </div>
          );
        }
        if (loading || (!summary && !error)) {
          return (
            <div className="py-8">
              <LoadingSpinner message="Calculando métricas del panel de control..." />
            </div>
          );
        }
        return summary && Object.keys(summary).length > 0 ? (
          <SummaryCards summary={summary} isAdmin={isAdmin} />
        ) : (
          <div className="empty-state">
            <div className="empty-state__icon">📊</div>
            <h3 className="empty-state__title">Panel de Control</h3>
            <p className="empty-state__text">No hay métricas disponibles para tu perfil o asignación comercial actual.</p>
          </div>
        );

      case 'reportes':
        if (!isAdmin && !can(PERMISSIONS.REPORTS_SALES) && !can(PERMISSIONS.REPORTS_FINANCIAL)) {
          return (
            <div className="empty-state" style={{ padding: '3rem', textAlign: 'center' }}>
              <div className="empty-state__icon" style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</div>
              <h3 className="empty-state__title">Acceso Restringido</h3>
              <p className="empty-state__text">Tu rol no cuenta con los permisos 'reports.sales' o 'reports.financial' para consultar la sección de reportes.</p>
            </div>
          );
        }
        return <SalesReport />;

      case 'clientes':
        return <ClientManagement />;

      case 'equipo':
      case 'vendedores':
      case 'grupos':
        return <SalesTeamManagement />;

      case 'roles':
        return <RolesManagement />;

      case 'pedidos':
        return <AllOrders />;

      case 'inventario':
        if (!isAdmin && !can(PERMISSIONS.CATALOG_VIEW)) {
          return (
            <div className="empty-state" style={{ padding: '3rem', textAlign: 'center' }}>
              <div className="empty-state__icon" style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</div>
              <h3 className="empty-state__title">Acceso Restringido</h3>
              <p className="empty-state__text">Tu rol no cuenta con el permiso 'catalog.view' para consultar el inventario de productos.</p>
            </div>
          );
        }
        return (
          <>
            <InventoryManager />
            {can(PERMISSIONS.CATALOG_CATEGORIES) && <CategoryManagement />}
          </>
        );

      case 'almacen':
        if (isAdmin || can(PERMISSIONS.WAREHOUSE_SUPERVISOR)) {
          return <WarehouseAdminSection isSupervisor={true} />;
        }
        return <WarehouseOperatorSection />;

      case 'precios':
        return <PriceListManager />;

      case 'descuentos':
        return <DiscountsManager />;

      case 'soporte':
        if (can(PERMISSIONS.SUPPORT_MANAGE) || isAdmin) {
          return <TicketDashboard refreshCounts={loadPendingCounts} />;
        }
        return <MyTickets />;

      case 'contacto':
        return <ContactClientPanel refreshCounts={loadPendingCounts} />;

      case 'anuncios':
        return <AnnouncementsPanel />;

      case 'promo_ads':
        return <PromoAdsPanel />;

      default:
        return (
          <div className="empty-state">
            <div className="empty-state__icon">📋</div>
            <h3 className="empty-state__title">Módulo Seleccionado</h3>
            <p className="empty-state__text">Por favor selecciona una pestaña disponible en la barra superior.</p>
          </div>
        );
    }
  };

  // Título dinámico según el nombre del rol asignado o capacidades del usuario
  const dashboardTitle = user?.role_name
    ? `Panel de ${user.role_name}`
    : isAdmin
    ? 'Panel de Administración'
    : 'Panel de Control';

  return (
    <div className="page">
      <Header />

      <main className="dashboard-layout">
        <div className="dashboard-layout__container">
          <div className="dashboard-layout__header">
            <div>
              <h1 className="dashboard-layout__greeting">{dashboardTitle}</h1>
              <span className="text-sm text-muted">
                Bienvenido, <strong>{user?.full_name || user?.username}</strong>
              </span>
            </div>
            <div className="dashboard-layout__controls">
              <ItemsPerPageSelector />
              {can(PERMISSIONS.SYSTEM_ADMIN) && (
                <button
                  type="button"
                  className="btn btn--secondary dashboard-layout__config-btn"
                  onClick={() => setIsConfigsModalOpen(true)}
                  title="Configuraciones globales del sistema (system_configs)"
                >
                  <FontAwesomeIcon icon={faCog} className="text-primary" />
                  <span className="dashboard-layout__config-btn-text">Configuración</span>
                </button>
              )}
            </div>
          </div>

          {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

          {/* Navegación por pestañas dinámicas */}
          <div className="dashboard-layout__tabs">
            {!isSidebarOpen && (
              <nav className="dashboard-layout__tabs-nav">
                {availableTabs.map((tab) => {
                  const isContactTab = tab.id === 'contacto';
                  const isSupportTab = tab.id === 'soporte';

                  return (
                    <button
                      key={tab.id}
                      type="button"
                      className={`dashboard-layout__tab ${activeTab === tab.id ? 'dashboard-layout__tab--active' : ''}`}
                      onClick={() => handleTabChange(tab.id)}
                    >
                      <span className="dashboard-layout__tab-icon">{tab.icon}</span>
                      <span className="dashboard-layout__tab-label">{tab.label}</span>

                      {/* Notificaciones dinámicas de contador */}
                      {isContactTab && (pendingContactCount > 0 || pendingClientCount > 0) && (
                        <div className="tab-badge-container">
                          {pendingContactCount > 0 && (
                            <span className="tab-badge tab-badge--contact" title={`${pendingContactCount} mensajes de contacto pendientes`}>
                              {pendingContactCount}
                            </span>
                          )}
                          {pendingClientCount > 0 && (
                            <span className="tab-badge tab-badge--client" title={`${pendingClientCount} solicitudes de cliente pendientes`}>
                              {pendingClientCount}
                            </span>
                          )}
                        </div>
                      )}

                      {isSupportTab && pendingTicketsCount > 0 && (
                        <span className="tab-badge tab-badge--support" title={`${pendingTicketsCount} tickets de soporte pendientes`}>
                          {pendingTicketsCount}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>
            )}

            {/* Contenido activo del submódulo */}
            <div className="dashboard-layout__tabs-content">
              {UNIFIED_HELP_CONTENT[activeTab] && (
                <HelpGuide
                  title={UNIFIED_HELP_CONTENT[activeTab].title}
                  description={UNIFIED_HELP_CONTENT[activeTab].description}
                  items={UNIFIED_HELP_CONTENT[activeTab].items}
                />
              )}
              {renderTabContent()}
            </div>
          </div>
        </div>

        {/* Modal de Configuraciones Globales del Sistema (system.admin) */}
        {can(PERMISSIONS.SYSTEM_ADMIN) && (
          <SystemConfigsModal
            isOpen={isConfigsModalOpen}
            onClose={() => setIsConfigsModalOpen(false)}
          />
        )}
      </main>

      <Footer />
    </div>
  );
}
