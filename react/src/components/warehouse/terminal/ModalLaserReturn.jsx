import React from 'react';

/**
 * ModalLaserReturn.jsx
 * Modal para devolver split a piso de surtido por discrepancia física.
 */
export default function ModalLaserReturn({
  isOpen,
  onClose,
  split,
  onConfirm,
  loading
}) {
  if (!isOpen || !split) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2 m-0 text-base text-warning">
            <span>↩️</span> Devolver a Piso de Surtido
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal__body">
          <p className="text-sm mb-3">
            ¿Confirmas que deseas devolver la <strong>Split #{split.split_number ?? 1}</strong> a piso de surtido por discrepancia física?
          </p>
          <div className="alert alert--warning text-xs mb-3 leading-normal">
            <strong>⚠️ Discrepancia Física:</strong>
            <p className="m-0 mt-1">
              El estatus de el split cambiará a <em>"in_progress" (En Surtido)</em> para que el recolector subsane los faltantes o productos incorrectos antes de volver a enviarla a revisión.
            </p>
          </div>
        </div>
        <div className="modal__footer">
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onClose}
            disabled={loading}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn--danger font-bold"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Devolviendo...' : '↩️ Confirmar Devolución a Surtido'}
          </button>
        </div>
      </div>
    </div>
  );
}
