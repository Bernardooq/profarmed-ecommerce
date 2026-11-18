"""
CRUD y Gestión Integral de Grupos Comerciales (Commercial Groups):

Funciones y Operaciones:
- Operaciones CRUD básicas de grupos de ventas (crear, listar, actualizar, eliminar).
- Asignación y desasignación unificada de colaboradores internos a grupos (relación N:M mediante GroupUser).
- Asignación de Clientes a grupos (relación N:1 en CustomerInfo.sales_group_id).
- Búsqueda, filtrado, conteo y paginación Lookahead de miembros por grupo.
- Desglose dinámico de miembros por rol (RoleBreakdown / members_by_role) independiente de N roles.
- Asignación masiva de múltiples grupos a colaboradores internos.

Estructura y Reglas de Negocio PBAC / RBAC Dinámico:
1. Colaboradores Internos (N Roles):
   - Pueden pertenecer a múltiples grupos comerciales (N:M mediante GroupUser).
   - Tienen visibilidad operativa sobre clientes, pedidos y tickets de sus grupos asignados.
   - Usuarios con permisos globales (ej. `orders.view_all`, `customers.view_all`, `system.admin`) tienen acceso transversal.
2. Clientes (Customers):
   - Pertenecen a un grupo de ventas a la vez (CustomerInfo.sales_group_id).
   - Al cambiar de grupo, se recalculan y sincronizan automáticamente las estadísticas desnormalizadas (OrderStats).
3. Permisos Requeridos:
   - Consulta de grupos y miembros: `groups.view`.
   - Administración de grupos y asignaciones de miembros: `groups.manage`.
   - Asignación de clientes a grupos: `customers.assign`.
"""

from typing import List, Optional, Union
from collections import defaultdict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, distinct
from fastapi import HTTPException, status

from db.base import (
    SalesGroup, GroupUser,
    User, Customer, CustomerInfo, OrderStat,
    Role, RolePermission
)
from schemas.sales_group import (
    SalesGroupCreate, 
    SalesGroupUpdate,
    SalesGroupWithMembers
)
from crud.crud_order_stats import sync_customer_group_change, sync_group_delete

### FUNCIONES CRUD BASICAS DE GRUPOS ###
""" Crea un nuevo grupo de ventas """
def create_sales_group(db: Session, group: SalesGroupCreate) -> SalesGroup:
    db_group = SalesGroup(**group.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

""" Obtiene un grupo de ventas por ID """
def get_sales_group(db: Session, group_id: int) -> Optional[SalesGroup]:
    return db.query(SalesGroup).filter(
        SalesGroup.sales_group_id == group_id
    ).first()

""" Obtiene lista de grupos de ventas con filtros """
def get_sales_groups(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    allowed_group_ids: Optional[List[int]] = None
) -> List[SalesGroup]:
    query = db.query(SalesGroup)
    
    if allowed_group_ids is not None:
        query = query.filter(SalesGroup.sales_group_id.in_(allowed_group_ids))
        
    if is_active is not None:
        query = query.filter(SalesGroup.is_active == is_active)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            SalesGroup.group_name.ilike(search_term)
        )
    total = query.count()
    return query.offset(skip).limit(limit).all(), total

""" Actualiza un grupo de ventas existente """
def update_sales_group(db: Session, group_id: int, group: SalesGroupUpdate) -> Optional[SalesGroup]:
    db_group = get_sales_group(db, group_id)
    if not db_group:
        return None
    
    update_data = group.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_group, field, value)
    
    db.commit()
    db.refresh(db_group)
    return db_group

""" Elimina un grupo de ventas """
def delete_sales_group(db: Session, group_id: int) -> Optional[SalesGroup]:
    db_group = get_sales_group(db, group_id)
    if db_group:
        db.delete(db_group)
        db.commit()
        sync_group_delete(db, group_id)
    return db_group

""" Obtiene múltiples grupos con contadores de miembros y desglose por rol en consultas agrupadas O(1) """
def get_sales_groups_with_counts_batch(db: Session, groups: List[SalesGroup]) -> List[SalesGroupWithMembers]:
    if not groups:
        return []
    
    group_ids = [g.sales_group_id for g in groups]

    # 1. Total de miembros por grupo (GroupUser N:M) en una sola consulta
    member_counts = dict(
        db.query(GroupUser.sales_group_id, func.count(GroupUser.user_id))
        .filter(GroupUser.sales_group_id.in_(group_ids))
        .group_by(GroupUser.sales_group_id)
        .all()
    )

    # 2. Desglose dinámico de miembros por rol dentro de estos grupos en una sola consulta
    members_by_role_data = (
        db.query(GroupUser.sales_group_id, Role.role_id, Role.name, Role.slug, func.count(User.user_id))
        .join(User, User.user_id == GroupUser.user_id)
        .join(Role, Role.role_id == User.role_id)
        .filter(
            GroupUser.sales_group_id.in_(group_ids),
            User.is_active == True,
            Role.slug != "admin"
        )
        .group_by(GroupUser.sales_group_id, Role.role_id, Role.name, Role.slug)
        .all()
    )
    roles_by_group = defaultdict(list)
    for gid, rid, rname, rslug, cnt in members_by_role_data:
        roles_by_group[gid].append({"role_id": rid, "name": rname, "slug": rslug, "count": cnt})

    # 3. Total de clientes asignados por grupo en una sola consulta
    customer_counts = dict(
        db.query(CustomerInfo.sales_group_id, func.count(CustomerInfo.customer_info_id))
        .filter(CustomerInfo.sales_group_id.in_(group_ids))
        .group_by(CustomerInfo.sales_group_id)
        .all()
    )

    # 4. Estadísticas desnormalizadas de pedidos en una sola consulta
    stats_data = (
        db.query(OrderStat.sales_group_id, OrderStat.status, OrderStat.count)
        .filter(OrderStat.sales_group_id.in_(group_ids))
        .all()
    )
    stats_by_group = defaultdict(dict)
    for gid, st, cnt in stats_data:
        stats_by_group[gid][st] = cnt

    results = []
    for g in groups:
        gid = g.sales_group_id
        g_dict = {k: v for k, v in g.__dict__.items() if not k.startswith('_')}
        results.append(
            SalesGroupWithMembers(
                **g_dict,
                member_count=member_counts.get(gid, 0),
                members_by_role=roles_by_group.get(gid, []),
                customer_count=customer_counts.get(gid, 0),
                order_stats=stats_by_group.get(gid, {})
            )
        )
    return results

""" Obtiene un grupo con contadores de miembros y desglose dinámico por rol """
def get_sales_group_with_counts(db: Session, group_id: int) -> Optional[SalesGroupWithMembers]:
    db_group = get_sales_group(db, group_id)
    if not db_group:
        return None
    res = get_sales_groups_with_counts_batch(db, [db_group])
    return res[0] if res else None

### FUNCIONES UNIFICADAS DE MIEMBROS DE GRUPO (RBAC / PBAC DINÁMICO) ###

def assign_member_to_group(db: Session, group_id: int, user_id: int) -> GroupUser:
    """
    Asigna cualquier usuario activo (no admin) a un grupo de ventas (GroupUser N:M).
    Totalmente agnóstico del rol del usuario (sea vendedor, marketing, capataz, etc.).
    """
    group = get_sales_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de ventas no encontrado"
        )
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    is_admin = bool(
        getattr(user, "role_id", None) == 1
        or getattr(user, "role_slug", None) == "admin"
        or getattr(user, "role", None) == "admin"
        or getattr(user, "user_id", 0) >= 15_000_000
        or (hasattr(user, "has_permission") and user.has_permission("system.admin"))
    )
    if is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los administradores tienen acceso omnisciente global y no se asignan a grupos"
        )
    
    existing = db.query(GroupUser).filter(
        and_(
            GroupUser.sales_group_id == group_id,
            GroupUser.user_id == user_id
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya está asignado a este grupo de ventas"
        )
    
    assignment = GroupUser(
        sales_group_id=group_id,
        user_id=user_id
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def remove_member_from_group(db: Session, group_id: int, user_id: int) -> bool:
    """
    Remueve a un usuario de un grupo de ventas.
    """
    assignment = db.query(GroupUser).filter(
        and_(
            GroupUser.sales_group_id == group_id,
            GroupUser.user_id == user_id
        )
    ).first()
    
    if assignment:
        db.delete(assignment)
        db.commit()
        return True
    return False


def _build_role_filter(role_str: str):
    """
    Construye un filtro 100% dinámico para roles en grupos comerciales.
    Compara de forma agnóstica contra el slug y el nombre del rol registrado en la BD,
    permitiendo filtrar cualquier rol personalizado o del sistema de forma dinámica
    sin depender de IDs fijos ni ramas quemadas en código.
    """
    clean_role = role_str.strip().lower()
    return or_(
        Role.slug == clean_role,
        Role.slug.ilike(f"{clean_role}%"),
        Role.name.ilike(f"%{clean_role}%")
    )


def get_group_members(
    db: Session,
    group_id: int,
    role: Optional[Union[str, int]] = None,
    role_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None
) -> List[User]:
    """
    Obtiene los miembros de un grupo de ventas (GroupUser N:M).
    Permite filtrar opcionalmente por rol (id, slug o nombre) o consultar todos los miembros.
    Completamente dinámico e independiente de N roles (vendedor, marketing, capataz, etc.).
    """
    query = db.query(User).join(
        GroupUser,
        User.user_id == GroupUser.user_id
    ).join(
        Role, Role.role_id == User.role_id
    ).filter(
        GroupUser.sales_group_id == group_id,
        User.is_active == True,
        Role.slug != "admin",
        Role.role_id != 1,
        User.user_id < 15_000_000
    )

    if role_id is not None:
        query = query.filter(User.role_id == role_id)
    elif role is not None and str(role).strip():
        role_str = str(role).strip()
        if role_str.isdigit():
            query = query.filter(User.role_id == int(role_str))
        else:
            query = query.filter(_build_role_filter(role_str))

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        )

    return query.order_by(User.full_name).offset(skip).limit(limit).all()


def get_available_members(
    db: Session,
    group_id: int,
    role: Optional[Union[str, int]] = None,
    role_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None
) -> List[User]:
    """
    Obtiene usuarios activos no asignados al grupo.
    Permite filtrar opcionalmente por rol (id, slug o nombre) o consultar todos los disponibles.
    Completamente dinámico e independiente de N roles.
    """
    group = get_sales_group(db, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo de ventas no encontrado")

    assigned_ids = db.query(GroupUser.user_id).filter(
        GroupUser.sales_group_id == group_id
    ).scalar_subquery()

    query = db.query(User).join(
        Role, Role.role_id == User.role_id
    ).filter(
        User.is_active == True,
        Role.slug != "admin",
        Role.role_id != 1,
        User.user_id < 15_000_000,
        ~User.user_id.in_(assigned_ids)
    )

    if role_id is not None:
        query = query.filter(User.role_id == role_id)
    elif role is not None and str(role).strip():
        role_str = str(role).strip()
        if role_str.isdigit():
            query = query.filter(User.role_id == int(role_str))
        else:
            query = query.filter(_build_role_filter(role_str))

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        )

    return query.order_by(User.full_name).offset(skip).limit(limit).all()

### FUNCIONES PARA CUSTOMERS ###
""" Asigna un cliente a un grupo (N:1) """
def assign_customer_to_sales_group(db: Session, group_id: int, customer_id: int) -> CustomerInfo:
    group = get_sales_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de ventas no encontrado"
        )

    # Validar customer
    customer = db.query(CustomerInfo).filter(CustomerInfo.customer_id == customer_id).first()
    if not customer:
        # Verificar si el cliente existe en la tabla principal
        base_customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not base_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer no encontrado"
            )
        # Si existe pero no tiene CustomerInfo, lo creamos
        # Se agregan defaults a business_name y rfc para evitar violations de NOT NULL en la DB
        customer = CustomerInfo(
            customer_id=customer_id, 
            sales_group_id=group_id,
            business_name=base_customer.full_name or " ",
            rfc=" "
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        sync_customer_group_change(db, customer_id, None, group_id)
        return customer

    # Verificar si ya tiene un grupo asignado (N:1)
    if customer.sales_group_id is not None:
        if customer.sales_group_id == group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El cliente ya esta en este grupo"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El cliente ya pertenece a otro grupo (ID: {customer.sales_group_id})"
            )

    customer.sales_group_id = group_id
    db.commit()
    db.refresh(customer)
    sync_customer_group_change(db, customer_id, None, group_id)
    return customer

""" Obtiene todos los clientes de un grupo """
def get_group_customers(db: Session, group_id: int) -> List[Customer]:
    return db.query(Customer).join(
        CustomerInfo,
        Customer.customer_id == CustomerInfo.customer_id
    ).filter(
        CustomerInfo.sales_group_id == group_id
    ).all()

""" Obtiene clientes paginados con busqueda """
def get_group_customers_paginated(db: Session, group_id: int, skip: int = 0, limit: int = 50, search: Optional[str] = None) -> List[Customer]:    
    query = db.query(Customer).options(joinedload(Customer.customer_info)).join(
        CustomerInfo,
        Customer.customer_id == CustomerInfo.customer_id
    ).filter(
        CustomerInfo.sales_group_id == group_id
    )
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Customer.full_name.ilike(search_term),
                Customer.username.ilike(search_term),
                Customer.email.ilike(search_term),
                CustomerInfo.rfc.ilike(search_term)
            )
        )
    
    return query.offset(skip).limit(limit).all()

""" Remueve un customer de un grupo """
def remove_customer_from_sales_group(db: Session, group_id: int, customer_id: int) -> bool:
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == customer_id,
        CustomerInfo.sales_group_id == group_id
    ).first()

    if not customer_info:
        return False

    customer_info.sales_group_id = None
    db.commit()
    sync_customer_group_change(db, customer_id, group_id, None)
    return True


# FUNCIONES PARA MODALES DE CLIENTES

""" Obtiene customers NO asignados al grupo """
def get_available_customers(db: Session, group_id: int, skip: int = 0, limit: int = 50, search: Optional[str] = None) -> List[Customer]:
    # Obtener IDs de customers que ya tienen un grupo asignado (CUALQUIER GRUPO)
    # Ya que un cliente es N:1 con grupos, si tiene un sales_group_id, no esta disponible.
    assigned_ids = db.query(CustomerInfo.customer_id).filter(
        CustomerInfo.sales_group_id.isnot(None)
    ).scalar_subquery()
    
    # Query: customers NO en esa subquery (es decir, sin grupo asignado)
    query = db.query(Customer).options(joinedload(Customer.customer_info)).filter(
        ~Customer.customer_id.in_(assigned_ids)
    )
    
    if search:
        search_term = f"%{search}%"
        # Necesitamos join con CustomerInfo para buscar por RFC
        query = query.outerjoin(Customer.customer_info).filter(
            or_(
                Customer.full_name.ilike(search_term),
                Customer.username.ilike(search_term),
                Customer.email.ilike(search_term),
                CustomerInfo.rfc.ilike(search_term)
            )
        )
    return query.order_by(Customer.full_name).offset(skip).limit(limit).all()


# UTILIDADES
""" Obtiene IDs de grupos donde esta asignado un usuario """
def get_user_groups(db: Session, user_id: int) -> List[int]:
    groups = db.query(GroupUser.sales_group_id).filter(
        GroupUser.user_id == user_id
    ).all()
    return list({g[0] for g in groups})

""" Verifica si un usuario puede gestionar pedidos de un cliente """
def user_can_manage_order(db: Session, user_id: int, customer_id: int, user_role=None, order=None) -> bool:        
    # Resolver objeto con capacidad has_permission (User o Role)
    user_target = None
    if hasattr(user_role, "has_permission"):
        user_target = user_role
    elif user_id:
        from db.base import User
        user_target = db.query(User).filter(User.user_id == user_id).first()

    # 1. Admin o Super Administrador (Bypass Maestro Absoluto)
    role_str = getattr(user_role, "value", str(user_role)) if user_role else ""
    role_slug = getattr(user_role, "role_slug", None)
    if role_str == "admin" or role_slug == "admin" or user_role == "admin":
        return True
    
    if user_target and user_target.has_permission("system.admin"):
        return True

    # 2. Gestor Global con alcance nacional (AND estricto):
    # Requiere ver todos los pedidos Y tener capacidades de gestión/acción
    if user_target and user_target.has_permission("orders.view_all"):
        has_action_perm = any(
            user_target.has_permission(p) for p in [
                "orders.status",
                "orders.approve",
                "orders.ship",
                "orders.deliver",
                "orders.cancel",
                "orders.assign"
            ]
        )
        if has_action_perm:
            return True
        # Si tiene orders.view_all pero es consulta contextual de cliente (sin modificar un pedido)
        if order is None:
            return True
    
    # 3. Validación de Grupo Comercial Obligatoria:
    # El usuario DEBE pertenecer al grupo comercial del cliente
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == customer_id
    ).first()
    
    if not customer_info or not customer_info.sales_group_id:
        # Cliente sin grupo comercial asignado
        return False
    
    user_groups = get_user_groups(db, user_id)
    if customer_info.sales_group_id not in user_groups:
        return False
    
    # 4. El usuario pertenece al grupo comercial del cliente:
    # Si tiene permisos de gestión o asignación dentro de su grupo comercial
    has_group_management = (
        user_target and (
            user_target.has_permission("orders.group_view") or
            user_target.has_permission("orders.status") or
            user_target.has_permission("orders.approve") or
            user_target.has_permission("orders.ship") or
            user_target.has_permission("orders.deliver") or
            user_target.has_permission("orders.cancel") or
            user_target.has_permission("orders.assign")
        )
    )
    if has_group_management:
        return True

    # 5. Vendedor base dentro del grupo (solo con orders.view):
    # Solo puede ver/gestionar pedidos asignados directamente a él
    if order:
        return getattr(order, "assigned_user_id", None) == user_id
    
    # Si no se especificó un pedido (ej. consulta contextual de cliente), se permite por pertenecer al grupo
    return True

""" Verifica si un usuario pertenece a un grupo especifico """
def user_belongs_to_group(db: Session, user_id: int, group_id: int) -> bool:    
    user_groups = get_user_groups(db, user_id)
    return group_id in user_groups

""" Asignacion masiva de grupos a un usuario """
def assign_user_groups_bulk(db: Session, user_id: int, group_ids: List[int]) -> dict:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError("Usuario no encontrado")

    is_admin = bool(getattr(user, "role_slug", None) == "admin" or getattr(user, "role", None) == "admin" or (hasattr(user, "has_permission") and user.has_permission("system.admin")))
    if is_admin:
        raise ValueError("No se pueden asignar grupos a un administrador")

    # Validar grupos
    if group_ids:
        existing = db.query(SalesGroup.sales_group_id).filter(SalesGroup.sales_group_id.in_(group_ids)).all()
        existing_ids = {g[0] for g in existing}
        if len(existing_ids) != len(set(group_ids)):
            raise ValueError("Uno o más IDs de grupo proporcionados no existen.")

    # Borrar asignaciones existentes del usuario en GroupUser
    db.query(GroupUser).filter(GroupUser.user_id == user_id).delete(synchronize_session=False)
    
    # Insertar nuevas asignaciones si las hay
    if group_ids:
        new_memberships = [GroupUser(sales_group_id=g_id, user_id=user_id) for g_id in set(group_ids)]
        db.bulk_save_objects(new_memberships)

    db.commit()
    return {
        "message": f"Grupos asignados exitosamente a {user.full_name}",
        "assigned_groups_count": len(group_ids)
    }