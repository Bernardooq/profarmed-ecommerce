"""
CRUD y Gestión de Canastas Físicas QR (Warehouse Containers / Totes) — PBAC & RBAC:

Módulo especializado en:
- Parque físico y enrolamiento de canastas QR reutilizables.
- Asignación atómica a splits de surtido (`bind_container_to_split`, `activate_container_for_split`).
- Liberación y mantenimiento de estado (`release_warehouse_container`, `update_warehouse_container_status`).
- Registro atómico de partidas contenidas (`_record_container_item`).
- Desglose consolidado y auditoría forense por canasta (`get_split_containers_summary`, `get_split_container_items`).
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from db.base import (
    WarehouseContainer, WarehouseSplit, WarehouseContainerItem, WarehouseItem, User
)


def list_warehouse_containers(
    db: Session,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[WarehouseContainer]:
    """Lista las canastas físicas de almacén con filtro por estado y búsqueda por código QR o ID"""
    try:
        from sqlalchemy import cast, or_, String
        q = db.query(WarehouseContainer).options(
            joinedload(WarehouseContainer.current_split),
            joinedload(WarehouseContainer.current_user)
        )
        if status_filter:
            q = q.filter(WarehouseContainer.status == status_filter)
        if search and search.strip():
            s = f"%{search.strip()}%"
            q = q.outerjoin(WarehouseSplit, WarehouseContainer.current_split_id == WarehouseSplit.split_id).filter(
                or_(
                    WarehouseContainer.qr_code.ilike(s),
                    cast(WarehouseContainer.container_id, String).ilike(s),
                    WarehouseSplit.split_code.ilike(s)
                )
            ).distinct()
        return q.order_by(WarehouseContainer.qr_code.asc()).offset(skip).limit(limit).all()
    except Exception as e:
        if "does not exist" in str(e).lower() or "undefinedtable" in type(e).__name__.lower():
            db.rollback()
            return []
        raise


def get_warehouse_containers_stats(db: Session) -> Dict[str, int]:
    """Devuelve las métricas consolidadas del parque físico de canastas QR"""
    try:
        rows = db.query(WarehouseContainer.status, func.count(WarehouseContainer.container_id)).group_by(WarehouseContainer.status).all()
        stats = {
            "total": 0,
            "available": 0,
            "in_use": 0,
            "maintenance": 0,
            "retired": 0
        }
        for st, count in rows:
            stats[st] = count
            stats["total"] += count
        return stats
    except Exception as e:
        if "does not exist" in str(e).lower() or "undefinedtable" in type(e).__name__.lower():
            db.rollback()
            return {"total": 0, "available": 0, "in_use": 0, "maintenance": 0, "retired": 0}
        raise


def _parse_container_id(cid: Any) -> Any:
    if cid is None:
        return None
    if isinstance(cid, UUID):
        return cid
    try:
        return UUID(str(cid))
    except Exception:
        return cid


def get_warehouse_container_by_id(db: Session, container_id: Union[UUID, str]) -> Optional[WarehouseContainer]:
    """Obtiene una canasta física por su UUID"""
    c_uuid = _parse_container_id(container_id)
    try:
        return db.query(WarehouseContainer).options(
            joinedload(WarehouseContainer.current_split),
            joinedload(WarehouseContainer.current_user)
        ).filter(WarehouseContainer.container_id == c_uuid).first()
    except Exception as e:
        if "does not exist" in str(e).lower() or "undefinedtable" in type(e).__name__.lower():
            db.rollback()
            return None
        raise


def get_warehouse_container_by_qr(db: Session, qr_code: str) -> Optional[WarehouseContainer]:
    """Obtiene una canasta física por su código QR escaneado"""
    cleaned_qr = qr_code.strip()
    try:
        return db.query(WarehouseContainer).options(
            joinedload(WarehouseContainer.current_split),
            joinedload(WarehouseContainer.current_user)
        ).filter(func.lower(WarehouseContainer.qr_code) == func.lower(cleaned_qr)).first()
    except Exception as e:
        if "does not exist" in str(e).lower() or "undefinedtable" in type(e).__name__.lower():
            db.rollback()
            return None
        raise


def create_warehouse_container(db: Session, qr_code: str) -> WarehouseContainer:
    """Enrola una nueva canasta QR en el sistema garantizando unicidad"""
    cleaned_qr = qr_code.strip().upper()
    try:
        existing = db.query(WarehouseContainer).filter(
            func.lower(WarehouseContainer.qr_code) == func.lower(cleaned_qr)
        ).first()
    except Exception as e:
        if "does not exist" in str(e).lower() or "undefinedtable" in type(e).__name__.lower():
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="La tabla 'warehouse_containers' aún no ha sido creada en la base de datos. Ejecute la migración de almacén."
            )
        raise

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una canasta registrada con el código QR '{cleaned_qr}'"
        )
    container = WarehouseContainer(
        qr_code=cleaned_qr,
        status="available"
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


def update_warehouse_container_status(db: Session, container_id: Union[UUID, str], new_status: str) -> WarehouseContainer:
    """Actualiza el estado físico de la canasta (available, in_use, damaged, maintenance, retired, unavailable)"""
    allowed_statuses = ["available", "in_use", "damaged", "maintenance", "retired", "unavailable"]
    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido '{new_status}'. Permitidos: {allowed_statuses}"
        )
    container = get_warehouse_container_by_id(db, container_id)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canasta #{container_id} no encontrada"
        )

    container.status = new_status
    if new_status in ["available", "damaged", "maintenance", "retired", "unavailable"]:
        container.current_split_id = None
        container.current_user_id = None

    db.commit()
    db.refresh(container)
    return container


def bind_container_to_split(
    db: Session,
    split_id: UUID,
    qr_code: str,
    user_id: int
) -> WarehouseContainer:
    """Vincula una canasta física con código QR a un split de surtido activo"""
    split = db.query(WarehouseSplit).filter(WarehouseSplit.split_id == split_id).first()
    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split '{split_id}' no encontrado"
        )

    container = get_warehouse_container_by_qr(db, qr_code)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canasta física con QR '{qr_code}' no registrada en el sistema"
        )

    if container.status in ["damaged", "maintenance", "retired", "unavailable"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La canasta QR '{qr_code}' está marcada como '{container.status}' y no puede ser utilizada para surtido"
        )

    # Si ya está en uso por otro split diferente
    if container.status == "in_use" and container.current_split_id and container.current_split_id != split_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La canasta QR '{qr_code}' ya está asignada a otro split. Libérela antes de reasignar."
        )

    container.status = "in_use"
    container.current_split_id = split_id
    container.current_user_id = user_id
    container.updated_at = datetime.now(timezone.utc)
    split.active_container_id = container.container_id

    # Si se asocia una canasta, asegurar que el split quede en modalidad con canastas
    split.uses_containers = True

    now = datetime.now(timezone.utc)
    if split.status == "pending":
        split.status = "picking"
        split.started_at = now
        if not split.picker_id:
            split.picker_id = user_id
    elif split.status == "ready_for_check":
        split.status = "checking"
        if not split.checker_id:
            split.checker_id = user_id
        if not split.checking_started_at:
            split.checking_started_at = now

    db.commit()
    db.refresh(container)
    db.refresh(split)
    return container


def activate_container_for_split(
    db: Session,
    split_id: UUID,
    qr_code: str,
    user_id: int
) -> WarehouseSplit:
    """Activa una canasta específica como la canasta de depósito actual para el split"""
    bind_container_to_split(db=db, split_id=split_id, qr_code=qr_code, user_id=user_id)
    split = db.query(WarehouseSplit).filter(WarehouseSplit.split_id == split_id).first()
    return split


def release_warehouse_container(
    db: Session,
    qr_code: Optional[str] = None,
    container_id: Optional[Union[UUID, str]] = None,
    current_user: Optional[User] = None,
    empty_items: bool = False
) -> WarehouseContainer:
    """
    Libera una canasta física devolviéndola al estado 'available'.
    
    Protección de Concurrencia y Máquina de Estados:
    - Aplica row-level locking (with_for_update) para evitar condiciones de carrera.
    - Si la canasta contiene piezas en un split activo y empty_items=False, rechaza con HTTP 400.
    - Si empty_items=True, descuenta atómicamente las piezas de warehouse_items para devolverlas
      a estado 'pending' y evitar que queden piezas huérfanas 'sin canasta'.
    """
    query = db.query(WarehouseContainer)
    if qr_code:
        container = query.filter(func.upper(WarehouseContainer.qr_code) == qr_code.strip().upper()).with_for_update().first()
    elif container_id:
        container = query.filter(WarehouseContainer.container_id == container_id).with_for_update().first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere 'qr_code' o 'container_id' para liberar la canasta"
        )

    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canasta física no encontrada"
        )

    old_split_id = container.current_split_id
    if old_split_id:
        split = db.query(WarehouseSplit).filter(WarehouseSplit.split_id == old_split_id).with_for_update().first()
        if split and split.status not in ["completed", "cancelled"]:
            # Verificar si el usuario que solicita la liberación es Administrador, Supervisor o el operador asignado
            is_allowed = False
            if current_user:
                is_allowed = (
                    current_user.role_id == 1
                    or (hasattr(current_user, "has_permission") and (
                        current_user.has_permission("system.admin")
                        or current_user.has_permission("warehouse.manage")
                        or current_user.has_permission("warehouse.supervisor")
                    ))
                    or split.picker_id == current_user.user_id
                    or split.checker_id == current_user.user_id
                )
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"La canasta '{container.qr_code}' está en uso en el split #{split.split_number} en proceso ('{split.status}'). Solo el operador asignado, Supervisor o Administrador puede desvincularla."
                )

            # Verificar si la canasta contiene piezas depositadas en este split
            from db.base import WarehouseContainerItem, WarehouseItem
            c_items = db.query(WarehouseContainerItem).filter(
                WarehouseContainerItem.split_id == old_split_id,
                WarehouseContainerItem.container_id == container.container_id
            ).all()

            tot_pieces = sum(
                (ci.picked_scanned_qty or 0) + (ci.picked_box_prods or 0) + (ci.picked_manual_qty or 0) +
                (ci.checked_scanned_qty or 0) + (ci.checked_box_prods or 0) + (ci.checked_manual_qty or 0)
                for ci in c_items
            )

            if tot_pieces > 0 and not empty_items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La canasta '{container.qr_code}' tiene {tot_pieces} pieza(s) depositada(s) en este lote. No se puede desvincular una canasta con producto adentro para evitar pérdida de trazabilidad. Confirma el vaciado para regresar las piezas a pendientes o transfiérelas antes de desvincularla."
                )

            # Optimización O(1) queries: Cargar en un solo query las demás canastas que contienen piezas de este split
            remaining_ci_list = db.query(WarehouseContainerItem).filter(
                WarehouseContainerItem.split_id == old_split_id,
                WarehouseContainerItem.container_id != container.container_id
            ).all()
            other_ci_map = {r.warehouse_item_id: r for r in remaining_ci_list}

            if tot_pieces > 0 and empty_items:
                # Mapeo en memoria O(1) de warehouse_items del split
                wi_map = {wi.warehouse_item_id: wi for wi in (split.warehouse_items or [])}
                # Revertir de forma atómica y consistente los escaneos de estas partidas en WarehouseItem
                for ci in c_items:
                    wi = wi_map.get(ci.warehouse_item_id)
                    if wi:
                        wi.picked_scanned_qty = max(0, (wi.picked_scanned_qty or 0) - (ci.picked_scanned_qty or 0))
                        wi.picked_boxes = max(0, (wi.picked_boxes or 0) - (ci.picked_boxes or 0))
                        wi.picked_box_prods = max(0, (wi.picked_box_prods or 0) - (ci.picked_box_prods or 0))
                        wi.picked_manual_qty = max(0, (wi.picked_manual_qty or 0) - (ci.picked_manual_qty or 0))
                        wi.checked_scanned_qty = max(0, (wi.checked_scanned_qty or 0) - (ci.checked_scanned_qty or 0))
                        wi.checked_boxes = max(0, (wi.checked_boxes or 0) - (ci.checked_boxes or 0))
                        wi.checked_box_prods = max(0, (wi.checked_box_prods or 0) - (ci.checked_box_prods or 0))
                        wi.checked_manual_qty = max(0, (wi.checked_manual_qty or 0) - (ci.checked_manual_qty or 0))

                        # Búsqueda O(1) en mapa en lugar de query individual
                        other_ci = other_ci_map.get(wi.warehouse_item_id)
                        if other_ci:
                            wi.container_id = other_ci.container_id
                            wi.container_qr = other_ci.container_qr
                        else:
                            wi.container_id = None
                            wi.container_qr = None
                            if (wi.picked_total_qty or 0) == 0:
                                wi.status = "pending"
                                wi.picked_at = None
                                wi.picked_by = None

                    db.delete(ci)
            else:
                for ci in c_items:
                    db.delete(ci)

            # Si alguna partida tenía este container asignado pero ya no hay piezas, actualizar referencia en O(1) por partida
            for wi in (split.warehouse_items or []):
                if wi.container_id == container.container_id:
                    other_ci = other_ci_map.get(wi.warehouse_item_id)
                    if other_ci:
                        wi.container_id = other_ci.container_id
                        wi.container_qr = other_ci.container_qr
                    else:
                        wi.container_id = None
                        wi.container_qr = None

    container.status = "available"
    container.current_split_id = None
    container.current_user_id = None
    container.updated_at = datetime.now(timezone.utc)

    # Si era la canasta activa del split, buscar otra canasta activa o setear a None
    if old_split_id:
        split = db.query(WarehouseSplit).filter(WarehouseSplit.split_id == old_split_id).first()
        if split:
            if split.active_container_id == container.container_id:
                other_container = db.query(WarehouseContainer).filter(
                    WarehouseContainer.current_split_id == old_split_id,
                    WarehouseContainer.container_id != container.container_id
                ).first()
                split.active_container_id = other_container.container_id if other_container else None

            if empty_items and tot_pieces > 0:
                if split.status in ["ready_for_check", "checking", "completed", "audited"]:
                    split.status = "picking"
                    split.picking_completed_at = None
                    split.completed_at = None
                    split.checking_started_at = None
                from crud.crud_warehouse_status import _recalculate_order_warehouse_status
                _recalculate_order_warehouse_status(db, split.order)

    db.commit()
    db.refresh(container)
    return container


def delete_warehouse_container(db: Session, container_id: Union[UUID, str]) -> bool:
    """Elimina una canasta física que nunca haya sido utilizada en pedidos"""
    container = get_warehouse_container_by_id(db, container_id)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canasta #{container_id} no encontrada"
        )

    if container.status == "in_use":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la canasta '{container.qr_code}' porque está actualmente en uso en un split activo"
        )

    # Verificar si la canasta ya tiene historial operativo previo en pedidos o splits
    has_history = (
        db.query(WarehouseContainerItem.container_item_id).filter(WarehouseContainerItem.container_id == container.container_id).first() is not None
        or db.query(WarehouseItem.warehouse_item_id).filter(WarehouseItem.container_id == container.container_id).first() is not None
    )

    if has_history:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La canasta '{container.qr_code}' ya cuenta con historial de auditoría en pedidos de bodega y no puede eliminarse para preservar la trazabilidad forense. En su lugar, márcala como 'Retirada / Baja' (retired) o 'En Mantenimiento'."
        )

    db.delete(container)
    db.commit()
    return True


def _record_container_item(
    db: Session,
    split: WarehouseSplit,
    order_item_id: UUID,
    product_id: str,
    warehouse_item_id: Optional[UUID],
    is_checking: bool,
    container_qr: Optional[str] = None,
    scanned_qty_delta: int = 0,
    boxes_delta: int = 0,
    box_prods_delta: int = 0,
    manual_qty_delta: int = 0
):
    """Registra la distribución física consolidada de un producto en una canasta QR (solo si el split usa canastas)"""
    if not getattr(split, "uses_containers", False):
        return

    target_container_id = None
    if container_qr and container_qr.strip():
        c = db.query(WarehouseContainer).filter(
            func.upper(WarehouseContainer.qr_code) == container_qr.strip().upper()
        ).first()
        if c:
            target_container_id = c.container_id
            if c.status == "available":
                c.status = "in_use"
                c.current_split_id = split.split_id
            split.active_container_id = c.container_id
    elif split.active_container_id:
        target_container_id = split.active_container_id
    elif split.containers:
        target_container_id = split.containers[-1].container_id
        split.active_container_id = target_container_id

    if target_container_id:
        ci = db.query(WarehouseContainerItem).filter(
            WarehouseContainerItem.split_id == split.split_id,
            WarehouseContainerItem.container_id == target_container_id,
            WarehouseContainerItem.product_id == product_id
        ).with_for_update().first()

        if not ci:
            ci = WarehouseContainerItem(
                split_id=split.split_id,
                container_id=target_container_id,
                warehouse_item_id=warehouse_item_id,
                order_item_id=order_item_id,
                product_id=product_id,
                picked_scanned_qty=0,
                picked_boxes=0,
                picked_box_prods=0,
                picked_manual_qty=0,
                checked_scanned_qty=0,
                checked_boxes=0,
                checked_box_prods=0,
                checked_manual_qty=0
            )
            db.add(ci)

        if is_checking:
            ci.checked_scanned_qty = (ci.checked_scanned_qty or 0) + scanned_qty_delta
            ci.checked_boxes = (ci.checked_boxes or 0) + boxes_delta
            ci.checked_box_prods = (ci.checked_box_prods or 0) + box_prods_delta
            ci.checked_manual_qty = (ci.checked_manual_qty or 0) + manual_qty_delta
        else:
            ci.picked_scanned_qty = (ci.picked_scanned_qty or 0) + scanned_qty_delta
            ci.picked_boxes = (ci.picked_boxes or 0) + boxes_delta
            ci.picked_box_prods = (ci.picked_box_prods or 0) + box_prods_delta
            ci.picked_manual_qty = (ci.picked_manual_qty or 0) + manual_qty_delta

        ci.updated_at = datetime.now(timezone.utc)


def get_split_container_items(db: Session, split_id: UUID) -> List[WarehouseContainerItem]:
    """Obtiene el listado atómico de partidas consolidadas en canastas físicas para un split"""
    try:
        return db.query(WarehouseContainerItem).options(
            joinedload(WarehouseContainerItem.container),
            joinedload(WarehouseContainerItem.product)
        ).filter(WarehouseContainerItem.split_id == split_id).all()
    except Exception as e:
        if "does not exist" in str(e).lower() or "undefinedtable" in type(e).__name__.lower():
            db.rollback()
            return []
        raise


def get_split_containers_summary(db: Session, split_id: UUID) -> List[Dict[str, Any]]:
    """Genera un reporte consolidado agrupado por canasta física con el total de piezas y partidas contenidas"""
    try:
        containers = db.query(WarehouseContainer).filter(WarehouseContainer.current_split_id == split_id).all()
        ci_records = db.query(WarehouseContainerItem).options(
            joinedload(WarehouseContainerItem.container),
            joinedload(WarehouseContainerItem.product)
        ).filter(WarehouseContainerItem.split_id == split_id).all()
    except Exception as e:
        if "does not exist" in str(e).lower() or "undefinedtable" in type(e).__name__.lower():
            db.rollback()
            return []
        raise

    grouped = {}
    for c in containers:
        grouped[c.container_id] = {
            "container_id": c.container_id,
            "qr_code": c.qr_code,
            "status": c.status,
            "total_pieces": 0,
            "total_products": 0,
            "picked_total_units": 0,
            "picked_laser_qty": 0,
            "picked_boxes": 0,
            "picked_box_prods": 0,
            "picked_manual_qty": 0,
            "checked_total_units": 0,
            "checked_laser_qty": 0,
            "checked_boxes": 0,
            "checked_box_prods": 0,
            "checked_manual_qty": 0,
            "items": []
        }

    for ci in ci_records:
        cid = ci.container_id
        if cid not in grouped:
            c_qr = ci.container.qr_code if ci.container else f"Canasta #{cid}"
            c_status = ci.container.status if ci.container else "in_use"
            grouped[cid] = {
                "container_id": cid,
                "qr_code": c_qr,
                "status": c_status,
                "total_pieces": 0,
                "total_products": 0,
                "picked_total_units": 0,
                "picked_laser_qty": 0,
                "picked_boxes": 0,
                "picked_box_prods": 0,
                "picked_manual_qty": 0,
                "checked_total_units": 0,
                "checked_laser_qty": 0,
                "checked_boxes": 0,
                "checked_box_prods": 0,
                "checked_manual_qty": 0,
                "items": []
            }
        
        tot_pieces = ci.picked_total_qty or 0
        grouped[cid]["total_pieces"] += tot_pieces
        grouped[cid]["total_products"] += 1
        grouped[cid]["picked_total_units"] += tot_pieces
        grouped[cid]["picked_laser_qty"] += (ci.picked_scanned_qty or 0)
        grouped[cid]["picked_boxes"] += (ci.picked_boxes or 0)
        grouped[cid]["picked_box_prods"] += (ci.picked_box_prods or 0)
        grouped[cid]["picked_manual_qty"] += (ci.picked_manual_qty or 0)
        grouped[cid]["checked_total_units"] += (ci.checked_total_qty or 0)
        grouped[cid]["checked_laser_qty"] += (ci.checked_scanned_qty or 0)
        grouped[cid]["checked_boxes"] += (ci.checked_boxes or 0)
        grouped[cid]["checked_box_prods"] += (ci.checked_box_prods or 0)
        grouped[cid]["checked_manual_qty"] += (ci.checked_manual_qty or 0)
        grouped[cid]["items"].append({
            "container_item_id": ci.container_item_id,
            "split_id": ci.split_id,
            "container_id": ci.container_id,
            "container_qr": ci.container_qr,
            "warehouse_item_id": ci.warehouse_item_id,
            "order_item_id": ci.order_item_id,
            "product_id": ci.product_id,
            "product_name": ci.product_name,
            "barcode": ci.product.codebar if ci.product else None,
            "picked_scanned_qty": ci.picked_scanned_qty,
            "picked_boxes": ci.picked_boxes,
            "picked_box_prods": ci.picked_box_prods,
            "picked_manual_qty": ci.picked_manual_qty,
            "picked_total_qty": ci.picked_total_qty,
            "checked_scanned_qty": ci.checked_scanned_qty,
            "checked_boxes": ci.checked_boxes,
            "checked_box_prods": ci.checked_box_prods,
            "checked_manual_qty": ci.checked_manual_qty,
            "checked_total_qty": ci.checked_total_qty,
            "updated_at": ci.updated_at
        })

    return list(grouped.values())
