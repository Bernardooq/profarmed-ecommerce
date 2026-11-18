import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import useTheme from '../../hooks/useTheme';
import useSidebar from '../../hooks/useSidebar';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSun, faMoon, faUser, faShieldAlt, faBars } from '@fortawesome/free-solid-svg-icons';
import ModalEditProfile from '../users/ModalEditProfile';
import SidebarDrawer from './SidebarDrawer';
import BRAND from '../../config/brand';
import usePermissions from '../../hooks/usePermissions';

export default function Header2() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showProfileModal, setShowProfileModal] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { isSidebarOpen, toggleSidebar, closeSidebar } = useSidebar();

  const { getDashboardPath } = usePermissions();

  const handleLogout = () => { logout(); navigate('/login'); };

  const getDashboardLink = () => {
    return getDashboardPath ? getDashboardPath() : '/dashboard';
  };

  const getDashboardLabel = () => {
    if (user?.role_name) return `Panel de ${user.role_name}`;
    if (user?.is_admin || user?.role === 'admin') return 'Panel de Administración';
    return 'Panel de Control';
  };

  const isOnDashboard = location.pathname === getDashboardLink();

  return (
    <>
      <header className="header">
        <div className="header__inner">
          <div className="flex items-center gap-3">
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

            <Link to={getDashboardLink()} className="header__logo" title="Ir al Panel">
              {BRAND.logoUrl ? (
                <img src={BRAND.logoUrl} alt={BRAND.name} />
              ) : (
                BRAND.logoText
              )}
              {(user?.role_name || user?.role_slug || user?.role) && (
                <span className="badge badge--secondary ml-2" style={{ fontSize: '0.65rem', textTransform: 'uppercase' }}>
                  {user?.role_name || user?.role_slug || user?.role}
                </span>
              )}
            </Link>
          </div>

          <nav className="header__nav">
            {!isOnDashboard && (
              <Link to={getDashboardLink()} className="btn btn--primary btn--sm">
                <FontAwesomeIcon icon={faShieldAlt} className="mr-1" />
                {getDashboardLabel()}
              </Link>
            )}
          </nav>

          <div className="header__actions">
            <button className="btn btn--icon btn--ghost" onClick={toggleTheme} title={`Cambiar a modo ${theme === 'light' ? 'oscuro' : 'claro'}`}>
              <FontAwesomeIcon icon={theme === 'light' ? faMoon : faSun} />
            </button>
            <span className="text-sm">Hola, {user?.full_name || user?.username}</span>
            <button className="btn btn--icon btn--ghost" onClick={() => setShowProfileModal(true)} title="Mi Perfil">
              <FontAwesomeIcon icon={faUser} />
            </button>
            <button className="btn btn--secondary btn--sm" onClick={handleLogout}>Salir</button>
          </div>
        </div>
      </header>

      <ModalEditProfile isOpen={showProfileModal} onClose={() => setShowProfileModal(false)} />
      <SidebarDrawer isOpen={isSidebarOpen} onClose={closeSidebar} />
    </>
  );
}