import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faQrcode, faBoxesStacked, faWrench, faTrash,
  faPlus, faRotate, faLinkSlash, faCopy, faCheck, faBan
} from '@fortawesome/free-solid-svg-icons';
import LoadingSpinner from '../../common/LoadingSpinner';

/**
 * ContainersTable
 * Tabla visual del parque de canastas físicas QR con sus estados, vinculación y acciones.
 */
export default function ContainersTable({
  containers = [],
  loading = false,
  canManageContainers = false,
  canRelease = false,
  copiedId = null,
  onCopyText,
  onSelectContainerForQr,
  onReleaseContainer,
  onUpdateStatus,
  onDeleteContainer,
  onOpenCreateModal
}) {
  if (loading) {
    return (
      <div className="data-table">
        <div className="p-8">
          <LoadingSpinner message="Cargando parque de canastas QR..." />
        </div>
      </div>
    );
  }

  if (containers.length === 0) {
    return (
      <div className="data-table">
        <div className="data-table__empty">
          <FontAwesomeIcon icon={faBoxesStacked} size="2x" className="mb-2 text-muted d-block mx-auto" />
          <p>No se encontraron canastas con los filtros seleccionados.</p>
          {canManageContainers && (
            <button
              type="button"
              className="btn btn--primary btn--sm mt-3"
              onClick={onOpenCreateModal}
            >
              <FontAwesomeIcon icon={faPlus} className="me-1" />
              Dar de alta la primera canasta
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="data-table">
      <table>
        <thead>
          <tr>
            <th>Código QR / Etiqueta</th>
            <th>Estado Físico</th>
            <th>Split Asignado</th>
            <th>Fecha de Alta</th>
            <th className="text-end">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {containers.map((container) => {
            const isAvailable = container.status === 'available';
            const isInUse = container.status === 'in_use';
            const isMaintenance = container.status === 'maintenance';
            const isRetired = container.status === 'retired';
            const isDamaged = container.status === 'damaged' || container.status === 'unavailable';

            return (
              <tr key={container.container_id}>
                <td>
                  <div className="d-flex align-items-center gap-2">
                    <button
                      type="button"
                      className="badge badge--dark font-mono text-sm px-2 py-1 btn btn--ghost d-inline-flex align-items-center"
                      onClick={() => onSelectContainerForQr(container)}
                      title="Clic para ver código QR, descargar imagen o imprimir etiqueta"
                      style={{ cursor: 'pointer', border: '1px solid var(--border-color, #334155)' }}
                    >
                      <FontAwesomeIcon icon={faQrcode} className="me-2 text-primary" />
                      <span>{container.qr_code}</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn--ghost btn--xs"
                      onClick={() => onCopyText(container.qr_code, container.container_id)}
                      title="Copiar folio como texto al portapapeles"
                    >
                      <FontAwesomeIcon icon={copiedId === container.container_id ? faCheck : faCopy} size="xs" />
                    </button>
                  </div>
                </td>
                <td>
                  {isAvailable && (
                    <span className="badge badge--success">🟢 Disponible</span>
                  )}
                  {isInUse && (
                    <span className="badge badge--primary">🔵 En Uso</span>
                  )}
                  {isMaintenance && (
                    <span className="badge badge--warning">🟡 Mantenimiento</span>
                  )}
                  {isRetired && (
                    <span className="badge badge--danger">🔴 Retirada (Baja)</span>
                  )}
                  {isDamaged && (
                    <span className="badge badge--secondary">⚪ No Disponible</span>
                  )}
                </td>
                <td>
                  {isInUse && container.current_split_id ? (
                    <span className="font-mono text-xs text-muted" title={container.current_split_id}>
                      📦 Split: {String(container.current_split_id).substring(0, 8)}...
                    </span>
                  ) : (
                    <span className="text-muted text-xs">— Sin asignar —</span>
                  )}
                </td>
                <td>
                  <small className="text-muted">
                    {container.created_at ? new Date(container.created_at).toLocaleDateString() : 'N/A'}
                  </small>
                </td>
                <td className="text-end">
                  <div className="d-flex justify-content-end align-items-center gap-1 flex-wrap">
                    {/* Botón Ver / Copiar / Imprimir QR */}
                    <button
                      type="button"
                      className="btn btn--ghost btn--xs"
                      onClick={() => onSelectContainerForQr(container)}
                      title="Generar imagen QR / Copiar / Imprimir Etiqueta"
                    >
                      <FontAwesomeIcon icon={faQrcode} className="text-primary me-1" />
                      QR
                    </button>

                    {/* Botón Liberar */}
                    {isInUse && canRelease && (
                      <button
                        type="button"
                        className="btn btn--secondary btn--xs"
                        onClick={() => onReleaseContainer(container)}
                        title="Liberar canasta desacoplándola del split"
                      >
                        <FontAwesomeIcon icon={faLinkSlash} className="me-1" />
                        Liberar
                      </button>
                    )}

                    {/* Gestión de Estado Físico */}
                    {!isInUse && canManageContainers && (
                      <div className="d-flex align-items-center gap-1">
                        {isAvailable && (
                          <>
                            <button
                              type="button"
                              className="btn btn--ghost btn--xs"
                              onClick={() => onUpdateStatus(container, 'maintenance')}
                              title="Enviar a mantenimiento o revisión física"
                            >
                              <FontAwesomeIcon icon={faWrench} className="me-1 text-warning" />
                              Mantenimiento
                            </button>
                            <button
                              type="button"
                              className="btn btn--ghost btn--xs text-danger"
                              onClick={() => onUpdateStatus(container, 'retired')}
                              title="Dar de baja / retirar del parque (preserva auditoría)"
                            >
                              <FontAwesomeIcon icon={faBan} className="me-1" />
                              Retirar
                            </button>
                          </>
                        )}

                        {isMaintenance && (
                          <>
                            <button
                              type="button"
                              className="btn btn--success btn--xs"
                              onClick={() => onUpdateStatus(container, 'available')}
                              title="Habilitar canasta (marcar disponible para surtido)"
                            >
                              <FontAwesomeIcon icon={faCheck} className="me-1" />
                              Habilitar
                            </button>
                            <button
                              type="button"
                              className="btn btn--ghost btn--xs text-danger"
                              onClick={() => onUpdateStatus(container, 'retired')}
                              title="Dar de baja / retirar del parque"
                            >
                              <FontAwesomeIcon icon={faBan} className="me-1" />
                              Retirar
                            </button>
                          </>
                        )}

                        {isRetired && (
                          <>
                            <button
                              type="button"
                              className="btn btn--primary btn--xs"
                              onClick={() => onUpdateStatus(container, 'available')}
                              title="Reactivar canasta (marcar disponible para surtido)"
                            >
                              <FontAwesomeIcon icon={faRotate} className="me-1" />
                              Reactivar
                            </button>
                            <button
                              type="button"
                              className="btn btn--ghost btn--xs"
                              onClick={() => onUpdateStatus(container, 'maintenance')}
                              title="Pasar a mantenimiento"
                            >
                              <FontAwesomeIcon icon={faWrench} className="me-1 text-warning" />
                              Mantenimiento
                            </button>
                          </>
                        )}
                      </div>
                    )}

                    {/* Botón Eliminar */}
                    {!isInUse && canManageContainers && (
                      <button
                        type="button"
                        className="btn btn--ghost btn--xs text-danger"
                        onClick={() => onDeleteContainer(container)}
                        title="Eliminar canasta del catálogo (solo si nunca fue usada)"
                      >
                        <FontAwesomeIcon icon={faTrash} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
