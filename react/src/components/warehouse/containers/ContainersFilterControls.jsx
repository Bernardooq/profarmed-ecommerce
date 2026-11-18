import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch } from '@fortawesome/free-solid-svg-icons';
import ItemsPerPageSelector from '../../common/ItemsPerPageSelector';

/**
 * ContainersFilterControls
 * Barra de búsqueda y botones de filtrado por estado de canastas físicas QR.
 */
export default function ContainersFilterControls({
  searchTerm = '',
  onSearchChange,
  onSearchSubmit,
  statusFilter = '',
  onSelectFilter,
  stats = {}
}) {
  const totalCount = stats.total || 0;
  const availableCount = stats.available || 0;
  const inUseCount = stats.in_use || 0;
  const maintenanceCount = stats.maintenance || 0;
  const retiredCount = stats.retired || 0;

  return (
    <div className="dashboard-controls mb-4">
      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault();
          if (onSearchSubmit) onSearchSubmit(searchTerm);
        }}
      >
        <input
          type="search"
          className="input"
          placeholder="Buscar por código QR (ej: TOTE-001) o ID..."
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <button type="submit" aria-label="Buscar">
          <FontAwesomeIcon icon={faSearch} />
        </button>
      </form>

      <div className="btn-group" role="group">
        <button
          type="button"
          className={`btn btn--sm ${statusFilter === '' ? 'btn--primary' : 'btn--secondary'}`}
          onClick={() => onSelectFilter('')}
        >
          Todas ({totalCount})
        </button>
        <button
          type="button"
          className={`btn btn--sm ${statusFilter === 'available' ? 'btn--primary' : 'btn--secondary'}`}
          onClick={() => onSelectFilter('available')}
        >
          🟢 Disponibles ({availableCount})
        </button>
        <button
          type="button"
          className={`btn btn--sm ${statusFilter === 'in_use' ? 'btn--primary' : 'btn--secondary'}`}
          onClick={() => onSelectFilter('in_use')}
        >
          🔵 En Uso ({inUseCount})
        </button>
        <button
          type="button"
          className={`btn btn--sm ${statusFilter === 'maintenance' ? 'btn--primary' : 'btn--secondary'}`}
          onClick={() => onSelectFilter('maintenance')}
        >
          🟡 Mantenimiento ({maintenanceCount})
        </button>
        <button
          type="button"
          className={`btn btn--sm ${statusFilter === 'retired' ? 'btn--primary' : 'btn--secondary'}`}
          onClick={() => onSelectFilter('retired')}
        >
          🔴 Retiradas ({retiredCount})
        </button>
      </div>

      <ItemsPerPageSelector />
    </div>
  );
}
