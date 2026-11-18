"""
CRUD y Gestión de Modificación y Edición de Pedidos Abiertos (Order Edit):

Funciones y Operaciones:
- Modificar partidas de un pedido existente: agregar nuevos ítems, actualizar cantidades o eliminar líneas.
- Recalcular automáticamente precio base, markup, IVA, descuentos unitarios y totales de la orden (`total_amount`, `order_profit`).
- Actualizar datos complementarios: costo de envío (`shipping_cost`), dirección de entrega y notas de asignación.
- Sincronizar en tiempo real el stock de productos, partidas de almacén (`WarehouseOrderItem`) y estadísticas anuales (`sync_order_products_on_edit`).

Reglas de Negocio y Restricciones (PBAC / RBAC Dinámico):
1. Restricciones por Estado del Pedido:
   - Solo se pueden editar pedidos en estado `pending_validation` o `approved` antes de empaque.
   - Si el pedido está `cancelled` o `delivered`, la edición está estrictamente bloqueada arrojando error 400.
2. Integridad de Inventario:
   - La modificación ajusta el inventario de productos comparando el diferencial entre cantidades previas y nuevas.
3. Permisos y Control de Acceso:
   - La edición requiere capacidad granular `orders.edit`.
   - Para colaboradores no administradores, se valida que el cliente pertenezca a sus grupos comerciales asignados (`user_can_manage_order`).
"""

from typing import List

from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from utils.price_utils import calculate_product_price_breakdown
from crud.crud_discount import get_active_discounts_for_products


from db.base import Order, OrderItem, Product, PriceListItem, CustomerInfo, OrderStatus
from schemas.order_edit import OrderItemEdit

"""Edita los items de un pedido existente"""
def edit_order_items(db: Session, order_id: int, items: List[OrderItemEdit], customer_id: int, shipping_cost: float = None, assignment_notes: str = None, shipping_address_number: int = None, invoice_type: str = None, is_synced: bool = None) -> Order:    
    # Obtener el pedido
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )
    
    # Validar que el pedido NO este cancelado o entregado
    if order.status in [OrderStatus.cancelled, OrderStatus.delivered]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede editar un pedido en estado '{order.status.value}'"
        )
    
    # Obtener la lista de precios del cliente
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == customer_id
    ).first()
    
    if not customer_info or not customer_info.price_list_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente no tiene una lista de precios asignada"
        )
    
    price_list_id = customer_info.price_list_id
    
    # Snapshot previo de items si el pedido ya está en estado contabilizado
    is_counted_status = order.status in [OrderStatus.approved, OrderStatus.shipped, OrderStatus.delivered]
    old_items_snapshot = []
    if is_counted_status and order.items:
        old_items_snapshot = [
            {
                "product_id": it.product_id,
                "quantity": it.quantity or 0,
                "final_price": Decimal(str(it.final_price or 0)),
                "base_price": Decimal(str(it.base_price or 0)) if it.base_price is not None else Decimal("0.00"),
                "price_without_iva": Decimal(str(it.price_without_iva or 0)) if it.price_without_iva is not None else Decimal("0.00")
            }
            for it in order.items if it.product_id
        ]

    # Obtener items existentes del pedido
    existing_items = {item.order_item_id: item for item in order.items}
    
    # IDs de items que se mantendran/actualizaran
    items_to_keep = set()
    new_items_list = []
    # Map de cantidades previas para sincronización de stock y apartados (si no está aprobado)
    old_items_map = {item.product_id: item.quantity for item in order.items if item.product_id}

    # Procesar cada item de la solicitud
    new_total = Decimal('0.00')
    new_profit = Decimal('0.00')
    
    # Optimizacion O(1) queries: Cargar productos, precios de lista y descuentos en bulk antes de iterar
    req_product_ids = [it.product_id for it in items if it.product_id]
    bulk_products = db.query(Product).filter(Product.product_id.in_(req_product_ids)).all() if req_product_ids else []
    product_map = {p.product_id: p for p in bulk_products}

    bulk_price_items = db.query(PriceListItem).filter(
        PriceListItem.price_list_id == price_list_id,
        PriceListItem.product_id.in_(req_product_ids)
    ).all() if req_product_ids else []
    price_item_map = {pi.product_id: pi for pi in bulk_price_items}

    discounts_map = get_active_discounts_for_products(
        db=db,
        product_ids=req_product_ids,
        price_list_id=price_list_id
    )

    for item_data in items:
        # Obtener informacion del producto desde mapa en memoria O(1)
        product = product_map.get(item_data.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto '{item_data.product_id}' no encontrado"
            )
        
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El producto '{product.name}' no esta activo"
            )
        
        # Obtener markup de la lista de precios desde mapa O(1)
        price_item = price_item_map.get(item_data.product_id)
        
        if not price_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El producto '{product.name}' no esta en la lista de precios del cliente"
            )
        
        # Calcular precio final Y DESCUENTOS usando utilidad centralizada con descuento precargado        
        breakdown = calculate_product_price_breakdown(
            product=product,
            price_item=price_item,
            db=None,
            active_discount=discounts_map.get(item_data.product_id)
        )
        
        base_price = breakdown["base_price"]
        markup_percentage = breakdown["markup_percentage"]
        iva_percentage = breakdown["iva_percentage"]
        price_without_iva = breakdown["price_without_iva"]
        final_price = breakdown["final_price_with_iva"]
        discount_applied = breakdown["discount_applied"]
        discount_type = breakdown["discount_type"]
        
        # Si el item ya existe, actualizarlo
        if item_data.order_item_id and item_data.order_item_id in existing_items:
            existing_item = existing_items[item_data.order_item_id]
            existing_item.quantity = item_data.quantity
            existing_item.product_id = item_data.product_id
            existing_item.base_price = base_price
            existing_item.markup_percentage = markup_percentage
            existing_item.iva_percentage = iva_percentage
            existing_item.price_without_iva = price_without_iva
            existing_item.final_price = final_price
            existing_item.discount_applied = float(discount_applied) if discount_applied else 0.0
            existing_item.discount_type = discount_type
            
            items_to_keep.add(item_data.order_item_id)
        else:
            # Crear nuevo item
            new_item = OrderItem(
                order_id=order_id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                base_price=base_price,
                markup_percentage=markup_percentage,
                iva_percentage=iva_percentage,
                price_without_iva=price_without_iva,
                final_price=final_price,
                discount_applied=float(discount_applied) if discount_applied else 0.0,
                discount_type=discount_type
            )
            db.add(new_item)
            new_items_list.append(new_item)
        
        # Sumar al total (con IVA) y ganancia (markup)
        new_total += final_price * item_data.quantity
        new_profit += (price_without_iva - base_price) * item_data.quantity
    
    # Eliminar items que ya no estan en la lista
    for item_id, item in existing_items.items():
        if item_id not in items_to_keep:
            db.delete(item)
    
    # Actualizar shipping_cost si se proporciona
    if shipping_cost is not None:
        order.shipping_cost = shipping_cost
    
    # Actualizar assignment_notes si se proporciona
    if assignment_notes is not None:
        order.assignment_notes = assignment_notes

    # Actualizar invoice_type si se proporciona
    if invoice_type is not None:
        order.invoice_type = invoice_type

    # Actualizar sincronización ERP: al editar items se marca False para re-sincronizar con el ERP (a menos que se especifique explícito)
    if is_synced is not None:
        order.is_synced = is_synced
    else:
        order.is_synced = False

    # Actualizar dirección de envío si se proporciona
    if shipping_address_number is not None:
        if shipping_address_number not in [1, 2, 3]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Número de dirección de envío inválido (debe ser 1, 2 o 3)"
            )
        order.shipping_address_number = shipping_address_number
        if customer_info:
            address_key = f"address_{shipping_address_number}"
            shipping_address = getattr(customer_info, address_key, None)
            if not shipping_address:
                shipping_address = customer_info.address_1 or customer_info.address_2 or customer_info.address_3
            order.shipping_address_snapshot = shipping_address or "No especificada"
    
    # Actualizar el total y ganancia del pedido
    shipping_cost_decimal = Decimal(str(order.shipping_cost or 0))
    order.total_amount = new_total + shipping_cost_decimal
    order.order_profit = new_profit

    # Sincronizar bodega si el pedido ya fue enviado a surtido
    if order.sent_to_warehouse:
        # Asegurar que los nuevos items insertados tengan su order_item_id generado en DB antes del sync
        db.flush()
        deleted_item_ids = [item_id for item_id in existing_items if item_id not in items_to_keep]
        from crud.crud_warehouse import sync_warehouse_on_order_edit
        sync_warehouse_on_order_edit(db, order, deleted_item_ids, new_items_list)

    # Sincronizar apartados y existencias según reglas operacionales (101 y 102) si el pedido no está aprobado aún
    if not is_counted_status:
        new_items_map = {item.product_id: item.quantity for item in order.items if item.product_id}
        from utils.stock_rules_utils import sync_order_edit_stock_rules
        sync_order_edit_stock_rules(db, order, old_items_map, new_items_map)

    db.commit()
    db.refresh(order)

    # Sincronizar product_yearly_stats si el pedido estaba contabilizado
    if is_counted_status:
        from crud.crud_product_yearly_stats import sync_order_products_on_edit
        sync_order_products_on_edit(db, order, old_items_snapshot)
    
    return order
