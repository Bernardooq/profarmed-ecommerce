"""
Routes para Enrutamiento y Despacho de Pedidos a Bodega (Warehouse Dispatch & Lifecycle)

Controla el ciclo de vida inicial de pedidos transferidos desde ventas hacia el piso de operaciones:
- Transferencia formal de pedidos hacia almacén con particionamiento configurable en splits.
- Control de visibilidad de detalles para operarios de piso (evita sesgo o filtrado anticipado).
- Cancelación o retiro seguro de pedidos en bodega con limpieza en cascada.

ENDPOINTS:
- POST /orders/{id}/send-to-warehouse - Enviar pedido a bodega y crear splits (requiere 'warehouse.send')
- PATCH /orders/{id}/visibility - Alternar visibilidad de partidas para operarios (requiere 'warehouse.supervisor')
- POST /orders/{id}/cancel-warehouse - Cancelar asignación en almacén y revertir a ventas (requiere 'warehouse.supervisor')

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.base import User
from dependencies import get_db, require_permission
from crud.crud_warehouse import (
    send_order_to_warehouse,
    toggle_order_warehouse_visibility,
    cancel_order_warehouse,
    get_order_warehouse_audit,
)
from schemas.warehouse import (
    WarehouseSendToWarehouseRequest,
    WarehouseToggleDetailsRequest,
    WarehouseAuditOrderResponse,
)

router = APIRouter()


# ============================================================================
# DESPACHO Y CONTROL DE ESTADOS DE PEDIDO EN BODEGA
# ============================================================================

""" POST /orders/{order_id}/send-to-warehouse - Enviar pedido formalmente a bodega y particionar en splits """
@router.post(
    "/orders/{order_id}/send-to-warehouse",
    response_model=WarehouseAuditOrderResponse
)
def send_order_route(
    order_id: int,
    payload: WarehouseSendToWarehouseRequest = WarehouseSendToWarehouseRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.send", "warehouse.supervisor", "warehouse.manage", "system.admin"))
):
    """
    Transfiere un pedido del estado comercial al flujo operativo de almacén.
    
    Acciones automáticas:
    - Valida que el pedido exista y se encuentre en estado apto para surtido.
    - Crea los Splits de surtido según el parámetro `total_splits` (1 a N lotes concurrentes).
    - Distribuye equitativamente las partidas del pedido entre los splits generados.
    - Registra la marca de tiempo de despacho y el ID del colaborador que autorizó el envío.
    """
    send_order_to_warehouse(
        db=db,
        order_id=order_id,
        total_splits=payload.total_splits,
        show_details=payload.show_details,
        user_id=current_user.user_id
    )
    return get_order_warehouse_audit(db=db, order_id=order_id, current_user=current_user)


""" PATCH /orders/{order_id}/visibility - Alternar visibilidad ciega de partidas para operarios """
@router.patch(
    "/orders/{order_id}/visibility",
    response_model=WarehouseAuditOrderResponse
)
def toggle_order_warehouse_visibility_route(
    order_id: int,
    payload: WarehouseToggleDetailsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.supervisor", "warehouse.manage", "system.admin"))
):
    """
    Modifica la visibilidad de los detalles del pedido en las terminales de surtido.
    
    Permite ocultar la lista completa de ítems para forzar un escaneo ciego estricto por código
    de barras, o bien habilitarla para agilizar surtidos abiertos por piezas visibles.
    """
    toggle_order_warehouse_visibility(db=db, order_id=order_id, show_details=payload.show_details)
    return get_order_warehouse_audit(db=db, order_id=order_id, current_user=current_user)


""" POST /orders/{order_id}/cancel-warehouse - Cancelar flujo de bodega y revertir a ventas """
@router.post("/orders/{order_id}/cancel-warehouse")
def cancel_order_warehouse_route(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.supervisor", "warehouse.manage", "system.admin"))
):
    """
    Cancela la orden en bodega y revierte su estado hacia el módulo de ventas.
    
    Efectos atómicos:
    - Remueve los splits asignados, ítems de fulfillment y desvincula las canastas QR físicas.
    - Restaura el flag `sent_to_warehouse = False` en la orden principal.
    - Deja registro en bitácora administrativa de la reversión.
    """
    order = cancel_order_warehouse(db=db, order_id=order_id, current_user=current_user)
    return {
        "success": True,
        "message": f"Envío a bodega del pedido #{order_id} cancelado exitosamente y registros eliminados en cascada",
        "order_id": order.order_id,
        "sent_to_warehouse": order.sent_to_warehouse
    }
