import React from 'react';

export default function LaserStationModeBar({
  split,
  isSegundoFiltro,
  canModeContainers,
  canModeDirect,
  handleSwitchContainer,
  handleReleaseContainer,
  handleToggleContainerMode,
  togglingContainerMode,
  setBindContainerError,
  setContainerQrInput,
  setShowBindContainerModal
}) {
  if (!split) return null;

  return (
    <div className="warehouse-terminal__mode-strip p-3 bg-surface border rounded-xl d-flex align-items-center justify-content-between flex-wrap gap-3 shadow-xs">
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <span className="text-xs text-muted font-bold text-uppercase tracking-wider">
          Modalidad:
        </span>
        {split.uses_containers ? (
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <span className="badge badge--primary text-xs font-bold d-inline-flex align-items-center gap-1">
              🧺 Con Canastas QR
            </span>
            {/* Canastas vinculadas */}
            {split.containers && split.containers.length > 0 ? (
              split.containers.map(c => {
                const isActive = c.qr_code === (split.active_container_qr || split.container_qr);
                const summary = (split.containers_summary || []).find(s => s.container_id === c.container_id);
                const pieces = summary?.total_pieces ?? 0;
                return (
                  <span
                    key={c.container_id}
                    className={`badge ${isActive ? 'badge--primary' : 'badge--secondary'} font-mono text-sm d-inline-flex align-items-center gap-1 shadow-xs`}
                    onClick={() => !isActive && handleSwitchContainer(c.qr_code)}
                    title={isActive ? `🧺 Canasta ACTUAL donde se depositan los siguientes escaneos (${c.qr_code}${pieces > 0 ? ` · ${pieces} pzs` : ''})` : `👉 Haz clic para activar canasta ${c.qr_code}${pieces > 0 ? ` · ${pieces} pzs` : ''}`}
                    style={{ cursor: 'pointer', border: isActive ? '2px solid #fff' : 'none' }}
                  >
                    <span>🧺 {c.qr_code}{pieces > 0 ? ` (${pieces} pz)` : ''}</span>
                    {isActive ? (
                      <small className="badge badge--success py-0 px-1 text-xs ms-1 font-bold">ACTIVA</small>
                    ) : (
                      <small className="opacity-75 ms-1">(activar)</small>
                    )}
                    {!isSegundoFiltro && split.status !== 'completed' && (
                      <button
                        type="button"
                        className="btn btn--ghost btn--xs text-white p-0 ms-1 opacity-75 hover-opacity-100"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReleaseContainer(c.container_id, c.qr_code);
                        }}
                        title={`Liberar canasta ${c.qr_code} de este split`}
                      >
                        ×
                      </button>
                    )}
                  </span>
                );
              })
            ) : (
              <span className="badge badge--warning text-xs font-bold" title="Usa canastas pero aún no tiene canasta física vinculada">
                ⚠️ Sin canasta activa vinculada
              </span>
            )}
          </div>
        ) : (
          <span className="badge badge--secondary text-xs font-bold" title="Surtido directo a nivel de split sin división en canastas">
            📦 Surtido Directo por Split (Sin Canastas)
          </span>
        )}
      </div>

      {/* Acciones de Modalidad */}
      {!isSegundoFiltro && split.status !== 'completed' && (
        <div className="d-flex align-items-center gap-2 flex-wrap">
          {split.uses_containers ? (
            <>
              {canModeContainers && (
                <button
                  type="button"
                  className="btn btn--primary btn--xs font-bold"
                  onClick={() => {
                    setBindContainerError(null);
                    setContainerQrInput('');
                    setShowBindContainerModal(true);
                  }}
                  title="Vincular o escanear otra canasta física para este split"
                >
                  ➕ Vincular Otra Canasta
                </button>
              )}
              {canModeDirect && (
                <button
                  type="button"
                  className="btn btn--ghost btn--xs text-muted"
                  onClick={() => handleToggleContainerMode(false)}
                  disabled={togglingContainerMode}
                  title="Cambiar a surtido directo por split sin canastas físicas"
                >
                  📦 Pasar a Surtido Directo
                </button>
              )}
            </>
          ) : (
            canModeContainers && (
              <button
                type="button"
                className="btn btn--outline-primary btn--xs font-bold"
                onClick={() => handleToggleContainerMode(true)}
                disabled={togglingContainerMode}
                title="Activar canastas QR físicas para este split"
              >
                🧺 Usar Canastas QR
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}
