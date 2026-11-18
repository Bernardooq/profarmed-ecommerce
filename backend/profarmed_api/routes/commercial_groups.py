"""
Routes para Grupos Comerciales (Commercial Groups)

Gestión completa de grupos comerciales y asignación colaborativa con relaciones N:M.

GRUPOS (CRUD):
- GET / - Lista de grupos con conteos
- GET /my-groups - Mis grupos asignados
- GET /{id} - Detalle con conteos
- POST / - Crear grupo
- PUT /{id} - Actualizar grupo
- DELETE /{id} - Eliminar grupo (cascade)

MEMBRESÍA Y USUARIOS ASIGNADOS AL GRUPO (N:M):
- POST /{id}/members - Asignar usuario/colaborador al grupo
- DELETE /{id}/members/{user_id} - Remover usuario del grupo
- GET /{id}/members - Ver todos los usuarios asignados al grupo (soporta filtro dinámico ?role=...)
- GET /{id}/available-members - Ver usuarios disponibles para agregar al grupo

ASIGNACIÓN POR USUARIO:
- GET /users/{user_id}/groups - Obtener IDs de grupos asignados a un usuario
- PUT /users/{user_id}/groups - Asignación masiva atómica de grupos a un usuario

CLIENTES B2B (N:1):
- POST /{id}/customers/{customer_id} - Asignar cliente al grupo
- DELETE /{id}/customers/{customer_id} - Remover cliente del grupo
- GET /{id}/customers - Ver clientes del grupo (paginado)
- GET /{id}/available-customers - Ver clientes disponibles para agregar

Sistema de Permisos PBAC:
- Control de Grupos ('groups.manage' o 'system.admin'): Acceso transversal a todos los grupos comerciales
- Colaboradores ('groups.view'): Acceso acotado a sus grupos comerciales asignados
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.base import User as UserModel, SalesGroup as SalesGroupModel

from dependencies import get_db, require_permission
from schemas.sales_group import (
    SalesGroup,
    SalesGroupCreate,
    SalesGroupUpdate,
    SalesGroupWithMembers,
    GroupUser,
    UserAssignment,
    SalesGroupPaginatedResponse,
)
from schemas.user import User
from schemas.customer import CustomerWithInfo
from crud.crud_commercial_group import (
    create_sales_group,
    get_sales_group,
    get_sales_groups,
    update_sales_group,
    delete_sales_group,
    get_sales_group_with_counts,
    get_sales_groups_with_counts_batch,
    get_user_groups,
    user_belongs_to_group,
    assign_user_groups_bulk,
    assign_customer_to_sales_group,
    remove_customer_from_sales_group,
    get_group_customers_paginated,
    get_available_customers,
    assign_member_to_group,
    remove_member_from_group,
    get_group_members,
    get_available_members,
)

router = APIRouter()


class BulkGroupAssign(BaseModel):
    group_ids: List[int]


# ============================================================================
# ASIGNACIÓN DE GRUPOS POR USUARIO
# ============================================================================

""" GET /users/{user_id}/groups - Obtener IDs de grupos de un usuario """
@router.get("/users/{user_id}/groups", response_model=List[int])
def get_groups_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage", "groups.view", "users.view"))
):
    if current_user.user_id != user_id and not (
        current_user.has_permission("system.admin") or current_user.has_permission("groups.manage")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso insuficiente para consultar grupos de otros usuarios"
        )
    return get_user_groups(db, user_id)


""" PUT /users/{user_id}/groups - Asignación masiva atómica de grupos a un usuario """
@router.put("/users/{user_id}/groups")
def bulk_assign_user_groups(
    user_id: int,
    data: BulkGroupAssign,
    current_user: UserModel = Depends(require_permission("groups.manage")),
    db: Session = Depends(get_db)
):
    try:
        result = assign_user_groups_bulk(db, user_id=user_id, group_ids=data.group_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al asignar grupos: {str(e)}")


# ============================================================================
# OPERACIONES CRUD DE GRUPOS DE VENTAS
# ============================================================================

""" GET / - Obtener todos los grupos de ventas con conteos de miembros """
@router.get("/", response_model=SalesGroupPaginatedResponse)
def read_sales_groups(
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"), 
    is_active: Optional[bool] = Query(None), 
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(require_permission("groups.manage", "groups.view", "users.view"))
):
    has_global_access = hasattr(current_user, "has_permission") and (
        current_user.has_permission("system.admin") or 
        current_user.has_permission("groups.manage") or
        current_user.has_permission("users.view")
    )
    allowed_group_ids = None
    if not has_global_access:
        allowed_group_ids = get_user_groups(db, current_user.user_id)
        if not allowed_group_ids:
            return {"items": [], "total": 0}

    groups, total = get_sales_groups(
        db, skip=skip, limit=limit, is_active=is_active, search=search, allowed_group_ids=allowed_group_ids
    )
    
    groups_with_counts = get_sales_groups_with_counts_batch(db, groups)
    
    return {"items": groups_with_counts, "total": total}


""" GET /my-groups - Obtener los grupos de ventas asignados al usuario actual """
@router.get("/my-groups", response_model=List[SalesGroupWithMembers])
def read_my_sales_groups(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.view", "users.view", "orders.create", "orders.view", "customers.view"))
):
    group_ids = get_user_groups(db, current_user.user_id)
    
    if not group_ids:
        if current_user.has_permission("system.admin") or current_user.has_permission("groups.manage") or current_user.has_permission("users.view"):
            all_groups = db.query(SalesGroupModel).filter(SalesGroupModel.is_active == True).all()
            return get_sales_groups_with_counts_batch(db, all_groups)
        else:
            return []

    groups = db.query(SalesGroupModel).filter(SalesGroupModel.sales_group_id.in_(group_ids)).all()
    return get_sales_groups_with_counts_batch(db, groups)


""" GET /{group_id} - Obtener un grupo de ventas por ID con conteos de miembros """
@router.get("/{group_id}", response_model=SalesGroupWithMembers)
def read_sales_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage", "groups.view", "users.view"))
):
    has_global_access = hasattr(current_user, "has_permission") and (
        current_user.has_permission("system.admin") or 
        current_user.has_permission("groups.manage") or
        current_user.has_permission("users.view")
    )
    if not has_global_access:
        if not user_belongs_to_group(db, current_user.user_id, group_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver este grupo de ventas"
            )

    group = get_sales_group_with_counts(db, group_id=group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de ventas no encontrado"
        )
    return group


""" POST / - Crear un nuevo grupo de ventas """
@router.post("/", response_model=SalesGroup, status_code=status.HTTP_201_CREATED)
def create_new_sales_group(
    group: SalesGroupCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    return create_sales_group(db=db, group=group)


""" PUT /{group_id} - Actualizar un grupo de ventas existente """
@router.put("/{group_id}", response_model=SalesGroup)
def update_existing_sales_group(
    group_id: int,
    group: SalesGroupUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    db_group = update_sales_group(db, group_id=group_id, group=group)
    if not db_group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo de ventas no encontrado")
    return db_group


""" DELETE /{group_id} - Eliminar un grupo de ventas """
@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_sales_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    db_group = delete_sales_group(db, group_id=group_id)
    if not db_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de ventas no encontrado"
        )
    return None


# ============================================================================
# MEMBRESÍA Y USUARIOS DEL GRUPO (PBAC / RBAC DINÁMICO)
# ============================================================================

""" GET /{group_id}/members - Obtener usuarios miembros del grupo con soporte de filtro dinámico por rol """
@router.get("/{group_id}/members", response_model=List[User])
def read_all_group_members(
    group_id: int,
    role: Optional[str] = Query(None, description="Filtro opcional por rol (ID, slug o nombre)"),
    role_id: Optional[int] = Query(None, description="Filtro opcional por ID de rol"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Máximo de registros"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre, username o email"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.view", "users.view", "groups.manage"))
):
    group = get_sales_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo de ventas no encontrado")
    
    has_global_access = (
        current_user.has_permission("system.admin") or 
        current_user.has_permission("groups.manage") or
        current_user.has_permission("users.view")
    )
    if not has_global_access:
        if not user_belongs_to_group(db, current_user.user_id, group_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver los miembros de este grupo"
            )

    return get_group_members(
        db, group_id=group_id, role=role, role_id=role_id, skip=skip, limit=limit, search=search
    )


""" GET /{group_id}/available-members - Obtener usuarios disponibles para agregar al grupo con filtro dinámico por rol """
@router.get("/{group_id}/available-members", response_model=List[User])
def read_available_group_members(
    group_id: int,
    role: Optional[str] = Query(None, description="Filtro opcional por rol (ID, slug o nombre)"),
    role_id: Optional[int] = Query(None, description="Filtro opcional por ID de rol"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Máximo de registros"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre, username o email"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    return get_available_members(
        db, group_id=group_id, role=role, role_id=role_id, skip=skip, limit=limit, search=search
    )


""" POST /{group_id}/members - Asignar usuario/miembro al grupo comercial """
@router.post("/{group_id}/members", response_model=GroupUser, status_code=status.HTTP_201_CREATED)
def assign_member_to_sales_group(
    group_id: int,
    assignment: UserAssignment,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    return assign_member_to_group(db=db, group_id=group_id, user_id=assignment.user_id)


""" DELETE /{group_id}/members/{user_id} - Remover usuario/miembro del grupo comercial """
@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member_from_sales_group(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    success = remove_member_from_group(db, group_id=group_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asignación no encontrada")
    return None


# ============================================================================
# CLIENTES B2B DEL GRUPO (N:1)
# ============================================================================

""" POST /{group_id}/customers/{customer_id} - Asignar un cliente al grupo de ventas """
@router.post("/{group_id}/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_customer_to_group(
    group_id: int,
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    try:
        assign_customer_to_sales_group(db, group_id=group_id, customer_id=customer_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


""" DELETE /{group_id}/customers/{customer_id} - Remover un cliente del grupo de ventas """
@router.delete("/{group_id}/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_customer_from_group(
    group_id: int,
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    success = remove_customer_from_sales_group(db, group_id=group_id, customer_id=customer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada"
        )
    return None


""" GET /{group_id}/customers - Obtener clientes de un grupo con paginación y búsqueda server-side """
@router.get("/{group_id}/customers", response_model=List[CustomerWithInfo])
def read_group_customers(
    group_id: int, 
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Máximo de registros"), 
    search: Optional[str] = Query(None), 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.view", "customers.view", "groups.manage", "customers.view_all", "users.view"))
):
    group = get_sales_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de ventas no encontrado"
        )
    has_global_access = (
        current_user.has_permission("system.admin") or 
        current_user.has_permission("groups.manage") or
        current_user.has_permission("customers.view_all") or
        current_user.has_permission("users.view")
    )
    if not has_global_access:
        if not user_belongs_to_group(db, current_user.user_id, group_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para ver los clientes de este grupo")
    return get_group_customers_paginated(db, group_id=group_id, skip=skip, limit=limit, search=search)


""" GET /{group_id}/available-customers - Obtener clientes disponibles para agregar al grupo """
@router.get("/{group_id}/available-customers", response_model=List[CustomerWithInfo])
def read_available_customers(
    group_id: int, 
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Máximo de registros"), 
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_permission("groups.manage"))
):
    return get_available_customers(db, group_id=group_id, skip=skip, limit=limit, search=search)
