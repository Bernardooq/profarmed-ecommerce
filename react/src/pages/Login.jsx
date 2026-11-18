/**
 * Login.jsx
 * =========
 * Página de inicio de sesión - Plataforma B2B
 * 
 * Esta página permite a los usuarios (clientes y staff) autenticarse
 * en el sistema para acceder a sus funcionalidades respectivas.
 * 
 * Funcionalidades:
 * - Formulario de login centralizado
 * - Validación de credenciales
 * - Redirección automática según rol después del login exitoso
 * - Diseño responsive y centrado
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowLeft } from '@fortawesome/free-solid-svg-icons';
import Footer from '../components/layout/Footer';
import LoginForm from '../components/users/LoginForm';
import SEO from '../components/common/SEO';
import BRAND from '../config/brand';

export default function Login() {
  const [currentView, setCurrentView] = useState('login');

  const getHeading = () => {
    switch (currentView) {
      case 'forgot_request':
      case 'forgot_verify':
      case 'forgot_new_password':
        return 'Recuperar Contraseña';
      case 'forgot_success':
        return 'Recuperación Completada';
      default:
        return 'Accede a tu cuenta';
    }
  };

  // ============================================
  // RENDER
  // ============================================
  return (
    <div className="page">
      <SEO 
        title={BRAND.getTitle(currentView === 'login' ? 'Iniciar Sesión' : 'Recuperar Contraseña')} 
        description={`Accede a tu cuenta de ${BRAND.name} para gestionar tus pedidos B2B.`}
        noindex={true} 
      />
      <main className="auth-layout">
        <Link to="/" className="auth-layout__back" aria-label="Volver al inicio" title="Volver al inicio">
          <FontAwesomeIcon icon={faArrowLeft} />
        </Link>

        <div className="auth-card">
          {/* Isotipo de la empresa */}
          <div className="auth-card__logo">
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
              <img src="/favicon.webp" alt={BRAND.name} style={{ height: '54px', width: 'auto', objectFit: 'contain' }} />
            </Link>
          </div>

          {currentView !== 'login' && (
            <h2 className="text-center mb-4" style={{ color: '#ffffff', fontSize: 'var(--text-lg)' }}>
              {getHeading()}
            </h2>
          )}

          {/* Formulario de autenticación y recuperación */}
          <LoginForm onViewChange={setCurrentView} />
        </div>
      </main>

      <Footer />
    </div>
  );
}