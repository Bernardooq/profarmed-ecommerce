"""
CRUD y Gestión Integral de Usuarios Internos del Sistema (Users) — PBAC & RBAC Dinámico:

Arquitectura y Modelo de Seguridad (PROFARMED v2.2):
- Catálogo dinámico de N roles configurables (`Role`) con asignación granular de permisos (`RolePermission`).
- Autenticación robusta y verificación de contraseñas mediante hash Argon2.
- Búsqueda y filtrado multi-criterio por rol (`role_id` o `slug`), correo, nombre, username y capacidad (`permission_code`).
- Auto-generación de grupo de ventas personal al crear usuarios con facultades comerciales (`orders.create`).
- Asignación flexible N:M a grupos de ventas mediante `GroupUser`.

Estructura de Identificadores (User IDs):
1. Colaboradores y Roles Operativos — [IDs < 15,000,000]:
   - Agentes comerciales sincronizados desde DBF o creados manualmente.
   - Coordinadores de ventas, supervisores, operadores y auditores de almacén, y roles personalizados.
2. Administradores Globales (Admin / System) — [IDs >= 15,000,000]:
   - Rango reservado para personal con control total del sistema (`system.admin`).

Permisos PBAC Requeridos:
- Consulta de usuarios: `users.view` o `system.admin`
- Creación de usuarios: `users.create` o `system.admin`
- Edición de usuarios: `users.edit` o `system.admin`
- Eliminación de usuarios: `users.delete` o `system.admin`
- Filtrado por capacidad comercial: `orders.create`

NOTA ARQUITECTÓNICA:
Los clientes de la plataforma e-commerce se encuentran estrictamente desacoplados en `crud_customer.py` (tabla `customers`).
"""

from typing import List, Optional, Union, Any
from datetime import datetime, timezone
from .crud_commercial_group import get_user_groups, create_sales_group, assign_member_to_group
from utils.sales_group_utils import auto_crear_grupo_usuario
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_
from schemas.sales_group import SalesGroupCreate        
from core.security import get_password_hash, verify_password
from db.base import GroupUser, User, SalesGroup, Role
from schemas.user import UserCreate, UserUpdate

""" Obtener un usuario interno por ID """
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.user_id == user_id).first()

""" Obtener un usuario interno por username """
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

""" Obtener un usuario interno por email """
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

""" Obtener lista de usuarios internos con filtros opcionales """
def get_users(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    role: Optional[str] = None, 
    search: Optional[str] = None,
    permission_code: Optional[Union[str, List[str]]] = None,
    exclude_admins: bool = False
) -> List[User]:
    query = db.query(User).join(Role, Role.role_id == User.role_id)
    
    # Identificar IDs de roles administradores del sistema
    admin_role_ids = set(
        r[0] for r in db.query(Role.role_id).filter(
            or_(
                Role.slug == "admin",
                Role.role_id == 1,
                Role.is_system == True
            )
        ).all()
    )

    # Filtrar por capacidad/permiso PBAC
    if permission_code:
        from db.base import RolePermission
        if isinstance(permission_code, (list, tuple, set)):
            perm_role_ids = set(
                rp[0] for rp in db.query(RolePermission.role_id)
                .filter(RolePermission.permission_code.in_(list(permission_code)))
                .all()
            )
            is_sys_admin = "system.admin" in permission_code
        else:
            # Roles que tienen explícitamente el permiso otorgado
            perm_role_ids = set(
                rp[0] for rp in db.query(RolePermission.role_id)
                .filter(RolePermission.permission_code == permission_code)
                .all()
            )
            is_sys_admin = (permission_code == "system.admin")
        
        # En consultas de personal operativo por permiso (ej: warehouse.operator, warehouse.checker, orders.create),
        # jamás incluir usuarios con rol de administrador ni IDs reservados de admin
        if exclude_admins or not is_sys_admin:
            allowed_roles = perm_role_ids - admin_role_ids
            query = query.filter(
                User.role_id.in_(allowed_roles),
                User.user_id < 15_000_000,
                ~User.role_id.in_(admin_role_ids),
                Role.slug != "admin"
            )
        else:
            query = query.filter(User.role_id.in_(perm_role_ids))
    elif role:
        role_slug = role.value if hasattr(role, "value") else str(role)
        role_str = role_slug.strip()
        if role_str.isdigit():
            query = query.filter(User.role_id == int(role_str))
        else:
            clean_role = role_str.lower()
            matching_role_ids = [
                r[0] for r in db.query(Role.role_id).filter(
                    or_(
                        Role.slug == clean_role,
                        Role.slug.ilike(f"{clean_role}%"),
                        Role.name.ilike(f"%{clean_role}%")
                    )
                ).all()
            ]
            if matching_role_ids:
                query = query.filter(User.role_id.in_(matching_role_ids))
            else:
                return []

    # Exclusión general de administradores si se solicita explícitamente
    clean_role_param = str(role or "").strip().lower()
    if exclude_admins and clean_role_param not in ("admin", "1"):
        query = query.filter(
            ~User.role_id.in_(admin_role_ids),
            Role.slug != "admin",
            User.user_id < 15_000_000
        )
    
    # Por nombre, username, email o ID
    if search:
        search_trimmed = search.strip()
        search_term = f"%{search_trimmed}%"
        filters = [
            User.full_name.ilike(search_term),
            User.username.ilike(search_term),
            User.email.ilike(search_term)
        ]
        if search_trimmed.isdigit():
            filters.append(User.user_id == int(search_trimmed))
        query = query.filter(or_(*filters))
    
    return query.offset(skip).limit(limit).all()



""" Crear un nuevo usuario interno """
def create_user(db: Session, user: UserCreate) -> User:
    """
    Crea un nuevo usuario interno con asignación dinámica de rol (RBAC Dinámico PROFARMED v2.2).
    
    Esquema de asignación de User IDs:
    - Colaboradores y Roles Operativos: IDs < 15,000,000 (auto-incremento o asignación explícita para agentes sincronizados DBF).
    - Administradores Globales: Rango reservado exclusivo a partir de 15,000,000 (`ADMIN_ID_MIN`).
    
    Si se proporciona user_id explícito, valida unicidad y que cumpla la regla de rango según el rol.
    Si no se proporciona, genera automáticamente el siguiente ID secuencial disponible.
    """
    # Resolver rol asignado (por role_id o slug)
    target_role = None
    if user.role_id is not None:
        target_role = db.query(Role).filter(Role.role_id == user.role_id).first()
        if not target_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró un rol con ID {user.role_id}"
            )
    elif user.role is not None:
        role_slug = user.role.value if hasattr(user.role, "value") else str(user.role)
        target_role = db.query(Role).filter(Role.slug == role_slug).first()
        if not target_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró un rol con slug '{role_slug}'"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe especificar un rol (role_id o role) para el usuario"
        )

    role_slug = target_role.slug

    # Rango reservado exclusivo para Administradores
    ADMIN_ID_MIN = 15_000_000          # Admin: 15,000,000+

    # Hashear contraseña
    hashed_password = get_password_hash(user.password)
    
    # Determinar el ID a usar
    if user.user_id is not None:
        # Validar que el ID sea positivo
        if user.user_id < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ID de usuario debe ser mayor a 0"
            )
        
        # Validar rango reservado de Administradores
        if role_slug == "admin":
            if user.user_id < ADMIN_ID_MIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Los administradores tienen reservado el rango a partir de {ADMIN_ID_MIN:,}"
                )
        else:
            if user.user_id >= ADMIN_ID_MIN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Los IDs a partir de {ADMIN_ID_MIN:,} están reservados exclusivamente para administradores"
                )

        # ID manual proporcionado - validar unicidad
        existing_user = db.query(User).filter(User.user_id == user.user_id).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un usuario con el ID {user.user_id}"
            )
        user_id_to_use = user.user_id
    else:
        # Auto-generar el siguiente ID disponible
        if role_slug == "admin":
            max_id = db.query(func.max(User.user_id)).filter(
                User.user_id >= ADMIN_ID_MIN
            ).scalar()
            user_id_to_use = (max_id + 1) if max_id else ADMIN_ID_MIN
        else:
            # Todos los demás roles operativos y dinámicos se crean en el rango general
            max_id = db.query(func.max(User.user_id)).filter(
                User.user_id < ADMIN_ID_MIN
            ).scalar()
            user_id_to_use = (max_id + 1) if max_id else 1
    
    db_user = User(
        user_id=user_id_to_use,
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        full_name=user.full_name,
        role_id=target_role.role_id,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Auto-crear grupo para cualquier usuario no-admin (desacoplado de slug fijo o permisos hardcodeados)
    if role_slug != "admin":
        auto_crear_grupo_usuario(db, db_user)
    
    return db_user

""" Actualizar un usuario interno """
def update_user(db: Session, user_id: int, user: UserUpdate) -> Optional[User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    update_data = user.model_dump(exclude_unset=True)

    # Validar unicidad del username
    if "username" in update_data and update_data["username"] != db_user.username:
        existing_user = (
            db.query(User)
            .filter(User.username == update_data["username"], User.user_id != user_id)
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso por otro usuario."
            )

    # Validar unicidad del email
    """if "email" in update_data and update_data["email"] != db_user.email:
        existing_email = (
            db.query(User)
            .filter(User.email == update_data["email"], User.user_id != user_id)
            .first()
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está en uso por otro usuario."
            )"""

    # Hashear nueva contraseña
    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = get_password_hash(update_data["password"])
        del update_data["password"]

    # Procesar actualización de rol si aplica
    if "role_id" in update_data and update_data["role_id"] is not None:
        target_role = db.query(Role).filter(Role.role_id == update_data["role_id"]).first()
        if not target_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró un rol con ID {update_data['role_id']}"
            )
        db_user.role_id = target_role.role_id
        del update_data["role_id"]
        update_data.pop("role", None)
    elif "role" in update_data and update_data["role"] is not None:
        role_val = update_data.pop("role")
        role_slug = role_val.value if hasattr(role_val, "value") else str(role_val)
        target_role = db.query(Role).filter(Role.slug == role_slug).first()
        if not target_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se encontró un rol con slug '{role_slug}'"
            )
        db_user.role_id = target_role.role_id

    # Actualizar campos restantes
    for field, value in update_data.items():
        if field != "role":
            setattr(db_user, field, value)

    # Sincronización consistente de seguridad backend
    if update_data.get("is_locked") is False:
        db_user.is_locked = False
        db_user.failed_login_attempts = 0
        db_user.locked_at = None
    elif update_data.get("is_locked") is True:
        db_user.is_locked = True
        if not db_user.locked_at:
            db_user.locked_at = datetime.now(timezone.utc)
        if db_user.failed_login_attempts < 5:
            db_user.failed_login_attempts = max(db_user.failed_login_attempts, 5)

    if "failed_login_attempts" in update_data:
        attempts = update_data["failed_login_attempts"]
        db_user.failed_login_attempts = attempts
        if attempts >= 5:
            db_user.is_locked = True
            if not db_user.locked_at:
                db_user.locked_at = datetime.now(timezone.utc)
        elif attempts == 0 and update_data.get("is_locked") is not True:
            db_user.is_locked = False
            db_user.locked_at = None

    db.commit()
    db.refresh(db_user)
    return db_user


"""" Eliminar un usuario interno (hard delete) """
def delete_user(db: Session, user_id: int) -> Optional[User]:
    db_user = get_user(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

""" Autenticar un usuario interno """
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:    
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    # Verificar contrasenia usando Argon2
    if not verify_password(password, user.password_hash):
        return None
    
    return user

""" Obtener todos los usuarios de un rol especifico """
def get_users_by_role(db: Session, role: Union[str, Any]) -> List[User]:
    # Obtiene todos los usuarios de un rol especifico mediante su slug
    role_slug = role.value if hasattr(role, "value") else str(role)
    role_obj = db.query(Role).filter(Role.slug == role_slug).first()
    if not role_obj:
        return []
    return db.query(User).filter(
        User.role_id == role_obj.role_id,
        User.is_active == True
    ).all()


""" Obtener colaboradores asociados a los grupos de venta de un usuario (PBAC dinámico) """
def get_colleagues_in_user_groups(db: Session, user_id: int) -> List[User]:
    """
    Obtiene todos los miembros (agentes, supervisores y coordinadores) que comparten al menos
    un grupo comercial con el usuario indicado (`user_id`).
    """
    # Obtener IDs de grupos donde participa el usuario
    user_groups = get_user_groups(db, user_id)
    
    if not user_groups:
        return []
    
    # IDs de todos los miembros (GroupUser) asignados a esos mismos grupos
    member_ids = db.query(GroupUser.user_id).filter(
        GroupUser.sales_group_id.in_(user_groups)
    ).distinct().all()
    
    all_assignable_ids = [r[0] for r in member_ids]
    
    # Retornar usuarios activos
    return db.query(User).filter(
        User.user_id.in_(all_assignable_ids),
        User.is_active == True
    ).all()