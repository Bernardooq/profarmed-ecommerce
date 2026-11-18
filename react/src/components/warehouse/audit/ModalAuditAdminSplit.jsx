import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCog } from '@fortawesome/free-solid-svg-icons';
import warehouseService from '../../../services/warehouseService';

export default function ModalAuditAdminSplit({ split, orderId, onClose, onSaved }) {
  const [adminStatus, setAdminStatus] = useState('pending');
  const [adminSealFolio, setAdminSealFolio] = useState('');
  const [adminClearSeal, setAdminClearSeal] = useState(false);
  const [adminSaving, setAdminSaving] = useState(false);

  useEffect(() => {
    if (split) {
      setAdminStatus(split.status || 'pending');
      setAdminSealFolio(split.security_seal_folio || '');
      setAdminClearSeal(false);
    }
  }, [split]);

  if (!split) return null;

  const handleGenerateSealFolio = () => {
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    setAdminSealFolio(`SL-${orderId}-${split.split_number ?? 1}-${randomSuffix}`);
    setAdminClearSeal(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!window.confirm(`¿Confirmas aplicar los cambios administrativos a la Split #${split.split_number}?\n\nEsta acción recalculará los estatus del pedido y quedará asentada en la auditoría.`)) {
      return;
    }

    try {
      setAdminSaving(true);
      await warehouseService.adminOverrideSplit(split.split_id, {
        status: adminStatus,
        security_seal_folio: adminClearSeal ? null : (adminSealFolio.trim() || null),
        clear_seal: adminClearSeal
      });
      onSaved?.(`✓ Modificación administrativa aplicada exitosamente a la Split #${split.split_number}.`);
      onClose();
    } catch (err) {
      alert(err.detail || err.message || 'Error al aplicar cambios de administrador');
    } finally {
      setAdminSaving(false);
    }
  };

  return (
    <div className="modal-overlay modal-overlay--audit-admin-split" onClick={onClose}>
      <div className="modal modal--sm" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3 className="d-flex align-items-center gap-2 m-0 text-base text-warning">
            <FontAwesomeIcon icon={faCog} /> Gestión Admin — Split #{split.split_number} {split.split_code ? `[Lote: ${split.split_code}]` : ''}
          </h3>
          <button type="button" className="modal__close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSave} className="warehouse-terminal__modal-form">
          <div className="modal__body">
            <div className="alert alert--danger p-2 mb-3 text-xs leading-normal">
              <strong>⚠️ Acción Pericial Exclusiva de Administrador:</strong>
              <p className="m-0 mt-1">
                Puedes forzar el cambio de estatus de la split (incluyendo la reapertura de splits sellados) y corregir o limpiar el cincho de seguridad inviolable.
              </p>
            </div>

            <div className="form-group mb-3">
              <label className="form-group__label">Modificar Estatus de Split:</label>
              <select
                className="input"
                value={adminStatus}
                onChange={(e) => setAdminStatus(e.target.value)}
              >
                <option value="pending">pending — Pendiente en Cola FIFO</option>
                <option value="in_progress">in_progress — En Piso de Surtido (Reapertura)</option>
                <option value="ready_for_check">ready_for_check — Enviar a Segundo Filtro (Revisión)</option>
                <option value="checking">checking — En Mesa de Control / Revisión Activa</option>
                <option value="completed">completed — Forzar Completado / Sellado</option>
              </select>
            </div>

            <div className="form-group mb-3">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <label className="form-group__label mb-0">Folio de Sello Inviolable (Cincho):</label>
                <button
                  type="button"
                  className="btn btn--ghost btn--xs text-primary font-bold"
                  onClick={handleGenerateSealFolio}
                >
                  ⚡ Generar SL-
                </button>
              </div>
              <input
                type="text"
                className="input font-mono"
                value={adminSealFolio}
                onChange={(e) => {
                  setAdminSealFolio(e.target.value);
                  if (e.target.value) setAdminClearSeal(false);
                }}
                placeholder="Ej. SL-1-1-8492 o cincho físico..."
                disabled={adminClearSeal}
              />
              <div className="mt-2">
                <label className="d-flex align-items-center gap-2 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={adminClearSeal}
                    onChange={(e) => {
                      setAdminClearSeal(e.target.checked);
                      if (e.target.checked) setAdminSealFolio('');
                    }}
                  />
                  <span>Quitar / Limpiar sello de seguridad (Dejar sin cincho)</span>
                </label>
              </div>
            </div>
          </div>

          <div className="modal__footer warehouse-terminal__modal-footer-responsive">
            <button type="button" className="btn btn--secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--warning font-bold" disabled={adminSaving}>
              {adminSaving ? 'Aplicando...' : 'Confirmar Cambios Admin'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
