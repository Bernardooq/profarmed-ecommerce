"""
Dependencias de FastAPI para PROFARMED

Este modulo define las dependencias que se inyectan en los endpoints:
- get_db: Proporciona una sesion de base de datos
- get_current_user: Autentica usuario o cliente desde JWT
- get_current_active_user: Verifica que el usuario este activo
- get_current_admin_user: Verifica permisos de administrador o sincronización
- get_current_internal_user: Verifica que sea usuario interno (no cliente B2B)
- require_permission: Factory dinámica para validación granular basada en permisos (PBAC)
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from db.session import SessionLocal
from db.base import User
from core.security import decode_access_token
from core import token_blacklist
from crud.crud_user import get_user_by_username

# Esquema de autenticacion OAuth2 con bearer token
# El token se obtiene desde el endpoint /auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # Obtiene el usuario autenticado actual desde el token JWT
    from db.base import Customer
    from crud.crud_customer import get_customer_by_username
    
    # Excepcion que se lanza si hay problemas con las credenciales
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decodificar el token JWT
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Verificar que el token no haya sido revocado (logout)
    jti = payload.get("jti")
    if jti and token_blacklist.contains(jti):
        raise credentials_exception
    
    # Extraer informacion del payload
    username: str = payload.get("sub")  # El 'subject' es el username
    user_type: str = payload.get("user_type")  # 'user' o 'customer'
    
    if username is None:
        raise credentials_exception
    
    # Buscar en la tabla correspondiente segun el tipo de usuario
    if user_type == "customer":
        # Buscar en la tabla de clientes
        authenticated_user = get_customer_by_username(db, username=username)
    else:
        # Buscar en la tabla de usuarios internos (colaboradores y administradores con roles dinámicos)
        authenticated_user = get_user_by_username(db, username=username)

    
    if authenticated_user is None:
        raise credentials_exception
    
    # Verificar que el usuario este activo
    if not authenticated_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )

    # Verificar que el rol asignado esté activo para usuarios internos
    if isinstance(authenticated_user, User):
        role = getattr(authenticated_user, "role_rel", None)
        if role and not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol '{role.name}' se encuentra inactivo. Acceso denegado."
            )
    
    return authenticated_user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    # Verifica que el usuario actual este activo
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    # Verifica que el usuario actual sea administrador o cuente con permisos de sincronización
    is_authorized = (
        getattr(current_user, "role_slug", None) == "admin"
        or getattr(current_user, "role", None) == "admin"
        or (hasattr(current_user, "has_permission") and (
            current_user.has_permission("system.admin") or current_user.has_permission("system.sync")
        ))
    )
    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos de administrador o de sincronización del sistema"
        )
    return current_user


async def get_current_internal_user(current_user: User = Depends(get_current_user)) -> User:
    # Verifica que sea cualquier usuario interno (no cliente B2B)
    if not isinstance(current_user, User) or getattr(current_user, "role", None) == "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a usuarios internos del sistema"
        )
    return current_user


def require_permission(*permission_codes: str):
    """
    Factory de dependencias FastAPI para verificar permisos granulares (PBAC).
    Soporta uno o múltiples códigos de permiso (basta con poseer al menos uno).
    
    Uso:
    @router.get('/ejemplo', dependencies=[Depends(require_permission('products.view'))])
    o
    current_user: User = Depends(require_permission('users.view'))
    """
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        # Clientes no pasan por esta verificación (tienen permisos intrínsecos de storefront)
        user_role = getattr(current_user, "role", None)
        if user_role == "customer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso restringido a usuarios internos del sistema"
            )

        # Admin omnisciente
        if (
            getattr(current_user, "role_slug", None) == "admin"
            or getattr(current_user, "role", None) == "admin"
            or (hasattr(current_user, "has_permission") and current_user.has_permission("system.admin"))
        ):
            return current_user

        # Verificar si posee al menos uno de los permisos requeridos
        for code in permission_codes:
            if hasattr(current_user, "has_permission") and current_user.has_permission(code):
                return current_user

        codes_str = ", ".join(f"'{c}'" for c in permission_codes)
        detail_msg = (
            f"Permiso insuficiente: Se requiere la capacidad {codes_str}"
            if len(permission_codes) == 1
            else f"Permiso insuficiente: Se requiere alguna de las siguientes capacidades: {codes_str}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_msg
        )

    return permission_checker

