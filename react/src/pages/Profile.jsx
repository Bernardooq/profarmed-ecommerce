/**
 * Profile.jsx
 * ===========
 * Página de perfil del cliente en Profarmed
 * 
 * Funcionalidades:
 * - Ver información del usuario y del negocio
 * - Preferencias de Notificaciones de pedidos y envíos
 * - Acceso directo a Mis Pedidos
 * 
 * Permisos: Clientes autenticados
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePermissions } from '../hooks/usePermissions';
import SearchBar from '../components/layout/SearchBar';
import Footer from '../components/layout/Footer';
import HelpGuide from '../components/common/HelpGuide';
import { userService } from '../services/userService';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faUser, faBuilding, faBell, faShoppingBag, faCheckCircle, 
  faToggleOn, faToggleOff, faArrowRight, faSpinner 
} from '@fortawesome/free-solid-svg-icons';

export default function Profile() {
  const { user } = useAuth();
  const { isCustomer, isStaff } = usePermissions();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [customerInfo, setCustomerInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatingNotification, setUpdatingNotification] = useState(false);
  const [error, setError] = useState(null);

  const [editData, setEditData] = useState({});

  useEffect(() => {
    if (user && isStaff) {
      navigate('/dashboard');
    }
  }, [user, isStaff, navigate]);

  useEffect(() => {
    loadProfileData();
  }, []);

  const loadProfileData = async () => {
    try {
      setLoading(true);
      const [userData, customerData] = await Promise.all([
        userService.getCurrentUser(),
        userService.getCurrentUserCustomerInfo().catch(() => null)
      ]);
      setProfile(userData);
      setCustomerInfo(customerData);
      setEditData({
        full_name: userData.full_name || '',
        email: userData.email || '',
        business_name: customerData?.business_name || '',
        address_1: customerData?.address_1 || '',
        address_2: customerData?.address_2 || '',
        address_3: customerData?.address_3 || '',
        telefono_1: customerData?.telefono_1 || '',
        telefono_2: customerData?.telefono_2 || '',
        rfc: customerData?.rfc || ''
      });
    } catch (err) {
      console.error('Error loading profile:', err);
      setError('Error al cargar la información del perfil');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleNotification = async () => {
    const newVal = !profile?.notificate;
    try {
      setUpdatingNotification(true);
      await userService.updateCurrentUser({ notificate: newVal });
      setProfile(prev => ({ ...prev, notificate: newVal }));
    } catch (err) {
      alert('Error al actualizar preferencia de notificaciones: ' + (err.message || 'Error de conexión'));
    } finally {
      setUpdatingNotification(false);
    }
  };

  if (loading && !profile) {
    return (
      <div className="page">
        <SearchBar />
        <main className="page__content">
          <div className="empty-state">
            <FontAwesomeIcon icon={faSpinner} spin className="empty-state__icon text-primary" />
            <div className="empty-state__text">Cargando perfil...</div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <SearchBar />
        <main className="page__content">
          <div className="page-container">
            <div className="alert alert--danger">{error}</div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="page">
      <SearchBar />

      <main className="page__content">
        <div className="page-container">
          <div className="d-flex items-center justify-between mb-6 flex-wrap gap-4">
            <div>
              <h1 className="section-title">Mi Perfil</h1>
              <p className="text-sm text-muted">Consulta tus datos de negocio, direcciones registradas y configuración de notificaciones.</p>
            </div>
            <div className="d-flex items-center gap-3">
              <button className="btn btn--primary" onClick={() => navigate('/orders')}>
                <FontAwesomeIcon icon={faShoppingBag} className="mr-2" />
                Ver Mis Pedidos
                <FontAwesomeIcon icon={faArrowRight} className="ml-2" />
              </button>
              <HelpGuide
                title="Guía del Perfil"
                items={[
                  "Datos: Si necesitas actualizar tu razón social o RFC, contacta a tu agente comercial asignado.",
                  "Notificaciones: Activa alertas por correo para saber al instante cuando tu pedido es aprobado, enviado o entregado.",
                  "Pedidos: Tus órdenes de compra se encuentran en la sección 'Mis Pedidos' del menú principal."
                ]}
              />
            </div>
          </div>

          {/* Configuración de Notificaciones (Tarjeta destacada y accesible) */}
          <div className="dashboard-section mb-6">
            <div className="notification-settings-card">
              <div className="notification-settings-card__content">
                <h3 className="notification-settings-card__title">
                  <FontAwesomeIcon icon={faBell} className="text-warning" />
                  Alertas Automáticas de Envíos
                  {profile?.notificate ? (
                    <span className="badge badge--success">
                      <FontAwesomeIcon icon={faCheckCircle} className="mr-1" />
                      Activo
                    </span>
                  ) : (
                    <span className="badge badge--secondary">Desactivado</span>
                  )}
                </h3>
                <p className="notification-settings-card__description">
                  Recibe correos electrónicos automáticos sobre el estado de tus pedidos (Enviado &rarr; Entregado) y promociones exclusivas.
                </p>
              </div>

              <div className="notification-settings-card__action">
                <button 
                  className={`btn ${profile?.notificate ? 'btn--success' : 'btn--secondary'} btn--md d-flex align-items-center gap-2`}
                  onClick={handleToggleNotification}
                  disabled={updatingNotification}
                >
                  <FontAwesomeIcon icon={profile?.notificate ? faToggleOn : faToggleOff} className="text-xl" />
                  <span>{profile?.notificate ? 'Notificaciones Activadas' : 'Activar Notificaciones'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Información del Usuario y Negocio */}
          <div className="dashboard-section">
            <div className="section-header">
              <h2 className="section-title">
                <FontAwesomeIcon icon={faUser} className="mr-2 text-primary" />
                Datos de Cuenta y Negocio
              </h2>
            </div>

            <div className="modal__form">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-group__label">Usuario:</label>
                  <input className="input" type="text" value={profile?.username || ''} disabled />
                </div>
                <div className="form-group">
                  <label className="form-group__label">Nombre del Contacto:</label>
                  <input className="input" type="text" value={editData.full_name} disabled />
                </div>
              </div>

              <div className="form-group">
                <label className="form-group__label">Correo Electrónico de Contacto:</label>
                <input className="input" type="email" value={editData.email} disabled />
              </div>

              {customerInfo && (
                <>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-group__label">Razón Social / Negocio:</label>
                      <input className="input" type="text" value={editData.business_name} disabled />
                    </div>
                    <div className="form-group">
                      <label className="form-group__label">RFC:</label>
                      <input className="input" type="text" value={editData.rfc} disabled />
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-group__label">Dirección Principal de Entrega:</label>
                    <input className="input" type="text" value={editData.address_1} disabled />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-group__label">Dirección Alternativa 2:</label>
                      <input className="input" type="text" value={editData.address_2 || 'No registrada'} disabled />
                    </div>
                    <div className="form-group">
                      <label className="form-group__label">Dirección Alternativa 3:</label>
                      <input className="input" type="text" value={editData.address_3 || 'No registrada'} disabled />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-group__label">Teléfono 1:</label>
                      <input className="input" type="text" value={editData.telefono_1} disabled />
                    </div>
                    <div className="form-group">
                      <label className="form-group__label">Teléfono 2:</label>
                      <input className="input" type="text" value={editData.telefono_2 || 'No registrado'} disabled />
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* ACCESO A CENTRO DE SOPORTE & TICKETS */}
          <div className="card p-4 mt-6 d-flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-base font-semibold mb-1">¿Necesitas ayuda, aclaraciones o levantar un reporte?</h3>
              <p className="text-sm text-muted mb-0">
                Gestiona tus tickets de soporte técnico o contacta a tu ejecutivo de ventas en nuestro centro oficial de atención.
              </p>
            </div>
            <button 
              className="btn btn--secondary btn--sm"
              onClick={() => navigate('/support')}
            >
              Ir a Soporte & Tickets
            </button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}