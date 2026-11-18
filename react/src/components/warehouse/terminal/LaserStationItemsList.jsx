import React from 'react';

export default function LaserStationItemsList({
  sortedItems,
  split,
  isSegundoFiltro,
  isAdminOrAuditor,
  lastActiveItemId,
  copiedBarcode,
  setCopiedBarcode,
  handleDirectScan,
  scanning,
  setBoxModalItem,
  setBoxesCount,
  setUnitsPerBox,
  setBoxModalError,
  setManualModalItem,
  setManualQty,
  setManualReason,
  setCustomReason,
  setManualModalError
}) {
  if (!split) return null;

  return (
    <div className="warehouse-terminal__items-grid">
      <h4 className="mb-2">
        Partidas de la Split ({split.items?.length || 0})
      </h4>

      {sortedItems && sortedItems.map((item) => {
        const reqQty = item.quantity ?? item.quantity_required ?? 0;
        const isItemDone = isSegundoFiltro
          ? (item.checker_total_verified || 0) >= reqQty
          : (item.total_verified || 0) >= reqQty;

        const itemActiveVerified = isSegundoFiltro ? (item.checker_total_verified || 0) : (item.total_verified || 0);
        const isCurItem = (item.order_item_id || item.product_id) === lastActiveItemId;

        return (
          <div
            key={item.order_item_id || item.product_id}
            className={`warehouse-terminal__item-card ${isItemDone ? 'warehouse-terminal__item-card--complete' : ''} ${isCurItem ? 'warehouse-terminal__item-card--active-surtiendo' : ''}`}
          >
            <div className="warehouse-terminal__item-main">
              <span className="warehouse-terminal__location-tag" title="Ubicación física en anaquel">
                📍 {item.location || 'SIN UBIC'}
              </span>

              <div className="warehouse-terminal__item-info">
                <div className="d-flex align-items-center gap-2 flex-wrap">
                  <span className="warehouse-terminal__item-name">{item.product_name}</span>
                  {isCurItem && !isItemDone && (
                    <span className="badge badge--primary text-xs font-bold" title="Partida en proceso activo de escaneo">
                      {isSegundoFiltro ? '🔍 Revisando Ahora' : '🎯 Surtiendo Ahora'}
                    </span>
                  )}
                </div>

                <div
                  className={`warehouse-terminal__item-codebar-wrap ${copiedBarcode === (item.codebar || item.barcode || item.product_id) ? 'warehouse-terminal__item-codebar-wrap--copied' : ''}`}
                  onClick={(e) => {
                    if (!isItemDone && split.status !== 'completed') {
                      handleDirectScan(item.codebar || item.barcode || item.product_id, e, item);
                    } else {
                      e.stopPropagation();
                      const code = item.codebar || item.barcode || item.product_id;
                      if (navigator.clipboard?.writeText) {
                        navigator.clipboard.writeText(code).catch(() => {});
                      }
                      setCopiedBarcode(code);
                      setTimeout(() => setCopiedBarcode(null), 1500);
                    }
                  }}
                  title={isItemDone ? "Partida completada al 100% (Toca para copiar)" : "Toca para escanear +1 pieza directamente sin teclado ⚡"}
                  role="button"
                  tabIndex={0}
                >
                  <span className="warehouse-terminal__codebar-text">
                    Cód: <strong className="font-mono">{item.codebar || item.barcode || 'Sin código'}</strong> | SKU: {item.product_id}
                  </span>
                  <span className="warehouse-terminal__copy-badge">
                    {copiedBarcode === (item.codebar || item.barcode || item.product_id)
                      ? (isItemDone ? '✓ Copiado' : '⚡ ¡Escaneado!')
                      : (isItemDone ? '✓ Completo' : '⚡ Escanear +1')}
                  </span>
                </div>

                {/* Detalle de Surtido de Piso (Solo visible para el Picker en 1er filtro para evitar sesgos en la revisión ciega) */}
                {!isSegundoFiltro && (
                  <div className="text-xs text-muted mt-1">
                    {(item.scanned_prods || item.verified_by_scan_count) > 0 && `Láser: ${item.scanned_prods ?? item.verified_by_scan_count} pzs `}
                    {(item.box_prods || item.verified_by_box_count) > 0 && (
                      `| Cajas: ${item.boxes ? `${item.boxes} cja${item.boxes > 1 ? 's' : ''} (${item.box_prods ?? item.verified_by_box_count} pzs) ` : `${item.box_prods ?? item.verified_by_box_count} pzs `}`
                    )}
                    {(item.manual_prods || item.verified_by_manual_count) > 0 && `| Manual: ${item.manual_prods ?? item.verified_by_manual_count} pzs (${item.manual_reason || 'Justificado'})`}
                  </div>
                )}

                {/* Detalle de Segundo Filtro si está activo */}
                {isSegundoFiltro && (
                  <div className="text-xs text-warning mt-1">
                    <strong>Tu Revisión (2do Filtro):</strong> Láser: {item.checker_scanned_prods || 0} pzs | Cajas: {item.checker_boxes ? `${item.checker_boxes} cja${item.checker_boxes > 1 ? 's' : ''} (${item.checker_box_prods || 0} pzs)` : `${item.checker_box_prods || 0} pzs`} | Manual: {item.checker_manual_prods || 0} pzs
                    {item.checker_manual_reason && ` (${item.checker_manual_reason})`}
                  </div>
                )}

                {/* Discrepancia Forense si existe (Solo Admin / Auditor) */}
                {isAdminOrAuditor && item.has_forensic_discrepancy && (
                  <div className="badge badge--danger text-xs mt-1 warehouse-audit-modal__discrepancy-badge text-left">
                    ⚠️ {item.discrepancy_note}
                  </div>
                )}

                {/* Validado por Confianza */}
                {item.checker_manual_reason?.includes('Confianza') && (
                  <div className="badge badge--info text-xs mt-1">
                    🤝 Validado por Confianza de Surtido
                  </div>
                )}
              </div>
            </div>

            <div className="warehouse-terminal__item-stats">
              <div className="warehouse-terminal__qty-counter">
                {isSegundoFiltro ? (
                  <>
                    <span className="verified text-warning">{item.checker_total_verified || 0}</span>
                    <span className="total">/ {reqQty}</span>
                  </>
                ) : (
                  <>
                    <span className="verified">{item.total_verified || 0}</span>
                    <span className="total">/ {reqQty}</span>
                  </>
                )}
              </div>

              {split.status !== 'completed' && (
                <div className="warehouse-terminal__item-btn-group">
                  {!isItemDone ? (
                    <button
                      type="button"
                      className="btn btn--primary btn--sm warehouse-terminal__direct-scan-btn"
                      disabled={scanning}
                      title={`Escanear 1 pieza de ${item.product_name} al instante sin teclado`}
                      onClick={(e) => handleDirectScan(item.codebar || item.barcode || item.product_id, e, item)}
                    >
                      ⚡ +1 Escanear
                    </button>
                  ) : (
                    <span className="badge badge--success text-xs font-bold py-1 px-2 d-inline-flex align-items-center gap-1">
                      ✓ Completo
                    </span>
                  )}

                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    title={isSegundoFiltro ? 'Revisar por cajas maestras' : 'Registrar cajas maestras de fábrica'}
                    onClick={() => {
                      setBoxModalItem(item);
                      setBoxesCount('1');
                      const existingBoxes = isSegundoFiltro ? (item.checker_boxes || item.boxes || 0) : (item.boxes || 0);
                      const existingBoxProds = isSegundoFiltro ? (item.checker_box_prods || item.box_prods || 0) : (item.box_prods || 0);
                      let serverUnits = '10';
                      if (existingBoxes > 0 && existingBoxProds > 0) {
                        serverUnits = Math.round(existingBoxProds / existingBoxes).toString();
                      }
                      setUnitsPerBox(serverUnits);
                      setBoxModalError(null);
                    }}
                  >
                    📦 Cajas
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    title={isSegundoFiltro ? 'Revisión manual en 2do filtro' : 'Validación manual con motivo de auditoría'}
                    onClick={() => {
                      setManualModalItem(item);
                      setManualQty(Math.max(1, reqQty - itemActiveVerified).toString());
                      setManualReason(isSegundoFiltro ? 'Revisión física conforme' : 'Etiqueta o código dañado');
                      setCustomReason('');
                      setManualModalError(null);
                    }}
                  >
                    ✍️ Manual
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
