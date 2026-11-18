"""
CRUD y Gestión de Pedidos, Colas de Trabajo y Canastas QR en Almacén (Warehouse Orders, Queue & Containers) — PBAC & RBAC Dinámico:

Funciones y Operaciones:
- Enviar pedidos aprobados a bodega particionados en splits físicas (`send_order_to_warehouse`).
- Alternar modo de visualización en cola FIFO (surtido ciego vs detallado con SKU y nombres).
- Cancelar envío a bodega con borrado en cascada y liberación de canastas (`cancel_order_warehouse`).
- Eliminación limpia en cascada de registros de almacén (`cleanup_warehouse_for_order`).
- Consultar cola FIFO de trabajo paginada con Lookahead (`get_warehouse_queue`).
- Consultar historial pericial de pedidos completados en bodega (`get_warehouse_orders_history`).
- CRUD completo y ciclo de vida de canastas físicas QR (`warehouse_containers`).

Reglas de Negocio y Permisos PBAC (PROFARMED v2.2):
1. Envío a Bodega:
   - Requiere pedido en estado `approved` y permiso `orders.approve`, `warehouse.manage` o `system.admin`.
   - Se particiona la orden en splits físicas (`total_splits >= 1`) y partidas granulares `warehouse_items`.
2. Cola FIFO de Almacén:
   - Ordenada estrictamente por fecha de envío a bodega (`warehouse_sent_at ASC`).
   - Permisos requeridos: `warehouse.view`, `warehouse.operator`, `warehouse.supervisor`.
3. Surtido Ciego vs Detallado:
   - En surtido ciego (`show_details = False`), operadores de piso ven datos sensibles del cliente enmascarados para evitar desvíos o fraudes.
4. Cancelación de Surtido:
   - Colaboradores sin avance físico pueden cancelar; órdenes en curso requieren facultades de supervisión (`warehouse.manage` o `system.admin`).
   - Libera automáticamente todas las canastas QR vinculadas (retornándolas a 'available') y purga en cascada `warehouse_scan_events`, `warehouse_items` y `warehouse_splits`.
5. Canastas Físicas QR:
   - Enrolamiento único de códigos QR, vinculación transaccional a splits y liberación segura.
"""

from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_, and_

from db.base import (
    Order, OrderItem, WarehouseSplit, WarehouseItem, 
    WarehouseContainer, WarehouseContainerItem, User, OrderStatus
)
from utils.pagination import get_lookahead_pagination


# ============================================================================
# ENVÍO Y CONTROL DE PEDIDOS EN BODEGA
# ============================================================================

def send_order_to_warehouse(
    db: Session,
    order_id: int,
    total_splits: int,
    user_id: int,
    show_details: bool = False
) -> Order:
    """Enviar un pedido a surtido de bodega dividiéndolo en splits concurrentes y partidas granulares"""
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.product),
        selectinload(Order.splits).selectinload(WarehouseSplit.warehouse_items)
    ).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido #{order_id} no encontrado"
        )

    if order.sent_to_warehouse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El pedido #{order_id} ya se encuentra en bodega con estado '{order.warehouse_status}'"
        )

    if order.status != OrderStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden enviar a bodega pedidos aprobados. Estado actual: '{order.status.value}'"
        )

    items = order.items
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido no contiene partidas para surtir"
        )

    # Si existían splits o partidas previas de un envío cancelado/corrupto, limpiar primero en cascada
    if order.splits:
        cleanup_warehouse_for_order(db, order)
        db.flush()

    total_splits = max(1, min(total_splits, len(items)))

    # Ordenar por ubicación física y nombre para optimizar ruta del recolector en piso
    sorted_items = sorted(
        items,
        key=lambda it: (
            (it.product.location or "").strip().lower() if it.product else "",
            (it.product.name or "").strip().lower() if it.product else ""
        )
    )

    splits_map: Dict[int, List[OrderItem]] = {}
    for idx, item in enumerate(sorted_items):
        split_num = (idx % total_splits) + 1
        splits_map.setdefault(split_num, []).append(item)

    now = datetime.now(timezone.utc)
    for b_num in range(1, total_splits + 1):
        b_items = splits_map.get(b_num, [])
        split_code = f"{order.order_id}-{b_num}"
        split = WarehouseSplit(
            order_id=order.order_id,
            split_number=b_num,
            split_code=split_code,
            total_splits=total_splits,
            status="pending"
        )
        db.add(split)
        db.flush()

        for it in b_items:
            wi = WarehouseItem(
                split_id=split.split_id,
                order_item_id=it.order_item_id,
                product_id=it.product_id,
                required_quantity=it.quantity,
                status="pending",
                picked_scanned_qty=0,
                picked_boxes=0,
                picked_box_prods=0,
                picked_manual_qty=0,
                checked_scanned_qty=0,
                checked_boxes=0,
                checked_box_prods=0,
                checked_manual_qty=0
            )
            db.add(wi)

    order.sent_to_warehouse = True
    order.warehouse_status = "pending"
    order.total_splits = total_splits
    order.warehouse_sent_by = user_id
    order.warehouse_sent_at = now
    order.warehouse_show_details = show_details
    order.audit_verdict = "clean"

    db.commit()
    db.refresh(order)
    return order


def toggle_order_warehouse_visibility(db: Session, order_id: int, show_details: bool) -> Order:
    """Cambiar configuración de visibilidad (surtido ciego vs detallado)"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido #{order_id} no encontrado"
        )
    order.warehouse_show_details = show_details
    db.commit()
    db.refresh(order)
    return order


# ============================================================================
# CANCELACIÓN Y LIMPIEZA EN CASCADA
# ============================================================================

def cleanup_warehouse_for_order(db: Session, order: Order) -> None:
    """
    Eliminación completa en cascada de todos los registros de almacén de un pedido.
    1. Libera canastas físicas vinculadas (devolviéndolas a estado 'available').
    2. Borra eventos atómicos de escaneo (warehouse_scan_events).
    3. Borra partidas de almacén (warehouse_items).
    4. Borra los splits físicos (warehouse_splits).
    5. Restablece metadatos de almacén en la orden.
    """
    if not order:
        return

    splits = list(order.splits or db.query(WarehouseSplit).filter(WarehouseSplit.order_id == order.order_id).all())
    split_ids = [s.split_id for s in splits]

    if split_ids:
        # 1. Liberar canastas físicas QR asociadas a cualquiera de los splits
        db.query(WarehouseContainer).filter(WarehouseContainer.current_split_id.in_(split_ids)).update({
            WarehouseContainer.status: "available",
            WarehouseContainer.current_split_id: None,
            WarehouseContainer.current_user_id: None
        }, synchronize_session=False)

        # 2. Borrar partidas consolidadas en canastas de los splits
        db.query(WarehouseContainerItem).filter(WarehouseContainerItem.split_id.in_(split_ids)).delete(synchronize_session=False)

        # 3. Borrar partidas de almacén vinculadas a los splits
        db.query(WarehouseItem).filter(WarehouseItem.split_id.in_(split_ids)).delete(synchronize_session=False)

        # 4. Borrar los splits físicos
        for s in splits:
            db.delete(s)

    # 5. Resetear metadatos de bodega en la orden
    order.sent_to_warehouse = False
    order.warehouse_status = None
    order.total_splits = 1
    order.warehouse_sent_by = None
    order.warehouse_sent_at = None
    order.warehouse_show_details = False
    order.audit_verdict = "clean"


def cancel_order_warehouse(db: Session, order_id: int, current_user: Optional[User] = None) -> Order:
    """Cancelar el envío a bodega de un pedido con limpieza en cascada y liberación de canastas"""
    order = db.query(Order).options(
        selectinload(Order.splits).selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.order_item),
        selectinload(Order.splits).selectinload(WarehouseSplit.containers)
    ).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido #{order_id} no encontrado"
        )

    if not order.sent_to_warehouse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El pedido #{order_id} no está en proceso de bodega"
        )

    is_admin = bool(current_user and (
        getattr(current_user, "role_slug", None) == "admin" or
        getattr(current_user, "role", None) == "admin" or
        (hasattr(current_user, "has_permission") and (
            current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage")
        ))
    ))

    # Si ya está completado/sellado, nadie puede cancelarlo sin antes quitar sellos o estado completed
    if order.warehouse_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cancelar el pedido #{order_id}: ya ha sido completado y sellado en bodega."
        )

    # Si no es admin, validar que ningún split ni partida tenga avance
    if not is_admin:
        for b in order.splits:
            if b.status in ["picking", "in_progress", "completed", "ready_for_check", "checking"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se puede cancelar: el split #{b.split_number} tiene estado '{b.status}'. Solo un Administrador puede forzar la cancelación de pedidos en surtido."
                )
            for f in (b.warehouse_items or []):
                tot = (f.picked_box_prods or 0) + (f.picked_scanned_qty or 0) + (f.picked_manual_qty or 0)
                if tot > 0:
                    prod_id = f.product_id or (f.order_item.product_id if f.order_item else "desconocido")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No se puede cancelar: el producto '{prod_id}' ya tiene piezas verificadas. Solo un Administrador puede forzar la cancelación."
                    )

    # Limpieza total en cascada (libera canastas QR y borra items, eventos y splits)
    cleanup_warehouse_for_order(db, order)

    db.commit()
    db.refresh(order)
    return order


# ============================================================================
# CRUD Y GESTIÓN DE CANASTAS FÍSICAS QR (RE-EXPORTADOS DESDE crud_warehouse_containers)
# ============================================================================

from crud.crud_warehouse_containers import (
    list_warehouse_containers,
    get_warehouse_containers_stats,
    get_warehouse_container_by_id,
    get_warehouse_container_by_qr,
    create_warehouse_container,
    update_warehouse_container_status,
    bind_container_to_split,
    activate_container_for_split,
    release_warehouse_container,
    delete_warehouse_container,
)



# ============================================================================
# FILTRADO Y CONSULTAS DE COLA FIFO DE ALMACÉN
# ============================================================================

def _build_warehouse_search_filter(search: str, current_user: Optional[User] = None):
    """Helper para construir filtros de búsqueda multi-criterio optimizados para almacén"""
    import re
    from db.base import Customer

    search_clean = search.strip()
    if not search_clean:
        return None

    normalized = re.sub(r'^(?:#|no\.?|folio:?)\s*', '', search_clean, flags=re.IGNORECASE).strip()
    search_cond = []

    # 1. Patrón Pedido-Split / Lote (ej. "105-1", "#105-1", "105_1", "105 1")
    split_pattern = re.match(r'^(?:pedido|orden|split|lote)?\s*#?\s*(\d+)[\-_/\s]+(\d+)$', search_clean, re.IGNORECASE)
    if split_pattern:
        o_id = int(split_pattern.group(1))
        s_num = int(split_pattern.group(2))
        clean_split_code = f"{o_id}-{s_num}"
        search_cond.append(
            and_(
                Order.order_id == o_id,
                Order.splits.any(
                    or_(
                        WarehouseSplit.split_code == clean_split_code,
                        WarehouseSplit.split_number == s_num
                    )
                )
            )
        )

    # 2. Patrón de solo número de pedido (ej. "105", "#105")
    order_num_pattern = re.match(r'^(?:pedido|orden|no\.?)?\s*#?\s*(\d+)$', search_clean, re.IGNORECASE)
    if order_num_pattern:
        o_id = int(order_num_pattern.group(1))
        search_cond.append(Order.order_id == o_id)

    # 3. Búsqueda por split_code en splits (coincidencia directa o parcial)
    search_cond.append(Order.splits.any(WarehouseSplit.split_code.ilike(f"%{normalized}%")))
    if normalized != search_clean:
        search_cond.append(Order.splits.any(WarehouseSplit.split_code.ilike(f"%{search_clean}%")))

    # 4. Búsqueda por folio de cincho / sello de seguridad (ej. "SL-105-1-8492")
    search_cond.append(Order.splits.any(WarehouseSplit.security_seal_folio.ilike(f"%{normalized}%")))

    # 5. Búsqueda por código QR de canasta vinculada
    search_cond.append(Order.splits.any(WarehouseSplit.containers.any(WarehouseContainer.qr_code.ilike(f"%{normalized}%"))))

    # Restricción estricta para operadores de piso de bodega en surtido ciego:
    is_admin = bool(current_user and (
        getattr(current_user, "role_slug", None) == "admin" or
        getattr(current_user, "role", None) == "admin" or
        (hasattr(current_user, "has_permission") and (
            current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage")
        ))
    ))
    is_floor_operator = bool(current_user and hasattr(current_user, "has_permission") and (
        current_user.has_permission("warehouse.operator") or
        current_user.has_permission("warehouse.pack") or
        current_user.has_permission("warehouse.check")
    ) and not current_user.has_permission("warehouse.supervisor") and not current_user.has_permission("warehouse.manage") and not is_admin)

    if is_floor_operator:
        return or_(*search_cond) if search_cond else None

    # 6. Búsqueda por cliente (razón social, nombre o usuario)
    search_cond.append(
        Order.customer.has(
            or_(
                Customer.full_name.ilike(f"%{search_clean}%"),
                Customer.username.ilike(f"%{search_clean}%")
            )
        )
    )

    # 7. Búsqueda por usuarios del sistema asignados o involucrados:
    can_supervise = is_admin or bool(current_user and hasattr(current_user, "has_permission") and (
        current_user.has_permission("warehouse.supervisor") or
        current_user.has_permission("orders.approve") or
        current_user.has_permission("warehouse.manage") or
        current_user.has_permission("orders.view_all")
    ))
    if can_supervise:
        search_cond.append(
            Order.assigned_user.has(
                or_(
                    User.full_name.ilike(f"%{search_clean}%"),
                    User.username.ilike(f"%{search_clean}%")
                )
            )
        )

    return or_(*search_cond) if search_cond else None


def get_warehouse_queue(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    warehouse_status: Optional[str] = None,
    assigned_to_me: Optional[bool] = None,
    search: Optional[str] = None,
    audit_verdict: Optional[str] = None,
    stage: Optional[str] = None,
    current_user: Optional[User] = None
) -> Tuple[List[Any], int]:
    """Consultar cola FIFO de pedidos en bodega con paginación lookahead y filtros operativos"""
    query = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.warehouse_sender),
        joinedload(Order.assigned_user),
        selectinload(Order.splits).joinedload(WarehouseSplit.picker),
        selectinload(Order.splits).joinedload(WarehouseSplit.checker),
        selectinload(Order.splits).selectinload(WarehouseSplit.containers)
    ).filter(Order.sent_to_warehouse == True)

    is_admin = bool(current_user and (
        getattr(current_user, "role_slug", None) == "admin" or
        getattr(current_user, "role", None) == "admin" or
        (hasattr(current_user, "has_permission") and (
            current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage")
        ))
    ))
    has_warehouse_perm = bool(current_user and hasattr(current_user, "has_permission") and (
        current_user.has_permission("warehouse.view") or
        current_user.has_permission("warehouse.operator") or
        current_user.has_permission("warehouse.pack") or
        current_user.has_permission("warehouse.check") or
        current_user.has_permission("warehouse.supervisor") or
        current_user.has_permission("warehouse.manage") or
        current_user.has_permission("orders.view_all")
    ))

    if current_user and not is_admin and not has_warehouse_perm:
        from crud.crud_commercial_group import get_user_groups
        from db.base import CustomerInfo

        user_group_ids = get_user_groups(db, current_user.user_id)
        if not user_group_ids:
            query = query.filter(Order.assigned_user_id == current_user.user_id)
        else:
            query = query.join(
                CustomerInfo, Order.customer_id == CustomerInfo.customer_id
            ).filter(
                or_(
                    CustomerInfo.sales_group_id.in_(user_group_ids),
                    Order.assigned_user_id == current_user.user_id
                )
            )

    # Filtro de asignación directa
    if assigned_to_me and current_user:
        if is_admin:
            query = query.filter(
                Order.splits.any(
                    (WarehouseSplit.admin_override_by == current_user.user_id) |
                    (WarehouseSplit.picker_id == current_user.user_id) |
                    (WarehouseSplit.checker_id == current_user.user_id) |
                    WarehouseSplit.warehouse_items.any(
                        (WarehouseItem.admin_override_by == current_user.user_id) |
                        (WarehouseItem.picked_by == current_user.user_id) |
                        (WarehouseItem.checked_by == current_user.user_id)
                    )
                )
            )
        else:
            query = query.filter(
                Order.splits.any(
                    (WarehouseSplit.picker_id == current_user.user_id) |
                    (WarehouseSplit.checker_id == current_user.user_id) |
                    WarehouseSplit.warehouse_items.any(
                        (WarehouseItem.picked_by == current_user.user_id) |
                        (WarehouseItem.checked_by == current_user.user_id)
                    )
                )
            )

    # Filtro por etapa (picker vs checker)
    if stage == "picker":
        query = query.filter(
            Order.splits.any(WarehouseSplit.status.in_(["pending", "picking", "in_progress"]))
        )
    elif stage == "checker":
        query = query.filter(
            Order.splits.any(WarehouseSplit.status.in_(["ready_for_check", "checking"]))
        )

    if warehouse_status:
        if warehouse_status in ["in_progress", "in_progress_partial"]:
            query = query.filter(Order.warehouse_status.in_(["in_progress", "in_progress_partial", "in_progress_full"]))
        elif warehouse_status in ["checking", "ready_for_check"]:
            query = query.filter(Order.warehouse_status.in_(["checking", "ready_for_check"]))
        else:
            query = query.filter(Order.warehouse_status == warehouse_status)
    else:
        query = query.filter(Order.warehouse_status != "completed")

    if audit_verdict and current_user and is_admin:
        query = query.filter(Order.audit_verdict == audit_verdict)

    if search:
        search_filter = _build_warehouse_search_filter(search, current_user)
        if search_filter is not None:
            query = query.filter(search_filter)

    query = query.order_by(Order.warehouse_sent_at.asc(), Order.order_id.asc())

    res = get_lookahead_pagination(
        query=query,
        model_id_column=Order.order_id,
        skip=skip,
        limit=limit
    )
    orders = res["items"]
    lookahead_pages = res["lookahead_pages"]

    is_floor_operator = bool(current_user and not is_admin and hasattr(current_user, "has_permission") and (
        current_user.has_permission("warehouse.operator") or
        current_user.has_permission("warehouse.pack") or
        current_user.has_permission("warehouse.check")
    ) and not current_user.has_permission("warehouse.supervisor") and not current_user.has_permission("warehouse.manage"))

    if is_floor_operator:
        formatted_orders = []
        for ord_obj in orders:
            if not ord_obj.warehouse_show_details:
                masked_splits = []
                for b in ord_obj.splits:
                    is_my_split = (b.picker_id == current_user.user_id or b.checker_id == current_user.user_id)
                    containers_summary = [
                        {"container_id": c.container_id, "qr_code": c.qr_code, "status": c.status}
                        for c in (b.containers or [])
                    ]
                    masked_splits.append({
                        "split_id": b.split_id,
                        "order_id": b.order_id,
                        "split_number": b.split_number,
                        "split_code": b.split_code or f"{b.order_id}-{b.split_number}",
                        "total_splits": b.total_splits,
                        "items_count": b.items_count if is_my_split else None,
                        "status": b.status,
                        "picker_id": b.picker_id,
                        "picker_name": b.picker_name,
                        "checker_id": b.checker_id,
                        "checker_name": b.checker_name,
                        "customer_name": None,
                        "seller_name": None,
                        "security_seal_folio": b.security_seal_folio,
                        "started_at": b.started_at,
                        "completed_at": b.completed_at,
                        "containers": containers_summary,
                        "containers_count": len(containers_summary)
                    })

                formatted_orders.append(dict(
                    order_id=ord_obj.order_id,
                    customer_id=ord_obj.customer_id,
                    customer_name="[Cliente Oculto - Surtido Ciego]",
                    seller_name=None,
                    total_amount=None,
                    shipping_address_snapshot=None,
                    created_at=ord_obj.created_at,
                    warehouse_sent_at=ord_obj.warehouse_sent_at,
                    sent_to_warehouse_at=ord_obj.warehouse_sent_at,
                    warehouse_sent_by_name=ord_obj.warehouse_sent_by_name,
                    warehouse_status=ord_obj.warehouse_status,
                    warehouse_show_details=False,
                    total_splits=ord_obj.total_splits or 1,
                    completed_splits_count=ord_obj.completed_splits_count,
                    splits=masked_splits
                ))
            else:
                formatted_orders.append(ord_obj)
        return formatted_orders, lookahead_pages

    return orders, lookahead_pages


def get_warehouse_orders_history(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    warehouse_status: Optional[str] = None,
    assigned_to_me: Optional[bool] = None,
    search: Optional[str] = None,
    audit_verdict: Optional[str] = None,
    current_user: Optional[User] = None
) -> Tuple[List[Any], int]:
    """Consultar historial de pedidos completados en bodega"""
    query = db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.warehouse_sender),
        joinedload(Order.assigned_user),
        selectinload(Order.splits).joinedload(WarehouseSplit.picker),
        selectinload(Order.splits).joinedload(WarehouseSplit.checker),
        selectinload(Order.splits).selectinload(WarehouseSplit.containers)
    ).filter(
        Order.sent_to_warehouse == True
    )

    is_admin = bool(current_user and (
        getattr(current_user, "role_slug", None) == "admin" or
        getattr(current_user, "role", None) == "admin" or
        (hasattr(current_user, "has_permission") and (
            current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage")
        ))
    ))
    has_warehouse_perm = bool(current_user and hasattr(current_user, "has_permission") and (
        current_user.has_permission("warehouse.view") or
        current_user.has_permission("warehouse.operator") or
        current_user.has_permission("warehouse.pack") or
        current_user.has_permission("warehouse.check") or
        current_user.has_permission("warehouse.supervisor") or
        current_user.has_permission("warehouse.manage") or
        current_user.has_permission("orders.view_all")
    ))

    if current_user and not is_admin and not has_warehouse_perm:
        from crud.crud_commercial_group import get_user_groups
        from db.base import CustomerInfo

        user_group_ids = get_user_groups(db, current_user.user_id)
        if not user_group_ids:
            query = query.filter(Order.assigned_user_id == current_user.user_id)
        else:
            query = query.join(
                CustomerInfo, Order.customer_id == CustomerInfo.customer_id
            ).filter(
                or_(
                    CustomerInfo.sales_group_id.in_(user_group_ids),
                    Order.assigned_user_id == current_user.user_id
                )
            )

    if assigned_to_me and current_user:
        if is_admin:
            query = query.filter(
                Order.splits.any(
                    (WarehouseSplit.admin_override_by == current_user.user_id) |
                    (WarehouseSplit.picker_id == current_user.user_id) |
                    (WarehouseSplit.checker_id == current_user.user_id) |
                    WarehouseSplit.warehouse_items.any(
                        (WarehouseItem.admin_override_by == current_user.user_id) |
                        (WarehouseItem.picked_by == current_user.user_id) |
                        (WarehouseItem.checked_by == current_user.user_id)
                    )
                )
            )
        else:
            query = query.filter(
                Order.splits.any(
                    (WarehouseSplit.picker_id == current_user.user_id) |
                    (WarehouseSplit.checker_id == current_user.user_id) |
                    WarehouseSplit.warehouse_items.any(
                        (WarehouseItem.picked_by == current_user.user_id) |
                        (WarehouseItem.checked_by == current_user.user_id)
                    )
                )
            )

    if warehouse_status:
        if warehouse_status == "pending":
            query = query.filter(
                (Order.warehouse_status == "pending") |
                Order.splits.any(WarehouseSplit.status == "pending")
            )
        elif warehouse_status in ["in_progress", "in_progress_partial"]:
            query = query.filter(
                (Order.warehouse_status.in_(["in_progress", "in_progress_partial", "in_progress_full"])) |
                Order.splits.any(WarehouseSplit.status.in_(["pending", "picking", "in_progress"]))
            )
        elif warehouse_status in ["checking", "ready_for_check"]:
            query = query.filter(
                (Order.warehouse_status.in_(["checking", "ready_for_check"])) |
                Order.splits.any(WarehouseSplit.status.in_(["ready_for_check", "checking"]))
            )
        elif warehouse_status == "completed":
            query = query.filter(Order.warehouse_status == "completed")
        else:
            query = query.filter(Order.warehouse_status == warehouse_status)

    if audit_verdict and current_user and is_admin:
        query = query.filter(Order.audit_verdict == audit_verdict)

    if search:
        search_filter = _build_warehouse_search_filter(search, current_user)
        if search_filter is not None:
            query = query.filter(search_filter)

    query = query.order_by(Order.warehouse_sent_at.desc(), Order.order_id.desc())
    res = get_lookahead_pagination(
        query=query,
        model_id_column=Order.order_id,
        skip=skip,
        limit=limit
    )
    return res["items"], res["lookahead_pages"]
