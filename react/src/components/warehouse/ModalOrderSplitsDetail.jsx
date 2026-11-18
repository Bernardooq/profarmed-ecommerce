import React, { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faRotate, faBolt, faLock } from '@fortawesome/free-solid-svg-icons';
import PaginationButtons from '../common/PaginationButtons';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function ModalOrderSplitsDetail({
  isOpen,
  onClose,
  order,
  userRole,
  currentUserId,
  onReassignSplit,
  onTakeSplit,
  stageFilter = null // 'picker' | 'checker' | null
}) {
  const { can, isAdmin, isStaff } = usePermissions();
  const canSupervisor = isAdmin || can(PERMISSIONS.WAREHOUSE_SUPERVISOR) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canOperatePicker = isAdmin || can(PERMISSIONS.WAREHOUSE_OPERATOR) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const canOperateChecker = isAdmin || can(PERMISSIONS.WAREHOUSE_CHECKER) || can(PERMISSIONS.WAREHOUSE_MANAGE);
  const [page, setPage] = useState(0);
  const pageSize = 5;

  if (!isOpen || !order) return null;

  const rawSplits = order.splits || [];

  // Priorizar splits no finalizadas: pending / in_progress / ready_for_check primero, completed al final
  const sortedSplits = [...rawSplits].sort((a, b) => {
    const isCompletedA = a.status === 'completed';
    const isCompletedB = b.status === 'completed';
    if (isCompletedA !== isCompletedB) {
      return isCompletedA ? 1 : -1;
    }
    return (a.split_number ?? a.split_index ?? 0) - (b.split_number ?? b.split_index ?? 0);
  });

  const totalPages = Math.max(1, Math.ceil(sortedSplits.length / pageSize));
  const currentSplits = sortedSplits.slice(page * pageSize, (page + 1) * pageSize);

  const getStatusBadge = (st) => {
    switch (st) {
      case 'pending':
        return <span className="warehouse-badge warehouse-badge--pending">Pendiente</span>;
      case 'picking':
      case 'in_progress_partial':
      case 'in_progress':
        return <span className="warehouse-badge warehouse-badge--in_progress_partial">En Surtido</span>;
      case 'ready_for_check':
        return <span className="warehouse-badge warehouse-badge--warning">2do Filtro (Por Revisar)</span>;
      case 'checking':
        return <span className="warehouse-badge warehouse-badge--info">En 2do Filtro</span>;
      case 'in_progress_full':
        return <span className="warehouse-badge warehouse-badge--in_progress_full">Surtido Completo</span>;
      case 'completed':
        return <span className="warehouse-badge warehouse-badge--completed">Sellada</span>;
      default:
        return <span className="warehouse-badge">{st}</span>;
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--lg" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="d-flex align-items-center gap-2">
            <span className="text-xl">🧺</span>
            <h3 className="m-0">Splits de Surtido — Pedido #{order.order_id}</h3>
          </div>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar">
            &times;
          </button>
        </div>

        <div className="modal__body">
          <div className="order-details mb-4">
            <div className="order-details__section p-0 pb-3 mb-0">
              <div className="order-details__grid">
                <div className="order-details__item">
                  <strong>Cliente:</strong>
                  <span>{order.customer_name || 'N/A'}</span>
                </div>
                <div className="order-details__item">
                  <strong>Total de Splits:</strong>
                  <span className="font-bold">{rawSplits.length} {rawSplits.length === 1 ? 'split' : 'splits'}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Lote / Split</th>
                  <th>Estatus</th>
                  <th className="text-center">Partidas</th>
                  <th>Operador / Revisor</th>
                  <th>Sello de Seguridad</th>
                  <th className="text-end">Acción</th>
                </tr>
              </thead>
              <tbody>
                {currentSplits.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center text-muted p-4">
                      No hay splits registradas para este pedido.
                    </td>
                  </tr>
                ) : (
                  currentSplits.map((split) => {
                    const isMyPicker = split.picker_id === currentUserId;
                    const isMyChecker = split.checker_id === currentUserId;
                    const canReassign = canSupervisor && split.status !== 'completed';
                    
                    // Permitir tomar como picker si el split no está terminada y no tiene picker (y no estamos filtrando solo checker)
                    const canTakePicker = (stageFilter !== 'checker')
                      && canOperatePicker 
                      && (split.status === 'pending' || split.status === 'picking' || split.status === 'in_progress') 
                      && !split.picker_id;
                    
                    // Permitir tomar como checker si está lista para segundo filtro y no tiene checker (y no estamos filtrando solo picker)
                    const canTakeChecker = (stageFilter !== 'picker')
                      && canOperateChecker 
                      && (split.status === 'ready_for_check' || split.status === 'checking')
                      && !split.checker_id;

                    return (
                      <tr key={split.split_id}>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            <span>{split.uses_containers ? '🧺' : '📦'}</span>
                            <strong>Split #{split.split_number ?? split.split_index}</strong>
                          </div>
                          {split.split_code && (
                            <div className="text-xs text-primary font-mono font-bold mt-1">
                              🏷️ Lote: {split.split_code}
                            </div>
                          )}
                          <div className="text-xs text-muted mt-0.5">
                            {split.uses_containers ? (
                              <span className="badge badge--primary text-xs py-0 px-1">🧺 Canastas</span>
                            ) : (
                              <span className="badge badge--secondary text-xs py-0 px-1">📦 Directo</span>
                            )}
                          </div>
                        </td>
                        <td>{getStatusBadge(split.status)}</td>
                        <td className="text-center font-bold">
                          {split.items_count != null ? split.items_count : '—'}
                        </td>
                        <td className="text-xs">
                          <div>
                            <strong>Picker:</strong> {split.picker_name || 'Sin asignar'}
                          </div>
                          <div>
                            <strong>Checker:</strong> {split.checker_name || 'Sin asignar'}
                          </div>
                        </td>
                        <td>
                          {split.security_seal_folio ? (
                            <span className="badge badge--success font-mono font-bold text-xs">
                              <FontAwesomeIcon icon={faLock} /> {split.security_seal_folio}
                            </span>
                          ) : (
                            <span className="text-muted text-xs">Sin sello</span>
                          )}
                        </td>
                        <td className="text-end">
                          <div className="d-flex justify-content-end gap-2">
                            {canReassign && (
                              <button
                                type="button"
                                className="btn btn--secondary btn--sm"
                                onClick={() => {
                                  onClose();
                                  if (onReassignSplit) onReassignSplit(split);
                                }}
                                title="Reasignar picker o checker"
                              >
                                <FontAwesomeIcon icon={faRotate} /> Reasignar
                              </button>
                            )}
                            {canTakePicker && (
                              <button
                                type="button"
                                className="btn btn--primary btn--sm"
                                onClick={() => {
                                  onClose();
                                  if (onTakeSplit) onTakeSplit(split.split_id, 'picker', split.split_number ?? split.split_index ?? 1, order.order_id);
                                }}
                                title="Tomar este split para surtir"
                              >
                                <FontAwesomeIcon icon={faBolt} /> Surtir
                              </button>
                            )}
                            {canTakeChecker && (
                              <button
                                type="button"
                                className="btn btn--secondary btn--sm"
                                onClick={() => {
                                  onClose();
                                  if (onTakeSplit) onTakeSplit(split.split_id, 'checker', split.split_number ?? split.split_index ?? 1, order.order_id);
                                }}
                                title="Tomar este split para segundo filtro"
                              >
                                🛡️ 2do Filtro
                              </button>
                            )}
                            {isMyPicker && (split.status === 'picking' || split.status === 'in_progress' || split.status === 'pending') && (
                              <button
                                type="button"
                                className="btn btn--primary btn--sm"
                                onClick={() => {
                                  onClose();
                                  if (onTakeSplit) onTakeSplit(split.split_id, 'picker', split.split_number ?? split.split_index ?? 1, order.order_id, true);
                                }}
                                title="Continuar surtido en terminal"
                              >
                                🧺 Surtir
                              </button>
                            )}
                            {isMyChecker && (split.status === 'checking' || split.status === 'ready_for_check') && (
                              <button
                                type="button"
                                className="btn btn--secondary btn--sm"
                                onClick={() => {
                                  onClose();
                                  if (onTakeSplit) onTakeSplit(split.split_id, 'checker', split.split_number ?? split.split_index ?? 1, order.order_id, true);
                                }}
                                title="Continuar segundo filtro en terminal"
                              >
                                🛡️ Revisar
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-3">
              <PaginationButtons
                currentPage={page}
                lookaheadPages={Math.max(0, totalPages - 1 - page)}
                onPageChange={setPage}
              />
            </div>
          )}
        </div>

        <div className="modal__footer">
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
