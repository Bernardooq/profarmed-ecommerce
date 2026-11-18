"""
CRUD y Lógica de Escaneo Láser y Empaque en Piso de Almacén (Warehouse Floor Scanning):

Módulo especializado en:
- Escaneo atómico con pistola láser (`scan_barcode_laser`).
- Registro de empaques por cajas maestras (`add_boxes_master`).
- Validación manual con motivo de auditoría forense (`add_manual_verification`).
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from db.base import (
    OrderItem, WarehouseItem, 
    WarehouseContainer, User
)
from schemas.warehouse import WarehouseSplitItemResponse
from crud.crud_warehouse_status import _recalculate_order_warehouse_status
from crud.crud_warehouse_containers import _record_container_item
from crud.crud_warehouse_splits import _get_split_model, _validate_split_operator_permissions


def scan_barcode_laser(
    db: Session,
    split_id: UUID,
    barcode: str,
    user_id: int,
    current_user: Optional[User] = None,
    container_qr: Optional[str] = None
) -> Dict[str, Any]:
    """Registrar escaneo de código de barras desde terminal láser o activación de canasta QR"""
    barcode = barcode.strip()
    if not barcode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo de barras vacio"
        )

    split = _get_split_model(db, split_id)

    # Validación estricta de permisos server-side
    _validate_split_operator_permissions(split, current_user, user_id, "escanear con láser")

    if split.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El split ya se encuentra completada y sellada"
        )

    # =========================================================================
    # 1. ¿ES EL ESCANEO DEL CÓDIGO QR DE UNA CANASTA FÍSICA (TOTE)?
    # =========================================================================
    container = db.query(WarehouseContainer).filter(
        func.upper(WarehouseContainer.qr_code) == barcode.upper()
    ).first()

    if container:
        if container.status in ["damaged", "maintenance", "retired", "unavailable"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La canasta QR '{container.qr_code}' está en estado '{container.status}' y no puede ser utilizada para surtido."
            )
        if container.status == "in_use" and container.current_split_id and container.current_split_id != split.split_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La canasta QR '{container.qr_code}' ya está asignada a otro split activo. Libérala antes de reutilizarla."
            )

        container.status = "in_use"
        container.current_split_id = split.split_id
        container.current_user_id = user_id
        container.updated_at = datetime.now(timezone.utc)
        split.active_container_id = container.container_id
        split.uses_containers = True

        now = datetime.now(timezone.utc)
        is_checking = (split.status in ["ready_for_check", "checking"]) or (split.checker_id == user_id and split.status not in ["pending", "picking", "in_progress"])

        if is_checking:
            if not split.checker_id:
                split.checker_id = user_id
            if not split.checking_started_at:
                split.checking_started_at = now
            if split.status == "ready_for_check":
                split.status = "checking"
        else:
            if not split.picker_id:
                split.picker_id = user_id
            if split.status == "pending":
                split.status = "picking"
                split.started_at = now

        db.commit()
        db.refresh(container)
        db.refresh(split)

        from db.base import WarehouseContainerItem
        existing_in_container = db.query(WarehouseContainerItem).filter(
            WarehouseContainerItem.split_id == split.split_id,
            WarehouseContainerItem.container_id == container.container_id
        ).all()
        tot_pieces = sum((ci.picked_total_qty or 0) if not is_checking else (ci.checked_total_qty or 0) for ci in existing_in_container)

        return {
            "success": True,
            "action": "container_activated",
            "is_container": True,
            "container_id": container.container_id,
            "container_qr": container.qr_code,
            "active_container_qr": container.qr_code,
            "total_pieces_in_container": tot_pieces,
            "products_in_container": len(existing_in_container),
            "message": f"🧺 Canasta '{container.qr_code}' activada. Escanea los productos a depositar en esta canasta.",
            "split_status": split.status,
            "is_checking_mode": is_checking
        }

    # =========================================================================
    # 2. ESCANEO DE PRODUCTO: RESOLVER CANASTA ACTIVA (SOLO SI USA CANASTAS)
    # =========================================================================
    target_container_id = None
    active_qr = None
    if getattr(split, "uses_containers", False):
        target_container_id = split.active_container_id
        if not target_container_id and container_qr and container_qr.strip():
            c = db.query(WarehouseContainer).filter(
                func.upper(WarehouseContainer.qr_code) == container_qr.strip().upper()
            ).first()
            if c:
                target_container_id = c.container_id
                split.active_container_id = c.container_id
        if not target_container_id and split.containers:
            target_container_id = split.containers[-1].container_id
            split.active_container_id = target_container_id

        if not target_container_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="🧺 Modo Canastas activo: Debes escanear o vincular el código QR de una canasta física antes de escanear productos."
            )

        if target_container_id:
            active_c = db.query(WarehouseContainer).filter(WarehouseContainer.container_id == target_container_id).first()
            active_qr = active_c.qr_code if active_c else None
    else:
        # Surtido Directo: opcionalmente vincular a canasta si hay una activa o enviada, sin obligatoriedad
        target_container_id = split.active_container_id
        if not target_container_id and container_qr and container_qr.strip():
            c = db.query(WarehouseContainer).filter(
                func.upper(WarehouseContainer.qr_code) == container_qr.strip().upper()
            ).first()
            if c:
                target_container_id = c.container_id
        if target_container_id:
            active_c = db.query(WarehouseContainer).filter(WarehouseContainer.container_id == target_container_id).first()
            active_qr = active_c.qr_code if active_c else None

    matching_ful: Optional[WarehouseItem] = None
    matching_item: Optional[OrderItem] = None
    barcode_clean = barcode.lower()

    for f in (split.warehouse_items or []):
        it = f.order_item
        if it and it.product:
            code_match = (it.product.codebar or "").strip().lower() == barcode_clean
            sku_match = (it.product_id or "").strip().lower() == barcode_clean
            if code_match or sku_match:
                matching_ful = f
                matching_item = it
                break

    if matching_ful and matching_item:
        now = datetime.now(timezone.utc)
        is_checking = (split.status in ["ready_for_check", "checking"]) or (split.checker_id == user_id and split.status not in ["pending", "picking", "in_progress"])

        if is_checking:
            current_verified = (matching_ful.checked_box_prods or 0) + (matching_ful.checked_scanned_qty or 0) + (matching_ful.checked_manual_qty or 0)
            if current_verified >= matching_item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Partida completa en 2do filtro ({matching_item.quantity} piezas de '{matching_item.product.name}')"
                )

            matching_ful.checked_scanned_qty = (matching_ful.checked_scanned_qty or 0) + 1
            new_verified = (matching_ful.checked_box_prods or 0) + (matching_ful.checked_scanned_qty or 0) + (matching_ful.checked_manual_qty or 0)
            matching_ful.checked_at = now
            matching_ful.checked_by = user_id
            if target_container_id:
                matching_ful.container_id = target_container_id

            if target_container_id:
                _record_container_item(
                    db=db,
                    split=split,
                    order_item_id=matching_item.order_item_id,
                    product_id=matching_item.product_id,
                    warehouse_item_id=matching_ful.warehouse_item_id,
                    is_checking=True,
                    container_qr=active_qr,
                    scanned_qty_delta=1
                )

            if not split.checker_id:
                split.checker_id = user_id
            if not split.checking_started_at:
                split.checking_started_at = now
            if split.status == "ready_for_check":
                split.status = "checking"

            _recalculate_order_warehouse_status(db, split.order)
            db.commit()
            db.refresh(matching_ful)
            db.refresh(split)

            canasta_tag = f" [Canasta: {active_qr}]" if active_qr else ""
            tot_1st = (matching_ful.picked_box_prods or 0) + (matching_ful.picked_scanned_qty or 0) + (matching_ful.picked_manual_qty or 0)
            return {
                "success": True,
                "message": f"2do Filtro: {matching_item.product.name} ({new_verified}/{matching_item.quantity}){canasta_tag}",
                "order_item_id": matching_item.order_item_id,
                "product_id": matching_item.product_id,
                "product_name": matching_item.product.name,
                "picked_scanned_qty": matching_ful.picked_scanned_qty,
                "checked_scanned_qty": matching_ful.checked_scanned_qty,
                "picked_total_qty": tot_1st,
                "checked_total_qty": new_verified,
                "scanned_prods": matching_ful.picked_scanned_qty,
                "checker_scanned_prods": matching_ful.checked_scanned_qty,
                "total_verified": tot_1st,
                "checker_total_verified": new_verified,
                "required_quantity": matching_item.quantity,
                "remaining_quantity": max(0, matching_item.quantity - new_verified),
                "status": matching_ful.status,
                "item_status": matching_ful.status,
                "split_status": split.status,
                "is_checking_mode": True,
                "container_qr": active_qr,
                "active_container_qr": active_qr
            }

        # Modo Surtido de Piso (Picker)
        current_verified = (matching_ful.picked_box_prods or 0) + (matching_ful.picked_scanned_qty or 0) + (matching_ful.picked_manual_qty or 0)
        if current_verified >= matching_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Partida completa ({matching_item.quantity} piezas de '{matching_item.product.name}')"
            )

        matching_ful.picked_scanned_qty = (matching_ful.picked_scanned_qty or 0) + 1
        new_verified = (matching_ful.picked_box_prods or 0) + (matching_ful.picked_scanned_qty or 0) + (matching_ful.picked_manual_qty or 0)
        matching_ful.picked_by = user_id
        matching_ful.picked_at = now
        if target_container_id:
            matching_ful.container_id = target_container_id

        if target_container_id:
            _record_container_item(
                db=db,
                split=split,
                order_item_id=matching_item.order_item_id,
                product_id=matching_item.product_id,
                warehouse_item_id=matching_ful.warehouse_item_id,
                is_checking=False,
                container_qr=active_qr,
                scanned_qty_delta=1
            )

        if new_verified >= matching_item.quantity:
            matching_ful.status = "completed"
        else:
            matching_ful.status = "partial"

        if not split.picker_id:
            split.picker_id = user_id

        if split.status == "pending":
            split.status = "picking"
            split.started_at = now

        _recalculate_order_warehouse_status(db, split.order)
        db.commit()
        db.refresh(matching_ful)
        db.refresh(split)

        canasta_tag = f" [Canasta: {active_qr}]" if active_qr else ""
        tot_2nd = (matching_ful.checked_box_prods or 0) + (matching_ful.checked_scanned_qty or 0) + (matching_ful.checked_manual_qty or 0)
        return {
            "success": True,
            "message": f"Escaneo registrado: {matching_item.product.name} ({new_verified}/{matching_item.quantity}){canasta_tag}",
            "order_item_id": matching_item.order_item_id,
            "product_id": matching_item.product_id,
            "product_name": matching_item.product.name,
            "picked_scanned_qty": matching_ful.picked_scanned_qty,
            "checked_scanned_qty": matching_ful.checked_scanned_qty,
            "picked_total_qty": new_verified,
            "checked_total_qty": tot_2nd,
            "scanned_prods": matching_ful.picked_scanned_qty,
            "checker_scanned_prods": matching_ful.checked_scanned_qty,
            "total_verified": new_verified,
            "checker_total_verified": tot_2nd,
            "required_quantity": matching_item.quantity,
            "remaining_quantity": max(0, matching_item.quantity - new_verified),
            "status": matching_ful.status,
            "item_status": matching_ful.status,
            "split_status": split.status,
            "is_checking_mode": False,
            "container_qr": active_qr,
            "active_container_qr": active_qr
        }

    # Revisar si el producto pertenece a otro split del pedido
    other_fulfillments = db.query(WarehouseItem).options(
        joinedload(WarehouseItem.split),
        joinedload(WarehouseItem.order_item).joinedload(OrderItem.product)
    ).join(
        OrderItem, WarehouseItem.order_item_id == OrderItem.order_item_id
    ).filter(
        OrderItem.order_id == split.order_id,
        WarehouseItem.split_id != split_id
    ).all()

    for o_ful in other_fulfillments:
        o_it = o_ful.order_item
        if o_it and o_it.product:
            code_match = (o_it.product.codebar or "").strip().lower() == barcode_clean
            sku_match = (o_it.product_id or "").strip().lower() == barcode_clean
            if code_match or sku_match:
                other_num = o_ful.split.split_number if o_ful.split else "?"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Este producto pertenece a el split #{other_num} de este pedido (#{split.order_id})"
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"El codigo '{barcode}' no corresponde a ningun producto del pedido #{split.order_id}"
    )


def add_boxes_master(
    db: Session,
    split_id: UUID,
    order_item_id: UUID,
    boxes_count: int,
    units_per_box: int,
    user_id: int,
    current_user: Optional[User] = None,
    container_qr: Optional[str] = None
) -> WarehouseSplitItemResponse:
    """Registrar piezas por cajas maestras (Master Boxes)"""
    if boxes_count <= 0 or units_per_box <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cajas y unidades deben ser mayores a 0"
        )

    split = _get_split_model(db, split_id)

    # Validación estricta de permisos server-side
    _validate_split_operator_permissions(split, current_user, user_id, "registrar cajas")

    if split.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El split ya se encuentra completada y sellada"
        )

    item = db.query(OrderItem).options(
        joinedload(OrderItem.product)
    ).filter(
        OrderItem.order_item_id == order_item_id
    ).first()

    ful = db.query(WarehouseItem).options(
        joinedload(WarehouseItem.picker),
        joinedload(WarehouseItem.admin_editor)
    ).filter(
        WarehouseItem.order_item_id == order_item_id,
        WarehouseItem.split_id == split_id
    ).first()

    if not item or not ful:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida no encontrada en este split"
        )
    total_units_to_add = boxes_count * units_per_box
    now = datetime.now(timezone.utc)
    is_checking = (split.status in ["ready_for_check", "checking"]) or (split.checker_id == user_id and split.status not in ["pending", "picking", "in_progress"])

    target_container_id = None
    active_qr = None
    if getattr(split, "uses_containers", False):
        target_container_id = split.active_container_id
        if not target_container_id and container_qr and container_qr.strip():
            c = db.query(WarehouseContainer).filter(
                func.upper(WarehouseContainer.qr_code) == container_qr.strip().upper()
            ).first()
            if c:
                target_container_id = c.container_id
                split.active_container_id = c.container_id
        if not target_container_id and split.containers:
            target_container_id = split.containers[-1].container_id
            split.active_container_id = target_container_id

        if not target_container_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="🧺 Modo Canastas activo: Debes escanear o vincular el código QR de una canasta física antes de empaquetar cajas."
            )

        if target_container_id:
            active_c = db.query(WarehouseContainer).filter(WarehouseContainer.container_id == target_container_id).first()
            active_qr = active_c.qr_code if active_c else None
            ful.container_id = target_container_id
    else:
        # Surtido Directo: opcionalmente vincular a canasta si hay una activa o enviada
        target_container_id = split.active_container_id
        if not target_container_id and container_qr and container_qr.strip():
            c = db.query(WarehouseContainer).filter(
                func.upper(WarehouseContainer.qr_code) == container_qr.strip().upper()
            ).first()
            if c:
                target_container_id = c.container_id
        if target_container_id:
            active_c = db.query(WarehouseContainer).filter(WarehouseContainer.container_id == target_container_id).first()
            active_qr = active_c.qr_code if active_c else None
            ful.container_id = target_container_id
        else:
            ful.container_id = None

    if is_checking:
        prev_boxes = ful.checked_boxes or 0
        prev_box_prods = ful.checked_box_prods or 0
        prev_units = int(round(prev_box_prods / prev_boxes)) if (prev_boxes > 0 and prev_box_prods > 0) else 0

        other_verified = (ful.checked_scanned_qty or 0) + (ful.checked_manual_qty or 0)

        if prev_units > 0 and prev_units != units_per_box:
            new_box_prods = total_units_to_add
            new_boxes = boxes_count
        else:
            new_box_prods = prev_box_prods + total_units_to_add
            new_boxes = prev_boxes + boxes_count

        new_total_verified = other_verified + new_box_prods
        if new_total_verified > item.quantity:
            available_to_verify = max(0, item.quantity - other_verified - (0 if (prev_units > 0 and prev_units != units_per_box) else prev_box_prods))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceso en 2do filtro: se intentan registrar {total_units_to_add} piezas en cajas pero solo caben {available_to_verify} piezas"
            )

        ful.checked_boxes = new_boxes
        ful.checked_box_prods = new_box_prods
        ful.checked_at = now
        ful.checked_by = user_id

        if target_container_id:
            _record_container_item(
                db=db,
                split=split,
                order_item_id=item.order_item_id,
                product_id=item.product_id,
                warehouse_item_id=ful.warehouse_item_id,
                is_checking=True,
                container_qr=active_qr,
                boxes_delta=boxes_count,
                box_prods_delta=total_units_to_add
            )

        if not split.checker_id:
            split.checker_id = user_id
        if not split.checking_started_at:
            split.checking_started_at = now
        if split.status == "ready_for_check":
            split.status = "checking"

        _recalculate_order_warehouse_status(db, split.order)
        db.commit()
        db.refresh(ful)
        db.refresh(item)
        is_admin = bool(current_user and (getattr(current_user, "role_slug", None) == "admin" or getattr(current_user, "role", None) == "admin" or (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))))
        can_supervise = bool(current_user and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.supervisor") or current_user.has_permission("orders.approve") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))
        is_wh_op = bool(current_user and not is_admin and not can_supervise and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.operator") or current_user.has_permission("warehouse.pack") or current_user.has_permission("warehouse.check")))
        return WarehouseSplitItemResponse.build_from_fulfillment(ful, item, is_warehouse_operator=is_wh_op, is_checker_mode=True)

    # Modo Surtido de Piso (Picker)
    prev_boxes = ful.picked_boxes or 0
    prev_box_prods = ful.picked_box_prods or 0
    prev_units = int(round(prev_box_prods / prev_boxes)) if (prev_boxes > 0 and prev_box_prods > 0) else 0

    other_verified = (ful.picked_scanned_qty or 0) + (ful.picked_manual_qty or 0)

    if prev_units > 0 and prev_units != units_per_box:
        new_box_prods = total_units_to_add
        new_boxes = boxes_count
    else:
        new_box_prods = prev_box_prods + total_units_to_add
        new_boxes = prev_boxes + boxes_count

    new_total_verified = other_verified + new_box_prods
    if new_total_verified > item.quantity:
        available_to_verify = max(0, item.quantity - other_verified - (0 if (prev_units > 0 and prev_units != units_per_box) else prev_box_prods))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exceso de piezas: se intentan registrar {total_units_to_add} piezas en cajas pero solo caben {available_to_verify} piezas"
        )

    ful.picked_boxes = new_boxes
    ful.picked_box_prods = new_box_prods
    ful.picked_by = user_id
    ful.picked_at = now

    if target_container_id:
        _record_container_item(
            db=db,
            split=split,
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            warehouse_item_id=ful.warehouse_item_id,
            is_checking=False,
            container_qr=active_qr,
            boxes_delta=boxes_count,
            box_prods_delta=total_units_to_add
        )

    if new_total_verified >= item.quantity:
        ful.status = "completed"
    else:
        ful.status = "partial"

    if not split.picker_id:
        split.picker_id = user_id

    if split.status == "pending":
        split.status = "picking"
        split.started_at = now

    _recalculate_order_warehouse_status(db, split.order)
    db.commit()
    db.refresh(ful)
    db.refresh(item)
    return WarehouseSplitItemResponse.build_from_fulfillment(ful, item)


def add_manual_verification(
    db: Session,
    split_id: UUID,
    order_item_id: UUID,
    quantity: int,
    reason: Optional[str],
    user_id: int,
    current_user: Optional[User] = None,
    container_qr: Optional[str] = None
) -> WarehouseSplitItemResponse:
    """Registrar verificación manual con motivo de auditoría"""
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cantidad debe ser mayor a 0"
        )

    split = _get_split_model(db, split_id)

    # Validación estricta de permisos server-side
    _validate_split_operator_permissions(split, current_user, user_id, "validar manualmente")

    if split.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El split ya se encuentra completada y sellada"
        )

    item = db.query(OrderItem).options(
        joinedload(OrderItem.product)
    ).filter(
        OrderItem.order_item_id == order_item_id
    ).first()

    ful = db.query(WarehouseItem).options(
        joinedload(WarehouseItem.picker),
        joinedload(WarehouseItem.admin_editor)
    ).filter(
        WarehouseItem.order_item_id == order_item_id,
        WarehouseItem.split_id == split_id
    ).first()

    if not item or not ful:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida no encontrada en este split"
        )
    now = datetime.now(timezone.utc)
    is_checking = (split.status in ["ready_for_check", "checking"]) or (split.checker_id == user_id and split.status not in ["pending", "picking", "in_progress"])

    target_container_id = None
    active_qr = None
    if getattr(split, "uses_containers", False):
        target_container_id = split.active_container_id
        if not target_container_id and container_qr and container_qr.strip():
            c = db.query(WarehouseContainer).filter(
                func.upper(WarehouseContainer.qr_code) == container_qr.strip().upper()
            ).first()
            if c:
                target_container_id = c.container_id
                split.active_container_id = c.container_id
        if not target_container_id and split.containers:
            target_container_id = split.containers[-1].container_id
            split.active_container_id = target_container_id

        if not target_container_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="🧺 Modo Canastas activo: Debes escanear o vincular el código QR de una canasta física antes de registrar conteo manual."
            )

        if target_container_id:
            active_c = db.query(WarehouseContainer).filter(WarehouseContainer.container_id == target_container_id).first()
            active_qr = active_c.qr_code if active_c else None
            ful.container_id = target_container_id
    else:
        # Surtido Directo: opcionalmente vincular a canasta si hay una activa o enviada
        target_container_id = split.active_container_id
        if not target_container_id and container_qr and container_qr.strip():
            c = db.query(WarehouseContainer).filter(
                func.upper(WarehouseContainer.qr_code) == container_qr.strip().upper()
            ).first()
            if c:
                target_container_id = c.container_id
        if target_container_id:
            active_c = db.query(WarehouseContainer).filter(WarehouseContainer.container_id == target_container_id).first()
            active_qr = active_c.qr_code if active_c else None
            ful.container_id = target_container_id
        else:
            ful.container_id = None

    if is_checking:
        current_verified = (ful.checked_box_prods or 0) + (ful.checked_scanned_qty or 0) + (ful.checked_manual_qty or 0)
        available = item.quantity - current_verified

        if quantity > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exceso en 2do filtro: faltan {available} piezas por revisar"
            )

        ful.checked_manual_qty = (ful.checked_manual_qty or 0) + quantity
        if reason:
            ful.checked_manual_reason = reason
        ful.checked_at = now
        ful.checked_by = user_id

        if target_container_id:
            _record_container_item(
                db=db,
                split=split,
                order_item_id=item.order_item_id,
                product_id=item.product_id,
                warehouse_item_id=ful.warehouse_item_id,
                is_checking=True,
                container_qr=active_qr,
                manual_qty_delta=quantity
            )

        if not split.checker_id:
            split.checker_id = user_id
        if not split.checking_started_at:
            split.checking_started_at = now
        if split.status == "ready_for_check":
            split.status = "checking"

        _recalculate_order_warehouse_status(db, split.order)
        db.commit()
        db.refresh(ful)
        db.refresh(item)
        is_admin = bool(current_user and (getattr(current_user, "role_slug", None) == "admin" or getattr(current_user, "role", None) == "admin" or (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))))
        can_supervise = bool(current_user and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.supervisor") or current_user.has_permission("orders.approve") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))
        is_wh_op = bool(current_user and not is_admin and not can_supervise and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.operator") or current_user.has_permission("warehouse.pack") or current_user.has_permission("warehouse.check")))
        return WarehouseSplitItemResponse.build_from_fulfillment(ful, item, is_warehouse_operator=is_wh_op, is_checker_mode=True)

    # Modo Surtido de Piso (Picker)
    current_verified = (ful.picked_box_prods or 0) + (ful.picked_scanned_qty or 0) + (ful.picked_manual_qty or 0)
    available = item.quantity - current_verified

    if quantity > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exceso de piezas: faltan {available} para completar la partida"
        )

    ful.picked_manual_qty = (ful.picked_manual_qty or 0) + quantity
    if reason:
        ful.picked_manual_reason = reason
    new_verified = (ful.picked_box_prods or 0) + (ful.picked_scanned_qty or 0) + (ful.picked_manual_qty or 0)
    ful.picked_by = user_id
    ful.picked_at = now

    if target_container_id:
        _record_container_item(
            db=db,
            split=split,
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            warehouse_item_id=ful.warehouse_item_id,
            is_checking=False,
            container_qr=active_qr,
            manual_qty_delta=quantity
        )

    if new_verified >= item.quantity:
        ful.status = "completed"
    else:
        ful.status = "partial"

    if not split.picker_id:
        split.picker_id = user_id

    if split.status == "pending":
        split.status = "picking"
        split.started_at = now

    _recalculate_order_warehouse_status(db, split.order)
    db.commit()
    db.refresh(ful)
    db.refresh(item)
    return WarehouseSplitItemResponse.build_from_fulfillment(ful, item)
