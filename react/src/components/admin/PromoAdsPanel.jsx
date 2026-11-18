import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faPlus, faTrash, faEdit, faEye, faArrowUp, faArrowDown, faImages
} from '@fortawesome/free-solid-svg-icons';

import promoAdService from '../../services/promoAdService';
import { invalidatePromoAdsCache } from '../../hooks/useHasPromoAds';
import usePermissions from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import ModalPromoAdSection from './promoAds/ModalPromoAdSection';
import ModalPromoAdItem from './promoAds/ModalPromoAdItem';
import ModalPromoAdPreview from './promoAds/ModalPromoAdPreview';

const LAYOUT_LABELS = {
  1: '1 Columna (Banner)',
  2: '2 Columnas',
  3: '3 Columnas',
  4: '4 Columnas',
};

/**
 * Panel administrativo de Publicidad de Inicio (PBAC).
 * Permite gestionar secciones de 1 a 4 columnas, sus anuncios/carruseles y previsualización en vivo.
 */
export default function PromoAdsPanel() {
  const { can } = usePermissions();
  const canCreate = can(PERMISSIONS.PROMO_ADS_CREATE);
  const canEdit = can(PERMISSIONS.PROMO_ADS_EDIT);
  const canDelete = can(PERMISSIONS.PROMO_ADS_DELETE);
  const canUpload = can(PERMISSIONS.PROMO_ADS_UPLOAD);

  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modales
  const [sectionModal, setSectionModal] = useState({ open: false, editing: null });
  const [itemModal, setItemModal] = useState({ open: false, section: null, slot: 1, defaultOrder: 0, editing: null });
  const [previewModal, setPreviewModal] = useState({ open: false, sections: [], title: '' });

  const loadSections = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await promoAdService.getSections({ limit: 100 });
      setSections(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudieron cargar las secciones publicitarias.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSections();
  }, []);

  const handleDataChanged = async () => {
    invalidatePromoAdsCache();
    await loadSections();
  };

  const handleDeleteSection = async (section) => {
    if (!window.confirm(`¿Eliminar la sección "${section.title || 'Sin título'}" y todos sus anuncios e imágenes en S3?`)) return;
    try {
      await promoAdService.deleteSection(section.section_id);
      await handleDataChanged();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al eliminar la sección.');
    }
  };

  const handleDeleteItem = async (item) => {
    if (!window.confirm(`¿Eliminar el anuncio "${item.title || 'Sin título'}"?`)) return;
    try {
      await promoAdService.deleteItem(item.item_id);
      await handleDataChanged();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al eliminar el anuncio.');
    }
  };

  const handleMoveSection = async (index, direction) => {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= sections.length) return;

    const reordered = [...sections];
    const [moved] = reordered.splice(index, 1);
    reordered.splice(targetIndex, 0, moved);

    const payload = reordered.map((sec, idx) => ({
      section_id: sec.section_id,
      display_order: idx,
    }));

    setSections(reordered);
    try {
      await promoAdService.reorderSections(payload);
      invalidatePromoAdsCache();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al reordenar secciones.');
      await loadSections();
    }
  };

  const handleToggleSectionActive = async (section) => {
    try {
      await promoAdService.updateSection(section.section_id, { is_active: !section.is_active });
      await handleDataChanged();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al actualizar estado.');
    }
  };

  return (
    <section className="dashboard-section promo-ads-admin">
      <div className="section-header promo-ads-admin__header">
        <div>
          <h2 className="section-title promo-ads-admin__title">Publicidad de Inicio</h2>
          <p className="text-sm text-muted promo-ads-admin__subtitle">
            Configura bloques de 1 a 4 columnas con carruseles e imágenes responsivas para la página de inicio del cliente.
          </p>
        </div>

        <div className="promo-ads-admin__header-actions">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => setPreviewModal({ open: true, sections, title: 'Vista Completa de Inicio (Cliente)' })}
            disabled={sections.length === 0}
          >
            <FontAwesomeIcon icon={faEye} /> Previsualizar Página
          </button>

          {canCreate && (
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => setSectionModal({ open: true, editing: null })}
            >
              <FontAwesomeIcon icon={faPlus} /> Nueva Sección
            </button>
          )}
        </div>
      </div>

      {error && <ErrorMessage error={error} onDismiss={() => setError('')} />}

      {loading ? (
        <LoadingSpinner message="Cargando secciones publicitarias..." />
      ) : sections.length === 0 ? (
        <div className="empty-state promo-ads-admin__empty">
          <div className="empty-state__icon">🖼️</div>
          <h3 className="empty-state__title">Sin secciones publicitarias</h3>
          <p className="empty-state__text">
            Mientras no haya anuncios activos, los clientes entrarán directamente al Catálogo de Productos.
          </p>
        </div>
      ) : (
        <div className="promo-ads-admin__list">
          {sections.map((section, idx) => {
            const slots = Array.from({ length: section.layout_type || 1 }, (_, i) => i + 1);

            return (
              <article key={section.section_id} className="promo-ads-admin__card">
                <div className="promo-ads-admin__card-header">
                  <div className="promo-ads-admin__card-meta">
                    <span className="badge badge--primary">#{idx + 1}</span>
                    <h3 className="promo-ads-admin__card-title">{section.title || 'Sección sin título'}</h3>
                    <span className="badge badge--secondary">{LAYOUT_LABELS[section.layout_type]}</span>
                    <button
                      type="button"
                      className={`badge promo-ads-admin__status-btn ${section.is_active ? 'badge--success' : 'badge--danger'}`}
                      onClick={() => canEdit && handleToggleSectionActive(section)}
                      disabled={!canEdit}
                      title={canEdit ? 'Clic para activar/desactivar' : ''}
                    >
                      {section.is_active ? 'Activa' : 'Inactiva'}
                    </button>
                  </div>

                  <div className="promo-ads-admin__card-actions">
                    {canEdit && (
                      <>
                        <button
                          type="button"
                          className="btn btn--secondary btn--sm"
                          onClick={() => handleMoveSection(idx, -1)}
                          disabled={idx === 0}
                          title="Subir orden"
                        >
                          <FontAwesomeIcon icon={faArrowUp} />
                        </button>
                        <button
                          type="button"
                          className="btn btn--secondary btn--sm"
                          onClick={() => handleMoveSection(idx, 1)}
                          disabled={idx === sections.length - 1}
                          title="Bajar orden"
                        >
                          <FontAwesomeIcon icon={faArrowDown} />
                        </button>
                      </>
                    )}

                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      onClick={() => setPreviewModal({ open: true, sections: [section], title: `Preview: ${section.title || 'Sección sin título'}` })}
                      title="Previsualizar sección"
                    >
                      <FontAwesomeIcon icon={faEye} />
                    </button>

                    {canEdit && (
                      <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        onClick={() => setSectionModal({ open: true, editing: section })}
                        title="Editar sección"
                      >
                        <FontAwesomeIcon icon={faEdit} />
                      </button>
                    )}

                    {canDelete && (
                      <button
                        type="button"
                        className="btn btn--danger btn--sm"
                        onClick={() => handleDeleteSection(section)}
                        title="Eliminar sección"
                      >
                        <FontAwesomeIcon icon={faTrash} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Grilla de Columnas (Slots) */}
                <div className={`promo-ads__grid promo-ads__grid--cols-${section.layout_type}`}>
                  {slots.map((slotNum) => {
                    const slotItems = (section.items || [])
                      .filter((it) => it.slot === slotNum)
                      .sort((a, b) => a.display_order - b.display_order);

                    return (
                      <div key={slotNum} className="promo-ads-admin__slot-box">
                        <div className="promo-ads-admin__slot-header">
                          <span className="promo-ads-admin__slot-label">
                            Cuadro {slotNum}
                            {slotItems.length > 1 && (
                              <span className="badge badge--info promo-ads-admin__slot-badge">
                                Carrusel ({slotItems.length})
                              </span>
                            )}
                          </span>
                          {canCreate && (
                            <button
                              type="button"
                              className="btn btn--secondary btn--sm"
                              onClick={() =>
                                setItemModal({
                                  open: true,
                                  section,
                                  slot: slotNum,
                                  defaultOrder: slotItems.length,
                                  editing: null,
                                })
                              }
                            >
                              <FontAwesomeIcon icon={faPlus} /> Anuncio
                            </button>
                          )}
                        </div>

                        {slotItems.length === 0 ? (
                          <div className="text-muted text-sm promo-ads-admin__slot-empty">
                            <FontAwesomeIcon icon={faImages} /> Sin anuncios
                          </div>
                        ) : (
                          <div className="promo-ads-admin__items-list">
                            {slotItems.map((item) => (
                              <div key={item.item_id} className="promo-ads-admin__item-row">
                                <img
                                  src={item.img_desktop_url}
                                  alt={item.title || 'Anuncio'}
                                  className="promo-ads-admin__item-thumb"
                                />
                                <div className="promo-ads-admin__item-info">
                                  <div className="promo-ads-admin__item-title">
                                    {item.title || 'Sin título'}
                                  </div>
                                  <div className="promo-ads-admin__item-sub">
                                    Orden: {item.display_order} · {item.is_active ? 'Activo' : 'Inactivo'}
                                  </div>
                                </div>
                                <div className="promo-ads-admin__item-actions">
                                  {canEdit && (
                                    <button
                                      type="button"
                                      className="btn btn--secondary btn--sm"
                                      onClick={() => setItemModal({ open: true, section, slot: slotNum, editing: item })}
                                      title="Editar anuncio"
                                    >
                                      <FontAwesomeIcon icon={faEdit} />
                                    </button>
                                  )}
                                  {canDelete && (
                                    <button
                                      type="button"
                                      className="btn btn--danger btn--sm"
                                      onClick={() => handleDeleteItem(item)}
                                      title="Eliminar anuncio"
                                    >
                                      <FontAwesomeIcon icon={faTrash} />
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <ModalPromoAdSection
        isOpen={sectionModal.open}
        onClose={() => setSectionModal({ open: false, editing: null })}
        onSaved={handleDataChanged}
        editingSection={sectionModal.editing}
        defaultOrder={sections.length}
      />

      <ModalPromoAdItem
        isOpen={itemModal.open}
        onClose={() => setItemModal({ open: false, section: null, slot: 1, defaultOrder: 0, editing: null })}
        onSaved={handleDataChanged}
        section={itemModal.section}
        defaultSlot={itemModal.slot}
        defaultOrder={itemModal.defaultOrder}
        editingItem={itemModal.editing}
        canUpload={canUpload}
      />

      <ModalPromoAdPreview
        isOpen={previewModal.open}
        onClose={() => setPreviewModal({ open: false, sections: [], title: '' })}
        sections={previewModal.sections}
        title={previewModal.title}
      />
    </section>
  );
}
