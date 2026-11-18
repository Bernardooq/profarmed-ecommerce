import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faShieldAlt } from '@fortawesome/free-solid-svg-icons';
import { MODULE_CONFIG } from './roleFormConstants';

export default function RoleModulesNav({
  moduleKeys,
  activeModule,
  setActiveModule,
  modulesMap,
  selectedPermissions
}) {
  return (
    <div className="role-modal__modules-nav">
      {moduleKeys.map(modKey => {
        const modCfg = MODULE_CONFIG[modKey] || { label: modKey, icon: faShieldAlt };
        const permsInMod = modulesMap[modKey] || [];
        const selectedInMod = permsInMod.filter(p => selectedPermissions.has(p.permission_code)).length;
        const isActive = activeModule === modKey;

        return (
          <button
            key={modKey}
            type="button"
            onClick={() => setActiveModule(modKey)}
            className={`role-modal__module-btn ${isActive ? 'role-modal__module-btn--active' : ''}`}
          >
            <div className="role-modal__module-btn-info">
              <FontAwesomeIcon icon={modCfg.icon} className="role-modal__module-btn-icon" />
              <span className="role-modal__module-btn-name">{modCfg.label}</span>
            </div>
            <span
              className={`badge ${selectedInMod > 0 ? (selectedInMod === permsInMod.length ? 'badge--success' : 'badge--primary') : 'badge--secondary'} role-modal__module-badge`}
            >
              {selectedInMod}/{permsInMod.length}
            </span>
          </button>
        );
      })}
    </div>
  );
}
