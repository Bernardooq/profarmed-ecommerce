import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheck, faTimes, faEye, faSpinner } from '@fortawesome/free-solid-svg-icons';
import { formatCurrency } from '../../utils/formatUtils';
import usePermissions from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function OrderRowAdmin({
  order,
  onApprove,
  onCancel,
  onViewDetails,
  isLoading
}) {
  const { can, isAdmin } = usePermissions();
  const canStatusMaster = isAdmin || can(PERMISSIONS.ORDERS_STATUS);
  const canApprove = canStatusMaster || can(PERMISSIONS.ORDERS_APPROVE);
  const canCancel = canStatusMaster || can(PERMISSIONS.ORDERS_CANCEL);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-MX', {
      timeZone: 'America/Mexico_City',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  const clientName = order.customer?.full_name || order.customer?.username || 'N/A';
  const clientContact = order.customer?.email || 'N/A';
  const itemCount = order.items_count !== undefined ? order.items_count : (order.items?.length || 0);

  return (
    <tr>
      <td data-label="Cliente">{clientName}</td>
      <td data-label="Contacto">{clientContact}</td>
      <td data-label="Id Pedido">{order.order_id}</td>
      <td data-label="Fecha">{formatDate(order.created_at)}</td>
      <td data-label="Items">{itemCount}</td>
      <td data-label="Total">{formatCurrency(order.total_amount)}</td>
      <td data-label="Acciones" className="actions-cell">
        {isLoading ? (
          <FontAwesomeIcon icon={faSpinner} spin />
        ) : (
          <>
            {canApprove && onApprove && (order.status === 'pending_validation' || order.status === 'assigned') && (
              <button className="btn btn--icon btn--success" aria-label="Aprobar pedido" onClick={() => onApprove(order.order_id)} disabled={isLoading} title="Aprobar">
                <FontAwesomeIcon icon={faCheck} />
              </button>
            )}
            {canCancel && onCancel && order.status !== 'cancelled' && order.status !== 'delivered' && (
              <button className="btn btn--icon btn--danger" aria-label="Rechazar pedido" onClick={() => onCancel(order.order_id)} disabled={isLoading} title="Rechazar">
                <FontAwesomeIcon icon={faTimes} />
              </button>
            )}
            <button className="btn btn--icon btn--ghost" aria-label="Ver detalles del pedido" onClick={() => onViewDetails && onViewDetails(order.order_id)} disabled={isLoading} title="Ver Detalles">
              <FontAwesomeIcon icon={faEye} />
            </button>
          </>
        )}
      </td>
    </tr>
  );
}