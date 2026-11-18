/**
 * Contact.jsx
 * ===========
 * Página de contacto - Plataforma B2B
 * 
 * Funcionalidades:
 * - Formulario de contacto con validación
 * - Información de contacto (dirección, teléfonos, email, horario)
 * - Envío de mensaje al backend
 * - Mensaje de confirmación de envío
 * 
 * Acceso: Página pública (no requiere autenticación)
 */

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePermissions } from '../hooks/usePermissions';
import Header from '../components/layout/Header';
import Header2 from '../components/layout/Header2';
import SearchBar from '../components/layout/SearchBar';
import Footer from '../components/layout/Footer';
import apiService from '../services/apiService';
import SEO from '../components/common/SEO';
import { localBusinessSchema, createBreadcrumbSchema } from '../utils/schemas';
import content from '../config/content.json';
import BRAND from '../config/brand';
import { resolveBrandAsset } from '../utils/brandAssets';

// ============================================
// CONSTANTES
// ============================================
const SUCCESS_MESSAGE_DURATION = 5000;
// Site key de Turnstile centralizada
const TURNSTILE_SITE_KEY = BRAND.turnstileSiteKey;

const INITIAL_FORM_STATE = {
  name: '',
  email: '',
  phone: '',
  subject: '',
  message: ''
};

export default function Contact() {
  // ============================================
  // HOOKS & STATE
  // ============================================
  const { isAuthenticated, user } = useAuth();
  const { isStaff } = usePermissions();
  const [formData, setFormData] = useState(INITIAL_FORM_STATE);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [turnstileReady, setTurnstileReady] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState('');
  const widgetIdRef = useRef(null);
  const containerRef = useRef(null);

  // ============================================
  // SEO CONFIGURATION
  // ============================================
  const breadcrumbSchema = createBreadcrumbSchema([
    { name: 'Inicio', url: `${BRAND.domain}/` },
    { name: 'Contacto', url: `${BRAND.domain}/contact` }
  ]);

  const combinedSchema = {
    "@context": "https://schema.org",
    "@graph": [localBusinessSchema, breadcrumbSchema]
  };

  // ============================================
  // EVENT HANDLERS
  // ============================================

  // Cargar script de Turnstile (Desactivado en demo local)
  /* useEffect(() => {
    if (document.getElementById('turnstile-script')) {
      if (window.turnstile) setTurnstileReady(true);
      return;
    }

    const script = document.createElement('script');
    script.id = 'turnstile-script';
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onloadContactTurnstileCallback';
    script.async = true;
    script.defer = true;

    window.onloadContactTurnstileCallback = () => {
      setTurnstileReady(true);
    };

    document.head.appendChild(script);

    return () => {
      delete window.onloadContactTurnstileCallback;
    };
  }, []); */

  // Renderizar widget invisible de Turnstile (Desactivado en demo local)
  /* useEffect(() => {
    if (turnstileReady && window.turnstile && containerRef.current && widgetIdRef.current === null) {
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: TURNSTILE_SITE_KEY,
        callback: (token) => { setTurnstileToken(token); },
        'expired-callback': () => { setTurnstileToken(''); },
        'error-callback': () => { setTurnstileToken(''); },
        theme: 'light',
        size: 'flexible'
      });
    }

    return () => {
      if (widgetIdRef.current !== null && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [turnstileReady]); */

  // eslint-disable-next-line no-unused-vars
  const getTurnstileToken = async () => {
    if (!turnstileReady || !window.turnstile || widgetIdRef.current === null) return '';
    try {
      return await window.turnstile.getResponse(widgetIdRef.current);
    } catch (e) {
      console.warn('Turnstile failed:', e);
      return '';
    }
  };

  const resetTurnstile = () => {
    setTurnstileToken('');
    if (widgetIdRef.current !== null && window.turnstile) {
      window.turnstile.reset(widgetIdRef.current);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Turnstile desactivado para demo local
    /* if (turnstileReady && !turnstileToken) {
      alert('Por favor completa la verificación de seguridad');
      return;
    } */

    setSending(true);

    try {
      await apiService.sendContactForm(formData, turnstileToken);
      setSent(true);
      setFormData(INITIAL_FORM_STATE);
      resetTurnstile();
      setTimeout(() => setSent(false), SUCCESS_MESSAGE_DURATION);
    } catch (error) {
      console.error('Error:', error);
      alert(error.message || 'Hubo un error al enviar el mensaje. Por favor intenta de nuevo.');
      resetTurnstile();
    } finally {
      setSending(false);
    }
  };

  // ============================================
  // RENDER HELPERS
  // ============================================
  const renderHeader = () => {
    if (!isAuthenticated) return <Header />;
    if (isStaff) return <Header2 />;
    return <SearchBar />;
  };

  // ============================================
  // RENDER
  // ============================================
  return (
    <div className="page">
      <SEO
        title={BRAND.getTitle('Contacto')}
        description={content.contacto.subtitle || BRAND.shortDescription}
        canonical={BRAND.getCanonical('/contact')}
        ogType="website"
        schema={combinedSchema}
      />

      {renderHeader()}

      <main className="page__content">
        {/* 1. ¿Dónde nos encontramos? + Mapa + 4 bloques de contacto */}
        <section className="pf-section pf-section--light">
          <div className="pf-section__container">
            <div className="pf-section__header">
              <h1 className="pf-section__title">{content.contacto.title}</h1>
              <div className="pf-divider">
                <span className="pf-divider__primary" />
                <span className="pf-divider__secondary" />
              </div>
            </div>

            {content.contacto.info.maps?.url && (
              <div className="pf-map-box">
                <iframe
                  src={content.contacto.info.maps.url}
                  allowFullScreen=""
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                  title={content.contacto.info.maps.title}
                />
              </div>
            )}

            <div className="pf-contact-grid">
              {/* Dirección */}
              <div className="pf-contact-item">
                <h3 className="pf-contact-item__title">{content.contacto.info.address.title}</h3>
                <div className="pf-contact-item__row">
                  {content.contacto.info.address.icon && (
                    <img src={resolveBrandAsset(content.contacto.info.address.icon)} alt="" className="pf-contact-item__icon" />
                  )}
                  <p className="pf-contact-item__text">
                    {content.contacto.info.address.lines.map((line, idx) => (
                      <span key={idx}>
                        {line}
                        {idx < content.contacto.info.address.lines.length - 1 && <br />}
                      </span>
                    ))}
                  </p>
                </div>
              </div>

              {/* Correo electrónico */}
              <div className="pf-contact-item">
                <h3 className="pf-contact-item__title">{content.contacto.info.email.title}</h3>
                <div className="pf-contact-item__row">
                  {content.contacto.info.email.icon && (
                    <img src={resolveBrandAsset(content.contacto.info.email.icon)} alt="" className="pf-contact-item__icon" />
                  )}
                  <p className="pf-contact-item__text">{content.contacto.info.email.value}</p>
                </div>
              </div>

              {/* Línea de atención */}
              <div className="pf-contact-item">
                <h3 className="pf-contact-item__title">{content.contacto.info.phones.title}</h3>
                <div className="pf-contact-item__row">
                  {content.contacto.info.phones.icon && (
                    <img src={resolveBrandAsset(content.contacto.info.phones.icon)} alt="" className="pf-contact-item__icon" />
                  )}
                  <p className="pf-contact-item__text">
                    {content.contacto.info.phones.lines.map((line, idx) => (
                      <span key={idx}>
                        {line}
                        {idx < content.contacto.info.phones.lines.length - 1 && <br />}
                      </span>
                    ))}
                  </p>
                </div>
              </div>

              {/* Horario de atención */}
              <div className="pf-contact-item">
                <h3 className="pf-contact-item__title">{content.contacto.info.schedule.title}</h3>
                <div className="pf-contact-item__row">
                  {content.contacto.info.schedule.icon && (
                    <img src={resolveBrandAsset(content.contacto.info.schedule.icon)} alt="" className="pf-contact-item__icon" />
                  )}
                  <p className="pf-contact-item__text">
                    {content.contacto.info.schedule.lines.map((line, idx) => (
                      <span key={idx}>
                        {line}
                        {idx < content.contacto.info.schedule.lines.length - 1 && <br />}
                      </span>
                    ))}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Formulario ¡Déjenos un mensaje! (Degradado 3) */}
        <section className="pf-section pf-section--green-to-navy">
          <div className="pf-section__container">
            <div className="pf-section__header">
              <h2 className="pf-section__title">{content.contacto.form.title}</h2>
            </div>

            {sent && (
              <div className="alert alert--success mb-6" style={{ maxWidth: '760px', margin: '0 auto var(--space-6)' }}>
                ✓ ¡Mensaje enviado con éxito! Te responderemos pronto.
              </div>
            )}

            <form onSubmit={handleSubmit} className="pf-glass-form">
              <div className="pf-glass-form__grid">
                <div className="pf-glass-form__field">
                  <label className="pf-glass-form__label" htmlFor="name">
                    {content.contacto.form.labels.name}
                  </label>
                  <input
                    className="pf-glass-form__input"
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    disabled={sending}
                  />
                </div>

                <div className="pf-glass-form__field">
                  <label className="pf-glass-form__label" htmlFor="email">
                    {content.contacto.form.labels.email}
                  </label>
                  <input
                    className="pf-glass-form__input"
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    disabled={sending}
                  />
                </div>

                <div className="pf-glass-form__field">
                  <label className="pf-glass-form__label" htmlFor="phone">
                    {content.contacto.form.labels.phone}
                  </label>
                  <input
                    className="pf-glass-form__input"
                    type="tel"
                    id="phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    disabled={sending}
                  />
                </div>

                <div className="pf-glass-form__field">
                  <label className="pf-glass-form__label" htmlFor="subject">
                    {content.contacto.form.labels.subject}
                  </label>
                  <input
                    className="pf-glass-form__input"
                    type="text"
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    disabled={sending}
                  />
                </div>

                <div className="pf-glass-form__field pf-glass-form__field--full">
                  <label className="pf-glass-form__label" htmlFor="message">
                    {content.contacto.form.labels.message}
                  </label>
                  <textarea
                    className="pf-glass-form__textarea"
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    required
                    disabled={sending}
                    rows="5"
                  />
                </div>
              </div>

              <div className="pf-glass-form__submit">
                <button
                  type="submit"
                  className="pf-pill-btn pf-pill-btn--dark-text"
                  disabled={sending}
                >
                  {sending ? content.contacto.form.buttonSending : content.contacto.form.button}
                </button>
                {sent && (
                  <p className="pf-glass-form__sent-note">
                    ✓ ¡Mensaje enviado con éxito! Te responderemos pronto.
                  </p>
                )}
              </div>
            </form>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
