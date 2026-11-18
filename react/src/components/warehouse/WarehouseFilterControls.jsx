import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSearch, faRotateRight } from '@fortawesome/free-solid-svg-icons';

/**
 * WarehouseFilterControls.jsx
 * Barra de controles y filtros reutilizable para Almacén / Bodega.
 */
export default function WarehouseFilterControls({
  search,
  onSearchChange,
  onSearchSubmit,
  searchPlaceholder = 'Buscar por # pedido, lote o cliente (ej. 105-1)...',
  assignedToMe,
  onAssignedToMeChange,
  statusFilter,
  onStatusFilterChange,
  auditVerdictFilter,
  onAuditVerdictFilterChange,
  showAuditVerdictFilter = false,
  onRefresh,
  loading = false,
  extraButtons = null,
  showStatusFilter = true,
  onQuickScanSplit = null
}) {
  const [quickSplitCode, setQuickSplitCode] = React.useState('');

  const handleQuickSplitSubmit = (e) => {
    e.preventDefault();
    const code = quickSplitCode.trim();
    if (code && onQuickScanSplit) {
      onQuickScanSplit(code);
      setQuickSplitCode('');
    }
  };
  return (
    <div className="dashboard-controls mb-4">
      <form className="search-bar" onSubmit={onSearchSubmit}>
        <input
          type="search"
          className="input"
          placeholder={searchPlaceholder}
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <button type="submit" aria-label="Buscar">
          <FontAwesomeIcon icon={faSearch} />
        </button>
      </form>

      {/* Selector de Asignación: Todos vs Solo asignados a mí */}
      {onAssignedToMeChange && (
        <div className="btn-group" role="group">
          <button
            type="button"
            className={`btn btn--sm ${!assignedToMe ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => onAssignedToMeChange(false)}
          >
            🌐 Todos
          </button>
          <button
            type="button"
            className={`btn btn--sm ${assignedToMe ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => onAssignedToMeChange(true)}
          >
            👤 Solo asignados a mí
          </button>
        </div>
      )}

      {/* Selector de Estatus */}
      {showStatusFilter && onStatusFilterChange && (
        <div className="filter-group">
          <label className="filter-group__label">Estatus:</label>
          <select
            className="input select"
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
          >
            <option value="">Todos los Estatus</option>
            <option value="pending">Pendiente FIFO</option>
            <option value="in_progress_partial">En Surtido (1er Filtro)</option>
            <option value="checking">En Revisión (2do Filtro)</option>
            <option value="completed">Completado / Sellado</option>
          </select>
        </div>
      )}

      {/* Selector de Veredicto de Auditoría (Exclusivo Administrador) */}
      {showAuditVerdictFilter && onAuditVerdictFilterChange && (
        <div className="filter-group">
          <label className="filter-group__label">⚖️ Veredicto:</label>
          <select
            className="input select"
            value={auditVerdictFilter || ''}
            onChange={(e) => onAuditVerdictFilterChange(e.target.value)}
          >
            <option value="">Todos los Veredictos</option>
            <option value="clean">✓ Íntegro / Escaneo Completo (Clean)</option>
            <option value="clean_confidence">🤝 Íntegro por Confianza (Fast-Track)</option>
            <option value="incomplete">⚠️ Faltantes (Incomplete)</option>
            <option value="inconsistent">⚡ Discrepancia Surtidor/Revisor (Inconsistent)</option>
            <option value="incomplete_and_inconsistent">🚨 Faltantes y Discrepancias</option>
          </select>
        </div>
      )}

      {/* Buscador directo de lote / split para abrir terminal */}
      {onQuickScanSplit && (
        <form className="warehouse-quick-scan" onSubmit={handleQuickSplitSubmit}>
          <input
            type="text"
            className="input input--sm warehouse-quick-scan__input"
            placeholder="⚡ Escanear Lote (ej. 105-1)..."
            value={quickSplitCode}
            onChange={(e) => setQuickSplitCode(e.target.value)}
          />
          <button
            type="submit"
            className="btn btn--sm btn--primary font-bold"
            title="Abrir este lote directamente en la terminal láser"
            disabled={!quickSplitCode.trim()}
          >
            Abrir
          </button>
        </form>
      )}

      {/* Botones adicionales / Acción */}
      <div className="d-flex align-items-center gap-2 flex-wrap">
        {extraButtons}

        {onRefresh && (
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={onRefresh}
            disabled={loading}
            title="Refrescar datos"
          >
            <FontAwesomeIcon icon={faRotateRight} spin={loading} /> Actualizar
          </button>
        )}
      </div>
    </div>
  );
}
