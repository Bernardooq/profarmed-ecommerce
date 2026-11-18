"""
CRUD y Generación de Métricas, KPIs e Informes de Paneles de Control (Dashboards):

Funciones y Operaciones:
- Dashboard de Administrador y Métricas Consolidadas: Métricas globales de usuarios, clientes, productos, pedidos, facturación y desglose dinámico por rol.
- Dashboard Operativo de Grupos Comerciales: Métricas de pedidos agregadas para colaboradores con grupos asignados (`GroupUser`).
- Informes de Ventas: Reportes analíticos por rango de fechas (hoy, semana, mes, custom) con desglose de utilidad neta.

Reglas de Negocio y Formatos:
1. Localización Temporal:
   - Todas las consultas de fechas e intervalos se calculan en la zona horaria oficial `America/Mexico_City`.
2. Segmentación de Ingresos y Ganancias:
   - Ingresos Totales (`total_revenue`): Suma de montos finales de pedidos aprobados/entregados con IVA incluido.
   - Utilidad Neta (`total_profit`): Suma calculada de `(precio_sin_iva - precio_base) * cantidad`.
3. Permisos de Visualización (PBAC / RBAC Dinámico):
   - Colaboradores Operativos de Campo (cualquier rol dinámico): Visualizan pedidos y ventas acotados estrictamente a sus grupos asignados (`orders.view`, `groups.view`).
   - Administradores y Reportes Globales: Acceso transversal sin restricciones con KPIs consolidados (`reports.view`, `reports.financial`).
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_, and_

from db.base import Order, OrderStatus, Product, User, Customer, CustomerInfo, GroupUser, OrderStat, Role
from schemas.dashboards import (
    DashboardStats,
    SalesReport,
    SalesReportItem,
    RoleBreakdownItem,
    OperationalDashboardStats,
    DashboardFinanceStats,
    DashboardOrderStats,
    DashboardUsersCustomersStats,
    DashboardInventoryStats
)
from crud.crud_commercial_group import get_user_groups
try:
    from zoneinfo import ZoneInfo
    MX_TZ = ZoneInfo("America/Mexico_City")
except Exception:
    try:
        import pytz
        MX_TZ = pytz.timezone("America/Mexico_City")
    except Exception:
        MX_TZ = timezone.utc


# ============================================================================
# FUNCIONES ATÓMICAS DESACOPLADAS PARA DASHBOARD
# ============================================================================

def get_dashboard_finance_stats(db: Session) -> DashboardFinanceStats:
    """Calcula métricas financieras globales (ingresos y utilidades anuales estimadas)"""
    current_year = datetime.now(MX_TZ).year
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.status.in_([
            OrderStatus.approved,
            OrderStatus.shipped,
            OrderStatus.delivered
        ]),
        func.extract('year', Order.created_at) == current_year
    ).scalar() or 0

    total_profit = db.query(func.sum(Order.order_profit)).filter(
        Order.status.in_([
            OrderStatus.approved,
            OrderStatus.shipped,
            OrderStatus.delivered
        ]),
        func.extract('year', Order.created_at) == current_year
    ).scalar() or 0

    return DashboardFinanceStats(
        total_revenue=float(total_revenue),
        total_profit=float(total_profit),
        current_year=current_year
    )


def get_dashboard_order_stats(
    db: Session,
    current_user: Optional[User] = None,
    sales_group_id: Optional[int] = None,
    is_admin_or_global: bool = False
) -> DashboardOrderStats:
    """
    Calcula embudo y estados de órdenes.
    - Si is_admin_or_global=True o current_user posee permiso global (orders.view_all/system.admin): consulta global (sales_group_id == 0).
    - Si es colaborador operativo: filtra estrictamente por sus grupos de venta asignados.
    """
    if is_admin_or_global or current_user is None:
        target_group_ids = [sales_group_id] if sales_group_id is not None else None
        user_group_ids = []
    else:
        has_perm = getattr(current_user, "has_permission", None)
        can_view_all = callable(has_perm) and (has_perm("system.admin") or has_perm("orders.view_all"))
        can_orders = can_view_all or (callable(has_perm) and (has_perm("orders.view") or has_perm("orders.group_view")))
        if not can_orders:
            return DashboardOrderStats(
                pending_orders=0,
                approved_orders=0,
                shipped_orders=0,
                delivered_orders=0,
                cancelled_orders=0,
                total_orders=0,
                assigned_groups_count=0
            )

        user_group_ids = get_user_groups(db, current_user.user_id) if hasattr(current_user, "user_id") else []

        if sales_group_id is not None:
            can_access_group = (callable(has_perm) and (has_perm("system.admin") or has_perm("groups.manage") or has_perm("orders.view_all"))) or (sales_group_id in user_group_ids)
            if not can_access_group:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No tiene permisos para consultar estadísticas del grupo de ventas {sales_group_id}."
                )
            target_group_ids = [sales_group_id]
        else:
            if can_view_all:
                target_group_ids = None
            else:
                target_group_ids = user_group_ids

    if target_group_ids is not None:
        if target_group_ids:
            rows = db.query(
                OrderStat.status, func.sum(OrderStat.count).label('total')
            ).filter(
                OrderStat.sales_group_id.in_(target_group_ids)
            ).group_by(OrderStat.status).all()
            stats = {r.status: r.total for r in rows}
        else:
            stats = {}
    else:
        rows = db.query(OrderStat.status, OrderStat.count).filter(
            OrderStat.sales_group_id == 0
        ).all()
        stats = {r.status: r.count for r in rows}

    pending_orders = stats.get('pending_validation', 0)
    approved_orders = stats.get('approved', 0)
    shipped_orders = stats.get('shipped', 0)
    delivered_orders = stats.get('delivered', 0)
    cancelled_orders = stats.get('cancelled', 0)
    total_orders = sum(stats.values())

    return DashboardOrderStats(
        pending_orders=pending_orders,
        approved_orders=approved_orders,
        shipped_orders=shipped_orders,
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders,
        total_orders=total_orders,
        assigned_groups_count=len(user_group_ids)
    )


def get_dashboard_users_customers_stats(
    db: Session,
    current_user: Optional[User] = None
) -> DashboardUsersCustomersStats:
    """
    Calcula total de clientes activos y desglose dinámico de colaboradores por rol (excluyendo admin).
    - Clientes:
      - Si posee system.admin o customers.view_all: conteo global nacional.
      - Si solo posee customers.view: conteo acotado a sus grupos de venta asignados.
      - Si no posee permisos de clientes: 0.
    - Personal:
      - Si posee system.admin o users.view: conteo global nacional y desglose de todos los usuarios.
      - Si no posee users.view: 0 personal y lista vacía de roles (cero fuga de datos de usuarios internos).
    """
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and has_perm("system.admin")

    user_group_ids = get_user_groups(db, current_user.user_id) if (current_user and hasattr(current_user, "user_id")) else []

    # 1. Clientes registrados
    has_customer_global = has_admin or (callable(has_perm) and has_perm("customers.view_all"))
    has_customer_view = callable(has_perm) and (has_perm("customers.view") or has_customer_global)

    if has_customer_global or current_user is None:
        total_customers = db.query(func.count(Customer.customer_id)).filter(Customer.is_active == True).scalar() or 0
    elif has_customer_view:
        if user_group_ids:
            total_customers = (
                db.query(func.count(Customer.customer_id.distinct()))
                .join(CustomerInfo, CustomerInfo.customer_id == Customer.customer_id)
                .filter(
                    CustomerInfo.sales_group_id.in_(user_group_ids),
                    Customer.is_active == True
                )
                .scalar() or 0
            )
        else:
            total_customers = 0
    else:
        total_customers = 0

    # 2. Personal y desglose de roles (Estrictamente gobernado por users.view o system.admin)
    has_users_global = has_admin or (callable(has_perm) and has_perm("users.view"))

    if has_users_global or current_user is None:
        total_users = db.query(func.count(User.user_id)).filter(User.is_active == True).scalar() or 0
        roles_data = (
            db.query(Role.role_id, Role.name, Role.slug, func.count(User.user_id))
            .outerjoin(User, and_(User.role_id == Role.role_id, User.is_active == True))
            .filter(Role.slug != "admin", Role.is_active == True)
            .group_by(Role.role_id, Role.name, Role.slug)
            .order_by(Role.name.asc())
            .all()
        )
        roles_breakdown = [
            RoleBreakdownItem(role_id=r[0], name=r[1], slug=r[2], count=r[3])
            for r in roles_data
        ]
    else:
        total_users = 0
        roles_breakdown = []

    return DashboardUsersCustomersStats(
        total_customers=total_customers,
        total_users=total_users,
        roles_breakdown=roles_breakdown
    )


def get_dashboard_inventory_stats(db: Session) -> DashboardInventoryStats:
    """Calcula salud de catálogo y conteos de stock (total, bajo stock, agotados)"""
    total_products = db.query(func.count(Product.product_id)).filter(
        Product.is_active == True
    ).scalar() or 0
    low_stock_count = db.query(func.count(Product.product_id)).filter(
        Product.stock_count < 10,
        Product.stock_count > 0,
        Product.is_active == True
    ).scalar() or 0
    out_of_stock_count = db.query(func.count(Product.product_id)).filter(
        Product.stock_count <= 0,
        Product.is_active == True
    ).scalar() or 0

    return DashboardInventoryStats(
        total_products=total_products,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count
    )


"""Obtiene estadísticas globales del negocio para el dashboard de administrador sin acoplamiento a slugs fijos"""
def get_admin_dashboard_stats(db: Session, current_user: Optional[User] = None) -> DashboardStats:
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and has_perm("system.admin")

    # 1. Finanzas: solo si posee reports.financial o system.admin
    can_financial = has_admin or (callable(has_perm) and has_perm("reports.financial"))
    if can_financial:
        fin_stats = get_dashboard_finance_stats(db)
        total_revenue = fin_stats.total_revenue
        total_profit = fin_stats.total_profit
    else:
        total_revenue = 0.0
        total_profit = 0.0

    # 2. Usuarios y Clientes
    usr_stats = get_dashboard_users_customers_stats(db, current_user=current_user)

    # 3. Inventario: solo si posee catalog.view o system.admin
    can_catalog = has_admin or (callable(has_perm) and has_perm("catalog.view"))
    if can_catalog:
        inv_stats = get_dashboard_inventory_stats(db)
        total_products = inv_stats.total_products
        low_stock_count = inv_stats.low_stock_count
        out_of_stock_count = inv_stats.out_of_stock_count
    else:
        total_products = 0
        low_stock_count = 0
        out_of_stock_count = 0

    # 4. Pedidos: global para admin/orders.view_all, por grupos asignados para campo
    order_stats = get_dashboard_order_stats(db, current_user=current_user)

    return DashboardStats(
        total_users=usr_stats.total_users,
        total_customers=usr_stats.total_customers,
        total_products=total_products,
        total_orders=order_stats.total_orders,
        delivered_orders=order_stats.delivered_orders,
        shipped_orders=order_stats.shipped_orders,
        approved_orders=order_stats.approved_orders,
        cancelled_orders=order_stats.cancelled_orders,
        pending_orders=order_stats.pending_orders,
        total_revenue=total_revenue,
        total_profit=total_profit,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        roles_breakdown=usr_stats.roles_breakdown
    )



"""Obtiene las estadísticas del dashboard operativo filtradas según permisos y grupos de ventas asignados"""
def get_operational_dashboard_stats(
    db: Session,
    current_user: User,
    sales_group_id: Optional[int] = None
) -> OperationalDashboardStats:
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and has_perm("system.admin")
    has_orders_view_all = callable(has_perm) and has_perm("orders.view_all")
    has_groups_manage = callable(has_perm) and has_perm("groups.manage")
    user_group_ids = get_user_groups(db, current_user.user_id)

    # 1. Resolución de ámbito de consulta de grupos
    if sales_group_id is not None:
        can_access_group = has_admin or has_orders_view_all or has_groups_manage or (sales_group_id in user_group_ids)
        if not can_access_group:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene permisos para consultar estadísticas del grupo de ventas {sales_group_id}."
            )
        target_group_ids = [sales_group_id]
    else:
        if has_admin or has_orders_view_all:
            target_group_ids = None  # Acceso global sin restricción de grupo
        else:
            target_group_ids = user_group_ids

    # 2. Agregación de conteos de órdenes desde OrderStat
    if target_group_ids is not None:
        if target_group_ids:
            rows = db.query(
                OrderStat.status, func.sum(OrderStat.count).label('total')
            ).filter(
                OrderStat.sales_group_id.in_(target_group_ids)
            ).group_by(OrderStat.status).all()
            stats = {r.status: r.total for r in rows}
        else:
            stats = {}
    else:
        # Visión global consolidada
        rows = db.query(OrderStat.status, OrderStat.count).filter(
            OrderStat.sales_group_id == 0
        ).all()
        stats = {r.status: r.count for r in rows}

    has_catalog = has_admin or (callable(has_perm) and has_perm("catalog.view"))
    if has_catalog:
        total_products = db.query(func.count(Product.product_id)).filter(Product.is_active == True).scalar() or 0
        low_stock_count = db.query(func.count(Product.product_id)).filter(
            Product.stock_count < 10,
            Product.stock_count > 0,
            Product.is_active == True
        ).scalar() or 0
        out_of_stock_count = db.query(func.count(Product.product_id)).filter(
            Product.stock_count <= 0,
            Product.is_active == True
        ).scalar() or 0
    else:
        total_products = 0
        low_stock_count = 0
        out_of_stock_count = 0

    return OperationalDashboardStats(
        pending_orders=stats.get('pending_validation', 0),
        approved_orders=stats.get('approved', 0),
        shipped_orders=stats.get('shipped', 0),
        delivered_orders=stats.get('delivered', 0),
        cancelled_orders=stats.get('cancelled', 0),
        total_products=total_products,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        assigned_groups_count=len(user_group_ids)
    )

"""Genera un reporte de ventas detallado filtrado por un rango de fechas en horario de México y convertido a UTC"""
def get_sales_report(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None) -> SalesReport:
    if not start_date:
        start_date = datetime.now(MX_TZ).replace(day=1).strftime("%Y-%m-%d")

    if not end_date:
        end_date = datetime.now(MX_TZ).strftime("%Y-%m-%d")

    try:
        parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
        start_dt = datetime.combine(parsed_start.date(), datetime.min.time()).replace(tzinfo=MX_TZ).astimezone(timezone.utc)
    except ValueError:
        parsed_start = datetime.now(MX_TZ).replace(day=1)
        start_dt = datetime.combine(parsed_start.date(), datetime.min.time()).replace(tzinfo=MX_TZ).astimezone(timezone.utc)
        start_date = parsed_start.strftime("%Y-%m-%d")

    try:
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d")
        end_dt = datetime.combine(parsed_end.date(), datetime.max.time()).replace(tzinfo=MX_TZ).astimezone(timezone.utc)
    except ValueError:
        parsed_end = datetime.now(MX_TZ)
        end_dt = datetime.combine(parsed_end.date(), datetime.max.time()).replace(tzinfo=MX_TZ).astimezone(timezone.utc)
        end_date = parsed_end.strftime("%Y-%m-%d")

    orders = db.query(Order).options(
        joinedload(Order.customer),
        selectinload(Order.items)
    ).filter(
        Order.created_at >= start_dt,
        Order.created_at <= end_dt,
        Order.status.in_([
            OrderStatus.approved,
            OrderStatus.shipped,
            OrderStatus.delivered
        ])
    ).order_by(Order.created_at.desc()).all()

    total_orders = len(orders)
    total_revenue = sum(float(order.total_amount) for order in orders)
    total_profit = sum(float(order.order_profit or 0) for order in orders)

    report_items: List[SalesReportItem] = []

    for order in orders:
        customer = order.customer

        items_count = len(order.items) if order.items else 0

        # Convertir created_at de UTC a hora de México (America/Mexico_City)
        order_date_str = "N/A"
        if order.created_at:
            dt = order.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            order_mx = dt.astimezone(MX_TZ)
            order_date_str = order_mx.strftime("%Y-%m-%d %H:%M")

        report_items.append(SalesReportItem(
            order_id=order.order_id,
            customer_name=customer.full_name if customer else "N/A",
            customer_email=customer.email if customer else "N/A",
            order_date=order_date_str,
            status=order.status.value,
            total_amount=float(order.total_amount),
            order_profit=float(order.order_profit or 0),
            items_count=items_count
        ))

    return SalesReport(
        start_date=start_date,
        end_date=end_date,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_profit=total_profit,
        orders=report_items
    )
