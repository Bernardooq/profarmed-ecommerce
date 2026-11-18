import React from 'react';

/**
 * WarehouseStatsGrid.jsx
 * Grid reutilizable de tarjetas KPI para el módulo de almacén / bodega.
 */
export default function WarehouseStatsGrid({ stats }) {
  return (
    <div className="stat-grid mb-6">
      <div className="stat-card">
        <div className="stat-card__icon stat-card__icon--warning">⏳</div>
        <div className="stat-card__content">
          <span className="stat-card__value">
            {stats ? (stats.orders_pending_queue ?? stats.pending_orders ?? 0) : '—'}
          </span>
          <span className="stat-card__label">Pedidos en Cola FIFO</span>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-card__icon stat-card__icon--info">🔄</div>
        <div className="stat-card__content">
          <span className="stat-card__value">
            {stats ? (stats.orders_in_progress ?? 0) : '—'}
          </span>
          <span className="stat-card__label">Pedidos en Surtido</span>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-card__icon">🧺</div>
        <div className="stat-card__content">
          <span className="stat-card__value">
            {stats ? (stats.active_splits_in_floor ?? stats.active_splits ?? 0) : '—'}
          </span>
          <span className="stat-card__label">Splits en Piso</span>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-card__icon stat-card__icon--success">🔒</div>
        <div className="stat-card__content">
          <span className="stat-card__value">
            {stats ? (stats.orders_completed_today ?? stats.completed_orders_today ?? 0) : '—'}
          </span>
          <span className="stat-card__label">Completados Hoy</span>
        </div>
      </div>
    </div>
  );
}
