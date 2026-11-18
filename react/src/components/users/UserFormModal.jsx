import { useState, useEffect } from 'react';
import adminService from '../../services/adminService';
import ErrorMessage from '../common/ErrorMessage';
import { usePermissions } from '../../hooks/usePermissions';

export default function UserFormModal({ user, role, onClose, onSaved }) {
  const { isAdmin } = usePermissions();

  const [formData, setFormData] = useState({
    user_id: '',
    username: '',
    email: '',
    password: '',
    full_name: '',
    role_id: null,
    role: role || '',
    is_active: true,
    is_locked: false,
    failed_login_attempts: 0
  });
  const [availableRoles, setAvailableRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Cargar roles dinámicos disponibles desde el backend
    const fetchRoles = async () => {
      try {
        const roles = await adminService.getRoles();
        if (Array.isArray(roles) && roles.length > 0) {
          // Filtrar roles: excluir 'customer' y roles protegidos de administración si el usuario no es admin
          const filteredRoles = roles.filter(r => {
            if (r.slug === 'customer') return false;
            if (!isAdmin && (r.slug === 'admin' || r.role_id === 1 || r.is_system)) return false;
            return true;
          });

          setAvailableRoles(filteredRoles);
          // Si no hay rol seleccionado en formData ni en las props, inicializar con el primer rol disponible
          setFormData(prev => {
            const currentSlug = prev.role || role || (user?.role_slug || user?.role);
            if (currentSlug) {
              const matched = filteredRoles.find(r => r.slug === currentSlug || r.role_id === prev.role_id);
              if (matched) {
                return { ...prev, role: matched.slug, role_id: matched.role_id };
              }
            }
            const fallbackRole = filteredRoles[0] || { slug: 'user', role_id: null };
            return {
              ...prev,
              role: fallbackRole.slug,
              role_id: fallbackRole.role_id
            };
          });
        }
      } catch (err) {
        console.error('No se pudieron cargar roles dinámicos:', err);
      }
    };
    fetchRoles();
  }, [role, user, isAdmin]);

  useEffect(() => {
    if (user) {
      setFormData({
        user_id: user.user_id || '',
        username: user.username || '',
        email: user.email || '',
        password: '',
        full_name: user.full_name || '',
        role_id: user.role_id || null,
        role: user.role_slug || user.role || '',
        is_active: user.is_active !== undefined ? user.is_active : true,
        is_locked: user.is_locked || false,
        failed_login_attempts: user.failed_login_attempts || 0
      });
    }
  }, [user]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (name === 'role') {
      const selected = availableRoles.find(r => r.slug === value || String(r.role_id) === String(value));
      setFormData(prev => ({
        ...prev,
        role: selected ? selected.slug : value,
        role_id: selected ? selected.role_id : prev.role_id
      }));
      return;
    }
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      if (user) {
        const updateData = { ...formData };
        if (!updateData.password || updateData.password.trim() === '') delete updateData.password;
        await adminService.updateUser(user.user_id, updateData);
      } else {
        const createData = { ...formData };
        if (!createData.user_id || createData.user_id === '') delete createData.user_id;
        else createData.user_id = parseInt(createData.user_id, 10);
        delete createData.is_locked;
        delete createData.failed_login_attempts;

        // Asegurar vinculación del rol dinámico
        const selectedRoleObj = availableRoles.find(
          r => (createData.role && r.slug === createData.role) || (createData.role_id && r.role_id === createData.role_id)
        );
        if (selectedRoleObj) {
          createData.role_id = selectedRoleObj.role_id;
          createData.role = selectedRoleObj.slug;
        }

        await adminService.createUser(createData);
      }
      if (onSaved) onSaved();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al guardar el usuario.');
      console.error('Failed to save user:', err);
    } finally { setLoading(false); }
  };

  const getRoleLabel = () => {
    const currentSlug = formData.role || role;
    const currentRoleId = formData.role_id;
    const foundRole = availableRoles.find(
      r => (currentSlug && r.slug === currentSlug) || (currentRoleId && r.role_id === currentRoleId)
    );
    if (foundRole) return foundRole.name;
    if (user?.role_name) return user.role_name;
    return currentSlug || 'Usuario';
  };

  const selectedRoleObj = availableRoles.find(
    r => (formData.role && r.slug === formData.role) || (formData.role_id && r.role_id === formData.role_id)
  );
  const isAdminRole = selectedRoleObj?.slug === 'admin' || formData.role === 'admin';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2>{user ? `Editar ${getRoleLabel()}` : `Añadir ${getRoleLabel()}`}</h2>
          <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">&times;</button>
        </div>
        <div className="modal__body">
          {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

          <form onSubmit={handleSubmit} className="modal__form">
            {!user && (
              <div className="form-group">
                <label className="form-group__label" htmlFor="user_id">ID (opcional)</label>
                <input className="input" type="number" id="user_id" name="user_id" value={formData.user_id} onChange={handleChange} disabled={loading} placeholder="Auto-generado si se deja vacío" min="1" />
                <small className="form-group__hint">
                  {isAdminRole
                    ? 'Rango reservado para Administradores: 15,000,000+'
                    : 'Cualquier ID disponible (1 a 14,999,999) o auto-generado si se deja vacío'}
                </small>
              </div>
            )}
            <div className="form-group">
              <label className="form-group__label" htmlFor="role">Rol del Usuario *</label>
              <select
                className="input"
                id="role"
                name="role"
                value={formData.role || (availableRoles[0]?.slug || '')}
                onChange={handleChange}
                disabled={loading}
                required
              >
                {availableRoles.length > 0 ? (
                  availableRoles.map(r => (
                    <option key={r.role_id || r.slug} value={r.slug}>
                      {r.name} ({r.slug})
                    </option>
                  ))
                ) : (
                  <option value="">Cargando roles disponibles...</option>
                )}
              </select>
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="full_name">Nombre Completo *</label>
              <input className="input" type="text" id="full_name" name="full_name" value={formData.full_name} onChange={handleChange} required disabled={loading} />
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="username">Usuario *</label>
              <input className="input" type="text" id="username" name="username" value={formData.username} onChange={handleChange} required disabled={loading} />
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="email">Email *</label>
              <input className="input" type="email" id="email" name="email" value={formData.email} onChange={handleChange} required disabled={loading} />
            </div>
            <div className="form-group">
              <label className="form-group__label" htmlFor="password">
                Contraseña {user ? '(dejar vacío para no cambiar)' : '*'}
              </label>
              <input className="input" type="password" id="password" name="password" value={formData.password} onChange={handleChange} required={!user} disabled={loading} placeholder={user ? 'Dejar vacío para mantener la actual' : 'Ingresa una contraseña'} />
            </div>
            <div className="form-group form-group--checkbox">
              <label>
                <input className="checkbox" type="checkbox" name="is_active" checked={formData.is_active} onChange={handleChange} disabled={loading} />
                {' '}Usuario Activo
              </label>
            </div>

            {user && (
              <div className={`alert ${formData.is_locked ? 'alert--danger' : 'alert--info'} flex-col w-full mt-3 mb-2`}>
                <div className="flex items-center justify-between w-full">
                  <span className="font-semibold text-sm">
                    {formData.is_locked ? '🔒 Cuenta Bloqueada por Intentos' : '🛡️ Estado de Seguridad'}
                  </span>
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-medium" htmlFor="user_failed_attempts">
                      Intentos fallidos:
                    </label>
                    <input
                      id="user_failed_attempts"
                      className="input input--sm input--qty"
                      type="number"
                      name="failed_login_attempts"
                      min="0"
                      max="10"
                      value={formData.failed_login_attempts ?? 0}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        const safeVal = isNaN(val) ? 0 : Math.max(0, val);
                        setFormData(prev => ({
                          ...prev,
                          failed_login_attempts: safeVal,
                          is_locked: safeVal >= 5 ? true : (safeVal === 0 ? false : prev.is_locked)
                        }));
                      }}
                      disabled={loading}
                    />
                  </div>
                </div>
                <div className="form-group form-group--checkbox m-0 mt-2">
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      className="checkbox"
                      type="checkbox"
                      name="is_locked"
                      checked={formData.is_locked}
                      onChange={(e) => {
                        const locked = e.target.checked;
                        setFormData(prev => ({
                          ...prev,
                          is_locked: locked,
                          failed_login_attempts: locked ? Math.max(prev.failed_login_attempts || 0, 5) : 0
                        }));
                      }}
                      disabled={loading}
                    />
                    <span>{formData.is_locked ? 'Cuenta bloqueada (desmarca para desbloquear)' : 'Bloquear cuenta manualmente'}</span>
                  </label>
                </div>
              </div>
            )}
            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={onClose} disabled={loading}>Cancelar</button>
              <button type="submit" className="btn btn--primary" disabled={loading}>{loading ? 'Guardando...' : 'Guardar'}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
