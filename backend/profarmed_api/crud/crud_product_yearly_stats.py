"""
CRUD y Sincronización de Estadísticas Anuales por Producto (ProductYearlyStat):

Funciones y Operaciones:
- Consultas O(1) de productos top por año: mayor número de pedidos, mayor volumen de unidades vendidas y mayor margen/utilidad generada.
- Sincronización en tiempo real al aprobar pedidos (`sync_order_products_on_approve`).
- Sincronización en tiempo real al editar pedidos aprobados/enviados/entregados (`sync_order_products_on_edit`).
- Sincronización en tiempo real al cancelar pedidos aprobados (`sync_order_products_on_cancel`).
- Recálculo global y backfill idempotente para migraciones históricas (`recalculate_all_product_yearly_stats`).

Reglas de Negocio y Arquitectura de Estadísticas:
1. Precálculo y Rendimiento O(1):
   - Evita agrupaciones masivas y bloqueos de tablas sobre el histórico de partidas de órdenes.
   - Cada registro `ProductYearlyStat` consolida: `orders_count`, `units_sold`, `total_revenue` y `total_profit` por año fiscal.
2. Manejo de Años y Fechas:
   - Los años se determinan en la zona horaria oficial `America/Mexico_City` según la fecha de creación del pedido (`created_at`).
3. Integridad Financiera:
   - Solo se contabilizan pedidos que alcancen estados confirmados (`approved`, `shipped`, `delivered`).
   - Al cancelarse un pedido, se revierten exactamente las cantidades y montos previamente acumulados.
4. Control de Acceso y Reglas PBAC / RBAC Dinámico:
   - Consulta de rankings y volúmenes: Requiere permisos analíticos o comerciales como `catalog.view`, `reports.view` o `dashboard.view`.
   - Consulta de márgenes y ganancia neta (`total_profit`): Métrica financiera confidencial reservada a roles con `reports.financial` o `catalog.prices`.
   - Recálculo global: Función administrativa reservada a `system.admin`.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
try:
    from zoneinfo import ZoneInfo
    MX_TZ = ZoneInfo("America/Mexico_City")
except Exception:
    try:
        import pytz
        MX_TZ = pytz.timezone("America/Mexico_City")
    except Exception:
        MX_TZ = timezone.utc

from sqlalchemy.orm import Session
from db.base import Order, Product, ProductYearlyStat, OrderStatus


"""Extrae el año del pedido en la zona horaria de México"""
def get_order_year(order: Order) -> int:
    if order.created_at:
        dt = order.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MX_TZ).year
    return datetime.now(MX_TZ).year


def sync_order_products_on_approve(db: Session, order: Order):
    """
    Suma las partidas de un pedido a product_yearly_stats cuando pasa a 'approved'.
    - orders_count: +1 (este producto apareció en un nuevo pedido aprobado)
    - units_sold: +cantidad
    - total_revenue: +monto con IVA
    - total_profit: +ganancia neta
    """
    if not order.items:
        return

    year = get_order_year(order)

    for item in order.items:
        if not item.product_id:
            continue

        stat = db.query(ProductYearlyStat).filter(
            ProductYearlyStat.product_id == item.product_id,
            ProductYearlyStat.year == year
        ).first()

        qty = item.quantity or 0
        final_price = Decimal(str(item.final_price or 0))
        base_price = Decimal(str(item.base_price or 0)) if item.base_price is not None else Decimal("0.00")
        price_without_iva = Decimal(str(item.price_without_iva or 0)) if item.price_without_iva is not None else Decimal("0.00")

        line_revenue = final_price * qty
        line_profit = (price_without_iva - base_price) * qty

        if not stat:
            stat = ProductYearlyStat(
                product_id=item.product_id,
                year=year,
                orders_count=1,
                units_sold=qty,
                total_revenue=line_revenue,
                total_profit=line_profit
            )
            db.add(stat)
        else:
            stat.orders_count += 1
            stat.units_sold += qty
            stat.total_revenue += line_revenue
            stat.total_profit += line_profit

    db.commit()


def sync_order_products_on_cancel(db: Session, order: Order):
    """
    Resta las partidas de un pedido de product_yearly_stats cuando se cancela
    (si previamente estuvo en approved, shipped o delivered).
    """
    if not order.items:
        return

    year = get_order_year(order)

    for item in order.items:
        if not item.product_id:
            continue

        stat = db.query(ProductYearlyStat).filter(
            ProductYearlyStat.product_id == item.product_id,
            ProductYearlyStat.year == year
        ).first()

        if stat:
            qty = item.quantity or 0
            final_price = Decimal(str(item.final_price or 0))
            base_price = Decimal(str(item.base_price or 0)) if item.base_price is not None else Decimal("0.00")
            price_without_iva = Decimal(str(item.price_without_iva or 0)) if item.price_without_iva is not None else Decimal("0.00")

            line_revenue = final_price * qty
            line_profit = (price_without_iva - base_price) * qty

            stat.orders_count = max(0, stat.orders_count - 1)
            stat.units_sold = max(0, stat.units_sold - qty)
            stat.total_revenue -= line_revenue
            stat.total_profit -= line_profit

    db.commit()


def sync_order_products_on_edit(db: Session, order: Order, old_items: List[dict]):
    """
    Ajusta product_yearly_stats al editar un pedido que ya está aprobado/enviado/entregado.
    Resta los items antiguos y suma los nuevos.
    """
    year = get_order_year(order)

    # 1. Revertir snapshot antiguo
    for item in old_items:
        pid = item["product_id"]
        stat = db.query(ProductYearlyStat).filter(
            ProductYearlyStat.product_id == pid,
            ProductYearlyStat.year == year
        ).first()

        if stat:
            qty = item["quantity"]
            final_price = item["final_price"]
            base_price = item["base_price"]
            price_without_iva = item["price_without_iva"]

            line_rev = final_price * qty
            line_prof = (price_without_iva - base_price) * qty

            stat.orders_count = max(0, stat.orders_count - 1)
            stat.units_sold = max(0, stat.units_sold - qty)
            stat.total_revenue -= line_rev
            stat.total_profit -= line_prof

    # 2. Aplicar nuevos items del pedido
    for item in order.items:
        stat = db.query(ProductYearlyStat).filter(
            ProductYearlyStat.product_id == item.product_id,
            ProductYearlyStat.year == year
        ).first()

        qty = item.quantity or 0
        final_price = Decimal(str(item.final_price or 0))
        base_price = Decimal(str(item.base_price or 0)) if item.base_price is not None else Decimal("0.00")
        price_without_iva = Decimal(str(item.price_without_iva or 0)) if item.price_without_iva is not None else Decimal("0.00")

        line_rev = final_price * qty
        line_prof = (price_without_iva - base_price) * qty

        if not stat:
            stat = ProductYearlyStat(
                product_id=item.product_id,
                year=year,
                orders_count=1,
                units_sold=qty,
                total_revenue=line_rev,
                total_profit=line_prof
            )
            db.add(stat)
        else:
            stat.orders_count += 1
            stat.units_sold += qty
            stat.total_revenue += line_rev
            stat.total_profit += line_prof

    db.commit()


def recalculate_all_yearly_stats(db: Session, target_year: Optional[int] = None):
    """
    Recalcula desde cero product_yearly_stats para pedidos con estatus
    approved, shipped o delivered. Idempotente y seguro para migraciones.
    """
    query = db.query(Order).filter(
        Order.status.in_([
            OrderStatus.approved,
            OrderStatus.shipped,
            OrderStatus.delivered
        ])
    )

    if target_year is not None:
        db.query(ProductYearlyStat).filter(ProductYearlyStat.year == target_year).delete()
    else:
        db.query(ProductYearlyStat).delete()

    db.commit()

    orders = query.all()
    temp_stats = {}  # (product_id, year) -> dict

    for order in orders:
        year = get_order_year(order)
        if target_year is not None and year != target_year:
            continue

        for item in order.items:
            if not item.product_id:
                continue

            key = (item.product_id, year)
            if key not in temp_stats:
                temp_stats[key] = {
                    "orders_count": 0,
                    "units_sold": 0,
                    "total_revenue": Decimal("0.00"),
                    "total_profit": Decimal("0.00")
                }

            qty = item.quantity or 0
            final_price = Decimal(str(item.final_price or 0))
            base_price = Decimal(str(item.base_price or 0)) if item.base_price is not None else Decimal("0.00")
            price_without_iva = Decimal(str(item.price_without_iva or 0)) if item.price_without_iva is not None else Decimal("0.00")

            temp_stats[key]["orders_count"] += 1
            temp_stats[key]["units_sold"] += qty
            temp_stats[key]["total_revenue"] += final_price * qty
            temp_stats[key]["total_profit"] += (price_without_iva - base_price) * qty

    for (product_id, year), data in temp_stats.items():
        stat = ProductYearlyStat(
            product_id=product_id,
            year=year,
            orders_count=data["orders_count"],
            units_sold=data["units_sold"],
            total_revenue=data["total_revenue"],
            total_profit=data["total_profit"]
        )
        db.add(stat)

    db.commit()


def get_top_products_yearly(db: Session, year: int, limit: int = 5, sort_by: str = "orders"):
    """
    Retorna los productos top del año especificado en O(1).
    sort_by:
      - 'orders': Ordenado por pedidos únicos donde apareció (popularidad)
      - 'units': Ordenado por total de unidades vendidas (volumen)
      - 'profit': Ordenado por ganancia neta acumulada (rentabilidad)
      - 'revenue': Ordenado por facturación total ($)
    """
    query = db.query(ProductYearlyStat, Product).join(
        Product, Product.product_id == ProductYearlyStat.product_id
    ).filter(
        ProductYearlyStat.year == year
    )

    if sort_by == "units":
        query = query.order_by(ProductYearlyStat.units_sold.desc())
    elif sort_by == "profit":
        query = query.order_by(ProductYearlyStat.total_profit.desc())
    elif sort_by == "revenue":
        query = query.order_by(ProductYearlyStat.total_revenue.desc())
    else:  # default 'orders'
        query = query.order_by(ProductYearlyStat.orders_count.desc())

    results = query.limit(limit).all()

    items = []
    for stat, product in results:
        items.append({
            "product_id": stat.product_id,
            "name": product.name if product else stat.product_id,
            "codebar": product.codebar if product else None,
            "orders_count": stat.orders_count,
            "units_sold": stat.units_sold,
            "total_revenue": float(stat.total_revenue),
            "total_profit": float(stat.total_profit)
        })

    return items
