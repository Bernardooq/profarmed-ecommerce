import React from 'react';

/**
 * ModalLaserFastTrack.jsx
 * Modal para confirmar la validación en bloque por confianza de surtido de piso.
 */
export default function ModalLaserFastTrack({
  isOpen,
  onClose,
  split,
  totalRequired,
  onConfirm,
  loading
}) {
  if (!isOpen || !split) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2 m-0 text-base text-info">
            <span>🤝</span> Confiar en Surtido y Validar Todo
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal__body">
          <p className="text-sm mb-3">
            ¿Deseas validar en bloque todas las partidas de la <strong>Split #{split.split_number ?? 1}</strong> confiando en la recolección física realizada por <strong>{split.picker_name || 'el recolector'}</strong>?
          </p>
          <div className="alert alert--info text-xs mb-3 leading-normal">
            <strong>ℹ️ Agilidad Operativa:</strong>
            <p className="m-0 mt-1">
              Se registrarán las <strong>{totalRequired} piezas</strong> como verificadas por ti en el 2do Filtro bajo el concepto <em>"Validado por Confianza de Surtido"</em>, permitiéndote sellar de inmediato el split.
            </p>
          </div>
          <p className="text-xs text-muted m-0">
            Esta acción queda registrada en el expediente forense de auditoría.
          </p>
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
            className="btn btn--info font-bold"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Validando...' : '🤝 Sí, Confiar y Validar Todo'}
          </button>
        </div>
      </div>
    </div>
  );
}
