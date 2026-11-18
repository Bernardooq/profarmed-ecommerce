"""
CRUD y Lógica de Recuperación de Contraseña por Código OTP (Password Reset):

Funciones y Operaciones:
- Generación de código numérico aleatorio de 6 dígitos con validez de 5 minutos.
- Enmascaramiento seguro de correos electrónicos simples y múltiples (separados por ';').
- Solicitud / Reenvío de código para Clientes B2B ('customers') y Usuarios Internos ('users').
- Almacenamiento y UPSERT idempotente en la tabla 'password_resets'.
- Verificación de código y autorización de cambio mediante la bandera 'allow'.
- Confirmación y cambio definitivo de contraseña con hash seguro Argon2.
"""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from sqlalchemy.orm import Session
import logging

from db.base import PasswordReset, Customer, User
from crud.crud_customer import get_password_hash
from utils.email_utils import parse_recipient_emails, send_email_background

logger = logging.getLogger(__name__)


def generate_numeric_code(length: int = 6) -> str:
    """Genera un código numérico aleatorio criptográficamente seguro de 6 dígitos."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def mask_single_email(email: str) -> str:
    """
    Enmascara un correo electrónico mostrando solo la terminación.
    Ej: 'bernardo.orozco@gmail.com' -> '***zco@gmail.com'
    """
    email = email.strip()
    if "@" not in email:
        return "***"
    user_part, domain = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = "***" + user_part[-1:]
    elif len(user_part) <= 5:
        masked_user = "***" + user_part[-2:]
    else:
        masked_user = "***" + user_part[-3:]
    return f"{masked_user}@{domain}"


def mask_email_list(raw_email: str) -> str:
    """
    Enmascara una lista de correos separados por ';' o ','.
    Retorna los correos enmascarados unidos por coma.
    """
    if not raw_email:
        return ""
    emails = parse_recipient_emails(raw_email)
    if not emails:
        return ""
    return ", ".join(mask_single_email(e) for e in emails)


def build_password_reset_email_html(recipient_name: str, code: str, expires_minutes: int = 5) -> str:
    """Construye un correo HTML premium con el código OTP de restablecimiento."""
    year = datetime.now().year
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Código de Restablecimiento</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #0b1120;
            color: #f1f5f9;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 520px;
            margin: 0 auto;
            background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }}
        .header {{
            background: linear-gradient(135deg, #4F46E5 0%, #4338CA 100%);
            padding: 32px 24px;
            text-align: center;
        }}
        .header-title {{
            color: #ffffff;
            font-size: 22px;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.02em;
        }}
        .header-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.22);
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 4px 12px;
            border-radius: 9999px;
            margin-top: 8px;
        }}
        .body {{
            padding: 32px 28px;
        }}
        .greeting {{
            font-size: 16px;
            color: #e2e8f0;
            margin-bottom: 16px;
        }}
        .description {{
            font-size: 14px;
            line-height: 1.6;
            color: #94a3b8;
            margin-bottom: 24px;
        }}
        .code-box {{
            background: rgba(15, 23, 42, 0.8);
            border: 2px dashed #4F46E5;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin: 24px 0;
        }}
        .code {{
            font-size: 36px;
            font-weight: 800;
            letter-spacing: 8px;
            color: #818cf8;
            font-family: 'Courier New', monospace;
        }}
        .expiry-note {{
            font-size: 12px;
            color: #fbbf24;
            font-weight: 600;
            margin-top: 8px;
        }}
        .warning-box {{
            background: rgba(239, 68, 68, 0.1);
            border-left: 4px solid #ef4444;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            font-size: 12px;
            color: #fca5a5;
            margin-top: 24px;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #64748b;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            background: #0f172a;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="header-title">Recuperación de Contraseña</h1>
            <span class="header-badge">Profarmed &bull; Seguridad de la Cuenta</span>
        </div>
        <div class="body">
            <div class="greeting">Hola, <strong>{recipient_name}</strong>:</div>
            <div class="description">
                Has solicitado un código para restablecer la contraseña de tu cuenta. 
                Ingresa el siguiente código de 6 dígitos en la pantalla de verificación para continuar:
            </div>
            
            <div class="code-box">
                <div class="code">{code}</div>
                <div class="expiry-note">⏱️ Válido durante {expires_minutes} minutos</div>
            </div>

            <div class="warning-box">
                <strong>¿No solicitaste este cambio?</strong> Si no realizaste esta solicitud, puedes ignorar este correo de forma segura. Tu contraseña actual no será modificada.
            </div>
        </div>
        <div class="footer">
            &copy; {year} Profarmed. Todos los derechos reservados.<br>
            Este es un correo automatizado de seguridad. Por favor no respondas a este mensaje.
        </div>
    </div>
</body>
</html>"""


def request_password_reset_code(
    db: Session, 
    username: str
) -> Tuple[bool, str, Optional[str], Optional[int]]:
    """
    Genera y envía un código de 6 dígitos al correo del usuario (Customer o User interno).
    Guarda o upsertea el registro en 'password_resets' con ventana de expiración de 5 minutos.
    Retorna: (éxito, mensaje, correos_enmascarados, expiracion_segundos)
    """
    clean_username = username.strip()
    if not clean_username:
        return False, "Debes ingresar un nombre de usuario válido.", None, None

    # 1. Buscar en Customer
    customer = db.query(Customer).filter(Customer.username == clean_username).first()
    user = None
    if not customer:
        # 2. Buscar en User
        user = db.query(User).filter(User.username == clean_username).first()

    account = customer or user
    if not account:
        return False, f"El usuario '{clean_username}' no está registrado en el sistema.", None, None

    if not account.is_active:
        return False, "Esta cuenta se encuentra inactiva. Contacta al administrador.", None, None

    raw_email = getattr(account, "email", None)
    if not raw_email or not raw_email.strip():
        return False, "Esta cuenta no tiene un correo electrónico configurado para recibir códigos.", None, None

    # Validar que al menos un correo sea válido
    recipients = parse_recipient_emails(raw_email)
    if not recipients:
        return False, "La dirección de correo registrada en tu cuenta no tiene un formato válido.", None, None

    masked_emails = mask_email_list(raw_email)

    # 3. Generar código y timestamps (5 minutos)
    code = generate_numeric_code(6)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=5)

    # 4. UPSERT en password_resets
    existing_reset = db.query(PasswordReset).filter(PasswordReset.username == clean_username).first()
    if existing_reset:
        existing_reset.code = code
        existing_reset.allow = False
        existing_reset.created_at = now
        existing_reset.expires_at = expires_at
        existing_reset.updated_at = now
        existing_reset.customer_id = customer.customer_id if customer else None
        existing_reset.user_id = user.user_id if user else None
    else:
        new_reset = PasswordReset(
            customer_id=customer.customer_id if customer else None,
            user_id=user.user_id if user else None,
            username=clean_username,
            code=code,
            allow=False,
            created_at=now,
            expires_at=expires_at,
            updated_at=now
        )
        db.add(new_reset)

    db.commit()

    # 5. Enviar correo transaccional
    recipient_name = getattr(account, "full_name", None) or clean_username
    email_html = build_password_reset_email_html(recipient_name=recipient_name, code=code, expires_minutes=5)
    
    try:
        send_email_background(
            to_email=raw_email,
            subject=f"Código de Restablecimiento: {code} - Profarmed",
            html_body=email_html,
            brand_name="Profarmed"
        )
        logger.info(f"[PASSWORD-RESET] Código enviado a {raw_email} para usuario {clean_username}")
    except Exception as email_err:
        logger.error(f"[PASSWORD-RESET-ERROR] Falló el envío de correo a {raw_email}: {email_err}")

    return True, f"Se ha enviado un código de recuperación a: {masked_emails}", masked_emails, 300


def verify_password_reset_code(
    db: Session, 
    username: str, 
    code: str
) -> Tuple[bool, str]:
    """
    Valida si el código ingresado coincide y se encuentra dentro de los 5 minutos de vigencia.
    Si coincide, marca allow = True para autorizar el cambio de contraseña.
    """
    clean_username = username.strip()
    clean_code = code.strip()

    if not clean_code:
        return False, "Debes ingresar el código de verificación."

    reset_record = db.query(PasswordReset).filter(PasswordReset.username == clean_username).first()
    if not reset_record or not reset_record.code:
        return False, "No existe ninguna solicitud de restablecimiento activa para este usuario."

    now = datetime.now(timezone.utc)
    if now > reset_record.expires_at:
        return False, "El código de verificación ha expirado (límite de 5 minutos). Solicita un nuevo código."

    if reset_record.code != clean_code:
        return False, "El código de verificación ingresado es incorrecto."

    # Autorizar cambio de contraseña
    reset_record.allow = True
    reset_record.updated_at = now
    db.commit()

    return True, "Código verificado correctamente. Ahora puedes definir tu nueva contraseña."


def confirm_password_reset(
    db: Session, 
    username: str, 
    code: str, 
    new_password: str
) -> Tuple[bool, str]:
    """
    Cambia definitivamente la contraseña del usuario si el código fue validado ('allow' == True)
    y aún no ha expirado la ventana de tiempo.
    Reutiliza la misma fila en 'password_resets' invalidando el código y autorización.
    """
    clean_username = username.strip()
    clean_code = code.strip()

    if len(new_password) < 6:
        return False, "La nueva contraseña debe tener al menos 6 caracteres."

    reset_record = db.query(PasswordReset).filter(PasswordReset.username == clean_username).first()
    if not reset_record or not reset_record.code:
        return False, "No se encontró registro de recuperación activo para este usuario."

    now = datetime.now(timezone.utc)
    if now > reset_record.expires_at:
        return False, "La sesión de restablecimiento ha expirado. Por favor solicita un nuevo código."

    if not reset_record.allow:
        return False, "Debes verificar primero el código antes de cambiar la contraseña."

    if reset_record.code != clean_code:
        return False, "El código de verificación es inválido."

    # Hashear contraseña con Argon2
    new_hash = get_password_hash(new_password)

    # Actualizar entidad correspondiente y desbloquear cuenta
    if reset_record.customer_id:
        cust = db.query(Customer).filter(Customer.customer_id == reset_record.customer_id).first()
        if cust:
            cust.password_hash = new_hash
            cust.failed_login_attempts = 0
            cust.is_locked = False
            cust.locked_at = None
            cust.updated_at = now
    elif reset_record.user_id:
        u = db.query(User).filter(User.user_id == reset_record.user_id).first()
        if u:
            u.password_hash = new_hash
            u.failed_login_attempts = 0
            u.is_locked = False
            u.locked_at = None
            u.updated_at = now
    else:
        # Fallback por username si id no estaba poblado
        cust = db.query(Customer).filter(Customer.username == clean_username).first()
        if cust:
            cust.password_hash = new_hash
            cust.failed_login_attempts = 0
            cust.is_locked = False
            cust.locked_at = None
            cust.updated_at = now
        else:
            u = db.query(User).filter(User.username == clean_username).first()
            if u:
                u.password_hash = new_hash
                u.failed_login_attempts = 0
                u.is_locked = False
                u.locked_at = None
                u.updated_at = now

    # Consumir e invalidar el registro reutilizando la misma fila fija (evita consumo de SERIAL y dead tuples)
    reset_record.code = None
    reset_record.allow = False
    reset_record.expires_at = now - timedelta(seconds=1)
    reset_record.updated_at = now
    db.commit()

    logger.info(f"[PASSWORD-RESET] Contraseña restablecida con éxito para usuario {clean_username} (fila reutilizable preservada)")
    return True, "Tu contraseña ha sido restablecida exitosamente. Ya puedes iniciar sesión con tu nueva clave."
