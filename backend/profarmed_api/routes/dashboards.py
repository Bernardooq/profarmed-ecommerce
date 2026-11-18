"""
Routes para Dashboards y Reportes (Dashboards)

Visualización de métricas de rendimiento del negocio y generación de informes de ventas históricos.

ESTADÍSTICAS (DASHBOARDS):
- GET /dashboard - Obtener estadísticas globales de ventas, productos y clientes (requiere 'reports.view')
- GET /dashboard/operational - Obtener estadísticas operativas filtradas según grupos asignados (requiere 'orders.view')
- GET /dashboard/top-products - Obtener productos top por año en O(1) (requiere 'reports.view', 'catalog.prices' para ver ganancias)

REPORTES DE VENTAS:
- GET /reports/sales - Generar reporte detallado de ventas por rango de fechas (requiere 'reports.sales')

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from dependencies import get_db, require_permission, get_current_user
from db.base import User
from schemas.dashboards import (
    DashboardStats,
    SalesReport,
    OperationalDashboardStats,
    TopProductsYearlyResponse,
    DashboardFinanceStats,
    DashboardOrderStats,
    DashboardUsersCustomersStats,
    DashboardInventoryStats
)
from crud.crud_dashboard import (
    get_admin_dashboard_stats,
    get_sales_report,
    get_operational_dashboard_stats,
    get_dashboard_finance_stats,
    get_dashboard_order_stats,
    get_dashboard_users_customers_stats,
    get_dashboard_inventory_stats
)
from crud.crud_product_yearly_stats import get_top_products_yearly

router = APIRouter()


# ============================================================================
# ENDPOINTS DESACOPLADOS POR CAPACIDADES PBAC
# ============================================================================

""" GET /dashboard/finance - Métricas financieras anuales y de ganancia (exclusivo financiero/admin) """
@router.get("/dashboard/finance", response_model=DashboardFinanceStats)
def get_dashboard_finance_stats_route(
    current_user: User = Depends(require_permission("reports.financial")),
    db: Session = Depends(get_db)
):
    return get_dashboard_finance_stats(db)


""" GET /dashboard/orders - Embudo operativo de pedidos (global para admin, acotado por grupos para campo) """
@router.get("/dashboard/orders", response_model=DashboardOrderStats)
def get_dashboard_order_stats_route(
    sales_group_id: Optional[int] = Query(None, description="Filtrar por grupo de ventas específico"),
    current_user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db)
):
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and current_user.has_permission("system.admin")
    can_orders = has_admin or (callable(has_perm) and (
        current_user.has_permission("orders.view") or 
        current_user.has_permission("orders.group_view") or 
        current_user.has_permission("orders.view_all")
    ))
    if not can_orders:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No cuenta con permisos de pedidos para consultar estadísticas."
        )
    return get_dashboard_order_stats(db, current_user, sales_group_id=sales_group_id)


""" GET /dashboard/users-customers - Métricas de clientes registrados y desglose de roles de usuario """
@router.get("/dashboard/users-customers", response_model=DashboardUsersCustomersStats)
def get_dashboard_users_customers_stats_route(
    current_user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db)
):
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and current_user.has_permission("system.admin")
    can_users = has_admin or (callable(has_perm) and current_user.has_permission("users.view"))
    can_customers = has_admin or (callable(has_perm) and (
        current_user.has_permission("customers.view") or current_user.has_permission("customers.view_all")
    ))
    if not can_users and not can_customers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No cuenta con permisos para consultar estadísticas de personal ni clientes."
        )
    return get_dashboard_users_customers_stats(db, current_user=current_user)


""" GET /dashboard/inventory - Salud de catálogo e inventario (total, bajo stock, agotados) """
@router.get("/dashboard/inventory", response_model=DashboardInventoryStats)
def get_dashboard_inventory_stats_route(
    current_user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db)
):
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and current_user.has_permission("system.admin")
    can_catalog = has_admin or (callable(has_perm) and (
        current_user.has_permission("catalog.view") or current_user.has_permission("products.stock")
    ))
    if not can_catalog:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No cuenta con permisos de catálogo para consultar estadísticas de inventario."
        )
    return get_dashboard_inventory_stats(db)


# ============================================================================
# ENDPOINTS AGREGADORES Y COMPATIBILIDAD
# ============================================================================

""" GET /dashboard - Obtener estadísticas globales consolidadas del negocio """
@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db)
):
    return get_admin_dashboard_stats(db, current_user=current_user)


""" GET /dashboard/operational - Obtener estadísticas operativas de sus grupos asignados """
@router.get("/dashboard/operational", response_model=OperationalDashboardStats)
def get_operational_dashboard_stats_route(
    sales_group_id: Optional[int] = Query(None, description="Filtrar por grupo de ventas específico"),
    current_user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db)
):
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and current_user.has_permission("system.admin")
    can_orders = has_admin or (callable(has_perm) and (
        current_user.has_permission("orders.view") or 
        current_user.has_permission("orders.group_view") or 
        current_user.has_permission("orders.view_all") or
        current_user.has_permission("groups.view")
    ))
    if not can_orders:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No cuenta con permisos para consultar estadísticas operativas."
        )
    return get_operational_dashboard_stats(db, current_user, sales_group_id=sales_group_id)

""" GET /reports/sales - Generar reporte detallado de ventas por rango de fechas """
@router.get("/reports/sales", response_model=SalesReport)
def sales_report(
    start_date: Optional[str] = Query(
        None,
        description="Fecha inicio (YYYY-MM-DD). Default: primer dia del mes actual"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Fecha fin (YYYY-MM-DD). Default: hoy"
    ),
    current_user: User = Depends(require_permission("reports.sales", "reports.financial")),
    db: Session = Depends(get_db)
):
    return get_sales_report(db, start_date, end_date)

""" GET /dashboard/top-products - Obtener productos top por año en O(1) """
@router.get("/dashboard/top-products", response_model=TopProductsYearlyResponse)
def get_top_products_dashboard_route(
    year: Optional[int] = Query(None, description="Año a consultar (default: año actual)"),
    sort_by: str = Query("orders", pattern="^(orders|units|profit|revenue)$", description="Criterio: orders, units, profit, revenue"),
    limit: int = Query(5, ge=1, le=50, description="Cantidad de productos a retornar"),
    current_user: User = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db)
):
    if not year:
        year = datetime.now().year

    # Verificar si el usuario tiene permiso para visualizar u ordenar por márgenes de utilidad (reports.financial o system.admin)
    has_financial = (
        current_user.has_permission("reports.financial") or current_user.has_permission("system.admin")
    )

    if sort_by == "profit" and not has_financial:
        sort_by = "orders"

    items = get_top_products_yearly(db, year=year, limit=limit, sort_by=sort_by)

    # Ocultar utilidad confidencial si no tiene permiso reports.financial
    if not has_financial:
        for item in items:
            item["total_profit"] = 0.0

    return TopProductsYearlyResponse(year=year, sort_by=sort_by, items=items)
