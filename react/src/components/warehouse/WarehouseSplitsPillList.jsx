import React from 'react';

/**
 * WarehouseSplitsPillList.jsx
 * Renderizado reutilizable de pastillas (pills) de splits en tablas de pedidos.
 */
export default function WarehouseSplitsPillList({ splits = [], onOrderClick }) {
  const sortedSplits = [...splits].sort((a, b) => {
    const isACompleted = a.status === 'completed';
    const isBCompleted = b.status === 'completed';
    if (isACompleted && !isBCompleted) return 1;
    if (!isACompleted && isBCompleted) return -1;
    return (a.split_number ?? 0) - (b.split_number ?? 0);
  });

  const visibleSplits = sortedSplits.slice(0, 2);
  const extraCount = sortedSplits.length - 2;

  return (
    <div className="warehouse-manager__splits-preview">
      {visibleSplits.map((b) => (
        <button
          key={b.split_id}
          type="button"
          className={`warehouse-manager__split-pill warehouse-manager__split-pill--${b.status}`}
          title={`Lote / Split ${b.split_code ? `[${b.split_code}] ` : ''}#${b.split_number ?? b.split_index}: ${b.status}. Clic para ver detalle / asignar.`}
          onClick={onOrderClick}
        >
          <span>{b.uses_containers ? '🧺' : '📦'} {b.split_code || `#${b.split_number ?? b.split_index}`}</span>
          <span className="text-xs opacity-75">
            ({b.status === 'completed' ? 'Sellada' : b.status})
          </span>
        </button>
      ))}
      {extraCount > 0 && (
        <button
          type="button"
          className="warehouse-manager__split-pill warehouse-manager__split-pill--pending font-bold"
          title={`Ver las ${splits.length} splits de este pedido`}
          onClick={onOrderClick}
        >
          ... (+{extraCount})
        </button>
      )}
    </div>
  );
}
