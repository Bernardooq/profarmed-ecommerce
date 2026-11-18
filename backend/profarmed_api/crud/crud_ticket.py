"""
CRUD y Sistema de Tickets de Soporte y Atención a Clientes (Tickets):

Funciones y Operaciones:
- Crear tickets de soporte asociados opcionalmente a un pedido específico.
- Actualizar estado (open, in_progress, resolved, closed), prioridad y agente asignado.
- Consulta de tickets con filtros por estado, prioridad, creador y grupos de venta.
- Hilos de mensajería interactiva entre clientes, colaboradores y administradores (TicketMessage).
- Enriquecimiento de nombres y datos legibles de creadores y participantes.

Reglas de Visibilidad y Permisos PBAC / RBAC Dinámico:
1. Clientes (CreatorType.customer):
   - Solo pueden consultar tickets creados por ellos mismos y participar en sus hilos respectivos (aislamiento por `customer_id`).
2. Colaboradores Internos (N Roles):
   - Atienden tickets asignados directamente (`assigned_to`), creados por ellos mismos, o creados por clientes y miembros de sus grupos comerciales asignados.
3. Administradores y Permisos Globales:
   - Acceso global para consultar, reasignar, responder o cerrar cualquier ticket del sistema (`system.admin` o `tickets.manage`).
4. Permisos Requeridos:
   - Consulta de tickets: `tickets.view`.
   - Creación de tickets: `tickets.create`.
   - Respuesta a tickets: `tickets.respond`.
   - Gestión, asignación y cierre: `tickets.manage` o `tickets.close`.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from db.base import Ticket, TicketMessage, TicketStatus, CreatorType, SenderType, CustomerInfo, GroupUser, User as UserModel, Customer, Order
from schemas.ticket import TicketCreate, TicketUpdate, TicketMessageCreate
from crud.crud_commercial_group import get_user_groups

"""Crea un nuevo ticket de soporte asociado a un cliente o usuario del sistema"""
def create_ticket(db: Session, ticket: TicketCreate, creator_id: int, creator_type: CreatorType) -> Ticket:
    db_ticket = Ticket(
        title=ticket.title,
        description=ticket.description,
        priority=ticket.priority,
        order_id=ticket.order_id,
        creator_id=creator_id,
        creator_type=creator_type,
        status=TicketStatus.open
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

"""Asocia y adjunta nombres legibles de creadores y usuarios asignados a una lista de tickets"""
def attach_names_to_tickets(db: Session, tickets: List[Ticket]) -> List[Ticket]:
    if not tickets: return tickets
    
    user_ids = set()
    customer_ids = set()
    for t in tickets:
        if t.creator_type == CreatorType.user: user_ids.add(t.creator_id)
        elif t.creator_type == CreatorType.customer: customer_ids.add(t.creator_id)
        if t.assigned_to: user_ids.add(t.assigned_to)

    user_map = {}
    if user_ids:
        users = db.query(UserModel.user_id, UserModel.full_name, UserModel.username).filter(UserModel.user_id.in_(user_ids)).all()
        user_map = {u.user_id: u.full_name or u.username for u in users}

    customer_map = {}
    if customer_ids:
        customers = db.query(Customer.customer_id, Customer.full_name, Customer.username).filter(Customer.customer_id.in_(customer_ids)).all()
        customer_map = {c.customer_id: c.full_name or c.username for c in customers}

    for t in tickets:
        if t.creator_type == CreatorType.user: t.creator_name = user_map.get(t.creator_id)
        elif t.creator_type == CreatorType.customer: t.creator_name = customer_map.get(t.creator_id)
        if t.assigned_to: t.assigned_to_name = user_map.get(t.assigned_to)

    return tickets

"""Asocia y adjunta nombres legibles de los remitentes a los mensajes de un ticket"""
def attach_names_to_ticket_messages(db: Session, ticket: Ticket) -> Ticket:
    if not ticket or not ticket.messages: return ticket
    
    user_ids = set()
    customer_ids = set()
    for m in ticket.messages:
        if m.sender_type == SenderType.user: user_ids.add(m.sender_id)
        elif m.sender_type == SenderType.customer: customer_ids.add(m.sender_id)

    user_map, customer_map = {}, {}
    if user_ids:
        user_map = {u.user_id: u.full_name or u.username for u in db.query(UserModel.user_id, UserModel.full_name, UserModel.username).filter(UserModel.user_id.in_(user_ids)).all()}
    if customer_ids:
        customer_map = {c.customer_id: c.full_name or c.username for c in db.query(Customer.customer_id, Customer.full_name, Customer.username).filter(Customer.customer_id.in_(customer_ids)).all()}

    for m in ticket.messages:
        if m.sender_type == SenderType.user: m.sender_name = user_map.get(m.sender_id)
        elif m.sender_type == SenderType.customer: m.sender_name = customer_map.get(m.sender_id)

    return ticket

"""Obtiene un ticket específico por su ID enriquecido con los nombres legibles de remitentes y mensajes"""
def get_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if ticket:
        ticket = attach_names_to_tickets(db, [ticket])[0]
        ticket = attach_names_to_ticket_messages(db, ticket)
    return ticket

"""Obtiene la lista global de tickets con soporte de paginación y filtrado por estado para administradores"""
def get_tickets_for_admin(db: Session, skip: int = 0, limit: int = 100, status_filter: Optional[TicketStatus] = None) -> tuple[List[Ticket], int]:
    query = db.query(Ticket)
    if status_filter: query = query.filter(Ticket.status == status_filter)
    total = query.count()
    tickets = query.order_by(desc(Ticket.created_at)).offset(skip).limit(limit).all()
    return attach_names_to_tickets(db, tickets), total

"""Obtiene los tickets visibles para un colaborador interno según sus grupos de ventas asignados"""
def get_tickets_for_group_user(db: Session, user_id: int, skip: int = 0, limit: int = 100, status_filter: Optional[TicketStatus] = None) -> tuple[List[Ticket], int]:
    # El colaborador con pertenencia a grupos puede ver:
    # 1. Tickets que él mismo creó
    # 2. Tickets asignados a él directamente
    # 3. Tickets de clientes pertenecientes a sus grupos comerciales asignados
    # 4. Tickets de otros colaboradores en sus grupos comerciales asignados
    # 5. Tickets vinculados a pedidos de clientes pertenecientes a sus grupos
    
    group_ids = get_user_groups(db, user_id)
    if not group_ids:
        # Si no tiene grupos, solo ve los propios o directamente asignados
        query = db.query(Ticket).filter(
            or_(
                and_(Ticket.creator_id == user_id, Ticket.creator_type == CreatorType.user),
                Ticket.assigned_to == user_id
            )
        )
    else:
        # Clientes en sus grupos comerciales
        customer_ids_subquery = db.query(CustomerInfo.customer_id).filter(
            CustomerInfo.sales_group_id.in_(group_ids)
        ).scalar_subquery()
        
        # Miembros colaboradores en sus grupos comerciales
        user_ids_subquery = db.query(GroupUser.user_id).filter(
            GroupUser.sales_group_id.in_(group_ids)
        ).scalar_subquery()
        
        query = db.query(Ticket).filter(
            or_(
                # Tickets propios o asignados
                and_(Ticket.creator_id == user_id, Ticket.creator_type == CreatorType.user),
                Ticket.assigned_to == user_id,
                # Clientes en sus grupos
                and_(Ticket.creator_id.in_(customer_ids_subquery), Ticket.creator_type == CreatorType.customer),
                # Otros colaboradores en sus grupos
                and_(Ticket.creator_id.in_(user_ids_subquery), Ticket.creator_type == CreatorType.user),
                # Tickets con order_id perteneciente a clientes en sus grupos
                and_(Ticket.order_id.isnot(None), Ticket.order.has(Order.customer_id.in_(customer_ids_subquery)))
            )
        )
        
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
        
    total = query.count()
    tickets = query.order_by(desc(Ticket.created_at)).offset(skip).limit(limit).all()
    return attach_names_to_tickets(db, tickets), total

# Alias semánticos y retrocompatibles
get_tickets_for_marketing = get_tickets_for_group_user
get_tickets_for_user = get_tickets_for_group_user

"""Obtiene los tickets de soporte creados por una entidad (cliente o usuario) en específico"""
def get_tickets_for_user_or_customer(
    db: Session,
    entity_id: int,
    entity_type: CreatorType,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TicketStatus] = None
) -> tuple[List[Ticket], int]:
    query = db.query(Ticket).filter(
        Ticket.creator_id == entity_id,
        Ticket.creator_type == entity_type
    )
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    total = query.count()
    tickets = query.order_by(desc(Ticket.created_at)).offset(skip).limit(limit).all()
    return attach_names_to_tickets(db, tickets), total

"""Actualiza las propiedades de un ticket (como prioridad, agente asignado o estado)"""
def update_ticket(db: Session, ticket_id: int, update_data: TicketUpdate) -> Optional[Ticket]:
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return None
        
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_ticket, field, value)
        
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

"""Agrega un nuevo mensaje al hilo de discusión de un ticket de soporte"""
def add_ticket_message(db: Session, ticket_id: int, sender_id: int, sender_type: SenderType, content: str) -> TicketMessage:
    msg = TicketMessage(
        ticket_id=ticket_id,
        sender_id=sender_id,
        sender_type=sender_type,
        content=content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
