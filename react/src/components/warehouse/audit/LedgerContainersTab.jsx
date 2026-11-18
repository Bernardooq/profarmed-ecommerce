import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faQrcode, faCheckCircle, faExclamationTriangle,
  faBoxOpen, faListCheck
} from '@fortawesome/free-solid-svg-icons';

export default function LedgerContainersTab({
  containersSummary,
  onSelectContainer,
  onGoToItems,
  isFilter2Omitted = false
}) {
  if (!containersSummary || containersSummary.length === 0) {
    return (
      <div className="text-center py-5 text-muted bg-surface rounded-lg border border-dashed p-4">
        <FontAwesomeIcon icon={faBoxOpen} size="2x" className="mb-2 text-primary opacity-75" />
        <h4 className="font-bold text-base mb-1">Modalidad de Surtido Directo</h4>
        <p className="text-muted text-sm max-w-md mx-auto mb-3">
          Este split fue procesado directamente del estante al empaque final sin requerir canastas intermedias de traslado.
        </p>
        <button
          type="button"
          className="btn btn--primary btn--sm"
          onClick={onGoToItems}
        >
          <FontAwesomeIcon icon={faListCheck} className="me-1" />
          Ver Partidas Verificadas Directas
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {containersSummary.map(c => {
        const items = c.items || [];
        const pickedTotal = c.picked_total_units ?? (items.length > 0 ? items.reduce((sum, it) => sum + (it.picked_total_qty || 0), 0) : (c.total_pieces ?? 0));
        const pickedLaser = c.picked_laser_qty ?? items.reduce((sum, it) => sum + (it.picked_scanned_qty || 0), 0);
        const pickedBoxes = c.picked_boxes ?? items.reduce((sum, it) => sum + (it.picked_boxes || 0), 0);
        const pickedBoxProds = c.picked_box_prods ?? items.reduce((sum, it) => sum + (it.picked_box_prods || 0), 0);
        const pickedManual = c.picked_manual_qty ?? items.reduce((sum, it) => sum + (it.picked_manual_qty || 0), 0);

        const checkedTotal = c.checked_total_units ?? items.reduce((sum, it) => sum + (it.checked_total_qty || 0), 0);
        const checkedLaser = c.checked_laser_qty ?? items.reduce((sum, it) => sum + (it.checked_scanned_qty || 0), 0);
        const checkedBoxes = c.checked_boxes ?? items.reduce((sum, it) => sum + (it.checked_boxes || 0), 0);
        const checkedBoxProds = c.checked_box_prods ?? items.reduce((sum, it) => sum + (it.checked_box_prods || 0), 0);
        const checkedManual = c.checked_manual_qty ?? items.reduce((sum, it) => sum + (it.checked_manual_qty || 0), 0);

        const isCheckedOk = (checkedTotal === pickedTotal && pickedTotal > 0) || (isFilter2Omitted && pickedTotal > 0);

        return (
          <div key={c.container_id} className="warehouse-audit-modal__split-card shadow-xs">
            <div className="warehouse-audit-modal__split-card-header">
              <div className="d-flex align-items-center gap-2">
                <span className="container-qr-badge">
                  <FontAwesomeIcon icon={faQrcode} className="text-primary" />
                  {c.qr_code}
                </span>
                <span className={`container-status-pill ${c.status === 'in_use' ? 'container-status-pill--in_use' : 'container-status-pill--available'}`}>
                  {c.status === 'in_use' ? 'En Uso' : c.status}
                </span>
              </div>
              <button
                type="button"
                className="btn btn--link btn--xs text-primary p-0 font-bold"
                onClick={() => onSelectContainer(c.qr_code)}
              >
                Ver productos →
              </button>
            </div>

            <div className="p-3">
              <div className="d-flex justify-content-between text-xs mb-2">
                <span className="text-muted">Productos distintos:</span>
                <strong>{c.total_products} SKUs</strong>
              </div>

              {/* Desglose 1er Filtro */}
              <div className="bg-subtle p-2 rounded mb-2 text-xs border border-subtle">
                <div className="d-flex justify-content-between font-bold text-success mb-1">
                  <span>1er Filtro (Surtido):</span>
                  <span>{pickedTotal} pz</span>
                </div>
                <div className="d-flex gap-2 flex-wrap mt-1">
                  {pickedLaser > 0 && (
                    <span className="audit-method-tag audit-method-tag--laser">
                      🔫 {pickedLaser} pz
                    </span>
                  )}
                  {pickedBoxProds > 0 && (
                    <span className="audit-method-tag audit-method-tag--box">
                      📦 {pickedBoxes} cj ({pickedBoxProds} pz)
                    </span>
                  )}
                  {pickedManual > 0 && (
                    <span className="audit-method-tag audit-method-tag--manual">
                      ✍️ {pickedManual} pz
                    </span>
                  )}
                </div>
              </div>

              {/* Desglose 2do Filtro */}
              <div className="bg-subtle p-2 rounded text-xs border border-subtle">
                <div className="d-flex justify-content-between font-bold text-primary mb-1">
                  <span>2do Filtro (Revisión):</span>
                  <span>{isFilter2Omitted ? 'Omitido (Salida Directa)' : `${checkedTotal} pz`}</span>
                </div>
                {isFilter2Omitted ? (
                  <div className="text-muted text-xs mt-1">
                    Completado en piso sin segundo filtro
                  </div>
                ) : (
                  <div className="d-flex gap-2 flex-wrap mt-1">
                    {checkedLaser > 0 && (
                      <span className="audit-method-tag audit-method-tag--laser">
                        🔫 {checkedLaser} pz
                      </span>
                    )}
                    {checkedBoxProds > 0 && (
                      <span className="audit-method-tag audit-method-tag--box">
                        📦 {checkedBoxes} cj ({checkedBoxProds} pz)
                      </span>
                    )}
                    {checkedManual > 0 && (
                      <span className="audit-method-tag audit-method-tag--manual">
                        ✍️ {checkedManual} pz
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div className="mt-2 pt-2 border-top d-flex justify-content-between align-items-center text-xs">
                <span className="text-muted">Balance Canasta:</span>
                {isCheckedOk ? (
                  <span className="warehouse-audit-modal__diff-alert warehouse-audit-modal__diff-alert--ok d-flex align-items-center gap-1">
                    <FontAwesomeIcon icon={faCheckCircle} /> {isFilter2Omitted ? `Cuadrada en Surtido (${pickedTotal} pz)` : 'Cuadrada 100%'}
                  </span>
                ) : (
                  <span className="warehouse-audit-modal__diff-alert warehouse-audit-modal__diff-alert--mismatch d-flex align-items-center gap-1">
                    <FontAwesomeIcon icon={faExclamationTriangle} /> Pendiente ({pickedTotal - checkedTotal} pz)
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
