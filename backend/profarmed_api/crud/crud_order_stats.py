"""
CRUD y Sincronización de Estadísticas Desnormalizadas de Pedidos (OrderStats):

Funciones y Operaciones:
- Incremento y decremento atómico de contadores de estados de pedidos en tiempo real.
- Sincronización en creación de pedido (`sync_order_on_create`).
- Sincronización en cambio de estado (`sync_order_on_status_change`).
- Sincronización en eliminación física de pedido (`sync_order_on_delete`).
- Sincronización al transferir clientes entre grupos de ventas (`sync_customer_group_change`).
- Limpieza al eliminar un grupo de ventas (`sync_group_delete`).

Propósito y Arquitectura de Rendimiento:
1. Consultas O(1) en Dashboard:
   - Evita consultas costosas con `COUNT()` sobre millones de registros en la tabla `orders`.
   - La tabla `order_stats` almacena los totales precálculados por cada combinación de `(group_id, status)`.
2. Segmentación de Ámbito (PBAC / RBAC Dinámico):
   - `group_id = 0`: Contadores globales consolidados de toda la plataforma (consumido por superadministradores y usuarios con permisos de reportes globales `reports.view`).
   - `group_id > 0`: Contadores específicos por cada grupo de ventas (consumido por colaboradores internos asignados a ese grupo comercial, independientemente de su rol dinámico).
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.base import OrderStat, CustomerInfo, Order

"""Incrementa las estadísticas globales y de grupo de ventas correspondientes al crearse un pedido"""
def sync_order_on_create(db: Session, order: Order):
    status = order.status.value if hasattr(order.status, 'value') else order.status
    group_id = _get_customer_group(db, order.customer_id)
    _upsert(db, 0, status, 1)
    if group_id is not None:
        _upsert(db, group_id, status, 1)
    db.commit()

"""Actualiza los contadores de estado correspondientes cuando un pedido cambia de estado"""
def sync_order_on_status_change(db: Session, order_id: int, old_status: str, new_status: str, customer_id: int):
    if old_status == new_status:
        return
    _decrement(db, 0, old_status)
    _upsert(db, 0, new_status, 1)
    group_id = _get_customer_group(db, customer_id)
    if group_id is not None:
        _decrement(db, group_id, old_status)
        _upsert(db, group_id, new_status, 1)
    db.commit()

"""Decrementa las estadísticas correspondientes si un pedido es eliminado del sistema"""
def sync_order_on_delete(db: Session, order_status: str, customer_id: int):
    _decrement(db, 0, order_status)
    group_id = _get_customer_group(db, customer_id)
    if group_id is not None:
        _decrement(db, group_id, order_status)
    db.commit()

"""Reubica los contadores de pedidos del cliente al transferirse de un grupo de ventas a otro"""
def sync_customer_group_change(db: Session, customer_id: int, old_group_id: Optional[int], new_group_id: Optional[int]):
    orders_by_status = db.query(Order.status, func.count(Order.order_id).label('cnt'))\
        .filter(Order.customer_id == customer_id)\
        .group_by(Order.status).all()

    for row in orders_by_status:
        status = row.status.value if hasattr(row.status, 'value') else row.status
        cnt = row.cnt
        if old_group_id is not None:
            _decrement_by(db, old_group_id, status, cnt)
        if new_group_id is not None:
            _upsert(db, new_group_id, status, cnt)
    db.commit()

"""Elimina todas las estadísticas registradas para un grupo de ventas eliminado"""
def sync_group_delete(db: Session, sales_group_id: int):
    db.query(OrderStat).filter(OrderStat.sales_group_id == sales_group_id).delete()
    db.commit()

"""Obtiene el ID del grupo de ventas asociado al cliente"""
def _get_customer_group(db: Session, customer_id: int) -> Optional[int]:
    ci = db.query(CustomerInfo.sales_group_id).filter(CustomerInfo.customer_id == customer_id).first()
    return ci[0] if ci else None

"""Inserta o incrementa un contador de estado para un grupo de ventas"""
def _upsert(db: Session, group_id: int, status: str, amount: int):
    row = db.query(OrderStat).filter(
        OrderStat.sales_group_id == group_id,
        OrderStat.status == status
    ).first()
    if row:
        row.count += amount
    else:
        db.add(OrderStat(sales_group_id=group_id, status=status, count=amount))
    db.flush()

"""Decrementa en uno un contador de estado para un grupo de ventas"""
def _decrement(db: Session, group_id: int, status: str):
    _decrement_by(db, group_id, status, 1)

"""Decrementa en una cantidad específica un contador de estado para un grupo de ventas"""
def _decrement_by(db: Session, group_id: int, status: str, amount: int):
    row = db.query(OrderStat).filter(
        OrderStat.sales_group_id == group_id,
        OrderStat.status == status
    ).first()
    if row:
        row.count = max(row.count - amount, 0)
    db.flush()
