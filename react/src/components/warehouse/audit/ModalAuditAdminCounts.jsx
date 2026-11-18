import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCog } from '@fortawesome/free-solid-svg-icons';
import warehouseService from '../../../services/warehouseService';

const PRESETS_1ST = [
  'Etiqueta o código dañado',
  'Producto sin código de barras',
  'Código borroso o manchado',
  'Lote / Presentación especial',
  'Ajuste final de surtido'
];

const PRESETS_2ND = [
  'Por Confianza (Validación en bloque)',
  'Mesa de Control y Calidad',
  'Etiqueta o código dañado',
  'Producto sin código de barras'
];

export default function ModalAuditAdminCounts({ item, onClose, onSaved }) {
  const [adminCounts, setAdminCounts] = useState({
    scanned_prods: 0,
    boxes: 0,
    box_prods: 0,
    box_units_calc: 1,
    manual_prods: 0,
    manual_reason: '',
    checker_scanned_prods: 0,
    checker_boxes: 0,
    checker_box_prods: 0,
    checker_box_units_calc: 1,
    checker_manual_prods: 0,
    checker_manual_reason: ''
  });
  const [adminSavingCounts, setAdminSavingCounts] = useState(false);

  useEffect(() => {
    if (item) {
      const boxP = item.box_prods ?? item.verified_by_box_count ?? 0;
      const chkBoxP = item.checker_box_prods || 0;
      const bCount = item.boxes || 0;
      const chkBCount = item.checker_boxes || 0;
      setAdminCounts({
        scanned_prods: item.scanned_prods ?? item.verified_by_scan_count ?? 0,
        boxes: bCount,
        box_prods: boxP,
        box_units_calc: bCount > 0 ? Math.round(boxP / bCount) : (boxP > 0 ? boxP : 10),
        manual_prods: item.manual_prods ?? item.verified_by_manual_count ?? 0,
        manual_reason: item.manual_reason || '',
        checker_scanned_prods: item.checker_scanned_prods || 0,
        checker_boxes: chkBCount,
        checker_box_prods: chkBoxP,
        checker_box_units_calc: chkBCount > 0 ? Math.round(chkBoxP / chkBCount) : (chkBoxP > 0 ? chkBoxP : 10),
        checker_manual_prods: item.checker_manual_prods || 0,
        checker_manual_reason: item.checker_manual_reason || ''
      });
    }
  }, [item]);

  if (!item) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setAdminSavingCounts(true);
      await warehouseService.adminOverrideItemCounts(item.order_item_id, {
        scanned_prods: Number(adminCounts.scanned_prods) || 0,
        boxes: Number(adminCounts.boxes) || 0,
        box_prods: Number(adminCounts.box_prods) || 0,
        manual_prods: Number(adminCounts.manual_prods) || 0,
        manual_reason: adminCounts.manual_reason ? adminCounts.manual_reason.trim() : null,
        checker_scanned_prods: Number(adminCounts.checker_scanned_prods) || 0,
        checker_boxes: Number(adminCounts.checker_boxes) || 0,
        checker_box_prods: Number(adminCounts.checker_box_prods) || 0,
        checker_manual_prods: Number(adminCounts.checker_manual_prods) || 0,
        checker_manual_reason: adminCounts.checker_manual_reason ? adminCounts.checker_manual_reason.trim() : null
      });

      onSaved?.(`✓ Conteos y dictamen forense rectificados para '${item.product_name}'.`);
      onClose();
    } catch (err) {
      alert(err.detail || err.message || 'Error al actualizar conteos');
    } finally {
      setAdminSavingCounts(false);
    }
  };

  const total1st = (Number(adminCounts.scanned_prods) || 0) + (Number(adminCounts.box_prods) || 0) + (Number(adminCounts.manual_prods) || 0);
  const total2nd = (Number(adminCounts.checker_scanned_prods) || 0) + (Number(adminCounts.checker_box_prods) || 0) + (Number(adminCounts.checker_manual_prods) || 0);

  return (
    <div className="modal-overlay modal-overlay--audit-admin-item" onClick={onClose}>
      <div className="modal modal--md" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2 m-0 text-base text-warning">
            <FontAwesomeIcon icon={faCog} /> Gestión Admin — Conteos y Justificaciones
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSave} className="warehouse-terminal__modal-form">
          <div className="modal__body">
            <div className="p-3 mb-3 bg-surface rounded border">
              <div className="font-bold text-base mb-1">{item.product_name}</div>
              <div className="d-flex justify-content-between align-items-center text-xs text-muted flex-wrap gap-2">
                <span>SKU: <strong className="font-mono">{item.product_id}</strong></span>
                <span>Requerido en Pedido: <strong className="text-primary font-bold">{item.quantity ?? item.quantity_required ?? 0} pzs</strong></span>
              </div>
            </div>

            <div className="alert alert--danger p-2 mb-3 text-xs leading-normal">
              <strong>⚠️ Rectificación Pericial Exclusiva de Administrador:</strong>
              <p className="m-0 mt-0.5">
                Modifica piezas de láser, cajas maestras y manuales de ambos filtros. Los totales y discrepancias se sincronizarán al instante.
              </p>
            </div>

            {/* 1er Filtro (Surtidor de Piso / Picker) */}
            <div className="order-details__section mb-3 p-3 border rounded">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h4 className="m-0 text-sm font-bold text-primary">
                  1er Filtro — Surtidor de Piso (Picker)
                </h4>
                <span className="badge badge--primary font-bold">
                  Total: {total1st} pzs
                </span>
              </div>

              <div className="warehouse-audit-modal__input-grid mb-3">
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Láser (L) pzs:</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.scanned_prods}
                    onChange={(e) => setAdminCounts({ ...adminCounts, scanned_prods: e.target.value })}
                    required
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Cajas (Cant):</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.boxes}
                    onChange={(e) => {
                      const b = Math.max(0, parseInt(e.target.value, 10) || 0);
                      const u = Math.max(1, parseInt(adminCounts.box_units_calc, 10) || 1);
                      setAdminCounts({
                        ...adminCounts,
                        boxes: e.target.value,
                        box_prods: b * u
                      });
                    }}
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Pzs / Caja:</label>
                  <input
                    type="number"
                    min="1"
                    className="input"
                    value={adminCounts.box_units_calc}
                    onChange={(e) => {
                      const u = Math.max(1, parseInt(e.target.value, 10) || 1);
                      const b = Math.max(0, parseInt(adminCounts.boxes, 10) || 0);
                      setAdminCounts({
                        ...adminCounts,
                        box_units_calc: e.target.value,
                        box_prods: b * u
                      });
                    }}
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Cajas (C) pzs:</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.box_prods}
                    onChange={(e) => {
                      const bp = Math.max(0, parseInt(e.target.value, 10) || 0);
                      const b = Math.max(1, parseInt(adminCounts.boxes, 10) || 1);
                      setAdminCounts({
                        ...adminCounts,
                        box_prods: e.target.value,
                        box_units_calc: Math.round(bp / b)
                      });
                    }}
                    required
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Manual (M) pzs:</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.manual_prods}
                    onChange={(e) => setAdminCounts({ ...adminCounts, manual_prods: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-group mb-0">
                <label className="form-group__label text-xs">Motivo / Justificación 1er Filtro:</label>
                <select
                  className="input mb-2"
                  value={
                    PRESETS_1ST.includes(adminCounts.manual_reason)
                      ? adminCounts.manual_reason
                      : adminCounts.manual_reason ? 'Otro' : ''
                  }
                  onChange={(e) => {
                    if (e.target.value === 'Otro') {
                      if (PRESETS_1ST.includes(adminCounts.manual_reason)) {
                        setAdminCounts({ ...adminCounts, manual_reason: '' });
                      }
                    } else {
                      setAdminCounts({ ...adminCounts, manual_reason: e.target.value });
                    }
                  }}
                >
                  <option value="">— Sin justificación manual —</option>
                  <option value="Etiqueta o código dañado">Etiqueta o código de barras dañado / ilegible</option>
                  <option value="Producto sin código de barras">Producto sin código de barras de origen</option>
                  <option value="Código borroso o manchado">Código borroso o manchado</option>
                  <option value="Lote / Presentación especial">Lote o presentación especial autorizada</option>
                  <option value="Ajuste final de surtido">Ajuste final de surtido de partidas restantes</option>
                  <option value="Otro">Otro motivo personalizado...</option>
                </select>

                {(!PRESETS_1ST.includes(adminCounts.manual_reason) || adminCounts.manual_reason === '') && (
                  <input
                    type="text"
                    className="input text-xs"
                    value={adminCounts.manual_reason}
                    onChange={(e) => setAdminCounts({ ...adminCounts, manual_reason: e.target.value })}
                    placeholder="Escribe el motivo o justificación pericial..."
                  />
                )}
              </div>
            </div>

            {/* 2do Filtro (Revisor / Checker) */}
            <div className="order-details__section p-3 border rounded">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h4 className="m-0 text-sm font-bold text-warning">
                  2do Filtro — Revisor / Mesa de Calidad (Checker)
                </h4>
                <span className="badge badge--warning font-bold">
                  Total: {total2nd} pzs
                </span>
              </div>

              <div className="warehouse-audit-modal__input-grid mb-3">
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Láser (L) pzs:</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.checker_scanned_prods}
                    onChange={(e) => setAdminCounts({ ...adminCounts, checker_scanned_prods: e.target.value })}
                    required
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Cajas (Cant):</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.checker_boxes}
                    onChange={(e) => {
                      const b = Math.max(0, parseInt(e.target.value, 10) || 0);
                      const u = Math.max(1, parseInt(adminCounts.checker_box_units_calc, 10) || 1);
                      setAdminCounts({
                        ...adminCounts,
                        checker_boxes: e.target.value,
                        checker_box_prods: b * u
                      });
                    }}
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Pzs / Caja:</label>
                  <input
                    type="number"
                    min="1"
                    className="input"
                    value={adminCounts.checker_box_units_calc}
                    onChange={(e) => {
                      const u = Math.max(1, parseInt(e.target.value, 10) || 1);
                      const b = Math.max(0, parseInt(adminCounts.checker_boxes, 10) || 0);
                      setAdminCounts({
                        ...adminCounts,
                        checker_box_units_calc: e.target.value,
                        checker_box_prods: b * u
                      });
                    }}
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Cajas (C) pzs:</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.checker_box_prods}
                    onChange={(e) => {
                      const bp = Math.max(0, parseInt(e.target.value, 10) || 0);
                      const b = Math.max(1, parseInt(adminCounts.checker_boxes, 10) || 1);
                      setAdminCounts({
                        ...adminCounts,
                        checker_box_prods: e.target.value,
                        checker_box_units_calc: Math.round(bp / b)
                      });
                    }}
                    required
                  />
                </div>
                <div className="warehouse-audit-modal__input-col">
                  <label className="form-group__label text-xs">Manual (M) pzs:</label>
                  <input
                    type="number"
                    min="0"
                    className="input"
                    value={adminCounts.checker_manual_prods}
                    onChange={(e) => setAdminCounts({ ...adminCounts, checker_manual_prods: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-group mb-0">
                <label className="form-group__label text-xs">Motivo / Justificación 2do Filtro:</label>
                <select
                  className="input mb-2"
                  value={
                    PRESETS_2ND.includes(adminCounts.checker_manual_reason)
                      ? adminCounts.checker_manual_reason
                      : adminCounts.checker_manual_reason ? 'Otro' : ''
                  }
                  onChange={(e) => {
                    if (e.target.value === 'Otro') {
                      if (PRESETS_2ND.includes(adminCounts.checker_manual_reason)) {
                        setAdminCounts({ ...adminCounts, checker_manual_reason: '' });
                      }
                    } else {
                      setAdminCounts({ ...adminCounts, checker_manual_reason: e.target.value });
                    }
                  }}
                >
                  <option value="">— Sin justificación de 2do filtro —</option>
                  <option value="Por Confianza (Validación en bloque)">🤝 Por Confianza (Validación en bloque)</option>
                  <option value="Mesa de Control y Calidad">Mesa de Control y Calidad</option>
                  <option value="Etiqueta o código dañado">Etiqueta o código de barras dañado / ilegible</option>
                  <option value="Producto sin código de barras">Producto sin código de barras de origen</option>
                  <option value="Otro">Otro motivo personalizado...</option>
                </select>

                {(!PRESETS_2ND.includes(adminCounts.checker_manual_reason) || adminCounts.checker_manual_reason === '') && (
                  <input
                    type="text"
                    className="input text-xs"
                    value={adminCounts.checker_manual_reason}
                    onChange={(e) => setAdminCounts({ ...adminCounts, checker_manual_reason: e.target.value })}
                    placeholder="Escribe el motivo o justificación pericial de 2do filtro..."
                  />
                )}
              </div>
            </div>
          </div>

          <div className="modal__footer warehouse-terminal__modal-footer-responsive">
            <button type="button" className="btn btn--secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--warning font-bold" disabled={adminSavingCounts}>
              {adminSavingCounts ? 'Guardando Conteos...' : 'Confirmar Rectificación Forense'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
