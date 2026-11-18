import React, { useState } from 'react';
import warehouseService from '../../services/warehouseService';

export default function ModalSendToWarehouse({ isOpen, onClose, orderId, onSuccess }) {
  const [manualOrderId, setManualOrderId] = useState('');
  const [splitsCountInput, setSplitsCountInput] = useState('1');
  const [blindMode, setBlindMode] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  React.useEffect(() => {
    if (isOpen) {
      setSplitsCountInput('1');
      setManualOrderId('');
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const targetOrderId = orderId || parseInt(manualOrderId, 10);

  const handleSplitsBlur = () => {
    const val = parseInt(splitsCountInput, 10);
    if (isNaN(val) || val < 1) {
      setSplitsCountInput('1');
    } else if (val > 20) {
      setSplitsCountInput('20');
    } else {
      setSplitsCountInput(String(val));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!targetOrderId) {
      setError('Por favor indica un ID de pedido válido');
      return;
    }
    const finalSplits = Math.max(1, Math.min(20, parseInt(splitsCountInput, 10) || 1));
    try {
      setLoading(true);
      setError(null);
      await warehouseService.sendToWarehouse(targetOrderId, finalSplits, !blindMode);
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err.detail || err.message || 'Error al enviar pedido a bodega');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2">
            <span>🏭</span> Enviar Pedido {orderId ? `#${orderId}` : ''} a Bodega
          </h3>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar">
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal__body">
            {error && <div className="alert alert--danger mb-4">{error}</div>}

            {!orderId && (
              <div className="form-group mb-4">
                <label className="form-group__label" htmlFor="manual_order_id">
                  ID del Pedido: *
                </label>
                <input
                  id="manual_order_id"
                  type="number"
                  min="1"
                  className="input"
                  placeholder="Ej. 1042"
                  value={manualOrderId}
                  onChange={(e) => setManualOrderId(e.target.value)}
                  required
                />
                <span className="text-xs text-muted mt-1 d-block">
                  💡 Tip: Puedes enviar pedidos con un solo clic directamente desde la pestaña de <strong>Pedidos</strong>.
                </span>
              </div>
            )}
            
            <p className="text-sm text-muted mb-4">
              Al enviar este pedido a bodega, entrará en la <strong>Cola FIFO de Surtido</strong>. 
              Los productos se ordenarán automáticamente por ubicación física en anaqueles para agilizar la recolección.
            </p>

            <div className="form-group mb-4">
              <label className="d-flex align-items-center gap-2 cursor-pointer font-bold">
                <input
                  type="checkbox"
                  checked={blindMode}
                  onChange={(e) => setBlindMode(e.target.checked)}
                />
                <span>🔒 Activar Modo Surtido Ciego (Recomendado)</span>
              </label>
              <span className="text-xs text-muted mt-1 d-block">
                Oculta el nombre del cliente y el conteo de partidas a los almacenistas para evitar que omitan pedidos grandes por flojera.
              </span>
            </div>
            <div className="form-group mb-4">
              <label className="form-group__label" htmlFor="total_splits">
                Número de splits físicas para particionar:
              </label>
              <input
                id="total_splits"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                className="input"
                placeholder="1"
                value={splitsCountInput}
                onChange={(e) => {
                  const cleaned = e.target.value.replace(/[^0-9]/g, '');
                  setSplitsCountInput(cleaned);
                }}
                onBlur={handleSplitsBlur}
                required
              />
              <span className="text-xs text-muted mt-1 d-block">
                Para pedidos voluminosos, reparte los productos en 2 o más splits.
              </span>
            </div>
          </div>

          <div className="modal__footer">
            <button type="button" className="btn btn--secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--primary" disabled={loading}>
              {loading ? 'Enviando...' : 'Confirmar Envío'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
