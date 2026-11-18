import React, { useState, useEffect } from 'react';
import warehouseService from '../../services/warehouseService';
import LoadingSpinner from '../common/LoadingSpinner';
import PaginationButtons from '../common/PaginationButtons';
import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { useAuth } from '../../context/AuthContext';
import ModalWarehouseAudit from './ModalWarehouseAudit';
import ModalReassignSplit from './ModalReassignSplit';
import ModalOrderSplitsDetail from './ModalOrderSplitsDetail';
import WarehouseLaserStation from './WarehouseLaserStation';
import WarehouseStatusBadge from './WarehouseStatusBadge';
import WarehouseStatsGrid from './WarehouseStatsGrid';
import WarehouseFilterControls from './WarehouseFilterControls';
import WarehouseSplitsPillList from './WarehouseSplitsPillList';
import WarehouseContainersManagement from './WarehouseContainersManagement';
import ModalSendToWarehouse from './ModalSendToWarehouse';

import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function WarehouseAdminSection({ isSupervisor = false }) {
  const { user } = useAuth();
  const { can, isAdmin } = usePermissions();
  const canAudit = isAdmin || can(PERMISSIONS.WAREHOUSE_AUDIT) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canSupervisor = isSupervisor || isAdmin || can(PERMISSIONS.WAREHOUSE_SUPERVISOR) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canSendWarehouse = isAdmin || can(PERMISSIONS.WAREHOUSE_SEND) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canContainers = isAdmin || can(PERMISSIONS.WAREHOUSE_CONTAINERS) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canPicker = isAdmin || canSupervisor || can(PERMISSIONS.WAREHOUSE_OPERATOR);
  const canChecker = isAdmin || canSupervisor || can(PERMISSIONS.WAREHOUSE_CHECKER);
  const [subTab, setSubTab] = useState('queue_picker'); // 'queue_picker' | 'queue_checker' | 'history' | 'containers'
  const { limit: globalLimit } = usePaginationLimit();
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [totalOrders, setTotalOrders] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showSendModal, setShowSendModal] = useState(false);
  const [search, setSearch] = useState('');
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [auditVerdictFilter, setAuditVerdictFilter] = useState('');
  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);
  const limit = globalLimit || 15;

  // Modales y Estación Láser
  const [activeSplitId, setActiveSplitId] = useState(null);
  const [selectedAuditOrderId, setSelectedAuditOrderId] = useState(null);
  const [reassignSplitData, setReassignSplitData] = useState(null);
  const [selectedSplitsOrder, setSelectedSplitsOrder] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);
  const [claimConfirmation, setClaimConfirmation] = useState(null);
  const [claimContainerMode, setClaimContainerMode] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  // Reset de página al cambiar la cantidad de items por página
  useEffect(() => {
    setPage(0);
  }, [globalLimit]);

  useEffect(() => {
    if (subTab !== 'containers') {
      loadOrders();
    }
  }, [subTab, page, assignedToMe, statusFilter, auditVerdictFilter, globalLimit]);

  const loadStats = async () => {
    try {
      const data = await warehouseService.getStats();
      setStats(data);
    } catch (err) {
      console.error('Error loading warehouse stats:', err);
    }
  };

  const loadOrders = async (pageToLoad = page) => {
    if (subTab === 'containers') return;
    try {
      setLoading(true);
      const isHistory = subTab === 'history';
      const stage = subTab === 'queue_checker' ? 'checker' : (subTab === 'queue_picker' ? 'picker' : undefined);

      const params = {
        skip: pageToLoad * limit,
        limit,
        warehouse_status: isHistory ? (statusFilter || undefined) : undefined,
        stage: !isHistory ? stage : undefined,
        assigned_to_me: assignedToMe ? true : undefined,
        search: search.trim() || undefined,
        audit_verdict: (canAudit && isHistory && auditVerdictFilter) ? auditVerdictFilter : undefined
      };

      const res = !isHistory
        ? await warehouseService.getQueue(params)
        : await warehouseService.getOrdersHistory(params);

      setOrders(res.orders || []);
      setTotalOrders(res.total || 0);
      setLookaheadPages(res.lookahead_pages ?? (res.orders?.length === limit ? 1 : 0));
    } catch (err) {
      console.error('Error loading warehouse orders:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(0);
    loadOrders(0);
  };

  const handleToggleVisibility = async (orderId, newShowDetails) => {
    try {
      setLoading(true);
      setOrders(prev => prev.map(o => o.order_id === orderId ? { ...o, warehouse_show_details: newShowDetails } : o));
      
      await warehouseService.toggleVisibility(orderId, newShowDetails);
      setActionMessage({
        type: 'success',
        text: `Modo de surtido para pedido #${orderId} actualizado a: ${newShowDetails ? '👁️ Detalles Visibles' : '🔒 Surtido Ciego (Protegido)'}`
      });
      await loadOrders();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.detail || err.message || 'Error al cambiar visibilidad' });
      await loadOrders();
    } finally {
      setLoading(false);
      setTimeout(() => setActionMessage(null), 4000);
    }
  };

  const handleCancelWarehouse = async (order) => {
    const orderId = typeof order === 'object' ? order.order_id : order;
    const orderObj = typeof order === 'object' ? order : orders.find(o => o.order_id === orderId);
    const hasAdvance = orderObj?.splits?.some(b => b.status !== 'pending') || orderObj?.warehouse_status === 'in_progress_partial' || orderObj?.warehouse_status === 'in_progress_full';

    let confirmText = `¿Estás seguro de cancelar la asignación a bodega del Pedido #${orderId}?`;
    if (isAdmin && hasAdvance) {
      confirmText = `⚠️ ATENCIÓN ADMINISTRADOR: El Pedido #${orderId} ya tiene splits iniciadas o en surtido.\n\nAl cancelar se ELIMINARÁN los splits y el progreso físico de escaneo.\n\n¿Deseas proceder con la cancelación forzosa?`;
    } else if (!isAdmin && hasAdvance) {
      alert(`No se puede cancelar el Pedido #${orderId} porque ya tiene splits con avance físico o en proceso de surtido.\n\nContacte al Administrador.`);
      return;
    } else {
      confirmText = `¿Estás seguro de cancelar la asignación a bodega del Pedido #${orderId}?\n\nNota: Solo se pueden cancelar pedidos pendientes sin avance físico ni productos escaneados.`;
    }

    if (!window.confirm(confirmText)) {
      return;
    }

    try {
      setLoading(true);
      await warehouseService.cancelWarehouse(orderId);
      setActionMessage({
        type: 'success',
        text: `✓ Pedido #${orderId} retirado de bodega exitosamente.`
      });
      await loadStats();
      await loadOrders();
    } catch (err) {
      const errorMsg = err.detail || err.message || 'No se pudo cancelar la asignación a bodega.';
      setActionMessage({
        type: 'error',
        text: `⚠️ ${errorMsg}`
      });
    } finally {
      setLoading(false);
      setTimeout(() => setActionMessage(null), 6000);
    }
  };

  const handleClaimSplit = async (splitId, roleType = 'picker', usesContainers = false) => {
    try {
      setLoading(true);
      await warehouseService.claimSplit(splitId, roleType, usesContainers);
      setActionMessage({
        type: 'success',
        text: `✓ Te has autoasignado exitosamente como ${roleType === 'checker' ? 'Revisor (Checker)' : 'Surtidor (Picker)'}. Abriendo terminal de trabajo...`
      });
      setClaimConfirmation(null);
      await loadStats();
      await loadOrders();
      // Abrir inmediatamente la terminal de escaneo / cajas manuales para este operador
      setActiveSplitId(splitId);
    } catch (err) {
      setActionMessage({
        type: 'error',
        text: err.detail || err.message || 'Error al autoasignarse a el split'
      });
    } finally {
      setLoading(false);
      setTimeout(() => setActionMessage(null), 4000);
    }
  };

  return (
    <div className="warehouse-manager">
      {actionMessage && (
        <div className={`alert ${actionMessage.type === 'success' ? 'alert--success' : 'alert--danger'}`}>
          {actionMessage.text}
        </div>
      )}

      {activeSplitId ? (
        <div className="warehouse-operator-terminal-wrap">
          <WarehouseLaserStation
            activeSplitId={activeSplitId}
            onSplitFinished={() => {
              loadStats();
              loadOrders();
              setActiveSplitId(null);
            }}
            onBackToQueue={() => {
              setActiveSplitId(null);
              loadOrders();
            }}
          />
        </div>
      ) : (
        <>
          {/* Encabezado */}
          <div className="warehouse-manager__header">
            <div>
              <h2>
                <span>🏭</span> Módulo de Bodega & Logística (Fulfillment)
              </h2>
              <p>
                {isSupervisor
                  ? 'Supervisión de surtido de pedidos, asignación de turnos y auditoría forense de splits.'
                  : 'Control operativo de bodega: cola FIFO, splits de surtido, empaque y sellos inviolables.'}
              </p>
            </div>
            {canSendWarehouse && (
              <div className="d-flex align-items-center gap-2">
                <button
                  type="button"
                  className="btn btn--primary font-bold"
                  onClick={() => setShowSendModal(true)}
                  title="Enviar un pedido aprobado al surtido de bodega"
                >
                  <span>➕</span> Enviar Pedido a Bodega
                </button>
              </div>
            )}
          </div>

          {/* Grid de KPIs usando componente reutilizable */}
          <WarehouseStatsGrid stats={stats} />

      {/* Sub-navegación: Surtido (1er Filtro) vs Revisión (2do Filtro) vs Historial General vs Canastas QR */}
      <div className="warehouse-manager__subtabs">
        {canPicker && (
          <button
            type="button"
            className={`warehouse-manager__subtab-btn ${subTab === 'queue_picker' ? 'warehouse-manager__subtab-btn--active' : ''}`}
            onClick={() => {
              setSubTab('queue_picker');
              setPage(0);
            }}
          >
            📦 Cola: Surtido (1er Filtro)
          </button>
        )}
        {canChecker && (
          <button
            type="button"
            className={`warehouse-manager__subtab-btn ${subTab === 'queue_checker' ? 'warehouse-manager__subtab-btn--active' : ''}`}
            onClick={() => {
              setSubTab('queue_checker');
              setPage(0);
            }}
          >
            🔍 Cola: Revisión (2do Filtro)
          </button>
        )}
        <button
          type="button"
          className={`warehouse-manager__subtab-btn ${subTab === 'history' ? 'warehouse-manager__subtab-btn--active' : ''}`}
          onClick={() => {
            setSubTab('history');
            setPage(0);
          }}
        >
          📜 Historial General de Bodega
        </button>
        {canContainers && (
          <button
            type="button"
            className={`warehouse-manager__subtab-btn ${subTab === 'containers' ? 'warehouse-manager__subtab-btn--active' : ''}`}
            onClick={() => {
              setSubTab('containers');
              setPage(0);
            }}
          >
            🧺 Canastas Físicas QR
          </button>
        )}
      </div>

      {subTab === 'containers' ? (
        <WarehouseContainersManagement />
      ) : (
        <>
          {/* Barra de Filtros y Búsqueda */}
          <WarehouseFilterControls
            search={search}
            onSearchChange={setSearch}
            onSearchSubmit={handleSearchSubmit}
        searchPlaceholder={
          subTab === 'queue_picker'
            ? 'Buscar en cola de surtido por # pedido, cliente, vendedor o picker...'
            : subTab === 'queue_checker'
            ? 'Buscar en cola de revisión por # pedido, cliente, vendedor o revisor...'
            : 'Buscar en historial por # pedido, cliente, vendedor o almacenista...'
        }
        assignedToMe={assignedToMe}
        onAssignedToMeChange={(val) => {
          setAssignedToMe(val);
          setPage(0);
        }}
        statusFilter={subTab === 'history' ? statusFilter : ''}
        onStatusFilterChange={subTab === 'history' ? ((val) => {
          setStatusFilter(val);
          setPage(0);
        }) : null}
        showStatusFilter={subTab === 'history'}
        auditVerdictFilter={subTab === 'history' ? auditVerdictFilter : ''}
        onAuditVerdictFilterChange={subTab === 'history' ? ((val) => {
          setAuditVerdictFilter(val);
          setPage(0);
        }) : null}
        showAuditVerdictFilter={subTab === 'history' && canAudit}
        onQuickScanSplit={(splitCode) => setActiveSplitId(splitCode)}
        onRefresh={() => {
          loadStats();
          loadOrders();
        }}
        loading={loading}
      />

      {/* Tabla de Pedidos usando data-table estándar */}
      <div className="data-table">
        {loading ? (
          <div className="p-8">
            <LoadingSpinner message="Consultando pedidos en almacén..." />
          </div>
        ) : orders.length === 0 ? (
          <div className="data-table__empty">
            No se encontraron pedidos de almacén con los filtros seleccionados.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Cliente</th>
                <th>Fecha Ingreso</th>
                <th>Splits</th>
                <th>Estatus Bodega</th>
                {canAudit && <th>⚖️ Veredicto Forense</th>}
                <th className="text-center">Modo Cola</th>
                <th className="text-end">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((ord) => {
                const renderVerdictBadge = (verdict) => {
                  switch (verdict) {
                    case 'clean':
                      return <span className="badge badge--success text-xs font-bold" title="Partidas completas y verificadas sin discrepancias">✓ Íntegro</span>;
                    case 'clean_confidence':
                      return <span className="badge badge--info text-xs font-bold" title="Partidas completas validadas por confianza en segundo filtro">🤝 Íntegro (Confianza)</span>;
                    case 'incomplete':
                      return <span className="badge badge--warning text-xs font-bold" title="Pedido con piezas faltantes respecto al pedido requerido">⚠️ Faltantes</span>;
                    case 'inconsistent':
                      return <span className="badge badge--danger text-xs font-bold" title="Discrepancia de conteo entre el 1er filtro (surtidor) y 2do filtro (revisor)">⚡ Discrepancia</span>;
                    case 'incomplete_and_inconsistent':
                      return <span className="badge badge--danger text-xs font-bold" title="Faltan piezas y existen diferencias entre surtidor y revisor">🚨 Incompleto + Discrepancia</span>;
                    default:
                      return <span className="badge badge--secondary text-xs">{verdict || 'clean'}</span>;
                  }
                };

                return (
                  <tr key={ord.order_id}>
                    <td>
                      <strong>#{ord.order_id}</strong>
                      <div className="text-xs text-muted">
                        Vendedor: {ord.seller_name || 'N/A'}
                      </div>
                    </td>
                    <td>
                      <div className="font-semibold">{ord.customer_name}</div>
                      <div className="text-xs text-muted">
                        Total: ${Number(ord.total_amount || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                      </div>
                    </td>
                    <td className="text-sm">
                      {ord.sent_to_warehouse_at || ord.warehouse_sent_at
                        ? new Date(ord.sent_to_warehouse_at || ord.warehouse_sent_at).toLocaleDateString('es-MX', {
                            day: '2-digit',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit'
                          })
                        : 'N/A'}
                    </td>
                    <td>
                      <WarehouseSplitsPillList
                        splits={ord.splits}
                        onOrderClick={() => setSelectedSplitsOrder(ord)}
                      />
                    </td>
                    <td>
                      <WarehouseStatusBadge status={ord.warehouse_status} />
                    </td>
                    {canAudit && (
                      <td>
                        {renderVerdictBadge(ord.audit_verdict)}
                      </td>
                    )}
                    <td className="text-center">
                      <button
                        type="button"
                        className={`warehouse-blind-btn ${ord.warehouse_show_details ? 'warehouse-blind-btn--open' : 'warehouse-blind-btn--blind'}`}
                        title="Alternar entre Surtido Ciego (oculta cliente/items) o Detallado para almacenistas"
                        onClick={() => handleToggleVisibility(ord.order_id, !ord.warehouse_show_details)}
                      >
                        {ord.warehouse_show_details ? '👁️ Detallado' : '🔒 Ciego'}
                      </button>
                    </td>
                    <td className="text-end">
                      <div className="d-flex justify-content-end gap-2">
                        <button
                          type="button"
                          className="btn btn--secondary btn--sm"
                          title="Ver auditoría pericial completa del pedido"
                          onClick={() => setSelectedAuditOrderId(ord.order_id)}
                        >
                          🔍 Auditoría
                        </button>

                        {/* Cancelar bodega: solo si no ha sido completado */}
                        {ord.warehouse_status !== 'completed' && (
                          <button
                            type="button"
                            className="btn btn--danger btn--sm"
                            title="Cancelar y retirar de bodega"
                            onClick={() => handleCancelWarehouse(ord)}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginación */}
      <PaginationButtons
        currentPage={page}
        lookaheadPages={lookaheadPages}
        onPageChange={setPage}
      />
        </>
      )}

      {/* Modal Auditoría Forense */}
      <ModalWarehouseAudit
        isOpen={Boolean(selectedAuditOrderId)}
        onClose={() => setSelectedAuditOrderId(null)}
        orderId={selectedAuditOrderId}
        onAuditUpdated={() => {
          loadStats();
          loadOrders();
        }}
      />

      {/* Modal Enviar Pedido a Bodega (Supervisor / Admin) */}
      <ModalSendToWarehouse
        isOpen={showSendModal}
        onClose={() => setShowSendModal(false)}
        onSuccess={() => {
          loadStats();
          loadOrders();
        }}
      />

      {/* Modal Reasignación de Splits (Supervisor / Admin) */}
      <ModalReassignSplit
        isOpen={Boolean(reassignSplitData && canSupervisor)}
        onClose={() => setReassignSplitData(null)}
        split={reassignSplitData}
        onSuccess={() => {
          loadStats();
          loadOrders();
        }}
      />

      {/* Modal Detalle Completo de Splits */}
      <ModalOrderSplitsDetail
        isOpen={Boolean(selectedSplitsOrder)}
        onClose={() => setSelectedSplitsOrder(null)}
        order={selectedSplitsOrder}
        userRole={user?.role}
        stageFilter={subTab === 'queue_checker' ? 'checker' : (subTab === 'queue_picker' ? 'picker' : null)}
        currentUserId={user?.user_id}
        onReassignSplit={(split) => {
          if (canSupervisor) {
            setSelectedSplitsOrder(null);
            setReassignSplitData(split);
          }
        }}
        onTakeSplit={(splitId, roleType, splitNumber, orderId, isDirectResume = false) => {
          if (!isDirectResume && splitNumber && orderId) {
            setClaimContainerMode(false);
            setClaimConfirmation({
              splitId,
              roleType,
              splitNumber,
              orderId
            });
          } else {
            // Ya asignado a este usuario, abrir terminal directamente
            setSelectedSplitsOrder(null);
            setActiveSplitId(splitId);
          }
        }}
      />

      {/* Modal Confirmación de Autoasignación para Marketing / Vendedor / Admin */}
      {claimConfirmation && (
        <div className="modal-overlay" onClick={() => setClaimConfirmation(null)}>
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="d-flex align-items-center gap-2">
                <span>{claimConfirmation.roleType === 'checker' ? '🔍' : '⚡'}</span>
                {claimConfirmation.roleType === 'checker' ? 'Asignarse Segundo Filtro' : 'Tomar Split para Surtir'}
              </h3>
              <button
                type="button"
                className="modal__close"
                onClick={() => setClaimConfirmation(null)}
                aria-label="Cerrar"
              >
                &times;
              </button>
            </div>
            <div className="modal__body">
              <p className="mb-2">
                ¿Deseas auto-asignarte la <strong>Split #{claimConfirmation.splitNumber}</strong> del <strong>Pedido #{claimConfirmation.orderId}</strong>?
              </p>
              <div className="alert alert--info text-xs mb-3">
                {claimConfirmation.roleType === 'checker' ? (
                  <span>
                    🛡️ Quedarás asignado como <strong>Revisor (Checker)</strong> oficial para la revisión de este split.
                  </span>
                ) : (
                  <span>
                    🧺 Quedarás asignado como <strong>Surtidor (Picker)</strong> para la recolección física de este split.
                  </span>
                )}
              </div>

              {/* Selector de Modalidad con / sin Canastas (Solo para Picker) */}
              {claimConfirmation.roleType === 'picker' && (
                <div className="form-group mb-2">
                  <label className="form-label font-bold text-xs d-block mb-1">
                    Modalidad de Recolección en Piso:
                  </label>
                  <div className="btn-group w-100" role="group">
                    <button
                      type="button"
                      className={`btn btn--sm flex-1 ${!claimContainerMode ? 'btn--primary font-bold' : 'btn--secondary'}`}
                      onClick={() => setClaimContainerMode(false)}
                    >
                      📦 Surtido Directo
                    </button>
                    <button
                      type="button"
                      className={`btn btn--sm flex-1 ${claimContainerMode ? 'btn--primary font-bold' : 'btn--secondary'}`}
                      onClick={() => setClaimContainerMode(true)}
                    >
                      🧺 Con Canastas QR
                    </button>
                  </div>
                  <small className="form-text text-muted text-xs mt-1 d-block">
                    {claimContainerMode
                      ? 'Se vincularán canastas QR físicas reutilizables para separar los productos.'
                      : 'Recolección general de productos directo al lote de surtido sin división en canastas.'}
                  </small>
                </div>
              )}
            </div>
            <div className="modal__footer">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => setClaimConfirmation(null)}
                disabled={loading}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn--primary font-bold"
                onClick={() => handleClaimSplit(claimConfirmation.splitId, claimConfirmation.roleType, claimContainerMode)}
                disabled={loading}
              >
                {loading ? 'Asignando...' : 'Confirmar Asignación'}
              </button>
            </div>
          </div>
        </div>
      )}
        </>
      )}

    </div>
  );
}
