import React, { useState, useEffect } from 'react';
import warehouseService from '../../../services/warehouseService';

const PRESETS = [
  'Etiqueta o código dañado',
  'Producto sin código de barras',
  'Código borroso o manchado',
  'Lote / Presentación especial',
  'Ajuste final de surtido'
];

export default function ModalAuditEditReason({ item, onClose, onSaved }) {
  const [selectedReasonPreset, setSelectedReasonPreset] = useState('Etiqueta o código dañado');
  const [customReasonText, setCustomReasonText] = useState('');
  const [savingReason, setSavingReason] = useState(false);

  useEffect(() => {
    if (item) {
      const existing = item.manual_reason || '';
      if (PRESETS.includes(existing)) {
        setSelectedReasonPreset(existing);
        setCustomReasonText('');
      } else if (existing) {
        setSelectedReasonPreset('Otro');
        setCustomReasonText(existing);
      } else {
        setSelectedReasonPreset('Etiqueta o código dañado');
        setCustomReasonText('');
      }
    }
  }, [item]);

  if (!item) return null;

  const handleSave = async (e) => {
    e.preventDefault();
    const finalReason = selectedReasonPreset === 'Otro' ? customReasonText.trim() : selectedReasonPreset;
    if (!finalReason) {
      alert('Debes indicar un motivo o justificación');
      return;
    }

    try {
      setSavingReason(true);
      await warehouseService.updateOrderItemManualReason(item.order_item_id, finalReason);
      onSaved?.(`✓ Justificación actualizada para '${item.product_name}'.`);
      onClose();
    } catch (err) {
      alert(err.detail || err.message || 'Error al actualizar motivo');
    } finally {
      setSavingReason(false);
    }
  };

  return (
    <div className="modal-overlay modal-overlay--audit-edit" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2 m-0 text-base">
            <span>✏️</span> Editar Justificación de Partida
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSave}>
          <div className="modal__body">
            <p className="text-sm font-bold mb-1">{item.product_name}</p>
            <p className="text-xs text-muted mb-3">
              Requerido: {item.quantity ?? item.quantity_required ?? 0} | Verificado Manual: {item.manual_prods || 0}
            </p>

            <div className="form-group mb-3">
              <label className="form-group__label">Motivo de Auditoría:</label>
              <select
                className="input"
                value={selectedReasonPreset}
                onChange={(e) => setSelectedReasonPreset(e.target.value)}
              >
                <option value="Etiqueta o código dañado">Etiqueta o código de barras dañado / ilegible</option>
                <option value="Producto sin código de barras">Producto sin código de barras de origen</option>
                <option value="Código borroso o manchado">Código borroso o manchado</option>
                <option value="Lote / Presentación especial">Lote o presentación especial autorizada</option>
                <option value="Ajuste final de surtido">Ajuste final de surtido de partidas restantes</option>
                <option value="Otro">Otro motivo personalizado...</option>
              </select>
            </div>

            {selectedReasonPreset === 'Otro' && (
              <div className="form-group mb-3">
                <label className="form-group__label">Detalle pericial del motivo:</label>
                <textarea
                  className="input"
                  rows={3}
                  value={customReasonText}
                  onChange={(e) => setCustomReasonText(e.target.value)}
                  placeholder="Explica la razón pericial para auditoría y vendedor..."
                  required
                />
              </div>
            )}
          </div>

          <div className="modal__footer">
            <button type="button" className="btn btn--secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--primary" disabled={savingReason}>
              {savingReason ? 'Guardando...' : 'Guardar Justificación'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
