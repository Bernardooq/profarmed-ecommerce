import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faCartShopping, faKey, faSun, faMoon, faBars } from '@fortawesome/free-solid-svg-icons';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import { useNavigate, Link } from 'react-router-dom';
import useTheme from '../../hooks/useTheme';
import useSidebar from '../../hooks/useSidebar';
import usePermissions from '../../hooks/usePermissions';
import useHasPromoAds from '../../hooks/useHasPromoAds';
import ModalChangePassword from '../users/ModalChangePassword';
import SidebarDrawer from './SidebarDrawer';
import BRAND from '../../config/brand';

export default function SearchBar() {
  const { isAuthenticated, user, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const { isSidebarOpen, toggleSidebar, closeSidebar } = useSidebar();
  const { isCustomer } = usePermissions();
  const hasPromoAds = useHasPromoAds(isAuthenticated && isCustomer);

  const handleLogout = () => { logout(); navigate('/'); };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchTerm.trim()) navigate(`/products?search=${encodeURIComponent(searchTerm.trim())}`);
  };

  return (
    <>
      <header className="header">
        <div className="header__inner">
          <div className="flex items-center gap-3">
            {isAuthenticated && !isSidebarOpen && (
              <button 
                className="btn btn--icon btn--ghost text-xl" 
                onClick={toggleSidebar}
                title="Mostrar menú lateral"
                aria-label="Mostrar menú lateral"
              >
                <FontAwesomeIcon icon={faBars} />
              </button>
            )}
            <Link to={isAuthenticated && isCustomer ? (hasPromoAds ? '/novedades' : '/products') : '/'} className="header__logo">
              {BRAND.logoUrl ? (
                <img src={BRAND.logoUrl} alt={BRAND.name} />
              ) : (
                BRAND.logoText
              )}
            </Link>
          </div>
          {!isSidebarOpen && (
            <nav className="header__nav">
              {isAuthenticated && isCustomer ? (
                hasPromoAds && <Link to="/novedades">Inicio</Link>
              ) : (
                <Link to="/">Inicio</Link>
              )}
              <Link to="/products">Productos</Link>
              <Link to="/orders">Mis Pedidos</Link>
              <Link to="/favorites">Favoritos</Link>
              <Link to="/profile">Perfil</Link>
            </nav>
          )}
          <form className="search-bar" onSubmit={handleSearch}>
            <input className="input" type="search" placeholder="Buscar en todo el catálogo..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
            <button className="btn btn--primary" type="submit" aria-label="Buscar">
              <FontAwesomeIcon icon={faSearch} />
            </button>
          </form>
          <div className="header__actions">
            {!isSidebarOpen && (
              <>
                <button className="btn btn--icon btn--ghost" onClick={toggleTheme} title={`Cambiar a modo ${theme === 'light' ? 'oscuro' : 'claro'}`}>
                  <FontAwesomeIcon icon={theme === 'light' ? faMoon : faSun} />
                </button>
                {isAuthenticated ? (
                  <>
                    <span className="text-sm">Hola, {user?.full_name || user?.username}</span>
                    <button className="btn btn--icon btn--ghost" onClick={() => setShowPasswordModal(true)} title="Cambiar contraseña">
                      <FontAwesomeIcon icon={faKey} />
                    </button>
                    <button className="btn btn--secondary btn--sm" onClick={handleLogout}>Salir</button>
                  </>
                ) : (
                  <Link to="/login" className="btn btn--primary btn--sm">Acceder</Link>
                )}
              </>
            )}
            {isSidebarOpen && !isAuthenticated && (
              <Link to="/login" className="btn btn--primary btn--sm">Acceder</Link>
            )}
            <Link to="/cart" className="header__cart-link" title="Mi Carrito">
              <span className="header__cart-icon-wrap">
                <FontAwesomeIcon icon={faCartShopping} />
                {itemCount > 0 && <span className="header__cart-badge">{itemCount}</span>}
              </span>
              <span className="header__cart-label">Mi Carrito</span>
            </Link>
          </div>
        </div>
      </header>

      <ModalChangePassword isOpen={showPasswordModal} onClose={() => setShowPasswordModal(false)} />
      {isAuthenticated && (
        <SidebarDrawer isOpen={isSidebarOpen} onClose={closeSidebar} />
      )}
    </>
  );
}