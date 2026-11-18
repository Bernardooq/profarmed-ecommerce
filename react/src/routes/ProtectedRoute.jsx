import { Navigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import usePermissions from '../hooks/usePermissions';
import LoadingSpinner from '../components/common/LoadingSpinner';

const NOINDEX_HELMET = (
  <Helmet>
    <meta name="robots" content="noindex, nofollow, noarchive" />
    <meta name="googlebot" content="noindex, nofollow, noarchive" />
  </Helmet>
);

/**
 * ProtectedRoute: Enrutador de protección perimetral.
 * Soporta tanto 'allowedRoles' (roles legacy/actuales) como 'permission' (permisos PBAC dinámicos).
 */
export default function ProtectedRoute({ children, allowedRoles = [], permission = null }) {
  const { isAuthenticated, loading, hasRole, can } = usePermissions();

  // 1. Cargando sesión
  if (loading) {
    return (
      <>
        {NOINDEX_HELMET}
        <LoadingSpinner message="Verificando sesión..." />
      </>
    );
  }

  // 2. No autenticado -> redirigir a Login
  if (!isAuthenticated) {
    return (
      <>
        {NOINDEX_HELMET}
        <Navigate to="/login" replace />
      </>
    );
  }

  // 3. Validación por permiso granular PBAC (futuro)
  if (permission && !can(permission)) {
    return (
      <>
        {NOINDEX_HELMET}
        <div className="access-denied card p-8 m-8 text-center max-w-md mx-auto">
          <h1 className="text-xl font-bold text-danger mb-2">Acceso Denegado</h1>
          <p className="text-muted mb-4">No cuentas con los permisos requeridos para acceder a este módulo ({permission}).</p>
          <a href="/" className="btn btn--primary btn--sm inline-flex">Volver al inicio</a>
        </div>
      </>
    );
  }

  // 4. Validación por rol legacy / actual
  if (allowedRoles.length > 0 && !hasRole(allowedRoles)) {
    return (
      <>
        {NOINDEX_HELMET}
        <div className="access-denied card p-8 m-8 text-center max-w-md mx-auto">
          <h1 className="text-xl font-bold text-danger mb-2">Acceso Denegado</h1>
          <p className="text-muted mb-4">No tienes los privilegios asignados para acceder a esta página.</p>
          <a href="/" className="btn btn--primary btn--sm inline-flex">Volver al inicio</a>
        </div>
      </>
    );
  }

  return (
    <>
      {NOINDEX_HELMET}
      {children}
    </>
  );
}
