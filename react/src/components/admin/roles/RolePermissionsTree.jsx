import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLink } from '@fortawesome/free-solid-svg-icons';
import { PERMISSION_METADATA } from '../../../config/permissionMetadata';
import { MODULE_CONFIG } from './roleFormConstants';

export default function RolePermissionsTree({
  searchTerm,
  activeModule,
  selectAllInModule,
  deselectAllInModule,
  loading,
  hierarchicalPermissions,
  selectedPermissions,
  togglePermission,
  catalogByCode
}) {
  // Helper recursivo para renderizar ramas dependientes a cualquier profundidad
  const renderChildBranch = (childNode, depth = 1) => {
    const child = childNode.perm;
    const isChildSelected = selectedPermissions.has(child.permission_code);
    const childMeta = PERMISSION_METADATA[child.permission_code];
    const hasSubChildren = childNode.children && childNode.children.length > 0;

    return (
      <div key={child.permission_code} className={`role-modal__child-branch role-modal__child-branch--depth-${depth}`}>
        <label
          className={`role-modal__child-item ${isChildSelected ? 'role-modal__child-item--selected' : ''}`}
        >
          <input
            type="checkbox"
            checked={isChildSelected}
            onChange={() => togglePermission(child.permission_code)}
            className="role-modal__child-checkbox"
          />
          <div className="role-modal__perm-content">
            <div className="role-modal__perm-header">
              <span className="role-modal__child-name">{childMeta?.label || child.name}</span>
              <code className="role-modal__perm-code">
                {child.permission_code}
              </code>
              {childMeta?.actionTag && (
                <span className="role-modal__action-tag role-modal__action-tag--child">
                  ⚡ {childMeta.actionTag}
                </span>
              )}
              {childMeta?.scope && (
                <span className="role-modal__scope-badge role-modal__scope-badge--child">
                  📍 {childMeta.scope}
                </span>
              )}
            </div>
            <p className="role-modal__perm-desc">
              {childMeta?.description || child.description}
            </p>
          </div>
        </label>

        {/* Sub-hijos dependientes recursivos */}
        {hasSubChildren && (
          <div className="role-modal__children-tree role-modal__children-tree--sub">
            <div className="role-modal__children-title">
              ↳ Capacidades que dependen de {childMeta?.label || child.name}:
            </div>
            {childNode.children.map(subChildNode => renderChildBranch(subChildNode, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="role-modal__perms-tree">
      {/* Cabecera del módulo activo */}
      {!searchTerm.trim() && (
        <div className="role-modal__module-banner">
          <div>
            <b className="role-modal__module-banner-title">{MODULE_CONFIG[activeModule]?.label || activeModule}</b>
            {MODULE_CONFIG[activeModule]?.description && (
              <div className="role-modal__module-banner-desc">
                {MODULE_CONFIG[activeModule].description}
              </div>
            )}
          </div>
          <div className="role-modal__module-banner-actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => selectAllInModule(activeModule)}
            >
              Marcar Módulo
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => deselectAllInModule(activeModule)}
            >
              Desmarcar
            </button>
          </div>
        </div>
      )}

      {/* Lista de permisos */}
      {loading ? (
        <div className="role-modal__empty">
          Cargando catálogo de permisos...
        </div>
      ) : hierarchicalPermissions.length === 0 ? (
        <div className="role-modal__empty">
          No se encontraron permisos coincidentes.
        </div>
      ) : (
        hierarchicalPermissions.map(({ perm: root, children }) => {
          const isRootSelected = selectedPermissions.has(root.permission_code);
          const hasDependsOn = Boolean(root.depends_on);
          const parentObj = hasDependsOn ? catalogByCode[root.depends_on] : null;
          const rootMeta = PERMISSION_METADATA[root.permission_code];

          return (
            <div
              key={root.permission_code}
              className={`role-modal__perm-card ${isRootSelected ? 'role-modal__perm-card--selected' : ''}`}
            >
              {/* Permiso Principal / Raíz */}
              <label className="role-modal__perm-label">
                <input
                  type="checkbox"
                  checked={isRootSelected}
                  onChange={() => togglePermission(root.permission_code)}
                  className="role-modal__perm-checkbox"
                />
                <div className="role-modal__perm-content">
                  <div className="role-modal__perm-header">
                    <span className="role-modal__perm-name">{rootMeta?.label || root.name}</span>
                    <code className="role-modal__perm-code">
                      {root.permission_code}
                    </code>
                    {rootMeta?.actionTag && (
                      <span className="role-modal__action-tag">
                        ⚡ {rootMeta.actionTag}
                      </span>
                    )}
                    {rootMeta?.scope && (
                      <span className="role-modal__scope-badge">
                        📍 {rootMeta.scope}
                      </span>
                    )}
                    {hasDependsOn && (
                      <span className="badge badge--warning text-xs role-modal__perm-badge">
                        <FontAwesomeIcon icon={faLink} size="xs" /> Requiere: {parentObj?.name || root.depends_on}
                      </span>
                    )}
                  </div>
                  <p className="role-modal__perm-desc">
                    {rootMeta?.description || root.description}
                  </p>
                </div>
              </label>

              {/* Sub-permisos Jerárquicos Dependientes (Recursivos) */}
              {children.length > 0 && (
                <div className="role-modal__children-tree">
                  <div className="role-modal__children-title">
                    ↳ Capacidades que dependen de {rootMeta?.label || root.name}:
                  </div>
                  {children.map(childNode => renderChildBranch(childNode, 1))}
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
