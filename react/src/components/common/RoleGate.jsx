import usePermissions from '../../hooks/usePermissions';

/**
 * Componente declarativo para renderizado condicional por rol.
 * Uso:
 *   <RoleGate allowed={['admin', 'marketing']}>
 *       <button>Asignar Vendedor</button>
 *   </RoleGate>
 */
export default function RoleGate({ allowed, permission, children, fallback = null }) {
    const { hasRole, can } = usePermissions();

    // 1. Si se define permiso (evaluado dinámicamente contra backend o mapeo RBAC)
    if (permission) {
        return can(permission) ? children : fallback;
    }

    // 2. Si se evalúa solo por rol estático
    if (allowed) {
        return hasRole(allowed) ? children : fallback;
    }

    return children;
}
