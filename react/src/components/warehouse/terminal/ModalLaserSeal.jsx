import React from 'react';

/**
 * ModalLaserSeal.jsx
 * Modal para confirmación de sellado inviolable y registro de folios SL-.
 */
export default function ModalLaserSeal({
  isOpen,
  onClose,
  split,
  hasActiveDiscrepancy,
  itemsWithDiscrepancy = [],
  sealMode,
  setSealMode,
  sealFolio,
  setSealFolio,
  onSubmit,
  loading
}) {
  if (!isOpen || !split) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm warehouse-terminal-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2 m-0 text-base font-bold">
            <span>🔒</span> Sellar Split y Finalizar Empaque
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={onSubmit} className="warehouse-terminal__modal-form">
          <div className="modal__body">
            {hasActiveDiscrepancy ? (
              <div className="alert alert--danger mb-3 text-xs leading-normal">
                <strong>⚠️ ADVERTENCIA DE DISCREPANCIA EN 2DO FILTRO:</strong>
                <p className="m-0 mt-1">
                  Existen <strong>{itemsWithDiscrepancy.length} partidas con diferencias</strong> físicas entre lo recolectado por el Picker y lo contado por el Revisor:
                </p>
                <ul className="mt-2 mb-2 ps-3 font-semibold">
                  {itemsWithDiscrepancy.map((it) => {
                    const pQty = it.total_verified || 0;
                    const cQty = it.checker_total_verified || 0;
                    const reqQty = it.quantity ?? it.quantity_required ?? 0;
                    const diff = cQty - pQty;
                    return (
                      <li key={it.order_item_id || it.product_id} className="mb-1">
                        <strong>{it.product_name}</strong> (Req: {reqQty} pz):
                        <span className="ms-1">Surtidor contó <strong>{pQty}</strong> vs Revisor contó <strong>{cQty}</strong> ({diff > 0 ? `+${diff} excedente` : `${diff} faltante`})</span>
                      </li>
                    );
                  })}
                </ul>
                <p className="m-0 text-muted">
                  ¿Deseas continuar y sellar el split a pesar de estas diferencias? Las discrepancias quedarán asentadas permanentemente en el dictamen forense de auditoría.
                </p>
              </div>
            ) : (
              <div className="alert alert--success mb-4 text-sm">
                ✓ Todas las partidas de la split han sido verificadas al 100%.
              </div>
            )}

            <div className="form-group mb-4">
              <label className="form-group__label mb-2 font-bold">¿Cómo vas a cerrar este paquete?:</label>
              <div className="warehouse-terminal__seal-options-list">
                <label className={`warehouse-terminal__seal-option ${sealMode === 'auto' ? 'warehouse-terminal__seal-option--active' : ''}`}>
                  <input
                    type="radio"
                    name="sealMode"
                    value="auto"
                    checked={sealMode === 'auto'}
                    onChange={() => {
                      setSealMode('auto');
                      if (!sealFolio || !sealFolio.startsWith('SL-')) {
                        setSealFolio(`SL-${split.order_id}-${split.split_number ?? split.split_index ?? 1}-${Math.floor(1000 + Math.random() * 9000)}`);
                      }
                    }}
                  />
                  <div className="warehouse-terminal__seal-option-content">
                    <strong>⚡ Folio Automático del Sistema (Recomendado)</strong>
                    <span className="text-xs text-muted d-block">El sistema genera y registra un folio único automáticamente. No requieres cincho numerado.</span>
                  </div>
                </label>

                <label className={`warehouse-terminal__seal-option ${sealMode === 'physical' ? 'warehouse-terminal__seal-option--active' : ''}`}>
                  <input
                    type="radio"
                    name="sealMode"
                    value="physical"
                    checked={sealMode === 'physical'}
                    onChange={() => {
                      setSealMode('physical');
                      setSealFolio('');
                    }}
                  />
                  <div className="warehouse-terminal__seal-option-content">
                    <strong>🏷️ Cincho de Seguridad o Cinta Rotulada</strong>
                    <span className="text-xs text-muted d-block">Dispara la pistola lectora sobre el código impreso en el cincho físico o escribe su folio.</span>
                  </div>
                </label>

                <label className={`warehouse-terminal__seal-option ${sealMode === 'none' ? 'warehouse-terminal__seal-option--active' : ''}`}>
                  <input
                    type="radio"
                    name="sealMode"
                    value="none"
                    checked={sealMode === 'none'}
                    onChange={() => {
                      setSealMode('none');
                      setSealFolio('');
                    }}
                  />
                  <div className="warehouse-terminal__seal-option-content">
                    <strong>📦 Empaque Estándar (Cinta Tradicional)</strong>
                    <span className="text-xs text-muted d-block">Empaque cerrado de forma ordinaria sin folio de cincho numerado.</span>
                  </div>
                </label>
              </div>
            </div>

            {sealMode === 'auto' && (
              <div className="form-group mb-3">
                <label className="form-group__label">Folio Automático del Sistema:</label>
                <div className="warehouse-terminal__folio-wrap">
                  <input
                    type="text"
                    className="input font-mono font-bold"
                    value={sealFolio}
                    onChange={(e) => setSealFolio(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    onClick={() => setSealFolio(`SL-${split.order_id}-${split.split_number ?? split.split_index ?? 1}-${Math.floor(1000 + Math.random() * 9000)}`)}
                    title="Generar otro código"
                  >
                    🔄 Nuevo
                  </button>
                </div>
                <span className="text-xs text-muted mt-1 d-block">
                  Candado digital consecutivo registrado para auditoría y despacho.
                </span>
              </div>
            )}

            {sealMode === 'physical' && (
              <div className="form-group mb-3">
                <label className="form-group__label" htmlFor="seal_folio">
                  Folio de Cinta de Seguridad o Cincho Físico:
                </label>
                <input
                  id="seal_folio"
                  type="text"
                  className="input font-mono font-bold"
                  placeholder="Escanea con láser o teclea el folio..."
                  value={sealFolio}
                  onChange={(e) => setSealFolio(e.target.value)}
                  autoFocus
                  required
                />
                <span className="text-xs text-muted mt-1 d-block">
                  Dispara la pistola lectora sobre el código de la cinta o cincho de seguridad.
                </span>
              </div>
            )}

            {sealMode === 'none' && (
              <div className="alert alert--info text-xs mb-3">
                ℹ️ El sello inviolable es opcional. El split quedará completada bajo modalidad de empaque estándar.
              </div>
            )}
          </div>

          <div className="modal__footer warehouse-terminal__modal-footer-responsive">
            <button type="button" className="btn btn--secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn--primary warehouse-seal-btn" disabled={loading}>
              {loading ? 'Sellando...' : (sealMode === 'none' ? 'Finalizar Empaque' : '🔒 Confirmar y Sellar Split')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
