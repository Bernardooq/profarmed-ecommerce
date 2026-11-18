"""
Routes para Tickets de Soporte (Tickets)

Gestión completa de los tickets de asistencia técnica y sus flujos de conversación
basada en PBAC (Permission-Based Access Control) 100% dinámico.

TICKETS:
- GET / - Listar todos los tickets visibles según permisos
- POST / - Crear un nuevo ticket de soporte
- GET /{ticket_id} - Obtener el detalle de un ticket con sus respuestas enriquecidas

GESTIÓN DE TICKET (AGENTES):
- PUT /{ticket_id}/status - Cambiar estado del ticket (requiere 'support.manage')
- PUT /{ticket_id}/escalate - Escalar un ticket (requiere 'support.manage')
- PUT /{ticket_id}/de-escalate - Desescalar un ticket (requiere 'support.deescalate')
- PUT /{ticket_id}/assign - Asignarse/tomar el ticket (requiere 'support.manage')

MENSAJES DE SOPORTE:
- POST /{ticket_id}/messages - Agregar un mensaje de respuesta en el ticket
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from dependencies import get_db, get_current_user, require_permission
from db.base import TicketStatus, TicketPriority, CreatorType, SenderType, User, Customer, Order, WarehouseSplit, CustomerInfo
from schemas.ticket import TicketCreate, TicketUpdate, TicketResponse, TicketDetailResponse, TicketMessageCreate, TicketMessageResponse, TicketPaginatedResponse
from crud.crud_ticket import (
    create_ticket, get_ticket, update_ticket, add_ticket_message, attach_names_to_tickets, attach_names_to_ticket_messages,
    get_tickets_for_admin, get_tickets_for_group_user, get_tickets_for_marketing, get_tickets_for_user_or_customer
)
from crud.crud_commercial_group import get_user_groups, user_can_manage_order

router = APIRouter()

""" UTILIDAD - Obtener el ID del remitente y tipo de entidad del usuario autenticado """
def get_sender_info(current_user):
    if hasattr(current_user, 'user_id'):
        return current_user.user_id, CreatorType.user
    else:
        return current_user.customer_id, CreatorType.customer

""" GET / - Listar todos los tickets visibles según permisos """
@router.get("/", response_model=TicketPaginatedResponse)
@router.get("", response_model=TicketPaginatedResponse, include_in_schema=False)
def read_tickets(
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"),
    status_filter: Optional[TicketStatus] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    is_admin = hasattr(current_user, "has_permission") and current_user.has_permission("system.admin")
    can_manage = is_admin or (hasattr(current_user, "has_permission") and current_user.has_permission("support.manage"))

    if isinstance(current_user, User):
        if is_admin:
            tickets, total = get_tickets_for_admin(db, skip=skip, limit=limit, status_filter=status_filter)
        elif can_manage:
            tickets, total = get_tickets_for_group_user(db, user_id=current_user.user_id, skip=skip, limit=limit, status_filter=status_filter)
        else:
            tickets, total = get_tickets_for_user_or_customer(db, current_user.user_id, CreatorType.user, skip, limit, status_filter=status_filter)
    else:
        tickets, total = get_tickets_for_user_or_customer(db, current_user.customer_id, CreatorType.customer, skip, limit, status_filter=status_filter)
        
    return {"items": tickets, "total": total}

""" POST / - Crear un nuevo ticket de soporte """
@router.post("/", response_model=TicketResponse)
@router.post("", response_model=TicketResponse, include_in_schema=False)
def create_new_ticket(
    ticket_in: TicketCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entity_id, creator_type = get_sender_info(current_user)

    # Validaciones de pedido si se especificó order_id
    if ticket_in.order_id:
        order = db.query(Order).filter(Order.order_id == ticket_in.order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El Pedido #{ticket_in.order_id} no existe en el sistema."
            )

        if isinstance(current_user, User):
            is_admin = hasattr(current_user, "has_permission") and current_user.has_permission("system.admin")
            if is_admin:
                pass
            elif hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.operator") or current_user.has_permission("warehouse.view")):
                # Almacén: Debe tener al menos una split asignada en ese pedido (como picker o checker)
                has_split = db.query(WarehouseSplit).filter(
                    WarehouseSplit.order_id == order.order_id,
                    (WarehouseSplit.picker_id == current_user.user_id) | (WarehouseSplit.checker_id == current_user.user_id)
                ).first()
                if not has_split:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"No tienes splits asignados en el Pedido #{order.order_id} para reportar incidencias."
                    )
            else:
                # Colaborador comercial/interno: El pedido debe estar asignado a él o pertenecer a clientes de sus grupos asignados
                is_own = (order.assigned_user_id == current_user.user_id)
                can_manage = user_can_manage_order(db, current_user.user_id, order.customer_id, current_user)
                if not is_own and not can_manage:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"No tienes autorización para vincular un ticket al Pedido #{order.order_id}."
                    )
        else:
            # Cliente: Validar que el pedido pertenezca a este cliente
            if order.customer_id != current_user.customer_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes vincular tickets a pedidos de otros clientes."
                )

    ticket = create_ticket(db, ticket=ticket_in, creator_id=entity_id, creator_type=creator_type)
    return attach_names_to_tickets(db, [ticket])[0]

""" GET /{ticket_id} - Obtener el detalle de un ticket con sus respuestas enriquecidas """
@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def read_ticket_detail(
    ticket_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    is_admin = hasattr(current_user, "has_permission") and current_user.has_permission("system.admin")
    can_manage = is_admin or (hasattr(current_user, "has_permission") and current_user.has_permission("support.manage"))

    if is_admin:
        pass
    elif can_manage:
        # Colaborador con permiso support.manage puede ver tickets propios, asignados a él, de clientes de sus grupos o pedidos de sus grupos
        group_ids = get_user_groups(db, current_user.user_id)
        is_own = (ticket.creator_id == current_user.user_id and ticket.creator_type == CreatorType.user)
        is_assigned = (ticket.assigned_to == current_user.user_id)
        
        has_group_access = False
        if group_ids:
            if ticket.creator_type == CreatorType.customer:
                c_info = db.query(CustomerInfo).filter(CustomerInfo.customer_id == ticket.creator_id).first()
                if c_info and c_info.sales_group_id in group_ids:
                    has_group_access = True
            elif ticket.order_id:
                ord_obj = db.query(Order).filter(Order.order_id == ticket.order_id).first()
                if ord_obj:
                    c_info = db.query(CustomerInfo).filter(CustomerInfo.customer_id == ord_obj.customer_id).first()
                    if c_info and c_info.sales_group_id in group_ids:
                        has_group_access = True

        if not (is_own or is_assigned or has_group_access):
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este ticket")
    else:
        # Usuario sin support.manage o cliente
        entity_id, c_type = get_sender_info(current_user)
        is_creator = (ticket.creator_id == entity_id and ticket.creator_type == c_type)
        is_assigned = isinstance(current_user, User) and (ticket.assigned_to == current_user.user_id)
        if not is_creator and not is_assigned:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este ticket")

    return ticket

""" POST /{ticket_id}/messages - Agregar un mensaje de respuesta en el ticket """
@router.post("/{ticket_id}/messages", response_model=TicketMessageResponse)
def add_message(
    ticket_id: int,
    msg_in: TicketMessageCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
    entity_id, creator_type = get_sender_info(current_user)
    sender_type = SenderType.user if creator_type == CreatorType.user else SenderType.customer
    
    msg = add_ticket_message(db, ticket_id, sender_id=entity_id, sender_type=sender_type, content=msg_in.content)
    ticket.messages.append(msg)
    ticket = attach_names_to_ticket_messages(db, ticket)
    return ticket.messages[-1]

class TicketStatusUpdate(BaseModel):
    status: TicketStatus

""" PUT /{ticket_id}/status - Cambiar estado del ticket """
@router.put("/{ticket_id}/status", response_model=TicketResponse)
def change_ticket_status(
    ticket_id: int,
    status_update: TicketStatusUpdate,
    current_user: User = Depends(require_permission("support.manage")),
    db: Session = Depends(get_db)
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
    ticket = update_ticket(db, ticket_id, TicketUpdate(status=status_update.status))
    return attach_names_to_tickets(db, [ticket])[0]

""" PUT /{ticket_id}/escalate - Escalar un ticket a estado escalado """
@router.put("/{ticket_id}/escalate", response_model=TicketResponse)
def escalate_ticket(
    ticket_id: int,
    current_user: User = Depends(require_permission("support.manage")),
    db: Session = Depends(get_db)
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
    ticket = update_ticket(db, ticket_id, TicketUpdate(status=TicketStatus.escalated))
    return attach_names_to_tickets(db, [ticket])[0]

""" PUT /{ticket_id}/de-escalate - Desescalar un ticket escalado a en progreso """
@router.put("/{ticket_id}/de-escalate", response_model=TicketResponse)
def de_escalate_ticket(
    ticket_id: int,
    current_user: User = Depends(require_permission("support.deescalate")),
    db: Session = Depends(get_db)
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
    if ticket.status != TicketStatus.escalated:
        raise HTTPException(status_code=400, detail="Solo se pueden desescalar tickets en estado escalado")
        
    ticket = update_ticket(db, ticket_id, TicketUpdate(status=TicketStatus.in_progress))
    return attach_names_to_tickets(db, [ticket])[0]

""" PUT /{ticket_id}/assign - Asignarse/tomar el ticket """
@router.put("/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(
    ticket_id: int,
    current_user: User = Depends(require_permission("support.manage")),
    db: Session = Depends(get_db)
):
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
    status = TicketStatus.in_progress if ticket.status == TicketStatus.open else ticket.status
    
    ticket = update_ticket(db, ticket_id, TicketUpdate(assigned_to=current_user.user_id, status=status))
    return attach_names_to_tickets(db, [ticket])[0]
