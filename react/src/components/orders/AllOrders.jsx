import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faSpinner, faSync, faFileAlt, faEdit, faPlus } from '@fortawesome/free-solid-svg-icons';
import orderService from '../../services/orderService';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import ModalOrderDetails from '../modals/orders/ModalOrderDetails';
import ModalAssignUser from '../modals/clients/ModalAssignUser';
import ModalEditOrder from '../modals/orders/ModalEditOrder';
import ModalCreateOrder from '../modals/orders/ModalCreateOrder';
import ModalDownloadTxtOptions from '../modals/orders/ModalDownloadTxtOptions';
import ModalSendToWarehouse from '../warehouse/ModalSendToWarehouse';
import ModalWarehouseAudit from '../warehouse/ModalWarehouseAudit';
import PaginationButtons from '../common/PaginationButtons';
import { useAuth } from '../../context/AuthContext';
import usePermissions from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';
import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { formatCurrency } from '../../utils/formatUtils';

export default function AllOrders() {
  const { user } = useAuth();
  const { can, isAdmin, isStaff } = usePermissions();
  const canAssign = isAdmin || can(PERMISSIONS.ORDERS_ASSIGN);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [page, setPage] = useState(0);
  const [lookaheadPages, setLookaheadPages] = useState(0);
  const { limit: itemsPerPage } = usePaginationLimit();

  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [syncFilter, setSyncFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const [showAssignModal, setShowAssignModal] = useState(false);
  const [orderToAssign, setOrderToAssign] = useState(null);
  const [assignGroupId, setAssignGroupId] = useState(null);

  const [showEditModal, setShowEditModal] = useState(false);
  const [orderToEdit, setOrderToEdit] = useState(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTxtModal, setShowTxtModal] = useState(false);
  const [orderForTxt, setOrderForTxt] = useState(null);

  const [showSendWarehouseModal, setShowSendWarehouseModal] = useState(false);
  const [orderToSendWarehouse, setOrderToSendWarehouse] = useState(null);
  const [showWarehouseAuditModal, setShowWarehouseAuditModal] = useState(false);
  const [auditOrderId, setAuditOrderId] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => { setDebouncedSearchTerm(searchTerm); setPage(0); }, 2500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => { loadOrders(); }, [page, statusFilter, syncFilter, debouncedSearchTerm, startDate, endDate, itemsPerPage]);

  // Auto-refresh interval (every 30s)
  useEffect(() => {
    const interval = setInterval(() => {
      // Only refresh if no modals are open (even if tab is in the background)
      if (
        !showModal &&
        !showAssignModal &&
        !showEditModal &&
        !showCreateModal &&
        !showTxtModal &&
        !showSendWarehouseModal &&
        !showWarehouseAuditModal
      ) {
        loadOrders(true); // silent refresh
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [page, statusFilter, syncFilter, debouncedSearchTerm, startDate, endDate, itemsPerPage, showModal, showAssignModal, showEditModal, showCreateModal, showTxtModal, showSendWarehouseModal, showWarehouseAuditModal]);

  const loadOrders = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      const params = { skip: page * itemsPerPage, limit: itemsPerPage };
      if (statusFilter) params.status = statusFilter;
      if (syncFilter === 'synced') params.is_synced = true;
      if (syncFilter === 'pending') params.is_synced = false;
      if (debouncedSearchTerm) params.search = debouncedSearchTerm;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      const data = await orderService.getAllOrders(params);
      if (data && Array.isArray(data.items)) {
        setOrders(data.items);
        setLookaheadPages(data.lookahead_pages);
      } else {
        const isArray = Array.isArray(data);
        const list = isArray ? data : (data?.items || []);
        setOrders(list);
        setLookaheadPages(0);
      }
    } catch (err) {
      setError('No se pudieron cargar los pedidos. Intenta de nuevo.');
      console.error('Failed to load orders:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const handleSearch = (e) => { e.preventDefault(); setDebouncedSearchTerm(searchTerm); setPage(0); };

  const handleStatusChange = async (orderId, newStatus) => {
    try { setActionLoading(orderId); await orderService.updateOrderStatus(orderId, newStatus); await loadOrders(); }
    catch (err) { 
      const msg = err.response?.data?.detail || err.message || 'Error al actualizar el estado del pedido.';
      setError(msg); 
      console.error(err); 
    }
    finally { setActionLoading(null); }
  };

  const handleApprove = async (orderId) => { if (window.confirm('¿Aprobar este pedido?')) await handleStatusChange(orderId, 'approved'); };
  const handleShip = async (orderId) => { if (window.confirm('¿Marcar como enviado?')) await handleStatusChange(orderId, 'shipped'); };
  const handleDeliver = async (orderId) => { if (window.confirm('¿Marcar como entregado?')) await handleStatusChange(orderId, 'delivered'); };
  const handleCancel = async (orderId) => {
    if (!window.confirm('¿Cancelar este pedido?')) return;
    try { setActionLoading(orderId); await orderService.cancelOrder(orderId); await loadOrders(); }
    catch (err) { setError('Error al cancelar el pedido.'); console.error(err); }
    finally { setActionLoading(null); }
  };

  const handleViewDetails = async (orderId) => {
    try {
      setActionLoading(orderId);
      const orderDetails = await orderService.getOrderById(orderId);
      orderDetails.shippingAddress = orderDetails.shipping_address || 'No especificada';
      setSelectedOrder(orderDetails);
      setShowModal(true);
    } catch (err) { setError('Error al cargar detalles.'); console.error(err); }
    finally { setActionLoading(null); }
  };

  const handleAssignClick = (order) => {
    const groupId = order.sales_group_id;
    const canViewAll = can(PERMISSIONS.ORDERS_VIEW_ALL);
    const canViewUsers = can(PERMISSIONS.USERS_VIEW);
    const canAssignFreely = canAssign && ((canViewAll && canViewUsers) || isAdmin);

    if (!groupId && !canAssignFreely) {
      setError('El cliente de este pedido no está asignado a ningún grupo de ventas. Asígnalo a un grupo primero o requiere permisos transversales (orders.view_all y users.view) para asignación libre.');
      return;
    }
    setAssignGroupId(groupId || null);
    setOrderToAssign(order);
    setShowAssignModal(true);
  };

  const handleAssign = async (userId, notes) => {
    try { await orderService.assignOrder(orderToAssign.order_id, userId, notes); await loadOrders(); setShowAssignModal(false); setOrderToAssign(null); }
    catch (err) { setError(err.response?.data?.detail || err.message || 'Error al asignar asesor'); }
  };

  const handleOpenTxtModal = async (order) => {
    try {
      const orderId = order.order_id || order;
      setActionLoading(orderId);
      const details = (order && order.items && order.items.length > 0)
        ? order 
        : await orderService.getOrderById(orderId);
      setOrderForTxt(details);
      setShowTxtModal(true);
    } catch (err) {
      setError('Error al obtener información del pedido.');
      console.error(err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenSendWarehouse = (order) => {
    if (order.status !== 'approved') {
      setError('Solo se pueden enviar a bodega pedidos previamente aprobados.');
      return;
    }
    setOrderToSendWarehouse(order);
    setShowSendWarehouseModal(true);
  };

  const handleOpenWarehouseAudit = (orderId) => {
    setAuditOrderId(orderId);
    setShowWarehouseAuditModal(true);
  };

  const handleSendWarehouseSuccess = () => {
    loadOrders();
  };

  const handleConfirmDownloadTXT = async (orderId, itemsPerFile) => {
    try {
      setActionLoading(orderId);
      await orderService.downloadOrderTXT(orderId, itemsPerFile);
    } catch (err) {
      setError('Error al descargar el archivo TXT.');
      console.error(err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEditOrder = async (order) => {
    try { setActionLoading(order.order_id); const details = await orderService.getOrderById(order.order_id); setOrderToEdit(details); setShowEditModal(true); }
    catch (err) { setError('Error al cargar pedido para editar'); console.error(err); }
    finally { setActionLoading(null); }
  };

  const handleSaveEditedOrder = async (orderId, editData) => {
    try { await orderService.editOrder(orderId, editData); await loadOrders(); }
    catch (err) { setError(err.response?.data?.detail || err.message || 'Error al guardar cambios'); }
  };

  const handleCreateOrderSuccess = async () => { await loadOrders(); };

  if (loading && orders.length === 0) {
    return (
      <section className="dashboard-section">
        <h2 className="section-title">Gestión de Pedidos</h2>
        <LoadingSpinner message="Cargando pedidos..." />
      </section>
    );
  }

  return (
    <section className="dashboard-section">
      <h2 className="section-title">Gestión de Pedidos</h2>

      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      <div className="dashboard-controls">
        {(isAdmin || can('orders.create')) && (
          <button className="btn btn--primary btn--sm" onClick={() => setShowCreateModal(true)} title="Crear Pedido para Cliente">
            <FontAwesomeIcon icon={faPlus} /> Crear Pedido
          </button>
        )}

        <form className="search-bar" onSubmit={handleSearch}>
          <input className="input" type="search" placeholder="Buscar por N° de Pedido, Cliente o Asesor..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          <button type="submit" className="btn btn--primary" aria-label="Buscar">
            <FontAwesomeIcon icon={faSearch} />
          </button>
        </form>

        <div className="d-flex align-items-center gap-1">
          <button className="btn btn--secondary btn--sm" onClick={() => loadOrders(false)} disabled={loading} title="Recargar Pedidos">
            <FontAwesomeIcon icon={faSync} spin={loading} /> {loading ? 'Cargando...' : 'Recargar'}
          </button>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }} title="Se actualiza automáticamente cada 30 segundos" aria-label="Auto-refresh activado">
            <span style={{ color: 'var(--success)', marginRight: '4px' }}>●</span>Auto
          </span>
        </div>

        <div className="filter-group d-flex align-items-center gap-1" style={{ flexWrap: 'wrap' }}>
          <div className="d-flex align-items-center gap-05">
            <label className="filter-group__label" htmlFor="start-date-filter" style={{ whiteSpace: 'nowrap', margin: 0 }}>Desde:</label>
            <input
              className="input input--sm"
              type="date"
              id="start-date-filter"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(0); }}
              style={{ width: 'auto', padding: '6px 8px', fontSize: '0.9rem' }}
            />
          </div>
          <div className="d-flex align-items-center gap-05">
            <label className="filter-group__label" htmlFor="end-date-filter" style={{ whiteSpace: 'nowrap', margin: 0 }}>Hasta:</label>
            <input
              className="input input--sm"
              type="date"
              id="end-date-filter"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(0); }}
              style={{ width: 'auto', padding: '6px 8px', fontSize: '0.9rem' }}
            />
          </div>
          {(startDate || endDate) && (
            <button
              className="btn btn--sm btn--ghost text-danger"
              onClick={() => { setStartDate(''); setEndDate(''); setPage(0); }}
              title="Limpiar filtros de fecha"
              style={{ padding: '4px 8px', fontSize: '0.85rem' }}
            >
              Limpiar
            </button>
          )}
        </div>

        <div className="filter-group">
          <label className="filter-group__label" htmlFor="status-filter">Estado:</label>
          <select className="select" id="status-filter" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}>
            <option value="">Todos los Estados</option>
            <optgroup label="Flujo Comercial">
              <option value="pending_validation">Pendiente de Validación</option>
              <option value="assigned">Asignado a Vendedor</option>
              <option value="approved">Aprobado</option>
              <option value="shipped">Enviado</option>
              <option value="delivered">Entregado</option>
              <option value="cancelled">Cancelado</option>
            </optgroup>
            <optgroup label="Fulfillment / Bodega">
              <option value="in_warehouse">🏭 En Bodega (Cualquier fase)</option>
              <option value="not_in_warehouse">🚫 Fuera de Bodega (No enviado)</option>
              <option value="warehouse_pending">⏳ Bodega: Pendiente FIFO</option>
              <option value="warehouse_in_progress">🔄 Bodega: En Surtido</option>
              <option value="warehouse_completed">🔒 Bodega: Surtido y Sellado</option>
            </optgroup>
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-group__label" htmlFor="sync-filter">ERP Sync:</label>
          <select className="select" id="sync-filter" value={syncFilter} onChange={(e) => { setSyncFilter(e.target.value); setPage(0); }}>
            <option value="">Todos</option>
            <option value="synced">⚡ Sincronizados</option>
            <option value="pending">⏳ Pendientes (No sinc.)</option>
          </select>
        </div>
      </div>

      {orders.length === 0 ? (
        <p className="empty-state">No hay pedidos que mostrar.</p>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                {(isAdmin || can(PERMISSIONS.ORDERS_ASSIGN) || can(PERMISSIONS.ORDERS_EDIT)) && <th>Admin</th>}
                <th>Id Cliente</th>
                <th>Cliente / Contacto</th>
                <th>Pedido / Fecha</th>
                <th>Montos</th>
                <th>Asesor / Usuario</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <OrderRowAllOrders
                  key={order.order_id}
                  order={order}
                  onApprove={handleApprove}
                  onShip={handleShip}
                  onDeliver={handleDeliver}
                  onCancel={handleCancel}
                  onAssign={handleAssignClick}
                  onViewDetails={handleViewDetails}
                  onDownloadTXT={handleOpenTxtModal}
                  onEdit={handleEditOrder}
                  onSendWarehouse={handleOpenSendWarehouse}
                  onViewWarehouse={handleOpenWarehouseAudit}
                  can={can}
                  isAdmin={isAdmin}
                  isLoading={actionLoading === order.order_id}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {orders.length > 0 && (
        <PaginationButtons
          currentPage={page}
          lookaheadPages={lookaheadPages}
          onPageChange={setPage}
        />
      )}

      <ModalOrderDetails visible={showModal} order={selectedOrder} isAdmin={isAdmin} isStaff={isStaff} onClose={() => { setShowModal(false); setSelectedOrder(null); }} onDownloadTXT={(ord) => handleOpenTxtModal(ord)} />
      <ModalAssignUser visible={showAssignModal} order={orderToAssign} groupId={assignGroupId} onAssign={handleAssign} onClose={() => { setShowAssignModal(false); setOrderToAssign(null); setAssignGroupId(null); }} />
      <ModalEditOrder visible={showEditModal} order={orderToEdit} onSave={handleSaveEditedOrder} onClose={() => { setShowEditModal(false); setOrderToEdit(null); }} />
      <ModalCreateOrder visible={showCreateModal} onClose={() => setShowCreateModal(false)} onSuccess={handleCreateOrderSuccess} />
      <ModalDownloadTxtOptions visible={showTxtModal} order={orderForTxt} onClose={() => { setShowTxtModal(false); setOrderForTxt(null); }} onConfirm={handleConfirmDownloadTXT} />
      <ModalSendToWarehouse
        isOpen={showSendWarehouseModal}
        orderId={orderToSendWarehouse?.order_id}
        onClose={() => { setShowSendWarehouseModal(false); setOrderToSendWarehouse(null); }}
        onSuccess={handleSendWarehouseSuccess}
      />
      <ModalWarehouseAudit
        isOpen={showWarehouseAuditModal}
        orderId={auditOrderId}
        onClose={() => { setShowWarehouseAuditModal(false); setAuditOrderId(null); }}
      />
    </section>
  );
}

function OrderRowAllOrders({
  order,
  onApprove,
  onShip,
  onDeliver,
  onCancel,
  onAssign,
  onViewDetails,
  onDownloadTXT,
  onEdit,
  onSendWarehouse,
  onViewWarehouse,
  can,
  isAdmin,
  isLoading
}) {
  const canStatusMaster = isAdmin || can(PERMISSIONS.ORDERS_STATUS);
  const canApprove = canStatusMaster || can(PERMISSIONS.ORDERS_APPROVE);
  const canCancel = canStatusMaster || can(PERMISSIONS.ORDERS_CANCEL);
  const canAssign = isAdmin || can(PERMISSIONS.ORDERS_ASSIGN);
  const canSendWarehouse = isAdmin || can(PERMISSIONS.WAREHOUSE_SEND) || can(PERMISSIONS.WAREHOUSE_SUPERVISOR) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canShip = canStatusMaster || can(PERMISSIONS.ORDERS_SHIP);
  const canDeliver = canStatusMaster || can(PERMISSIONS.ORDERS_DELIVER);
  const canExport = isAdmin || can(PERMISSIONS.ORDERS_EXPORT);
  const canAdminColumn = isAdmin || can(PERMISSIONS.ORDERS_ASSIGN) || can(PERMISSIONS.ORDERS_EDIT) || canExport;
  const canEdit = isAdmin || can(PERMISSIONS.ORDERS_EDIT);

  const renderDate = (dateString) => {
    if (!dateString) return null;
    const d = new Date(dateString);
    const formatter = new Intl.DateTimeFormat('es-MX', {
      timeZone: 'America/Mexico_City',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
    const parts = formatter.formatToParts(d);
    const getPart = (t) => parts.find(p => p.type === t)?.value || '';
    const day = getPart('day');
    const month = getPart('month');
    const year = getPart('year');
    const hour = getPart('hour');
    const minute = getPart('minute');
    const dayPeriod = getPart('dayPeriod') || '';
    const time = `${hour}:${minute} ${dayPeriod}`.trim();

    return (
      <div className="date-stack">
        <span className="date-stack__date">
          <strong className="date-stack__day">{day}</strong>/{month}/{year}
        </span>
        <span className="date-stack__time">{time}</span>
      </div>
    );
  };

  const getStatusLabel = (status) => {
    const labels = { 'pending_validation': 'Pendiente', 'assigned': 'Asignado', 'approved': 'Aprobado', 'shipped': 'Enviado', 'delivered': 'Entregado', 'cancelled': 'Cancelado' };
    return labels[status] || status;
  };
  const getStatusClass = (status) => {
    const classes = { 'pending_validation': 'pending', 'assigned': 'assigned', 'approved': 'approved', 'shipped': 'shipped', 'delivered': 'delivered', 'cancelled': 'cancelled' };
    return classes[status] || 'pending';
  };

  const getWarehouseStatusLabel = (ws) => {
    switch (ws) {
      case 'pending': return 'Bodega: Pendiente';
      case 'in_progress_partial': return 'Bodega: Surtido Parcial';
      case 'in_progress_full': return 'Bodega: Surtido Completo';
      case 'splits_completed':
      case 'completed': return 'Bodega: Completado';
      case 'cancelled': return 'Bodega: Cancelado';
      default: return ws ? `Bodega: ${ws}` : 'En Bodega';
    }
  };

  const clientId = order.customer_id || order.customer?.customer_id || 'N/A';
  const clientName = order.customer?.full_name || order.customer?.username || 'N/A';
  const clientContact = order.customer?.email || 'N/A';
  const itemCount = order.items_count !== undefined ? order.items_count : (order.items?.length || 0);
  const assignedUserName = order.assigned_user?.full_name || order.assigned_user?.username || 'Sin asignar';

  return (
    <tr>
      {canAdminColumn && (
        <td data-label="Admin" className="actions-cell">
          {isLoading ? (
            <FontAwesomeIcon icon={faSpinner} spin />
          ) : (
            <div className="d-flex gap-1">
              {canExport && (
                <button className="btn btn--icon btn--ghost" onClick={() => onDownloadTXT(order)} title="Descargar TXT">
                  <FontAwesomeIcon icon={faFileAlt} />
                </button>
              )}
              {canEdit && order.status !== 'cancelled' && order.status !== 'delivered' && (
                <button className="btn btn--icon btn--ghost" onClick={() => onEdit(order)} title="Editar Pedido">
                  <FontAwesomeIcon icon={faEdit} />
                </button>
              )}
            </div>
          )}
        </td>
      )}
      <td data-label="Id Cliente">{clientId}</td>
      <td data-label="Cliente">
        <div className="user-cell__info">
          <span className="user-cell__name">{clientName}</span>
          {order.customer?.username && (
            <span className="user-cell__username">
              @{order.customer.username}
            </span>
          )}
          <span className="user-cell__email">{clientContact.toLowerCase()}</span>
        </div>
      </td>
      <td data-label="Pedido">
        <div className="stacked-cell">
          <span className="stacked-cell__primary stacked-cell__primary--accent" style={{ marginBottom: '4px' }}>
            #{order.order_id}
            {order.order_notes && <span title={`Nota del cliente: ${order.order_notes}`} style={{ marginLeft: '5px', cursor: 'help' }}>📝</span>}
            {order.assignment_notes && canAssign && <span title={`Nota de asignación: ${order.assignment_notes}`} style={{ marginLeft: '3px', cursor: 'help' }}>📋</span>}
          </span>
          {renderDate(order.created_at)}
        </div>
      </td>
      <td data-label="Montos">
        <div className="stacked-cell">
          <span className="stacked-cell__primary stacked-cell__primary--success">{formatCurrency(order.total_amount)}</span>
          <span className="stacked-cell__secondary">{itemCount} {itemCount === 1 ? 'artículo' : 'artículos'}</span>
        </div>
      </td>
      <td data-label="Asesor / Usuario">
        <span style={{ fontSize: '0.9em', fontWeight: '500' }}>{assignedUserName}</span>
      </td>
      <td data-label="Estado">
        <div className="order-status-stack">
          <span className={`status-badge status-badge--${getStatusClass(order.status)}`}>
            {getStatusLabel(order.status)}
          </span>
          <div className="order-status-stack__sub">
            {order.is_synced ? (
              <span className="order-sub-badge order-sub-badge--synced" title="Sincronizado con ERP">
                ⚡ ERP Sincronizado
              </span>
            ) : (
              <span className="order-sub-badge order-sub-badge--pending" title="Pendiente de sincronizar con ERP">
                ⏳ ERP Pendiente
              </span>
            )}
            {order.sent_to_warehouse && (
              <span
                className={`order-sub-badge order-sub-badge--warehouse warehouse-badge--${order.warehouse_status || 'pending'}`}
                title="Estatus en Bodega. Clic para ver auditoría de partidas."
                onClick={() => onViewWarehouse(order.order_id)}
              >
                🏭 {getWarehouseStatusLabel(order.warehouse_status)}
              </span>
            )}
          </div>
        </div>
      </td>
      <td data-label="Acciones" className="actions-cell">
        {isLoading ? (
          <FontAwesomeIcon icon={faSpinner} spin />
        ) : (
          <div className="d-flex gap-1 flex-wrap">
            {order.status === 'pending_validation' && (
              <button
                className={`btn btn--sm ${!canApprove ? 'btn--secondary' : 'btn--success'}`}
                onClick={() => canApprove && onApprove(order.order_id)}
                title={!canApprove ? 'No cuentas con permiso para aprobar' : 'Aprobar'}
                disabled={!canApprove}
              >
                {!canApprove ? 'Validando...' : 'Aprobar'}
              </button>
            )}
            {order.status === 'assigned' && (
              <button
                className={`btn btn--sm ${!canApprove ? 'btn--secondary' : 'btn--success'}`}
                onClick={() => canApprove && onApprove(order.order_id)}
                title={!canApprove ? 'No cuentas con permiso para aprobar' : 'Aprobar'}
                disabled={!canApprove}
              >
                {!canApprove ? 'Esperando validación' : 'Aprobar'}
              </button>
            )}
            {order.status === 'approved' && canShip && (
              <button className="btn btn--sm btn--primary" onClick={() => onShip(order.order_id)} title="Marcar como Enviado">
                Enviar
              </button>
            )}
            {order.status === 'shipped' && canDeliver && (
              <button className="btn btn--sm btn--success" onClick={() => onDeliver(order.order_id)} title="Marcar como Entregado">
                Entregar
              </button>
            )}

            {/* Cancel button - PBAC: Nunca se permite cancelar pedidos entregados ni cancelados */}
            {canCancel && order.status !== 'cancelled' && order.status !== 'delivered' && (
              <button className="btn btn--sm btn--danger" onClick={() => onCancel(order.order_id)} title="Cancelar Pedido">
                Cancelar
              </button>
            )}

            {canAssign && order.status !== 'cancelled' && order.status !== 'delivered' && (
              <button className="btn btn--sm btn--secondary" onClick={() => onAssign(order)} title="Asignar/Reasignar Asesor Comercial">
                Asignar
              </button>
            )}

            {/* Enviar a Bodega si aún no se ha enviado y está APROBADO */}
            {!order.sent_to_warehouse && order.status === 'approved' && canSendWarehouse && (
              <button
                className="btn btn--sm btn--warehouse-send"
                onClick={() => onSendWarehouse(order)}
                title="Enviar pedido a surtido de bodega (Cola FIFO)"
              >
                <span>📦</span> A Bodega
              </button>
            )}

            {/* Ver Almacén si ya fue enviado a bodega */}
            {order.sent_to_warehouse && (
              <button
                className="btn btn--sm btn--warehouse-view"
                onClick={() => onViewWarehouse(order.order_id)}
                title="Ver avance de surtido de partidas y splits en almacén"
              >
                <span>🔍</span> En Bodega
              </button>
            )}

            <button className="btn btn--sm btn--ghost" onClick={() => onViewDetails(order.order_id)} title="Ver Detalles">
              Ver
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}
