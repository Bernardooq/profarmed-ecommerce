"""
Routes de Autenticacion

Endpoints para autenticacion y gestion de sesion:
- POST /register - Registrar nuevo usuario interno (requiere users.create)
- POST /login - Login unificado (clientes B2B y colaboradores del sistema)
- POST /login/sync - Login para sincronización externa (requiere system.sync o system.admin)
- POST /logout - Revocar sesión actual
- GET /me - Informacion del usuario autenticado con permisos calculados

Sistema de Autenticacion:
- Soporta Customers y Users con roles dinámicos (RBAC / PBAC)
- Usa JWT tokens con OAuth2
- Token incluye role_slug, role_id y user_type
- Expiracion configurable
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging
import httpx

from dependencies import get_db, get_current_user, require_permission
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES, SYNC_TOKEN_EXPIRE_MINUTES, TURNSTILE_SECRET_KEY
from core.security import create_access_token, verify_password, decode_access_token
from core import token_blacklist
from crud.crud_user import authenticate_user, create_user, get_user_by_username, get_user_by_email
from schemas.user import User, UserCreate
from db.base import Customer, User as UserModel

router = APIRouter()

# Configuración de logger para este módulo
logger = logging.getLogger(__name__)

"""Schemas de respuesta de token"""
class Token(BaseModel):
    access_token: str
    token_type: str

"""Schemas de datos del token"""
class TokenData(BaseModel):
    username: Optional[str] = None

""" POST /register - Registrar nuevo usuario interno """
@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.create"))
):
    # Constraint: No se puede crear un usuario con roles del sistema salvo que quien lo cree posea 'system.admin'
    target_role_record = None
    if user.role_id:
        from db.base import Role
        target_role_record = db.query(Role).filter(Role.role_id == user.role_id).first()
    
    target_is_system = False
    if target_role_record:
        target_is_system = target_role_record.is_system or target_role_record.slug == "admin" or any(rp.permission_code == "system.admin" for rp in (target_role_record.permissions or []))
    elif user.role:
        target_slug = user.role.value if hasattr(user.role, "value") else str(user.role)
        target_is_system = (target_slug == "admin")

    if target_is_system and not current_user.has_permission("system.admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con 'system.admin' pueden crear usuarios administradores o del sistema"
        )

    # Registra un nuevo usuario interno (colaborador o administrador con rol dinámico)
    # Validar username unico
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya esta registrado"
        )
    
    # Validar email unico
    if user.email:
        db_user = get_user_by_email(db, email=user.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya esta registrado"
            )
    return create_user(db=db, user=user)

""" POST /login - Login (customers o users internos) """
@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Validar Turnstile CAPTCHA (comentado para demo local)
    if False and TURNSTILE_SECRET_KEY:
        captcha_token = request.headers.get("X-Turnstile-Token", "")
        
        # Validar contra la API de Cloudflare con estrategia Fail-Open
        try:
            # Siempre intentamos contactar a Cloudflare. 
            # Si el token falta, mandamos un valor dummy para verificar si el servicio está en línea.
            response = httpx.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": TURNSTILE_SECRET_KEY,
                    "response": captcha_token or "ping-healthcheck"
                },
                timeout=5.0 # Timeout reducido para no bloquear al usuario en caso de lentitud de red
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Caso 1: El usuario envió un token pero Cloudflare dice que es INVÁLIDO
                # Bloqueamos porque es un posible ataque o token expirado.
                if captcha_token and not result.get("success"):
                    logger.warning(f"Turnstile rechazó el token: {result.get('error-codes')}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Verificación CAPTCHA fallida. Intenta de nuevo."
                    )
                
                # Caso 2: NO se envió token y Cloudflare está FUNCIONANDO (respondió 200 OK)
                # Bloqueamos porque el usuario se saltó el captcha intencionalmente.
                elif not captcha_token:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Verificación CAPTCHA requerida"
                    )
                
                # Caso 3: Todo bien (token válido) -> El flujo continúa normal.
            else:
                # Si Cloudflare responde un error 500 o rate limit (429), permitimos el paso por precaución operativa
                logger.warning(f"Turnstile API falló con status {response.status_code}. Permitiendo login por fallback de seguridad.")
                
        except (httpx.RequestError, httpx.TimeoutException) as e:
            # FALLBACK CRÍTICO: Si no se puede contactar a Cloudflare (caída de red, DNS, caída de CF), 
            # permitimos el login para no detener la operación del negocio.
            logger.warning(f"Cloudflare inalcanzable ({type(e).__name__}). Bypass de seguridad activado por resiliencia.")
            pass
    
    # Autenticacion con username y password
    clean_username = form_data.username.strip()
    target_account = db.query(Customer).filter(Customer.username == clean_username).first()
    is_customer = True if target_account else False

    if not target_account:
        target_account = db.query(UserModel).filter(UserModel.username == clean_username).first()
        is_customer = False

    # Validar existencia de la cuenta
    if not target_account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validar si la cuenta está bloqueada por intentos fallidos
    if getattr(target_account, "is_locked", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta se encuentra bloqueada por exceder los intentos permitidos. Debes restablecer tu contraseña para desbloquearla."
        )

    # Validar contraseña
    if not verify_password(form_data.password, target_account.password_hash):
        current_attempts = (getattr(target_account, "failed_login_attempts", 0) or 0) + 1
        target_account.failed_login_attempts = current_attempts
        
        MAX_LOGIN_ATTEMPTS = 5
        if current_attempts >= MAX_LOGIN_ATTEMPTS:
            target_account.is_locked = True
            target_account.locked_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Has superado el límite de {MAX_LOGIN_ATTEMPTS} intentos fallidos. Tu cuenta ha sido bloqueada por seguridad. Restablece tu contraseña para continuar."
            )
        else:
            db.commit()
            remaining = MAX_LOGIN_ATTEMPTS - current_attempts
            word = "intento" if remaining == 1 else "intentos"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Contraseña incorrecta. Te quedan {remaining} {word} antes de que tu cuenta sea bloqueada.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Contraseña correcta -> Resetear contador de fallos si tenía
    if (getattr(target_account, "failed_login_attempts", 0) or 0) > 0 or getattr(target_account, "is_locked", False):
        target_account.failed_login_attempts = 0
        target_account.is_locked = False
        target_account.locked_at = None
        db.commit()

    authenticated_user = target_account
    
    # Validar que este activo
    if not authenticated_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo. Contacta al administrador."
        )

    # Constraint de Rol Activo: Si es usuario interno, su rol debe estar activo en el sistema
    if not is_customer:
        role = getattr(authenticated_user, "role_rel", None)
        if role and not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol '{role.name}' se encuentra inactivo. Contacta al administrador."
            )
    
    # Generar token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    if is_customer:
        # Token para Customer
        token_data = {
            "sub": authenticated_user.username,
            "role": "customer",
            "user_type": "customer",
            "customer_id": authenticated_user.customer_id
        }
    else:
        # Token para User interno
        role_val = getattr(authenticated_user, "role", None)
        role_slug = role_val.value if hasattr(role_val, "value") else str(role_val or "")
        token_data = {
            "sub": authenticated_user.username,
            "role": role_slug,
            "user_type": "user",
            "user_id": authenticated_user.user_id,
            "role_id": getattr(authenticated_user, "role_id", None)
        }
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


""" POST /login/sync - Login con token de corta duracion (5 min) para sincronizaciones """
@router.post("/login/sync", response_model=Token)
def login_sync(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Usuario con facultades de sincronización o administración de sistema
    authenticated_user = authenticate_user(db, form_data.username, form_data.password)
    
    # Validar auth
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validar que este activo
    if not authenticated_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo. Contacta al administrador."
        )

    # Constraint de Rol Activo: El rol del usuario debe estar activo
    role = getattr(authenticated_user, "role_rel", None)
    if role and not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El rol '{role.name}' se encuentra inactivo. Contacta al administrador."
        )
    
    # Validar que tenga facultades de sincronización o administración de sistema (system.admin o system.sync)
    has_sync_permission = (
        authenticated_user.has_permission("system.sync")
        or authenticated_user.has_permission("system.admin")
    )
    if not has_sync_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios con 'system.admin' o 'system.sync' pueden usar el endpoint de sincronización"
        )

    
    # Generar token DE CORTA DURACION (5 minutos)
    access_token_expires = timedelta(minutes=SYNC_TOKEN_EXPIRE_MINUTES)
    
    user_role = getattr(authenticated_user, "role", None)
    role_slug = user_role.value if hasattr(user_role, "value") else str(user_role or "")
    # Token para User interno
    token_data = {
        "sub": authenticated_user.username,
        "role": role_slug,
        "user_type": "user",
        "user_id": authenticated_user.user_id,
        "role_id": getattr(authenticated_user, "role_id", None)
    }
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


""" POST /logout - Revocar token actual (logout real) """
@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: Request, current_user = Depends(get_current_user)):
    """Revoca el token JWT actual agregando su JTI a la blacklist.
    El token queda inmediatamente inutilizable aunque no haya expirado."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    if payload:
        jti = payload.get("jti")
        exp = payload.get("exp")   # unix timestamp — usado para auto-prune
        if jti:
            token_blacklist.add(jti, exp)
    return {"message": "Sesión cerrada exitosamente"}


""" GET /me - Informacion del usuario actual """
@router.get("/me")
def read_users_me(current_user = Depends(get_current_user)):
    # Obtiene informacion del usuario autenticado actual
    if isinstance(current_user, Customer):
        # Es un Customer (permisos intrinsecos de tienda B2B aislados por sesion; catalogo, ofertas, pedidos y soporte)
        customer_perms = [
            "catalog.view",
            "announcements.view",
            "orders.view",
            "support.view",
            "support.create",
            "support.reply"
        ]
        user_dict = {
            "customer_id": current_user.customer_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "notificate": current_user.notificate,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "role": "customer",  # Role explicito para frontend
            "role_slug": "customer",
            "permissions": customer_perms
        }
    else:
        # Es un User interno
        role_val = getattr(current_user, "role", None)
        role_slug = role_val.value if hasattr(role_val, "value") else str(role_val or "")
        
        role_rel = getattr(current_user, "role_rel", None)
        role_name = role_rel.name if role_rel else role_slug.capitalize()
        
        # Obtener lista de códigos de permisos asignados
        perms = []
        if role_rel and getattr(role_rel, "permissions", None):
            perms = [rp.permission_code for rp in role_rel.permissions]
        
        user_dict = {
            "user_id": current_user.user_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role_id": getattr(current_user, "role_id", None),
            "role": role_slug,
            "role_slug": role_slug,
            "role_name": role_name,
            "permissions": perms,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None
        }
    
    return JSONResponse(content=user_dict)