/**
 * BeClient.jsx
 * ============
 * Página pública para registro de nuevos clientes B2B (Quiero ser cliente)
 * 
 * Permite subir la documentación requerida:
 * - Identificación oficial (PDF)
 * - Licencia sanitaria (PDF)
 * - Comprobante de domicilio (PDF)
 * - Constancia de Situación Fiscal (PDF)
 */

import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/layout/Header';
import Header2 from '../components/layout/Header2';
import SearchBar from '../components/layout/SearchBar';
import Footer from '../components/layout/Footer';
import SEO from '../components/common/SEO';
import { useAuth } from '../context/AuthContext';
import { usePermissions } from '../hooks/usePermissions';
import apiService from '../services/apiService';
import content from '../config/content.json';
import BRAND from '../config/brand';

// Site key de Turnstile centralizada
const TURNSTILE_SITE_KEY = BRAND.turnstileSiteKey;
const SUCCESS_MESSAGE_DURATION = 8000;

export default function BeClient() {
  const { isAuthenticated, user } = useAuth();
  const { isStaff } = usePermissions();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    subject: 'Solicitud de alta de cliente nuevo',
    message: ''
  });

  const [files, setFiles] = useState({
    id_pdf: null,
    sanitary_license_pdf: null,
    proof_of_address_pdf: null,
    tax_cert_pdf: null
  });

  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [turnstileReady, setTurnstileReady] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState('');

  const containerRef = useRef(null);
  const widgetIdRef = useRef(null);

  const idPdfRef = useRef(null);
  const sanitaryLicenseRef = useRef(null);
  const proofOfAddressRef = useRef(null);
  const taxCertRef = useRef(null);
  const fileRefs = { id_pdf: idPdfRef, sanitary_license_pdf: sanitaryLicenseRef, proof_of_address_pdf: proofOfAddressRef, tax_cert_pdf: taxCertRef };

  const clearFile = (name) => {
    if (fileRefs[name]?.current) {
      fileRefs[name].current.value = '';
    }
    setFiles(prev => ({ ...prev, [name]: null }));
  };

  const renderFileField = (name, label) => {
    const file = files[name];
    const fileName = file?.name || null;
    return (
      <div className="pf-glass-form__field">
        <label className="pf-glass-form__label" htmlFor={name}>{label}</label>
        <input
          ref={fileRefs[name]}
          type="file"
          id={name}
          name={name}
          accept=".pdf"
          onChange={handleFileChange}
          required
          disabled={sending}
          style={{ display: 'none' }}
        />
        <div className="pf-glass-form__file-box">
          <button
            type="button"
            className="pf-glass-form__file-btn"
            onClick={() => fileRefs[name]?.current?.click()}
            disabled={sending}
          >
            {fileName ? 'Cambiar PDF' : 'Seleccionar PDF'}
          </button>
          <span className={`pf-glass-form__file-name${fileName ? ' pf-glass-form__file-name--selected' : ''}`}>
            {fileName || 'Ningún archivo seleccionado'}
          </span>
          {fileName && (
            <button
              type="button"
              className="pf-glass-form__file-remove"
              onClick={() => clearFile(name)}
              disabled={sending}
              aria-label="Remover archivo"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    );
  };

  // Cargar Turnstile (Desactivado en demo local)
  /* useEffect(() => {
    if (document.getElementById('turnstile-script')) {
      if (window.turnstile) setTurnstileReady(true);
      return;
    }

    const script = document.createElement('script');
    script.id = 'turnstile-script';
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onloadBeClientTurnstileCallback';
    script.async = true;
    script.defer = true;

    window.onloadBeClientTurnstileCallback = () => {
      setTurnstileReady(true);
    };

    document.head.appendChild(script);

    return () => {
      delete window.onloadBeClientTurnstileCallback;
    };
  }, []); */

  // Inicializar Turnstile (Desactivado en demo local)
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

  const handleFileChange = (e) => {
    const { name, files: selectedFiles } = e.target;
    if (selectedFiles && selectedFiles[0]) {
      const file = selectedFiles[0];
      
      if (file.type !== 'application/pdf') {
        alert('Solo se admiten documentos en formato PDF.');
        e.target.value = '';
        setFiles(prev => ({ ...prev, [name]: null }));
        return;
      }
      
      const MAX_SIZE = 5 * 1024 * 1024;
      if (file.size > MAX_SIZE) {
        alert(`El archivo "${file.name}" supera el tamaño máximo permitido de 5 MB.`);
        e.target.value = '';
        setFiles(prev => ({ ...prev, [name]: null }));
        return;
      }
      
      setFiles(prev => ({ ...prev, [name]: file }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Turnstile desactivado para demo local
    /* if (turnstileReady && !turnstileToken) {
      alert('Por favor completa la verificación de seguridad.');
      return;
    } */

    if (!files.id_pdf || !files.sanitary_license_pdf || !files.proof_of_address_pdf || !files.tax_cert_pdf) {
      alert('Debes adjuntar los 4 documentos requeridos en formato PDF para enviar la solicitud.');
      return;
    }

    setSending(true);

    // Preparar FormData para subir archivos y campos
    const submissionData = new FormData();
    submissionData.append('full_name', formData.name);
    submissionData.append('email', formData.email);
    submissionData.append('phone', formData.phone);
    submissionData.append('subject', formData.subject);
    if (formData.message && formData.message.trim()) {
      submissionData.append('message', formData.message.trim());
    }

    // Adjuntar archivos PDF
    submissionData.append('id_pdf', files.id_pdf);
    submissionData.append('sanitary_license_pdf', files.sanitary_license_pdf);
    submissionData.append('proof_of_address_pdf', files.proof_of_address_pdf);
    submissionData.append('tax_cert_pdf', files.tax_cert_pdf);

    try {
      // Usar la función centralizada del servicio apiService
      await apiService.sendClientRequest(submissionData, turnstileToken);

      setSent(true);
      setFormData({
        name: '',
        email: '',
        phone: '',
        subject: 'Solicitud de alta de cliente nuevo',
        message: ''
      });
      setFiles({
        id_pdf: null,
        sanitary_license_pdf: null,
        proof_of_address_pdf: null,
        tax_cert_pdf: null
      });
      // Limpiar inputs de archivo en el DOM
      document.querySelectorAll('input[type="file"]').forEach(input => input.value = '');

      resetTurnstile();
    } catch (error) {
      console.error('Error al enviar la solicitud:', error);
      alert(error.message || 'Hubo un error al procesar tu solicitud. Verifica que todos los campos sean correctos.');
      resetTurnstile();
    } finally {
      setSending(false);
    }
  };

  const renderHeader = () => {
    if (!isAuthenticated) return <Header />;
    if (isStaff) return <Header2 />;
    return <SearchBar />;
  };

  return (
    <div className="page">
      <SEO
        title={BRAND.getTitle('Quiero Ser Cliente B2B')}
        description={`Regístrate como cliente B2B en la plataforma ${BRAND.name} y accede a catálogos exclusivos, listas de precio personalizadas y gestión de pedidos empresariales.`}
        canonical={BRAND.getCanonical('/quiero-ser-cliente')}
      />

      {renderHeader()}

      <main className="page__content">
        {sent ? (
          <section className="pf-section pf-section--degradado-3-welcome">
            <div className="pf-welcome__confetti" aria-hidden="true" />
            <div className="pf-section__container">
              <div className="pf-welcome">
                <h1 className="pf-welcome__title">
                  {content.quieroSerCliente.thankYou?.title}
                </h1>
                <p className="pf-welcome__subtitle">
                  {content.quieroSerCliente.thankYou?.subtitlePrefix}
                  <strong>{content.quieroSerCliente.thankYou?.subtitleBold}</strong>
                </p>
                <Link to="/" className="pf-pill-btn pf-pill-btn--dark-text">
                  {content.quieroSerCliente.thankYou?.buttonText || 'Regresar al inicio'}
                </Link>
              </div>
            </div>
          </section>
        ) : (
        <section className="pf-section pf-section--degradado-2">
          <div className="pf-section__container">
            <div className="pf-section__header">
              <h1 className="pf-section__title">{content.quieroSerCliente.title}</h1>
              <div className="pf-divider pf-divider--on-dark">
                <span className="pf-divider__primary" />
                <span className="pf-divider__secondary" />
              </div>
              <p className="pf-section__subtitle">{content.quieroSerCliente.subtitle}</p>
            </div>

            <div className="pf-glass-card">
              <form onSubmit={handleSubmit} className="pf-glass-form">
                <h3 className="pf-glass-form__section-title">
                  {content.quieroSerCliente.form.sections.general}
                </h3>

                <div className="pf-glass-form__grid">
                  <div className="pf-glass-form__field">
                    <label className="pf-glass-form__label" htmlFor="name">
                      {content.quieroSerCliente.form.labels.companyName}
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
                      {content.quieroSerCliente.form.labels.email}
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
                      {content.quieroSerCliente.form.labels.phone}
                    </label>
                    <input
                      className="pf-glass-form__input"
                      type="tel"
                      id="phone"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      required
                      disabled={sending}
                    />
                  </div>

                  <div className="pf-glass-form__field">
                    <label className="pf-glass-form__label" htmlFor="subject">
                      {content.quieroSerCliente.form.labels.subject}
                    </label>
                    <input
                      className="pf-glass-form__input"
                      type="text"
                      id="subject"
                      name="subject"
                      value={formData.subject}
                      onChange={handleChange}
                      required
                      disabled
                    />
                  </div>

                  <div className="pf-glass-form__field pf-glass-form__field--full">
                    <label className="pf-glass-form__label" htmlFor="message">
                      {content.quieroSerCliente.form.labels.message}
                    </label>
                    <textarea
                      className="pf-glass-form__textarea"
                      id="message"
                      name="message"
                      value={formData.message}
                      onChange={handleChange}
                      placeholder={content.quieroSerCliente.form.labels.placeholderMessage}
                      disabled={sending}
                      rows="4"
                    />
                  </div>
                </div>

                <h3 className="pf-glass-form__section-title" style={{ marginTop: 'var(--space-8)' }}>
                  {content.quieroSerCliente.form.sections.documents}
                </h3>

                <div className="pf-glass-form__grid">
                  {renderFileField('id_pdf', content.quieroSerCliente.form.labels.idPdf)}
                  {renderFileField('sanitary_license_pdf', content.quieroSerCliente.form.labels.sanitaryLicense)}
                  {renderFileField('proof_of_address_pdf', content.quieroSerCliente.form.labels.proofAddress)}
                  {renderFileField('tax_cert_pdf', content.quieroSerCliente.form.labels.taxCert)}
                </div>

                <div className="pf-glass-form__submit">
                  <button
                    type="submit"
                    className="pf-pill-btn pf-pill-btn--dark-text"
                    disabled={sending}
                  >
                    {sending ? content.quieroSerCliente.form.buttonSending : content.quieroSerCliente.form.button}
                  </button>
                  {sent && (
                    <p className="pf-glass-form__sent-note">
                      ✓ ¡Solicitud de cliente enviada con éxito! Revisaremos tu documentación y nos pondremos en contacto contigo a la brevedad.
                    </p>
                  )}
                </div>
              </form>
            </div>
          </div>
        </section>
        )}
      </main>

      <Footer />
    </div>
  );
}
