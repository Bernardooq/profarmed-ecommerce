"""
Routes de Administración de Roles y Permisos (PBAC / RBAC)

Endpoints para la gestión dinámica de roles y consulta del catálogo de permisos:
- GET /permissions - Catálogo maestro de permisos (sólo lectura)
- GET /roles - Lista de roles con estadísticas de usuarios y permisos
- GET /roles/{id} - Detalle de un rol específico con sus permisos
- POST /roles - Crear nuevo rol personalizado
- PUT /roles/{id} - Actualizar información y permisos de un rol
- DELETE /roles/{id} - Eliminar un rol personalizado
- POST /roles/{id}/permissions - Asignar o revocar matriz de permisos

Permisos: Acceso exclusivo para administradores del sistema.

NOTA DE SEGURIDAD ARQUITECTÓNICA:
Los permisos son definidos por el sistema y no poseen rutas de creación ni eliminación vía API.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from dependencies import get_db, require_permission
from db.base import User
from schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleWithPermissionsResponse,
    PermissionResponse,
    RolePermissionsAssignRequest
)
from crud.crud_role import (
    get_permissions,
    get_roles,
    get_role_by_id,
    create_role,
    update_role as crud_update_role,
    delete_role as crud_delete_role,
    assign_role_permissions as crud_assign_role_permissions
)

router = APIRouter()


""" GET /permissions - Catálogo maestro de permisos del sistema (sólo lectura) """
@router.get("/permissions", response_model=List[PermissionResponse])
@router.get("/permissions/", response_model=List[PermissionResponse], include_in_schema=False)
@router.get("/roles/permissions", response_model=List[PermissionResponse], include_in_schema=False)
@router.get("/roles/permissions/", response_model=List[PermissionResponse], include_in_schema=False)
def read_all_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin"))
):
    """
    Lista el catálogo maestro completo de permisos granulares del sistema.
    Solo accesible para administradores.
    """
    return get_permissions(db)


""" GET /roles - Lista de roles del sistema con métricas enriquecidas """
@router.get("/roles", response_model=List[Dict[str, Any]])
@router.get("/roles/", response_model=List[Dict[str, Any]], include_in_schema=False)
def read_all_roles(
    team_only: bool = Query(False, description="Excluir roles protegidos de administración"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin", "roles.view", "users.view", "groups.view"))
):
    """
    Retorna la lista de roles del sistema.
    Si el usuario solicitante no es administrador (slug != 'admin') o se solicita team_only=True,
    se excluyen los datos del Administrador General ('admin').
    """
    caller_slug = getattr(current_user.role_rel, "slug", "") if current_user.role_rel else ""
    is_caller_admin = (caller_slug == "admin" or current_user.role_id == 1 or current_user.has_permission("system.admin"))

    roles = get_roles(db)
    if team_only or not is_caller_admin:
        roles = [r for r in roles if r.get("slug") != "admin" and r.get("role_id") != 1]

    return roles


""" GET /roles/{role_id} - Detalle de un rol por ID """
@router.get("/roles/{role_id}", response_model=RoleWithPermissionsResponse)
@router.get("/roles/{role_id}/", response_model=RoleWithPermissionsResponse, include_in_schema=False)
def read_role_detail(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin", "roles.view", "users.view", "groups.view"))
):
    """
    Obtiene el detalle completo de un rol, incluyendo la lista plana
    y detallada de permisos asociados.
    """
    role = get_role_by_id(db, role_id=role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol con ID {role_id} no encontrado"
        )

    assigned_perms = [rp.permission_code for rp in role.permissions] if role.permissions else []
    assigned_details = [rp.permission for rp in role.permissions if rp.permission] if role.permissions else []

    return RoleWithPermissionsResponse(
        role_id=role.role_id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        permissions=assigned_perms,
        permissions_detail=assigned_details,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


""" POST /roles - Crear un nuevo rol personalizado """
@router.post("/roles", response_model=RoleWithPermissionsResponse, status_code=status.HTTP_201_CREATED)
@router.post("/roles/", response_model=RoleWithPermissionsResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_new_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin"))
):
    """
    Crea un nuevo rol en el sistema y le asocia los permisos validados.
    Los roles creados desde este endpoint son marcados como no pertenecientes al sistema (is_system = False).
    """
    role = create_role(db=db, role_data=role_data)

    assigned_perms = [rp.permission_code for rp in role.permissions] if role.permissions else []
    assigned_details = [rp.permission for rp in role.permissions if rp.permission] if role.permissions else []

    return RoleWithPermissionsResponse(
        role_id=role.role_id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        permissions=assigned_perms,
        permissions_detail=assigned_details,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


""" PUT /roles/{role_id} - Actualizar rol existente """
@router.put("/roles/{role_id}", response_model=RoleWithPermissionsResponse)
@router.put("/roles/{role_id}/", response_model=RoleWithPermissionsResponse, include_in_schema=False)
def update_role_info(
    role_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin"))
):
    """
    Actualiza la información básica y/o los permisos asociados a un rol.
    Para el Administrador General ('admin'), nombre, slug, descripción y estado activo son inmutables,
    permitiendo únicamente modificar su matriz de permisos granulares.
    Solo un usuario con rol de Administrador General ('admin') puede editar los permisos de 'admin'.
    Para cualquier otro rol se permite renombrar, modificar slug, estado y permisos.
    """
    target_role = get_role_by_id(db, role_id)
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol con ID {role_id} no encontrado"
        )

    if target_role.slug == "admin" or target_role.role_id == 1:
        caller_slug = getattr(current_user.role_rel, "slug", "") if current_user.role_rel else ""
        if not (caller_slug == "admin" or current_user.role_id == 1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un usuario con rol 'admin' (Administrador General) tiene autorización para modificar los permisos del Administrador General."
            )

    role = crud_update_role(db=db, role_id=role_id, role_data=role_data)

    assigned_perms = [rp.permission_code for rp in role.permissions] if role.permissions else []
    assigned_details = [rp.permission for rp in role.permissions if rp.permission] if role.permissions else []

    return RoleWithPermissionsResponse(
        role_id=role.role_id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        permissions=assigned_perms,
        permissions_detail=assigned_details,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


""" DELETE /roles/{role_id} - Eliminar rol """
@router.delete("/roles/{role_id}", status_code=status.HTTP_200_OK)
@router.delete("/roles/{role_id}/", status_code=status.HTTP_200_OK, include_in_schema=False)
def delete_role_account(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin"))
):
    """
    Elimina un rol del sistema con eliminación en cascada de sus permisos.
    Reglas de negocio:
    - El rol 'admin' (Administrador General) no puede ser eliminado bajo ninguna circunstancia.
    - Cualquier otro rol puede ser eliminado siempre y cuando tenga 0 usuarios asociados.
    """
    target_role = get_role_by_id(db, role_id)
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol con ID {role_id} no encontrado"
        )
    if target_role.slug == "admin" or target_role.role_id == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol Administrador General ('admin') es el rol protegido principal del sistema y no puede ser eliminado."
        )

    role = crud_delete_role(db=db, role_id=role_id)
    return {"message": f"Rol '{role.name}' eliminado exitosamente"}


""" POST /roles/{role_id}/permissions - Asignar matriz completa de permisos """
@router.post("/roles/{role_id}/permissions", response_model=RoleWithPermissionsResponse)
@router.post("/roles/{role_id}/permissions/", response_model=RoleWithPermissionsResponse, include_in_schema=False)
def assign_permissions_to_role(
    role_id: int,
    payload: RolePermissionsAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin"))
):
    """
    Reemplaza la matriz completa de permisos asignados a un rol por la nueva lista proporcionada.
    Solo un usuario con rol 'admin' puede editar los permisos del Administrador General.
    """
    target_role = get_role_by_id(db, role_id)
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol con ID {role_id} no encontrado"
        )

    if target_role.slug == "admin" or target_role.role_id == 1:
        caller_slug = getattr(current_user.role_rel, "slug", "") if current_user.role_rel else ""
        if not (caller_slug == "admin" or current_user.role_id == 1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un usuario con rol 'admin' (Administrador General) tiene autorización para modificar los permisos del Administrador General."
            )

    role = crud_assign_role_permissions(db=db, role_id=role_id, permissions=payload.final_permissions)

    assigned_perms = [rp.permission_code for rp in role.permissions] if role.permissions else []
    assigned_details = [rp.permission for rp in role.permissions if rp.permission] if role.permissions else []

    return RoleWithPermissionsResponse(
        role_id=role.role_id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        permissions=assigned_perms,
        permissions_detail=assigned_details,
        created_at=role.created_at,
        updated_at=role.updated_at
    )
