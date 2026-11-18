import React from 'react';

/**
 * ModalLaserManual.jsx
 * Modal para validación manual justificada con selector de causas de auditoría.
 */
export default function ModalLaserManual({
  item,
  isSegundoFiltro,
  manualQty,
  setManualQty,
  manualReason,
  setManualReason,
  customReason,
  setCustomReason,
  manualModalError,
  onClose,
  onSubmit,
  loading
}) {
  if (!item) return null;

  const requiredQty = item.quantity ?? item.quantity_required ?? 0;
  const currentVerified = isSegundoFiltro ? (item.checker_total_verified || 0) : (item.total_verified || 0);
  const remainingQty = Math.max(0, requiredQty - currentVerified);
  const parsedManualQty = parseInt(manualQty, 10) || 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2">
            <span>✍️</span> {isSegundoFiltro ? 'Revisión Manual de Piezas' : 'Conteo Manual de Piezas'}
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={onSubmit} className="warehouse-terminal__modal-form">
          <div className="modal__body">
            <p className="text-sm font-bold mb-1">{item.product_name}</p>

            {manualModalError && (
              <div className="alert alert--danger text-xs mb-3 leading-normal">
                <strong>⚠️ Atención:</strong> {manualModalError}
              </div>
            )}
            
            {/* Banner de Ayuda Rápida */}
            <div className="alert alert--info p-3 mb-3 text-xs leading-normal">
              <div className="d-flex align-items-center gap-1 mb-1 font-bold">
                <span>💡</span> ¿Cuándo usar conteo manual?
              </div>
              <p className="m-0">
                Úsalo cuando la etiqueta física esté rota, borrosa, manchada o el producto venga sin código de barras de fábrica.
              </p>
            </div>

            {/* Resumen de piezas */}
            <div className="d-flex justify-content-between align-items-center mb-3 p-2 bg-light rounded text-xs">
              <span>Requerido: <strong>{requiredQty}</strong></span>
              <span>{isSegundoFiltro ? 'Revisado (2do Filtro):' : 'Verificado (Surtido):'} <strong className="text-primary">{currentVerified}</strong></span>
              <span>Pendientes: <strong className="text-warning">{remainingQty}</strong></span>
            </div>

            {remainingQty === 0 ? (
              <div className="alert alert--success p-3 mb-3 text-xs leading-normal">
                <strong>✓ Partida Completa (100%):</strong>
                <p className="m-0 mt-1">
                  Esta partida ya tiene todas sus <strong>{requiredQty} piezas</strong> {isSegundoFiltro ? 'revisadas en 2do filtro' : 'verificadas en surtido'}. No se requieren más piezas.
                </p>
              </div>
            ) : (
              <>
                <div className="form-group mb-3">
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <label className="form-group__label mb-0">Piezas a validar manualmente:</label>
                    <button
                      type="button"
                      className="btn btn--ghost btn--xs text-primary font-bold"
                      onClick={() => setManualQty(remainingQty.toString())}
                      title="Llenar con el total de piezas faltantes"
                    >
                      ⚡ Completar restantes ({remainingQty})
                    </button>
                  </div>
                  <input
                    type="number"
                    min="1"
                    max={remainingQty}
                    className="input"
                    value={manualQty}
                    onChange={(e) => setManualQty(e.target.value)}
                    onBlur={() => {
                      const val = parseInt(manualQty, 10);
                      if (!manualQty || isNaN(val) || val < 1) setManualQty('1');
                      else if (val > remainingQty) setManualQty(remainingQty.toString());
                    }}
                    autoFocus
                    required
                  />
                  {parsedManualQty > 0 && parsedManualQty < remainingQty && (
                    <div className="alert alert--warning p-2 mt-2 mb-0 text-xs">
                      ℹ️ Se registrarán <strong>{parsedManualQty} de {remainingQty}</strong> faltantes. La partida quedará en surtido parcial ({currentVerified + parsedManualQty}/{requiredQty}) hasta validar las {remainingQty - parsedManualQty} restantes.
                    </div>
                  )}
                </div>

                <div className="form-group mb-3">
                  <label className="form-group__label">Motivo justificado de auditoría:</label>
                  <select
                    className="input"
                    value={manualReason}
                    onChange={(e) => setManualReason(e.target.value)}
                  >
                    <option value="Rapidez operativa (flujo ágil)">⚡ Rapidez operativa (flujo ágil / alta demanda)</option>
                    <option value="Etiqueta o código dañado">Etiqueta o código de barras dañado / ilegible</option>
                    <option value="Producto sin código de barras">Producto sin código de barras de origen</option>
                    <option value="Código borroso o manchado">Código borroso o manchado</option>
                    <option value="Lote / Presentación especial">Lote o presentación especial autorizada</option>
                    <option value="Ajuste final de surtido">Ajuste final de surtido de partidas restantes</option>
                    <option value="Otro">Otro motivo (especificar)</option>
                  </select>
                </div>

                {manualReason === 'Otro' && (
                  <div className="form-group mb-3">
                    <label className="form-group__label">Describe el motivo:</label>
                    <input
                      type="text"
                      className="input"
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      placeholder="Explica la razón pericial..."
                      required
                    />
                  </div>
                )}
              </>
            )}
          </div>

          <div className="modal__footer warehouse-terminal__modal-footer-responsive">
            <button type="button" className="btn btn--secondary" onClick={onClose}>
              {remainingQty === 0 ? 'Cerrar' : 'Cancelar'}
            </button>
            {remainingQty > 0 && (
              <button type="submit" className="btn btn--primary" disabled={loading}>
                {loading ? 'Registrando...' : 'Registrar Verificación'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
