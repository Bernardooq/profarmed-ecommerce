import React from 'react';

export default function LaserStationHeader({
  split,
  isSegundoFiltro,
  hasActiveDiscrepancy,
  itemsWithDiscrepancy,
  onBackToQueue,
  setShowEventsLedger,
  isAllVerified,
  canSendToFilter2,
  canSealDirect,
  canChecker,
  canFastTrack,
  handleSendToSegundoFiltro,
  loading,
  setSealMode,
  setSealFolio,
  setShowSealModal,
  handleReturnToSurtido,
  setShowFastTrackModal,
  fastTracking,
  isAllCheckerVerified
}) {
  if (!split) return null;

  return (
    <>
      {/* Alerta explicativa de Segundo Filtro si está activo */}
      {isSegundoFiltro && (
        <div className={`alert ${hasActiveDiscrepancy ? 'alert--danger' : 'alert--warning'} p-3 mb-3`}>
          <div className="d-flex align-items-center justify-content-between flex-wrap gap-2">
            <div>
              <strong>🔍 Segundo Filtro Activo (Mesa de Revisión y Calidad):</strong>
              <span className="ms-2">
                Re-escanea con pistola láser, registra cajas o manual, o usa "Confiar en Surtido" para validar todo en bloque.
              </span>
            </div>
            {canChecker && (
              <button
                type="button"
                className="btn btn--danger btn--sm font-bold"
                onClick={handleReturnToSurtido}
                disabled={loading}
                title="Devolver split a recolector si falta algún producto o está dañado"
              >
                ↩️ Devolver a Surtido por Discrepancia
              </button>
            )}
          </div>

          {/* Banner explícito si se detectaron discrepancias */}
          {hasActiveDiscrepancy && (
            <div className="mt-2 pt-2 border-top border-danger-subtle text-xs">
              <strong className="text-danger d-block mb-1">
                ⚠️ ALERTA DE DISCREPANCIA DETECTADA ({itemsWithDiscrepancy.length} {itemsWithDiscrepancy.length === 1 ? 'partida con diferencia' : 'partidas con diferencia'}):
              </strong>
              <ul className="m-0 ps-3">
                {itemsWithDiscrepancy.map(item => {
                  const pQty = item.total_verified || 0;
                  const cQty = item.checker_total_verified || 0;
                  const diff = cQty - pQty;
                  return (
                    <li key={item.order_item_id || item.product_id} className="mb-0.5">
                      <strong>{item.product_name}</strong> (SKU: {item.product_id}): Surtidor contó <strong>{pQty}</strong> pz vs Revisor contó <strong>{cQty}</strong> pz ({diff > 0 ? `+${diff} excedente` : `${diff} faltante`}).
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Banner de Split Activa */}
      <div className="warehouse-terminal__active-banner">
        <div className="warehouse-terminal__split-headline">
          <div className="d-flex align-items-center gap-2">
            <button type="button" className="btn btn--ghost btn--sm" onClick={onBackToQueue} title="Volver a la Cola">
              ← Cola FIFO
            </button>
            {isSegundoFiltro ? (
              <span className="badge badge--warning">🔍 2DO FILTRO (REVISIÓN)</span>
            ) : (
              <span className="badge badge--primary">BODEGA PISO</span>
            )}
          </div>
          <h3>
            <span>🧺</span> Split #{split.split_number ?? split.split_index ?? 1} de {split.total_splits ?? split.total_splits_in_order ?? 1}
            <span className="text-muted fw-normal text-base ms-1">
              (Pedido #{split.order_id})
            </span>
            {split.split_code && (
              <span className="badge badge--dark ms-2 font-mono text-sm" title="Código de etiqueta física para pegatinas o rotulación">
                🏷️ Lote: {split.split_code}
              </span>
            )}
          </h3>
          <div className="warehouse-terminal__split-meta">
            <span><strong>Cliente:</strong> {split.customer_name || 'N/A'}</span>
            {(split.seller_name || split.assigned_user_name) && (
              <span><strong>Asesor:</strong> {split.seller_name || split.assigned_user_name}</span>
            )}
            <span><strong>Picker:</strong> {split.picker_name || 'Sin asignar'}</span>
            {isSegundoFiltro && (
              <span><strong>Checker (Revisor):</strong> {split.checker_name || 'Sin asignar (Pendiente)'}</span>
            )}
            <span><strong>Partidas:</strong> {split.items?.length || 0}</span>
          </div>
        </div>

        <div className="warehouse-terminal__banner-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setShowEventsLedger(true)}
            title="Ver bitácora atómica de escaneos láser y auditoría forense (Event Ledger)"
          >
            📜 Bitácora
          </button>

          {/* Si estamos en surtido ordinario y se verificó todo */}
          {!isSegundoFiltro && isAllVerified && split.status !== 'completed' && (
            <>
              {canSendToFilter2 && (
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={handleSendToSegundoFiltro}
                  disabled={loading}
                  title="Transferir a mesa de revisión para doble chequeo"
                >
                  🔍 Enviar a 2do Filtro (Opcional)
                </button>
              )}
              {canSealDirect && (
                <button
                  type="button"
                  className="btn btn--primary warehouse-seal-btn"
                  onClick={() => {
                    setSealMode('auto');
                    setSealFolio(`SL-${split.order_id}-${split.split_number ?? split.split_index ?? 1}-${Math.floor(1000 + Math.random() * 9000)}`);
                    setShowSealModal(true);
                  }}
                >
                  🔒 Sellar Split y Finalizar (Directo)
                </button>
              )}
            </>
          )}

          {/* Si estamos en Segundo Filtro */}
          {isSegundoFiltro && split.status !== 'completed' && (
            <>
              {canChecker && (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={handleReturnToSurtido}
                  disabled={loading}
                  title="Regresar a piso por discrepancia"
                >
                  ↩️ Discrepancia
                </button>
              )}
              {canFastTrack && (
                <button
                  type="button"
                  className="btn btn--info btn--sm d-flex align-items-center gap-1 font-bold"
                  onClick={() => setShowFastTrackModal(true)}
                  disabled={loading || fastTracking || isAllCheckerVerified}
                  title="Validar todo en bloque confiando en el surtido previo de piso"
                >
                  🤝 Confiar en Surtido y Validar Todo
                </button>
              )}
              {canChecker && (
                <button
                  type="button"
                  className={`btn ${hasActiveDiscrepancy ? 'btn--warning' : 'btn--primary'} warehouse-seal-btn`}
                  disabled={!isAllCheckerVerified}
                  title={isAllCheckerVerified ? (hasActiveDiscrepancy ? '⚠️ Hay discrepancia entre surtidor y revisor. Haz clic para revisar o forzar sellado.' : 'Sellar y autorizar despacho') : 'Debes revisar todas las partidas o aplicar Confianza'}
                  onClick={() => {
                    setSealMode('auto');
                    setSealFolio(`SL-${split.order_id}-${split.split_number ?? split.split_index ?? 1}-${Math.floor(1000 + Math.random() * 9000)}`);
                    setShowSealModal(true);
                  }}
                >
                  {hasActiveDiscrepancy ? '⚠️ Sellar con Discrepancia' : '🔒 Aprobar 2do Filtro y Sellar'}
                </button>
              )}
            </>
          )}

          {split.status === 'completed' && (
            <span className="warehouse-badge warehouse-badge--completed">
              ✓ Split Sellada ({split.security_seal_folio || 'CERRADA'})
            </span>
          )}
        </div>
      </div>
    </>
  );
}
