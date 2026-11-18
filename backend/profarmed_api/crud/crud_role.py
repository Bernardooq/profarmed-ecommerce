"""
CRUD y Gestión de Roles y Permisos Dinámicos (PBAC / RBAC)

Funciones y Operaciones:
- Consulta del catálogo maestro de permisos del sistema (sólo lectura, no modificable por API).
- Operaciones CRUD de roles dinámicos (creación, lectura, actualización y eliminación de roles).
- Asignación y revocación granular de permisos a roles con resolución recursiva de dependencias (`depends_on`).
- Validación de integridad y protección de roles nativos del sistema (`is_system = True`).

Reglas de Control de Acceso PBAC / RBAC Dinámico:
- Catálogo de permisos inmutable: Definido exclusivamente en migraciones/seeds de base de datos.
- Permisos requeridos para gestión: `roles.view` (consulta de roles y matriz), `roles.manage` (crear, editar, asignar permisos o eliminar roles) o `system.admin`.
- Integridad de dependencias: La asignación de permisos secundarios expande automáticamente los permisos padre declarados en `depends_on`.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from db.base import Role, Permission, RolePermission, User
from schemas.role import RoleCreate, RoleUpdate, RolePermissionsAssignRequest


""" Obtener catálogo maestro de permisos del sistema """
def get_permissions(db: Session) -> List[Permission]:
    """
    Retorna el catálogo completo de permisos maestros ordenados por módulo y código.
    Los permisos son inmutables y definidos por el sistema.
    """
    return db.query(Permission).order_by(Permission.module, Permission.permission_code).all()


""" Obtener lista de todos los roles con métricas enriquecidas """
def get_roles(db: Session) -> List[Dict[str, Any]]:
    """
    Retorna todos los roles del sistema con su conteo de usuarios y códigos de permisos asignados.
    """
    roles = db.query(Role).order_by(Role.role_id).all()
    results = []

    for role in roles:
        users_count = db.query(func.count(User.user_id)).filter(User.role_id == role.role_id).scalar() or 0
        perms = [rp.permission_code for rp in role.permissions] if role.permissions else []
        results.append({
            "role_id": role.role_id,
            "name": role.name,
            "slug": role.slug,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "users_count": users_count,
            "permissions": perms,
            "created_at": role.created_at.isoformat() if role.created_at else None,
            "updated_at": role.updated_at.isoformat() if role.updated_at else None
        })

    return results


""" Obtener un rol por su ID """
def get_role_by_id(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.role_id == role_id).first()


""" Obtener un rol por su slug """
def get_role_by_slug(db: Session, slug: str) -> Optional[Role]:
    return db.query(Role).filter(Role.slug == slug.strip().lower()).first()


""" Resuelve recursivamente las dependencias de permisos declaradas en depends_on """
def resolve_permission_dependencies(db: Session, permission_codes: List[str]) -> List[str]:
    """
    Dada una lista de códigos de permisos, inspecciona la tabla permissions y
    agrega automáticamente todos los permisos ancestros requeridos por depends_on.
    Garantiza que ningún rol tenga un permiso secundario sin su dependencia requerida.
    """
    if not permission_codes:
        return []

    # Obtener el mapa de dependencias de todos los permisos en la base de datos
    all_perms = db.query(Permission.permission_code, Permission.depends_on).all()
    dep_map = {p[0]: p[1] for p in all_perms}

    resolved = set(permission_codes)
    changed = True
    while changed:
        changed = False
        to_add = set()
        for code in resolved:
            parent = dep_map.get(code)
            if parent and parent not in resolved:
                to_add.add(parent)
                changed = True
        resolved.update(to_add)

    return list(resolved)


""" Crear un nuevo rol personalizado """
def create_role(db: Session, role_data: RoleCreate) -> Role:
    """
    Crea un nuevo rol en el sistema y le asocia los permisos solicitados.
    Los roles creados desde la API siempre se marcan como no protegidos (is_system = False).
    Valida que los códigos de permisos existan en el catálogo maestro y resuelve sus dependencias.
    """
    normalized_slug = role_data.slug.strip().lower()

    # Validar slug único
    existing_role = get_role_by_slug(db, normalized_slug)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un rol con el slug '{normalized_slug}'"
        )

    # Validar permisos en catálogo
    if role_data.permissions:
        valid_perms = set(
            p[0] for p in db.query(Permission.permission_code).filter(
                Permission.permission_code.in_(role_data.permissions)
            ).all()
        )
        invalid_perms = set(role_data.permissions) - valid_perms
        if invalid_perms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Los siguientes códigos de permiso no existen en el catálogo: {list(invalid_perms)}"
            )

    new_role = Role(
        name=role_data.name.strip(),
        slug=normalized_slug,
        description=role_data.description,
        is_system=False,
        is_active=role_data.is_active
    )
    db.add(new_role)
    db.flush()

    # Asignar permisos validados expandiendo dependencias
    resolved_permissions = resolve_permission_dependencies(db, role_data.permissions)
    for code in resolved_permissions:
        db.add(RolePermission(role_id=new_role.role_id, permission_code=code))

    db.commit()
    db.refresh(new_role)
    return new_role


""" Actualizar un rol existente """
def update_role(db: Session, role_id: int, role_data: RoleUpdate) -> Role:
    """
    Actualiza la información básica y/o permisos de un rol.
    Para el rol 'admin' (Administrador General), los campos name, slug, description e is_active
    son estrictamente inmutables; únicamente se permite actualizar su matriz de permisos.
    Para cualquier otro rol, se permite renombrar, modificar slug, descripción, estado activo y permisos.
    """
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol con ID {role_id} no encontrado"
        )

    is_admin = (role.slug == "admin" or role.role_id == 1)

    if is_admin:
        # Los datos básicos de Administrador General son estrictamente inmutables
        # Asegurar integridad de valores protegidos
        role.name = "Administrador General"
        role.slug = "admin"
        role.is_active = True
        
        # Solo se permite actualizar la matriz de permisos
        if role_data.permissions is not None:
            valid_perms = set(
                p[0] for p in db.query(Permission.permission_code).filter(
                    Permission.permission_code.in_(role_data.permissions)
                ).all()
            )
            invalid_perms = set(role_data.permissions) - valid_perms
            if invalid_perms:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Los siguientes códigos de permiso no existen: {list(invalid_perms)}"
                )

            resolved_permissions = resolve_permission_dependencies(db, role_data.permissions)
            db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
            for code in resolved_permissions:
                db.add(RolePermission(role_id=role_id, permission_code=code))

        db.commit()
        db.refresh(role)
        return role

    # --- Resto de roles (no admin) ---
    # Validar y actualizar slug si fue proporcionado
    if role_data.slug is not None:
        new_slug = role_data.slug.strip().lower()
        if new_slug == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El slug 'admin' está reservado exclusivamente para el Administrador General del sistema."
            )
        if new_slug != role.slug:
            existing = db.query(Role).filter(Role.slug == new_slug, Role.role_id != role_id).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe otro rol con el slug '{new_slug}'"
                )
            role.slug = new_slug

    # Renombrar
    if role_data.name is not None:
        role.name = role_data.name.strip()

    # Modificar descripción
    if role_data.description is not None:
        role.description = role_data.description

    # Modificar estado activo
    if role_data.is_active is not None:
        role.is_active = role_data.is_active

    # Modificar matriz de permisos
    if role_data.permissions is not None:
        valid_perms = set(
            p[0] for p in db.query(Permission.permission_code).filter(
                Permission.permission_code.in_(role_data.permissions)
            ).all()
        )
        invalid_perms = set(role_data.permissions) - valid_perms
        if invalid_perms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Los siguientes códigos de permiso no existen: {list(invalid_perms)}"
            )

        resolved_permissions = resolve_permission_dependencies(db, role_data.permissions)
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for code in resolved_permissions:
            db.add(RolePermission(role_id=role_id, permission_code=code))

    db.commit()
    db.refresh(role)
    return role


""" Eliminar un rol """
def delete_role(db: Session, role_id: int) -> Role:
    """
    Elimina un rol del sistema.
    Reglas de negocio:
    - El rol 'admin' (Administrador General) es vital e inmutable, no puede ser eliminado bajo ninguna circunstancia.
    - Cualquier otro rol puede ser eliminado siempre y cuando no tenga usuarios asociados (users_count == 0).
    - Si tiene usuarios asociados, se rechaza la solicitud hasta que se reasignen o desvinculen todos sus usuarios.
    - Al eliminarse el rol, sus permisos asignados se eliminan automáticamente en cascada.
    """
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol con ID {role_id} no encontrado"
        )

    # Protección absoluta del Administrador General
    if role.slug == "admin" or role.role_id == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol Administrador General ('admin') es el rol protegido principal del sistema y no puede ser eliminado."
        )

    # Verificar si hay usuarios asociados al rol
    users_count = db.query(func.count(User.user_id)).filter(User.role_id == role_id).scalar() or 0
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar el rol '{role.name}' porque tiene {users_count} usuario(s) asignado(s). Debe reasignar o desvincular todos sus usuarios antes de eliminar este rol."
        )

    # Eliminar en cascada los permisos del rol (vía foreign key ON DELETE CASCADE y ORM cascade) y el rol
    db.delete(role)
    db.commit()
    return role


""" Asignar masivamente permisos a un rol """
def assign_role_permissions(db: Session, role_id: int, permissions: List[str]) -> Role:
    """
    Reemplaza la lista completa de permisos asignados a un rol, resolviendo dependencias jerárquicas.
    """
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol con ID {role_id} no encontrado"
        )

    if permissions:
        valid_perms = set(
            p[0] for p in db.query(Permission.permission_code).filter(
                Permission.permission_code.in_(permissions)
            ).all()
        )
        invalid_perms = set(permissions) - valid_perms
        if invalid_perms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permisos no reconocidos en el catálogo maestro: {list(invalid_perms)}"
            )

    # Reemplazar permisos resolviendo dependencias requeridas
    resolved_permissions = resolve_permission_dependencies(db, permissions)
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    for code in resolved_permissions:
        db.add(RolePermission(role_id=role_id, permission_code=code))

    db.commit()
    db.refresh(role)
    return role
