import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTrash, faBan, faExclamationTriangle, faRotate } from '@fortawesome/free-solid-svg-icons';

/**
 * ModalDeleteContainer
 * Modal de confirmación defensiva con advertencia de auditoría, despliegue interno de errores (409)
 * y opción alternativa de retiro (baja).
 */
export default function ModalDeleteContainer({
  container = null,
  isOpen = false,
  onClose,
  onConfirmDelete,
  onRetireContainer,
  deleting = false,
  error = null
}) {
  if (!isOpen || !container) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="text-danger">
            <FontAwesomeIcon icon={faTrash} className="me-2" />
            Eliminar Canasta QR
          </h3>
          <button className="modal__close" onClick={onClose} disabled={deleting}>
            &times;
          </button>
        </div>
        <div className="modal__body">
          <p className="mb-3">
            ¿Deseas eliminar permanentemente la canasta física <strong>{container.qr_code}</strong>?
          </p>

          {/* Si hubo un error del servidor (ej: 409 conflicto por auditoría), mostrarlo aquí dentro */}
          {error ? (
            <div className="alert alert--danger mb-3" style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <FontAwesomeIcon icon={faExclamationTriangle} className="text-danger mt-1" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <strong className="d-block mb-1 text-danger">No se puede eliminar la canasta:</strong>
                <span className="text-xs" style={{ lineHeight: '1.45', display: 'block', wordBreak: 'break-word' }}>
                  {error}
                </span>
              </div>
            </div>
          ) : (
            <div className="alert alert--warning mb-3" style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <FontAwesomeIcon icon={faExclamationTriangle} className="text-warning mt-1" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <strong className="d-block mb-1 text-warning">Regla de Trazabilidad y Auditoría:</strong>
                <span className="text-xs" style={{ lineHeight: '1.45', display: 'block' }}>
                  Si esta canasta ya fue utilizada en el surtido o revisión de algún pedido previo, el sistema <strong>rechazará su eliminación</strong> para preservar la trazabilidad forense. En ese caso, debes cambiar su estado a <strong>Retirada / Baja</strong>.
                </span>
              </div>
            </div>
          )}

          <p className="text-muted text-xs mb-0">
            Solo canastas creadas por error que nunca hayan participado en ningún split pueden eliminarse por completo.
          </p>
        </div>

        <div
          className="modal__footer"
          style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}
        >
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onClose}
            disabled={deleting}
          >
            Cancelar
          </button>

          {container.status !== 'retired' && (
            <button
              type="button"
              className={error ? 'btn btn--warning font-bold' : 'btn btn--warning'}
              onClick={() => onRetireContainer(container)}
              disabled={deleting}
              title="Dar de baja sin perder el historial de pedidos anteriores"
            >
              <FontAwesomeIcon icon={faBan} className="me-1" />
              Marcar como Retirada (Baja)
            </button>
          )}

          <button
            type="button"
            className="btn btn--danger"
            onClick={onConfirmDelete}
            disabled={deleting}
          >
            {deleting ? (
              <>
                <FontAwesomeIcon icon={faRotate} spin className="me-1" />
                Eliminando...
              </>
            ) : (
              'Eliminar Definitivamente'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
