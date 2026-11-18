"""
Routes para Perfil y Configuracion de Usuario

Endpoints para que los usuarios gestionen su propio perfil:

PERFIL:
- GET /me - Ver mi perfil
- PUT /me - Actualizar mi perfil

INFORMACIoN DE CLIENTE:
- GET /me/customer-info - Ver mi informacion comercial
- PUT /me/customer-info - Actualizar informacion comercial

CONSULTA DE USUARIOS:
- GET / - Lista de usuarios con filtrado dinamico por rol y busqueda (RBAC/PBAC)

Funciona para:
- Customers (gestion de perfil y customer_info)
- Users internos (gestion de perfil basico)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional

from dependencies import get_db, get_current_user, require_permission
from db.base import User, Customer, CustomerInfo, Role, GroupUser, RolePermission
from schemas.user import UserUpdate, User as UserSchema
from schemas.customer_info import CustomerInfo as CustomerInfoSchema, CustomerInfoUpdate
from crud.crud_user import get_user, update_user, get_users
from crud.crud_commercial_group import get_user_groups
from crud.crud_customer import get_customer_info, update_customer

router = APIRouter()

""" GET /me - Obtener perfil del usuario autenticado actual """
@router.get("/me")
def read_current_user_profile(current_user = Depends(get_current_user)):
    if isinstance(current_user, Customer):
        user_dict = {
            "customer_id": current_user.customer_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
            "notificate": current_user.notificate,
            "role": "customer"
        }
    else:
        role_val = getattr(current_user, "role", None)
        role_slug = role_val.value if hasattr(role_val, "value") else str(role_val or "")
        role_name = current_user.role_name if getattr(current_user, "role_name", None) else role_slug.capitalize()
        user_dict = {
            "user_id": current_user.user_id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role_id": getattr(current_user, "role_id", None),
            "role": role_slug,
            "role_slug": role_slug,
            "role_name": role_name,
            "permissions": getattr(current_user, "permissions", []),
            "is_active": current_user.is_active
        }
    
    return JSONResponse(content=user_dict)

""" PUT /me - Actualizar perfil del usuario autenticado actual """
@router.put("/me")
def update_current_user_profile(user_update: UserUpdate, current_user = Depends(get_current_user),
    db: Session = Depends(get_db)):
    if isinstance(current_user, Customer):
        update_data = user_update.model_dump(exclude_unset=True)

        # Validar que solo se este cambiando la contraseña o la preferencia de notificaciones
        disallowed_fields = set(update_data.keys()) - {'password', 'notificate'}
        if disallowed_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Los clientes solo pueden cambiar su contraseña o preferencia de notificaciones. No se pueden modificar: {', '.join(disallowed_fields)}"
            )
        
        # Al menos un campo a modificar
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar al menos un campo para actualizar"
            )

        updated = update_customer(db, customer_id=current_user.customer_id, customer=user_update)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
        return JSONResponse(content={
            "customer_id": updated.customer_id, "username": updated.username, "email": updated.email,
            "full_name": updated.full_name, "is_active": updated.is_active, "notificate": updated.notificate, "role": "customer"})
    else:
        # === ACTUALIZAR USER INTERNO (Admin, Marketing, Seller, etc.) ===
        user_data = user_update.model_dump(exclude_unset=True)
        
        # En /me jamás se permite alterar el estado de seguridad o bloqueo de cuenta
        for sec_field in ('is_locked', 'failed_login_attempts'):
            if sec_field in user_data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="El estado de seguridad y bloqueo de la cuenta no se puede modificar desde el perfil personal."
                )

        # Si NO es admin, solo permitir cambio de password
        is_admin = hasattr(current_user, "has_permission") and current_user.has_permission("system.admin")
        if not is_admin:
            disallowed_fields = set(user_data.keys()) - {'password'}
            if disallowed_fields:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos para modificar su perfil. Solo puede cambiar su contraseña."
                )

        user = update_user(db, user_id=current_user.user_id, user=user_update)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        role_slug = user.role if isinstance(user.role, str) else (user.role.value if hasattr(user.role, "value") else "user")
        role_name = user.role_rel.name if user.role_rel else role_slug.capitalize()
        permissions = [rp.permission_code for rp in user.role_rel.permissions] if (user.role_rel and user.role_rel.permissions) else []

        return JSONResponse(content={
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email, 
            "full_name": user.full_name,
            "role": role_slug,
            "role_slug": role_slug,
            "role_name": role_name,
            "role_id": user.role_id,
            "permissions": permissions,
            "is_active": user.is_active
        })

""" GET /me/customer-info - Obtener la informacion comercial del cliente actual """
@router.get("/me/customer-info", response_model=CustomerInfoSchema)
def read_current_user_customer_info(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if not isinstance(current_user, Customer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado. Este endpoint es solo para clientes.")

    customer_id = current_user.customer_id

    customer_info = get_customer_info(db, customer_id)

    if not customer_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Informacion de cliente no encontrada"
        )
    
    return customer_info

""" GET / - Lista de usuarios con filtrado dinamico por rol, permiso PBAC y busqueda (RBAC/PBAC) """
@router.get("", response_model=List[UserSchema])
@router.get("/", response_model=List[UserSchema], include_in_schema=False)
def get_users_list(
    role: Optional[str] = Query(None, description="Filtrar por slug de rol dinamico (ej: seller, cadenero, mark, etc.)"),
    permission_code: Optional[str] = Query(None, description="Filtrar por código de permiso PBAC (ej: orders.create, warehouse.operator)"),
    search: Optional[str] = Query(None, description="Buscar por nombre, username, email o ID"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Maximo de registros"),
    current_user: User = Depends(require_permission("users.view", "orders.view", "groups.view", "customers.assign", "customers.view")),
    db: Session = Depends(get_db)
):
    caller_slug = getattr(current_user.role_rel, "slug", "") if getattr(current_user, "role_rel", None) else getattr(current_user, "role", "")
    caller_slug_str = caller_slug.value if hasattr(caller_slug, "value") else str(caller_slug or "").strip().lower()
    is_caller_sys_admin = (
        caller_slug_str == "admin" or
        getattr(current_user, "role_id", None) == 1 or
        (hasattr(current_user, "has_permission") and current_user.has_permission("system.admin"))
    )

    # Si quien consulta no es admin del sistema y solicita explícitamente el rol admin, no enviar nada
    if not is_caller_sys_admin and role and str(role).strip().lower() in ("admin", "1"):
        return []

    # Si posee users.view (o es admin), tiene visibilidad global sobre usuarios
    has_users_view = hasattr(current_user, "has_permission") and (current_user.has_permission("users.view") or is_caller_sys_admin)

    if has_users_view:
        # Excluir administradores a menos que el que consulte sea system.admin
        return get_users(
            db,
            skip=skip,
            limit=limit,
            role=role,
            search=search,
            permission_code=permission_code,
            exclude_admins=not is_caller_sys_admin
        )

    # Si NO tiene users.view, su visibilidad se acota dinamicamente a los miembros de sus grupos comerciales asignados
    user_groups = get_user_groups(db, current_user.user_id)
    if user_groups:
        group_member_ids = db.query(GroupUser.user_id).filter(
            GroupUser.sales_group_id.in_(user_groups)
        ).distinct().all()
        allowed_user_ids = {r[0] for r in group_member_ids}
    else:
        allowed_user_ids = set()

    # El usuario siempre tiene visibilidad de si mismo
    allowed_user_ids.add(current_user.user_id)

    query = db.query(User).join(Role, Role.role_id == User.role_id).filter(
        User.user_id.in_(allowed_user_ids),
        User.is_active == True
    )

    # Exclusión estricta de administradores si quien consulta no es system.admin
    if not is_caller_sys_admin:
        query = query.filter(
            User.role_id != 1,
            Role.slug != "admin",
            User.user_id < 15_000_000
        )

    # Filtrar por capacidad/permiso PBAC
    if permission_code:
        perm_role_ids = [rp[0] for rp in db.query(RolePermission.role_id).filter(
            RolePermission.permission_code.in_([permission_code, "*", "system.admin"])
        ).all()]
        query = query.filter(User.role_id.in_(set(perm_role_ids)))
    elif role:
        # Filtrar por rol dinamico (resolviendo el slug del rol en la tabla roles)
        role_slug = role.strip().lower()
        role_obj = db.query(Role).filter(Role.slug == role_slug).first()
        if not role_obj:
            return []
        query = query.filter(User.role_id == role_obj.role_id)

    # Busqueda por nombre, username, email o ID
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


