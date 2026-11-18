"""
Utilidades para gestión de configuración y reglas de apartados/descuento de stock
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from db.base import SystemConfig, OrderStockHold, Product, OrderItem, Order

# IDs estáticos de configuración operacional
CONFIG_ID_APARTAR = 101   # order.apartar
CONFIG_ID_DISCOUNT = 102  # order.discount


def is_config_active(db: Session, config_id: int) -> bool:
    """
    Verifica si una bandera de configuración del sistema está activa.
    """
    conf = db.query(SystemConfig).filter(SystemConfig.config_id == config_id).first()
    return bool(conf and conf.is_active)


def get_active_stock_configs(db: Session) -> Dict[str, bool]:
    """
    Obtiene el estado de las banderas clave de inventario de forma agrupada.
    """
    configs = db.query(SystemConfig).filter(
        SystemConfig.config_id.in_([CONFIG_ID_APARTAR, CONFIG_ID_DISCOUNT])
    ).all()
    status = {"apartar": False, "discount": False}
    for c in configs:
        if c.config_id == CONFIG_ID_APARTAR:
            status["apartar"] = bool(c.is_active)
        elif c.config_id == CONFIG_ID_DISCOUNT:
            status["discount"] = bool(c.is_active)
    return status


def validate_and_process_order_stock_rules(db: Session, order_id: int, items_data: List[Dict]) -> None:
    """
    Aplica las reglas de inventario para pedidos (web o directos/manuales):
    - Si ambas están en False (order.apartar y order.discount):
        No se valida stock, no se aparta nada y no se descuenta nada (se confía 100% en el ERP SAI).

    - Si order.apartar (101) o order.discount (102) están activas:
        * Se evalúa si algún item de la orden causaría existencias negativas (solicitado > disponible).
        * REGLA DE ORO ATÓMICA: Si va a dar negativo, mejor de la orden completa NO se aparta nada.
          Con que 1 solo orderitem dé negativo, no se aparta ningún otro orderitem.
        * Si ningún item da negativo:
            - Si order.apartar está activo: se registran los apartados en order_stock_holds.
            - Si order.discount está activo: se descuenta del stock_count del producto garantizando >= 0.

    Args:
        db: Sesión de SQLAlchemy
        order_id: ID del pedido creado
        items_data: Lista de dicts con {'product_id': str, 'quantity': int}
    """
    flags = get_active_stock_configs(db)
    should_hold = flags["apartar"]
    should_discount = flags["discount"]

    # Si ambas están en False, se confía 100% en el ERP: no se aparta ni se descuenta
    if not should_hold and not should_discount:
        return

    # Consolidar cantidades por product_id para evaluar stock real acumulado y evitar duplicados
    aggregated_items: Dict[str, int] = {}
    for item in items_data:
        pid = str(item.get("product_id") or "").strip()
        qty = int(item.get("quantity", 0))
        if pid and qty > 0:
            aggregated_items[pid] = aggregated_items.get(pid, 0) + qty

    if not aggregated_items:
        return

    # 1. Comprobar si algún item de la orden causaría números negativos (solicitado > disponible)
    any_item_exceeds_stock = False
    products_cache = {}

    for pid, qty in aggregated_items.items():
        product = db.query(Product).filter(Product.product_id == pid).first()
        products_cache[pid] = product
        available_stock = int(product.stock_count or 0) if product else 0

        if qty > available_stock:
            any_item_exceeds_stock = True
            break

    # 2. Aplicar regla 101 (order.apartar):
    # "tomando en cuenta que no dé negativo; si va a dar negativo mejor de la orden completa
    # no apartes nada, con que 1 orderitem dé negativo, no se aparta ningún otro orderitem"
    if should_hold and not any_item_exceeds_stock:
        for pid, qty in aggregated_items.items():
            existing_hold = db.query(OrderStockHold).filter(
                OrderStockHold.order_id == order_id,
                OrderStockHold.product_id == pid
            ).first()
            if existing_hold:
                existing_hold.quantity = qty
            else:
                db.add(OrderStockHold(
                    order_id=order_id,
                    product_id=pid,
                    quantity=qty
                ))

    # 3. Aplicar regla 102 (order.discount):
    # Descuenta inmediatamente las existencias del catálogo web (garantizando >= 0)
    if should_discount:
        for pid, qty in aggregated_items.items():
            product = products_cache.get(pid) or db.query(Product).filter(Product.product_id == pid).first()
            if product:
                product.stock_count = max(0, int(product.stock_count or 0) - qty)


# Alias por compatibilidad
process_customer_order_stock_rules = validate_and_process_order_stock_rules


def release_order_stock_holds(db: Session, order_id: int) -> None:
    """
    Elimina los apartados de un pedido cuando pasa a 'approved'
    (porque el ERP/SAI ya lo procesó y descontó de forma definitiva).
    """
    db.query(OrderStockHold).filter(OrderStockHold.order_id == order_id).delete(synchronize_session=False)


def restore_cancelled_order_stock(db: Session, order: Order) -> None:
    """
    Restaura el stock y/o apartados cuando un pedido es cancelado:
    
    1. Si 'order.discount' (102) está ACTIVO:
       - Los items del pedido cancelado se regresan (se vuelven a sumar a products.stock_count).
       - Si está INACTIVO: NO se regresa ni se suma nada (ya que no se descontó stock al crearlo).

    2. Si 'order.apartar' (101) está ACTIVO:
       - Los apartados asociados a este pedido deben restarse, SIEMPRE Y CUANDO la resta no dé menor a 0.
       - Blindaje ante casos donde order.apartar estaba desactivado al crear el pedido y luego se activó:
         si el pedido no tenía apartados registrados, no se resta nada y jamás da negativo.
       - Si está INACTIVO: NO se restan ni tocan apartados.
    """
    flags = get_active_stock_configs(db)
    should_discount = flags["discount"]
    should_hold = flags["apartar"]

    # 1. Regla order.discount: volver a sumar el stock a los productos SOLO si está activa
    if should_discount:
        items_to_restore: Dict[str, int] = {}
        for order_item in (order.items or []):
            if order_item.product_id and order_item.quantity:
                pid = str(order_item.product_id).strip()
                qty = int(order_item.quantity)
                if pid and qty > 0:
                    items_to_restore[pid] = items_to_restore.get(pid, 0) + qty

        for pid, qty in items_to_restore.items():
            product = db.query(Product).filter(Product.product_id == pid).first()
            if product:
                product.stock_count = max(0, int(product.stock_count or 0)) + qty

    # 2. Regla order.apartar: restar apartados SOLO si está activa y con blindaje estricto >= 0
    if should_hold:
        holds = db.query(OrderStockHold).filter(OrderStockHold.order_id == order.order_id).all()
        holds_by_product = {h.product_id: h for h in holds}

        for order_item in (order.items or []):
            if not order_item.product_id:
                continue
            qty_to_subtract = int(order_item.quantity or 0)
            hold = holds_by_product.get(order_item.product_id)

            if hold:
                current_hold_qty = int(hold.quantity or 0)
                # Restar asegurando que nunca dé menor a 0
                new_hold_qty = max(0, current_hold_qty - qty_to_subtract)
                if new_hold_qty == 0:
                    db.delete(hold)
                else:
                    hold.quantity = new_hold_qty

        # Limpiar cualquier hold residual asociado a este pedido
        for h in holds:
            if h in db:
                db.delete(h)


def sync_order_edit_stock_rules(db: Session, order: Order, old_items_map: Dict[str, int], new_items_map: Dict[str, int]) -> None:
    """
    Sincroniza los apartados (order_stock_holds) y existencias (products.stock_count)
    cuando se edita un pedido pendiente (antes de ser aprobado/surtido):
    - Si 101 o 102 están activos:
        * Valida que ningún producto con incremento delta > 0 sobrepase el stock actual disponible.
        * Ajusta los apartados y/o el stock_count sumando o restando el delta según corresponda.
    - Si ambos están inactivos (False): No hace nada (se confía 100% en el ERP).
    """
    flags = get_active_stock_configs(db)
    should_hold = flags["apartar"]
    should_discount = flags["discount"]

    if not should_hold and not should_discount:
        return

    all_product_ids = set(old_items_map.keys()) | set(new_items_map.keys())
    deltas = {}  # product_id -> delta (positivo si se pide más, negativo si se redujo)

    for pid in all_product_ids:
        old_qty = old_items_map.get(pid, 0)
        new_qty = new_items_map.get(pid, 0)
        delta = new_qty - old_qty
        if delta != 0:
            deltas[pid] = delta

    # 1. Validación de stock si delta > 0
    for pid, delta in deltas.items():
        if delta > 0:
            product = db.query(Product).filter(Product.product_id == pid).first()
            available = int(product.stock_count or 0) if product else 0
            if delta > available:
                prod_name = product.name if product else pid
                raise ValueError(
                    f"Stock insuficiente para '{prod_name}'. Disponible: {available}, Adicional solicitado: {delta}."
                )

    # 2. Aplicar ajustes
    for pid, delta in deltas.items():
        if should_hold:
            hold = db.query(OrderStockHold).filter(
                OrderStockHold.order_id == order.order_id,
                OrderStockHold.product_id == pid
            ).first()
            new_total_qty = new_items_map.get(pid, 0)
            if new_total_qty <= 0:
                if hold:
                    db.delete(hold)
            else:
                if hold:
                    hold.quantity = max(0, new_total_qty)
                else:
                    db.add(OrderStockHold(
                        order_id=order.order_id,
                        product_id=pid,
                        quantity=max(0, new_total_qty)
                    ))

        if should_discount:
            product = db.query(Product).filter(Product.product_id == pid).first()
            if product:
                # Si delta > 0, se descuenta más; si delta < 0, se devuelve stock al producto
                product.stock_count = max(0, int(product.stock_count or 0) - delta)
