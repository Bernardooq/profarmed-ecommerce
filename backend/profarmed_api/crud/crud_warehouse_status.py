"""
CRUD y Gestión de Máquina de Estados, Sellos y Sincronización en Almacén (Warehouse Status & Seals) — PBAC & RBAC Dinámico:

Funciones y Operaciones:
- Avance de estados del ciclo de vida del split (`advance_split_status`).
- Generación y validación de sellos / cinchos de seguridad inviolables (`SL-YYYYMMDD-XXXX`).
- Aprobación por confianza en segundo filtro (Fast-Track / `fast_track_approve_second_filter`).
- Sincronización automática de splits y partidas tras edición de pedidos (`sync_warehouse_on_order_edit`).
- Recálculo global del estado de almacén y veredicto forense a nivel pedido (`_recalculate_order_warehouse_status`).

Máquina de Estados de Splits y Fases Operativas (PROFARMED v2.2):
1. `pending`: Split disponible en cola FIFO para toma por surtidor (`warehouse.operator`).
2. `in_progress`: Surtido activo con escaneo láser/cajas maestras/manual en 1er Filtro (Picker).
3. `ready_for_check`: Surtido completado al 100%, split lista para mesa de control y revisión (Checker).
4. `checking`: Re-escaneo y verificación de piezas en 2do Filtro (`warehouse.checker` o `warehouse.operator`).
5. `completed`: Split verificada al 100%, sellada con cincho inviolable y lista para despacho/embarque.

Permisos PBAC Asociados:
- Surtido y avance de 1er filtro: `warehouse.operator`
- Revisión y avance de 2do filtro: `warehouse.checker`, `warehouse.operator`
- Supervisión y aprobación por confianza: `warehouse.supervisor`, `warehouse.manage`, `orders.approve`
- Control total y sellado forzado: `warehouse.manage`, `warehouse.audit`, `system.admin`
"""

from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
import time
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from db.base import (
    Order, OrderItem, WarehouseSplit, WarehouseItem, 
    WarehouseContainer, WarehouseContainerItem, User
)


def advance_split_status(
    db: Session,
    split_id: UUID,
    user_id: int,
    security_seal_folio: Optional[str] = None,
    force_status: Optional[str] = None
) -> WarehouseSplit:
    """Avanzar estado del split o aplicar sello de seguridad"""
    split = db.query(WarehouseSplit).options(
        joinedload(WarehouseSplit.order),
        selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.order_item).joinedload(OrderItem.product),
        selectinload(WarehouseSplit.containers)
    ).filter(WarehouseSplit.split_id == split_id).first()

    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split '{split_id}' no encontrada"
        )

    now = datetime.now(timezone.utc)

    # 1. Regresar a surtido por discrepancia física detectada en mesa de control
    if force_status in ["in_progress", "picking"]:
        split.status = "picking"
        split.completed_at = None
        split.checking_started_at = None
        split.checker_id = None

        # Si alguna partida tiene más piezas verificadas de las que requiere el pedido,
        # resetearla a 0 para que el operador de piso la vuelva a escanear en limpio
        for f in (split.warehouse_items or []):
            it = f.order_item
            req_qty = f.required_quantity or (it.quantity if it else 0)
            tot_1st = f.picked_total_qty or 0
            if tot_1st > req_qty:
                f.picked_boxes = 0
                f.picked_box_prods = 0
                f.picked_scanned_qty = 0
                f.picked_manual_qty = 0
                f.picked_manual_reason = None
                f.picked_at = None
                f.picked_by = None
                f.status = "pending"

            tot_2nd = f.checked_total_qty or 0
            if tot_2nd > req_qty:
                f.checked_boxes = 0
                f.checked_box_prods = 0
                f.checked_scanned_qty = 0
                f.checked_manual_qty = 0
                f.checked_manual_reason = None
                f.checked_at = None
                f.checked_by = None

        _recalculate_order_warehouse_status(db, split.order)
        db.commit()
        db.refresh(split)
        return split

    # 2. Enviar a segundo filtro (checking / ready_for_check): validar que el 1er filtro cubra el 100%
    if force_status in ["ready_for_check", "checking"]:
        # Validación de Modalidad Canastas (Integridad de Máquina de Estados)
        if getattr(split, "uses_containers", False):
            from db.base import WarehouseContainer, WarehouseContainerItem
            from sqlalchemy import func
            linked_containers = db.query(WarehouseContainer).filter(
                WarehouseContainer.current_split_id == split.split_id
            ).all()
            if not linked_containers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inconsistencia de trazabilidad: El split está configurado en 'Modo Canastas' pero no tiene ninguna canasta física vinculada (0 canastas). Vincula al menos una canasta QR o cambia la modalidad a Surtido Directo antes de enviar a revisión."
                )
            linked_container_ids = [c.container_id for c in linked_containers]

            # Consulta agregada O(1) con GROUP BY para evitar N consultas en bucle
            ci_sums = dict(
                db.query(
                    WarehouseContainerItem.warehouse_item_id,
                    func.coalesce(func.sum(
                        WarehouseContainerItem.picked_scanned_qty + WarehouseContainerItem.picked_box_prods + WarehouseContainerItem.picked_manual_qty
                    ), 0)
                ).filter(
                    WarehouseContainerItem.split_id == split.split_id,
                    WarehouseContainerItem.container_id.in_(linked_container_ids)
                ).group_by(WarehouseContainerItem.warehouse_item_id).all()
            )

            for f in (split.warehouse_items or []):
                it = f.order_item
                tot = f.picked_total_qty or 0
                if tot > 0:
                    ci_tot = ci_sums.get(f.warehouse_item_id, 0)
                    if ci_tot < tot:
                        prod_name = it.product.name if it and it.product else (f.product_id or "desconocido")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Inconsistencia de trazabilidad: '{prod_name}' tiene {tot - ci_tot} pieza(s) sin canasta física activa en 'Modo Canastas'. Todos los productos deben pertenecer a una canasta válida antes de enviar a revisión."
                        )

        for f in (split.warehouse_items or []):
            it = f.order_item
            tot = f.picked_total_qty or 0
            req_qty = f.required_quantity or (it.quantity if it else 0)
            if tot < req_qty:
                prod_name = it.product.name if it and it.product else (f.product_id or "desconocido")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Incompleto: '{prod_name}' tiene {tot}/{req_qty} piezas verificadas en 1er filtro"
                )
            # Reset de conteos del 2do filtro al entrar nuevamente a revisión para asegurar conteo ciego
            f.checked_boxes = 0
            f.checked_box_prods = 0
            f.checked_scanned_qty = 0
            f.checked_manual_qty = 0
            f.checked_manual_reason = None
            f.checked_at = None
            f.checked_by = None

        split.status = force_status
        if not split.picking_completed_at:
            split.picking_completed_at = now
        split.completed_at = None
        split.checking_started_at = None
        _recalculate_order_warehouse_status(db, split.order)
        db.commit()
        db.refresh(split)
        return split

    # 3. Cierre definitivo y sellado inviolable
    is_sealing_from_checker = (split.status in ["ready_for_check", "checking"]) or (force_status in ["audited", "checking"])

    # Validación de Modalidad Canastas al sellar
    if getattr(split, "uses_containers", False):
        from db.base import WarehouseContainer, WarehouseContainerItem
        from sqlalchemy import func
        linked_containers = db.query(WarehouseContainer).filter(
            WarehouseContainer.current_split_id == split.split_id
        ).all()
        if not linked_containers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inconsistencia de modalidad: El split está configurado en 'Modo Canastas' pero no tiene ninguna canasta física vinculada (0 canastas). Vincula al menos una canasta QR o cambia la modalidad a Surtido Directo antes de sellar."
            )
        linked_container_ids = [c.container_id for c in linked_containers]

        # Consulta agregada O(1) con GROUP BY para evitar N consultas en bucle
        sum_expr = (
            (WarehouseContainerItem.checked_scanned_qty + WarehouseContainerItem.checked_box_prods + WarehouseContainerItem.checked_manual_qty) if is_sealing_from_checker else
            (WarehouseContainerItem.picked_scanned_qty + WarehouseContainerItem.picked_box_prods + WarehouseContainerItem.picked_manual_qty)
        )
        ci_sums = dict(
            db.query(
                WarehouseContainerItem.warehouse_item_id,
                func.coalesce(func.sum(sum_expr), 0)
            ).filter(
                WarehouseContainerItem.split_id == split.split_id,
                WarehouseContainerItem.container_id.in_(linked_container_ids)
            ).group_by(WarehouseContainerItem.warehouse_item_id).all()
        )

        for f in (split.warehouse_items or []):
            it = f.order_item
            tot = (f.checked_total_qty if is_sealing_from_checker else f.picked_total_qty) or 0
            if tot > 0:
                ci_tot = ci_sums.get(f.warehouse_item_id, 0)
                if ci_tot < tot:
                    prod_name = it.product.name if it and it.product else (f.product_id or "desconocido")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Inconsistencia de trazabilidad: '{prod_name}' tiene {tot - ci_tot} pieza(s) sin canasta física activa en 'Modo Canastas'. Todos los productos deben pertenecer a una canasta válida antes de sellar."
                    )

    if is_sealing_from_checker:
        for f in (split.warehouse_items or []):
            it = f.order_item
            tot = f.checked_total_qty or 0
            req_qty = f.required_quantity or (it.quantity if it else 0)
            if tot < req_qty:
                prod_name = it.product.name if it and it.product else (f.product_id or "desconocido")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Incompleto en 2do filtro: '{prod_name}' tiene {tot}/{req_qty} piezas revisadas"
                )
        if not split.checker_id:
            split.checker_id = user_id
        if not split.completed_at:
            split.completed_at = now
    else:
        for f in (split.warehouse_items or []):
            it = f.order_item
            tot = f.picked_total_qty or 0
            req_qty = f.required_quantity or (it.quantity if it else 0)
            if tot < req_qty:
                prod_name = it.product.name if it and it.product else (f.product_id or "desconocido")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Incompleto: '{prod_name}' tiene {tot}/{req_qty} piezas verificadas"
                )
        if not split.picking_completed_at:
            split.picking_completed_at = now
        if not split.completed_at:
            split.completed_at = now

    if security_seal_folio in ["Sin sello", "SIN_SELLO", "none", "NONE"]:
        split.security_seal_folio = None
    elif security_seal_folio:
        split.security_seal_folio = security_seal_folio.strip()
    else:
        now_ts = int(time.time() * 1000) % 1000000
        split.security_seal_folio = f"SL-{split.order_id}-{split.split_number}-{now_ts:06d}"

    split.status = "completed"
    if not split.completed_at:
        split.completed_at = now

    for f in (split.warehouse_items or []):
        f.status = "completed"

    # Liberar canastas físicas vinculadas a este split al completarse
    from db.base import WarehouseContainer
    containers_to_release = db.query(WarehouseContainer).filter(
        WarehouseContainer.current_split_id == split.split_id
    ).all()
    for c in containers_to_release:
        c.status = "available"
        c.current_split_id = None
        c.current_user_id = None
        c.updated_at = now
    split.active_container_id = None

    _recalculate_order_warehouse_status(db, split.order)
    db.commit()
    db.refresh(split)
    return split


def fast_track_approve_second_filter(
    db: Session,
    split_id: UUID,
    user_id: int
) -> WarehouseSplit:
    """Aprobación rápida de segundo filtro confiando en el surtido previo del 1er filtro"""
    split = db.query(WarehouseSplit).options(
        joinedload(WarehouseSplit.order),
        selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.order_item)
    ).filter(WarehouseSplit.split_id == split_id).first()

    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split '{split_id}' no encontrada"
        )

    if split.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El split ya se encuentra completada y sellada"
        )

    now = datetime.now(timezone.utc)
    if not split.checker_id:
        split.checker_id = user_id
    if not split.checking_started_at:
        split.checking_started_at = now
    split.status = "checking"

    for f in (split.warehouse_items or []):
        f.checked_boxes = f.picked_boxes or 0
        f.checked_scanned_qty = f.picked_scanned_qty or 0
        f.checked_box_prods = f.picked_box_prods or 0
        f.checked_manual_qty = f.picked_manual_qty or 0
        f.checked_by = user_id
        if f.picked_manual_reason:
            f.checked_manual_reason = f"Validado por Confianza ({f.picked_manual_reason})"
        else:
            f.checked_manual_reason = "Validado por Confianza de Surtido"
        f.checked_at = now
        f.status = "completed"

    ci_records = db.query(WarehouseContainerItem).filter(WarehouseContainerItem.split_id == split_id).all()
    for ci in ci_records:
        ci.checked_scanned_qty = ci.picked_scanned_qty or 0
        ci.checked_boxes = ci.picked_boxes or 0
        ci.checked_box_prods = ci.picked_box_prods or 0
        ci.checked_manual_qty = ci.picked_manual_qty or 0
        ci.updated_at = now

    _recalculate_order_warehouse_status(db, split.order)
    db.commit()
    db.refresh(split)
    return split


def sync_warehouse_on_order_edit(
    db: Session,
    order: Order,
    deleted_item_ids: List[UUID],
    new_items: List[OrderItem]
):
    """Sincronizar splits y partidas cuando un pedido en bodega es editado"""
    if not order.sent_to_warehouse:
        return

    # 1. Eliminación de partidas canceladas/removidas
    if deleted_item_ids:
        # Borrar registros en warehouse_items
        db.query(WarehouseItem).filter(WarehouseItem.order_item_id.in_(deleted_item_ids)).delete(synchronize_session=False)

        for b in list(order.splits or []):
            remaining_items = db.query(WarehouseItem).filter(WarehouseItem.split_id == b.split_id).count()
            if remaining_items <= 0:
                # Liberar canastas físicas vinculadas a este split antes de borrarlo
                db.query(WarehouseContainer).filter(WarehouseContainer.current_split_id == b.split_id).update({
                    WarehouseContainer.status: "available",
                    WarehouseContainer.current_split_id: None,
                    WarehouseContainer.current_user_id: None
                }, synchronize_session=False)

                db.query(WarehouseContainerItem).filter(WarehouseContainerItem.split_id == b.split_id).delete(synchronize_session=False)
                db.delete(b)
                order.total_splits = max(1, (order.total_splits or 1) - 1)

    # 2. Inserción de nuevas partidas
    if new_items:
        open_split = next((b for b in (order.splits or []) if b.status in ["pending", "picking", "in_progress"]), None)

        if open_split:
            for it in new_items:
                wi = WarehouseItem(
                    split_id=open_split.split_id,
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
        else:
            new_split_num = (order.total_splits or 0) + 1
            order.total_splits = new_split_num
            extra_split = WarehouseSplit(
                order_id=order.order_id,
                split_number=new_split_num,
                total_splits=new_split_num,
                status="pending",
                split_code=f"{order.order_id}-{new_split_num}"
            )
            db.add(extra_split)
            db.flush()

            for it in new_items:
                wi = WarehouseItem(
                    split_id=extra_split.split_id,
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

    # 3. Ajuste de cantidades requeridas y reseteo por discrepancia
    for b in (order.splits or []):
        for f in (b.warehouse_items or []):
            it = f.order_item
            req_qty = it.quantity if it else (f.required_quantity or 0)
            f.required_quantity = req_qty
            tot_1st = f.picked_total_qty or 0

            # Si la cantidad requerida disminuyó y lo verificado supera el requerimiento, resetear
            if tot_1st > req_qty:
                f.picked_boxes = 0
                f.picked_box_prods = 0
                f.picked_scanned_qty = 0
                f.picked_manual_qty = 0
                f.picked_manual_reason = None
                f.picked_at = None
                f.picked_by = None
                f.status = "pending"

            tot_2nd = f.checked_total_qty or 0
            if tot_2nd > req_qty:
                f.checked_boxes = 0
                f.checked_box_prods = 0
                f.checked_scanned_qty = 0
                f.checked_manual_qty = 0
                f.checked_manual_reason = None
                f.checked_at = None
                f.checked_by = None

            # Actualizar estatus de la partida física
            new_tot_1st = f.picked_total_qty or 0
            if new_tot_1st >= req_qty and req_qty > 0:
                f.status = "completed"
            elif new_tot_1st > 0:
                f.status = "partial"
            else:
                f.status = "pending"

            if f.status != "completed" and b.status == "completed":
                b.status = "picking"
                b.completed_at = None

    _recalculate_order_warehouse_status(db, order)


def _recalculate_order_warehouse_status(db: Session, order: Order):
    """Recalcular warehouse_status y audit_verdict de una orden según sus splits y partidas granulares"""
    if not order or not order.sent_to_warehouse:
        return

    splits = order.splits or []
    if not splits:
        order.warehouse_status = "pending"
        order.audit_verdict = "clean"
        return

    total = len(splits)
    completed_count = sum(1 for b in splits if b.status == "completed")
    ready_or_checking_count = sum(1 for b in splits if b.status in ["ready_for_check", "checking"])
    has_pending_or_in_progress = any(b.status in ["pending", "picking", "in_progress"] for b in splits)

    if completed_count == total:
        order.warehouse_status = "completed"
    elif ready_or_checking_count > 0 and not has_pending_or_in_progress:
        order.warehouse_status = "checking"
    elif completed_count > 0 or ready_or_checking_count > 0 or any(b.status in ["picking", "in_progress"] for b in splits):
        order.warehouse_status = "in_progress"
    else:
        order.warehouse_status = "pending"

    # Evaluación pericial forense del veredicto de auditoría (audit_verdict)
    has_incomplete = False
    has_inconsistency = False
    has_confidence_approval = False

    for b in splits:
        for ful in (b.warehouse_items or []):
            req_qty = ful.required_quantity or (ful.order_item.quantity if ful.order_item else 0)
            tot_1st = ful.picked_total_qty or 0
            tot_2nd = ful.checked_total_qty or 0

            # Si el pedido está marcado como completado y una partida no cubre la cantidad
            if order.warehouse_status == "completed" and (tot_1st < req_qty or (tot_2nd < req_qty and tot_2nd > 0)):
                has_incomplete = True
            elif order.warehouse_status == "completed" and tot_1st == 0:
                has_incomplete = True

            # Si el segundo filtro tiene validación por confianza
            is_confidence_val = bool(ful.checked_manual_reason and "Confianza" in ful.checked_manual_reason)
            if is_confidence_val:
                has_confidence_approval = True

            # Si el segundo filtro difiere del primer filtro
            if tot_2nd > 0 and not is_confidence_val:
                diff_totals = (tot_1st != tot_2nd)
                diff_boxes = ((ful.picked_boxes or 0) != (ful.checked_boxes or 0))
                diff_box_prods = ((ful.picked_box_prods or 0) != (ful.checked_box_prods or 0))
                diff_scanned = ((ful.picked_scanned_qty or 0) != (ful.checked_scanned_qty or 0))
                diff_manual = ((ful.picked_manual_qty or 0) != (ful.checked_manual_qty or 0))

                if diff_totals or diff_boxes or diff_box_prods or diff_scanned or diff_manual:
                    has_inconsistency = True

    if has_incomplete and has_inconsistency:
        order.audit_verdict = "incomplete_and_inconsistent"
    elif has_incomplete:
        order.audit_verdict = "incomplete"
    elif has_inconsistency:
        order.audit_verdict = "inconsistent"
    elif has_confidence_approval:
        order.audit_verdict = "clean_confidence"
    else:
        order.audit_verdict = "clean"
