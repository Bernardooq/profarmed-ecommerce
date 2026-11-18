import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faUserTie, faUsers, faUserCircle, faPlus, faTrashAlt, faTimes, faSearch, faFilter
} from '@fortawesome/free-solid-svg-icons';
import salesGroupService from '../../../services/salesGroupService';
import { adminService } from '../../../services/adminService';
import ErrorMessage from '../../common/ErrorMessage';
import PaginationButtons from '../../common/PaginationButtons';
import LoadingSpinner from '../../common/LoadingSpinner';
import { usePaginationLimit } from '../../../context/PaginationLimitContext';
import { usePermissions } from '../../../hooks/usePermissions';
import { PERMISSIONS } from '../../../config/permissions';

export default function GroupDetailsModal({ group, onClose, onUpdate }) {
  const { can } = usePermissions();
  const canManageGroups = can(PERMISSIONS.GROUPS_MANAGE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Tabs: 'members' (unified internal team) or 'customers' (commercial portfolio)
  const [activeTab, setActiveTab] = useState('members');

  // Dynamic roles state for filtering members
  const [availableRoles, setAvailableRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState('');

  const [availableUsers, setAvailableUsers] = useState([]);
  const [loadingAvailable, setLoadingAvailable] = useState(false);
  const [availablePage, setAvailablePage] = useState(0);
  const [availableHasMore, setAvailableHasMore] = useState(true);

  const [inGroupUsers, setInGroupUsers] = useState([]);
  const [loadingInGroup, setLoadingInGroup] = useState(false);
  const [inGroupPage, setInGroupPage] = useState(0);
  const [inGroupHasMore, setInGroupHasMore] = useState(true);

  const [searchInGroup, setSearchInGroup] = useState('');
  const [searchAvailable, setSearchAvailable] = useState('');
  const [searchInGroupTimeout, setSearchInGroupTimeout] = useState(null);
  const [searchAvailableTimeout, setSearchAvailableTimeout] = useState(null);

  const { limit: ITEMS_PER_PAGE } = usePaginationLimit();

  // Load available roles dynamically on component mount
  useEffect(() => {
    let isMounted = true;
    adminService.getRoles()
      .then((roles) => {
        if (isMounted && Array.isArray(roles)) {
          setAvailableRoles(roles.filter(r => r.slug !== 'admin'));
        }
      })
      .catch((err) => {
        console.warn('No se pudieron cargar roles para filtrado:', err);
      });
    return () => { isMounted = false; };
  }, []);

  useEffect(() => {
    if (group) {
      setLoading(false);
      setAvailablePage(0);
      setInGroupPage(0);
    }
  }, [group, activeTab, selectedRole]);

  useEffect(() => {
    if (group && canManageGroups) loadAvailableUsers(availablePage, searchAvailable);
  }, [activeTab, selectedRole, availablePage, canManageGroups]);

  useEffect(() => {
    if (group) loadInGroupUsers(inGroupPage, searchInGroup);
  }, [activeTab, selectedRole, inGroupPage]);

  useEffect(() => {
    if (!canManageGroups) return;
    if (searchAvailableTimeout) clearTimeout(searchAvailableTimeout);
    const timeout = setTimeout(() => {
      setAvailablePage(0);
      if (group && canManageGroups) loadAvailableUsers(0, searchAvailable);
    }, 400);
    setSearchAvailableTimeout(timeout);
    return () => { if (timeout) clearTimeout(timeout); };
  }, [searchAvailable, canManageGroups]);

  useEffect(() => {
    if (searchInGroupTimeout) clearTimeout(searchInGroupTimeout);
    const timeout = setTimeout(() => {
      setInGroupPage(0);
      if (group) loadInGroupUsers(0, searchInGroup);
    }, 400);
    setSearchInGroupTimeout(timeout);
    return () => { if (timeout) clearTimeout(timeout); };
  }, [searchInGroup]);

  const loadAvailableUsers = async (page, search = '') => {
    if (!canManageGroups) return;
    try {
      setLoadingAvailable(true);
      const params = { skip: page * ITEMS_PER_PAGE, limit: ITEMS_PER_PAGE };
      if (search?.trim()) params.search = search.trim();

      let available = [];
      if (activeTab === 'customers') {
        available = await salesGroupService.getAvailableCustomers(group.sales_group_id, params);
      } else {
        if (selectedRole) params.role = selectedRole;
        available = await salesGroupService.getAvailableMembers(group.sales_group_id, params);
      }
      setAvailableUsers(available);
      setAvailableHasMore(available.length === ITEMS_PER_PAGE);
    } catch (err) {
      console.error(err);
      setError('Error al cargar usuarios disponibles');
    } finally {
      setLoadingAvailable(false);
    }
  };

  const loadInGroupUsers = async (page, search = '') => {
    try {
      setLoadingInGroup(true);
      const params = { skip: page * ITEMS_PER_PAGE, limit: ITEMS_PER_PAGE };
      if (search?.trim()) params.search = search.trim();

      let inGroup = [];
      if (activeTab === 'customers') {
        inGroup = await salesGroupService.getGroupCustomers(group.sales_group_id, params);
      } else {
        if (selectedRole) params.role = selectedRole;
        inGroup = await salesGroupService.getGroupMembers(group.sales_group_id, params);
      }
      setInGroupUsers(inGroup);
      setInGroupHasMore(inGroup.length === ITEMS_PER_PAGE);
    } catch (err) {
      console.error(err);
      setError('Error al cargar miembros del grupo');
    } finally {
      setLoadingInGroup(false);
    }
  };

  const handleAddMember = async (id) => {
    try {
      setError(null);
      if (activeTab === 'customers') {
        await salesGroupService.assignCustomerToGroup(group.sales_group_id, id);
      } else {
        await salesGroupService.assignMemberToGroup(group.sales_group_id, id);
      }
      onUpdate?.();
      loadAvailableUsers(availablePage, searchAvailable);
      loadInGroupUsers(inGroupPage, searchInGroup);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al añadir elemento al grupo.');
    }
  };

  const handleRemoveMember = async (id) => {
    const isCustomer = activeTab === 'customers';
    const confirmMsg = isCustomer
      ? '¿Estás seguro de desasignar este cliente del grupo de ventas?'
      : '¿Estás seguro de remover este miembro del grupo de ventas?';
    if (!window.confirm(confirmMsg)) return;

    try {
      setError(null);
      if (isCustomer) {
        await salesGroupService.removeCustomerFromGroup(group.sales_group_id, id);
      } else {
        await salesGroupService.removeMemberFromGroup(group.sales_group_id, id);
      }
      onUpdate?.();
      loadAvailableUsers(availablePage, searchAvailable);
      loadInGroupUsers(inGroupPage, searchInGroup);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al remover elemento del grupo.');
    }
  };

  if (!group) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--lg" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="d-flex align-center gap-2">
            <FontAwesomeIcon icon={faUsers} className="text-primary" />
            <div>
              <h2>{group.group_name}</h2>
              {group.description && <p className="text-muted">{group.description}</p>}
            </div>
          </div>
          <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>
        <div className="modal__body">
          {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}
          {loading ? <LoadingSpinner message="Cargando..." /> : (
            <>
              {/* Pestañas Principales: Usuarios vs Clientes */}
              <div className="tabs">
                <button
                  className={`tabs__btn ${activeTab === 'members' ? 'tabs__btn--active' : ''}`}
                  onClick={() => {
                    setActiveTab('members');
                    setSelectedRole('');
                    setSearchInGroup('');
                    setSearchAvailable('');
                    setAvailablePage(0);
                    setInGroupPage(0);
                  }}
                >
                  <FontAwesomeIcon icon={faUsers} />
                  <span>Usuarios</span>
                </button>
                <button
                  className={`tabs__btn ${activeTab === 'customers' ? 'tabs__btn--active' : ''}`}
                  onClick={() => {
                    setActiveTab('customers');
                    setSelectedRole('');
                    setSearchInGroup('');
                    setSearchAvailable('');
                    setAvailablePage(0);
                    setInGroupPage(0);
                  }}
                >
                  <FontAwesomeIcon icon={faUserCircle} />
                  <span>Clientes</span>
                </button>
              </div>

              {/* Barra de Filtro de Rol Dinámico para Usuarios */}
              {activeTab === 'members' && availableRoles.length > 0 && (
                <div className="group-roles-filter">
                  <FontAwesomeIcon icon={faFilter} className="text-muted text-sm" />
                  <span className="group-roles-filter__label">Filtrar por rol:</span>
                  <select
                    className="input group-roles-filter__select"
                    value={selectedRole}
                    onChange={(e) => {
                      setSelectedRole(e.target.value);
                      setAvailablePage(0);
                      setInGroupPage(0);
                    }}
                  >
                    <option value="">Todos los roles (sin filtrar)</option>
                    {availableRoles.map(role => (
                      <option key={role.role_id} value={role.slug}>
                        {role.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Vista Dividida (Split View): Disponibles vs En el Grupo */}
              <div className="split-view">
                {/* Columna Izquierda: Disponibles para agregar (solo visible si tiene permiso de gestión) */}
                {canManageGroups && (
                  <div className="split-view__column">
                    <h3>Disponibles</h3>
                    <div className="search-bar search-bar--sm">
                      <input
                        className="input"
                        type="search"
                        placeholder={activeTab === 'customers' ? "Nombre, email, RFC..." : "Buscar por nombre, usuario..."}
                        value={searchAvailable}
                        onChange={(e) => setSearchAvailable(e.target.value)}
                      />
                      <button className="btn btn--primary" type="button"><FontAwesomeIcon icon={faSearch} /></button>
                    </div>
                    <div className="split-view__list-container">
                      {loadingAvailable ? <LoadingSpinner message="Cargando..." /> : availableUsers.length === 0 ? (
                        <p className="empty-state">{searchAvailable ? 'No se encontraron resultados' : 'No hay usuarios disponibles'}</p>
                      ) : (
                        <>
                          <ul className="split-view__list">
                            {availableUsers.map((user, idx) => {
                              const rawId = activeTab === 'customers' ? (user.customer_id ?? user.id) : (user.user_id ?? user.id);
                              const itemId = rawId != null ? rawId : idx;
                              const roleBadge = user.role_name || user.role_slug || user.role;
                              return (
                                <li key={`avail-${itemId}-${idx}`} className="list-item-card">
                                  <div className="member-info d-flex align-center gap-3 flex-1 overflow-hidden">
                                    <FontAwesomeIcon
                                      icon={activeTab === 'customers' ? faUserCircle : faUserTie}
                                      className="text-2xl text-muted"
                                    />
                                    <div className="overflow-hidden">
                                      <div className="d-flex align-center gap-2 flex-wrap">
                                        <span className="font-bold text-sm truncate">{user.full_name || user.username}</span>
                                        {activeTab === 'members' && roleBadge && (
                                          <span className="badge badge--info text-xs">{roleBadge}</span>
                                        )}
                                      </div>
                                      <div className="text-xs text-muted truncate">{user.email || user.rfc || 'Sin email'}</div>
                                      <div className="text-xs text-primary truncate">@{user.username}</div>
                                    </div>
                                  </div>
                                  <button
                                    className="btn btn--icon btn--success"
                                    onClick={() => handleAddMember(itemId)}
                                    title="Agregar al grupo"
                                  >
                                    <FontAwesomeIcon icon={faPlus} />
                                  </button>
                                </li>
                              );
                            })}
                          </ul>
                          <PaginationButtons
                            onPrev={() => setAvailablePage(p => Math.max(0, p - 1))}
                            onNext={() => setAvailablePage(p => p + 1)}
                            canGoPrev={availablePage > 0}
                            canGoNext={availableHasMore}
                          />
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Columna Derecha: Asignados Actualmente */}
                <div className="split-view__column">
                  <h3>{canManageGroups ? 'En el Grupo' : (activeTab === 'customers' ? 'Clientes Asignados' : 'Miembros del Grupo')}</h3>
                  <div className="search-bar search-bar--sm">
                    <input
                      className="input"
                      type="search"
                      placeholder={activeTab === 'customers' ? "Nombre, email, RFC..." : "Buscar en miembros..."}
                      value={searchInGroup}
                      onChange={(e) => setSearchInGroup(e.target.value)}
                    />
                    <button className="btn btn--primary" type="button"><FontAwesomeIcon icon={faSearch} /></button>
                  </div>
                  <div className="split-view__list-container">
                    {loadingInGroup ? <LoadingSpinner message="Cargando..." /> : inGroupUsers.length === 0 ? (
                      <p className="empty-state">
                        {searchInGroup ? 'No se encontraron resultados' : `No hay ${activeTab === 'customers' ? 'clientes' : 'miembros'} en este grupo`}
                      </p>
                    ) : (
                      <>
                        <ul className="split-view__list">
                          {inGroupUsers.map((user, idx) => {
                            const rawId = activeTab === 'customers' ? (user.customer_id ?? user.id) : (user.user_id ?? user.id);
                            const itemId = rawId != null ? rawId : idx;
                            const roleBadge = user.role_name || user.role_slug || user.role;
                            return (
                              <li key={`ingroup-${itemId}-${idx}`} className="list-item-card">
                                <div className="member-info d-flex align-center gap-3 flex-1 overflow-hidden">
                                  <FontAwesomeIcon
                                    icon={activeTab === 'customers' ? faUserCircle : faUserTie}
                                    className="text-2xl text-muted"
                                  />
                                  <div className="overflow-hidden">
                                    <div className="d-flex align-center gap-2 flex-wrap">
                                      <span className="font-bold text-sm truncate">{user.full_name || user.username}</span>
                                      {activeTab === 'members' && roleBadge && (
                                        <span className="badge badge--info text-xs">{roleBadge}</span>
                                      )}
                                    </div>
                                    <div className="text-xs text-muted truncate">{user.email || user.rfc || 'Sin email'}</div>
                                    <div className="text-xs text-primary truncate">@{user.username}</div>
                                  </div>
                                </div>
                                {canManageGroups && (
                                  <button
                                    className="btn btn--icon btn--danger"
                                    onClick={() => handleRemoveMember(itemId)}
                                    title="Remover del grupo"
                                  >
                                    <FontAwesomeIcon icon={faTrashAlt} />
                                  </button>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                        <PaginationButtons
                          onPrev={() => setInGroupPage(p => Math.max(0, p - 1))}
                          onNext={() => setInGroupPage(p => p + 1)}
                          canGoPrev={inGroupPage > 0}
                          canGoNext={inGroupHasMore}
                        />
                      </>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}