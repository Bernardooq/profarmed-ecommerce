/**
 * Support.jsx
 * ===========
 * Página oficial de Soporte & Atención a Clientes.
 * Permite gestionar y dar seguimiento a tickets de soporte,
 * e interactuar vía WhatsApp con su ejecutivo de ventas asignado.
 */

import { useEffect, useState } from 'react';
import SEO from '../components/common/SEO';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faComments, faHeadset } from '@fortawesome/free-solid-svg-icons';
import SearchBar from '../components/layout/SearchBar';
import Footer from '../components/layout/Footer';
import MyTickets from '../components/tickets/MyTickets';
import HelpGuide from '../components/common/HelpGuide';
import { userService } from '../services/userService';
import { useAuth } from '../context/AuthContext';
import content from '../config/content.json';
import BRAND from '../config/brand';

export default function Support() {
  const { user } = useAuth();
  const [customerInfo, setCustomerInfo] = useState(null);

  useEffect(() => {
    userService.getCurrentUserCustomerInfo()
      .then(data => setCustomerInfo(data))
      .catch(() => setCustomerInfo(null));
  }, []);

  const brandName = BRAND.name;

  const whatsappMessage = encodeURIComponent(
    `Hola, soy ${user?.full_name || user?.username || 'cliente'} de ${brandName}. Requiero asistencia con mi cuenta.`
  );

  return (
    <div className="min-h-screen bg-app flex flex-col">
      <SEO title={BRAND.getTitle('Soporte & Tickets')} description={`Centro de soporte y seguimiento de tickets de ${BRAND.name}.`} noindex={true} />

      <SearchBar />

      <main className="page__content flex-1">
        <div className="page-container">
          <div className="d-flex items-center justify-between mb-6 flex-wrap gap-4">
            <div>
              <h1 className="section-title d-flex align-items-center gap-2">
                <FontAwesomeIcon icon={faHeadset} className="text-primary" />
                Centro de Soporte & Tickets
              </h1>
              <p className="text-sm text-muted">
                Reporta incidencias, devoluciones o aclaraciones con seguimiento oficial por folio.
              </p>
            </div>
            <HelpGuide
              title="Guía de Soporte"
              items={[
                "Tickets: Levanta reportes formales para problemas de facturación, pedidos o aclaraciones con seguimiento continuo.",
                "Estados: Puedes consultar si tu caso está Recibido, En Revisión, En Escalamiento o Solucionado.",
                "WhatsApp: Para atención rápida sobre cotizaciones o dudas urgentes, comunícate directo con tu ejecutivo de ventas."
              ]}
            />
          </div>

          {/* Banner de Contacto Directo WhatsApp */}
          <div className="support-executive-banner">
            <div className="support-executive-banner__info">
              <div className="support-executive-banner__icon">
                <FontAwesomeIcon icon={faComments} />
              </div>
              <div>
                <h3 className="support-executive-banner__title">¿Atención comercial inmediata?</h3>
                <p className="support-executive-banner__desc">
                  Contacta a tu ejecutivo de ventas asignado directamente por WhatsApp en caso de requerir asistencia rápida.
                </p>
              </div>
            </div>
            <a
              href={`https://wa.me/?text=${whatsappMessage}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn--success"
            >
              <FontAwesomeIcon icon={faComments} className="mr-2" />
              Contactar por WhatsApp
            </a>
          </div>

          {/* Módulo Oficial de Tickets de Soporte */}
          <MyTickets />
        </div>
      </main>

      <Footer />
    </div>
  );
}
