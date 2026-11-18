import { useState, useEffect } from 'react';
import announcementService from '../../services/announcementService';

/**
 * Modal para crear o editar un anuncio (Pop-up, Story o Footer Banner).
 * Sigue la misma estructura y clases SCSS de ModalAddProduct / ModalPromoAdItem.
 */
export default function ModalAnnouncementForm({
  isOpen,
  onClose,
  onSaved,
  editingItem = null,
  canUpload = false,
}) {
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    type: 'popup',
    status: 'activo',
    start_date: '',
    end_date: '',
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setError('');
    setSelectedFile(null);

    if (editingItem) {
      setFormData({
        title: editingItem.title || '',
        content: editingItem.content || '',
        type: editingItem.type || 'popup',
        status: editingItem.status || 'activo',
        start_date: editingItem.start_date ? new Date(editingItem.start_date).toISOString().slice(0, 16) : '',
        end_date: editingItem.end_date ? new Date(editingItem.end_date).toISOString().slice(0, 16) : '',
      });
      setPreviewUrl(editingItem.img_url || '');
    } else {
      setFormData({
        title: '',
        content: '',
        type: 'popup',
        status: 'activo',
        start_date: new Date().toISOString().slice(0, 16),
        end_date: '',
      });
      setPreviewUrl('');
    }
  }, [isOpen, editingItem]);

  useEffect(() => {
    if (!selectedFile) return undefined;
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setUploading(true);
    setError('');
    try {
      const payload = {
        title: formData.title,
        content: formData.content,
        type: formData.type,
        status: formData.status,
        start_date: new Date(formData.start_date).toISOString(),
        end_date: formData.end_date ? new Date(formData.end_date).toISOString() : null,
      };

      if (selectedFile) {
        const uploadRes = await announcementService.uploadPromoImage(selectedFile);
        payload.img = uploadRes.img_key;
      }

      if (editingItem) {
        await announcementService.updateAnnouncement(editingItem.id, payload);
      } else {
        await announcementService.createAnnouncement(payload);
      }

      onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al guardar el anuncio.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2>{editingItem ? 'Editar Anuncio' : 'Nuevo Anuncio'}</h2>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar modal">×</button>
        </div>

        <div className="modal__body">
          <form onSubmit={handleSubmit} className="modal__form">
            {error && <div className="alert alert--danger">{error}</div>}

            <div className="form-group">
              <label className="form-group__label" htmlFor="announcement_title">Título *</label>
              <input
                className="input"
                type="text"
                id="announcement_title"
                name="title"
                value={formData.title}
                onChange={handleChange}
                required
                maxLength={150}
                disabled={uploading}
                placeholder="Ej: Promoción de Temporada"
              />
            </div>

            <div className="form-group">
              <label className="form-group__label" htmlFor="announcement_content">Contenido *</label>
              <textarea
                className="textarea"
                id="announcement_content"
                name="content"
                value={formData.content}
                onChange={handleChange}
                required
                rows={3}
                disabled={uploading}
                placeholder="Descripción o mensaje del anuncio..."
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="announcement_type">Tipo *</label>
                <select
                  className="select"
                  id="announcement_type"
                  name="type"
                  value={formData.type}
                  onChange={handleChange}
                  disabled={uploading}
                >
                  <option value="popup">Pop-up (Emergente)</option>
                  <option value="story">Story</option>
                  <option value="footer">Footer Banner</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-group__label" htmlFor="announcement_status">Estado *</label>
                <select
                  className="select"
                  id="announcement_status"
                  name="status"
                  value={formData.status}
                  onChange={handleChange}
                  disabled={uploading}
                >
                  <option value="activo">Activo</option>
                  <option value="inactivo">Inactivo</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-group__label" htmlFor="announcement_start_date">Fecha de Inicio *</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="announcement_start_date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleChange}
                  required
                  disabled={uploading}
                />
              </div>

              <div className="form-group">
                <label className="form-group__label" htmlFor="announcement_end_date">Fecha de Fin (Opcional)</label>
                <input
                  className="input"
                  type="datetime-local"
                  id="announcement_end_date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleChange}
                  disabled={uploading}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-group__label">Imagen / Promocional</label>
              <div className="promo-ads-admin__upload-row">
                <input
                  className="input promo-ads-admin__upload-input"
                  type="text"
                  value={selectedFile ? selectedFile.name : editingItem?.img_url ? 'Imagen actual vinculada' : ''}
                  readOnly
                  placeholder={canUpload || editingItem ? 'Selecciona una imagen...' : 'Sin permiso para subir'}
                />
                {(canUpload || editingItem) && (
                  <label className="btn btn--secondary btn--sm promo-ads-admin__upload-btn">
                    📤 Subir
                    <input
                      type="file"
                      accept="image/*"
                      className="promo-ads-admin__hidden-file"
                      disabled={uploading || (!canUpload && !editingItem)}
                      onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    />
                  </label>
                )}
              </div>
              {!canUpload && !editingItem && (
                <small className="text-muted">No tienes permiso para subir nuevas imágenes promocionales.</small>
              )}
              {previewUrl && (
                <div className="image-preview mt-2">
                  <img src={previewUrl} alt="Preview del anuncio" loading="lazy" />
                </div>
              )}
            </div>

            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={onClose} disabled={uploading}>
                Cancelar
              </button>
              <button type="submit" className="btn btn--primary" disabled={uploading}>
                {uploading ? 'Guardando...' : editingItem ? 'Guardar Cambios' : 'Guardar Anuncio'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
