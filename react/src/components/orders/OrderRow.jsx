import usePermissions from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function OrderRow({ order, onSelect, onCancel, onOpenTicket }) {
  const { can } = usePermissions();
  const canCancelPermission = can(PERMISSIONS.ORDERS_CANCEL);
  // Un cliente o staff puede cancelar si el backend/rol lo autoriza y el pedido sigue en validación preliminar
  const isCancellableState = order.rawStatus === 'pending_validation';
  const showCancelButton = canCancelPermission && isCancellableState && Boolean(onCancel);
  const showTicketButton = can(PERMISSIONS.SUPPORT_CREATE) && Boolean(onOpenTicket);

  return (
    <tr>
      <td data-label="N° de Pedido">{order.id}</td>
      <td data-label="Fecha">{order.date}</td>
      <td data-label="Total">{order.total}</td>
      <td data-label="Estado">
        <span className={`status-badge status-badge--${order.statusClass}`}>
          {order.status}
        </span>
      </td>
      <td data-label="Acciones" className="actions-cell">
        <button className="btn btn--secondary btn--sm" onClick={onSelect} title="Ver detalles del pedido">
          Ver Detalles
        </button>
        {showTicketButton && (
          <button 
            className="btn btn--outline btn--sm" 
            onClick={() => onOpenTicket(order)} 
            title="Reportar incidencia o abrir ticket sobre este pedido"
          >
            🎫 Reportar
          </button>
        )}
        {showCancelButton && (
          <button className="btn btn--danger btn--sm" onClick={() => onCancel(order)}>
            Cancelar
          </button>
        )}
      </td>
    </tr>
  );
}