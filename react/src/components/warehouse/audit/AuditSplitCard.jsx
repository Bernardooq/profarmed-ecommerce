import React, { useState, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faLock, faClock, faUserTie, faShieldAlt,
  faEdit, faCog, faListCheck, faChevronDown,
  faChevronUp, faSearch, faTimes, faBarcode,
  faDollarSign, faBoxesStacked, faCheckCircle,
  faExclamationTriangle
} from '@fortawesome/free-solid-svg-icons';

export default function AuditSplitCard({
  split,
  auditData,
  isAdmin,
  canSupervisor,
  canSeeDiscrepancies,
  isWarehouseRole,
  canEditManualReason,
  getStatusBadge,
  onOpenAdminModal,
  onOpenReassignModal,
  onOpenEventsLedger,
  onOpenEditReason,
  onOpenAdminCounts
}) {
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [searchFilter, setSearchFilter] = useState('');

  // Formateadores seguros
  const formatCurrency = (amount) => {
    if (amount == null) return '—';
    return `$${Number(amount).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return null;
    try {
      const d = new Date(dateStr);
      return `${d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' })}, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return dateStr;
    }
  };

  // Alternar expansión de una partida
  const toggleItemExpand = (itemKey) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(itemKey)) {
        next.delete(itemKey);
      } else {
        next.add(itemKey);
      }
      return next;
    });
  };

  // Expandir o colapsar todas
  const toggleExpandAll = () => {
    const allKeys = [];
    containersWithProducts.forEach(c => {
      (c.items || []).forEach(it => {
        allKeys.push(`${c.container_id || 'direct'}-${it.order_item_id || it.product_id}`);
      });
    });
    if (expandedItems.size >= allKeys.length && allKeys.length > 0) {
      setExpandedItems(new Set());
    } else {
      setExpandedItems(new Set(allKeys));
    }
  };

  // Sello inviolable sin duplicar prefijo SL-
  const sealFolio = split.security_seal_folio
    ? (String(split.security_seal_folio).startsWith('SL-') ? split.security_seal_folio : `SL-${split.security_seal_folio}`)
    : null;

  // Mapa de items completos de la split indexados por product_id y order_item_id
  const splitItemsMap = useMemo(() => {
    const map = new Map();
    (split.items || []).forEach(it => {
      if (it.product_id) map.set(String(it.product_id), it);
      if (it.order_item_id) map.set(String(it.order_item_id), it);
    });
    return map;
  }, [split.items]);

  // Cálculo preciso de piezas totales en piso
  const totalSplitPieces = useMemo(() => {
    return (split.items || []).reduce((acc, it) => {
      const p1 = it.picked_total_qty ?? it.total_verified ?? 0;
      const p2 = it.checked_total_qty ?? 0;
      return acc + (p2 > 0 ? p2 : p1);
    }, 0);
  }, [split.items]);

  const totalRequiredPieces = useMemo(() => {
    return (split.items || []).reduce((acc, it) => {
      return acc + (it.quantity ?? it.quantity_required ?? it.required_quantity ?? 0);
    }, 0);
  }, [split.items]);

  // Agrupación de canastas y productos
  const containersWithProducts = useMemo(() => {
    const term = searchFilter.trim().toLowerCase();

    const matchesSearch = (item) => {
      if (!term) return true;
      return (
        item.product_name?.toLowerCase().includes(term) ||
        String(item.product_id || '').toLowerCase().includes(term) ||
        item.barcode?.toLowerCase().includes(term) ||
        item.codebar?.toLowerCase().includes(term) ||
        item.location?.toLowerCase().includes(term)
      );
    };

    // Si la split está configurada con canastas
    if (split.uses_containers) {
      if (!split.containers_summary || split.containers_summary.length === 0) {
        const directItems = (split.items || []).filter(matchesSearch);
        return [
          {
            container_id: 'empty_containers_anomaly',
            qr_code: '⚠️ Inconsistencia Forense: Split en Modo Canastas sin Canastas QR Activas (0 QR)',
            total_pieces: totalSplitPieces,
            items: directItems,
            isCanasta: false,
            isAnomaly: true
          }
        ];
      }

      const canastas = split.containers_summary.map(c => {
        const enrichedItems = (c.items || []).map(ci => {
          const full = splitItemsMap.get(String(ci.order_item_id)) || splitItemsMap.get(String(ci.product_id)) || {};
          return {
            ...full,
            ...ci,
            container_id: c.container_id,
            container_qr: c.qr_code,
            isCanastaItem: true
          };
        }).filter(matchesSearch);

        return {
          container_id: c.container_id,
          qr_code: c.qr_code,
          total_pieces: c.total_pieces,
          items: enrichedItems,
          isCanasta: true
        };
      });

      // Partidas o piezas de la split que no entraron en ninguna canasta (optimizado a O(N) con Map)
      const assignedMap = new Map();
      (split.containers_summary || []).forEach(c => {
        (c.items || []).forEach(ci => {
          const qty = ci.picked_total_qty || 0;
          if (ci.product_id) {
            const pId = String(ci.product_id);
            assignedMap.set(pId, (assignedMap.get(pId) || 0) + qty);
          }
          if (ci.order_item_id) {
            const oId = String(ci.order_item_id);
            assignedMap.set(oId, (assignedMap.get(oId) || 0) + qty);
          }
        });
      });

      const unassignedItems = [];
      (split.items || []).forEach(it => {
        const fullKey = String(it.order_item_id || it.product_id);
        const assignedInCanastas = assignedMap.get(fullKey) || assignedMap.get(String(it.product_id)) || 0;
        const itTotal = it.picked_total_qty ?? it.total_verified ?? 0;
        const unassignedQty = itTotal - assignedInCanastas;
        if (unassignedQty > 0 && matchesSearch(it)) {
          unassignedItems.push({
            ...it,
            container_id: 'unassigned',
            unassigned_qty: unassignedQty,
            isOrphan: true
          });
        }
      });

      if (unassignedItems.length > 0) {
        canastas.push({
          container_id: 'unassigned',
          qr_code: '⚠️ Surtido General / Piezas Fuera de Canasta',
          total_pieces: unassignedItems.reduce((acc, it) => acc + (it.unassigned_qty || 0), 0),
          items: unassignedItems,
          isCanasta: false,
          isOrphan: true
        });
      }

      return canastas;
    }

    // Si es Surtido Directo (sin canastas)
    const directItems = (split.items || []).filter(matchesSearch);
    return [
      {
        container_id: 'direct',
        qr_code: `Surtido Directo a Tarima / Caja Máster`,
        total_pieces: totalSplitPieces,
        items: directItems,
        isCanasta: false
      }
    ];
  }, [split.uses_containers, split.containers_summary, split.items, splitItemsMap, searchFilter, totalSplitPieces]);

  // Renderizado individual de una fila de producto y su acordeón forense
  const renderProductItem = (item, isCanasta = false) => {
    const itemKey = `${item.container_id || 'direct'}-${item.order_item_id || item.product_id}`;
    const isExpanded = expandedItems.has(itemKey);

    const fullItem = splitItemsMap.get(String(item.order_item_id)) || splitItemsMap.get(String(item.product_id)) || item;
    const req = fullItem.quantity ?? fullItem.quantity_required ?? fullItem.required_quantity ?? item.quantity ?? 0;

    // Conteo Global en todo el split
    const globalP1 = fullItem.picked_total_qty ?? fullItem.total_verified ?? 0;
    const globalP2 = fullItem.checked_total_qty ?? 0;
    const globalVerified = globalP2 > 0 ? globalP2 : globalP1;
    const globalDiff = globalVerified - req;

    // Conteo Específico en este contenedor
    const canastaP1 = item.picked_total_qty ?? item.total_verified ?? 0;
    const canastaP2 = item.checked_total_qty ?? 0;
    const canastaVerified = canastaP2 > 0 ? canastaP2 : canastaP1;

    // Balance visual
    const displayVerified = isCanasta ? canastaVerified : globalVerified;
    const diff = globalDiff;

    // Filtros de conteo para desglose pericial
    const p1 = isCanasta ? canastaP1 : globalP1;
    const p2 = isCanasta ? canastaP2 : globalP2;

    return (
      <div
        key={itemKey}
        className={`audit-product-card ${isExpanded ? 'audit-product-card--expanded' : ''} ${diff !== 0 ? 'audit-product-card--discrepancy' : ''}`}
      >
        {/* Cabecera / Fila Principal Resumida del Producto */}
        <div
          className="audit-product-card__summary"
          onClick={() => toggleItemExpand(itemKey)}
          title="Haz click para ver u ocultar el expediente forense de esta partida"
        >
          {/* Ubicación en Bodega */}
          <div className="audit-product-card__loc">
            <span className="badge badge--secondary font-mono font-bold font-xs">
              {item.location || 'SIN UBIC'}
            </span>
          </div>

          {/* Información del Producto */}
          <div className="audit-product-card__info">
            <div className="audit-product-card__name text-truncate" title={item.product_name}>
              <span className="me-1">💊</span>
              <strong>{item.product_name}</strong>
            </div>
            <div className="audit-product-card__sub text-muted font-mono font-xs">
              {item.product_id && <span>SKU: {item.product_id}</span>}
              {(item.barcode || item.codebar) && <span className="ms-2">🏷️ {item.barcode || item.codebar}</span>}
            </div>
          </div>

          {/* Balance Requerido vs Surtido */}
          <div className="audit-product-card__balance text-center">
            <div className="font-mono font-bold text-sm">
              <span className={diff < 0 ? 'text-danger' : diff > 0 ? 'text-warning' : 'text-success'}>
                {displayVerified}
              </span>
              <span className="text-muted font-normal">
                {isCanasta ? ' pz en canasta' : ` / ${req} pz`}
              </span>
            </div>
            {isCanasta && (
              <div className="text-xs text-muted font-mono mt-1">
                Total Split: <strong>{globalVerified}</strong> / {req} pz
              </div>
            )}
            <div className="d-flex align-items-center justify-content-center gap-1 font-mono font-xs text-muted mt-1">
              {(item.picked_scanned_qty ?? 0) > 0 && (
                <span className="badge badge--subtle font-xs" title="Unidades escaneadas con pistola láser">
                  🔫 {item.picked_scanned_qty} lsr
                </span>
              )}
              {(item.picked_boxes ?? 0) > 0 && (
                <span className="badge badge--subtle font-xs" title="Cajas completas cerradas">
                  📦 {item.picked_boxes} cj
                </span>
              )}
              {(item.picked_manual_qty ?? 0) > 0 && (
                <span className="badge badge--warning font-xs" title="Ingresadas manualmente por teclado">
                  ⌨️ {item.picked_manual_qty} man
                </span>
              )}
            </div>
          </div>

          {/* Dictamen Forense */}
          <div className="audit-product-card__verdict text-center">
            {diff === 0 ? (
              <span className="badge badge--success font-xs font-bold">✓ Cuadrado</span>
            ) : diff < 0 ? (
              <span className="badge badge--danger font-xs font-bold">Faltante ({diff})</span>
            ) : (
              <span className="badge badge--warning font-xs font-bold">Sobrante (+{diff})</span>
            )}
            {isCanasta && diff === 0 && canastaVerified < req && (
              <div className="text-xs text-muted mt-1">
                (multi-canasta)
              </div>
            )}
          </div>

          {/* Botones de Acción */}
          <div className="audit-product-card__actions" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="btn btn--ghost btn--xs font-bold d-flex align-items-center gap-1"
              onClick={() => toggleItemExpand(itemKey)}
            >
              <span>{isExpanded ? 'Ocultar' : 'Detalles'}</span>
              <FontAwesomeIcon icon={isExpanded ? faChevronUp : faChevronDown} />
            </button>
            {isAdmin && (
              <button
                type="button"
                className="btn btn--secondary btn--xs d-flex align-items-center gap-1 font-bold"
                onClick={() => onOpenAdminCounts(item)}
                title="Gestión Admin: Rectificar conteos de esta partida"
              >
                ✏️
              </button>
            )}
          </div>
        </div>

        {/* Acordeón Pericial Desplegable con Todos los Datos */}
        {isExpanded && (
          <div className="audit-product-card__details">
            <div className="audit-detail-grid">
              {/* Tarjeta 1: Identificación y Costos */}
              <div className="audit-detail-card">
                <div className="audit-detail-card__header">
                  <span>🏷️ Identificación & Costos</span>
                </div>
                <div className="audit-detail-card__body">
                  <div className="audit-detail-row">
                    <span className="label">Código de barras:</span>
                    <span className="val font-mono">{item.barcode || item.codebar || '—'}</span>
                  </div>
                  <div className="audit-detail-row">
                    <span className="label">Ubicación física:</span>
                    <span className="val font-mono">{item.location || 'Sin ubicación asignada'}</span>
                  </div>
                  {auditData.can_see_costs && (
                    <>
                      <div className="audit-detail-row">
                        <span className="label">Precio Base:</span>
                        <span className="val font-mono font-bold">{formatCurrency(item.base_price ?? item.unit_price)}</span>
                      </div>
                      <div className="audit-detail-row">
                        <span className="label">Precio Final c/IVA:</span>
                        <span className="val font-mono font-bold text-primary">{formatCurrency(item.final_price ?? item.final_unit_price)}</span>
                      </div>
                    </>
                  )}
                  {item.container_qr && (
                    <div className="audit-detail-row">
                      <span className="label">Canasta QR:</span>
                      <span className="val font-mono font-bold text-primary">🧺 {item.container_qr}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Tarjeta 2: 1er Filtro (Surtidor) */}
              <div className="audit-detail-card">
                <div className="audit-detail-card__header">
                  <span>🔫 1er Filtro — Surtidor de Piso</span>
                  <span className="badge badge--primary font-mono">{p1} pzs</span>
                </div>
                <div className="audit-detail-card__body">
                  <div className="audit-detail-row">
                    <span className="label">Surtido por:</span>
                    <span className="val font-bold">{item.picked_by_name || split.picker_name || 'En proceso'}</span>
                  </div>
                  <div className="audit-detail-row">
                    <span className="label">Pistola Láser:</span>
                    <span className="val font-mono font-bold">{item.picked_scanned_qty ?? 0} pz</span>
                  </div>
                  <div className="audit-detail-row">
                    <span className="label">Cajas Maestras:</span>
                    <span className="val font-mono font-bold">{item.picked_boxes ?? 0} cj ({item.picked_box_prods ?? 0} pz)</span>
                  </div>
                  <div className="audit-detail-row">
                    <span className="label">Auditoría Manual:</span>
                    <span className="val font-mono text-warning font-bold">{item.picked_manual_qty ?? 0} pz</span>
                  </div>
                  {item.picked_manual_reason && (
                    <div className="audit-detail-row audit-detail-row--alert">
                      <span className="label">Motivo manual:</span>
                      <div className="d-flex align-items-center gap-1">
                        <span className="val text-warning text-xs font-bold">{item.picked_manual_reason}</span>
                        {canEditManualReason && (
                          <button
                            type="button"
                            className="btn btn--link btn--xs text-primary p-0 ms-1"
                            onClick={() => onOpenEditReason(item)}
                            title="Editar justificación manual"
                          >
                            <FontAwesomeIcon icon={faEdit} />
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                  {canEditManualReason && !item.picked_manual_reason && (item.picked_manual_qty ?? 0) > 0 && (
                    <button
                      type="button"
                      className="btn btn--outline btn--xs text-warning mt-2 d-inline-flex align-items-center gap-1 font-bold"
                      onClick={() => onOpenEditReason(item)}
                    >
                      <FontAwesomeIcon icon={faEdit} />
                      <span>+ Justificar conteo manual</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Tarjeta 3: 2do Filtro (Revisor) */}
              <div className="audit-detail-card">
                <div className="audit-detail-card__header">
                  <span>🔬 2do Filtro — Mesa de Calidad</span>
                  <span className="badge badge--info font-mono">{p2} pzs</span>
                </div>
                <div className="audit-detail-card__body">
                  <div className="audit-detail-row">
                    <span className="label">Revisado por:</span>
                    <span className="val font-bold">{item.checked_by_name || split.checker_name || 'Sin asignar'}</span>
                  </div>
                  <div className="audit-detail-row">
                    <span className="label">Pistola Láser:</span>
                    <span className="val font-mono font-bold">{item.checked_scanned_qty ?? 0} pz</span>
                  </div>
                  <div className="audit-detail-row">
                    <span className="label">Cajas Maestras:</span>
                    <span className="val font-mono font-bold">{item.checked_boxes ?? 0} cj ({item.checked_box_prods ?? 0} pz)</span>
                  </div>
                  <div className="audit-detail-row">
                    <span className="label">Validación Manual:</span>
                    <span className="val font-mono text-warning font-bold">{item.checked_manual_qty ?? 0} pz</span>
                  </div>
                  {item.checked_manual_reason && (
                    <div className="audit-detail-row audit-detail-row--alert">
                      <span className="label">Nota Revisor:</span>
                      <span className="val text-warning text-xs font-bold">{item.checked_manual_reason}</span>
                    </div>
                  )}
                  {item.discrepancy_note && (
                    <div className="audit-detail-row audit-detail-row--alert">
                      <span className="label">Discrepancia:</span>
                      <span className="val text-danger text-xs font-bold">{item.discrepancy_note}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="warehouse-audit-modal__split-card mb-4">
      {/* Header Ejecutivo de la Split */}
      <div className="warehouse-audit-modal__split-card-header">
        <div className="d-flex align-items-center gap-3 flex-wrap">
          <span className="text-xl">{split.uses_containers ? '🧺' : '📦'}</span>
          <h4 className="m-0 font-bold">
            Split #{split.split_number ?? 1} de {auditData.total_splits}
            {split.split_code && <span className="ms-2 font-mono text-xs text-muted">🏷️ Lote: {split.split_code}</span>}
          </h4>
          <span className="ms-1">{getStatusBadge(split.status)}</span>
          {sealFolio && (
            <span className="badge badge--success font-mono text-xs font-bold" title="Cincho inviolable de seguridad verificado">
              <FontAwesomeIcon icon={faLock} className="me-1" />
              {sealFolio}
            </span>
          )}
          {split.uses_containers ? (
            <span className="badge badge--primary font-mono text-xs font-bold">
              🧺 Modo Canastas ({split.containers_summary?.length || 0} QR)
            </span>
          ) : (
            <span className="badge badge--secondary font-mono text-xs font-bold">
              📦 Surtido Directo
            </span>
          )}
        </div>

        <div className="d-flex align-items-center gap-2 flex-wrap">
          {/* Botón Bitácora */}
          <button
            type="button"
            className="btn btn--outline btn--xs text-primary d-flex align-items-center gap-1 font-bold"
            onClick={() => onOpenEventsLedger(split)}
            title="Ver Bitácora Forense de Escaneos y Línea de Tiempo de este Split"
          >
            <FontAwesomeIcon icon={faListCheck} />
            <span>Bitácora</span>
          </button>

          {/* Botón Reasignar Split */}
          {(isAdmin || canSupervisor) && (
            <button
              type="button"
              className="btn btn--outline btn--xs d-flex align-items-center gap-1 font-bold"
              onClick={() => onOpenReassignModal(split)}
              title="Reasignar picker o revisor"
            >
              <FontAwesomeIcon icon={faUserTie} />
              <span>Reasignar</span>
            </button>
          )}

          {/* Botón Gestión Admin */}
          {isAdmin && (
            <button
              type="button"
              className="btn btn--secondary btn--xs d-flex align-items-center gap-1 font-bold"
              onClick={() => onOpenAdminModal(split)}
              title="Gestión de estatus y sellos"
            >
              <FontAwesomeIcon icon={faCog} />
              <span>Gestión Admin</span>
            </button>
          )}
        </div>
      </div>

      {/* Fila de Metadatos y Tiempos de Auditoría (Restaurada al diseño limpio natural) */}
      <div className="warehouse-audit-modal__split-meta-bar">
        <div className="d-flex align-items-center gap-4 flex-wrap text-xs">
          {split.split_code && (
            <div>
              <span className="text-muted">Etiqueta / Lote: </span>
              <span className="font-bold font-mono">{split.split_code}</span>
            </div>
          )}
          <div>
            <span className="text-muted">Picker: </span>
            <span className="font-bold">{split.picker_name || 'Sin asignar'}</span>
          </div>
          <div>
            <span className="text-muted">Checker: </span>
            <span className="font-bold">{split.checker_name || 'Sin asignar'}</span>
          </div>
          <div>
            <span className="text-muted">Partidas: </span>
            <span className="font-bold">
              {split.items?.length || 0} productos ({totalSplitPieces} de {totalRequiredPieces} pzs)
            </span>
          </div>
          {split.picking_started_at && (
            <div>
              <span className="text-muted">🚀 Inicio: </span>
              <span className="font-mono">{formatDateTime(split.picking_started_at)}</span>
            </div>
          )}
          {split.picking_completed_at && (
            <div>
              <span className="text-muted">🏁 Fin Surtido: </span>
              <span className="font-mono">{formatDateTime(split.picking_completed_at)}</span>
            </div>
          )}
          {split.duration_formatted && (
            <div>
              <span className="badge badge--info font-bold font-mono">
                ⏱️ Surtido: {split.duration_formatted}
              </span>
            </div>
          )}
          {split.checking_completed_at && (
            <div>
              <span className="text-muted">🔍 Fin 2do Filtro: </span>
              <span className="font-mono">{formatDateTime(split.checking_completed_at)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Barra de Filtro de Productos y Controles de Expansión */}
      <div className="d-flex justify-content-between align-items-center p-3 border-bottom bg-subtle flex-wrap gap-2">
        <div className="d-flex align-items-center gap-2 flex-1" style={{ minWidth: '220px', maxWidth: '380px' }}>
          <div className="search-bar position-relative w-100">
            <input
              type="text"
              className="input input--sm w-100"
              placeholder="Buscar por SKU, nombre, código o ubicación..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
            {searchFilter && (
              <button
                type="button"
                className="btn btn--ghost btn--xs position-absolute right-1 top-50 translate-middle-y text-muted"
                onClick={() => setSearchFilter('')}
                title="Limpiar filtro"
              >
                <FontAwesomeIcon icon={faTimes} />
              </button>
            )}
          </div>
        </div>

        <button
          type="button"
          className="btn btn--ghost btn--xs font-bold d-flex align-items-center gap-1 text-primary"
          onClick={toggleExpandAll}
        >
          <span>{expandedItems.size > 0 ? '▲ Colapsar Todo' : '▼ Expandir Todo'}</span>
        </button>
      </div>

      {/* Contenido Forense: Contenedores Físicos con sus Productos Integrados */}
      {split.is_blind_masked ? (
        <div className="alert alert--warning d-flex align-items-center gap-3 m-3">
          <span className="text-2xl"><FontAwesomeIcon icon={faLock} /></span>
          <div>
            <strong>Partidas protegidas por modo Surtido Ciego</strong>
            <p className="m-0 text-xs text-muted">
              Este split no fue asignado a tu usuario. Sus partidas físicas permanecen confidenciales hasta que el pedido sea completado y sellado.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-3">
          {containersWithProducts.map((container, cIdx) => (
            <div key={container.container_id || cIdx} className="audit-container-card mb-4">
              {/* Header de la Canasta / Contenedor */}
              <div className="audit-container-card__header">
                <div className="d-flex align-items-center gap-2">
                  <span className="text-lg">{container.isCanasta ? '🧺' : '📦'}</span>
                  <div>
                    <h5 className="m-0 font-mono font-bold text-sm text-primary">
                      {container.qr_code}
                    </h5>
                    <span className="text-xs text-muted">
                      {container.items.length} producto(s) en este contenedor
                    </span>
                  </div>
                </div>
                <div className="text-end">
                  <span className="badge badge--primary font-mono font-bold text-xs">
                    Total: {container.total_pieces} pzs
                  </span>
                </div>
              </div>

              {/* Lista de Productos de la Canasta */}
              <div className="audit-container-card__body">
                {container.items.length === 0 ? (
                  <div className="text-center py-3 text-muted text-xs">
                    No se encontraron productos coincidentes en este contenedor.
                  </div>
                ) : (
                  container.items.map(item => renderProductItem(item, container.isCanasta))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
