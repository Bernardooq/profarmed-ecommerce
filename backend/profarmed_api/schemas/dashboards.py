"""
Schemas para Dashboards y Reportes

Define la estructura de datos para:
- Dashboard de administrador (estadisticas generales)
- Reporte de ventas (con desglose de pedidos)
"""

from pydantic import BaseModel, Field
from typing import List, Optional



class RoleBreakdownItem(BaseModel):
    role_id: int
    name: str
    slug: str
    count: int


class DashboardFinanceStats(BaseModel):
    """Métricas financieras del negocio (anuales y acumuladas)"""
    total_revenue: float
    total_profit: float = 0.0
    current_year: int


class DashboardOrderStats(BaseModel):
    """Estadísticas operativas de órdenes y embudo de estados"""
    pending_orders: int
    approved_orders: int = 0
    shipped_orders: int = 0
    delivered_orders: int = 0
    cancelled_orders: int = 0
    total_orders: int = 0
    assigned_groups_count: int = 0


class DashboardUsersCustomersStats(BaseModel):
    """Métricas de personal interno y clientes registrados"""
    total_customers: int
    total_users: int
    roles_breakdown: List[RoleBreakdownItem] = []


class DashboardInventoryStats(BaseModel):
    """Métricas de catálogo e inventario físico"""
    total_products: int
    low_stock_count: int
    out_of_stock_count: int


class DashboardStats(BaseModel):
    """
    Estadísticas generales para el dashboard de administrador
    
    Muestra métricas clave del negocio en tiempo real con desglose dinámico de roles (PBAC/RBAC).
    """
    total_users: int  # Total de usuarios internos activos
    total_customers: int  # Total de clientes registrados activos
    total_products: int  # Total de productos en catalogo
    total_orders: int  # Total de pedidos historicos
    delivered_orders: int  # Total de pedidos entregados (delivered)
    shipped_orders: int  # Total de pedidos enviados (shipped)
    approved_orders: int  # Total de pedidos aprobados (approved)
    cancelled_orders: int  # Total de pedidos cancelados (cancelled)
    pending_orders: int  # Pedidos pendientes de asignacion
    total_revenue: float  # Ingresos totales (pedidos completados)
    total_profit: float = 0.0  # Ganancia total estimada por markup
    low_stock_count: int  # Productos con bajo inventario (< 10 unidades)
    out_of_stock_count: int  # Productos sin stock (0 unidades)
    roles_breakdown: List[RoleBreakdownItem] = Field(default_factory=list, description="Conteo dinamico por cada rol configurado")


class OperationalDashboardStats(BaseModel):
    """
    Estadísticas para el dashboard operativo basadas en capacidades dinámicas (PBAC)
    
    Muestra métricas relevantes para grupos de venta o asignaciones operativas.
    """
    pending_orders: int  # Pedidos pendientes de validación
    approved_orders: int = 0  # Pedidos aprobados
    shipped_orders: int = 0  # Pedidos enviados
    delivered_orders: int = 0  # Pedidos entregados
    cancelled_orders: int = 0  # Pedidos cancelados
    total_products: int  # Total de productos en catálogo
    low_stock_count: int  # Productos con bajo inventario (< 10 unidades)
    out_of_stock_count: int  # Productos sin stock (0 unidades)
    assigned_groups_count: int = 0  # Cantidad de grupos asignados al usuario


class SalesReportItem(BaseModel):
    """
    Item individual en el reporte de ventas
    
    Representa un pedido con informacion resumida del cliente.
    """
    order_id: int  # ID del pedido (BIGSERIAL)
    customer_name: str  # Nombre completo del cliente
    customer_email: str  # Email del cliente
    order_date: str  # Fecha del pedido (formato: "YYYY-MM-DD HH:MM")
    status: str  # Estado actual del pedido
    total_amount: float  # Monto total del pedido
    order_profit: float = 0.0  # Ganancia del pedido por markup
    items_count: int  # Numero de productos en el pedido


class SalesReport(BaseModel):
    """
    Reporte completo de ventas con totales y desglose
    
    Incluye estadisticas agregadas y lista detallada de pedidos.
    """
    start_date: str  # Fecha inicial del reporte (formato: "YYYY-MM-DD")
    end_date: str  # Fecha final del reporte (formato: "YYYY-MM-DD")
    total_orders: int  # Numero total de pedidos en el periodo
    total_revenue: float  # Ingresos totales en el periodo
    total_profit: float = 0.0  # Ganancia total en el periodo
    orders: List[SalesReportItem]  # Lista de pedidos con detalles

class TopProductYearlyItem(BaseModel):
    product_id: str
    name: str
    codebar: Optional[str] = None
    orders_count: int
    units_sold: int
    total_revenue: float
    total_profit: float


class TopProductsYearlyResponse(BaseModel):
    year: int
    sort_by: str
    items: List[TopProductYearlyItem]
