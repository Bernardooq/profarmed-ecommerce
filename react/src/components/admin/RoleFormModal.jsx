import { useState, useEffect, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faShieldAlt, faSave, faSearch } from '@fortawesome/free-solid-svg-icons';
import adminService from '../../services/adminService';
import ErrorMessage from '../common/ErrorMessage';
import { PERMISSION_METADATA } from '../../config/permissionMetadata';

import {
  CANONICAL_MODULE_ORDER,
  CANONICAL_PERMISSION_ORDER,
  PERMISSION_TO_MODULE,
  MODULE_CONFIG
} from './roles/roleFormConstants';
import RoleMetaFields from './roles/RoleMetaFields';
import RoleModulesNav from './roles/RoleModulesNav';
import RolePermissionsTree from './roles/RolePermissionsTree';

export default function RoleFormModal({ role, onClose, onSaved }) {
  const isEditing = Boolean(role);
  const isAdminRole = Boolean(role && (role.slug === 'admin' || role.role_id === 1));

  const [formData, setFormData] = useState({
    name: isAdminRole ? 'Administrador General' : (role?.name || ''),
    slug: isAdminRole ? 'admin' : (role?.slug || ''),
    description: isAdminRole ? (role?.description || 'Control total y acceso irrestricto sobre todos los módulos operativos y de sistema.') : (role?.description || ''),
    is_active: isAdminRole ? true : (role?.is_active !== undefined ? role.is_active : true),
  });

  const [slugManuallyEdited, setSlugManuallyEdited] = useState(isEditing);
  const [catalog, setCatalog] = useState([]);
  const [selectedPermissions, setSelectedPermissions] = useState(new Set(role?.permissions || []));
  const [activeModule, setActiveModule] = useState('orders');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Cargar catálogo maestro de permisos y detalle del rol si aplica
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [permsData, roleDetail] = await Promise.all([
          adminService.getPermissions(),
          role?.role_id ? adminService.getRoleById(role.role_id).catch(() => null) : null
        ]);

        if (!isMounted) return;

        const permsList = (Array.isArray(permsData) ? permsData : []).filter(
          p => p.module !== 'storefront' && !['cart.manage', 'storefront.favorites'].includes(p.permission_code)
        );
        setCatalog(permsList);

        if (roleDetail && Array.isArray(roleDetail.permissions)) {
          setSelectedPermissions(new Set(roleDetail.permissions));
        } else if (role?.permissions && Array.isArray(role.permissions)) {
          setSelectedPermissions(new Set(role.permissions));
        }

        // Seleccionar el primer módulo canónico disponible por defecto
        if (permsList.length > 0) {
          const availableMods = new Set(permsList.map(p => p.module));
          const firstMod = CANONICAL_MODULE_ORDER.find(m => availableMods.has(m)) || permsList[0].module;
          setActiveModule(firstMod);
        }
      } catch (err) {
        if (!isMounted) return;
        setError(err.response?.data?.detail || err.message || 'Error al cargar catálogo de permisos');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadData();
    return () => { isMounted = false; };
  }, [role]);

  // Generación automática de slug a partir del nombre
  const handleNameChange = (e) => {
    if (isAdminRole) return;
    const newName = e.target.value;
    setFormData(prev => {
      const updated = { ...prev, name: newName };
      if (!slugManuallyEdited && !isEditing) {
        updated.slug = newName
          .toLowerCase()
          .trim()
          .normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '')
          .replace(/[^a-z0-9]+/g, '_')
          .replace(/(^_|_$)/g, '');
      }
      return updated;
    });
  };

  const handleSlugChange = (e) => {
    if (isAdminRole) return;
    setSlugManuallyEdited(true);
    setFormData(prev => ({ ...prev, slug: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '') }));
  };

  // Mapa de permisos por módulo sincronizado con el mapeo canónico
  const modulesMap = useMemo(() => {
    const map = {};
    catalog.forEach(p => {
      const mod = PERMISSION_TO_MODULE[p.permission_code] || p.module || 'otros';
      if (!map[mod]) map[mod] = [];
      map[mod].push(p);
    });
    return map;
  }, [catalog]);

  const moduleKeys = useMemo(() => {
    const rawKeys = Object.keys(modulesMap).filter(k => k !== 'storefront');
    return rawKeys.sort((a, b) => {
      const idxA = CANONICAL_MODULE_ORDER.indexOf(a);
      const idxB = CANONICAL_MODULE_ORDER.indexOf(b);
      const posA = idxA === -1 ? 999 : idxA;
      const posB = idxB === -1 ? 999 : idxB;
      return posA - posB;
    });
  }, [modulesMap]);

  // Diccionario rápido de permisos por código
  const catalogByCode = useMemo(() => {
    const map = {};
    catalog.forEach(p => { map[p.permission_code] = p; });
    return map;
  }, [catalog]);

  // Manejador inteligente de dependencias (Bidireccional y Recursivo)
  const togglePermission = (code) => {
    const isCurrentlySelected = selectedPermissions.has(code);
    const updated = new Set(selectedPermissions);

    if (isCurrentlySelected) {
      // Al desmarcar: desmarcar este permiso y cualquier descendiente que dependa de él
      updated.delete(code);
      const removeDependents = (parentCode) => {
        catalog.forEach(p => {
          if (p.depends_on === parentCode && updated.has(p.permission_code)) {
            updated.delete(p.permission_code);
            removeDependents(p.permission_code);
          }
        });
      };
      removeDependents(code);
    } else {
      // Al marcar: marcar este permiso y asegurar que todos sus ancestros se marquen
      updated.add(code);
      const addAncestors = (childCode) => {
        const p = catalogByCode[childCode];
        if (p && p.depends_on) {
          updated.add(p.depends_on);
          addAncestors(p.depends_on);
        }
      };
      addAncestors(code);
    }

    setSelectedPermissions(updated);
  };

  // Acciones en lote por módulo
  const selectAllInModule = (mod) => {
    const perms = modulesMap[mod] || [];
    const updated = new Set(selectedPermissions);
    perms.forEach(p => {
      updated.add(p.permission_code);
      let curr = p;
      while (curr && curr.depends_on) {
        updated.add(curr.depends_on);
        curr = catalogByCode[curr.depends_on];
      }
    });
    setSelectedPermissions(updated);
  };

  const deselectAllInModule = (mod) => {
    const perms = modulesMap[mod] || [];
    const updated = new Set(selectedPermissions);
    const toRemoveCodes = perms.map(p => p.permission_code);

    toRemoveCodes.forEach(code => {
      updated.delete(code);
      const removeDependents = (parentCode) => {
        catalog.forEach(p => {
          if (p.depends_on === parentCode && updated.has(p.permission_code)) {
            updated.delete(p.permission_code);
            removeDependents(p.permission_code);
          }
        });
      };
      removeDependents(code);
    });

    setSelectedPermissions(updated);
  };

  // Acciones globales
  const selectAllGlobal = () => {
    setSelectedPermissions(new Set(catalog.map(p => p.permission_code)));
  };

  const deselectAllGlobal = () => {
    setSelectedPermissions(new Set());
  };

  // Permisos a mostrar según búsqueda o módulo activo
  const displayedPermissions = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (query) {
      return catalog.filter(p => {
        const meta = PERMISSION_METADATA[p.permission_code];
        const mod = PERMISSION_TO_MODULE[p.permission_code] || p.module || '';
        return (
          p.name.toLowerCase().includes(query) ||
          p.permission_code.toLowerCase().includes(query) ||
          (p.description && p.description.toLowerCase().includes(query)) ||
          (meta?.label && meta.label.toLowerCase().includes(query)) ||
          (meta?.actionTag && meta.actionTag.toLowerCase().includes(query)) ||
          (meta?.description && meta.description.toLowerCase().includes(query)) ||
          (meta?.scope && meta.scope.toLowerCase().includes(query)) ||
          mod.toLowerCase().includes(query)
        );
      });
    }
    return modulesMap[activeModule] || [];
  }, [catalog, modulesMap, activeModule, searchTerm]);

  // Estructura jerárquica para la vista del módulo
  const hierarchicalPermissions = useMemo(() => {
    const getPermOrder = (code) => {
      const idx = CANONICAL_PERMISSION_ORDER.indexOf(code);
      return idx === -1 ? 999 : idx;
    };

    if (searchTerm.trim()) {
      const sorted = [...displayedPermissions].sort(
        (a, b) => getPermOrder(a.permission_code) - getPermOrder(b.permission_code)
      );
      return sorted.map(p => ({ perm: p, children: [] }));
    }

    const currentList = modulesMap[activeModule] || [];
    const currentCodes = new Set(currentList.map(p => p.permission_code));
    const childrenMap = {};
    const hasParentInModule = new Set();

    currentList.forEach(p => {
      if (p.depends_on && currentCodes.has(p.depends_on)) {
        hasParentInModule.add(p.permission_code);
        if (!childrenMap[p.depends_on]) childrenMap[p.depends_on] = [];
        childrenMap[p.depends_on].push(p);
      }
    });

    const buildNode = (perm) => {
      const rawChildren = childrenMap[perm.permission_code] || [];
      rawChildren.sort((a, b) => getPermOrder(a.permission_code) - getPermOrder(b.permission_code));
      return {
        perm,
        children: rawChildren.map(buildNode)
      };
    };

    const roots = currentList.filter(p => !hasParentInModule.has(p.permission_code));
    roots.sort((a, b) => getPermOrder(a.permission_code) - getPermOrder(b.permission_code));

    return roots.map(buildNode);
  }, [displayedPermissions, modulesMap, activeModule, searchTerm]);

  // Guardar formulario
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (isAdminRole) {
      setSaving(true);
      setError(null);
      try {
        await adminService.updateRole(role.role_id, {
          permissions: Array.from(selectedPermissions)
        });
        if (onSaved) onSaved();
        onClose();
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Error al actualizar permisos del Administrador General.');
      } finally {
        setSaving(false);
      }
      return;
    }

    if (!formData.name.trim()) {
      setError('El nombre del rol es requerido.');
      return;
    }
    if (!formData.slug.trim()) {
      setError('El slug del rol es requerido.');
      return;
    }

    setSaving(true);
    setError(null);

    const payload = {
      name: formData.name.trim(),
      slug: formData.slug.trim(),
      description: formData.description?.trim() || null,
      is_active: formData.is_active,
      permissions: Array.from(selectedPermissions)
    };

    try {
      if (isEditing) {
        await adminService.updateRole(role.role_id, payload);
      } else {
        await adminService.createRole(payload);
      }
      if (onSaved) onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al guardar el rol.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal--lg role-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <div className="role-modal__header-content">
            <FontAwesomeIcon icon={faShieldAlt} className="role-modal__header-icon" />
            <div>
              <h2 className="role-modal__header-title">
                {isAdminRole ? 'Editar Permisos: Administrador General' : (isEditing ? `Editar Rol: ${role.name}` : 'Crear Nuevo Rol')}
              </h2>
              <small className="text-muted">
                {isAdminRole
                  ? 'Configuración granular de capacidades del rol maestro de administración'
                  : (isEditing ? `Identificador slug: ${role.slug}` : 'Define un rol personalizado y asigna sus permisos granulares')}
              </small>
            </div>
          </div>
          <button className="modal__close" onClick={onClose} aria-label="Cerrar modal">&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal__body role-modal__body">
            {error && <ErrorMessage error={error} onDismiss={() => setError(null)} />}

            {/* Metadatos del Rol (Nombre, slug, estado, descripción) */}
            <RoleMetaFields
              isAdminRole={isAdminRole}
              formData={formData}
              setFormData={setFormData}
              handleNameChange={handleNameChange}
              handleSlugChange={handleSlugChange}
              saving={saving}
            />

            {/* Matriz y Jerarquía de Permisos */}
            <div className="role-modal__perms-section">
              {/* Barra superior de control de permisos */}
              <div className="role-modal__perms-toolbar">
                <div className="role-modal__perms-title-wrap">
                  <h3 className="role-modal__perms-heading">
                    Jerarquía de Permisos
                  </h3>
                  <span className="badge badge--primary role-modal__perms-counter">
                    {selectedPermissions.size} de {catalog.length} seleccionados
                  </span>
                </div>

                <div className="role-modal__perms-controls">
                  <div className="role-modal__search-box">
                    <FontAwesomeIcon
                      icon={faSearch}
                      className="role-modal__search-icon"
                    />
                    <input
                      type="search"
                      className="input role-modal__search-input"
                      placeholder="Buscar permiso..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    onClick={selectAllGlobal}
                    title="Marcar todos los permisos del sistema"
                  >
                    Marcar Todos
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary btn--sm"
                    onClick={deselectAllGlobal}
                    title="Desmarcar todos los permisos"
                  >
                    Limpiar
                  </button>
                </div>
              </div>

              {/* Contenedor Split: Módulos a la izquierda / Permisos jerárquicos a la derecha */}
              <div className={`role-modal__split ${searchTerm.trim() ? 'role-modal__split--searching' : ''}`}>
                {!searchTerm.trim() && (
                  <RoleModulesNav
                    moduleKeys={moduleKeys}
                    activeModule={activeModule}
                    setActiveModule={setActiveModule}
                    modulesMap={modulesMap}
                    selectedPermissions={selectedPermissions}
                  />
                )}

                <RolePermissionsTree
                  searchTerm={searchTerm}
                  activeModule={activeModule}
                  selectAllInModule={selectAllInModule}
                  deselectAllInModule={deselectAllInModule}
                  loading={loading}
                  hierarchicalPermissions={hierarchicalPermissions}
                  selectedPermissions={selectedPermissions}
                  togglePermission={togglePermission}
                  catalogByCode={catalogByCode}
                />
              </div>
            </div>
          </div>

          <div className="modal__footer">
            <button type="button" className="btn btn--secondary" onClick={onClose} disabled={saving}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--primary" disabled={saving || loading}>
              <FontAwesomeIcon icon={faSave} /> {saving ? 'Guardando...' : (isAdminRole ? 'Guardar Permisos' : (isEditing ? 'Actualizar Rol' : 'Crear Rol'))}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
