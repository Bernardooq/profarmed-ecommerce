import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLock } from '@fortawesome/free-solid-svg-icons';

export default function RoleMetaFields({
  isAdminRole,
  formData,
  setFormData,
  handleNameChange,
  handleSlugChange,
  saving
}) {
  return (
    <>
      {/* Aviso especial de rol Administrador General */}
      {isAdminRole && (
        <div className="role-modal__protected-notice">
          <FontAwesomeIcon icon={faLock} className="role-modal__protected-icon" />
          <div className="role-modal__protected-text">
            <strong>Rol Protegido del Sistema:</strong> El nombre, identificador (slug), descripción y estado activo del <strong>Administrador General</strong> son inmutables para garantizar la integridad operativa. Solo puedes modificar y guardar su matriz de permisos granulares.
          </div>
        </div>
      )}

      {/* Datos Principales del Rol - Layout Compacto */}
      <div className="role-modal__meta-compact">
        <div className="role-modal__meta-row">
          <div className="role-modal__field role-modal__field--name">
            <label className="role-modal__label" htmlFor="role_name">
              Nombre del Rol <span className="role-modal__required">*</span>
            </label>
            <input
              id="role_name"
              type="text"
              className="input input--sm role-modal__input"
              placeholder="Ej: Supervisor de Almacén, Auditor, Vendedor Sr..."
              value={formData.name}
              onChange={handleNameChange}
              disabled={saving || isAdminRole}
              required
            />
            {isAdminRole && (
              <small className="role-modal__hint-locked">
                🔒 Nombre inmutable
              </small>
            )}
          </div>

          <div className="role-modal__field role-modal__field--slug">
            <label className="role-modal__label" htmlFor="role_slug">
              Slug <span className="role-modal__required">*</span>
              <span className="role-modal__label-hint">(minúsculas, ej: supervisor_almacen)</span>
            </label>
            <input
              id="role_slug"
              type="text"
              className="input input--sm role-modal__slug-input"
              placeholder="ej: supervisor_almacen"
              value={formData.slug}
              onChange={handleSlugChange}
              disabled={saving || isAdminRole}
              required
            />
          </div>

          <div className="role-modal__field role-modal__field--toggle">
            <label className="role-modal__label">Estado Operativo</label>
            <label
              htmlFor="role_active"
              className={`role-modal__toggle-pill ${formData.is_active ? 'role-modal__toggle-pill--active' : ''}`}
            >
              <input
                id="role_active"
                type="checkbox"
                checked={isAdminRole ? true : formData.is_active}
                onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                disabled={saving || isAdminRole}
              />
              <span>{isAdminRole ? '🔒 Rol Activo (Sistema)' : (formData.is_active ? 'Rol Activo' : 'Inactivo')}</span>
            </label>
          </div>
        </div>

        <div className="role-modal__meta-row role-modal__meta-row--desc">
          <div className="role-modal__field role-modal__field--full">
            <label className="role-modal__label" htmlFor="role_desc">
              Descripción del Rol
            </label>
            <input
              id="role_desc"
              type="text"
              className="input input--sm role-modal__input"
              placeholder="Breve resumen de responsabilidades y alcance operativo de este rol..."
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              disabled={saving || isAdminRole}
            />
          </div>
        </div>
      </div>
    </>
  );
}
