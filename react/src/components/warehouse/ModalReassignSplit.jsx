import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faSearch, faUserCircle, faUserSlash, faSpinner,
  faChevronLeft, faChevronRight, faBoxesStacked, faInfoCircle, faUserCheck
} from '@fortawesome/free-solid-svg-icons';
import warehouseService from '../../services/warehouseService';
import adminService from '../../services/adminService';

export default function ModalReassignSplit({ isOpen, onClose, split, onSuccess }) {
  const [roleType, setRoleType] = useState('picker');
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize] = useState(5);
  const [operators, setOperators] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [loadingOperators, setLoadingOperators] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Inicializar o resetear cuando se abre el modal o cambia el split
  useEffect(() => {
    if (isOpen && split) {
      // Si el surtido ya terminó, por defecto sugerir 'checker'
      const surtidoTerminado = split.status === 'completed' || split.completed_at;
      const initialRole = surtidoTerminado ? 'checker' : 'picker';
      setRoleType(initialRole);

      const currentAssignedId = initialRole === 'picker' ? split.picker_id : split.checker_id;
      setSelectedUserId(currentAssignedId ?? null);

      setSearchTerm('');
      setDebouncedSearch('');
      setPage(0);
      setError(null);
    }
  }, [isOpen, split]);

  // Al cambiar de rol (picker <-> checker), actualizar la selección actual
  const handleRoleChange = (newRole) => {
    setRoleType(newRole);
    const currentAssignedId = newRole === 'picker' ? split.picker_id : split.checker_id;
    setSelectedUserId(currentAssignedId ?? null);
    setError(null);
  };

  // Debounce para el campo de búsqueda
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Cargar lista paginada de almacenistas desde el backend
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const fetchOperators = async () => {
      try {
        setLoadingOperators(true);
        const users = await warehouseService.getOperators({
          search: debouncedSearch || undefined,
          role_type: roleType,
          skip: page * pageSize,
          limit: pageSize + 1
        });

        if (!isMounted) return;

        const hasNext = users.length > pageSize;
        setHasMore(hasNext);
        setOperators(hasNext ? users.slice(0, pageSize) : users);
      } catch (err) {
        if (isMounted) {
          console.error('Error al cargar almacenistas:', err);
          setError('No se pudo cargar la lista de almacenistas');
        }
      } finally {
        if (isMounted) setLoadingOperators(false);
      }
    };

    fetchOperators();
    return () => { isMounted = false; };
  }, [isOpen, debouncedSearch, roleType, page, pageSize]);

  if (!isOpen || !split) return null;

  const currentAssignedId = roleType === 'picker' ? split.picker_id : split.checker_id;

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);

      // Si selectedUserId es 'unassign' o null, enviamos null para desasignar
      const targetId = (selectedUserId === 'unassign' || selectedUserId === null || selectedUserId === '')
        ? null
        : Number(selectedUserId);

      await warehouseService.reassignSplit(split.split_id, roleType, targetId);

      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error('Error al reasignar split:', err);
      setError(err.detail || err.message || 'No se pudo reasignar el split');
    } finally {
      setSubmitting(false);
    }
  };

  // Buscar objeto del operador seleccionado (para mostrar resumen en el pie)
  const selectedOperatorObj = operators.find(op => String(op.user_id) === String(selectedUserId));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--md reassign-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="reassign-modal-header">
            <span className="reassign-modal-header-icon">🔄</span>
            <div>
              <h3 className="reassign-modal-title">
                Reasignar Split #{split.split_number ?? split.split_index}
              </h3>
              <span className="reassign-modal-subtitle">
                Pedido #{split.order_id} • Split {split.split_number ?? split.split_index} de {split.total_splits || split.total_splits_in_order || 1}
              </span>
            </div>
          </div>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Cerrar">
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="reassign-modal-form">
          <div className="modal__body reassign-modal-body">
            {error && (
              <div className="alert alert--danger reassign-modal-alert">
                ⚠️ {error}
              </div>
            )}

            {/* Regla de Supervisión */}
            <div className="alert alert--info reassign-modal-supervision">
              <FontAwesomeIcon icon={faInfoCircle} className="reassign-modal-supervision-icon" />
              <div>
                <strong>Regla de Supervisión:</strong> La reasignación solo es permitida si el proceso seleccionado (
                {roleType === 'picker' ? 'Surtido' : 'Revisión / Checking'}) aún <strong>NO</strong> ha concluido. Si ya finalizó, el sistema bloqueará la transferencia por integridad de auditoría.
              </div>
            </div>

            {/* Selector de Rol a Reasignar */}
            <div>
              <label className="reassign-role-label">
                Selecciona el rol que deseas reasignar:
              </label>
              <div className="reassign-role-group">
                <div
                  className={`reassign-role-group__card ${roleType === 'picker' ? 'reassign-role-group__card--active' : ''}`}
                  onClick={() => handleRoleChange('picker')}
                >
                  <div className="d-flex align-items-center justify-content-between">
                    <label className="d-flex align-items-center gap-2 cursor-pointer mb-0">
                      <input
                        type="radio"
                        name="modalRoleType"
                        value="picker"
                        checked={roleType === 'picker'}
                        onChange={() => handleRoleChange('picker')}
                      />
                      <strong>Surtidor (Picker)</strong>
                    </label>
                    <FontAwesomeIcon icon={faBoxesStacked} />
                  </div>
                  <div className="reassign-role-meta">
                    Actual: <span className="reassign-role-meta-name">{split.picker_name || 'Sin asignar'}</span>
                  </div>
                </div>

                <div
                  className={`reassign-role-group__card ${roleType === 'checker' ? 'reassign-role-group__card--active' : ''}`}
                  onClick={() => handleRoleChange('checker')}
                >
                  <div className="d-flex align-items-center justify-content-between">
                    <label className="d-flex align-items-center gap-2 cursor-pointer mb-0">
                      <input
                        type="radio"
                        name="modalRoleType"
                        value="checker"
                        checked={roleType === 'checker'}
                        onChange={() => handleRoleChange('checker')}
                      />
                      <strong>Revisor (Checker)</strong>
                    </label>
                    <FontAwesomeIcon icon={faUserCheck} />
                  </div>
                  <div className="reassign-role-meta">
                    Actual: <span className="reassign-role-meta-name">{split.checker_name || 'Sin asignar'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Buscador de Almacenistas */}
            <div>
              <div className="reassign-operators-header">
                <label className="reassign-operators-label">
                  Seleccionar Almacenista Destino:
                </label>
                <span className="reassign-operators-caption">
                  Equipo de Bodega Activo
                </span>
              </div>

              <div className="reassign-search-box">
                <FontAwesomeIcon icon={faSearch} className="reassign-search-icon" />
                <input
                  type="text"
                  className="input reassign-search-input"
                  placeholder="Buscar almacenista por nombre, @usuario o ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={() => setSearchTerm('')}
                    className="reassign-search-clear"
                    title="Limpiar búsqueda"
                  >
                    &times;
                  </button>
                )}
              </div>

              {/* Lista de Almacenistas */}
              <div className="operator-selection-list">
                {/* Opción para Desasignar */}
                <div
                  className={`operator-selection-list__item operator-selection-list__item--unassign ${selectedUserId === 'unassign' || selectedUserId === null
                      ? 'operator-selection-list__item--selected'
                      : ''
                    }`}
                  onClick={() => setSelectedUserId('unassign')}
                >
                  <input
                    type="radio"
                    name="operatorSelection"
                    checked={selectedUserId === 'unassign' || selectedUserId === null}
                    onChange={() => setSelectedUserId('unassign')}
                    className="cursor-pointer"
                  />
                  <div className="operator-avatar-icon operator-avatar-icon--unassign">
                    <FontAwesomeIcon icon={faUserSlash} />
                  </div>
                  <div className="operator-card-content">
                    <div className="operator-unassign-title">
                      🚫 Dejar sin asignar (Quitar operador)
                    </div>
                    <div className="operator-unassign-desc">
                      El split quedará en cola general disponible para reclamo
                    </div>
                  </div>
                </div>

                {/* Loading state */}
                {loadingOperators ? (
                  <div className="text-center py-4 text-muted reassign-modal-alert">
                    <FontAwesomeIcon icon={faSpinner} spin className="me-2" /> Cargando equipo de bodega...
                  </div>
                ) : operators.length === 0 ? (
                  <div className="text-center py-4 text-muted reassign-modal-alert">
                    No se encontraron almacenistas {searchTerm ? `con "${searchTerm}"` : 'activos'}.
                  </div>
                ) : (
                  operators.map((op) => {
                    const isSelected = String(selectedUserId) === String(op.user_id);
                    const isCurrentlyAssigned = currentAssignedId === op.user_id;

                    return (
                      <div
                        key={op.user_id}
                        className={`operator-selection-list__item ${isSelected ? 'operator-selection-list__item--selected' : ''
                          }`}
                        onClick={() => setSelectedUserId(op.user_id)}
                      >
                        <input
                          type="radio"
                          name="operatorSelection"
                          checked={isSelected}
                          onChange={() => setSelectedUserId(op.user_id)}
                          className="cursor-pointer"
                        />
                        <div className={`operator-avatar-icon ${isSelected ? 'operator-avatar-icon--selected' : 'operator-avatar-icon--default'}`}>
                          <FontAwesomeIcon icon={faUserCircle} />
                        </div>
                        <div className="operator-card-content">
                          <div className="d-flex align-items-center gap-2 flex-wrap">
                            <span className="operator-name">
                              {op.full_name}
                            </span>
                            <span className="operator-id-badge">
                              ID #{op.user_id}
                            </span>
                            {isCurrentlyAssigned && (
                              <span className="badge badge--info operator-current-badge">
                                ✓ Asignado Actual
                              </span>
                            )}
                          </div>
                          <div className="operator-meta-sub">
                            @{op.username} {op.email ? `• ${op.email}` : ''}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Controles de Paginación */}
              <div className="reassign-pagination">
                <span className="reassign-pagination-text">
                  Página {page + 1} {hasMore ? '(más operadores...)' : ''}
                </span>
                <div className="d-flex gap-2">
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm reassign-pagination-btn"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0 || loadingOperators}
                  >
                    <FontAwesomeIcon icon={faChevronLeft} /> Anterior
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm reassign-pagination-btn"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={!hasMore || loadingOperators}
                  >
                    Siguiente <FontAwesomeIcon icon={faChevronRight} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="reassign-modal-footer">
            <div className="reassign-footer-action">
              Acción:{' '}
              {selectedUserId === 'unassign' || selectedUserId === null ? (
                <strong className="reassign-footer-action--unassign">
                  Desasignar {roleType === 'picker' ? 'surtidor' : 'revisor'}
                </strong>
              ) : selectedOperatorObj ? (
                <strong className="reassign-footer-action--assign">
                  Asignar a {selectedOperatorObj.full_name} (#{selectedOperatorObj.user_id})
                </strong>
              ) : (
                <strong>Asignar ID #{selectedUserId}</strong>
              )}
            </div>

            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={onClose}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn btn--primary reassign-footer-submit"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <FontAwesomeIcon icon={faSpinner} spin className="me-2" /> Guardando...
                  </>
                ) : (
                  'Guardar Reasignación'
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
