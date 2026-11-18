import React from 'react';

export default function LaserStationScannerHUD({
  split,
  isSegundoFiltro,
  isAdminOrAuditor,
  flashType,
  barcodeInputRef,
  barcodeInput,
  setBarcodeInput,
  scanning,
  handleScanSubmit,
  executeScan,
  setShowCameraModal,
  scanMessage,
  currentProgressCount,
  totalRequired,
  progressPct,
  totalVerified,
  checkerTotalVerified
}) {
  if (!split) return null;

  return (
    <>
      {/* Guía visual paso a paso para operarios */}
      <div className="warehouse-terminal__quick-instruction">
        <div className="warehouse-terminal__instruction-step">
          <span className="warehouse-terminal__instruction-num">1</span>
          <span>Apunta con la <strong>pistola lectora</strong> al código o haz clic en <strong>⚡ +1 Escanear</strong></span>
        </div>
        <div className="warehouse-terminal__instruction-step">
          <span className="warehouse-terminal__instruction-num">2</span>
          <span>Usa <strong>📦 Cajas</strong> para cajas cerradas o <strong>✍️ Manual</strong> si el código está roto</span>
        </div>
        <div className="warehouse-terminal__instruction-step">
          <span className="warehouse-terminal__instruction-num">3</span>
          <span>Al completar el 100%, presiona <strong>🔒 Sellar Split</strong> o <strong>🔍 Enviar a 2do Filtro</strong></span>
        </div>
      </div>

      {/* Escáner Láser Central Hands-Free (HUD Interactivo) */}
      <div className={`warehouse-terminal__scanner-card ${flashType === 'success' ? 'warehouse-terminal__scanner-card--success-flash' : flashType ? 'warehouse-terminal__scanner-card--error-flash' : ''}`}>
        <div className="d-flex align-items-center justify-content-between text-xs px-1 text-muted flex-wrap gap-2">
          <div className="d-flex align-items-center gap-2">
            <span>🟢</span>
            {split.uses_containers ? (
              (split.active_container_qr || split.container_qr) ? (
                <span>
                  Láser depositando en: <strong className="text-primary font-mono">{split.active_container_qr || split.container_qr}</strong>
                </span>
              ) : (
                <span className="text-warning font-bold">
                  ⚠️ Escanea el QR de una canasta antes de pistolear productos
                </span>
              )
            ) : (
              <span>
                Láser activo: <strong className="text-dark">Surtido Directo en Split</strong>
              </span>
            )}
          </div>
          <span className="text-xs opacity-75">
            Pistola lectora USB/Bluetooth lista • Foco automático
          </span>
        </div>

        <form onSubmit={handleScanSubmit}>
          <div className="warehouse-terminal__scanner-input-wrap">
            <input
              ref={barcodeInputRef}
              type="text"
              className="warehouse-terminal__scanner-input"
              placeholder={isSegundoFiltro 
                ? (split.uses_containers ? "⚡ Revisor: Dispara láser al producto o canasta..." : "⚡ Revisor: Dispara láser directo al producto...") 
                : split.uses_containers
                  ? ((split.active_container_qr || split.container_qr)
                    ? `⚡ Láser activo → Canasta ${split.active_container_qr || split.container_qr}...`
                    : "⚡ Modo Canastas: Dispara al QR de una canasta...")
                  : "⚡ Surtido Directo: Dispara con pistola láser al producto..."
              }
              value={barcodeInput}
              onChange={(e) => setBarcodeInput(e.target.value)}
              disabled={scanning || split.status === 'completed'}
              autoComplete="off"
            />
            {barcodeInput.trim() ? (
              <button
                type="submit"
                className="btn btn--primary warehouse-terminal__scanner-submit-btn"
                disabled={scanning || split.status === 'completed'}
                title="Disparar escaneo de este código"
              >
                {scanning ? '...' : '⚡ Disparar'}
              </button>
            ) : (
              <div className="d-flex align-items-center gap-1">
                <button
                  type="button"
                  className="warehouse-terminal__scanner-paste-btn"
                  title="Abrir cámara del dispositivo para escanear productos o canastas"
                  onClick={() => setShowCameraModal(true)}
                  style={{
                    backgroundColor: 'var(--color-primary)',
                    color: '#fff',
                    border: 'none',
                    fontWeight: '800'
                  }}
                >
                  📷 Cámara
                </button>
                <button
                  type="button"
                  className="warehouse-terminal__scanner-paste-btn"
                  title="Pegar código del portapapeles y disparar de inmediato sin abrir teclado"
                  onClick={async () => {
                    try {
                      if (navigator.clipboard?.readText) {
                        const text = await navigator.clipboard.readText();
                        if (text && text.trim()) {
                          await executeScan(text.trim());
                        }
                      }
                    } catch {
                      barcodeInputRef.current?.focus();
                    }
                  }}
                >
                  ⚡ Pegar
                </button>
              </div>
            )}
            <span className="warehouse-terminal__scanner-icon" title="Lector Láser Activo">
              📡
            </span>
          </div>
        </form>

        {/* Mensaje de Último Escaneo */}
        {scanMessage && (
          <div className={`warehouse-terminal__last-scan-status warehouse-terminal__last-scan-status--${scanMessage.type}`}>
            {scanMessage.text}
          </div>
        )}

        {/* Barra de Progreso General */}
        <div className="warehouse-terminal__progress-section">
          <div className="warehouse-terminal__progress-labels">
            <span>
              {isSegundoFiltro ? 'Progreso de revisión en 2do Filtro (Checker)' : 'Progreso de recolección en split (Picker)'}
            </span>
            <span>{currentProgressCount} de {totalRequired} piezas ({progressPct}%)</span>
          </div>
          <div className="warehouse-terminal__progress-bar-bg">
            <div
              className={`warehouse-terminal__progress-bar-fill ${isSegundoFiltro ? 'bg-warning' : ''}`}
              style={{ width: `${progressPct}%` }}
            ></div>
          </div>
          {isSegundoFiltro && (
            <div className="text-xs text-muted mt-1 d-flex justify-content-between">
              {isAdminOrAuditor && (
                <span>Surtido de piso (Picker): <strong>{totalVerified}/{totalRequired} piezas (100%)</strong></span>
              )}
              <span>Revisado en 2do filtro: <strong className="text-warning">{checkerTotalVerified}/{totalRequired} piezas</strong></span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
