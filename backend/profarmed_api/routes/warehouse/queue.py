"""
Routes para Cola FIFO, Historial, Métricas y Operadores de Bodega (Queue & Stats)

Controla la bandeja de entrada y visibilidad global de las órdenes en bodega:
- Cola FIFO con paginación lookahead y filtros multidimensionales (estado, asignación, etapa, veredicto).
- Historial histórico de órdenes procesadas y cerradas en almacén.
- Métricas operativas en tiempo real (tiempos promedio, pedidos pendientes, en surtido y completados).
- Directorio filtrado de personal operativo disponible para asignación (Surtidores y Revisores).

ENDPOINTS:
- GET /queue - Cola FIFO operativa de pedidos listos para surtir (requiere 'warehouse.view')
- GET /orders/history - Historial de pedidos procesados en almacén (requiere 'warehouse.view')
- GET /stats - Métricas acumuladas y volumetría de bodega (requiere 'warehouse.view')
- GET /operators - Directorio de usuarios con permisos de almacén (requiere 'warehouse.supervisor' o 'warehouse.view')

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.base import User
from dependencies import get_db, require_permission
from crud.crud_user import get_users
from schemas.user import User as UserSchema
from crud.crud_warehouse import (
    get_warehouse_queue,
    get_warehouse_orders_history,
    get_warehouse_stats,
)
from schemas.warehouse import (
    WarehouseQueuePaginatedResponse,
    WarehouseStatsResponse,
)

router = APIRouter()


# ============================================================================
# COLA FIFO OPERATIVA E HISTORIAL DE PEDIDOS
# ============================================================================

""" GET /queue - Cola FIFO de pedidos en bodega con lookahead pagination y filtros """
@router.get(
    "/queue",
    response_model=WarehouseQueuePaginatedResponse
)
def get_warehouse_queue_route(
    skip: int = Query(0, ge=0, description="Desplazamiento de registros para paginación"),
    limit: int = Query(20, ge=1, le=200, description="Cantidad máxima de pedidos a devolver"),
    warehouse_status: Optional[str] = Query(None, description="Filtrar por status interno (pending, picking, checking, completed)"),
    assigned_to_me: Optional[bool] = Query(None, description="Filtrar pedidos donde el usuario actual sea picker o checker"),
    search: Optional[str] = Query(None, description="Término de búsqueda libre (ID pedido, cliente, folio)"),
    audit_verdict: Optional[str] = Query(None, description="Filtrar por veredicto forense (clean, discrepancy, etc.)"),
    stage: Optional[str] = Query(None, description="Filtrar por etapa de fulfillment"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "system.admin"))
):
    """
    Obtiene la lista priorizada de pedidos en cola de surtido de almacén.
    
    Características de rendimiento:
    - Paginación Lookahead O(1) que evita `COUNT(*)` masivos en tablas de millones de filas.
    - Soporta scoping por rol: operarios pueden filtrar únicamente sus lotes asignados.
    - Devuelve indicadores agregados de avance por cada pedido y lote.
    """
    orders, lookahead_pages = get_warehouse_queue(
        db=db,
        skip=skip,
        limit=limit,
        warehouse_status=warehouse_status,
        assigned_to_me=assigned_to_me,
        search=search,
        audit_verdict=audit_verdict,
        stage=stage,
        current_user=current_user
    )
    return {
        "orders": orders,
        "skip": skip,
        "limit": limit,
        "lookahead_pages": lookahead_pages
    }


""" GET /orders/history - Historial de pedidos finalizados y despachados en almacén """
@router.get(
    "/orders/history",
    response_model=WarehouseQueuePaginatedResponse
)
def get_warehouse_history_route(
    skip: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    limit: int = Query(20, ge=1, le=200, description="Límite por página"),
    warehouse_status: Optional[str] = Query(None, description="Filtrar por estado histórico"),
    assigned_to_me: Optional[bool] = Query(None, description="Solo pedidos donde participó el usuario"),
    search: Optional[str] = Query(None, description="Búsqueda por folio o cliente"),
    audit_verdict: Optional[str] = Query(None, description="Filtrar por resultado de auditoría"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "system.admin"))
):
    """
    Consulta el histórico de pedidos completados o archivados en almacén.
    
    Incluye tiempos de ciclo (recolección, revisión y sellado), colaboradores
    responsables de cada etapa y folios de sellos de seguridad asignados.
    """
    orders, lookahead_pages = get_warehouse_orders_history(
        db=db,
        skip=skip,
        limit=limit,
        warehouse_status=warehouse_status,
        assigned_to_me=assigned_to_me,
        search=search,
        audit_verdict=audit_verdict,
        current_user=current_user
    )
    return {
        "orders": orders,
        "skip": skip,
        "limit": limit,
        "lookahead_pages": lookahead_pages
    }


# ============================================================================
# MÉTRICAS Y DIRECTORIO DE PERSONAL OPERATIVO
# ============================================================================

""" GET /stats - Métricas acumuladas y volumetría de rendimiento en almacén """
@router.get(
    "/stats",
    response_model=WarehouseStatsResponse
)
def get_warehouse_stats_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "system.admin"))
):
    """
    Calcula los KPIs operacionales de la bodega en tiempo real:
    - Total de pedidos en cola, en proceso de surtido, en segundo filtro y terminados hoy.
    - Promedio de tiempo de surtido por split.
    - Nivel de discrepancias detectadas entre primer y segundo filtro.
    """
    return get_warehouse_stats(db=db, current_user=current_user)


""" GET /operators - Directorio de colaboradores con permisos de almacén para asignación """
@router.get(
    "/operators",
    response_model=List[UserSchema]
)
def get_warehouse_operators_route(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Búsqueda por nombre o username"),
    role_type: Optional[str] = Query(None, description="Tipo de operador: 'picker' o 'checker'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.supervisor", "warehouse.view", "warehouse.manage", "system.admin"))
):
    """
    Lista el personal operativo disponible para asignarse como Surtidores (1er Filtro)
    o Revisores (2do Filtro).
    
    Filtra automáticamente excluyendo administradores y usuarios inactivos, garantizando
    que solo se devuelvan colaboradores con las capacidades técnicas adecuadas.
    """
    perm_codes = (
        "warehouse.checker" if role_type == "checker"
        else ("warehouse.operator" if role_type == "picker"
        else ["warehouse.operator", "warehouse.checker"])
    )
    return get_users(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        permission_code=perm_codes,
        exclude_admins=True
    )
