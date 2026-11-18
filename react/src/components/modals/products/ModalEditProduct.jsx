import { useState, useEffect } from 'react';
import { categoryService } from '../../../services/categoryService';
import productService from '../../../services/productService';

const toDatetimeLocal = (isoStr) => {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

export default function ModalEditProduct({ isOpen, onClose, onSubmit, product }) {
  const [formData, setFormData] = useState({
    codebar: '', name: '', description: '', descripcion_2: '', location: '', base_price: '',
    iva_percentage: '', stock_count: '', category_id: '', image_url: '', is_active: true, lock: false,
    display_priority: '', created_at: '', updated_at: ''
  });
  const [initialUpdatedAt, setInitialUpdatedAt] = useState('');
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen && product) {
      const localCreated = toDatetimeLocal(product.created_at);
      const localUpdated = toDatetimeLocal(product.updated_at);
      setInitialUpdatedAt(localUpdated);
      setFormData({
        codebar: product.codebar || '', name: product.name || '', description: product.description || '',
        descripcion_2: product.descripcion_2 || '', location: product.location || '', base_price: product.base_price || '',
        iva_percentage: product.iva_percentage || '16.00', unidad_medida: product.unidad_medida || '',
        stock_count: product.stock_count || '', category_id: product.category_id || '',
        image_url: product.image_url || '', is_active: product.is_active !== undefined ? product.is_active : true,
        lock: product.lock !== undefined ? Boolean(product.lock) : false,
        display_priority: product.display_priority !== undefined && product.display_priority !== null ? product.display_priority : 1000000,
        created_at: localCreated,
        updated_at: localUpdated
      });
      loadCategories();
    }
  }, [isOpen, product]);

  const loadCategories = async () => { try { setCategories(await categoryService.getCategories()); } catch (err) { console.error(err); } };

  const handleUploadImage = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const result = await productService.uploadImage(product.product_id, file);
      setFormData(prev => ({ ...prev, image_url: result.image_url }));
    } catch (err) {
      setError(err.message || 'Error al subir la imagen');
    } finally {
      setUploading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); setError('');
    const basePrice = parseFloat(formData.base_price); const stock = parseInt(formData.stock_count);
    if (basePrice < 0) { setError('El precio no puede ser negativo'); return; }
    if (basePrice === 0) { setError('El precio debe ser mayor a 0'); return; }
    if (stock < 0) { setError('El stock no puede ser negativo'); return; }
    setLoading(true);
    try {
      const parsedPriority = formData.display_priority !== '' && !isNaN(parseInt(formData.display_priority))
        ? parseInt(formData.display_priority)
        : 1000000;
      const payload = {
        ...formData,
        base_price: basePrice,
        iva_percentage: parseFloat(formData.iva_percentage),
        stock_count: stock,
        category_id: parseInt(formData.category_id),
        display_priority: parsedPriority,
        lock: Boolean(formData.lock)
      };

      if (formData.created_at) {
        const dCreated = new Date(formData.created_at);
        if (!isNaN(dCreated.getTime())) payload.created_at = dCreated.toISOString();
      } else {
        delete payload.created_at;
      }

      if (formData.updated_at && formData.updated_at !== initialUpdatedAt) {
        const dUpdated = new Date(formData.updated_at);
        if (!isNaN(dUpdated.getTime())) payload.updated_at = dUpdated.toISOString();
      } else {
        delete payload.updated_at;
      }

      await onSubmit(product.product_id, payload);
      onClose();
    } catch (err) { setError(err.message || err.detail || 'Error al actualizar el producto'); }
    finally { setLoading(false); }
  };

  if (!isOpen || !product) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2>Editar Producto</h2>
          <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">×</button>
        </div>
        <div className="modal__body">
          <form onSubmit={handleSubmit} className="modal__form">
            {error && <div className="alert alert--danger">{error}</div>}

            <div className="form-group">
              <label className="form-group__label" htmlFor="codebar">Codigo de barras *</label>
              <input className="input" type="text" id="codebar" name="codebar" value={formData.codebar} onChange={handleChange} required disabled={loading} />
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="name">Nombre *</label>
              <input className="input" type="text" id="name" name="name" value={formData.name} onChange={handleChange} required disabled={loading} />
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="description">Descripción *</label>
              <textarea className="textarea" id="description" name="description" value={formData.description} onChange={handleChange} required disabled={loading} rows="3" />
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="descripcion_2">Descripción 2</label>
              <textarea className="textarea" id="descripcion_2" name="descripcion_2" value={formData.descripcion_2} onChange={handleChange} disabled={loading} rows="3" />
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="location">Ubicación / Anaquel</label>
              <input className="input" type="text" id="location" name="location" value={formData.location} onChange={handleChange} disabled={loading} placeholder="Ej: Pasillo 2, Anaquel B-4" />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="base_price">Precio Base *</label>
                <input className="input" type="number" id="base_price" name="base_price" value={formData.base_price} onChange={handleChange} step="0.01" min="0" required disabled={loading} placeholder="0.00" />
              </div>
              <div className="form-group">
                <label className="form-group__label" htmlFor="iva_percentage">IVA (%) *</label>
                <input className="input" type="number" id="iva_percentage" name="iva_percentage" value={formData.iva_percentage} onChange={handleChange} step="0.01" min="0" max="100" required disabled={loading} placeholder="16.00" />
              </div>
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="unidad_medida">Unidad de medida: *</label>
              <input className="input" type="text" id="unidad_medida" name="unidad_medida" value={formData.unidad_medida} onChange={handleChange} required disabled={loading} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="category_id">Categoría *</label>
                <select className="select" id="category_id" name="category_id" value={formData.category_id} onChange={handleChange} required disabled={loading}>
                  <option value="">Seleccionar categoría</option>
                  {categories.map(cat => (<option key={cat.category_id} value={cat.category_id}>{cat.name}</option>))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="image_url">URL de Imagen</label>
              <div className="d-flex gap-1" style={{ display: 'flex', gap: '0.5rem' }}>
                <input className="input" type="url" id="image_url" name="image_url" value={formData.image_url} onChange={handleChange} disabled={loading} placeholder="https://ejemplo.com/imagen.jpg" style={{ flex: 1 }} />
                <label className="btn btn--secondary btn--sm" style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap' }}>
                  {uploading ? 'Subiendo...' : '📤 Subir'}
                  <input type="file" accept="image/*" onChange={handleUploadImage} style={{ display: 'none' }} disabled={uploading} />
                </label>
              </div>
              {formData.image_url && (
                <div className="image-preview mt-2">
                  <img src={formData.image_url} loading='lazy' alt="Preview del producto" onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'block'; }} />
                  <div className="image-error" style={{ display: 'none' }}>❌ No se pudo cargar la imagen</div>
                </div>
              )}
            </div>
            <div className="form-group form-group--checkbox">
              <label>
                <input className="checkbox" type="checkbox" name="is_active" checked={formData.is_active} onChange={handleChange} disabled={loading} />
                Producto activo
              </label>
            </div>
            <div className="form-group form-group--checkbox">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input className="checkbox" type="checkbox" name="lock" checked={formData.lock} onChange={handleChange} disabled={loading} />
                <span>🔒 Bloqueado / Lock ({formData.lock ? 'Habilitado / True' : 'Deshabilitado / False'})</span>
              </label>
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="edit_display_priority">Prioridad en Catálogo:</label>
              <input
                className="input"
                type="number"
                id="edit_display_priority"
                name="display_priority"
                value={formData.display_priority}
                onChange={handleChange}
                placeholder="1000000 (1 a 999,999 para fijar al frente)"
                min="1"
                disabled={loading}
              />
              <small style={{ color: 'var(--color-text-secondary, #64748b)', fontSize: '0.8rem', display: 'block', marginTop: '0.25rem' }}>
                💡 De 1 a 999,999 fija el producto al inicio del catálogo. De 1,000,000 en adelante rota semanalmente.
              </small>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="edit_created_at">Fecha de Creación:</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="edit_created_at"
                  name="created_at"
                  value={formData.created_at}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
              <div className="form-group">
                <label className="form-group__label" htmlFor="edit_updated_at">Última Actualización:</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="edit_updated_at"
                  name="updated_at"
                  value={formData.updated_at}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
            </div>
            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={onClose} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn btn--primary" disabled={loading}>{loading ? 'Guardando...' : 'Guardar Cambios'}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
