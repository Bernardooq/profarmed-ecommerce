import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faSearch, faFilter, faShieldHalved,
  faQrcode, faCheckCircle, faExclamationTriangle
} from '@fortawesome/free-solid-svg-icons';

export default function LedgerItemsTab({
  items,
  hasContainers,
  containersSummary,
  filterContainer,
  setFilterContainer,
  filterMethod,
  setFilterMethod,
  searchQuery,
  setSearchQuery,
  isFilter2Omitted = false
}) {
  return (
    <div>
      {/* Filtros de Partidas */}
      <div className="d-flex align-items-center gap-2 flex-wrap mb-3">
        <div className="d-flex align-items-center gap-1 flex-1" style={{ minWidth: '220px' }}>
          <FontAwesomeIcon icon={faSearch} className="text-muted" />
          <input
            type="text"
            className="input input--sm w-100"
            placeholder="Buscar por SKU, nombre, código de barras o pasillo..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {hasContainers && (
          <div className="d-flex align-items-center gap-1">
            <FontAwesomeIcon icon={faQrcode} className="text-muted text-xs" />
            <select
              className="select select--sm"
              value={filterContainer}
              onChange={(e) => setFilterContainer(e.target.value)}
            >
              <option value="">Todas las Canastas ({containersSummary?.length || 0})</option>
              {containersSummary?.map(c => (
                <option key={c.container_id} value={c.qr_code}>
                  {c.qr_code} ({c.total_products} SKUs)
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="d-flex align-items-center gap-1">
          <FontAwesomeIcon icon={faFilter} className="text-muted text-xs" />
          <select
            className="select select--sm"
            value={filterMethod}
            onChange={(e) => setFilterMethod(e.target.value)}
          >
            <option value="all">Todos los Métodos</option>
            <option value="laser">🔫 Pistola Láser</option>
            <option value="box">📦 Caja Cerrada</option>
            <option value="manual">✍️ Manual / Teclado</option>
          </select>
        </div>

        {(filterContainer || searchQuery || filterMethod !== 'all') && (
          <button
            type="button"
            className="btn btn--ghost btn--xs text-muted"
            onClick={() => {
              setFilterContainer('');
              setSearchQuery('');
              setFilterMethod('all');
            }}
          >
            Limpiar
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <div className="text-center py-5 text-muted bg-surface rounded border border-dashed">
          <FontAwesomeIcon icon={faShieldHalved} size="2x" className="mb-2 opacity-50 text-muted" />
          <p className="m-0">No se encontraron partidas con los filtros especificados.</p>
        </div>
      ) : (
        <div className="table-responsive border rounded bg-surface" style={{ maxHeight: '55vh', overflowY: 'auto' }}>
          <table className="data-table m-0">
            <thead>
              <tr>
                {hasContainers && <th>Canasta QR</th>}
                <th>Producto / Ubicación</th>
                <th className="text-center">1er Filtro (Surtido)</th>
                <th className="text-center">2do Filtro (Revisión)</th>
                <th className="text-center">Estado</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => {
                const isMatch = item.picked_total_qty === item.checked_total_qty && item.picked_total_qty > 0;
                return (
                  <tr key={item.container_item_id || item.product_id}>
                    {hasContainers && (
                      <td data-label="Canasta QR" className="text-nowrap">
                        <span className="container-qr-badge">
                          <FontAwesomeIcon icon={faQrcode} />
                          {item.container_qr || 'Sin Canasta'}
                        </span>
                      </td>
                    )}
                    <td data-label="Producto">
                      <div className="fw-bold font-sans text-sm">{item.product_name || item.product_id}</div>
                      <div className="text-muted text-xs d-flex align-items-center gap-2 flex-wrap mt-1">
                        <span className="badge badge--dark font-mono text-xs">SKU: {item.product_id}</span>
                        {item.barcode && <span>🏷️ {item.barcode}</span>}
                        {item.location && <span className="text-info font-mono">📍 {item.location}</span>}
                      </div>
                    </td>
                    <td data-label="1er Filtro (Surtido)" className="text-center">
                      <span className="fw-bold text-success text-sm">
                        {item.picked_total_qty} pz
                      </span>
                      <div className="d-flex justify-content-center gap-1 flex-wrap mt-1">
                        {item.picked_scanned_qty > 0 && (
                          <span className="audit-method-tag audit-method-tag--laser" title="Piezas leídas con pistola láser">
                            🔫 {item.picked_scanned_qty}
                          </span>
                        )}
                        {item.picked_box_prods > 0 && (
                          <span className="audit-method-tag audit-method-tag--box" title="Cajas maestras selladas">
                            📦 {item.picked_boxes} cj ({item.picked_box_prods} pz)
                          </span>
                        )}
                        {item.picked_manual_qty > 0 && (
                          <span className="audit-method-tag audit-method-tag--manual" title={item.manual_reason ? `Motivo: ${item.manual_reason}` : 'Conteo manual'}>
                            ✍️ {item.picked_manual_qty}
                          </span>
                        )}
                      </div>
                      {item.manual_reason && (
                        <div className="text-xs text-warning mt-1 text-truncate" style={{ maxWidth: '180px' }} title={item.manual_reason}>
                          💬 {item.manual_reason}
                        </div>
                      )}
                    </td>
                    <td data-label="2do Filtro (Revisión)" className="text-center">
                      {isFilter2Omitted ? (
                        <span className="text-muted text-xs font-mono">
                          — (Salida Directa)
                        </span>
                      ) : (
                        <>
                          <span className={`fw-bold text-sm ${isMatch ? 'text-success' : 'text-warning'}`}>
                            {item.checked_total_qty || 0} pz
                          </span>
                          <div className="d-flex justify-content-center gap-1 flex-wrap mt-1">
                            {item.checked_scanned_qty > 0 && (
                              <span className="audit-method-tag audit-method-tag--laser" title="Verificado con pistola láser">
                                🔫 {item.checked_scanned_qty}
                              </span>
                            )}
                            {item.checked_box_prods > 0 && (
                              <span className="audit-method-tag audit-method-tag--box" title="Cajas validadas">
                                📦 {item.checked_boxes} cj ({item.checked_box_prods} pz)
                              </span>
                            )}
                            {item.checked_manual_qty > 0 && (
                              <span className="audit-method-tag audit-method-tag--manual" title={item.checker_manual_reason ? `Motivo: ${item.checker_manual_reason}` : 'Revisión manual'}>
                                ✍️ {item.checked_manual_qty}
                              </span>
                            )}
                          </div>
                          {item.checker_manual_reason && (
                            <div className="text-xs text-warning mt-1 text-truncate" style={{ maxWidth: '180px' }} title={item.checker_manual_reason}>
                              💬 {item.checker_manual_reason}
                            </div>
                          )}
                        </>
                      )}
                    </td>
                    <td data-label="Estado" className="text-center">
                      {isMatch ? (
                        <span className="badge badge--success" title="Cantidades coinciden exactamente">
                          <FontAwesomeIcon icon={faCheckCircle} className="me-1" /> OK
                        </span>
                      ) : isFilter2Omitted ? (
                        <span className="badge badge--success" title="Surtido completo sin 2do filtro">
                          <FontAwesomeIcon icon={faCheckCircle} className="me-1" /> Surtido OK
                        </span>
                      ) : (
                        <span className="badge badge--warning" title="Diferencia detectada">
                          <FontAwesomeIcon icon={faExclamationTriangle} className="me-1" />
                          Dif ({item.picked_total_qty - item.checked_total_qty} pz)
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
