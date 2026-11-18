import React from 'react';

export default function AuditKpiGrid({
  auditData,
  totalProductsSummary,
  getStatusBadge,
  isAdmin,
  canSupervisor,
  onToggleVisibility,
  togglingVisibility
}) {
  if (!auditData) return null;

  return (
    <div className="warehouse-audit-modal__kpi-grid">
      {/* Card 1: Dictamen y Estatus */}
      <div className={`warehouse-audit-modal__kpi-card ${
        auditData.audit_verdict === 'clean' ? 'warehouse-audit-modal__kpi-card--success' :
        auditData.audit_verdict === 'incomplete' ? 'warehouse-audit-modal__kpi-card--warning' :
        (auditData.audit_verdict === 'inconsistent' || auditData.audit_verdict === 'incomplete_and_inconsistent') ? 'warehouse-audit-modal__kpi-card--danger' :
        ''
      }`}>
        <div className="warehouse-audit-modal__kpi-icon">
          {auditData.audit_verdict === 'clean' ? '✅' :
           auditData.audit_verdict === 'incomplete' ? '⚠️' :
           (auditData.audit_verdict === 'inconsistent' || auditData.audit_verdict === 'incomplete_and_inconsistent') ? '🚨' :
           '📦'}
        </div>
        <div className="warehouse-audit-modal__kpi-content">
          <span className="kpi-label">Dictamen de Almacén</span>
          <div className="kpi-val">
            {auditData.audit_verdict === 'clean' && <span className="text-success">Íntegro y Cuadrado</span>}
            {auditData.audit_verdict === 'incomplete' && <span className="text-warning">Faltantes Detectados</span>}
            {auditData.audit_verdict === 'inconsistent' && <span className="text-danger">Discrepancia Surtidor/Revisor</span>}
            {auditData.audit_verdict === 'incomplete_and_inconsistent' && <span className="text-danger">Incompleto + Discrepancia</span>}
            {!auditData.audit_verdict && <span>{getStatusBadge(auditData.warehouse_status)}</span>}
          </div>
          <div className="kpi-sub d-flex align-items-center gap-1 flex-wrap">
            <span>Estatus:</span>
            {getStatusBadge(auditData.warehouse_status)}
          </div>
        </div>
      </div>

      {/* Card 2: Modalidad Operativa (Canastas vs Directo) */}
      <div className="warehouse-audit-modal__kpi-card warehouse-audit-modal__kpi-card--highlight">
        <div className="warehouse-audit-modal__kpi-icon">
          {auditData.splits?.some(s => s.uses_containers || (s.containers && s.containers.length > 0)) ? '🧺' : '📦'}
        </div>
        <div className="warehouse-audit-modal__kpi-content">
          <span className="kpi-label">Modalidad Operativa</span>
          <div className="kpi-val">
            {auditData.splits?.some(s => s.uses_containers || (s.containers && s.containers.length > 0)) ? (
              <span className="badge badge--primary font-bold">
                🧺 Con Canastas Físicas
              </span>
            ) : (
              <span className="badge badge--secondary font-bold">
                📦 Surtido Directo (Sin Canastas)
              </span>
            )}
          </div>
          <div className="kpi-sub">
            {auditData.splits?.some(s => s.uses_containers || (s.containers && s.containers.length > 0))
              ? `${auditData.splits?.reduce((acc, s) => acc + (s.containers?.length || (s.containers_summary?.length || 0)), 0)} canasta(s) QR vinculadas`
              : 'Recolección directa a empaque final en piso'}
          </div>
        </div>
      </div>

      {/* Card 3: Balance de Piezas */}
      <div className="warehouse-audit-modal__kpi-card">
        <div className="warehouse-audit-modal__kpi-icon">
          📊
        </div>
        <div className="warehouse-audit-modal__kpi-content">
          <span className="kpi-label">Balance de Piezas</span>
          <div className="kpi-val font-mono">
            {(() => {
              const req = totalProductsSummary.reduce((acc, it) => acc + it.required, 0);
              const verif = totalProductsSummary.reduce((acc, it) => acc + it.quantity, 0);
              const pct = req > 0 ? Math.min(100, Math.round((verif / req) * 100)) : 0;
              return (
                <>
                  <span className={verif >= req ? 'text-success' : 'text-warning'}>
                    {verif} / {req} pz
                  </span>
                  <span className="badge badge--info text-xs">{pct}%</span>
                </>
              );
            })()}
          </div>
          <div className="kpi-sub">
            {totalProductsSummary.length} producto(s) en {auditData.total_splits} split(s)
          </div>
        </div>
      </div>

      {/* Card 4: Sellos y Trazabilidad */}
      <div className="warehouse-audit-modal__kpi-card">
        <div className="warehouse-audit-modal__kpi-icon">
          🔒
        </div>
        <div className="warehouse-audit-modal__kpi-content">
          <span className="kpi-label">Sellos y Trazabilidad</span>
          <div className="kpi-val font-mono text-sm">
            {auditData.security_seals && auditData.security_seals.length > 0
              ? auditData.security_seals.join(', ')
              : (auditData.splits && auditData.splits.map(b => b.security_seal_folio).filter(Boolean).join(', ')) || (
                <span className="text-muted font-normal text-xs">Sin sellos aplicados</span>
              )}
          </div>
          <div className="kpi-sub d-flex align-items-center gap-1 flex-wrap">
            <span>Liberado:</span>
            <span className="font-mono text-xs">
              {auditData.sent_to_warehouse_at || auditData.warehouse_sent_at
                ? new Date(auditData.sent_to_warehouse_at || auditData.warehouse_sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : 'N/A'}
            </span>
            {(isAdmin || canSupervisor) && (
              <button
                type="button"
                className="btn btn--link btn--xs p-0 text-primary ms-1"
                onClick={onToggleVisibility}
                disabled={togglingVisibility}
                title={auditData.warehouse_show_details ? "Cambiar a Surtido Ciego" : "Cambiar a Modo Detallado"}
              >
                {togglingVisibility ? '...' : (auditData.warehouse_show_details ? '👁️ Detallado' : '🔒 Ciego')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
