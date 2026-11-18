import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import useTheme from '../../hooks/useTheme';
import useSidebar from '../../hooks/useSidebar';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBars, faSun, faMoon } from '@fortawesome/free-solid-svg-icons';
import SidebarDrawer from './SidebarDrawer';
import BRAND from '../../config/brand';
import usePermissions from '../../hooks/usePermissions';
import useHasPromoAds from '../../hooks/useHasPromoAds';
import catalogService from '../../services/catalogService';

export default function Header() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const { isSidebarOpen, toggleSidebar, closeSidebar } = useSidebar();
  const { theme, toggleTheme } = useTheme();
  const { isCustomer, getDashboardPath } = usePermissions();
  const hasPromoAds = useHasPromoAds(isAuthenticated && isCustomer);
  const [hasPublicLists, setHasPublicLists] = useState(false);

  useEffect(() => {
    let isMounted = true;
    if (!isAuthenticated) {
      catalogService.getPublicPriceLists()
        .then((lists) => {
          if (isMounted && Array.isArray(lists) && lists.length > 0) {
            setHasPublicLists(true);
          } else if (isMounted) {
            setHasPublicLists(false);
          }
        })
        .catch(() => {
          if (isMounted) setHasPublicLists(false);
        });
    }
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated]);

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <>
      <header className="header">
        <div className={`header__inner${!isAuthenticated ? ' header__inner--public' : ''}`}>
          {!isAuthenticated ? (
            <>
              <nav className="header__nav">
                <Link to="/">Inicio</Link>
                {hasPublicLists && <Link to="/catalogo">Catálogo</Link>}
                <Link to="/about">Quienes somos</Link>
                <Link to="/contact">Contacto</Link>
              </nav>

              <Link to="/" className="header__logo">
                {BRAND.logoUrl ? (
                  <img src={BRAND.logoUrl} alt={BRAND.name} />
                ) : (
                  BRAND.logoText
                )}
              </Link>

              <div className="header__actions">
                <nav className="header__nav">
                  <Link to="/quiero-ser-cliente">Quiero ser cliente</Link>
                </nav>
                <button className="btn btn--icon btn--ghost" onClick={toggleTheme} title={`Cambiar a modo ${theme === 'light' ? 'oscuro' : 'claro'}`}>
                  <FontAwesomeIcon icon={theme === 'light' ? faMoon : faSun} />
                </button>
                <Link to="/login" className="btn btn--sm header__cta">Acceder</Link>
              </div>
            </>
          ) : (
            <>
              <div className="header__left">
                {!isSidebarOpen && (
                  <button
                    className="btn btn--icon btn--ghost text-xl"
                    onClick={toggleSidebar}
                    title="Mostrar menú lateral"
                    aria-label="Mostrar menú lateral"
                  >
                    <FontAwesomeIcon icon={faBars} />
                  </button>
                )}
                <Link to={isCustomer ? (hasPromoAds ? '/novedades' : '/products') : '/'} className="header__logo">
                  {BRAND.logoUrl ? (
                    <img src={BRAND.logoUrl} alt={BRAND.name} />
                  ) : (
                    BRAND.logoText
                  )}
                </Link>
              </div>

              {!isSidebarOpen && (
                <nav className="header__nav">
                  {isCustomer ? (
                    <>
                      {hasPromoAds && <Link to="/novedades">Inicio</Link>}
                      <Link to="/products">Productos</Link>
                      <Link to="/orders">Mis Pedidos</Link>
                      <Link to="/favorites">Favoritos</Link>
                      <Link to="/profile">Perfil</Link>
                    </>
                  ) : (
                    <>
                      <Link to="/">Inicio</Link>
                      <Link to={getDashboardPath()}>Panel</Link>
                      <Link to="/profile">Perfil</Link>
                    </>
                  )}
                </nav>
              )}

              <div className="header__actions">
                {!isSidebarOpen && (
                  <>
                    <button className="btn btn--icon btn--ghost" onClick={toggleTheme} title={`Cambiar a modo ${theme === 'light' ? 'oscuro' : 'claro'}`}>
                      <FontAwesomeIcon icon={theme === 'light' ? faMoon : faSun} />
                    </button>
                    <span className="text-sm">Hola, {user?.full_name || user?.username}</span>
                    <button className="btn btn--secondary btn--sm" onClick={handleLogout}>Salir</button>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </header>

      {isAuthenticated && (
        <SidebarDrawer isOpen={isSidebarOpen} onClose={closeSidebar} />
      )}
    </>
  );
}