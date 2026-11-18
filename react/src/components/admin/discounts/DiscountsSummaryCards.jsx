import React from 'react';

export default function DiscountsSummaryCards({ stats }) {
  if (!stats) return null;

  return (
    <div className="discounts-manager__summary-grid">
      <div className="discounts-manager__stat-card">
        <div className="discounts-manager__stat-label">Total Registrados</div>
        <div className="discounts-manager__stat-val">{stats.total ?? 0}</div>
      </div>
      <div className="discounts-manager__stat-card">
        <div className="discounts-manager__stat-label">Activos y Vigentes</div>
        <div className="discounts-manager__stat-val discounts-manager__stat-val--success">
          {stats.active ?? 0}
        </div>
      </div>
      <div className="discounts-manager__stat-card">
        <div className="discounts-manager__stat-label">Generales (Base)</div>
        <div className="discounts-manager__stat-val discounts-manager__stat-val--primary">
          {stats.general ?? 0}
        </div>
      </div>
      <div className="discounts-manager__stat-card">
        <div className="discounts-manager__stat-label">Por Lista de Precios</div>
        <div className="discounts-manager__stat-val discounts-manager__stat-val--purple">
          {stats.price_list ?? 0}
        </div>
      </div>
    </div>
  );
}
