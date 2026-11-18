import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faDesktop, faTabletAlt, faMobileAlt } from '@fortawesome/free-solid-svg-icons';
import PromoAdSectionBlock from '../../promoAds/PromoAdSectionBlock';

/**
 * Modal de previsualización en vivo de una o todas las secciones publicitarias.
 * Permite alternar entre ancho Desktop, Tablet y Móvil usando los componentes reales.
 */
export default function ModalPromoAdPreview({ isOpen, onClose, sections = [], title = 'Previsualización' }) {
  const [viewport, setViewport] = useState('desktop');

  if (!isOpen) return null;

  const now = new Date();
  const isWithinSchedule = (entry) => {
    if (!entry?.is_active) return false;
    if (entry.start_date && new Date(entry.start_date) > now) return false;
    if (entry.end_date && new Date(entry.end_date) < now) return false;
    return true;
  };

  const activeSections = sections
    .filter((sec) => isWithinSchedule(sec))
    .map((sec) => ({
      ...sec,
      items: (sec.items || []).filter((item) => isWithinSchedule(item)),
    }))
    .filter((sec) => sec.items.length > 0);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--xl promo-ads-preview__modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="promo-ads-preview__header-left">
            <h2 className="promo-ads-preview__title">{title}</h2>
            <div className="promo-ads-preview__toggles">
              <button
                type="button"
                className={`btn btn--sm ${viewport === 'desktop' ? 'btn--primary' : 'btn--secondary'}`}
                onClick={() => setViewport('desktop')}
              >
                <FontAwesomeIcon icon={faDesktop} /> Desktop
              </button>
              <button
                type="button"
                className={`btn btn--sm ${viewport === 'tablet' ? 'btn--primary' : 'btn--secondary'}`}
                onClick={() => setViewport('tablet')}
              >
                <FontAwesomeIcon icon={faTabletAlt} /> Tablet
              </button>
              <button
                type="button"
                className={`btn btn--sm ${viewport === 'mobile' ? 'btn--primary' : 'btn--secondary'}`}
                onClick={() => setViewport('mobile')}
              >
                <FontAwesomeIcon icon={faMobileAlt} /> Móvil
              </button>
            </div>
          </div>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar modal">×</button>
        </div>

        <div className="modal__body">
          {activeSections.length === 0 ? (
            <div className="empty-state promo-ads-preview__empty">
              <p className="empty-state__text">No hay anuncios activos en esta sección para previsualizar.</p>
            </div>
          ) : (
            <div className={`promo-ads-preview__frame promo-ads-preview__frame--${viewport}`}>
              <div className="promo-ads__sections promo-ads-preview__sections">
                {activeSections.map((sec) => (
                  <PromoAdSectionBlock key={sec.section_id} section={sec} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
