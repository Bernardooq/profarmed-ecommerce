import React from 'react';

/**
 * ModalLaserBoxes.jsx
 * Modal para empaque rápido y registro por Cajas Maestras en la estación láser.
 */
export default function ModalLaserBoxes({
  item,
  isSegundoFiltro,
  boxesCount,
  setBoxesCount,
  unitsPerBox,
  setUnitsPerBox,
  boxModalError,
  setBoxModalError,
  onClose,
  onSubmit,
  loading
}) {
  if (!item) return null;

  const req = item.quantity ?? item.quantity_required ?? 0;
  const prevBoxes = isSegundoFiltro ? (item.checker_boxes || 0) : (item.boxes || 0);
  const prevBoxProds = isSegundoFiltro ? (item.checker_box_prods || 0) : (item.box_prods || 0);
  const prevUnits = (prevBoxes > 0 && prevBoxProds > 0) ? Math.round(prevBoxProds / prevBoxes) : 0;

  const otherVerified = isSegundoFiltro
    ? ((item.checker_scanned_prods || 0) + (item.checker_manual_prods || 0))
    : ((item.scanned_prods || 0) + (item.manual_prods || 0));

  const count = parseInt(boxesCount, 10) || 0;
  const units = parseInt(unitsPerBox, 10) || 0;
  const isChangingUnitSize = prevUnits > 0 && units > 0 && units !== prevUnits;

  // Si cambia el tamaño de caja, las cajas previas se reemplazan con el nuevo tamaño
  const available = Math.max(0, req - otherVerified - (isChangingUnitSize ? 0 : prevBoxProds));
  const totalToAdd = count * units;
  const isExcess = totalToAdd > available;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2">
            <span>📦</span> Empaque Cajas Maestras
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={onSubmit} className="warehouse-terminal__modal-form">
          <div className="modal__body">
            <p className="text-sm font-bold mb-2">{item.product_name}</p>

            {boxModalError && (
              <div className="alert alert--danger text-xs mb-3 leading-normal">
                <strong>⚠️ Atención:</strong> {boxModalError}
              </div>
            )}

            {isChangingUnitSize && (
              <div className="alert alert--warning text-xs mb-3 leading-normal">
                <strong>🔄 Cambio de tamaño de caja detectado:</strong> Previamente se registraron cajas de <strong>{prevUnits} pzs</strong>. Al confirmar con <strong>{units} pzs/caja</strong>, el registro anterior de cajas ({prevBoxes} cjas = {prevBoxProds} pz) se reajustará al nuevo tamaño para mantener conteos exactos.
              </div>
            )}

            <div className="d-flex justify-content-between align-items-center mb-3 p-3 bg-light rounded text-xs border">
              <span>Total Requerido: <strong>{req} pzs</strong></span>
              <span>Láser / Manual: <strong className="text-primary">{otherVerified} pzs</strong></span>
              <span>Pendiente para Cajas: <strong className="text-warning font-bold">{available} pzs</strong></span>
            </div>

            <div className="form-group mb-3">
              <label className="form-group__label font-bold">1. ¿Cuántas piezas vienen por cada caja?:</label>
              <input
                type="number"
                min="1"
                className="input text-base font-bold"
                value={unitsPerBox}
                onChange={(e) => {
                  setUnitsPerBox(e.target.value);
                  setBoxModalError(null);
                }}
                onBlur={() => {
                  if (!unitsPerBox || parseInt(unitsPerBox, 10) < 1) setUnitsPerBox('1');
                }}
                required
              />
              <small className="text-muted text-xs">
                Ejemplo: si la caja sellada trae 10 piezas, escribe 10.
              </small>
            </div>

            <div className="form-group mb-3">
              <div className="d-flex justify-content-between align-items-center mb-1 flex-wrap gap-1">
                <label className="form-group__label font-bold mb-0">2. ¿Cuántas cajas completas tienes?:</label>
                <div className="d-flex gap-1 flex-wrap">
                  <button
                    type="button"
                    className="btn btn--secondary btn--xs"
                    onClick={() => setBoxesCount('1')}
                  >
                    1 Caja
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary btn--xs"
                    onClick={() => setBoxesCount('2')}
                  >
                    2 Cajas
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary btn--xs font-bold"
                    onClick={() => {
                      const u = parseInt(unitsPerBox, 10) || 1;
                      const maxBoxes = Math.max(1, Math.floor(available / u));
                      setBoxesCount(maxBoxes.toString());
                    }}
                  >
                    Llenar Faltante ({Math.max(1, Math.floor(available / (parseInt(unitsPerBox, 10) || 1)))})
                  </button>
                </div>
              </div>
              <input
                type="number"
                min="1"
                className="input text-base font-bold"
                value={boxesCount}
                onChange={(e) => {
                  setBoxesCount(e.target.value);
                  setBoxModalError(null);
                }}
                onBlur={() => {
                  if (!boxesCount || parseInt(boxesCount, 10) < 1) setBoxesCount('1');
                }}
                autoFocus
                required
              />
            </div>

            <div className={`alert ${isExcess ? 'alert--danger' : 'alert--info'} text-sm p-3`}>
              <div className="d-flex align-items-center gap-2">
                <span className="text-lg">📦</span>
                <div>
                  <strong>Cálculo:</strong> {count} {count === 1 ? 'caja' : 'cajas'} × {units} pzs = <strong>{totalToAdd} piezas en total</strong>
                </div>
              </div>
              {isExcess && (
                <div className="text-xs mt-2 font-bold text-danger">
                  ⚠️ No caben tantas piezas: Solo faltan {available} piezas. Reduce las cajas o las piezas por caja.
                </div>
              )}
            </div>
          </div>

          <div className="modal__footer warehouse-terminal__modal-footer-responsive">
            <button type="button" className="btn btn--secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn--primary" disabled={loading || isExcess || totalToAdd < 1}>
              {loading ? 'Guardando...' : (isChangingUnitSize ? 'Reajustar y Confirmar Cajas' : 'Confirmar y Sumar Cajas')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
