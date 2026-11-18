import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faShieldAlt, faUserTie, faUsers, faBoxesStacked, faPlus,
  faPencilAlt, faTrashAlt, faCheckCircle, faBan, faFileExport
} from '@fortawesome/free-solid-svg-icons';
import adminService from '../../services/adminService';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';
import RoleFormModal from './RoleFormModal';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSIONS } from '../../config/permissions';

export default function RolesManagement() {
  const { can, isAdmin } = usePermissions();
  const canManageRoles = can(PERMISSIONS.SYSTEM_ADMIN) || can(PERMISSIONS.USERS_CREATE) || can(PERMISSIONS.USERS_EDIT) || isAdmin;
  const canDeleteRoles = can(PERMISSIONS.SYSTEM_ADMIN) || can(PERMISSIONS.USERS_DELETE) || isAdmin;
  const canExport = can(PERMISSIONS.REPORTS_EXPORT) || can(PERMISSIONS.SYSTEM_ADMIN) || isAdmin;

  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [editingRole, setEditingRole] = useState(null);

  const getRoleIcon = (slug = '') => {
    const s = String(slug).toLowerCase();
    if (s.startsWith('admin')) return faShieldAlt;
    if (s.startsWith('seller') || s.includes('vent') || s.includes('comercial') || s.includes('agent')) return faUserTie;
    if (s.startsWith('market') || s.includes('mercad')) return faUsers;
    if (s.startsWith('ware') || s.includes('almacen') || s.includes('bodega')) return faBoxesStacked;
    return faShieldAlt;
  };


  const loadRoles = async () => {
    try {
      setLoading(true);
      setError(null);
      const rolesList = await adminService.getRoles();
      if (Array.isArray(rolesList)) {
        setRoles(rolesList);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudieron cargar los roles del sistema.');
      console.error('Error al cargar roles:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoles();
  }, []);

  const openAddRoleModal = () => {
    setEditingRole(null);
    setShowRoleModal(true);
  };

  const openEditRoleModal = (roleItem) => {
    if (isAdminRole(roleItem) && !isAdmin) {
      alert('Solo un Administrador General tiene autorización para modificar los permisos del Administrador General.');
      return;
    }
    setEditingRole(roleItem);
    setShowRoleModal(true);
  };

  const handleRoleSaved = () => {
    setShowRoleModal(false);
    setEditingRole(null);
    loadRoles();
  };

  const isAdminRole = (r) => Boolean(r && (r.slug === 'admin' || r.role_id === 1));

  const handleDeleteRole = async (roleItem) => {
    if (isAdminRole(roleItem)) {
      alert('El rol Administrador General es el rol protegido principal del sistema y no puede ser eliminado.');
      return;
    }
    const usersCount = roleItem.users_count || 0;
    if (usersCount > 0) {
      alert(`No se puede eliminar el rol "${roleItem.name}" porque tiene ${usersCount} usuario(s) asignado(s). Debe reasignar o desvincular a todos los usuarios antes de eliminarlo.`);
      return;
    }
    if (!window.confirm(`¿Estás seguro de que deseas eliminar permanentemente el rol "${roleItem.name}"? Sus permisos asignados se eliminarán en cascada.`)) {
      return;
    }

    try {
      await adminService.deleteRole(roleItem.role_id);
      loadRoles();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar el rol');
    }
  };

  if (loading && roles.length === 0) {
    return <LoadingSpinner message="Cargando roles y permisos del sistema..." />;
  }

  return (
    <section className="dashboard-section">
      {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

      <div className="section-header">
        <div>
          <h2 className="section-title">Roles y Permisos del Sistema</h2>
          <p className="text-muted text-sm section-subtitle">
            Configuración dinámica de roles y asignación de capacidades granulares (RBAC / PBAC).
          </p>
        </div>
        <div className="section-header__actions">
          {canExport && (
            <button
              className="btn btn--secondary btn--sm"
              onClick={() => adminService.exportXLSX('roles')}
              title="Exportar Roles y Permisos a Excel"
            >
              <FontAwesomeIcon icon={faFileExport} /> Exportar Excel
            </button>
          )}
          {canManageRoles && (
            <button className="btn btn--primary btn--sm" onClick={openAddRoleModal}>
              <FontAwesomeIcon icon={faPlus} /> Crear Nuevo Rol
            </button>
          )}
        </div>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Rol / Nombre</th>
              <th>Identificador (Slug)</th>
              <th>Descripción</th>
              <th>Permisos</th>
              <th>Usuarios</th>
              <th>Tipo</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {roles.length === 0 ? (
              <tr>
                <td colSpan="8" className="text-center">No se encontraron roles en el sistema</td>
              </tr>
            ) : (
              roles.map((roleItem) => {
                const isProtectedAdmin = isAdminRole(roleItem);
                const usersCount = roleItem.users_count || 0;
                const hasUsers = usersCount > 0;

                return (
                  <tr key={roleItem.role_id}>
                    <td data-label="Rol / Nombre">
                      <div className="roles-table__cell-name">
                        <FontAwesomeIcon icon={getRoleIcon(roleItem.slug)} className="roles-table__icon" />
                        <b>{roleItem.name}</b>
                      </div>
                    </td>
                    <td data-label="Slug">
                      <code className="roles-table__code">
                        {roleItem.slug}
                      </code>
                    </td>
                    <td data-label="Descripción">
                      <span className={`roles-table__desc ${!roleItem.description ? 'roles-table__desc--muted' : ''}`}>
                        {roleItem.description || '—'}
                      </span>
                    </td>
                    <td data-label="Permisos">
                      <span className="badge badge--info font-bold">
                        {roleItem.permissions?.length || 0} permisos
                      </span>
                    </td>
                    <td data-label="Usuarios">
                      <span className="badge badge--secondary font-bold">
                        {usersCount} usuarios
                      </span>
                    </td>
                    <td data-label="Tipo">
                      {isProtectedAdmin ? (
                        <span className="badge badge--secondary" title="Rol protegido del sistema">
                          🔒 Sistema
                        </span>
                      ) : (
                        <span className="badge badge--primary">
                          Personalizado
                        </span>
                      )}
                    </td>
                    <td data-label="Estado">
                      <span className={`status-badge ${roleItem.is_active ? 'status--active' : 'status--inactive'}`}>
                        {roleItem.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td data-label="Acciones" className="actions-cell">
                      {canManageRoles && (
                        <button
                          className="btn btn--icon btn--ghost"
                          onClick={() => openEditRoleModal(roleItem)}
                          disabled={isProtectedAdmin && !isAdmin}
                          aria-label={`Editar ${roleItem.name}`}
                          title={
                            isProtectedAdmin
                              ? (isAdmin
                                ? 'Editar permisos granulares del Administrador General'
                                : 'Solo un Administrador General tiene autorización para modificar sus permisos')
                              : `Editar propiedades y permisos del rol ${roleItem.name}`
                          }
                        >
                          <FontAwesomeIcon icon={faPencilAlt} />
                        </button>
                      )}
                      {canDeleteRoles && (
                        <button
                          className="btn btn--icon btn--danger"
                          onClick={() => handleDeleteRole(roleItem)}
                          disabled={isProtectedAdmin || hasUsers}
                          aria-label={`Eliminar ${roleItem.name}`}
                          title={
                            isProtectedAdmin
                              ? 'El rol Administrador General es el rol protegido principal del sistema y no puede eliminarse'
                              : (hasUsers
                                ? `No se puede eliminar: tiene ${usersCount} usuario(s) asignado(s). Debe desvincularlos primero.`
                                : `Eliminar permanentemente el rol ${roleItem.name}`)
                          }
                        >
                          <FontAwesomeIcon icon={faTrashAlt} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {showRoleModal && (
        <RoleFormModal
          role={editingRole}
          onClose={() => { setShowRoleModal(false); setEditingRole(null); }}
          onSaved={handleRoleSaved}
        />
      )}
    </section>
  );
}
