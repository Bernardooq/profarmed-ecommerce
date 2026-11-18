"""
CRUD y Gestión Integral del Ciclo de Vida de Pedidos (Orders):

Funciones y Operaciones:
- Crear pedidos desde el carrito calculando subtotales, IVA y utilidades comerciales.
- Consultas paginadas Lookahead con filtros por cliente, agente comercial asignado, grupos o administración global.
- Asignación manual de agentes comerciales a pedidos por parte de colaboradores autorizados (`orders.assign`).
- Transiciones y validaciones estrictas de estado de pedidos.
- Aprobación de pedidos con verificación de stock y sincronización de estadísticas anuales (`orders.approve`).
- Cancelación de pedidos con restauración de stock e invalidación de pedidos en bodega (`orders.cancel`).
- Modificación de direcciones de entrega, costos de envío y notas de asignación.

Flujo de Estados de un Pedido:
1. `pending_validation`: El cliente finaliza su carrito. Pedido recién creado pendiente de asignación/validación.
2. `assigned`: Colaborador autorizado asigna un agente comercial responsable para atender el pedido.
3. `approved`: Colaborador autorizado aprueba el pedido, permitiendo su despacho o envío a almacén.
4. `shipped`: El pedido fue empacado, rotulado y enviado con guía logística al cliente.
5. `delivered`: El cliente recibió la mercancía satisfactoriamente.
6. `cancelled`: El pedido fue cancelado, liberando inventario y revirtiendo estadísticas.

Reglas de Visibilidad y Permisos PBAC / RBAC Dinámico:
- Clientes: Solo pueden consultar sus propios pedidos y crear pedidos desde su carrito (aislamiento por `customer_id`).
- Colaboradores Internos (N Roles): Visibilidad basada en pertenencia a grupos comerciales (`sales_group_id`), agente asignado (`agent_id`) o permisos globales (`orders.view_all`).
- Permisos Requeridos: `orders.view`, `orders.create`, `orders.approve`, `orders.assign`, `orders.cancel`, `orders.export`.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo
    MX_TZ = ZoneInfo("America/Mexico_City")
except Exception:
    try:
        import pytz
        MX_TZ = pytz.timezone("America/Mexico_City")
    except Exception:
        MX_TZ = timezone.utc

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, cast, String

from db.base import Order, OrderItem, OrderStatus, Product, CartCache, CustomerInfo, PriceListItem, User, Customer
from schemas.order import OrderAssign, OrderCreate, OrderUpdate, OrderItemCreate
from utils.price_utils import calculate_product_price_breakdown
from crud.crud_order_stats import sync_order_on_create, sync_order_on_status_change
from crud.crud_discount import get_active_discounts_for_products


""" Obtener pedidos por ID con relaciones """
def get_order(db: Session, order_id: int) -> Optional[Order]:
    return db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.customer),
        joinedload(Order.assigned_user)
    ).filter(Order.order_id == order_id).first()

""" Obtener pedidos de un cliente especifico con relaciones """
def get_orders_by_customer(db: Session, customer_id: int, skip: int = 0, limit: int = 100, status: Optional[OrderStatus] = None, return_query: bool = False):    
    query = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.customer),
        joinedload(Order.assigned_user)
    ).filter(Order.customer_id == customer_id)
    
    if status:
        query = query.filter(Order.status == status)
        
    query = query.order_by(Order.created_at.desc())
    if return_query:
        return query
    return query.offset(skip).limit(limit).all()

""" Obtener todos los pedidos con filtros opcionales para administradores o colaboradores con permisos globales """
def get_orders(db: Session, skip: int = 0, limit: int = 100, status: Optional[OrderStatus] = None, search: Optional[str] = None) -> List[Order]:        
    query = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.assigned_user)
    )
    
    # Filtrar por status
    if status:
        query = query.filter(Order.status == status)
    
    # Busqueda
    if search:
        # Join con Customer y el usuario/colaborador comercial asignado (User)
        # Usamos outerjoin porque puede haber pedidos sin usuario asignado aún
        query = query.outerjoin(Order.customer).outerjoin(User, Order.assigned_user_id == User.user_id)
        
        # Si es numero puro, buscar solo por order_id exacto
        try:
            search_int = int(search)
            query = query.filter(Order.order_id == search_int)
        except (ValueError, AttributeError):
            # No es numero, buscar por nombre de cliente o usuario asignado
            search_term = f"%{search}%"
            query = query.filter(or_(
                Customer.full_name.ilike(search_term),
                Customer.username.ilike(search_term),
                User.full_name.ilike(search_term)  # Buscar por nombre del usuario comercial asignado
            ))
    
    return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

""" Crear un pedido a partir del carrito del cliente """
def create_order_from_cart(db: Session, customer_id: int, shipping_address_number: int = 1, shipping_cost: Decimal = Decimal("0.00"), order_notes: Optional[str] = None, invoice_type: str = "factura") -> Order:
    # Validar direccion
    if shipping_address_number not in [1, 2, 3]:
        raise ValueError("Numero de direccion invalido. Debe ser 1, 2 o 3.")
    
    # Obtener items del carrito
    cart_items = db.query(CartCache).filter(
        CartCache.customer_id == customer_id
    ).all()
    
    if not cart_items:
        raise ValueError("El carrito esta vacio")
    
    # Validar lista de precios
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == customer_id
    ).first()
    
    if not customer_info or not customer_info.price_list_id:
        raise ValueError("No tienes una lista de precios asignada. Contacta al administrador.")
    
    # Obtener el agente del cliente para asignarlo automáticamente
    from db.base import Customer
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    assigned_user_id = customer.agent_id if customer and customer.agent_id else None
    
    # Obtener dirección del cliente
    shipping_address = None
    if customer_info:
        address_key = f"address_{shipping_address_number}"
        shipping_address = getattr(customer_info, address_key, None)
        if not shipping_address:
            shipping_address = customer_info.address_1 or customer_info.address_2 or customer_info.address_3

    # Crear pedido con usuario comercial asignado automáticamente
    db_order = Order(
        customer_id=customer_id,
        status=OrderStatus.pending_validation,
        total_amount=0,  # Se calculara despues
        shipping_cost=float(shipping_cost),  # Costo de envío
        shipping_address_number=shipping_address_number,
        shipping_address_snapshot=shipping_address or "No especificada",
        assigned_user_id=assigned_user_id,  # Auto-asignar agente
        order_notes=order_notes,  # Notas del cliente
        invoice_type=invoice_type or "factura"
    )
    db.add(db_order)
    db.flush()  # Para obtener order_id
    
    # CREAR ITEMS Y CALCULAR TOTAL
    total = Decimal('0')
    profit = Decimal('0')
    
    # Optimizacion O(1) queries: Cargar productos, precios de lista y promociones en un solo viaje bulk
    cart_product_ids = [ci.product_id for ci in cart_items if ci.product_id]
    bulk_products = db.query(Product).filter(Product.product_id.in_(cart_product_ids)).all() if cart_product_ids else []
    product_map = {p.product_id: p for p in bulk_products}

    bulk_price_items = db.query(PriceListItem).filter(
        PriceListItem.price_list_id == customer_info.price_list_id,
        PriceListItem.product_id.in_(cart_product_ids)
    ).all() if (cart_product_ids and customer_info and customer_info.price_list_id) else []
    price_item_map = {pi.product_id: pi for pi in bulk_price_items}

    discounts_map = get_active_discounts_for_products(
        db=db,
        product_ids=cart_product_ids,
        price_list_id=customer_info.price_list_id if customer_info else None
    )

    for cart_item in cart_items:
        # Obtener producto desde mapa en memoria O(1)
        product = product_map.get(cart_item.product_id)
        
        # Validar producto activo
        if not product or not product.is_active:
            continue
        
        # Validar stock suficiente
        if product.stock_count < cart_item.quantity:
            raise ValueError(f"Stock insuficiente para {product.name}")
        
        # Obtener markup de la lista de precios del cliente desde mapa O(1)
        price_item = price_item_map.get(cart_item.product_id)
        
        if not price_item:
            raise ValueError(f"El producto {product.name} no esta en tu lista de precios")
        
        # CALCULAR PRECIO FINAL Y DESCUENTOS usando utilidad centralizada con descuento precargado        
        breakdown = calculate_product_price_breakdown(
            product=product,
            price_item=price_item,
            db=None,
            active_discount=discounts_map.get(cart_item.product_id)
        )
        
        base_price = breakdown["base_price"]
        markup_percentage = breakdown["markup_percentage"]
        iva = breakdown["iva_percentage"]
        price_without_iva = breakdown["price_without_iva"]
        final_price = breakdown["final_price_with_iva"]
        discount_applied = breakdown["discount_applied"]
        discount_type = breakdown["discount_type"]
        
        # Crear item del pedido (precios "congelados")
        order_item = OrderItem(
            order_id=db_order.order_id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            base_price=float(base_price),
            markup_percentage=float(markup_percentage),
            iva_percentage=float(iva),
            price_without_iva=float(price_without_iva),
            final_price=float(final_price),
            discount_applied=float(discount_applied) if discount_applied else 0.0,
            discount_type=discount_type
        )
        db.add(order_item)
        
        # Reducir stock
        # product.stock_count -= cart_item.quantity
        
        # Acumular total (con IVA) y ganancia (markup)
        total += final_price * cart_item.quantity
        profit += (price_without_iva - base_price) * cart_item.quantity
    
    # Actualizar total y ganancia del pedido
    db_order.total_amount = float(total + shipping_cost)
    db_order.order_profit = float(profit)
    
    # Procesar reglas de stock dinámicas para clientes (101 order.apartar y 102 order.discount)
    from utils.stock_rules_utils import process_customer_order_stock_rules
    process_customer_order_stock_rules(
        db=db,
        order_id=db_order.order_id,
        items_data=[{"product_id": ci.product_id, "quantity": ci.quantity} for ci in cart_items]
    )

    # === LIMPIAR CARRITO ===
    db.query(CartCache).filter(CartCache.customer_id == customer_id).delete()
    
    db.commit()
    db.refresh(db_order)
    
    # Sincronizar order_stats en tiempo real
    sync_order_on_create(db, db_order)
    
    return db_order


def create_order_direct(db: Session, customer_id: int, items: List[dict], shipping_address_number: int = 1, shipping_cost: Decimal = Decimal("0.00"), order_notes: Optional[str] = None, invoice_type: str = "factura") -> Order:
    """
    Crea un pedido directamente sin pasar por el carrito.
    
    Usado por colaboradores autorizados (orders.create) o administradores para crear pedidos directos en nombre de clientes.
    
    Args:
        db: Sesión de base de datos
        customer_id: ID del cliente para quien se crea el pedido
        items: Lista de dicts con {'product_id': str, 'quantity': int}
        shipping_address_number: Número de dirección (1, 2 o 3)
        shipping_cost: Costo de envío
        order_notes: Notas del cliente
        invoice_type: Tipo de documento (factura, remision, etc.)
    
    Returns:
        Order: El pedido creado
    """
    # Validar direccion
    if shipping_address_number not in [1, 2, 3]:
        raise ValueError("Numero de direccion invalido. Debe ser 1, 2 o 3.")
    
    if not items:
        raise ValueError("Debe incluir al menos un producto en el pedido")
    
    # Validar lista de precios del cliente
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == customer_id
    ).first()
    
    if not customer_info or not customer_info.price_list_id:
        raise ValueError("El cliente no tiene una lista de precios asignada")
    
    # Obtener el agente del cliente para asignarlo automáticamente
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise ValueError("Cliente no encontrado")
    
    assigned_user_id = customer.agent_id if customer.agent_id else None
    
    # Obtener dirección del cliente
    shipping_address = None
    if customer_info:
        address_key = f"address_{shipping_address_number}"
        shipping_address = getattr(customer_info, address_key, None)
        if not shipping_address:
            shipping_address = customer_info.address_1 or customer_info.address_2 or customer_info.address_3

    # Crear pedido con usuario comercial asignado automáticamente
    db_order = Order(
        customer_id=customer_id,
        status=OrderStatus.pending_validation,
        total_amount=0,  # Se calculara despues
        shipping_cost=float(shipping_cost),  # Costo de envío
        shipping_address_number=shipping_address_number,
        shipping_address_snapshot=shipping_address or "No especificada",
        assigned_user_id=assigned_user_id,
        order_notes=order_notes,  # Notas del cliente
        invoice_type=invoice_type or "factura"
    )
    db.add(db_order)
    db.flush()  # Para obtener order_id
    
    # CREAR ITEMS Y CALCULAR TOTAL
    total = Decimal('0')
    profit = Decimal('0')
    
    # Optimizacion O(1) queries: Cargar productos, precios de lista y promociones en un solo viaje bulk
    order_product_ids = [item_data.get('product_id') for item_data in items if item_data.get('product_id')]
    bulk_products = db.query(Product).filter(Product.product_id.in_(order_product_ids)).all() if order_product_ids else []
    product_map = {p.product_id: p for p in bulk_products}

    bulk_price_items = db.query(PriceListItem).filter(
        PriceListItem.price_list_id == customer_info.price_list_id,
        PriceListItem.product_id.in_(order_product_ids)
    ).all() if (order_product_ids and customer_info and customer_info.price_list_id) else []
    price_item_map = {pi.product_id: pi for pi in bulk_price_items}

    discounts_map = get_active_discounts_for_products(
        db=db,
        product_ids=order_product_ids,
        price_list_id=customer_info.price_list_id if customer_info else None
    )

    for item_data in items:
        product_id = item_data.get('product_id')
        quantity = item_data.get('quantity', 1)
        
        if not product_id or quantity <= 0:
            continue
        
        # Obtener producto desde mapa en memoria O(1)
        product = product_map.get(product_id)
        
        # Validar producto activo
        if not product or not product.is_active:
            raise ValueError(f"Producto {product_id} no encontrado o inactivo")
        
        # Validar stock suficiente
        # if product.stock_count < quantity:
        #     raise ValueError(f"Stock insuficiente para {product.name}")
        
        # Obtener markup de la lista de precios del cliente desde mapa O(1)
        price_item = price_item_map.get(product_id)
        
        if not price_item:
            raise ValueError(f"El producto {product.name} no esta en la lista de precios del cliente")
        
        # CALCULAR PRECIO FINAL Y DESCUENTOS usando utilidad centralizada con descuento precargado        
        breakdown = calculate_product_price_breakdown(
            product=product,
            price_item=price_item,
            db=None,
            active_discount=discounts_map.get(product_id)
        )
        
        base_price = breakdown["base_price"]
        markup_percentage = breakdown["markup_percentage"]
        iva = breakdown["iva_percentage"]
        price_without_iva = breakdown["price_without_iva"]
        final_price = breakdown["final_price_with_iva"]
        discount_applied = breakdown["discount_applied"]
        discount_type = breakdown["discount_type"]
        
        # Crear item del pedido (precios "congelados")
        order_item = OrderItem(
            order_id=db_order.order_id,
            product_id=product_id,
            quantity=quantity,
            base_price=float(base_price),
            markup_percentage=float(markup_percentage),
            iva_percentage=float(iva),
            price_without_iva=float(price_without_iva),
            final_price=float(final_price),
            discount_applied=float(discount_applied) if discount_applied else 0.0,
            discount_type=discount_type
        )
        db.add(order_item)
        
        # Acumular total (con IVA) y ganancia (markup)
        total += final_price * quantity
        profit += (price_without_iva - base_price) * quantity
    
    # Actualizar total y ganancia del pedido
    db_order.total_amount = float(total + shipping_cost)
    db_order.order_profit = float(profit)
    
    # Procesar reglas de stock (101 order.apartar y 102 order.discount si están activas)
    from utils.stock_rules_utils import validate_and_process_order_stock_rules
    validate_and_process_order_stock_rules(
        db=db,
        order_id=db_order.order_id,
        items_data=[{"product_id": item_data.get('product_id'), "quantity": item_data.get('quantity', 1)} for item_data in items]
    )

    db.commit()
    db.refresh(db_order)
    
    # Sincronizar order_stats en tiempo real
    sync_order_on_create(db, db_order)
    
    return db_order

""" Limpiar asignación de bodega si no hay productos escaneados, cajas ni manuales """
def cleanup_warehouse_if_no_progress(db: Session, db_order: Order) -> bool:
    """
    Si el pedido fue enviado a bodega, la máquina de estados borra el pedido en bodega
    y sus splits si y sólo si no hay productos aún escaneados, cajas o manuales.
    Retorna True si fue eliminado/limpiado de bodega, False si no procedió la limpieza.
    """
    if not db_order.sent_to_warehouse:
        return False

    from db.base import WarehouseSplit, WarehouseItem
    from sqlalchemy.orm import selectinload

    splits = db.query(WarehouseSplit).options(
        selectinload(WarehouseSplit.warehouse_items)
    ).filter(WarehouseSplit.order_id == db_order.order_id).all()

    if not splits:
        db_order.sent_to_warehouse = False
        db_order.warehouse_status = None
        db_order.total_splits = 1
        db_order.warehouse_sent_by = None
        db_order.warehouse_sent_at = None
        db_order.warehouse_show_details = False
        return True

    has_progress = False

    # Si ya fue completado o sellado globalmente, se preserva registro
    if db_order.warehouse_status == "completed":
        has_progress = True

    if not has_progress:
        for s in splits:
            if s.status in ["picking", "in_progress", "completed", "ready_for_check", "checking"]:
                has_progress = True
                break
            for f in (s.warehouse_items or []):
                tot = (
                    (f.picked_boxes or 0) + (f.picked_box_prods or 0) + (f.picked_scanned_qty or 0) + (f.picked_manual_qty or 0) +
                    (f.checked_boxes or 0) + (f.checked_box_prods or 0) + (f.checked_scanned_qty or 0) + (f.checked_manual_qty or 0)
                )
                if tot > 0:
                    has_progress = True
                    break
            if has_progress:
                break

    # Si NO hay productos escaneados, ni cajas, ni manuales:
    if not has_progress:
        from db.base import WarehouseContainer
        split_ids = [s.split_id for s in splits]
        if split_ids:
            db.query(WarehouseContainer).filter(WarehouseContainer.current_split_id.in_(split_ids)).update({
                WarehouseContainer.status: "available",
                WarehouseContainer.current_split_id: None,
                WarehouseContainer.current_user_id: None,
                WarehouseContainer.updated_at: datetime.now(timezone.utc)
            }, synchronize_session=False)

        for s in splits:
            for f in (s.warehouse_items or []):
                db.delete(f)
            db.delete(s)

        for it in (db_order.items or []):
            for wi in (it.warehouse_items or []):
                db.delete(wi)

        db_order.sent_to_warehouse = False
        db_order.warehouse_status = None
        db_order.total_splits = 1
        db_order.warehouse_sent_by = None
        db_order.warehouse_sent_at = None
        db_order.warehouse_show_details = False
        return True

    return False


""" Actualizar el estado de un pedido """
def update_order_status(db: Session, order_id: int, status: OrderStatus) -> Optional[Order]:
    # Actualiza el estado de un pedido
    db_order = get_order(db, order_id)
    if not db_order:
        return None
    
    old_status = db_order.status.value if hasattr(db_order.status, 'value') else db_order.status
    new_status = status.value if hasattr(status, 'value') else status
    customer_id = db_order.customer_id

    if old_status == new_status:
        return db_order
    
    if old_status == 'delivered':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar ni cancelar un pedido que ya fue entregado"
        )

    db_order.status = status
    
    # Si se aprueba, registrar validacion y sincronizar product_yearly_stats
    if status == OrderStatus.approved:
        db_order.validated_at = datetime.now(timezone.utc)
        if old_status != 'approved':
            from crud.crud_product_yearly_stats import sync_order_products_on_approve
            sync_order_products_on_approve(db, db_order)
            # Liberar apartados ya que el SAI/ERP procesa la venta definitiva
            from utils.stock_rules_utils import release_order_stock_holds
            release_order_stock_holds(db, db_order.order_id)
    elif status == OrderStatus.cancelled:
        # Al cancelar, marcar is_synced = False para que el runner ERP limpie partidas en cotiza3
        db_order.is_synced = False
        if old_status in ['approved', 'shipped', 'delivered']:
            from crud.crud_product_yearly_stats import sync_order_products_on_cancel
            sync_order_products_on_cancel(db, db_order)
        # Restaurar apartados y/o stock de catálogo web según configuración activa
        from utils.stock_rules_utils import restore_cancelled_order_stock
        restore_cancelled_order_stock(db, db_order)
        # Limpieza automática en almacén SOLO si el pedido fue enviado a bodega
        if getattr(db_order, "sent_to_warehouse", False):
            cleaned = False
            try:
                cleaned = cleanup_warehouse_if_no_progress(db, db_order)
            except Exception as e:
                logger.warning(f"Error en cleanup_warehouse_if_no_progress: {e}")
            if not cleaned:
                # Si tenía avance físico, las partidas y splits se conservan para auditoría,
                # pero las canastas físicas plásticas se liberan al parque operativo disponible
                try:
                    from db.base import WarehouseContainer
                    split_ids = [s.split_id for s in (db_order.splits or []) if hasattr(s, 'split_id')]
                    if split_ids:
                        db.query(WarehouseContainer).filter(
                            WarehouseContainer.current_split_id.in_(split_ids)
                        ).update({
                            WarehouseContainer.status: "available",
                            WarehouseContainer.current_split_id: None,
                            WarehouseContainer.current_user_id: None,
                            WarehouseContainer.updated_at: datetime.now(timezone.utc)
                        }, synchronize_session=False)
                except Exception as e:
                    logger.warning(f"Error liberando canastas en cancelación de pedido {order_id}: {e}")
    elif status in [OrderStatus.shipped, OrderStatus.delivered]:
        # Liberar canastas físicas vinculadas a los splits del pedido SOLO si pasó por bodega
        if getattr(db_order, "sent_to_warehouse", False):
            try:
                from db.base import WarehouseContainer
                split_ids = [s.split_id for s in (db_order.splits or []) if hasattr(s, 'split_id')]
                if split_ids:
                    db.query(WarehouseContainer).filter(
                        WarehouseContainer.current_split_id.in_(split_ids)
                    ).update({
                        WarehouseContainer.status: "available",
                        WarehouseContainer.current_split_id: None,
                        WarehouseContainer.current_user_id: None,
                        WarehouseContainer.updated_at: datetime.now(timezone.utc)
                    }, synchronize_session=False)
            except Exception as e:
                logger.warning(f"Error liberando canastas en cambio de estado de pedido {order_id}: {e}")
    
    db.commit()
    db.refresh(db_order)
    
    # Sincronizar order_stats en tiempo real
    sync_order_on_status_change(db, order_id, old_status, new_status, customer_id)

    return db_order


""" Cancelar un pedido y restaurar stock """
def cancel_order(db: Session, order_id: int) -> Optional[Order]:
    # Cancela un pedido y puede restaurar el stock
    
    db_order = get_order(db, order_id)
    if not db_order:
        return None
    
    # Validar que se pueda cancelar
    if db_order.status not in [
        OrderStatus.pending_validation,
        OrderStatus.approved,
        OrderStatus.shipped
    ]:
        raise ValueError("No se puede cancelar este pedido")
    
    # Cambiar estado a cancelado
    old_status = db_order.status.value if hasattr(db_order.status, 'value') else db_order.status
    customer_id = db_order.customer_id

    db_order.status = OrderStatus.cancelled
    # Al cancelar, marcar is_synced = False para que el runner ERP limpie partidas en cotiza3
    db_order.is_synced = False
    if old_status in ['approved', 'shipped', 'delivered']:
        from crud.crud_product_yearly_stats import sync_order_products_on_cancel
        sync_order_products_on_cancel(db, db_order)
    # Restaurar apartados y/o stock de catálogo web según configuración activa
    from utils.stock_rules_utils import restore_cancelled_order_stock
    restore_cancelled_order_stock(db, db_order)

    # Limpieza en bodega según la máquina de estados:
    # Borra el pedido en bodega y sus splits si y sólo si fue enviado a bodega y no hay productos escaneados
    if getattr(db_order, "sent_to_warehouse", False):
        try:
            cleanup_warehouse_if_no_progress(db, db_order)
        except Exception as e:
            logger.warning(f"Error en cleanup_warehouse_if_no_progress durante cancelacion de #{order_id}: {e}")

    db.commit()
    db.refresh(db_order)
    sync_order_on_status_change(db, order_id, old_status, "cancelled", customer_id)
    return db_order

""" Obtener pedidos filtrados segun los grupos del usuario """
def get_orders_for_user_groups(db: Session, user_id: int, user_role,
    skip: int = 0, limit: int = 100, status: Optional[OrderStatus] = None, status_filter: Optional[str] = None,  # Filtro raw (puede ser "assigned")
    search: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, return_query: bool = False,
    is_synced: Optional[bool] = None):
    # Obtiene pedidos filtrados segun los grupos del usuario
    from db.base import User, Customer
    
    query = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.assigned_user)
    )
    
    # Filtros segun rol:
    # 1. Admin o colaboradores con orders.view_all ven todo a nivel nacional.
    # 2. Colaboradores con orders.group_view ven pedidos de sus grupos comerciales O asignados a ellos.
    # 3. Colaboradores con solo orders.view ven EXCLUSIVAMENTE los pedidos asignados a ellos (bandeja personal).
    is_admin = (
        (getattr(user_role, "value", str(user_role)) == "admin")
        or (getattr(user_role, "role_slug", None) == "admin")
        or (user_role == "admin")
        or (hasattr(user_role, "has_permission") and (user_role.has_permission("system.admin") or user_role.has_permission("orders.view_all")))
    )
    if not is_admin:
        from crud.crud_commercial_group import get_user_groups
        user_group_ids = get_user_groups(db, user_id)
        if not user_group_ids:
            if return_query:
                return db.query(Order).filter(Order.order_id == -1)
            return []
        
        # Filtro base: el pedido siempre debe pertenecer a un cliente de los grupos comerciales del usuario
        query = query.join(
            CustomerInfo,
            Order.customer_id == CustomerInfo.customer_id
        ).filter(
            CustomerInfo.sales_group_id.in_(user_group_ids)
        )

        has_group_view = hasattr(user_role, "has_permission") and user_role.has_permission("orders.group_view")
        if not has_group_view:
            # Si solo tiene orders.view (sin orders.group_view):
            # además de pertenecer a su grupo comercial, debe estar asignado directamente a él
            query = query.filter(Order.assigned_user_id == user_id)
    
    # Filtros especiales de status_filter
    if status_filter == "assigned":
        query = query.filter(Order.assigned_user_id.isnot(None))
    elif status_filter == "in_warehouse":
        query = query.filter(Order.sent_to_warehouse == True)
    elif status_filter == "not_in_warehouse":
        query = query.filter(Order.sent_to_warehouse == False)
    elif status_filter == "warehouse_pending":
        query = query.filter(Order.sent_to_warehouse == True, Order.warehouse_status == "pending")
    elif status_filter == "warehouse_in_progress":
        query = query.filter(Order.sent_to_warehouse == True, Order.warehouse_status.in_(["in_progress_partial", "in_progress_full"]))
    elif status_filter == "warehouse_completed":
        query = query.filter(Order.sent_to_warehouse == True, Order.warehouse_status == "completed")
    # Filtro por status normal
    elif status:
        query = query.filter(Order.status == status)

    # Filtro por sincronización ERP (cotiza3)
    if is_synced is not None:
        query = query.filter(Order.is_synced == is_synced)

    # Filtro por rango de fechas
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
            start_dt = datetime.combine(parsed_start.date(), datetime.min.time()).replace(tzinfo=MX_TZ).astimezone(timezone.utc)
            query = query.filter(Order.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = datetime.combine(parsed_end.date(), datetime.max.time()).replace(tzinfo=MX_TZ).astimezone(timezone.utc)
            query = query.filter(Order.created_at <= end_dt)
        except ValueError:
            pass
    
    # Busqueda
    if search:
        # Join con Customer y el usuario comercial asignado (User)
        # Se usa outerjoin para no excluir pedidos sin usuario asignado
        query = query.outerjoin(Order.customer).outerjoin(User, Order.assigned_user_id == User.user_id)
        
        # Si es numero puro, buscar solo por order_id exacto
        try:
            search_int = int(search)
            query = query.filter(Order.order_id == search_int)
        except (ValueError, AttributeError):
            # No es numero, buscar por nombre de cliente o usuario asignado
            search_term = f"%{search}%"
            query = query.filter(or_(
                Customer.full_name.ilike(search_term),
                Customer.username.ilike(search_term),
                User.full_name.ilike(search_term)  # Buscar por nombre del usuario comercial asignado
            ))
            
    query = query.order_by(Order.created_at.desc())
    if return_query:
        return query
    return query.offset(skip).limit(limit).all()

    
""" Obtener el conteo de pedidos de un cliente especifico """
def get_order_count_by_customer(db: Session, customer_id: int) -> int:
    # Obtiene el conteo de pedidos de un cliente especifico
    corder_count = db.query(Order).filter(
        Order.customer_id == customer_id
    ).count()

    return corder_count

""" Calcular y actualizar la direccion de envio de un pedido """
def calculate_order_shipping_address(db: Session, order: Order) -> str:
    # Calcula la direccion de envio completa basada en el numero seleccionado
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == order.customer_id
    ).first()
    
    # Intentar usar el snapshot primero. Si no existe, usar el método dinámico (retrocompatibilidad).
    if order.shipping_address_snapshot:
        order.shipping_address = order.shipping_address_snapshot
    elif order.shipping_address_number and customer_info:
        address_key = f"address_{order.shipping_address_number}"
        shipping_address = getattr(customer_info, address_key, None)
        
        if not shipping_address:
            # Fallback to address_1
            shipping_address = customer_info.address_1 or customer_info.address_2 or customer_info.address_3
        
        order.shipping_address = shipping_address or "No especificada"
    else:
        order.shipping_address = "No especificada"
    
    # Agregar customerInfo completo al order
    if customer_info:
        order.customerInfo = {
            "business_name": customer_info.business_name,
            "rfc": customer_info.rfc,
            "telefono_1": customer_info.telefono_1,
            "telefono_2": customer_info.telefono_2,
            "address_1": customer_info.address_1,
            "address_2": customer_info.address_2,
            "address_3": customer_info.address_3
        }
    
    return order

""" Asignar un pedido a un usuario comercial responsable """
def assign_order_user(db: Session, order: Order, assign_data: OrderAssign, current_user: User) -> Optional[Order]:
    # Asignación final
    assigned_id = assign_data.assigned_user_id
    order.assigned_user_id = assigned_id
    order.assigned_by_user_id = current_user.user_id
    order.assigned_at = datetime.now(timezone.utc)  

    if assign_data.assignment_notes:
        order.assignment_notes = assign_data.assignment_notes

    db.commit()
    db.refresh(order)
    return order


""" Generar archivo(s) TXT del pedido en formato de ancho fijo, con soporte para división por partes """
def generate_order_txt_files(db: Session, order_id: int, items_per_file: Optional[int] = None) -> List[Tuple[str, str]]:
    """
    Genera uno o varios archivos TXT en formato de ancho fijo para el pedido.
    Retorna una lista de tuplas (nombre_archivo, contenido_txt).
    
    Si items_per_file no se especifica, es None, 0, o >= total_items, retorna 1 solo archivo `pedido_{order_id}.txt`.
    Si se especifica items_per_file (ej. 4, 5, 10) y el pedido supera ese límite:
      Retorna archivos `pedido_{order_id}_1.txt`, `pedido_{order_id}_2.txt`, etc.
    """
    order = get_order(db, order_id)
    if not order:
        raise ValueError(f"Pedido {order_id} no encontrado")
    
    lines = []
    
    for item in order.items:
        if not item.product:
            continue
        
        # Obtener datos del producto y item
        product_id = item.product.product_id or ""
        quantity = item.quantity
        unit_price = Decimal(str(item.price_without_iva))  # Precio SIN IVA para ERP
        
        # 1. Product ID (40 chars, alineado izquierda)
        product_id_field = product_id[:40].ljust(40)
        
        # 2. Unidad (7 chars, alineado izquierda)
        unit = item.product.unidad_medida or "PZ"  # Default a "PZ" si es None
        unit_field = unit[:7].ljust(7)  # Truncar a 7 chars y alinear izquierda
        
        # 3 y 4. Decimales fijos (12 chars c/u, incluye espaciado)
        decimal1_field = "0.00000000  "
        decimal2_field = "0.00000000  "
        
        # 5. Espaciado central (28 espacios)
        spaces_field = " " * 28
        
        # 6. Columna auxiliar (10 chars, alineado derecha)
        other_field = str(1).rjust(10)
        
        # 7. Cantidad (20 chars, 8 decimales, alineado derecha)
        quantity_str = f"{float(quantity):.8f}".rjust(20)
        
        # 8. Precio Unitario (20 chars, 8 decimales, alineado derecha)
        total_price_str = f"{float(unit_price):.8f}".rjust(20)
        
        # Construir línea completa
        line = (
            product_id_field +
            unit_field +
            decimal1_field + 
            decimal2_field +
            spaces_field +
            other_field +
            quantity_str +
            total_price_str
        )
        
        # Agregar trailing spaces hasta ~404 chars (longitud total de linea en archivo valido)
        line = line.ljust(405)
        
        lines.append(line)
    
    if not lines:
        filename = f"pedido_{order_id}_1.txt" if (items_per_file and items_per_file > 0) else f"pedido_{order_id}.txt"
        return [(filename, "")]
        
    # Si no se solicitó división por partes (items_per_file es None o <= 0), retornar 1 solo archivo completo
    if not items_per_file or items_per_file <= 0:
        content = "\r\n".join(lines) + "\r\n"
        return [(f"pedido_{order_id}.txt", content)]
        
    # Dividir las líneas en partes/chunks de tamaño items_per_file
    chunk_count = (len(lines) + items_per_file - 1) // items_per_file
    
    files = []
    for i in range(chunk_count):
        chunk = lines[i * items_per_file : (i + 1) * items_per_file]
        content = "\r\n".join(chunk) + "\r\n"
        filename = f"pedido_{order_id}_{i+1}.txt"
        files.append((filename, content))
        
    return files

def generate_order_txt(db: Session, order_id: int) -> str:
    """ Mantiene retrocompatibilidad retornando el contenido completo en un solo string """
    files = generate_order_txt_files(db, order_id)
    return files[0][1]

def set_order_sync_status(db: Session, order_id: int, is_synced: bool) -> Optional[Order]:
    """Actualiza el estado de sincronización ERP (is_synced) de un pedido"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return None
    order.is_synced = is_synced
    db.commit()
    db.refresh(order)
    return order
