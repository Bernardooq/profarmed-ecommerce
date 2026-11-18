import React from 'react';

/**
 * WarehouseStatusBadge.jsx
 * Componente reutilizable para renderizar insignias de estado de pedidos y splits de bodega.
 */
export default function WarehouseStatusBadge({ status }) {
  switch (status) {
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
      return <span className="warehouse-badge">{status || '—'}</span>;
  }
}
