import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTimes, faHome, faBoxOpen, faTag, faShoppingBag,
  faStar, faUser, faKey, faHeadset, faSignOutAlt, faSignInAlt,
  faShieldAlt, faSun, faMoon, faCartShopping, faBullhorn,
  faUsers, faUserTie, faBoxes, faChartLine, faTags, faFileAlt, faEnvelope,
  faClipboardList, faFileUpload, faFileDownload, faChevronDown, faChevronUp, faBolt
} from '@fortawesome/free-solid-svg-icons';
import useTheme from '../../hooks/useTheme';
import ModalChangePassword from '../users/ModalChangePassword';
import contactClientService from '../../services/contactClientService';
import ticketService from '../../services/ticketService';
import catalogService from '../../services/catalogService';
import BRAND from '../../config/brand';
import usePermissions from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import { NAVIGATION_MODULES } from '../../config/navigationModules';
import useHasPromoAds from '../../hooks/useHasPromoAds';

export default function SidebarDrawer({ isOpen, onClose }) {
  const { user, isAuthenticated, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { can, isAdmin, isCustomer, getDashboardPath: resolveDashboardPath } = usePermissions();
  const hasPromoAds = useHasPromoAds(isAuthenticated && isCustomer);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showOffersModal, setShowOffersModal] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(true);
  const [exportingCatalog, setExportingCatalog] = useState(false);
  const [pendingContactCount, setPendingContactCount] = useState(0);
  const [pendingClientCount, setPendingClientCount] = useState(0);
  const [pendingTicketsCount, setPendingTicketsCount] = useState(0);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen && window.innerWidth < 1024) {
        onClose();
      }
    };
    if (isOpen && window.innerWidth < 1024) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    let isMounted = true;

    const loadCounts = async () => {
      try {
        const promises = [
          ticketService.getTickets({ status_filter: 'open', limit: 5 }).catch(() => ({ items: [] })),
          ticketService.getTickets({ status_filter: 'in_progress', limit: 5 }).catch(() => ({ items: [] }))
        ];

        // Si puede gestionar soporte o supervisar, también contar escalados
        if (can(PERMISSIONS.SUPPORT_MANAGE)) {
          promises.push(ticketService.getTickets({ status_filter: 'escalated', limit: 5 }).catch(() => ({ items: [] })));
        }

        // Si puede ver solicitudes de clientes o mensajes de contacto
        if (can(PERMISSIONS.CUSTOMERS_REQUESTS_VIEW) || can(PERMISSIONS.CONTACT_VIEW)) {
          promises.push(contactClientService.getContactMessages({ status_filter: 'pending', limit: 5 }).catch(() => []));
          promises.push(contactClientService.getClientRequests({ status: 'pending', limit: 5 }).catch(() => []));
        }

        const results = await Promise.all(promises);
        if (!isMounted) return;

        const openTickets = results[0];
        const inProgressTickets = results[1];
        const escalatedTickets = can(PERMISSIONS.SUPPORT_MANAGE) ? results[2] : { items: [] };
        const hasExtraQueries = can(PERMISSIONS.CUSTOMERS_REQUESTS_VIEW) || can(PERMISSIONS.CONTACT_VIEW);
        const contactMsgs = hasExtraQueries ? (can(PERMISSIONS.SUPPORT_MANAGE) ? results[3] : results[2]) : [];
        const clientReqs = hasExtraQueries ? (can(PERMISSIONS.SUPPORT_MANAGE) ? results[4] : results[3]) : [];

        const totalTickets = (openTickets?.items || []).length + (inProgressTickets?.items || []).length + (escalatedTickets?.items || []).length;
        setPendingTicketsCount(totalTickets >= 5 ? '5+' : totalTickets);

        if (contactMsgs) {
          const contactCount = Array.isArray(contactMsgs) ? contactMsgs.length : 0;
          setPendingContactCount(contactCount >= 5 ? '5+' : contactCount);
        }

        if (clientReqs) {
          const clientCount = Array.isArray(clientReqs) ? clientReqs.length : 0;
          setPendingClientCount(clientCount >= 5 ? '5+' : clientCount);
        }
      } catch (err) {
        console.error('Error loading pending counts for sidebar:', err);
      }
    };

    loadCounts();
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, user?.role]);

  if (!isOpen) return null;

  const handleLogout = () => {
    onClose();
    logout();
    navigate('/login');
  };

  const handleNav = (path) => {
    if (window.innerWidth < 1024) {
      onClose();
    }
    navigate(path);
  };

  const handleExportCatalog = async () => {
    try {
      setExportingCatalog(true);
      await catalogService.exportProducts();
    } catch (err) {
      console.error('Error al descargar catálogo Excel:', err);
    } finally {
      setExportingCatalog(false);
    }
  };

  const handleBackdropClick = () => {
    if (window.innerWidth < 1024) {
      onClose();
    }
  };

  const getDashboardPath = () => {
    return resolveDashboardPath ? resolveDashboardPath() : '/dashboard';
  };

  const getUserRoleLabel = () => {
    return user?.role_name || (isAdmin ? 'Administrador' : 'Usuario');
  };

  const isTabActive = (basePath, tabId, defaultTab) => {
    if (location.pathname !== basePath) return false;
    const currentTab = new URLSearchParams(location.search).get('tab') || defaultTab;
    return currentTab === tabId;
  };

  const isPathActive = (path) => {
    return location.pathname === path;
  };

  const isCurrentPath = isPathActive;

  return (
    <>
      <div className="sidebar-drawer-overlay" onClick={handleBackdropClick}>
        <aside className="sidebar-drawer" onClick={(e) => e.stopPropagation()}>
          {/* Drawer Header */}
          <div className="sidebar-drawer__header">
            <div className="sidebar-drawer__brand" onClick={() => handleNav(isAuthenticated && !isCustomer ? getDashboardPath() : '/')}>
              {BRAND.logoUrl ? (
                <img src={BRAND.logoUrl} alt={BRAND.name} style={{ maxHeight: '32px', maxWidth: '140px', objectFit: 'contain' }} />
              ) : (
                <span className="sidebar-drawer__logo-text">{BRAND.logoText.toUpperCase()}</span>
              )}
              <span className="sidebar-drawer__badge">B2B</span>
            </div>
            <button className="sidebar-drawer__close" onClick={onClose} aria-label="Ocultar menú lateral" title="Ocultar menú lateral">
              <FontAwesomeIcon icon={faTimes} />
            </button>
          </div>

          {/* User Profile Card */}
          {isAuthenticated ? (
            <div className="sidebar-drawer__user-card" onClick={() => handleNav('/profile')}>
              <div className="sidebar-drawer__avatar">
                <FontAwesomeIcon icon={faUser} />
              </div>
              <div className="sidebar-drawer__user-info">
                <div className="sidebar-drawer__username">{user?.full_name || user?.username}</div>
                <div className="sidebar-drawer__user-role">{getUserRoleLabel()}</div>
              </div>
            </div>
          ) : (
            <div className="sidebar-drawer__user-card" onClick={() => handleNav('/login')}>
              <div className="sidebar-drawer__avatar">
                <FontAwesomeIcon icon={faSignInAlt} />
              </div>
              <div className="sidebar-drawer__user-info">
                <div className="sidebar-drawer__username">Bienvenido a {BRAND.name}</div>
                <div className="sidebar-drawer__user-role">Inicia sesión para ordenar</div>
              </div>
            </div>
          )}

          {/* Navigation Items by Role */}
          <nav className="sidebar-drawer__nav">

            {/* ========================================================= */}
            {/* SECCIONES OPERATIVAS Y ADMINISTRATIVAS (PBAC DINÁMICO)    */}
            {/* ========================================================= */}
            {isAuthenticated && !isCustomer && (
              <div className="sidebar-drawer__group">
                <span className="sidebar-drawer__section-label">Panel de Control</span>

                {NAVIGATION_MODULES.filter(mod => mod.isVisible(can, isAdmin)).map(mod => {
                  const isContact = mod.id === 'contacto';
                  const isSupport = mod.id === 'soporte';

                  return (
                    <button
                      key={mod.id}
                      className={`sidebar-drawer__item ${isTabActive('/dashboard', mod.id, 'dashboard') ? 'sidebar-drawer__item--active' : ''}`}
                      onClick={() => handleNav(`/dashboard?tab=${mod.id}`)}
                    >
                      <span className="sidebar-drawer__icon-emoji">{mod.icon}</span>
                      <span>{mod.label}</span>

                      {/* Notificaciones dinámicas de contadores */}
                      {isSupport && pendingTicketsCount > 0 && (
                        <span className="tab-badge tab-badge--support ml-auto" title={`${pendingTicketsCount} tickets pendientes`}>
                          {pendingTicketsCount}
                        </span>
                      )}

                      {isContact && (pendingContactCount > 0 || pendingClientCount > 0) && (
                        <div className="tab-badge-container ml-auto">
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
                    </button>
                  );
                })}
              </div>
            )}

            {/* ========================================================= */}
            {/* 4. SECCIONES PARA CLIENTE O PÚBLICO                       */}
            {/* ========================================================= */}
            {(!isAuthenticated || isCustomer) && (
              <>
                <div className="sidebar-drawer__group">
                  <span className="sidebar-drawer__section-label">Catálogo & Compras</span>

                  {hasPromoAds && (
                    <button className={`sidebar-drawer__item ${isCurrentPath('/novedades') ? 'sidebar-drawer__item--active' : ''}`} onClick={() => handleNav('/novedades')}>
                      <FontAwesomeIcon icon={faBullhorn} className="sidebar-drawer__icon" />
                      <span>Inicio & Novedades</span>
                    </button>
                  )}

                  {/* Desplegable: Captura de Pedidos */}
                  <div className="sidebar-drawer__dropdown">
                    <button
                      type="button"
                      className={`sidebar-drawer__item sidebar-drawer__dropdown-trigger ${captureOpen ? 'is-open' : ''}`}
                      onClick={() => setCaptureOpen(prev => !prev)}
                    >
                      <FontAwesomeIcon icon={faClipboardList} className="sidebar-drawer__icon" />
                      <span>Captura de Pedidos</span>
                      <FontAwesomeIcon icon={captureOpen ? faChevronUp : faChevronDown} className="sidebar-drawer__chevron" />
                    </button>

                    {captureOpen && (
                      <div className="sidebar-drawer__submenu">
                        <button
                          className={`sidebar-drawer__subitem ${isCurrentPath('/products') && !location.search.includes('sort=newest') ? 'sidebar-drawer__item--active' : ''}`}
                          onClick={() => handleNav('/products')}
                        >
                          <FontAwesomeIcon icon={faBoxOpen} className="sidebar-drawer__icon" />
                          <span>Catálogo de Productos</span>
                        </button>

                        <button
                          className={`sidebar-drawer__subitem ${isCurrentPath('/cart') ? 'sidebar-drawer__item--active' : ''}`}
                          onClick={() => handleNav('/cart')}
                        >
                          <FontAwesomeIcon icon={faFileUpload} className="sidebar-drawer__icon" />
                          <span>Cargar Pedido con Excel</span>
                        </button>

                        {isCustomer && (
                          <button
                            className="sidebar-drawer__subitem"
                            onClick={handleExportCatalog}
                            disabled={exportingCatalog}
                          >
                            <FontAwesomeIcon icon={faFileDownload} className="sidebar-drawer__icon" />
                            <span>{exportingCatalog ? 'Descargando...' : 'Descargar Catálogo Excel'}</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  <button className={`sidebar-drawer__item ${isCurrentPath('/cart') ? 'sidebar-drawer__item--active' : ''}`} onClick={() => handleNav('/cart')}>
                    <FontAwesomeIcon icon={faCartShopping} className="sidebar-drawer__icon" />
                    <span>Mi Carrito</span>
                    {itemCount > 0 && (
                      <span className="sidebar-drawer__badge-count">{itemCount}</span>
                    )}
                  </button>

                  <button className={`sidebar-drawer__item ${isCurrentPath('/orders') ? 'sidebar-drawer__item--active' : ''}`} onClick={() => handleNav('/orders')}>
                    <FontAwesomeIcon icon={faShoppingBag} className="sidebar-drawer__icon" />
                    <span>Estatus de Pedidos</span>
                  </button>

                  <button
                    className={`sidebar-drawer__item ${isCurrentPath('/products') && location.search.includes('sort=newest') ? 'sidebar-drawer__item--active' : ''}`}
                    onClick={() => handleNav('/products?sort=newest')}
                  >
                    <FontAwesomeIcon icon={faBolt} className="sidebar-drawer__icon" />
                    <span>Productos Nuevos</span>
                  </button>

                  <button className={`sidebar-drawer__item ${isCurrentPath('/favorites') ? 'sidebar-drawer__item--active' : ''}`} onClick={() => handleNav('/favorites')}>
                    <FontAwesomeIcon icon={faStar} className="sidebar-drawer__icon" />
                    <span>Mis Listas Favoritas</span>
                  </button>

                  <button
                    className={`sidebar-drawer__item sidebar-drawer__item--offers ${isCurrentPath('/promos') ? 'sidebar-drawer__item--active' : ''}`}
                    onClick={() => handleNav('/promos')}
                  >
                    <FontAwesomeIcon icon={faTag} className="sidebar-drawer__icon sidebar-drawer__icon--accent" />
                    <span>Ofertas & Promos</span>
                    <span className="badge badge--discount badge--sm">
                      PROMOS
                    </span>
                  </button>
                </div>

                <div className="sidebar-drawer__group">
                  <span className="sidebar-drawer__section-label">Cuenta & Soporte</span>

                  <button className={`sidebar-drawer__item ${isCurrentPath('/profile') ? 'sidebar-drawer__item--active' : ''}`} onClick={() => handleNav('/profile')}>
                    <FontAwesomeIcon icon={faUser} className="sidebar-drawer__icon" />
                    <span>Mi Perfil</span>
                  </button>

                  <button className={`sidebar-drawer__item ${isCurrentPath('/support') ? 'sidebar-drawer__item--active' : ''}`} onClick={() => handleNav('/support')}>
                    <FontAwesomeIcon icon={faHeadset} className="sidebar-drawer__icon" />
                    <span>Soporte & Tickets</span>
                    {pendingTicketsCount > 0 && (
                      <span className="tab-badge tab-badge--support ml-auto" title={`${pendingTicketsCount} tickets abiertos`}>
                        {pendingTicketsCount}
                      </span>
                    )}
                  </button>

                  <button className={`sidebar-drawer__item ${isCurrentPath('/') ? 'sidebar-drawer__item--active' : ''}`} onClick={() => handleNav('/')}>
                    <FontAwesomeIcon icon={faHome} className="sidebar-drawer__icon" />
                    <span>Portal Web Público</span>
                  </button>
                </div>
              </>
            )}

            {/* ========================================================= */}
            {/* 5. PREFERENCIAS & CUENTA (GLOBAL)                         */}
            {/* ========================================================= */}
            <div className="sidebar-drawer__group">
              <span className="sidebar-drawer__section-label">Ajustes</span>

              {isAuthenticated && (
                <button className="sidebar-drawer__item" onClick={() => setShowPasswordModal(true)}>
                  <FontAwesomeIcon icon={faKey} className="sidebar-drawer__icon" />
                  <span>Cambiar Contraseña</span>
                </button>
              )}

              <button className="sidebar-drawer__item" onClick={toggleTheme}>
                <FontAwesomeIcon icon={theme === 'light' ? faMoon : faSun} className="sidebar-drawer__icon" />
                <span>Modo {theme === 'light' ? 'Oscuro' : 'Claro'}</span>
              </button>
            </div>
          </nav>

          {/* Drawer Footer */}
          <div className="sidebar-drawer__footer">
            {isAuthenticated ? (
              <button className="sidebar-drawer__logout-btn" onClick={handleLogout}>
                <FontAwesomeIcon icon={faSignOutAlt} />
                <span>Cerrar Sesión</span>
              </button>
            ) : (
              <button className="sidebar-drawer__login-btn" onClick={() => handleNav('/login')}>
                <FontAwesomeIcon icon={faSignInAlt} className="mr-2" />
                <span>Iniciar Sesión</span>
              </button>
            )}
          </div>
        </aside>
      </div>

      {/* Modal Cambiar Contraseña */}
      <ModalChangePassword isOpen={showPasswordModal} onClose={() => setShowPasswordModal(false)} />

      {/* Modal Próximamente Ofertas & Promociones */}
      {showOffersModal && (
        <div className="modal-overlay" onClick={() => setShowOffersModal(false)}>
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="d-flex align-items-center gap-2">
                <FontAwesomeIcon icon={faTag} className="text-primary" />
                Ofertas & Promociones B2B
              </h3>
              <button
                type="button"
                className="modal__close"
                onClick={() => setShowOffersModal(false)}
                aria-label="Cerrar modal"
              >
                &times;
              </button>
            </div>
            <div className="modal__body text-center p-6">
              <div className="sidebar-drawer__soon-icon-wrap">
                <FontAwesomeIcon icon={faBullhorn} />
              </div>
              <h4 className="text-lg font-bold mb-1">Próximamente</h4>
            </div>
            <div className="modal__footer">
              <button
                type="button"
                className="btn btn--primary w-full"
                onClick={() => setShowOffersModal(false)}
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
