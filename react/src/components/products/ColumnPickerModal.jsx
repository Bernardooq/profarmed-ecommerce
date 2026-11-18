import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSlidersH, faTimes, faUndo, faCheck } from '@fortawesome/free-solid-svg-icons';

export default function ColumnPickerModal({ 
  isOpen, 
  onClose, 
  allColumns = [], 
  visibleColumns = [], 
  toggleColumn, 
  resetColumns 
}) {
  if (!isOpen) return null;

  const safeAllColumns = Array.isArray(allColumns) ? allColumns : [];
  const safeVisibleColumns = Array.isArray(visibleColumns) ? visibleColumns : [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--sm column-picker-modal" onClick={e => e.stopPropagation()}>
        <div className="modal__header">
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center' }}>
            <FontAwesomeIcon icon={faSlidersH} style={{ marginRight: '10px', color: 'var(--color-primary)' }} />
            Configurar Campos Visibles
          </h3>
          <button className="modal__close" onClick={onClose} title="Cerrar">
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        <div className="modal__body" style={{ padding: '20px' }}>
          <p className="column-picker-hint">
            Selecciona qué columnas deseas mostrar u ocultar en el Punto de Venta. Las preferencias se guardan de inmediato en tu navegador.
          </p>

          <div className="columns-grid">
            {safeAllColumns.map(col => {
              const isChecked = safeVisibleColumns.includes(col.id);
              const isDisabled = col.required;

              return (
                <div 
                  key={col.id} 
                  className={`column-option-row ${isDisabled ? 'disabled' : ''} ${isChecked ? 'active' : ''}`}
                  onClick={() => !isDisabled && toggleColumn && toggleColumn(col.id)}
                >
                  <div className={`custom-checkbox-box ${isChecked ? 'checked' : ''}`}>
                    {isChecked && <FontAwesomeIcon icon={faCheck} size="xs" />}
                  </div>

                  <div className="column-option-info">
                    <span className="column-option-title">
                      {col.label}
                      {col.required && <span className="badge-required">Requerido</span>}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="modal__footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px' }}>
          <button className="btn btn--secondary btn--sm" onClick={resetColumns}>
            <FontAwesomeIcon icon={faUndo} style={{ marginRight: '6px' }} />
            Restablecer por Defecto
          </button>
          <button className="btn btn--primary btn--sm" onClick={onClose}>
            Listo
          </button>
        </div>
      </div>
    </div>
  );
}
