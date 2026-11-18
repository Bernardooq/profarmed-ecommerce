import { useState, useEffect } from 'react';
import promoAdService from '../../../services/promoAdService';

const LAYOUT_OPTIONS = [
  { value: 1, label: '1 Columna (Banner Completo)' },
  { value: 2, label: '2 Columnas' },
  { value: 3, label: '3 Columnas' },
  { value: 4, label: '4 Columnas' },
];

/**
 * Modal para crear o editar una sección de publicidad (1 a 4 columnas).
 * Sigue la misma estructura y clases SCSS de ModalAddProduct.
 */
export default function ModalPromoAdSection({ isOpen, onClose, onSaved, editingSection = null, defaultOrder = 0 }) {
  const [formData, setFormData] = useState({
    title: '',
    layout_type: 1,
    display_order: 0,
    is_active: true,
    start_date: '',
    end_date: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    if (editingSection) {
      setFormData({
        title: editingSection.title || '',
        layout_type: editingSection.layout_type || 1,
        display_order: editingSection.display_order ?? 0,
        is_active: editingSection.is_active ?? true,
        start_date: editingSection.start_date ? new Date(editingSection.start_date).toISOString().slice(0, 16) : '',
        end_date: editingSection.end_date ? new Date(editingSection.end_date).toISOString().slice(0, 16) : '',
      });
    } else {
      setFormData({
        title: '',
        layout_type: 1,
        display_order: defaultOrder,
        is_active: true,
        start_date: '',
        end_date: '',
      });
    }
  }, [isOpen, editingSection, defaultOrder]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : name === 'layout_type' || name === 'display_order' ? Number(value) : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const payload = {
        title: formData.title.trim() || null,
        layout_type: Number(formData.layout_type),
        display_order: Number(formData.display_order) || 0,
        is_active: Boolean(formData.is_active),
        start_date: formData.start_date ? new Date(formData.start_date).toISOString() : null,
        end_date: formData.end_date ? new Date(formData.end_date).toISOString() : null,
      };

      if (editingSection) {
        await promoAdService.updateSection(editingSection.section_id, payload);
      } else {
        await promoAdService.createSection(payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al guardar la sección');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2>{editingSection ? 'Editar Sección Publicitaria' : 'Nueva Sección Publicitaria'}</h2>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar modal">×</button>
        </div>

        <div className="modal__body">
          <form onSubmit={handleSubmit} className="modal__form">
            {error && <div className="alert alert--danger">{error}</div>}

            <div className="form-group">
              <label className="form-group__label" htmlFor="promo_ad_section_title">Título de la Sección (Opcional)</label>
              <input
                className="input"
                type="text"
                id="promo_ad_section_title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="Ej: Destacados del Mes (déjalo vacío para no mostrar título)"
                disabled={loading}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="promo_ad_layout_type">Diseño (Columnas) *</label>
                <select
                  className="select"
                  id="promo_ad_layout_type"
                  name="layout_type"
                  value={formData.layout_type}
                  onChange={handleChange}
                  disabled={loading}
                >
                  {LAYOUT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                {editingSection && Number(formData.layout_type) < Number(editingSection.layout_type) && (
                  <small className="text-muted">
                    Al reducir columnas de {editingSection.layout_type} a {formData.layout_type}, se eliminarán los anuncios de los cuadros sobrantes y sus imágenes en S3.
                  </small>
                )}
              </div>

              <div className="form-group">
                <label className="form-group__label" htmlFor="promo_ad_display_order">Orden Vertical</label>
                <input
                  className="input"
                  type="number"
                  id="promo_ad_display_order"
                  name="display_order"
                  value={formData.display_order}
                  onChange={handleChange}
                  min="0"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="promo_ad_start_date">Fecha Inicio (Opcional)</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="promo_ad_start_date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label className="form-group__label" htmlFor="promo_ad_end_date">Fecha Fin (Opcional)</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="promo_ad_end_date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group form-group--checkbox">
              <label className="promo-ads-admin__checkbox-label">
                <input
                  className="checkbox"
                  type="checkbox"
                  name="is_active"
                  checked={formData.is_active}
                  onChange={handleChange}
                  disabled={loading}
                />
                <span>Sección activa y visible para clientes</span>
              </label>
            </div>

            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={onClose} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn btn--primary" disabled={loading}>
                {loading ? 'Guardando...' : editingSection ? 'Guardar Cambios' : 'Crear Sección'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
