import React, { useState, useEffect, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faBoxesStacked, faQrcode, faClock, faRotate,
  faCheckCircle, faExclamationTriangle, faListCheck,
  faUser, faBoxOpen, faLock
} from '@fortawesome/free-solid-svg-icons';
import warehouseService from '../../services/warehouseService';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import LedgerTimelineTab from './audit/LedgerTimelineTab';
import LedgerContainersTab from './audit/LedgerContainersTab';
import LedgerItemsTab from './audit/LedgerItemsTab';

export default function ModalWarehouseEventsLedger({
  isOpen,
  onClose,
  splitId,
  splitCode,
  orderId,
  split,
  orderAuditData
}) {
  const [containersSummary, setContainersSummary] = useState([]);
  const [containerItems, setContainerItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modalidad operativa del Split
  const hasContainers = split?.uses_containers === true || containersSummary.length > 0;

  // Pestañas disponibles: 'timeline' | 'containers' | 'items'
  const [activeTab, setActiveTab] = useState(hasContainers ? 'containers' : 'timeline');
  const [filterContainer, setFilterContainer] = useState('');
  const [filterMethod, setFilterMethod] = useState('all'); // 'all' | 'laser' | 'box' | 'manual'
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (isOpen && splitId) {
      loadData();
    }
  }, [isOpen, splitId]);

  useEffect(() => {
    // Si no tiene canastas, por defecto ir a la línea de tiempo
    if (!hasContainers && activeTab === 'containers') {
      setActiveTab('timeline');
    }
  }, [hasContainers]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [summaryRes, itemsRes] = await Promise.all([
        warehouseService.getSplitContainersSummary(splitId).catch(() => []),
        warehouseService.getSplitContainerItems(splitId).catch(() => [])
      ]);
      setContainersSummary(Array.isArray(summaryRes) ? summaryRes : []);
      setContainerItems(Array.isArray(itemsRes) ? itemsRes : []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al cargar bitácora');
    } finally {
      setLoading(false);
    }
  };

  // Consolidar partidas: Si hay partidas por canasta las usamos; si es modo directo, usamos split.items
  const consolidatedItems = useMemo(() => {
    if (containerItems && containerItems.length > 0) {
      return containerItems;
    }
    if (split && Array.isArray(split.items) && split.items.length > 0) {
      return split.items.map((item, idx) => ({
        container_item_id: `direct-${item.product_id || idx}`,
        container_qr: 'Surtido Directo',
        product_id: item.product_id,
        product_name: item.product_name,
        barcode: item.barcode,
        location: item.location,
        requested_qty: item.quantity ?? item.requested_quantity ?? 0,
        picked_total_qty: (item.scanned_prods || 0) + (item.box_prods || 0) + (item.manual_prods || 0),
        picked_scanned_qty: item.scanned_prods || 0,
        picked_boxes: item.boxes || 0,
        picked_box_prods: item.box_prods || 0,
        picked_manual_qty: item.manual_prods || 0,
        manual_reason: item.manual_reason,
        checked_total_qty: item.is_checked
          ? ((item.scanned_prods || 0) + (item.box_prods || 0) + (item.manual_prods || 0))
          : 0,
        checked_scanned_qty: item.scanned_prods || 0,
        checked_boxes: item.boxes || 0,
        checked_box_prods: item.box_prods || 0,
        checked_manual_qty: item.manual_prods || 0,
        checker_status: item.checker_status || (item.is_checked ? 'checked' : 'pending'),
        checker_manual_reason: item.checker_manual_reason,
        updated_at: split.completed_at || split.started_at
      }));
    }
    return [];
  }, [containerItems, split]);

  // Filtrado de partidas
  const filteredItems = useMemo(() => {
    return consolidatedItems.filter(item => {
      if (filterContainer && item.container_qr !== filterContainer) return false;
      if (filterMethod === 'laser' && (item.picked_scanned_qty || 0) <= 0) return false;
      if (filterMethod === 'box' && (item.picked_box_prods || 0) <= 0) return false;
      if (filterMethod === 'manual' && (item.picked_manual_qty || 0) <= 0) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchSku = item.product_id?.toLowerCase().includes(q);
        const matchName = item.product_name?.toLowerCase().includes(q);
        const matchBarcode = item.barcode?.toLowerCase().includes(q);
        const matchQr = item.container_qr?.toLowerCase().includes(q);
        const matchLoc = item.location?.toLowerCase().includes(q);
        if (!matchSku && !matchName && !matchBarcode && !matchQr && !matchLoc) return false;
      }
      return true;
    });
  }, [consolidatedItems, filterContainer, filterMethod, searchQuery]);

  // Totales acumulados
  const totalContainers = containersSummary.length;
  const totalProducts = consolidatedItems.length;
  const totalPickedUnits = consolidatedItems.reduce((acc, it) => acc + (it.picked_total_qty || 0), 0);
  const totalCheckedUnits = consolidatedItems.reduce((acc, it) => acc + (it.checked_total_qty || 0), 0);
  const totalLaserUnits = consolidatedItems.reduce((acc, it) => acc + (it.picked_scanned_qty || 0), 0);
  const totalBoxUnits = consolidatedItems.reduce((acc, it) => acc + (it.picked_box_prods || 0), 0);
  const totalManualUnits = consolidatedItems.reduce((acc, it) => acc + (it.picked_manual_qty || 0), 0);

  // Determinar si el 2do filtro fue omitido (pasó directo o fue completado/sellado sin revisor)
  const isFilter2Omitted = useMemo(() => {
    const isCompletedOrSealed =
      split?.status === 'completed' ||
      split?.status === 'in_progress_full' ||
      Boolean(split?.security_seal_folio) ||
      Boolean(split?.completed_at);

    const hasNoChecker =
      !split?.checker_name ||
      split?.checker_name === 'Sin asignar' ||
      split?.checker_name === 'En mesa de control' ||
      !split?.checker_id;

    return isCompletedOrSealed && totalCheckedUnits === 0 && totalPickedUnits > 0 && hasNoChecker;
  }, [split, totalCheckedUnits, totalPickedUnits]);

  const isBalanced = totalPickedUnits > 0 && (totalCheckedUnits === totalPickedUnits || isFilter2Omitted);

  if (!isOpen) return null;

  return (
    <div
      className="modal-overlay"
      style={{ zIndex: 1060 }}
      onClick={(e) => {
        e.stopPropagation();
        onClose?.();
      }}
    >
      <div
        className="modal modal--lg"
        style={{
          maxWidth: '1050px',
          width: '95%',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cabecera Ejecutiva */}
        <div className="modal__header">
          <div className="d-flex align-items-center gap-3">
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                background: hasContainers ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: hasContainers ? '#3b82f6' : '#10b981',
                fontSize: '1.2rem'
              }}
            >
              <FontAwesomeIcon icon={hasContainers ? faBoxesStacked : faBoxOpen} />
            </div>
            <div>
              <h3 className="m-0 d-flex align-items-center gap-2 flex-wrap">
                <span>
                  {hasContainers
                    ? 'Bitácora de Surtido por Canastas QR'
                    : 'Bitácora de Trazabilidad y Surtido Directo'}
                </span>
                <span className="badge badge--dark text-primary font-mono text-xs">
                  Split #{split?.split_number ?? 1}
                </span>
                {orderId && (
                  <span className="badge badge--secondary font-mono text-xs">
                    Pedido #{orderId}
                  </span>
                )}
              </h3>
              <small className="text-muted d-block mt-1">
                {hasContainers
                  ? `Trazabilidad física agrupada en ${totalContainers} canastas QR para auditoría de custodia.`
                  : 'Recolección directa a empaque final en piso de bodega sin canastas intermedias.'}
              </small>
            </div>
          </div>
          <button
            className="modal__close"
            onClick={(e) => {
              e.stopPropagation();
              onClose?.();
            }}
            aria-label="Cerrar modal"
          >
            &times;
          </button>
        </div>

        <div className="modal__body p-3 p-md-4 warehouse-audit-modal" style={{ overflowY: 'auto' }}>
          {error && <ErrorMessage message={error} />}

          {/* KPI Grid Ejecutivo para dueños de negocio */}
          <div className="warehouse-audit-modal__kpi-grid">
            <div className={`warehouse-audit-modal__kpi-card ${isBalanced ? 'warehouse-audit-modal__kpi-card--success' : 'warehouse-audit-modal__kpi-card--warning'}`}>
              <div className="warehouse-audit-modal__kpi-icon text-primary">
                <FontAwesomeIcon icon={isBalanced ? faCheckCircle : faExclamationTriangle} />
              </div>
              <div className="warehouse-audit-modal__kpi-content">
                <span className="kpi-label">Balance de Unidades</span>
                <div className="kpi-val">
                  {isFilter2Omitted ? totalPickedUnits : totalCheckedUnits} / {totalPickedUnits} <small className="text-xs fw-normal text-muted">pz</small>
                </div>
                <span className="kpi-sub">
                  {isFilter2Omitted
                    ? '✓ 100% Cuadrado (Salida Directa sin 2do Filtro)'
                    : isBalanced
                      ? '✓ 100% Cuadrado entre Surtido y Revisión'
                      : `Diferencia de ${totalPickedUnits - totalCheckedUnits} pz`}
                </span>
              </div>
            </div>

            <div className="warehouse-audit-modal__kpi-card warehouse-audit-modal__kpi-card--highlight">
              <div className="warehouse-audit-modal__kpi-icon text-info">
                <FontAwesomeIcon icon={hasContainers ? faQrcode : faBoxOpen} />
              </div>
              <div className="warehouse-audit-modal__kpi-content">
                <span className="kpi-label">Modalidad Operativa</span>
                <div className="kpi-val text-info">
                  {hasContainers ? `${totalContainers} Canastas QR` : 'Surtido Directo'}
                </div>
                <span className="kpi-sub">
                  {hasContainers ? `${totalProducts} SKUs distribuidos` : 'Directo a caja de despacho final'}
                </span>
              </div>
            </div>

            <div className="warehouse-audit-modal__kpi-card">
              <div className="warehouse-audit-modal__kpi-icon text-success">
                <FontAwesomeIcon icon={faUser} />
              </div>
              <div className="warehouse-audit-modal__kpi-content">
                <span className="kpi-label">Custodia / Personal</span>
                <div className="kpi-val text-sm font-sans">
                  {split?.picker_name || 'En asignación'}
                </div>
                <span className="kpi-sub">
                  Revisor: <strong>{split?.checker_name && split.checker_name !== 'Sin asignar' ? split.checker_name : (isFilter2Omitted ? 'No requerido (Salida Directa)' : 'En mesa de control')}</strong>
                </span>
              </div>
            </div>

            <div className="warehouse-audit-modal__kpi-card">
              <div className="warehouse-audit-modal__kpi-icon text-warning">
                <FontAwesomeIcon icon={faLock} />
              </div>
              <div className="warehouse-audit-modal__kpi-content">
                <span className="kpi-label">Cincho de Seguridad</span>
                <div className="kpi-val font-mono text-sm">
                  {split?.security_seal_folio ? (
                    <span className="text-primary font-bold">🔒 #{split.security_seal_folio}</span>
                  ) : (
                    <span className="text-muted text-xs">Sin precinto</span>
                  )}
                </div>
                <span className="kpi-sub">
                  Estado: <strong className="text-uppercase">{split?.status || 'Procesando'}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Barra de pestañas BEM */}
          <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
            <div className="tabs m-0 p-0 border-0">
              <button
                type="button"
                className={`tabs__btn ${activeTab === 'timeline' ? 'tabs__btn--active' : ''}`}
                onClick={() => setActiveTab('timeline')}
              >
                <FontAwesomeIcon icon={faClock} />
                Línea de Tiempo Operativa
              </button>

              {hasContainers && (
                <button
                  type="button"
                  className={`tabs__btn ${activeTab === 'containers' ? 'tabs__btn--active' : ''}`}
                  onClick={() => setActiveTab('containers')}
                >
                  <FontAwesomeIcon icon={faQrcode} />
                  Canastas Físicas ({totalContainers})
                </button>
              )}

              <button
                type="button"
                className={`tabs__btn ${activeTab === 'items' ? 'tabs__btn--active' : ''}`}
                onClick={() => setActiveTab('items')}
              >
                <FontAwesomeIcon icon={faListCheck} />
                Partidas y Métodos ({totalProducts})
              </button>
            </div>

            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={loadData}
              disabled={loading}
              title="Actualizar datos"
            >
              <FontAwesomeIcon icon={faRotate} spin={loading} />
            </button>
          </div>

          {loading ? (
            <LoadingSpinner message="Cargando trazabilidad operativa..." />
          ) : activeTab === 'timeline' ? (
            <LedgerTimelineTab
              split={split}
              splitCode={splitCode}
              splitId={splitId}
              orderAuditData={orderAuditData}
              hasContainers={hasContainers}
              totalProducts={totalProducts}
              totalPickedUnits={totalPickedUnits}
              totalCheckedUnits={totalCheckedUnits}
              totalLaserUnits={totalLaserUnits}
              totalBoxUnits={totalBoxUnits}
              totalManualUnits={totalManualUnits}
              isBalanced={isBalanced}
              isFilter2Omitted={isFilter2Omitted}
            />
          ) : activeTab === 'containers' ? (
            <LedgerContainersTab
              containersSummary={containersSummary}
              onSelectContainer={(qr) => {
                setFilterContainer(qr);
                setActiveTab('items');
              }}
              onGoToItems={() => setActiveTab('items')}
              isFilter2Omitted={isFilter2Omitted}
            />
          ) : (
            <LedgerItemsTab
              items={filteredItems}
              hasContainers={hasContainers}
              containersSummary={containersSummary}
              filterContainer={filterContainer}
              setFilterContainer={setFilterContainer}
              filterMethod={filterMethod}
              setFilterMethod={setFilterMethod}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              isFilter2Omitted={isFilter2Omitted}
            />
          )}
        </div>

        {/* Pie del modal con balance y cierre */}
        <div className="modal__footer d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div className="d-flex align-items-center gap-2 text-xs flex-wrap">
            <span className="audit-method-tag audit-method-tag--laser">
              🔫 Total Láser: {totalLaserUnits} pz
            </span>
            <span className="audit-method-tag audit-method-tag--box">
              📦 Total Cajas: {totalBoxUnits} pz
            </span>
            <span className="audit-method-tag audit-method-tag--manual">
              ✍️ Total Manual: {totalManualUnits} pz
            </span>
          </div>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={(e) => {
              e.stopPropagation();
              onClose?.();
            }}
          >
            Cerrar Bitácora
          </button>
        </div>
      </div>
    </div>
  );
}
