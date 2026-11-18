"""
CRUD y Gestión de Splits de Almacén (Warehouse Splits) — PBAC & RBAC:

Módulo especializado en:
- Obtención de splits con relaciones eager-load optimizadas (`_get_split_model`, `get_split_by_id`, `get_split_by_code`).
- Autoasignación de splits en piso y mesa de revisión (`claim_split`).
- Conmutación dinámica de modalidad con canastas vs surtido directo (`set_split_container_mode`).
- Reasignación controlada por supervisores (`reassign_split`).
- Validación estricta de permisos de operador server-side (`_validate_split_operator_permissions`).
"""

from typing import Optional
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from db.base import (
    Order, OrderItem, WarehouseItem, WarehouseSplit, 
    WarehouseContainer, WarehouseContainerItem, User
)
from schemas.warehouse import WarehouseSplitResponse
from crud.crud_warehouse_status import _recalculate_order_warehouse_status


def _get_split_model(db: Session, split_id: UUID) -> WarehouseSplit:
    """Helper interno para obtener el modelo ORM de WarehouseSplit con joins optimizados"""
    split = db.query(WarehouseSplit).options(
        joinedload(WarehouseSplit.order).joinedload(Order.customer),
        joinedload(WarehouseSplit.order).joinedload(Order.assigned_user),
        joinedload(WarehouseSplit.picker),
        joinedload(WarehouseSplit.checker),
        joinedload(WarehouseSplit.admin_editor),
        joinedload(WarehouseSplit.active_container),
        selectinload(WarehouseSplit.containers),
        selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.order_item).joinedload(OrderItem.product),
        selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.picker),
        selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.admin_editor)
    ).filter(WarehouseSplit.split_id == split_id).first()

    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split '{split_id}' no encontrada"
        )
    return split


def get_split_by_id(
    db: Session,
    split_id: UUID,
    current_user: Optional[User] = None
) -> WarehouseSplitResponse:
    """Obtener split por ID con relaciones cargadas para respuesta API y validación de surtido ciego"""
    split = _get_split_model(db, split_id)
    is_admin = bool(current_user and (getattr(current_user, "role_slug", None) == "admin" or getattr(current_user, "role", None) == "admin" or (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))))
    can_supervise = bool(current_user and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.supervisor") or current_user.has_permission("orders.approve") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))
    is_warehouse_operator = bool(current_user and not is_admin and not can_supervise and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.operator") or current_user.has_permission("warehouse.pack") or current_user.has_permission("warehouse.check")))

    if is_warehouse_operator:
        if not getattr(split.order, "warehouse_show_details", False):
            is_my_split = (split.picker_id == current_user.user_id or split.checker_id == current_user.user_id)
            if not is_my_split and split.status == "pending":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Surtido Ciego: Debes tomar el split #{split.split_number} para ver sus partidas."
                )

    return WarehouseSplitResponse.build_from_split(split, is_warehouse_operator=is_warehouse_operator)


def get_split_by_code(
    db: Session,
    code: str,
    current_user: Optional[User] = None
) -> WarehouseSplitResponse:
    """Obtener split o lote por UUID o split_code (ej. 105-1)"""
    clean_code = (code or "").strip()
    split = None

    # Intentar búsqueda por UUID si tiene formato UUID
    try:
        val_uuid = UUID(clean_code)
        split = db.query(WarehouseSplit).options(
            joinedload(WarehouseSplit.order).joinedload(Order.customer),
            joinedload(WarehouseSplit.order).joinedload(Order.assigned_user),
            joinedload(WarehouseSplit.picker),
            joinedload(WarehouseSplit.checker),
            joinedload(WarehouseSplit.admin_editor),
            joinedload(WarehouseSplit.active_container),
            selectinload(WarehouseSplit.containers),
            selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.order_item).joinedload(OrderItem.product),
            selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.picker),
            selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.admin_editor)
        ).filter(WarehouseSplit.split_id == val_uuid).first()
    except Exception:
        pass

    # Búsqueda por split_code exacto (o insensitive)
    if not split:
        split = db.query(WarehouseSplit).options(
            joinedload(WarehouseSplit.order).joinedload(Order.customer),
            joinedload(WarehouseSplit.order).joinedload(Order.assigned_user),
            joinedload(WarehouseSplit.picker),
            joinedload(WarehouseSplit.checker),
            joinedload(WarehouseSplit.admin_editor),
            joinedload(WarehouseSplit.active_container),
            selectinload(WarehouseSplit.containers),
            selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.order_item).joinedload(OrderItem.product),
            selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.picker),
            selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.admin_editor)
        ).filter(WarehouseSplit.split_code.ilike(clean_code)).first()

    # Fallback si split_code tiene formato order_id-split_number (ej. 105-1)
    if not split and "-" in clean_code:
        parts = clean_code.split("-", 1)
        if parts[0].isdigit() and parts[1].isdigit():
            split = db.query(WarehouseSplit).options(
                joinedload(WarehouseSplit.order).joinedload(Order.customer),
                joinedload(WarehouseSplit.order).joinedload(Order.assigned_user),
                joinedload(WarehouseSplit.picker),
                joinedload(WarehouseSplit.checker),
                joinedload(WarehouseSplit.admin_editor),
                joinedload(WarehouseSplit.active_container),
                selectinload(WarehouseSplit.containers),
                selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.order_item).joinedload(OrderItem.product),
                selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.picker),
                selectinload(WarehouseSplit.warehouse_items).joinedload(WarehouseItem.admin_editor)
            ).filter(
                WarehouseSplit.order_id == int(parts[0]),
                WarehouseSplit.split_number == int(parts[1])
            ).first()

    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split o lote con código '{clean_code}' no encontrada"
        )

    is_admin = bool(current_user and (getattr(current_user, "role_slug", None) == "admin" or getattr(current_user, "role", None) == "admin" or (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))))
    can_supervise = bool(current_user and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.supervisor") or current_user.has_permission("orders.approve") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))
    is_warehouse_operator = bool(current_user and not is_admin and not can_supervise and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.operator") or current_user.has_permission("warehouse.pack") or current_user.has_permission("warehouse.check")))
    if is_warehouse_operator:
        if not getattr(split.order, "warehouse_show_details", False):
            is_my_split = (split.picker_id == current_user.user_id or split.checker_id == current_user.user_id)
            if not is_my_split and split.status == "pending":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Surtido Ciego: Debes tomar el split #{split.split_number} para ver sus partidas."
                )

    return WarehouseSplitResponse.build_from_split(split, is_warehouse_operator=is_warehouse_operator)


def claim_split(
    db: Session,
    split_id: UUID,
    user_id: int,
    as_role: str = "picker",
    uses_containers: Optional[bool] = None
) -> WarehouseSplit:
    """Autoasignar o reclamar un split como picker o checker con configuración de modalidad con o sin canastas"""
    split = _get_split_model(db, split_id)
    now = datetime.now(timezone.utc)

    if as_role == "picker":
        surtido_terminado = (
            split.status == "completed"
            or (split.completed_at is not None and split.status not in ["pending", "picking", "in_progress"])
        )
        if surtido_terminado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El proceso de surtido de el split #{split.split_number} ya ha finalizado"
            )

        if split.picker_id and split.picker_id != user_id and split.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Este split ya esta asignada al surtidor #{split.picker_id}"
            )
        split.picker_id = user_id
        if uses_containers is not None:
            split.uses_containers = bool(uses_containers)

    elif as_role == "checker":
        checking_terminado = (
            split.status in ["completed", "audited", "shipped", "delivered", "cancelled"]
            or (split.checker_id is not None and split.status == "completed" and split.security_seal_folio is not None)
        )
        if checking_terminado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El proceso de revision de el split #{split.split_number} ya ha finalizado"
            )

        if split.checker_id and split.checker_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Este split ya esta asignada al revisor #{split.checker_id}"
            )
        split.checker_id = user_id
        if split.status == "ready_for_check":
            split.status = "checking"
        split.completed_at = None
        if not split.checking_started_at:
            split.checking_started_at = now
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol invalido para reclamar split (debe ser 'picker' o 'checker')"
        )

    if as_role == "picker" and split.status == "pending":
        split.status = "picking"
        split.started_at = now

    _recalculate_order_warehouse_status(db, split.order)
    db.commit()
    db.refresh(split)
    return split


def set_split_container_mode(
    db: Session,
    split_id: UUID,
    uses_containers: bool,
    user_id: int,
    current_user: Optional[User] = None,
    reset_progress: bool = False
) -> WarehouseSplitResponse:
    """Configurar explícitamente modalidad con o sin canastas para el split"""
    split = _get_split_model(db, split_id)
    _validate_split_operator_permissions(split, current_user, user_id, "cambiar la modalidad de canastas")

    # Contar avance físico actual de surtido
    total_picked_units = sum(
        (wi.picked_scanned_qty or 0) + (wi.picked_box_prods or 0) + (wi.picked_manual_qty or 0)
        for wi in (split.warehouse_items or [])
    )

    if bool(uses_containers):
        # Transición: Surtido Directo -> Con Canastas QR
        # Si el split ya tenía progreso en directo y no se ha autorizado reiniciar:
        if not split.uses_containers and total_picked_units > 0 and not reset_progress:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "require_reset_confirmation": True,
                    "picked_units": total_picked_units,
                    "message": (
                        f"El split #{split.split_number} tiene {total_picked_units} piezas surtidas en modo directo. "
                        f"Para activar el modo estricto de Canastas QR, es necesario reiniciar los contadores a 0 "
                        f"para que cada pieza sea depositada físicamente en su contenedor QR."
                    )
                }
            )

        split.uses_containers = True
        split.active_container_id = None

        # Si se confirmó reiniciar el progreso:
        if reset_progress and total_picked_units > 0:
            for wi in (split.warehouse_items or []):
                wi.picked_scanned_qty = 0
                wi.picked_boxes = 0
                wi.picked_box_prods = 0
                wi.picked_manual_qty = 0
                wi.picked_manual_reason = None
                wi.picked_by = None
                wi.picked_at = None
                wi.container_id = None
                wi.status = "pending"

            db.query(WarehouseContainerItem).filter(
                WarehouseContainerItem.split_id == split.split_id
            ).delete(synchronize_session=False)

            if split.status not in ["pending", "cancelled"]:
                split.status = "picking"

    else:
        # Transición: Con Canastas QR -> Surtido Directo
        split.uses_containers = False
        split.active_container_id = None

        # 1. Eliminar registros de warehouse_container_items de este split
        db.query(WarehouseContainerItem).filter(
            WarehouseContainerItem.split_id == split.split_id
        ).delete(synchronize_session=False)

        # 2. Desasociar canastas de las partidas en warehouse_items (preservando el conteo de surtido)
        for wi in (split.warehouse_items or []):
            wi.container_id = None

        # 3. Liberar todas las canastas asignadas a este split
        assigned_containers = db.query(WarehouseContainer).filter(
            WarehouseContainer.current_split_id == split.split_id
        ).all()
        for c in assigned_containers:
            c.status = "available"
            c.current_split_id = None
            c.current_user_id = None
            c.updated_at = datetime.now(timezone.utc)

    _recalculate_order_warehouse_status(db, split.order)
    db.commit()
    db.refresh(split)
    return WarehouseSplitResponse.build_from_split(split)


def reassign_split(
    db: Session,
    split_id: UUID,
    role_type: str = "picker",
    target_user_id: Optional[int] = None,
    picker_id: Optional[int] = None,
    checker_id: Optional[int] = None
) -> WarehouseSplit:
    """Reasignar el operador de un split (picker o checker)"""
    split = _get_split_model(db, split_id)

    if picker_id is not None:
        role_type = "picker"
        target_user_id = picker_id if picker_id > 0 else None
    elif checker_id is not None:
        role_type = "checker"
        target_user_id = checker_id if checker_id > 0 else None

    if role_type == "picker":
        all_fulfilled = (
            len(split.warehouse_items or []) > 0
            and all(
                (f.picked_total_qty or 0) >= (f.required_quantity or (f.order_item.quantity if f.order_item else 0))
                for f in (split.warehouse_items or [])
            )
        )
        surtido_terminado = (
            split.status == "completed"
            or split.completed_at is not None
            or all_fulfilled
        )
        if surtido_terminado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede reasignar: el surtido de el split #{split.split_number} ya ha terminado"
            )

        if target_user_id is not None and target_user_id > 0:
            user = db.query(User).filter(User.user_id == target_user_id).first()
            if not user or not user.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado o inactivo")
            user_slug = getattr(user.role_rel, "slug", "") if user.role_rel else ""
            if user.role_id == 1 or user_slug == "admin" or user.user_id >= 15_000_000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede asignar un lote o split de bodega a una cuenta administradora del sistema."
                )
            split.picker_id = target_user_id
        else:
            split.picker_id = None

    elif role_type == "checker":
        checking_terminado = (
            split.completed_at is not None
            or (split.checker_id is not None and split.status == "completed" and split.security_seal_folio is not None)
        )
        if checking_terminado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede reasignar: la revision de el split #{split.split_number} ya ha terminado"
            )

        if target_user_id is not None and target_user_id > 0:
            user = db.query(User).filter(User.user_id == target_user_id).first()
            if not user or not user.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado o inactivo")
            user_slug = getattr(user.role_rel, "slug", "") if user.role_rel else ""
            if user.role_id == 1 or user_slug == "admin" or user.user_id >= 15_000_000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede asignar un lote o split de bodega a una cuenta administradora del sistema."
                )
            split.checker_id = target_user_id
        else:
            split.checker_id = None

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol invalido para reasignar (debe ser 'picker' o 'checker')"
        )

    db.commit()
    db.refresh(split)
    return split


def _validate_split_operator_permissions(
    split: WarehouseSplit,
    user: Optional[User],
    user_id: int,
    action_description: str = "operar este split"
) -> bool:
    """Valida estrictamente los permisos operativos sobre el split en el servidor"""
    if not user:
        return True

    is_admin = bool(getattr(user, "role_slug", None) == "admin" or getattr(user, "role", None) == "admin" or (hasattr(user, "has_permission") and (user.has_permission("system.admin") or user.has_permission("warehouse.manage") or user.has_permission("warehouse.audit"))))
    if is_admin:
        return True

    # Determinar si el split está en etapa de 2do filtro o 1er filtro
    is_checking = (
        split.status in ["ready_for_check", "checking"]
        or (split.checker_id == user_id and split.status not in ["pending", "picking", "in_progress"])
    )

    if is_checking:
        if split.status == "completed" or split.completed_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado: El 2do filtro de el split #{split.split_number} ya ha concluido y está sellada."
            )
        if split.checker_id != user_id:
            if not split.checker_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Acción denegada: Debes tomar el split #{split.split_number} formalmente como Revisor antes de {action_description}."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permiso denegado: El split #{split.split_number} está asignada a otro revisor."
                )
    else:
        surtido_terminado = (
            split.status in ["ready_for_check", "checking", "completed"]
            or split.completed_at is not None
        )
        if surtido_terminado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado: El 1er filtro (surtido) de el split #{split.split_number} ya ha finalizado."
            )
        if split.picker_id != user_id:
            if not split.picker_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Acción denegada: Debes tomar el split #{split.split_number} formalmente como Recolector antes de {action_description}."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permiso denegado: El split #{split.split_number} está asignada a otro recolector."
                )

    return True
