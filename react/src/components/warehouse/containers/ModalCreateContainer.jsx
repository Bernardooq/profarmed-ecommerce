import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlus } from '@fortawesome/free-solid-svg-icons';
import ErrorMessage from '../../common/ErrorMessage';

/**
 * ModalCreateContainer
 * Modal accesible y enfocado para enrolar nuevas canastas QR físicas.
 */
export default function ModalCreateContainer({
  isOpen = false,
  onClose,
  onSubmit
}) {
  const [qrCode, setQrCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setQrCode('');
      setError(null);
      setSubmitting(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanQr = qrCode.trim().toUpperCase();
    if (!cleanQr) {
      setError('El código QR o identificador de canasta es requerido');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      await onSubmit(cleanQr);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al enrolar canasta');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3>
            <FontAwesomeIcon icon={faPlus} className="me-2 text-primary" />
            Registrar Canasta QR
          </h3>
          <button className="modal__close" onClick={onClose} disabled={submitting}>
            &times;
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal__body">
            {error && <ErrorMessage message={error} />}
            <div className="form-group mb-3">
              <label className="form-label">
                Código QR / Identificador Físico *
              </label>
              <input
                type="text"
                className="input font-mono"
                placeholder="Ej: TOTE-001, CAN-042..."
                value={qrCode}
                onChange={(e) => setQrCode(e.target.value.toUpperCase())}
                autoFocus
                required
                disabled={submitting}
              />
              <small className="form-text text-muted">
                Escanea con la pistola láser la etiqueta física pegada a la canasta o escribe su folio identificador. Al crearla, podrás imprimir o copiar el QR generado directamente.
              </small>
            </div>
          </div>
          <div className="modal__footer">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={submitting || !qrCode.trim()}
            >
              {submitting ? 'Guardando...' : 'Enrolar Canasta'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
