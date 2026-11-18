import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import authService from '../../services/authService';
import promoAdService from '../../services/promoAdService';

export default function LoginForm({ onViewChange }) {
  const { login } = useAuth();
  const navigate = useNavigate();

  // Estados de vista: 'login' | 'forgot_request' | 'forgot_verify' | 'forgot_new_password' | 'forgot_success'
  const [view, setViewState] = useState('login');

  const setView = (newView) => {
    setViewState(newView);
    if (onViewChange) {
      onViewChange(newView);
    }
  };

  // Campos de formulario
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Campos de recuperación
  const [resetCode, setResetCode] = useState('');
  const [maskedEmails, setMaskedEmails] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Estados de interfaz
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  // ============================================
  // MANEJADORES DE LOGIN
  // ============================================
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(username, password);
      if (user?.role === 'customer' || user?.user_type === 'customer') {
        try {
          const ads = await promoAdService.getActiveAds();
          navigate(ads?.has_ads ? '/novedades' : '/products');
        } catch {
          navigate('/products');
        }
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.message || 'Usuario o contraseña incorrectos');
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // MANEJADORES DE RECUPERACIÓN DE CONTRASEÑA
  // ============================================

  // 1. Solicitar código por username
  const handleRequestCode = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (!username.trim()) {
      setError('Por favor ingresa tu nombre de usuario');
      return;
    }

    setLoading(true);
    try {
      const res = await authService.requestPasswordResetCode(username.trim());
      setMaskedEmails(res.masked_emails || '');
      setSuccessMsg(res.message || 'Código enviado correctamente');
      setResetCode('');
      setView('forgot_verify');
    } catch (err) {
      setError(err.message || 'No se pudo enviar el código de recuperación');
    } finally {
      setLoading(false);
    }
  };

  // 2. Reenviar código
  const handleResendCode = async () => {
    setError('');
    setSuccessMsg('');
    setResending(true);

    try {
      const res = await authService.resendPasswordResetCode(username.trim());
      setSuccessMsg(res.message || 'Nuevo código generado y enviado');
    } catch (err) {
      setError(err.message || 'Error al reenviar el código');
    } finally {
      setResending(false);
    }
  };

  // 3. Verificar código de 6 dígitos
  const handleVerifyCode = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (!resetCode.trim()) {
      setError('Por favor ingresa el código de 6 dígitos');
      return;
    }

    setLoading(true);
    try {
      await authService.verifyPasswordResetCode(username.trim(), resetCode.trim());
      setSuccessMsg('Código validado con éxito. Ahora define tu nueva contraseña.');
      setView('forgot_new_password');
    } catch (err) {
      setError(err.message || 'Código de verificación incorrecto o expirado');
    } finally {
      setLoading(false);
    }
  };

  // 4. Confirmar nueva contraseña
  const handleConfirmPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (newPassword.length < 6) {
      setError('La nueva contraseña debe tener al menos 6 caracteres');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }

    setLoading(true);
    try {
      await authService.confirmPasswordReset(username.trim(), resetCode.trim(), newPassword);
      setView('forgot_success');
    } catch (err) {
      setError(err.message || 'No se pudo actualizar la contraseña');
    } finally {
      setLoading(false);
    }
  };

  // Volver a estado login inicial
  const resetToLogin = () => {
    setError('');
    setSuccessMsg('');
    setPassword('');
    setResetCode('');
    setNewPassword('');
    setConfirmPassword('');
    setView('login');
  };

  // ============================================
  // RENDERIZADO CONDICIONAL POR PASO
  // ============================================

  // --- VISTA 5: ÉXITO DEFINITIVO ---
  if (view === 'forgot_success') {
    return (
      <div className="login-form__success-card">
        <span className="success-icon" role="img" aria-label="Éxito">🎉</span>
        <h3>¡Contraseña Actualizada!</h3>
        <p>Tu contraseña ha sido restablecida exitosamente. Ya puedes iniciar sesión con tus nuevas credenciales.</p>
        <button type="button" className="btn btn--primary btn--block" onClick={resetToLogin}>
          Volver a Iniciar Sesión
        </button>
      </div>
    );
  }

  // --- VISTA 4: INGRESAR NUEVA CONTRASEÑA ---
  if (view === 'forgot_new_password') {
    return (
      <form className="login-form" onSubmit={handleConfirmPassword}>
        <div className="auth-card__subtitle">
          Define una nueva contraseña segura para la cuenta <strong>{username}</strong>.
        </div>

        {error && <div className="alert alert--danger">{error}</div>}
        {successMsg && <div className="alert alert--success">{successMsg}</div>}

        <div className="form-group">
          <label className="form-group__label" htmlFor="newPassword">Nueva Contraseña:</label>
          <input
            className="input"
            type={showNewPassword ? 'text' : 'password'}
            id="newPassword"
            placeholder="Mínimo 6 caracteres"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            disabled={loading}
            autoFocus
          />
        </div>

        <div className="form-group">
          <label className="form-group__label" htmlFor="confirmPassword">Confirmar Contraseña:</label>
          <input
            className="input"
            type={showNewPassword ? 'text' : 'password'}
            id="confirmPassword"
            placeholder="Repite tu nueva contraseña"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            disabled={loading}
          />
        </div>

        <div className="form-group form-group--checkbox">
          <input
            className="checkbox"
            type="checkbox"
            id="showNewPass"
            checked={showNewPassword}
            onChange={(e) => setShowNewPassword(e.target.checked)}
          />
          <label htmlFor="showNewPass">Mostrar contraseñas</label>
        </div>

        <div className="login-form__actions">
          <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
            {loading ? 'Guardando...' : 'Guardar nueva contraseña'}
          </button>
          <button type="button" className="btn btn--outline btn--block" onClick={resetToLogin} disabled={loading}>
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  // --- VISTA 3: VERIFICAR CÓDIGO OTP ---
  if (view === 'forgot_verify') {
    return (
      <form className="login-form" onSubmit={handleVerifyCode}>
        <div className="auth-card__subtitle">
          Ingresa el código de 6 dígitos que enviamos a tu correo.
        </div>

        {maskedEmails && (
          <div className="login-form__masked-box">
            <span>✉️ Correo(s) de destino:</span>
            <span className="masked-emails">{maskedEmails}</span>
          </div>
        )}

        {error && <div className="alert alert--danger">{error}</div>}
        {successMsg && <div className="alert alert--success">{successMsg}</div>}

        <div className="form-group">
          <label className="form-group__label text-center" htmlFor="resetCode">
            Código de Verificación (5 min):
          </label>
          <input
            className="input login-form__code-input"
            type="text"
            id="resetCode"
            maxLength={6}
            placeholder="000000"
            value={resetCode}
            onChange={(e) => setResetCode(e.target.value.replace(/[^0-9]/g, ''))}
            required
            disabled={loading}
            autoFocus
          />
        </div>

        <div className="login-form__resend-row">
          <span>¿No recibiste el correo?</span>
          <button
            type="button"
            className="login-form__forgot-link"
            onClick={handleResendCode}
            disabled={loading || resending}
          >
            {resending ? 'Reenviando...' : '⚡ Reenviar código'}
          </button>
        </div>

        <div className="login-form__actions">
          <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
            {loading ? 'Verificando...' : 'Verificar código'}
          </button>
          <button
            type="button"
            className="btn btn--outline btn--block"
            onClick={() => {
              setError('');
              setSuccessMsg('');
              setView('forgot_request');
            }}
            disabled={loading}
          >
            Cambiar usuario
          </button>
        </div>
      </form>
    );
  }

  // --- VISTA 2: SOLICITAR CÓDIGO POR USERNAME ---
  if (view === 'forgot_request') {
    return (
      <form className="login-form" onSubmit={handleRequestCode}>
        <div className="auth-card__subtitle">
          Ingresa tu usuario para recibir un código de restablecimiento en tu correo registrado.
        </div>

        {error && <div className="alert alert--danger">{error}</div>}
        {successMsg && <div className="alert alert--success">{successMsg}</div>}

        <div className="form-group">
          <label className="form-group__label" htmlFor="forgotUsername">Nombre de Usuario:</label>
          <input
            className="input"
            type="text"
            id="forgotUsername"
            placeholder="ej. cliente_01 o asesor.demo"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={loading}
            autoFocus
          />
        </div>

        <div className="login-form__actions">
          <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
            {loading ? 'Verificando cuenta...' : 'Enviar código de recuperación'}
          </button>
          <button type="button" className="btn btn--outline btn--block" onClick={resetToLogin} disabled={loading}>
            Volver al inicio de sesión
          </button>
        </div>
      </form>
    );
  }

  // --- VISTA 1: LOGIN ESTÁNDAR ---
  return (
    <form className="login-form" onSubmit={handleLoginSubmit}>
      {error && (
        <div className="alert alert--danger">
          <div>
            <span>{error}</span>
            {(error.toLowerCase().includes('bloqueada') || error.toLowerCase().includes('intentos permitidos') || error.toLowerCase().includes('límite de')) && (
              <button
                type="button"
                className="login-form__alert-action"
                onClick={() => {
                  setError('');
                  setSuccessMsg('');
                  setView('forgot_request');
                }}
              >
                Restablecer mi contraseña ahora →
              </button>
            )}
          </div>
        </div>
      )}

      <div className="form-group">
        <label className="form-group__label" htmlFor="username">Usuario</label>
        <input
          className="input"
          type="text"
          id="username"
          name="username"
          placeholder="ejemplo.usuario"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          disabled={loading}
          autoComplete="username"
        />
      </div>

      <div className="form-group">
        <label className="form-group__label" htmlFor="password">Contraseña</label>
        <input
          className="input"
          type={showPassword ? 'text' : 'password'}
          id="password"
          name="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={loading}
          autoComplete="current-password"
        />
      </div>

      <div className="form-group form-group--checkbox">
        <input
          className="checkbox"
          type="checkbox"
          id="showPass"
          checked={showPassword}
          onChange={(e) => setShowPassword(e.target.checked)}
        />
        <label htmlFor="showPass">Mostrar contraseña</label>
      </div>

      {/* Botón Olvidé contraseña */}
      <div className="login-form__forgot-container" style={{ marginTop: 0 }}>
        <button
          type="button"
          className="login-form__forgot-link"
          onClick={() => {
            setError('');
            setSuccessMsg('');
            setView('forgot_request');
          }}
          disabled={loading}
        >
          Olvidé contraseña
        </button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 'var(--space-2)' }}>
        <button type="submit" className="btn btn--primary" disabled={loading} style={{ minWidth: '160px' }}>
          {loading ? 'Ingresando...' : 'Ingresar'}
        </button>
      </div>
    </form>
  );
}