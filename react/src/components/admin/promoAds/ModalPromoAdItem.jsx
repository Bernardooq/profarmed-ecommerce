import { useState, useEffect } from 'react';
import promoAdService from '../../../services/promoAdService';

const RECOMMENDED_SIZES = {
  1: {
    desktop: '1440 × 420 px (Banner panorámico)',
    tablet: '960 × 360 px',
    mobile: '720 × 420 px',
  },
  2: {
    desktop: '720 × 400 px (por cuadro)',
    tablet: '500 × 320 px (por cuadro)',
    mobile: '720 × 400 px',
  },
  3: {
    desktop: '480 × 360 px (4:3 por cuadro)',
    tablet: '480 × 360 px (2 columnas)',
    mobile: '720 × 420 px',
  },
  4: {
    desktop: '360 × 360 px (1:1 por cuadro)',
    tablet: '440 × 440 px (2×2)',
    mobile: '360 × 360 px (2×2)',
  },
};

const LINK_PRESETS = [
  { value: 'none', label: 'Sin enlace (solo imagen informativa)' },
  { value: 'search', label: 'Buscar producto / marca / sustancia (recomendado)' },
  { value: 'promos', label: 'Ir a Ofertas & Promos (/promos)' },
  { value: 'catalog', label: 'Ir al Catálogo completo (/products)' },
  { value: 'favorites', label: 'Ir a Mis Listas Favoritas (/favorites)' },
  { value: 'orders', label: 'Ir a Mis Pedidos (/orders)' },
  { value: 'custom', label: 'URL personalizada o externa' },
];

function parseLinkUrl(rawUrl) {
  const url = (rawUrl || '').trim();
  if (!url) return { type: 'none', value: '' };
  if (url.startsWith('/products?search=')) {
    try {
      return { type: 'search', value: decodeURIComponent(url.slice('/products?search='.length)) };
    } catch {
      return { type: 'search', value: url.slice('/products?search='.length) };
    }
  }
  if (url === '/promos') return { type: 'promos', value: '' };
  if (url === '/products') return { type: 'catalog', value: '' };
  if (url === '/favorites') return { type: 'favorites', value: '' };
  if (url === '/orders') return { type: 'orders', value: '' };
  return { type: 'custom', value: url };
}

function buildLinkUrl(type, value) {
  const clean = (value || '').trim();
  switch (type) {
    case 'search':
      return clean ? `/products?search=${encodeURIComponent(clean)}` : null;
    case 'promos':
      return '/promos';
    case 'catalog':
      return '/products';
    case 'favorites':
      return '/favorites';
    case 'orders':
      return '/orders';
    case 'custom':
      return clean || null;
    default:
      return null;
  }
}

/**
 * Modal para crear o editar un anuncio dentro de una columna (slot) de la sección.
 * Permite subir imágenes optimizadas para Desktop, Tablet y Móvil con preview inmediato.
 */
export default function ModalPromoAdItem({
  isOpen,
  onClose,
  onSaved,
  section,
  defaultSlot = 1,
  defaultOrder = 0,
  editingItem = null,
  canUpload = false,
}) {
  const [formData, setFormData] = useState({
    slot: 1,
    display_order: 0,
    title: '',
    link_type: 'none',
    link_value: '',
    img_desktop: '',
    img_tablet: '',
    img_mobile: '',
    is_active: true,
    start_date: '',
    end_date: '',
  });
  const [previews, setPreviews] = useState({
    desktop: '',
    tablet: '',
    mobile: '',
  });
  const [uploadingVariant, setUploadingVariant] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    if (editingItem) {
      const parsedLink = parseLinkUrl(editingItem.link_url);
      setFormData({
        slot: editingItem.slot || 1,
        display_order: editingItem.display_order ?? 0,
        title: editingItem.title || '',
        link_type: parsedLink.type,
        link_value: parsedLink.value,
        img_desktop: editingItem.img_desktop || '',
        img_tablet: editingItem.img_tablet || '',
        img_mobile: editingItem.img_mobile || '',
        is_active: editingItem.is_active ?? true,
        start_date: editingItem.start_date ? new Date(editingItem.start_date).toISOString().slice(0, 16) : '',
        end_date: editingItem.end_date ? new Date(editingItem.end_date).toISOString().slice(0, 16) : '',
      });
      setPreviews({
        desktop: editingItem.img_desktop_url || '',
        tablet: editingItem.img_tablet_url || '',
        mobile: editingItem.img_mobile_url || '',
      });
    } else {
      setFormData({
        slot: defaultSlot,
        display_order: defaultOrder,
        title: '',
        link_type: 'none',
        link_value: '',
        img_desktop: '',
        img_tablet: '',
        img_mobile: '',
        is_active: true,
        start_date: '',
        end_date: '',
      });
      setPreviews({ desktop: '', tablet: '', mobile: '' });
    }
  }, [isOpen, editingItem, defaultSlot, defaultOrder]);

  if (!isOpen || !section) return null;

  const maxSlots = section.layout_type || 1;
  const slotOptions = Array.from({ length: maxSlots }, (_, i) => i + 1);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : name === 'slot' || name === 'display_order' ? Number(value) : value,
    }));
  };

  const handleUploadVariant = async (variant, e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const keyField = `img_${variant}`;
    const prevKey = formData[keyField];
    const savedKey = editingItem ? editingItem[keyField] : '';

    setUploadingVariant(variant);
    setError('');
    try {
      const res = await promoAdService.uploadImage(file, variant);
      // Si había una imagen recién subida sin guardar, purgarla de S3
      if (prevKey && prevKey !== savedKey) {
        promoAdService.deleteImage(prevKey).catch(() => {});
      }
      setFormData((prev) => ({ ...prev, [keyField]: res.img_key }));
      setPreviews((prev) => ({ ...prev, [variant]: res.img_url }));
    } catch (err) {
      setError(err.response?.data?.detail || err.message || `Error al subir imagen (${variant})`);
    } finally {
      setUploadingVariant(null);
    }
  };

  const handleClearVariant = (variant) => {
    const keyField = `img_${variant}`;
    const currentKey = formData[keyField];
    const savedKey = editingItem ? editingItem[keyField] : '';
    if (currentKey && currentKey !== savedKey) {
      promoAdService.deleteImage(currentKey).catch(() => {});
    }
    setFormData((prev) => ({ ...prev, [keyField]: '' }));
    setPreviews((prev) => ({ ...prev, [variant]: '' }));
  };

  const handleCancelAndClose = () => {
    ['desktop', 'tablet', 'mobile'].forEach((variant) => {
      const keyField = `img_${variant}`;
      const currentKey = formData[keyField];
      const savedKey = editingItem ? editingItem[keyField] : '';
      if (currentKey && currentKey !== savedKey) {
        promoAdService.deleteImage(currentKey).catch(() => {});
      }
    });
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.img_desktop) {
      setError('La imagen para Desktop es obligatoria.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      const payload = {
        slot: Number(formData.slot),
        display_order: Number(formData.display_order) || 0,
        title: formData.title.trim() || null,
        link_url: buildLinkUrl(formData.link_type, formData.link_value),
        img_desktop: formData.img_desktop,
        img_tablet: formData.img_tablet || null,
        img_mobile: formData.img_mobile || null,
        is_active: Boolean(formData.is_active),
        start_date: formData.start_date ? new Date(formData.start_date).toISOString() : null,
        end_date: formData.end_date ? new Date(formData.end_date).toISOString() : null,
      };

      if (editingItem) {
        await promoAdService.updateItem(editingItem.item_id, payload);
      } else {
        await promoAdService.createItem(section.section_id, payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al guardar el anuncio');
    } finally {
      setLoading(false);
    }
  };

  const renderImageField = (variant, label, required = false) => {
    const keyVal = formData[`img_${variant}`];
    const previewUrl = previews[variant];
    const isBusy = uploadingVariant === variant;
    const layoutType = section.layout_type || 1;
    const recommendedText = (RECOMMENDED_SIZES[layoutType] || RECOMMENDED_SIZES[1])[variant];

    return (
      <div className="form-group">
        <label className="form-group__label">
          {label} {required ? '*' : '(Opcional)'}
        </label>
        <div className="promo-ads-admin__upload-row">
          <input
            className="input promo-ads-admin__upload-input"
            type="text"
            value={keyVal}
            readOnly
            placeholder={canUpload ? 'Sube una imagen...' : 'Sin permiso para subir'}
          />
          {canUpload && (
            <label className="btn btn--secondary btn--sm promo-ads-admin__upload-btn">
              {isBusy ? 'Subiendo...' : '📤 Subir'}
              <input
                type="file"
                accept="image/*"
                className="promo-ads-admin__hidden-file"
                disabled={isBusy || loading}
                onChange={(e) => handleUploadVariant(variant, e)}
              />
            </label>
          )}
          {!required && keyVal && (
            <button
              type="button"
              className="btn btn--danger btn--sm"
              onClick={() => handleClearVariant(variant)}
              disabled={loading}
              title="Quitar imagen"
            >
              ×
            </button>
          )}
        </div>
        <small className="text-muted">
          Tamaño sugerido ({layoutType} col{layoutType > 1 ? 's' : ''}): {recommendedText} · Se optimiza a WebP automáticamente.
        </small>
        {previewUrl && (
          <div className="image-preview mt-2">
            <img src={previewUrl} alt={`Preview ${variant}`} loading="lazy" />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="modal-overlay" onClick={handleCancelAndClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2>{editingItem ? 'Editar Anuncio' : 'Añadir Anuncio a Columna'}</h2>
          <button type="button" className="modal__close" onClick={handleCancelAndClose} aria-label="Cerrar modal">×</button>
        </div>

        <div className="modal__body">
          <form onSubmit={handleSubmit} className="modal__form">
            {error && <div className="alert alert--danger">{error}</div>}

            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="item_slot">Columna (Cuadro) *</label>
                <select
                  className="select"
                  id="item_slot"
                  name="slot"
                  value={formData.slot}
                  onChange={handleChange}
                  disabled={loading}
                >
                  {slotOptions.map((s) => (
                    <option key={s} value={s}>Cuadro {s}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-group__label" htmlFor="item_order">Orden en Carrusel</label>
                <input
                  className="input"
                  type="number"
                  id="item_order"
                  name="display_order"
                  value={formData.display_order}
                  onChange={handleChange}
                  min="0"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-group__label" htmlFor="item_title">Nombre / Alt Text</label>
              <input
                className="input"
                type="text"
                id="item_title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                placeholder="Ej: Promo Bayer Mayo"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-group__label" htmlFor="item_link_type">¿A dónde lleva al hacer clic? (Opcional)</label>
              <select
                className="select"
                id="item_link_type"
                name="link_type"
                value={formData.link_type}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    link_type: e.target.value,
                    link_value: e.target.value === 'search' || e.target.value === 'custom' ? prev.link_value : '',
                  }))
                }
                disabled={loading}
              >
                {LINK_PRESETS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {formData.link_type === 'search' && (
              <div className="form-group">
                <label className="form-group__label" htmlFor="item_link_search">Producto, marca o palabra clave a buscar</label>
                <input
                  className="input"
                  type="text"
                  id="item_link_search"
                  name="link_value"
                  value={formData.link_value}
                  onChange={handleChange}
                  placeholder="Ej: Pregabalina Maver, Paracetamol, Bayer..."
                  disabled={loading}
                />
                <small className="text-muted">
                  Escribe solo el nombre (sin URL). Al hacer clic, el cliente irá directo a los resultados de búsqueda.
                </small>
              </div>
            )}

            {formData.link_type === 'custom' && (
              <div className="form-group">
                <label className="form-group__label" htmlFor="item_link_custom">URL personalizada o externa</label>
                <input
                  className="input"
                  type="text"
                  id="item_link_custom"
                  name="link_value"
                  value={formData.link_value}
                  onChange={handleChange}
                  placeholder="Ej: /products?category=7 o https://..."
                  disabled={loading}
                />
              </div>
            )}

            {renderImageField('desktop', 'Imagen Desktop (>= 1024px)', true)}
            {renderImageField('tablet', 'Imagen Tablet (768px - 1023px)', false)}
            {renderImageField('mobile', 'Imagen Móvil (< 768px)', false)}

            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="item_start_date">Inicio del Anuncio (Opcional)</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="item_start_date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label className="form-group__label" htmlFor="item_end_date">Fin del Anuncio (Opcional)</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="item_end_date"
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
                <span>Anuncio activo</span>
              </label>
            </div>

            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={handleCancelAndClose} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn btn--primary" disabled={loading || !!uploadingVariant}>
                {loading ? 'Guardando...' : editingItem ? 'Guardar Cambios' : 'Agregar Anuncio'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
