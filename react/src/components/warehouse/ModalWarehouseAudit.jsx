import React, { useEffect, useState } from 'react';
import warehouseService from '../../services/warehouseService';
import LoadingSpinner from '../common/LoadingSpinner';
import PaginationButtons from '../common/PaginationButtons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLock, faCheckCircle, faClock, faUserTie, faShieldAlt, faEdit, faCog, faRotate, faListCheck, faQrcode } from '@fortawesome/free-solid-svg-icons';
import { useAuth } from '../../context/AuthContext';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import ModalReassignSplit from './ModalReassignSplit';
import ModalWarehouseEventsLedger from './ModalWarehouseEventsLedger';
import AuditKpiGrid from './audit/AuditKpiGrid';
import ModalAuditEditReason from './audit/ModalAuditEditReason';
import ModalAuditAdminSplit from './audit/ModalAuditAdminSplit';
import ModalAuditAdminCounts from './audit/ModalAuditAdminCounts';
import AuditSplitCard from './audit/AuditSplitCard';

export default function ModalWarehouseAudit({ isOpen, onClose, orderId, onAuditUpdated }) {
  const { user } = useAuth();
  const { can, isAdmin, isStaff } = usePermissions();
  const [loading, setLoading] = useState(true);
  const [auditData, setAuditData] = useState(null);
  const [error, setError] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [page, setPage] = useState(0);
  const limit = 15;

  // Capacidades dinámicas PBAC
  const canSupervisor = can(PERMISSIONS.WAREHOUSE_SUPERVISOR);
  const canAudit = can(PERMISSIONS.WAREHOUSE_AUDIT);
  const canManage = can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canOperator = can(PERMISSIONS.WAREHOUSE_OPERATOR) || can(PERMISSIONS.WAREHOUSE_CHECKER);
  // Solo Auditoría Forense, Jefatura y Administrador Global pueden ver discrepancias periciales
  const canSeeDiscrepancies = isAdmin || canAudit || canManage;
  const isWarehouseRole = !isAdmin && canOperator && !canSupervisor && !canAudit && !canManage;
  const canEditManualReason = can(PERMISSIONS.ORDERS_EDIT) || can(PERMISSIONS.WAREHOUSE_OPERATOR) || can(PERMISSIONS.WAREHOUSE_CHECKER) || isStaff;

  // Estados de submodales
  const [editingItem, setEditingItem] = useState(null);
  const [adminSplit, setAdminSplit] = useState(null);
  const [reassignSplitData, setReassignSplitData] = useState(null);
  const [selectedEventsSplit, setSelectedEventsSplit] = useState(null);
  const [adminEditingItem, setAdminEditingItem] = useState(null);
  const [togglingVisibility, setTogglingVisibility] = useState(false);

  const loadingRef = React.useRef(false);

  useEffect(() => {
    if (isOpen && orderId) {
      setFeedbackMsg(null);
      setPage(0);
      loadAudit(0);
    }
  }, [isOpen, orderId]);

  const loadAudit = async (pageToLoad = 0) => {
    if (loadingRef.current) return;
    try {
      loadingRef.current = true;
      setLoading(true);
      setError(null);
      const data = await warehouseService.getAuditBreakdown(orderId, {
        skip: pageToLoad * limit,
        limit
      });
      setAuditData(data);
    } catch (err) {
      setError(err.detail || err.message || 'No se pudo cargar la auditoría de bodega');
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  };

  // Cálculo consolidado de productos en almacén (Total en Almacén)
  const totalProductsSummary = React.useMemo(() => {
    if (!auditData?.splits) return [];
    const map = {};
    auditData.splits.forEach(split => {
      (split.items || []).forEach(it => {
        const pid = it.product_id || 'unknown';
        const name = it.product_name || `Producto ${pid}`;
        const qty = (it.total_verified ?? it.picked_total_qty) || 0;
        const req = (it.quantity ?? it.quantity_required) || 0;
        if (!map[pid]) {
          map[pid] = { product_id: pid, name, quantity: 0, required: 0 };
        }
        map[pid].quantity += qty;
        map[pid].required += req;
      });
    });
    return Object.values(map);
  }, [auditData]);

  if (!isOpen) return null;

  const totalForensicItems = auditData?.total_forensic_items ?? (auditData?.forensic_items?.length || 0);
  const totalPages = Math.max(1, Math.ceil(totalForensicItems / limit));

  const getStatusBadge = (st) => {
    switch (st) {
      case 'pending':
        return <span className="warehouse-badge warehouse-badge--pending">Pendiente FIFO</span>;
      case 'in_progress_partial':
      case 'in_progress':
        return <span className="warehouse-badge warehouse-badge--in_progress_partial">En Surtido</span>;
      case 'ready_for_check':
        return <span className="warehouse-badge warehouse-badge--checking">🔍 2do Filtro (Pendiente)</span>;
      case 'checking':
        return <span className="warehouse-badge warehouse-badge--checking">🔍 En Revisión</span>;
      case 'in_progress_full':
        return <span className="warehouse-badge warehouse-badge--in_progress_full">Surtido Completo</span>;
      case 'completed':
        return <span className="warehouse-badge warehouse-badge--completed">Completado / Sellado</span>;
      case 'cancelled':
        return <span className="warehouse-badge warehouse-badge--cancelled">Cancelado</span>;
      default:
        return <span className="warehouse-badge">{st}</span>;
    }
  };

  // Handlers para abrir submodales
  const handleOpenEditReason = (item) => setEditingItem(item);
  const handleOpenAdminModal = (split) => setAdminSplit(split);
  const handleOpenAdminCounts = (item) => setAdminEditingItem(item);


  // Alternar modo de visibilidad en bodega
  const handleToggleVisibility = async () => {
    const currentShowDetails = Boolean(auditData?.warehouse_show_details);
    const nextShowDetails = !currentShowDetails;
    const confirmMsg = nextShowDetails
      ? `¿Deseas cambiar este pedido a Modo Detallado (👁️ Detallado)?\n\nLos almacenistas podrán ver el nombre de los productos, códigos de barra y ubicaciones desde la cola FIFO antes de tomar el pedido.`
      : `¿Deseas cambiar este pedido a Modo Surtido Ciego (🔒 Surtido Ciego)?\n\nLos almacenistas verán los datos protegidos hasta que tomen el split.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      setTogglingVisibility(true);
      await warehouseService.toggleVisibility(orderId, nextShowDetails);
      setFeedbackMsg({
        type: 'success',
        text: `✓ Modo de visibilidad cambiado a '${nextShowDetails ? 'Detallado (👁️)' : 'Surtido Ciego (🔒)'}' exitosamente.`
      });
      await loadAudit(page);
      onAuditUpdated?.();
    } catch (err) {
      alert(err.detail || err.message || 'Error al cambiar visibilidad de bodega');
    } finally {
      setTogglingVisibility(false);
    }
  };

  const hasSubModalOpen = Boolean(
    selectedEventsSplit || reassignSplitData || adminEditingItem || editingItem || adminSplit
  );

  const handleOverlayClick = (e) => {
    // Si hay un submodal abierto (bitácora, reasignar, etc.), ignorar el click en el overlay principal
    if (hasSubModalOpen) return;
    onClose?.();
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal modal--full warehouse-audit-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="d-flex align-items-center gap-2">
            <span className="text-xl">🔍</span>
            <h3 className="m-0">Auditoría Forense de Bodega — Pedido #{orderId}</h3>
          </div>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar">
            &times;
          </button>
        </div>

        <div className="modal__body">
          {feedbackMsg && (
            <div className={`alert alert--${feedbackMsg.type} mb-3 d-flex justify-content-between align-items-center`}>
              <span>{feedbackMsg.text}</span>
              <button type="button" className="btn btn--ghost btn--xs" onClick={() => setFeedbackMsg(null)}>&times;</button>
            </div>
          )}

          {loading && !auditData ? (
            <LoadingSpinner message="Generando reporte pericial de auditoría..." />
          ) : error ? (
            <div className="alert alert--danger">{error}</div>
          ) : !auditData ? (
            <p>No se encontraron datos de bodega para este pedido.</p>
          ) : (
            <div className="order-details warehouse-audit-modal">
              {/* Resumen General Ejecutivo de Bodega para Toma de Decisiones */}
              <AuditKpiGrid
                auditData={auditData}
                totalProductsSummary={totalProductsSummary}
                getStatusBadge={getStatusBadge}
                isAdmin={isAdmin}
                canSupervisor={canSupervisor}
                onToggleVisibility={handleToggleVisibility}
                togglingVisibility={togglingVisibility}
              />

              {/* Lista Detallada de Splits */}
              <div className="warehouse-audit-modal__splits-list">
                {auditData.splits && auditData.splits.map((split) => (
                  <AuditSplitCard
                    key={split.split_id}
                    split={split}
                    auditData={auditData}
                    isAdmin={isAdmin}
                    canSupervisor={canSupervisor}
                    canSeeDiscrepancies={canSeeDiscrepancies}
                    isWarehouseRole={isWarehouseRole}
                    canEditManualReason={canEditManualReason}
                    getStatusBadge={getStatusBadge}
                    onOpenAdminModal={handleOpenAdminModal}
                    onOpenReassignModal={setReassignSplitData}
                    onOpenEventsLedger={setSelectedEventsSplit}
                    onOpenEditReason={handleOpenEditReason}
                    onOpenAdminCounts={handleOpenAdminCounts}
                  />
                ))}
              </div>

              {/* Resumen Global Total en Almacén (Suma de todos los splits y canastas) */}
            {totalProductsSummary.length > 0 && (
              <div className="warehouse-audit-modal__global-summary mt-4">
                <div className="warehouse-audit-modal__global-summary-header">
                  <div className="d-flex align-items-center gap-3">
                    <div className="warehouse-audit-modal__global-summary-icon">
                      <span>📊</span>
                    </div>
                    <div>
                      <h4 className="m-0 font-bold text-sm">Total en Almacén</h4>
                      <span className="text-xs text-muted">
                        {auditData.splits?.some(s => s.uses_containers)
                          ? 'Suma de todos los splits y canastas'
                          : 'Suma de todos los splits'}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-muted font-bold">
                    {totalProductsSummary.length} producto(s) en pedido
                  </div>
                </div>

                <div className="warehouse-audit-modal__global-summary-chips">
                  {totalProductsSummary.map((p, idx) => (
                    <div key={p.product_id || idx} className="warehouse-audit-modal__summary-chip">
                      <div className="d-flex align-items-center gap-2 overflow-hidden flex-1">
                        <span className="chip-icon">💊</span>
                        <span className="chip-name text-truncate" title={p.name}>{p.name}</span>
                      </div>
                      <span className="chip-badge font-mono font-bold">{p.quantity}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

              {/* Paginación Server-Side Estándar */}
              {totalPages > 1 && (
                <div className="mt-3 pt-2 border-top">
                  <PaginationButtons
                    currentPage={page}
                    lookaheadPages={Math.max(0, totalPages - 1 - page)}
                    onPageChange={setPage}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal__footer">
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Cerrar Reporte
          </button>
        </div>
      </div>

      {/* Modal para Editar Justificación / Motivo Manual */}
      <ModalAuditEditReason
        item={editingItem}
        onClose={() => setEditingItem(null)}
        onSaved={(msg) => {
          setFeedbackMsg({ type: 'success', text: msg });
          loadAudit(page);
          onAuditUpdated?.();
        }}
      />

      {/* Modal Exclusivo de Administrador: Control y Override de Split */}
      <ModalAuditAdminSplit
        split={adminSplit}
        orderId={orderId}
        onClose={() => setAdminSplit(null)}
        onSaved={(msg) => {
          setFeedbackMsg({ type: 'success', text: msg });
          loadAudit(page);
          onAuditUpdated?.();
        }}
      />

      {/* Modal Exclusivo de Administrador: Rectificación Pericial de Conteos */}
      <ModalAuditAdminCounts
        item={adminEditingItem}
        onClose={() => setAdminEditingItem(null)}
        onSaved={(msg) => {
          setFeedbackMsg({ type: 'success', text: msg });
          loadAudit(page);
          onAuditUpdated?.();
        }}
      />
      {/* Modal Reasignación de Split para Admin y Marketing */}
      {reassignSplitData && (
        <ModalReassignSplit
          isOpen={Boolean(reassignSplitData)}
          onClose={() => setReassignSplitData(null)}
          split={reassignSplitData}
          onSuccess={() => {
            setReassignSplitData(null);
            loadAudit(page);
          }}
        />
      )}

      {/* Modal Bitácora Atómica de Escaneos (Event Ledger) */}
      {selectedEventsSplit && (
        <ModalWarehouseEventsLedger
          isOpen={Boolean(selectedEventsSplit)}
          onClose={() => setSelectedEventsSplit(null)}
          splitId={selectedEventsSplit.split_id}
          splitCode={selectedEventsSplit.split_code}
          orderId={orderId}
          split={selectedEventsSplit}
          orderAuditData={auditData}
        />
      )}
    </div>
  );
}
