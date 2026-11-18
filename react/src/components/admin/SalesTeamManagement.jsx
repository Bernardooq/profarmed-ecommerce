import { useState, useEffect, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faUserTie, faUsers, faUsersGear, faSearch, faUserCircle, faBoxesStacked,
  faPencilAlt, faTrashAlt, faPlus, faEye, faFileExport, faExchangeAlt, faLayerGroup,
  faClock, faCheckCircle, faTruck, faClipboardCheck, faBan, faShieldAlt, faChevronDown, faFilter
} from '@fortawesome/free-solid-svg-icons';
import adminService from '../../services/adminService';
import { userService } from '../../services/userService';
import salesGroupService from '../../services/salesGroupService';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import PaginationButtons from '../common/PaginationButtons';
import GroupDetailsModal from '../modals/groups/GroupDetailsModal';
import UserFormModal from '../users/UserFormModal';
import GroupFormModal from '../modals/groups/GroupFormModal';
import ModalAssignGroups from '../modals/users/ModalAssignGroups';

import { usePaginationLimit } from '../../context/PaginationLimitContext';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function SalesTeamManagement() {
  const { can } = usePermissions();
  const canManageUsers = can(PERMISSIONS.USERS_CREATE) || can(PERMISSIONS.USERS_EDIT) || can(PERMISSIONS.USERS_MANAGE) || can(PERMISSIONS.SYSTEM_ADMIN);
  const canDeleteUsers = can(PERMISSIONS.USERS_DELETE) || can(PERMISSIONS.SYSTEM_ADMIN);
  const canManageGroups = can(PERMISSIONS.GROUPS_MANAGE) || can(PERMISSIONS.SYSTEM_ADMIN);
  const canExport = can(PERMISSIONS.REPORTS_EXPORT) || can(PERMISSIONS.SYSTEM_ADMIN);

  // Pestañas dinámicas: roles operativos o 'groups'
  const [activeTab, setActiveTab] = useState('');
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [roleChangingUserId, setRoleChangingUserId] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const { limit: itemsPerPage } = usePaginationLimit();

  // Modals
  const [showUserModal, setShowUserModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showGroupDetailsModal, setShowGroupDetailsModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [userRole, setUserRole] = useState('');
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedUserForAssign, setSelectedUserForAssign] = useState(null);
  const [openRoleDropdownId, setOpenRoleDropdownId] = useState(null);

  // Helper para identificar y excluir roles que no pertenecen al equipo operativo
  const isExcludedRole = (r) => {
    if (!r) return true;
    const slug = (r.slug || '').toLowerCase();
    return slug === 'customer' || slug === 'admin' || r.role_id === 1 || Boolean(r.is_system);
  };

  // Filtrar roles de equipo (excluyendo cliente y administrador general del sistema)
  const teamRoles = useMemo(() => {
    return availableRoles.filter(r => !isExcludedRole(r));
  }, [availableRoles]);

  // Rol activo actual
  const activeRoleObj = useMemo(() => {
    return teamRoles.find(r => r.slug === activeTab) || teamRoles[0] || { slug: activeTab, name: activeTab };
  }, [teamRoles, activeTab]);

  // Cargar catálogo de roles al inicio
  const fetchAvailableRoles = async () => {
    try {
      const rolesList = await adminService.getRoles();
      if (Array.isArray(rolesList) && rolesList.length > 0) {
        setAvailableRoles(rolesList);
        // Roles de equipo operativo válidos
        const validSlugs = rolesList
          .filter(r => !isExcludedRole(r))
          .map(r => r.slug);

        if (validSlugs.length > 0 && activeTab !== 'groups' && (!validSlugs.includes(activeTab) || activeTab === 'admin')) {
          setActiveTab(validSlugs[0]);
        }
      }
    } catch (e) {
      console.error('Error al cargar roles disponibles:', e);
    }
  };

  useEffect(() => {
    fetchAvailableRoles();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => { 
      setDebouncedSearchTerm(searchTerm);
      setPage(0);
    }, 2500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    loadData();
  }, [activeTab, page, debouncedSearchTerm, itemsPerPage]);

  const loadData = async () => {
    if (!activeTab) return;
    if (activeTab === 'groups') {
      await loadGroups();
    } else {
      await loadUsersForRole(activeTab);
    }
  };

  const loadUsersForRole = async (roleSlug) => {
    if (roleSlug === 'admin') {
      setUsers([]);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const res = await userService.getUsers({
        role: roleSlug,
        skip: page * itemsPerPage,
        limit: itemsPerPage + 1,
        search: debouncedSearchTerm || undefined
      });
      const hasMorePages = res.length > itemsPerPage;
      setHasMore(hasMorePages);
      setUsers(hasMorePages ? res.slice(0, itemsPerPage) : res);
    } catch (err) {
      setError(`No se pudieron cargar los usuarios para el rol ${roleSlug}.`);
      console.error(`Failed to load users for ${roleSlug}:`, err);
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      setLoading(true);
      setError(null);
      const groupsData = await salesGroupService.getSalesGroups({
        skip: page * itemsPerPage,
        limit: itemsPerPage,
        search: debouncedSearchTerm || undefined
      });
      const total = groupsData.total || 0;
      setHasMore((page + 1) * itemsPerPage < total);
      setGroups(groupsData.items || []);
    } catch (err) {
      setError('No se pudieron cargar los grupos de ventas.');
      console.error('Failed to load groups:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setDebouncedSearchTerm(searchTerm);
    setPage(0);
  };

  const openAddUserModal = (roleSlug) => {
    setUserRole(roleSlug);
    setEditingUser(null);
    setShowUserModal(true);
  };

  const openEditUserModal = (user, roleSlug) => {
    setUserRole(roleSlug);
    setEditingUser(user);
    setShowUserModal(true);
  };

  const openAddGroupModal = () => {
    setEditingGroup(null);
    setShowGroupModal(true);
  };

  const openEditGroupModal = (group) => {
    setEditingGroup(group);
    setShowGroupModal(true);
  };

  const openGroupDetailsModal = (group) => {
    setSelectedGroup(group);
    setShowGroupDetailsModal(true);
  };

  const handleDeleteUser = async (user) => {
    if (!window.confirm(`¿Estás seguro de eliminar a ${user.full_name}?`)) return;
    try {
      await adminService.deleteUser(user.user_id);
      loadData();
    } catch (err) {
      setError('Error al eliminar el usuario.');
      console.error('Failed to delete user:', err);
    }
  };

  const handleDeleteGroup = async (group) => {
    if (!window.confirm(`¿Estás seguro de eliminar el grupo "${group.group_name}"? Esto eliminará todas las asignaciones de miembros.`)) return;
    try {
      await salesGroupService.deleteSalesGroup(group.sales_group_id);
      loadGroups();
    } catch (err) {
      setError('Error al eliminar el grupo.');
      console.error('Failed to delete group:', err);
    }
  };

  const handleUserSaved = () => {
    setShowUserModal(false);
    loadData();
  };

  const handleGroupSaved = () => {
    setShowGroupModal(false);
    loadGroups();
  };

  const handleRoleChange = async (user, targetRoleSlug) => {
    if (user.role === targetRoleSlug) return;
    const findRoleName = (slug) => {
      const found = availableRoles.find(r => r.slug === slug);
      if (found) return found.name;
      return slug;
    };

    const currentName = findRoleName(user.role);
    const targetName = findRoleName(targetRoleSlug);

    const confirmMsg = `¿Cambiar rol de "${user.full_name}" de "${currentName}" a "${targetName}"?\n\nLas capacidades y permisos del usuario se actualizarán inmediatamente según el nuevo rol.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      setRoleChangingUserId(user.user_id);
      await adminService.changeUserRole(user.user_id, targetRoleSlug);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al cambiar rol del usuario');
      console.error('Failed to change role:', err);
    } finally {
      setRoleChangingUserId(null);
    }
  };

  const handleAssignGroupsSave = async (userId, groupIds) => {
    try {
      await adminService.assignUserGroups(userId, groupIds);
      alert('Grupos asignados exitosamente');
      loadData();
    } catch (err) {
      throw err;
    }
  };

  const handleExportExcel = async (roleSlug) => {
    try {
      const extraParams = {};
      const currentSearch = debouncedSearchTerm || searchTerm;
      if (currentSearch) extraParams.search = currentSearch;
      await adminService.exportXLSX(roleSlug || 'usuarios', extraParams);
    } catch (err) {
      alert(err.message || 'No se pudo exportar la lista de usuarios.');
    }
  };

  // Helper de icono según el rol
  const getRoleIcon = (slug) => {
    switch (slug) {
      case 'seller': return faUserTie;
      case 'marketing': return faUsers;
      case 'warehouse': return faBoxesStacked;
      case 'admin': return faShieldAlt;
      default: return faUserCircle;
    }
  };

  // ─── Render Helpers ──────────────────────────

  const renderUserTable = (usersList, roleObj) => (
    <>
      <div className="section-header">
        <h2 className="section-title">{roleObj?.name || 'Equipo'}</h2>
        <div className="section-header__actions">
          {canExport && (
            <button
              className="btn btn--secondary btn--sm"
              onClick={() => handleExportExcel(roleObj?.slug)}
              title="Exportar a Excel"
            >
              <FontAwesomeIcon icon={faFileExport} /> Exportar Excel
            </button>
          )}
          {canManageUsers && (
            <button className="btn btn--primary btn--sm" onClick={() => openAddUserModal(roleObj?.slug)}>
              <FontAwesomeIcon icon={getRoleIcon(roleObj?.slug)} />
              {' '}Añadir {roleObj?.name || 'Usuario'}
            </button>
          )}
        </div>
      </div>

      <div className="dashboard-controls">
        <form className="search-bar" onSubmit={handleSearch}>
          <input
            type="search"
            className="input"
            placeholder={`Buscar en ${roleObj?.name || 'equipo'}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button type="submit" className="btn btn--primary" aria-label="Buscar">
            <FontAwesomeIcon icon={faSearch} />
          </button>
        </form>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>{roleObj?.name || 'Colaborador'}</th>
              <th>Usuario</th>
              <th>Rol Asignado</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usersList.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center">
                  No se encontraron usuarios con el rol {roleObj?.name || roleObj?.slug}
                </td>
              </tr>
            ) : (
              usersList.map((user) => (
                <tr key={user.user_id}>
                  <td data-label="ID">{user.user_id}</td>
                  <td data-label={roleObj?.name || 'Colaborador'}>
                    <div className="user-cell">
                      <FontAwesomeIcon icon={faUserCircle} className="user-cell__avatar" />
                      <div className="user-cell__info">
                        <span className="user-cell__name"><b>{user.full_name}</b></span>
                        <span className="user-cell__email">{user.email}</span>
                      </div>
                    </div>
                  </td>
                  <td data-label="Usuario">{user.username}</td>
                  <td data-label="Rol Asignado">
                    {canManageUsers ? (
                      <select
                        className="input select select--sm roles-table__role-select"
                        value={user.role || roleObj?.slug}
                        onChange={(e) => handleRoleChange(user, e.target.value)}
                        disabled={roleChangingUserId === user.user_id}
                        aria-label={`Cambiar rol operativo de ${user.full_name}`}
                      >
                        {teamRoles.length > 0 ? (
                          teamRoles.map(r => (
                            <option key={r.role_id || r.slug} value={r.slug}>
                              {r.name}
                            </option>
                          ))
                        ) : (
                          <option value={user.role || roleObj?.slug}>{roleObj?.name || user.role}</option>
                        )}
                      </select>
                    ) : (
                      <span className="badge badge--primary font-bold">
                        {roleObj?.name || user.role_name || user.role}
                      </span>
                    )}
                  </td>
                  <td data-label="Estado">
                    <span className={`status-badge ${user.is_active ? 'status--active' : 'status--inactive'}`}>
                      {user.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td data-label="Acciones" className="actions-cell">
                    {canManageGroups && (
                      <button
                        className="btn btn--icon btn--ghost"
                        onClick={() => { setSelectedUserForAssign(user); setShowAssignModal(true); }}
                        aria-label={`Asignar grupos a ${user.full_name}`}
                        title="Asignar grupos comerciales"
                      >
                        <FontAwesomeIcon icon={faLayerGroup} />
                      </button>
                    )}
                    {canManageUsers && (
                      <button
                        className="btn btn--icon btn--ghost"
                        onClick={() => openEditUserModal(user, roleObj?.slug)}
                        aria-label={`Editar ${roleObj?.name}`}
                      >
                        <FontAwesomeIcon icon={faPencilAlt} />
                      </button>
                    )}
                    {canDeleteUsers && (
                      <button
                        className="btn btn--icon btn--danger"
                        onClick={() => handleDeleteUser(user)}
                        aria-label={`Eliminar ${roleObj?.name}`}
                      >
                        <FontAwesomeIcon icon={faTrashAlt} />
                      </button>
                    )}
                    {!canManageGroups && !canManageUsers && !canDeleteUsers && (
                      <span className="text-muted text-sm">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {usersList.length > 0 && (
        <PaginationButtons
          onPrev={() => setPage(p => Math.max(0, p - 1))}
          onNext={() => setPage(p => p + 1)}
          canGoPrev={page > 0}
          canGoNext={hasMore}
        />
      )}
    </>
  );

  const statusConfig = {
    pending_validation: { label: 'Pendientes', color: 'var(--color-warning)', icon: faClock },
    approved: { label: 'Aprobados', color: 'var(--color-info)', icon: faCheckCircle },
    shipped: { label: 'Enviados', color: 'var(--color-secondary)', icon: faTruck },
    delivered: { label: 'Entregados', color: 'var(--color-success)', icon: faClipboardCheck },
    cancelled: { label: 'Cancelados', color: 'var(--color-danger)', icon: faBan },
  };

  const renderOrderStats = (stats) => {
    if (!stats || Object.keys(stats).length === 0) return <span className="text-muted">—</span>;
    const total = Object.values(stats).reduce((a, b) => a + b, 0);
    return (
      <div className="order-stats-preview">
        {Object.entries(statusConfig).map(([key, cfg]) => {
          const count = stats[key] || 0;
          if (count === 0) return null;
          const modClass = key === 'pending_validation' ? 'warning'
            : key === 'approved' ? 'info'
            : key === 'shipped' ? 'secondary'
            : key === 'delivered' ? 'success'
            : 'danger';
          return (
            <span 
              key={key} 
              className={`order-stats-badge order-stats-badge--${modClass}`}
              title={`${cfg.label}: ${count}`}
            >
              <FontAwesomeIcon icon={cfg.icon} size="xs" />
              <span>{count}</span>
            </span>
          );
        })}
        <span className="order-stats-total" title={`Total de pedidos: ${total}`}>
          ({total})
        </span>
      </div>
    );
  };

  const renderGroupsTab = () => (
    <>
      <div className="section-header">
        <h2 className="section-title">Grupos de Ventas</h2>
        <div className="section-header__actions">
          <button
            className="btn btn--secondary btn--sm"
            onClick={() => {
              const currentSearch = debouncedSearchTerm || searchTerm;
              adminService.exportXLSX('grupos', currentSearch ? { search: currentSearch } : {});
            }}
            title="Exportar a Excel"
          >
            <FontAwesomeIcon icon={faFileExport} /> Exportar Excel
          </button>
          {canManageGroups && (
            <button className="btn btn--primary btn--sm" onClick={openAddGroupModal}>
              <FontAwesomeIcon icon={faUsersGear} /> Crear Grupo
            </button>
          )}
        </div>
      </div>

      <div className="dashboard-controls">
        <form className="search-bar" onSubmit={handleSearch}>
          <input
            type="search"
            className="input"
            placeholder="Buscar grupo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button type="submit" className="btn btn--primary" aria-label="Buscar">
            <FontAwesomeIcon icon={faSearch} />
          </button>
        </form>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Grupo</th>
              <th>Miembros</th>
              <th>Clientes</th>
              <th><span title="Estados de pedidos">📊 Pedidos</span></th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {groups.length === 0 ? (
              <tr>
                <td colSpan="6" className="text-center">No se encontraron grupos de ventas</td>
              </tr>
            ) : (
              groups.map((group) => (
                <tr key={group.sales_group_id}>
                  <td data-label="Grupo">
                    <div>
                      <div><b>{group.group_name}</b></div>
                      {group.description && <div className="text-muted text-sm">{group.description}</div>}
                    </div>
                  </td>
                  <td data-label="Miembros">
                    <div className="role-dropdown-container">
                      <button
                        type="button"
                        className="role-dropdown-btn"
                        onClick={() => setOpenRoleDropdownId(openRoleDropdownId === group.sales_group_id ? null : group.sales_group_id)}
                        title="Clic para ver desglose de miembros por rol"
                      >
                        <FontAwesomeIcon icon={faUsers} className="text-primary" />
                        <span className="font-bold">
                          {group.member_count ?? 0} miembros
                        </span>
                        <FontAwesomeIcon
                          icon={faChevronDown}
                          className={`dropdown-chevron ${openRoleDropdownId === group.sales_group_id ? 'dropdown-chevron--open' : ''}`}
                        />
                      </button>
                      {openRoleDropdownId === group.sales_group_id && (
                        <div className="role-dropdown-menu">
                          <div className="role-dropdown-menu__header">
                            <span>Desglose por Rol</span>
                          </div>
                          {Array.isArray(group.members_by_role) && group.members_by_role.length > 0 ? (
                            <ul className="role-dropdown-menu__list">
                              {group.members_by_role.map(r => (
                                <li key={r.role_id} className="role-dropdown-menu__item">
                                  <span className="role-dropdown-menu__name">{r.name}</span>
                                  <span className="badge badge--info text-xs">{r.count}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div className="role-dropdown-menu__empty text-muted text-xs">
                              Sin miembros asignados
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </td>
                  <td data-label="Clientes"><span className="badge badge--primary">{group.customer_count || 0}</span></td>
                  <td data-label="Pedidos">{renderOrderStats(group.order_stats)}</td>
                  <td data-label="Estado">
                    <span className={`status-badge ${group.is_active ? 'status--active' : 'status--inactive'}`}>
                      {group.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td data-label="Acciones" className="actions-cell">
                    <button className="btn btn--icon btn--ghost" onClick={() => openGroupDetailsModal(group)} aria-label="Ver detalles" title="Ver miembros">
                      <FontAwesomeIcon icon={faEye} />
                    </button>
                    {canManageGroups && (
                      <>
                        <button className="btn btn--icon btn--ghost" onClick={() => openEditGroupModal(group)} aria-label="Editar grupo">
                          <FontAwesomeIcon icon={faPencilAlt} />
                        </button>
                        <button className="btn btn--icon btn--danger" onClick={() => handleDeleteGroup(group)} aria-label="Eliminar grupo">
                          <FontAwesomeIcon icon={faTrashAlt} />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {groups.length > 0 && (
        <PaginationButtons
          onPrev={() => setPage(p => Math.max(0, p - 1))}
          onNext={() => setPage(p => p + 1)}
          canGoPrev={page > 0}
          canGoNext={hasMore}
        />
      )}
    </>
  );



  if (loading && (users.length === 0 && groups.length === 0 && availableRoles.length === 0)) {
    return <LoadingSpinner message="Cargando..." />;
  }

  return (
    <>
      <section className="dashboard-section">
        {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

        {/* Selector responsivo para móvil / celular (Selection Button) */}
        <div className="team-nav-mobile">
          <div className="team-selection-btn-card">
            <div className="team-selection-btn-card__header">
              <span className="team-selection-btn-card__label">
                <FontAwesomeIcon icon={faFilter} className="text-primary mr-1" />
                Sección del Equipo
              </span>
              <span className="badge badge--info text-xs">
                {activeTab === 'groups' ? `${groups.length} Grupos` : `${users.length} Colaboradores`}
              </span>
            </div>

            <div className="team-selection-btn">
              {/* Selector nativo encima del botón para abrir el picker nativo del celular con 1 toque */}
              <select
                className="team-selection-btn__native-select"
                value={activeTab}
                onChange={(e) => {
                  setActiveTab(e.target.value);
                  setPage(0);
                  setSearchTerm('');
                  setDebouncedSearchTerm('');
                }}
                aria-label="Seleccionar rol o equipo a visualizar"
              >
                <optgroup label="── ROLES OPERATIVOS DEL EQUIPO ──">
                  {teamRoles.map(role => (
                    <option key={role.slug} value={role.slug}>
                      {role.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="── ESTRUCTURA COMERCIAL ──">
                  <option value="groups">👥 Grupos de Ventas</option>
                </optgroup>
              </select>

              {/* Contenido visual del botón de selección */}
              <div className="team-selection-btn__body">
                <div className="team-selection-btn__icon">
                  <FontAwesomeIcon icon={activeTab === 'groups' ? faUsersGear : getRoleIcon(activeTab)} />
                </div>
                <div className="team-selection-btn__info">
                  <span className="team-selection-btn__title">
                    {activeTab === 'groups' ? 'Grupos de Ventas' : (activeRoleObj?.name || 'Seleccionar Rol')}
                  </span>
                  <span className="team-selection-btn__desc">
                    {activeTab === 'groups'
                      ? 'Estructura comercial y carteras de clientes'
                      : (activeRoleObj?.description || 'Colaboradores del equipo operativo')}
                  </span>
                </div>
                <div className="team-selection-btn__action">
                  <span className="team-selection-btn__tag">Cambiar</span>
                  <FontAwesomeIcon icon={faChevronDown} className="team-selection-btn__chevron" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Pill-style sub-tabs dinámicos para Tablet / Desktop */}
        <nav className="dashboard-layout__tabs-nav team-nav-desktop">
          {teamRoles.map(role => (
            <button
              key={role.slug}
              className={`dashboard-layout__tab ${activeTab === role.slug ? 'dashboard-layout__tab--active' : ''}`}
              onClick={() => { setActiveTab(role.slug); setPage(0); setSearchTerm(''); setDebouncedSearchTerm(''); }}
            >
              <FontAwesomeIcon icon={getRoleIcon(role.slug)} /> {role.name}
            </button>
          ))}
          <button
            className={`dashboard-layout__tab ${activeTab === 'groups' ? 'dashboard-layout__tab--active' : ''}`}
            onClick={() => { setActiveTab('groups'); setPage(0); setSearchTerm(''); setDebouncedSearchTerm(''); }}
          >
            <FontAwesomeIcon icon={faUsersGear} /> Grupos de Ventas
          </button>
        </nav>

        <div className="dashboard-layout__tabs-content">
          {activeTab === 'groups' ? renderGroupsTab() : renderUserTable(users, activeRoleObj)}
        </div>
      </section>

      {showUserModal && (
        <UserFormModal
          user={editingUser}
          role={userRole}
          onClose={() => setShowUserModal(false)}
          onSaved={handleUserSaved}
        />
      )}

      {showGroupModal && (
        <GroupFormModal
          group={editingGroup}
          onClose={() => setShowGroupModal(false)}
          onSaved={handleGroupSaved}
        />
      )}

      {showAssignModal && selectedUserForAssign && (
        <ModalAssignGroups
          isOpen={showAssignModal}
          onClose={() => { setShowAssignModal(false); setSelectedUserForAssign(null); }}
          user={selectedUserForAssign}
          onSave={handleAssignGroupsSave}
        />
      )}

      {showGroupDetailsModal && selectedGroup && (
        <GroupDetailsModal
          group={selectedGroup}
          onClose={() => setShowGroupDetailsModal(false)}
          onUpdate={async () => {
            try {
              const updatedGroup = await salesGroupService.getSalesGroup(selectedGroup.sales_group_id);
              setGroups(prevGroups =>
                prevGroups.map(g =>
                  g.sales_group_id === updatedGroup.sales_group_id ? updatedGroup : g
                )
              );
              setSelectedGroup(updatedGroup);
            } catch (err) {
              console.error('Failed to reload group:', err);
              loadGroups();
            }
          }}
        />
      )}


    </>
  );
}
