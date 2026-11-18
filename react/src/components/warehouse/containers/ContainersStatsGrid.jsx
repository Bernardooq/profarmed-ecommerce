import React from 'react';

/**
 * ContainersStatsGrid
 * Despliega las tarjetas de métricas (KPIs) del parque físico de canastas QR.
 * Cada tarjeta es interactiva y permite filtrar el catálogo por estado.
 */
export default function ContainersStatsGrid({
  stats = {},
  statusFilter = '',
  onSelectFilter
}) {
  const totalCount = stats.total || 0;
  const availableCount = stats.available || 0;
  const inUseCount = stats.in_use || 0;
  const maintenanceCount = stats.maintenance || 0;
  const retiredCount = stats.retired || 0;

  return (
    <div className="stat-grid mb-6">
      <div
        className={`stat-card ${statusFilter === '' ? 'stat-card--active' : ''}`}
        style={{ cursor: 'pointer' }}
        onClick={() => onSelectFilter('')}
        title="Ver todas las canastas"
      >
        <div className="stat-card__icon">🧺</div>
        <div className="stat-card__content">
          <span className="stat-card__value">{totalCount}</span>
          <span className="stat-card__label">Total en Parque</span>
        </div>
      </div>

      <div
        className={`stat-card ${statusFilter === 'available' ? 'stat-card--active' : ''}`}
        style={{ cursor: 'pointer' }}
        onClick={() => onSelectFilter('available')}
        title="Filtrar por canastas disponibles (vacías)"
      >
        <div className="stat-card__icon stat-card__icon--success">🟢</div>
        <div className="stat-card__content">
          <span className="stat-card__value text-success">{availableCount}</span>
          <span className="stat-card__label">Disponibles (Vacías)</span>
        </div>
      </div>

      <div
        className={`stat-card ${statusFilter === 'in_use' ? 'stat-card--active' : ''}`}
        style={{ cursor: 'pointer' }}
        onClick={() => onSelectFilter('in_use')}
        title="Filtrar por canastas en surtido o revisión activa"
      >
        <div className="stat-card__icon stat-card__icon--info">🔵</div>
        <div className="stat-card__content">
          <span className="stat-card__value text-primary">{inUseCount}</span>
          <span className="stat-card__label">En Surtido / Revisión</span>
        </div>
      </div>

      <div
        className={`stat-card ${statusFilter === 'maintenance' ? 'stat-card--active' : ''}`}
        style={{ cursor: 'pointer' }}
        onClick={() => onSelectFilter('maintenance')}
        title="Filtrar por canastas en mantenimiento físico"
      >
        <div className="stat-card__icon stat-card__icon--warning">🟡</div>
        <div className="stat-card__content">
          <span className="stat-card__value text-warning">{maintenanceCount}</span>
          <span className="stat-card__label">En Mantenimiento</span>
        </div>
      </div>

      <div
        className={`stat-card ${statusFilter === 'retired' ? 'stat-card--active' : ''}`}
        style={{ cursor: 'pointer' }}
        onClick={() => onSelectFilter('retired')}
        title="Filtrar por canastas retiradas o dadas de baja"
      >
        <div className="stat-card__icon stat-card__icon--danger">🔴</div>
        <div className="stat-card__content">
          <span className="stat-card__value text-danger">{retiredCount}</span>
          <span className="stat-card__label">Retiradas / Bajas</span>
        </div>
      </div>
    </div>
  );
}
