import { useAuth } from '../context/AuthContext';
import { PERMISSIONS, STOREFRONT_PERMISSIONS } from '../config/permissions';

/**
 * Hook universal de permisos y roles (PBAC / RBAC).
 * Sincronizado con PERMISSIONS_AND_CONSTRAINTS.md y react/src/config/permissions.js
 */
export function usePermissions() {
    const { user, isAuthenticated } = useAuth();
    const role = user?.role || null;

    // Identidad y tipo de cuenta canónica (Cliente B2B Storefront vs Personal Interno)
    const isCustomer = user?.user_type === 'customer' || role === 'customer';
    const isStaff = !isCustomer && Boolean(isAuthenticated);

    // Superadministrador: por rol 'admin' O por poseer el permiso maestro 'system.admin'
    const isAdmin = role === 'admin' || Boolean(user?.permissions?.includes(PERMISSIONS.SYSTEM_ADMIN));

    // Helpers
    const hasRole = (allowedRoles) => {
        if (!Array.isArray(allowedRoles)) allowedRoles = [allowedRoles];
        return allowedRoles.includes(role);
    };

    const getDashboardPath = () => {
        if (isCustomer) return '/products';
        return '/dashboard';
    };

    /**
     * Evaluación de permisos PBAC / RBAC:
     * 1. Si no está autenticado -> denegado.
     * 2. Si es admin -> acceso total (superadmin).
     * 3. Si es cliente (customer) y el permiso es del Storefront -> concedido de inmediato.
     * 4. Evaluación PBAC directa O(1) contra user.permissions inyectado desde el JWT/Backend.
     */
    const can = (permissionCode) => {
        if (!isAuthenticated || !role) return false;
        
        // 1. Superadmin tiene todos los permisos
        if (isAdmin) return true;

        // 2. Si es cliente y el permiso pertenece al storefront de compras/tienda B2B
        if (isCustomer) {
            if (STOREFRONT_PERMISSIONS.includes(permissionCode)) return true;
        }

        // 3. Evaluación PBAC directa: permisos enviados por el backend en JWT/sesión
        return Array.isArray(user?.permissions) && user.permissions.includes(permissionCode);
    };

    /**
     * Evalúa si el usuario cumple con AL MENOS UNO de los permisos solicitados.
     */
    const canAny = (permissionCodes = []) => {
        return permissionCodes.some((code) => can(code));
    };

    /**
     * Evalúa si el usuario cumple con TODOS los permisos solicitados.
     */
    const canAll = (permissionCodes = []) => {
        return permissionCodes.every((code) => can(code));
    };

    return {
        user,
        role,
        isAuthenticated,
        isAdmin,
        isCustomer,
        isStaff,
        hasRole,
        can,
        canAny,
        canAll,
        getDashboardPath,
        PERMISSIONS
    };
}

export default usePermissions;
