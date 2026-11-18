import React, { useState, useEffect } from 'react';
import warehouseService from '../../services/warehouseService';
import LoadingSpinner from '../common/LoadingSpinner';
import PaginationButtons from '../common/PaginationButtons';
import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { useAuth } from '../../context/AuthContext';
import ModalWarehouseAudit from './ModalWarehouseAudit';
import ModalOrderSplitsDetail from './ModalOrderSplitsDetail';
import WarehouseLaserStation from './WarehouseLaserStation';
import WarehouseStatusBadge from './WarehouseStatusBadge';
import WarehouseStatsGrid from './WarehouseStatsGrid';
import WarehouseFilterControls from './WarehouseFilterControls';
import WarehouseSplitsPillList from './WarehouseSplitsPillList';
import WarehouseContainersManagement from './WarehouseContainersManagement';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function WarehouseOperatorSection() {
  const { user } = useAuth();
  const { can, isAdmin } = usePermissions();
  const canPicker = isAdmin || can(PERMISSIONS.WAREHOUSE_OPERATOR) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canChecker = isAdmin || can(PERMISSIONS.WAREHOUSE_CHECKER) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canContainers = isAdmin || can(PERMISSIONS.WAREHOUSE_CONTAINERS) || can(PERMISSIONS.WAREHOUSE_MANAGE);

  const initialSubTab = canPicker ? 'queue_picker' : (canChecker ? 'queue_checker' : (canContainers ? 'containers' : 'history'));
  const [subTab, setSubTab] = useState(initialSubTab);
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSplitId, setActiveSplitId] = useState(null);
  const [selectedAuditOrderId, setSelectedAuditOrderId] = useState(null);
  const [selectedSplitsOrder, setSelectedSplitsOrder] = useState(null);
  const [claimConfirmation, setClaimConfirmation] = useState(null);
  const [claimContainerMode, setClaimContainerMode] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);
  const { limit: globalLimit } = usePaginationLimit();
  const limit = globalLimit || 15;

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await warehouseService.getStats();
      setStats(data);
    } catch (err) {
      console.error('Error loading warehouse operator stats:', err);
    }
  };

  const handleClaimSplit = async (splitId, roleType = 'picker', usesContainers = false) => {
    if (roleType === 'checker' && !canChecker) {
      setActionMessage({
        type: 'error',
        text: 'No cuentas con el permiso de Revisor (warehouse.checker) para tomar el 2do filtro.'
      });
      return;
    }
    if (roleType === 'picker' && !canPicker) {
      setActionMessage({
        type: 'error',
        text: 'No cuentas con el permiso de Surtidor (warehouse.operator) para tomar el 1er filtro.'
      });
      return;
    }
    try {
      setLoading(true);
      await warehouseService.claimSplit(splitId, roleType, usesContainers);
      setActionMessage({
        type: 'success',
        text: `✓ Te has autoasignado exitosamente como ${roleType === 'checker' ? 'Revisor (Checker)' : 'Surtidor (Picker)'}. Abriendo terminal de trabajo...`
      });
      setClaimConfirmation(null);
      await loadStats();
      await loadWarehouseOrders();
      // Abrir terminal de inmediato
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

  useEffect(() => {
    setPage(0);
  }, [subTab, globalLimit, statusFilter, assignedToMe]);

  useEffect(() => {
    loadWarehouseOrders(page);
  }, [subTab, page, statusFilter, assignedToMe, globalLimit]);

  const loadWarehouseOrders = async (pageToLoad = page) => {
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
        search: search.trim() || undefined
      };

      const res = !isHistory
        ? await warehouseService.getQueue(params)
        : await warehouseService.getOrdersHistory(params);

      setOrders(res.orders || []);
      setLookaheadPages(res.lookahead_pages ?? (res.orders?.length === limit ? 1 : 0));
    } catch (err) {
      console.error('Error loading warehouse operator orders:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(0);
    loadWarehouseOrders(0);
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
              setActiveSplitId(null);
              loadStats();
              loadWarehouseOrders();
            }}
            onBackToQueue={() => setActiveSplitId(null)}
          />
        </div>
      ) : (
        <>
          <div className="warehouse-manager__header">
            <div>
              <h2><span>🏭</span> Módulo de Bodega & Logística (Fulfillment)</h2>
              <p>
                Supervisión de surtido de tus pedidos asignados, avance de recolección y auditoría forense.
              </p>
            </div>
          </div>

          {/* Grid de KPIs adaptadas a los pedidos asignados */}
          <WarehouseStatsGrid stats={stats} />

      {/* Sub-navegación: Surtido (1er Filtro) vs Revisión (2do Filtro) vs Historial General */}
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
          {/* Controles de Búsqueda y Filtros */}
          <WarehouseFilterControls
        search={search}
        onSearchChange={setSearch}
        onSearchSubmit={handleSearchSubmit}
        searchPlaceholder={
          subTab === 'queue_picker'
            ? 'Buscar en cola de surtido por # pedido, cliente o picker...'
            : subTab === 'queue_checker'
            ? 'Buscar en cola de revisión por # pedido, cliente o revisor...'
            : 'Buscar en historial por # pedido, cliente o almacenista...'
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
        onQuickScanSplit={(splitCode) => setActiveSplitId(splitCode)}
        onRefresh={() => {
          loadStats();
          loadWarehouseOrders(page);
        }}
        loading={loading}
      />

      {/* Tabla de Pedidos usando data-table estándar */}
      <div className="data-table">
        {loading ? (
          <div className="p-6">
            <LoadingSpinner message="Consultando avance en bodega..." />
          </div>
        ) : orders.length === 0 ? (
          <div className="data-table__empty">
            No hay pedidos en bodega que coincidan con la búsqueda.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Cliente</th>
                <th>Enviado a Bodega</th>
                <th>Splits</th>
                <th>Estatus Bodega</th>
                <th className="text-end">Auditoría</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((ord) => (
                <tr key={ord.order_id}>
                  <td>
                    <strong>#{ord.order_id}</strong>
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
                  <td className="text-end">
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={() => setSelectedAuditOrderId(ord.order_id)}
                    >
                      🔍 Auditoría Forense
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Paginación estándar */}
      {orders.length > 0 && (
        <PaginationButtons
          currentPage={page}
          lookaheadPages={lookaheadPages}
          onPageChange={setPage}
        />
      )}
        </>
      )}

      {/* Modal Auditoría Forense */}
      <ModalWarehouseAudit
        isOpen={Boolean(selectedAuditOrderId)}
        onClose={() => setSelectedAuditOrderId(null)}
        orderId={selectedAuditOrderId}
      />

      {/* Modal Detalle Completo de Splits */}
      <ModalOrderSplitsDetail
        isOpen={Boolean(selectedSplitsOrder)}
        onClose={() => setSelectedSplitsOrder(null)}
        order={selectedSplitsOrder}
        userRole={user?.role_slug || user?.role}
        stageFilter={subTab === 'queue_checker' ? 'checker' : (subTab === 'queue_picker' ? 'picker' : null)}
        currentUserId={user?.user_id}
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
            // Ya asignado a este colaborador, abrir terminal directamente
            setSelectedSplitsOrder(null);
            setActiveSplitId(splitId);
          }
        }}
      />

      {/* Modal Confirmación de Autoasignación para Operador / Colaborador */}
      {claimConfirmation && (
        <div className="modal-overlay" onClick={() => setClaimConfirmation(null)}>
          <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal__header">
              <h3>Confirmar Autoasignación</h3>
              <button
                type="button"
                className="modal__close"
                onClick={() => setClaimConfirmation(null)}
              >
                &times;
              </button>
            </div>
            <div className="modal__body">
              <p className="mb-2">
                ¿Deseas autoasignarte la <strong>Split #{claimConfirmation.splitNumber}</strong> del Pedido <strong>#{claimConfirmation.orderId}</strong> para trabajarla en la terminal?
              </p>

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
                      ? 'Se solicitará escanear canastas físicas QR para clasificar y separar los productos.'
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
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn--primary font-bold"
                onClick={() => handleClaimSplit(claimConfirmation.splitId, claimConfirmation.roleType, claimContainerMode)}
              >
                Sí, Tomar Split
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
