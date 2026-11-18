"""
Utilidades para manejo de grupos comerciales y asignaciones (Sales Group Utils)

Funciones desacopladas para gestionar la asignación automática y en lote
de clientes y colaboradores internos a grupos de venta/operativos.
Diseñado para operar con el sistema dinámico RBAC/PBAC de N roles.
"""

from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from db.base import User, SalesGroup, GroupUser, CustomerInfo, SystemConfig
from schemas.sales_group import SalesGroupCreate
from crud.crud_commercial_group import (
    create_sales_group,
    assign_member_to_group,
    assign_customer_to_sales_group,
    remove_customer_from_sales_group
)

CONFIG_AUTO_CREATE_SALES_GROUP = "user.auto_create_sales_group"
CONFIG_AUTO_ASSIGN_AGENT_GROUP = "customer.auto_assign_agent_group"


def is_auto_create_sales_group_enabled(db: Session) -> bool:
    """
    Verifica si la directiva operacional 'user.auto_create_sales_group' (ID 105)
    está activa en system_configs.
    """
    try:
        conf = db.query(SystemConfig).filter(
            (SystemConfig.config_id == 105) | (SystemConfig.config_name == CONFIG_AUTO_CREATE_SALES_GROUP)
        ).first()
        return bool(conf.is_active) if conf else False
    except Exception as e:
        print(f"[SALES_GROUP_UTILS] Error consultando bandera '{CONFIG_AUTO_CREATE_SALES_GROUP}': {e}")
        return False


def is_auto_assign_agent_group_enabled(db: Session) -> bool:
    """
    Verifica si la directiva operacional 'customer.auto_assign_agent_group' (ID 106)
    está activa en system_configs.
    """
    try:
        conf = db.query(SystemConfig).filter(
            (SystemConfig.config_id == 106) | (SystemConfig.config_name == CONFIG_AUTO_ASSIGN_AGENT_GROUP)
        ).first()
        return bool(conf.is_active) if conf else False
    except Exception as e:
        print(f"[SALES_GROUP_UTILS] Error consultando bandera '{CONFIG_AUTO_ASSIGN_AGENT_GROUP}': {e}")
        return False


def bulk_ensure_user_groups(db: Session, user_ids: List[int]) -> None:
    """
    Asegura que existan grupos comerciales y membresías para una lista de usuarios.
    Crea los grupos faltantes de forma dinámica y vincula a los colaboradores a ellos.
    Evalúa la bandera operacional 'user.auto_create_sales_group'.
    
    Args:
        db: Sesión de base de datos
        user_ids: Lista de IDs de usuarios internos
    """
    if not user_ids:
        return

    # Verificar si la creación automática de grupos está habilitada
    if not is_auto_create_sales_group_enabled(db):
        return

    # 1. Obtener todos los usuarios en una sola query
    users = db.query(User).filter(User.user_id.in_(user_ids)).all()
    if not users:
        return
        
    # 2. Crear nombres de grupos esperados
    expected_group_names = [f"Grupo {u.full_name or u.username}" for u in users]
    
    # 3. Obtener grupos existentes en una sola query
    existing_groups = db.query(SalesGroup).filter(
        SalesGroup.group_name.in_(expected_group_names)
    ).all()
    group_name_map = {g.group_name: g for g in existing_groups}
    
    # 4. Crear grupos faltantes en bulk
    groups_to_create = []
    for u in users:
        group_name = f"Grupo {u.full_name or u.username}"
        if group_name not in group_name_map:
            groups_to_create.append({
                'group_name': group_name,
                'description': f"Grupo comercial automático para {u.full_name or u.username}",
                'is_active': True
            })
    
    if groups_to_create:
        stmt = insert(SalesGroup).values(groups_to_create)
        db.execute(stmt)
        
        # Recargar grupos creados para mapeo completo
        new_group_names = [g['group_name'] for g in groups_to_create]
        new_groups = db.query(SalesGroup).filter(
            SalesGroup.group_name.in_(new_group_names)
        ).all()
        for group in new_groups:
            group_name_map[group.group_name] = group
            
    # 5. Asignar usuarios comerciales u operativos a sus grupos (bulk upsert)
    user_assignments = []
    for u in users:
        # Administradores globales tienen alcance total y no se confinan a un único grupo
        is_admin = bool(
            u.role_id == 1 or 
            getattr(u, "role_slug", None) == "admin" or 
            getattr(u, "role", None) == "admin" or 
            (hasattr(u, "has_permission") and u.has_permission("system.admin"))
        )
        if is_admin:
            continue
            
        group_name = f"Grupo {u.full_name or u.username}"
        group = group_name_map.get(group_name)
        if group:
            user_assignments.append({
                'sales_group_id': group.sales_group_id,
                'user_id': u.user_id
            })
    
    if user_assignments:
        stmt = insert(GroupUser).values(user_assignments)
        stmt = stmt.on_conflict_do_nothing(index_elements=['sales_group_id', 'user_id'])
        db.execute(stmt)
        db.commit()


def auto_crear_grupo_usuario(db: Session, user: User) -> None:
    """
    Auto-crea un grupo comercial/operativo para un usuario si no existe.
    Wrapper dinámico para bulk_ensure_user_groups que evalúa 'user.auto_create_sales_group'.
    """
    if not is_auto_create_sales_group_enabled(db):
        return
    if user and user.user_id:
        bulk_ensure_user_groups(db, [user.user_id])


def assign_customer_to_agent_group(db: Session, customer_id: int, agent_id: int) -> None:
    """
    Asigna un cliente al grupo comercial del colaborador responsable (agente/usuario).
    Si el usuario no tiene grupo, busca o crea uno llamado 'Grupo {user.full_name}'
    (respetando las directivas 'customer.auto_assign_agent_group' y 'user.auto_create_sales_group').
    
    Args:
        db: Sesión de base de datos
        customer_id: ID del cliente a asignar
        agent_id: ID del usuario/agente responsable
    """
    # Verificar directiva de auto-asignación de cliente a grupo del agente
    if not is_auto_assign_agent_group_enabled(db):
        return

    # Obtener colaborador interno
    user = db.query(User).filter(User.user_id == agent_id).first()
    if not user:
        return  # Usuario no existe, no hacer nada
    
    # Buscar grupo del colaborador por nombre
    group_name = f"Grupo {user.full_name or user.username}"
    group = db.query(SalesGroup).filter(SalesGroup.group_name == group_name).first()
    
    if not group:
        # Si la directiva de crear grupos automáticos está apagada, no creamos grupo
        if not is_auto_create_sales_group_enabled(db):
            return

        # Crear grupo automáticamente
        group = create_sales_group(db, SalesGroupCreate(
            group_name=group_name,
            description=f"Grupo comercial automático para {user.full_name or user.username}",
            is_active=True
        ))
        
        # Asignar colaborador al grupo
        try:
            assign_member_to_group(db, group.sales_group_id, user.user_id)
        except Exception:
            pass  # Ya está asignado
    
    # Asignar cliente al grupo
    customer_info = db.query(CustomerInfo).filter(CustomerInfo.customer_id == customer_id).first()
    
    if customer_info and customer_info.sales_group_id:
        if customer_info.sales_group_id == group.sales_group_id:
            return  # Ya está en el grupo correcto
            
        # Remover del grupo anterior
        try:
            remove_customer_from_sales_group(db, customer_info.sales_group_id, customer_id)
        except Exception as e:
            print(f"Error removing customer from previous group: {e}")
            
    # Asignar al nuevo grupo
    try:
        if not customer_info:
            new_info = CustomerInfo(
                customer_id=customer_id,
                business_name=f"Cliente {customer_id}"
            )
            db.add(new_info)
            db.commit()
            
        assign_customer_to_sales_group(db, group.sales_group_id, customer_id)
    except Exception as e:
        print(f"Error assigning customer to group: {e}")
        if customer_info:
            customer_info.sales_group_id = group.sales_group_id
            db.commit()


def bulk_assign_customers_to_agent_groups(db: Session, customer_agent_pairs: List[Dict]) -> None:
    """
    Asigna múltiples clientes a los grupos comerciales de sus colaboradores de forma optimizada (BULK).
    Respeta la directiva operacional 'customer.auto_assign_agent_group'.
    
    Args:
        db: Sesión de base de datos
        customer_agent_pairs: Lista de dicts con {'customer_id': int, 'agent_id': int}
    """
    if not customer_agent_pairs:
        return

    # Verificar directiva de auto-asignación de cliente a grupo del agente
    if not is_auto_assign_agent_group_enabled(db):
        return
    
    # 1. Obtener todos los agent_ids únicos
    unique_agent_ids = list({pair['agent_id'] for pair in customer_agent_pairs if pair.get('agent_id')})
    if not unique_agent_ids:
        return
    
    # 2. Asegurar grupos y asignaciones de usuarios
    bulk_ensure_user_groups(db, unique_agent_ids)
    
    # 3. Obtener colaboradores y grupos para mapeo
    users = db.query(User).filter(User.user_id.in_(unique_agent_ids)).all()
    user_map = {u.user_id: u for u in users}
    
    expected_group_names = [f"Grupo {u.full_name or u.username}" for u in users]
    existing_groups = db.query(SalesGroup).filter(
        SalesGroup.group_name.in_(expected_group_names)
    ).all()
    group_name_map = {g.group_name: g for g in existing_groups}
    
    # 4. Asignar clientes a grupos (bulk update de CustomerInfo)
    for pair in customer_agent_pairs:
        agent_id = pair.get('agent_id')
        if not agent_id:
            continue
        
        assigned_user = user_map.get(agent_id)
        if not assigned_user:
            continue
        
        group_name = f"Grupo {assigned_user.full_name or assigned_user.username}"
        group = group_name_map.get(group_name)
        if group:
            db.query(CustomerInfo).filter(
                CustomerInfo.customer_id == pair['customer_id']
            ).update({'sales_group_id': group.sales_group_id})


# ============================================================================
# ALIASES RETROCOMPATIBLES (Garantizan funcionamiento sin romper imports existentes)
# ============================================================================
bulk_ensure_seller_groups = bulk_ensure_user_groups
auto_crear_grupo_seller = auto_crear_grupo_usuario
