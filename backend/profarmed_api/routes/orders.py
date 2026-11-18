"""
Routes para Gestion de Pedidos y Carrito

Endpoints para el ciclo completo de pedidos:

CARRITO (Clientes):
- GET /cart - Ver carrito
- POST /cart - Agregar producto
- PUT /cart/{id} - Actualizar cantidad
- DELETE /cart/{id} - Eliminar item
- DELETE /cart - Vaciar carrito

PEDIDOS (Clientes):
- POST /checkout - Crear pedido desde carrito
- GET / - Ver mis pedidos
- GET /{id} - Ver detalle de pedido
- POST /{id}/cancel - Cancelar pedido

PEDIDOS (Colaboradores / PBAC):
- GET /all - Ver todos los pedidos (según capacidades y grupos asignados)
- PUT /{id}/status - Actualizar estado
- POST /{id}/assign - Asignar agente comercial a pedido

Sistema de Permisos:
- Clientes: Solo sus propios pedidos
- Colaboradores: Pedidos acotados por capacidades PBAC y grupos asignados
- Acceso global ('system.admin'): Todos los pedidos transversalmente
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, BackgroundTasks
from typing import List, Optional
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from utils.email_utils import send_order_shipped_email, send_order_delivered_email

logger = logging.getLogger(__name__)


from dependencies import get_db, get_current_user, require_permission
from crud.crud_customer import get_customer_info
from crud.crud_user import get_user
from schemas.order import Order, OrderUpdate, OrderWithAddress, OrderAssign
from schemas.order_edit import OrderEditRequest
from schemas.order_direct import DirectOrderCreate
from schemas.cart import CartItem
from db.base import OrderStatus, User, Customer, CustomerInfo, PriceListItem, Order as OrderModel, OrderItem
from utils.pagination import get_lookahead_pagination

from crud.crud_order import (assign_order_user, calculate_order_shipping_address, get_order, get_orders_by_customer, get_orders, 
    get_orders_for_user_groups, create_order_from_cart, create_order_direct, update_order_status, cancel_order, generate_order_txt, generate_order_txt_files)

from crud.crud_order_edit import edit_order_items

from crud.crud_cart import (get_cart, add_to_cart, update_cart_item, remove_from_cart, clear_cart, import_cart_from_excel)

from crud.crud_commercial_group import get_user_groups, user_can_manage_order

router = APIRouter()


def _user_can_view_order_profit(user) -> bool:
    """
    Evalúa si un usuario posee privilegios para visualizar utilidad (order_profit),
    precios sin IVA y márgenes confidenciales en un pedido.
    
    Condiciones de acceso (PBAC):
    1. Superadministrador: Posee 'system.admin' o rol maestro 'admin'.
    2. Perfil con suite completa de analítica financiera y auditoría de pedidos:
       - Debe contar con los 4 permisos del módulo de reportes:
         'reports.view', 'reports.financial', 'reports.sales', 'reports.export'
       - Y alcance global sobre pedidos:
         'orders.view', 'orders.view_all'
    """
    if not user or not hasattr(user, "has_permission"):
        return False
    if user.has_permission("system.admin"):
        return True
    
    has_full_reports = (
        user.has_permission("reports.view") and
        user.has_permission("reports.financial") and
        user.has_permission("reports.sales") and
        user.has_permission("reports.export")
    )
    has_global_orders = (
        user.has_permission("orders.view") and
        user.has_permission("orders.view_all")
    )
    return has_full_reports and has_global_orders


def _strip_admin_fields(order_dict: dict) -> dict:
    """Strip order_profit, price_without_iva, and product.location from order responses for non-admin/customer users."""
    order_dict.pop("order_profit", None)
    if "items" in order_dict:
        for item in order_dict["items"]:
            item.pop("price_without_iva", None)
            item.pop("base_price", None)
            item.pop("markup_percentage", None)
            if item.get("product") and isinstance(item["product"], dict):
                item["product"]["location"] = ""
    return order_dict

# === CARRITO DE COMPRAS ===

class CartItemAdd(BaseModel):
    product_id: str 
    quantity: int = 1

class CartItemUpdate(BaseModel):
    quantity: int

""" GET /cart - Ver carrito por el cliente autenticado """
@router.get("/cart")
def read_cart(current_user = Depends(get_current_user), db: Session = Depends(get_db)):    
    if isinstance(current_user, Customer):
        customer_id = current_user.customer_id
    else:
        customer_id = getattr(current_user, 'user_id', None)
    
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo identificar el cliente"
        )
    
    cart_items = get_cart(db, customer_id=customer_id)
    return cart_items

""" POST /cart - Agregar producto al carrito """
@router.post("/cart")
def add_item_to_cart(item: CartItemAdd, current_user = Depends(get_current_user), db: Session = Depends(get_db)):    
    if isinstance(current_user, Customer):
        customer_id = current_user.customer_id
    else:
        customer_id = getattr(current_user, 'user_id', None)
    
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo identificar el cliente")
    
    try:
        cart_item = add_to_cart(db, customer_id=customer_id, product_id=item.product_id, quantity=item.quantity)
        return cart_item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

""" POST /cart/import-excel - Importar productos al carrito desde Excel """
@router.post("/cart/import-excel")
async def import_excel_to_cart(file: UploadFile = File(...), current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if isinstance(current_user, Customer):
        customer_id = current_user.customer_id
    else:
        customer_id = getattr(current_user, 'user_id', None)
        
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo identificar el cliente")
        
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo debe ser un Excel (.xlsx o .xls)")
        
    try:
        content = await file.read()
        result = import_cart_from_excel(db, customer_id=customer_id, file_content=content)
        # Refrescar carrito para enviarlo actualizado
        result["cart"] = get_cart(db, customer_id=customer_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al procesar el archivo: {str(e)}")

""" PUT /cart/{id} - Actualizar cantidad de un item en el carrito """
@router.put("/cart/{cart_id}")
def update_cart_item_quantity(cart_id: int, item: CartItemUpdate, current_user = Depends(get_current_user),
    db: Session = Depends(get_db)):
    """
    Actualiza la cantidad de un producto en el carrito.
    Si quantity <= 0, el item se elimina del carrito.
    """    
    if isinstance(current_user, Customer):
        customer_id = current_user.customer_id
    else:
        customer_id = getattr(current_user, 'user_id', None)
    
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo identificar el cliente"
        )

    cart_item = update_cart_item(db, cart_id=cart_id, quantity=item.quantity)
    if cart_item is None and item.quantity > 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado en el carrito")
    
    if cart_item is None:
        return {"message": "Item eliminado del carrito"}
    return cart_item

""" DELETE /cart/{id} - Eliminar item del carrito """
@router.delete("/cart/{cart_id}")
def delete_cart_item(cart_id: int, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
    # Elimina un item del carrito
    success = remove_from_cart(db, cart_id=cart_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    return {"message": "Item eliminado del carrito"}

""" DELETE /cart - Vaciar carrito """
@router.delete("/cart")
def clear_user_cart(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    # Limpia el carrito del usuario    
    if isinstance(current_user, Customer):
        customer_id = current_user.customer_id
    else:
        customer_id = getattr(current_user, 'user_id', None)
    
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo identificar el cliente")

    clear_cart(db, customer_id=customer_id)
    return {"message": "Carrito limpiado"}

# --- Pedidos ---
class CheckoutRequest(BaseModel):
    shipping_address_number: int = 1  # Default to address 1
    order_notes: Optional[str] = None  # Notas del pedido escritas por el cliente
    invoice_type: Optional[str] = Field("factura", description="Tipo de comprobante: factura, remision, etc.")
    # shipping_cost removido - será manejado por el backend

""" POST /checkout - Crear pedido desde el carrito """
@router.post("/checkout", response_model=Order)
def checkout_cart(checkout_data: CheckoutRequest,
    current_user = Depends(get_current_user), db: Session = Depends(get_db)):

    # Get customer_id based on user type
    if isinstance(current_user, Customer):
        customer_id = current_user.customer_id
    else:
        customer_id = getattr(current_user, 'user_id', None)
    
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo identificar el cliente")
    
    # CLIENTES: Aplicar costo de envío por defecto (0 MXN)
    default_shipping_cost = Decimal("0.0")
    
    try:
        order = create_order_from_cart(
            db, 
            customer_id=customer_id, 
            shipping_address_number=checkout_data.shipping_address_number,
            shipping_cost=default_shipping_cost,  # Costo fijo para clientes
            order_notes=checkout_data.order_notes,
            invoice_type=checkout_data.invoice_type or "factura"
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=str(e))


""" POST /create-for-customer - Crear pedido para un cliente """
@router.post("/create-for-customer", response_model=Order)
def create_order_for_customer(
    order_data: DirectOrderCreate,
    current_user: User = Depends(require_permission("orders.create")),
    db: Session = Depends(get_db)):
    """
    Permite crear pedidos en nombre de clientes.
    Colaboradores no-admin solo pueden crear para clientes en sus grupos asignados.
    """
    
    # Verificar que el cliente existe
    customer = db.query(Customer).filter(Customer.customer_id == order_data.customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    # Control global puede crear para cualquiera; colaboradores sin permiso global solo para clientes en sus grupos asignados
    has_global_access = hasattr(current_user, "has_permission") and (
        current_user.has_permission("system.admin") or 
        current_user.has_permission("orders.view_all") or 
        current_user.has_permission("customers.view_all")
    )
    if not has_global_access:
        customer_info = db.query(CustomerInfo).filter(
            CustomerInfo.customer_id == order_data.customer_id
        ).first()
        
        if not customer_info or not customer_info.sales_group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este cliente no está asignado a ningún grupo de ventas"
            )
        
        # Verificar si el usuario puede manejar este grupo
        from crud.crud_commercial_group import get_user_groups
        user_group_ids = get_user_groups(db, current_user.user_id)
        
        if customer_info.sales_group_id not in user_group_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para crear pedidos para este cliente"
            )
    
    # Convertir items a formato dict para el CRUD
    items_dict = [{"product_id": item.product_id, "quantity": item.quantity} for item in order_data.items]
    
    try:
        order = create_order_direct(
            db=db,
            customer_id=order_data.customer_id,
            items=items_dict,
            shipping_address_number=order_data.shipping_address_number,
            shipping_cost=Decimal(str(order_data.shipping_cost)),
            order_notes=order_data.order_notes,
            invoice_type=order_data.invoice_type or "factura"
        )
        # Guardar assignment_notes si se proporcionan
        if order_data.assignment_notes:
            order.assignment_notes = order_data.assignment_notes
            db.commit()
            db.refresh(order)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

class OrderWithAddressLookaheadResponse(BaseModel):
    items: List[OrderWithAddress]
    lookahead_pages: int

class OrderLookaheadResponse(BaseModel):
    items: List[Order]
    lookahead_pages: int

""" GET / - Ver mis pedidos """
@router.get("/", response_model=OrderWithAddressLookaheadResponse)
def read_orders(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"), 
    status: Optional[OrderStatus] = None, 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    if isinstance(current_user, Customer):
        customer_id = current_user.customer_id
    else:
        customer_id = getattr(current_user, 'user_id', None)
    
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo identificar el cliente"
        )
    
    query = get_orders_by_customer(db, customer_id=customer_id, status=status, return_query=True)
    res = get_lookahead_pagination(
        query=query,
        model_id_column=OrderModel.order_id,
        skip=skip,
        limit=limit
    )
    
    # Calcular direccion de envio para cada pedido
    for order in res["items"]:
        calculate_order_shipping_address(db, order)
    
    # Strip admin-only fields — clientes nunca deben ver price_without_iva ni order_profit
    if isinstance(current_user, Customer):
        res["items"] = [_strip_admin_fields(OrderWithAddress.model_validate(o, from_attributes=True).model_dump()) for o in res["items"]]
    
    return res

""" GET /all - Ver todos los pedidos (según permisos y grupos) """
@router.get("/all", response_model=OrderLookaheadResponse)
def read_all_orders(
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"), 
    status: Optional[str] = Query(None), 
    search: Optional[str] = Query(None), 
    start_date: Optional[str] = Query(None), 
    end_date: Optional[str] = Query(None),
    is_synced: Optional[bool] = Query(None, description="Filtrar por sincronización ERP"),
    current_user: User = Depends(require_permission("orders.view")), 
    db: Session = Depends(get_db)
):

    order_status = None
    status_filter = None
    
    if status:
        if status in ["assigned", "in_warehouse", "not_in_warehouse", "warehouse_pending", "warehouse_in_progress", "warehouse_completed"]:
            status_filter = status
        else:
            try:
                order_status = OrderStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Status inválido: {status}"
                )
    
    query = get_orders_for_user_groups(
        db=db, 
        user_id=current_user.user_id, 
        user_role=current_user,
        status=order_status, 
        status_filter=status_filter, 
        search=search,
        start_date=start_date, 
        end_date=end_date,
        return_query=True,
        is_synced=is_synced
    )
    
    res = get_lookahead_pagination(
        query=query,
        model_id_column=OrderModel.order_id,
        skip=skip,
        limit=limit
    )

    # Inject sales_group_id and items_count via batch queries (O(1) roundtrips, no N+1)
    if res["items"]:
        order_ids = [o.order_id for o in res["items"]]
        customer_ids = [o.customer_id for o in res["items"]]

        counts = dict(
            db.query(OrderItem.order_id, func.count(OrderItem.order_item_id))
            .filter(OrderItem.order_id.in_(order_ids))
            .group_by(OrderItem.order_id)
            .all()
        )

        group_by_customer = {
            ci.customer_id: ci.sales_group_id
            for ci in db.query(CustomerInfo)
                        .filter(CustomerInfo.customer_id.in_(customer_ids))
                        .all()
        }

        can_view_margins = _user_can_view_order_profit(current_user)
        items_data = []
        for order in res["items"]:
            order_dict = {
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "assigned_user_id": order.assigned_user_id,
                "assigned_by_user_id": order.assigned_by_user_id,
                "status": order.status,
                "total_amount": order.total_amount,
                "order_profit": order.order_profit,
                "shipping_cost": order.shipping_cost,
                "shipping_address_number": order.shipping_address_number,
                "shipping_address_snapshot": order.shipping_address_snapshot,
                "assignment_notes": order.assignment_notes,
                "order_notes": order.order_notes,
                "invoice_type": order.invoice_type,
                "sent_to_warehouse": order.sent_to_warehouse,
                "warehouse_status": order.warehouse_status,
                "total_splits": order.total_splits,
                "warehouse_sent_by": order.warehouse_sent_by,
                "warehouse_sent_at": order.warehouse_sent_at,
                "warehouse_show_details": order.warehouse_show_details,
                "is_synced": order.is_synced,
                "created_at": order.created_at,
                "assigned_at": order.assigned_at,
                "validated_at": order.validated_at,
                "customer": order.customer,
                "assigned_user": order.assigned_user,
                "assigned_by": order.assigned_by,
                "sales_group_id": group_by_customer.get(order.customer_id),
                "items_count": counts.get(order.order_id, 0),
                "items": []
            }
            if not can_view_margins:
                order_dict = _strip_admin_fields(order_dict)
            items_data.append(order_dict)

        res["items"] = items_data

    return res

""" GET /{id} - Ver detalle de un pedido """
@router.get("/{order_id}", response_model=OrderWithAddress)
def read_order(order_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):

    order = get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    if isinstance(current_user, Customer):
        current_user_id = current_user.customer_id
        user_role = None
    else:
        current_user_id = current_user.user_id
        user_role = current_user.role
    
    can_view_margins = _user_can_view_order_profit(current_user)

    # Si es el cliente dueño del pedido, puede verlo
    if order.customer_id == current_user_id:
        pass  # Permitir
    # Si es usuario interno (colaborador), verificar permisos de grupo si no es admin
    elif isinstance(current_user, User):
        if not user_can_manage_order(db, current_user_id, order.customer_id, current_user, order=order):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver este pedido"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver este pedido"
        )
    
    # Calcular direccion de envio
    order_with_address = calculate_order_shipping_address(db, order)
    
    # Ocultar campos de costos y márgenes confidenciales si no posee privilegios financieros/auditoría
    if not can_view_margins:
        return _strip_admin_fields(
            OrderWithAddress.model_validate(order_with_address, from_attributes=True).model_dump()
        )
    
    return order_with_address

""" GET /{order_id}/details - Ver detalle completo de un pedido con relaciones (alias explícito) """
@router.get("/{order_id}/details", response_model=OrderWithAddress)
def read_order_details(order_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    return read_order(order_id=order_id, current_user=current_user, db=db)


""" PUT /{id}/status - Actualizar estado del pedido """
@router.put("/{order_id}/status", response_model=Order)
def update_order_status_route(order_id: int, order_update: OrderUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_permission("orders.status", "orders.approve", "orders.ship", "orders.deliver", "orders.cancel")),
    db: Session = Depends(get_db)):    
    # Obtener el pedido actual
    order = get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")
    
    current_status = order.status
    new_status = order_update.status

    has_global_access = (
        getattr(current_user, "role", None) == "admin"
        or (current_user.role_rel and current_user.role_rel.slug == "admin")
        or current_user.has_permission("system.admin")
        or current_user.has_permission("orders.view_all")
    )
    can_status_master = has_global_access or current_user.has_permission("orders.status")
    can_approve = can_status_master or current_user.has_permission("orders.approve")
    can_ship = can_status_master or current_user.has_permission("orders.ship")
    can_deliver = can_status_master or current_user.has_permission("orders.deliver")
    can_cancel = can_status_master or current_user.has_permission("orders.cancel")
    
    # Verificar permisos por grupo (si no posee acceso global)
    if not has_global_access:
        if not user_can_manage_order(db, current_user.user_id, order.customer_id, current_user, order=order):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para gestionar este pedido.")
        
        # VALIDACIÓN ADICIONAL PARA OPERADORES DE VENTAS / ACCIONES ESPECÍFICAS:
        # Si el colaborador cuenta con la facultad específica para la transición solicitada
        # (aprobar, enviar, entregar o cancelar), puede ejecutarla sobre clientes de su grupo.
        # De lo contrario, solo puede modificar pedidos asignados directamente a él.
        has_specific_action_perm = (
            can_status_master
            or (new_status == OrderStatus.approved and can_approve)
            or (new_status == OrderStatus.shipped and can_ship)
            or (new_status == OrderStatus.delivered and can_deliver)
            or (new_status == OrderStatus.cancelled and can_cancel)
        )
        if not has_specific_action_perm and (order.assigned_user_id != current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes modificar este pedido porque no te ha sido asignado."
            )
    
    # Validar que nadie puede modificar pedidos ya cancelados o entregados
    if current_status == OrderStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar un pedido que ya está cancelado"
        )
    
    if current_status == OrderStatus.delivered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar un pedido que ya fue entregado"
        )
    
    # Definir transiciones válidas según capacidades granulares PBAC y la máquina de estados
    valid_transitions = {
        OrderStatus.pending_validation: [],
        OrderStatus.approved: [],
        OrderStatus.shipped: [],
        OrderStatus.delivered: [],
        OrderStatus.cancelled: []
    }
    
    # 1. Aprobación comercial (pending_validation -> approved)
    if can_approve:
        valid_transitions[OrderStatus.pending_validation].append(OrderStatus.approved)
    
    # 2. Despacho logístico (approved -> shipped)
    if can_ship:
        valid_transitions[OrderStatus.approved].append(OrderStatus.shipped)
        
    # 3. Entrega física (estrictamente shipped -> delivered, no se permite entrega sin antes haber despachado/enviado)
    if can_deliver:
        valid_transitions[OrderStatus.shipped].append(OrderStatus.delivered)
        
    # 4. Cancelación de pedidos
    if can_cancel:
        # Cancelación antes de envío
        valid_transitions[OrderStatus.pending_validation].append(OrderStatus.cancelled)
        valid_transitions[OrderStatus.approved].append(OrderStatus.cancelled)
        # Cancelación en ruta (solo admin o supervisor con control total)
        if has_global_access or can_status_master:
            valid_transitions[OrderStatus.shipped].append(OrderStatus.cancelled)
    
    # Verificar si la transición solicitada es permitida
    if new_status not in valid_transitions[current_status]:
        if current_status == OrderStatus.pending_validation and new_status == OrderStatus.approved and not can_approve:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No posee el permiso ('orders.approve') requerido para aprobar pedidos."
            )
        elif current_status == OrderStatus.approved and new_status == OrderStatus.shipped and not can_ship:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No posee el permiso ('orders.ship') requerido para marcar pedidos como despachados."
            )
        elif new_status == OrderStatus.delivered and not can_deliver:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No posee el permiso ('orders.deliver') requerido para marcar pedidos como entregados."
            )
        elif new_status == OrderStatus.cancelled and not can_cancel:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No posee el permiso ('orders.cancel') requerido para cancelar pedidos."
            )
        elif current_status == OrderStatus.shipped and new_status == OrderStatus.cancelled and not (has_global_access or can_status_master):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores o supervisores pueden cancelar pedidos que ya se encuentran en ruta."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transición de estado inválida de '{current_status.value}' a '{new_status.value}' según la máquina de estados del pedido."
            )
    
    # Actualizar el estado del pedido
    updated_order = update_order_status(db, order_id=order_id, status=new_status)

    # Enviar correo si el cliente tiene habilitadas las notificaciones
    if new_status in [OrderStatus.shipped, OrderStatus.delivered]:
        try:
            customer = db.query(Customer).filter(Customer.customer_id == updated_order.customer_id).first()
            if customer and getattr(customer, 'notificate', False) and getattr(customer, 'email', None):
                customer_name = customer.full_name or customer.username
                if new_status == OrderStatus.shipped:
                    background_tasks.add_task(
                        send_order_shipped_email,
                        to_email=customer.email,
                        order_id=updated_order.order_id,
                        customer_name=customer_name
                    )
                elif new_status == OrderStatus.delivered:
                    background_tasks.add_task(
                        send_order_delivered_email,
                        to_email=customer.email,
                        order_id=updated_order.order_id,
                        customer_name=customer_name
                    )
        except Exception as e:
            logger.warning(f"Error preparando notificaciones por correo para pedido #{order_id}: {e}")

    return updated_order

""" POST /{id}/assign - Asignar usuario/agente a un pedido """
@router.post("/{order_id}/assign", response_model=Order)
def assign_order_to_user(order_id: int, assign_data: OrderAssign,
    current_user: User = Depends(require_permission("orders.assign")), db: Session = Depends(get_db)):
    # Obtener la orden
    order = get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )
    # Verificar que la orden NO este cancelada o entregada
    if order.status in [OrderStatus.cancelled, OrderStatus.delivered]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede asignar un pedido en estado '{order.status.value}'."
        )
    
    # Obtener el colaborador a asignar
    target_user_id = assign_data.assigned_user_id
    assigned_user = get_user(db, target_user_id)
    if not assigned_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario a asignar no encontrado")
    
    # Verificar que el usuario a asignar sea un colaborador interno (no cliente B2B)
    if not isinstance(assigned_user, User):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario seleccionado no es un colaborador interno válido")

    # Bloquear asignación de rol administrador o cuentas de sistema
    is_admin = bool(
        getattr(assigned_user, "role_id", None) == 1
        or getattr(assigned_user, "role_slug", None) == "admin"
        or getattr(assigned_user, "role", None) == "admin"
        or getattr(assigned_user, "user_id", 0) >= 15_000_000
        or (hasattr(assigned_user, "has_permission") and assigned_user.has_permission("system.admin"))
    )
    if is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los administradores tienen supervisión global y no pueden ser asignados como asesores de pedido."
        )

    # Obtener el grupo del cliente del pedido
    customer_info = get_customer_info(db, order.customer_id)
    customer_group_id = customer_info.sales_group_id if customer_info else None

    # Evaluar permisos globales y transversales del usuario que asigna
    is_sys_admin = (
        current_user.has_permission("system.admin")
        or getattr(current_user, "role_id", None) == 1
        or getattr(current_user, "role_slug", None) == "admin"
        or getattr(current_user, "role", None) == "admin"
    )
    has_global_orders = current_user.has_permission("orders.view_all")
    has_users_view = current_user.has_permission("users.view")
    
    # Se requiere ser administrador O tener AMBOS permisos (orders.view_all Y users.view)
    has_unrestricted_assign = is_sys_admin or (has_global_orders and has_users_view and current_user.has_permission("orders.assign"))
    has_global_access = is_sys_admin or has_global_orders

    # Si el cliente NO pertenece a ningún grupo de ventas
    if not customer_group_id:
        if not has_unrestricted_assign:
            my_groups = get_user_groups(db, current_user.user_id)
            target_groups = get_user_groups(db, assigned_user.user_id)
            is_self = (assigned_user.user_id == current_user.user_id)
            shares_group = any(group in target_groups for group in my_groups)
            if not is_self and not shares_group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El cliente no pertenece a ningún grupo de ventas. Para asignar libremente debe contar con permisos transversales (orders.view_all y users.view) o pertenecer al mismo equipo comercial."
                )
    else:
        # Si el cliente sí pertenece a un grupo de ventas
        user_groups = get_user_groups(db, assigned_user.user_id)
        if not has_unrestricted_assign and customer_group_id not in user_groups:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede asignar este agente. El agente no pertenece al grupo de ventas del cliente."
            )
        
        if not has_global_access:
            if not user_can_manage_order(db, current_user.user_id, order.customer_id, current_user, order=order):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permiso para asignar este pedido. El cliente no pertenece a sus grupos."
                )
            
            my_groups = get_user_groups(db, current_user.user_id)
            if not any(group in user_groups for group in my_groups):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puede asignar a este agente. No comparte grupo de ventas con usted."
                )

    return assign_order_user(db, order, assign_data, current_user)


""" POST /{id}/cancel - Cancelar un pedido """
@router.post("/{order_id}/cancel", response_model=Order)
def cancel_order_route(order_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Cancela un pedido.
    order = get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")    

    if isinstance(current_user, Customer):
        current_user_id = current_user.customer_id
        is_customer = True
        user_role = None  
    else:
        current_user_id = current_user.user_id
        is_customer = False
        user_role = current_user.role
    
    # Verificar permisos
    is_owner = order.customer_id == current_user_id
    has_global_access = (
        not is_customer and (
            getattr(current_user, "role", None) == "admin"
            or (current_user.role_rel and current_user.role_rel.slug == "admin")
            or current_user.has_permission("system.admin")
            or current_user.has_permission("orders.view_all")
        )
    )
    
    # Si es el cliente dueño, puede cancelar
    if is_owner:
        pass  # Permitir, validaciones de estado más abajo
    # Si es colaborador interno, verificar pertenencia a grupos
    elif isinstance(current_user, User):
        if not has_global_access and not user_can_manage_order(db, current_user_id, order.customer_id, current_user, order=order):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para cancelar este pedido. El cliente no pertenece a sus grupos."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para cancelar este pedido"
        )
        
    # No se puede cancelar si ya esta cancelado
    if order.status == OrderStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este pedido ya está cancelado"
        )
    
    # No se puede cancelar si ya esta entregado
    if order.status == OrderStatus.delivered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar un pedido que ya ha sido entregado"
        )
    
    # Validación basada en PBAC / Rol
    if is_customer:
        # Los clientes solo pueden cancelar antes de que sea validado
        if order.status != OrderStatus.pending_validation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Los clientes solo pueden cancelar pedidos pendientes de validación"
            )
    elif has_global_access or current_user.has_permission("orders.status"):
        # Admin o control total de pedidos puede cancelar hasta antes de entregado (ya validado arriba)
        pass
    elif current_user.has_permission("orders.cancel"):
        # Permiso de cancelación comercial: antes de que sea enviado
        if order.status == OrderStatus.shipped:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden cancelar pedidos que ya fueron enviados"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos ('orders.cancel') para cancelar este pedido"
        )
    
    try:
        cancelled_order = cancel_order(db, order_id=order_id)
        return cancelled_order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


""" PUT /{id}/edit - Editar un pedido """
@router.put("/{order_id}/edit", response_model=Order)
def edit_order_route(order_id: int, edit_data: OrderEditRequest, current_user: User = Depends(require_permission("orders.edit")),
    db: Session = Depends(get_db)):
    has_global_access = current_user.has_permission("system.admin")
    
    # Obtener el pedido
    order = get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )
    
    # Verificar permisos por grupo (si no posee acceso global)
    if not has_global_access:
        if not user_can_manage_order(db, current_user.user_id, order.customer_id, current_user, order=order):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para editar este pedido. El cliente no pertenece a sus grupos."
            )
    
    # Editar el pedido
    try:
        edited_order = edit_order_items(
            db, 
            order_id=order_id, 
            items=edit_data.items, 
            customer_id=order.customer_id,
            shipping_cost=edit_data.shipping_cost,
            assignment_notes=edit_data.assignment_notes,
            shipping_address_number=edit_data.shipping_address_number,
            invoice_type=edit_data.invoice_type,
            is_synced=edit_data.is_synced
        )
        return edited_order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


""" GET /{id}/download-txt - Descargar pedido en formato TXT (o ZIP si se especifica división por partes) """
@router.get("/{order_id}/download-txt")
def download_order_txt(
    order_id: int,
    items_per_file: Optional[int] = Query(None, ge=1, description="Número de ítems por archivo TXT para dividir el pedido"),
    current_user: User = Depends(require_permission("orders.export")),
    db: Session = Depends(get_db)
):
    """
    Descarga el pedido en formato TXT de ancho fijo para ERP.
    Si items_per_file está definido y genera múltiples partes, empaqueta los TXTs en un .zip.
    """
    # Obtener el pedido
    order = get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido {order_id} no encontrado"
        )
    
    # Validar permisos PBAC
    has_global_access = current_user.has_permission("system.admin")
    if not has_global_access:
        if not user_can_manage_order(db, current_user.user_id, order.customer_id, current_user, order=order):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para descargar este pedido. El cliente no pertenece a sus grupos."
            )
    
    # Generar contenido TXT por archivo(s)
    try:
        files = generate_order_txt_files(db, order_id, items_per_file=items_per_file)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    from fastapi.responses import Response
    import io
    import zipfile
    
    # Caso 1: Si se solicitó división por partes (items_per_file definido), siempre empaquetar en ZIP
    if items_per_file is not None and items_per_file > 0:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files:
                zip_file.writestr(filename, content.encode("utf-8"))
                
        zip_buffer.seek(0)
        zip_filename = f"pedido_{order_id}_partes.zip"
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"'
            }
        )
        
    # Caso 2: Un solo archivo TXT completo
    filename, content = files[0]
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
