"""
CRUD y Gestión de Auditoría Forense, Métricas y Overrides de Almacén (Warehouse Audit & Metrics) — PBAC & RBAC Dinámico:

Funciones y Operaciones:
- Generar reporte pericial forense detallado partida por partida (`get_order_warehouse_audit`).
- Obtener métricas y KPIs operativos en tiempo real por fecha (`get_warehouse_stats`).
- Modificar notas y motivos de excepción de auditoría manual (`update_order_item_manual_reason`).
- Overrides administrativos y periciales de estatus y sellos en splits (`admin_override_split`).
- Overrides administrativos de conteos físicos y cajas en 1er y 2do filtro (`admin_override_order_item_counts`).

Reglas de Negocio y Permisos PBAC (PROFARMED v2.2):
1. Trazabilidad Forense Inmutable:
   - Se registra cada pieza validada indicando: método de escaneo (láser / manual / cajas), ID de operador, fecha y timestamp exacto.
2. Permisos y Niveles de Acceso:
   - Auditoría pericial y veredictos: `warehouse.audit` o `system.admin`
   - Supervisión y métricas: `warehouse.supervisor`, `warehouse.manage`, `orders.approve`
   - Operaciones de piso (recolector / revisor): `warehouse.operator`, `warehouse.pack`, `warehouse.check`
   - Overrides y rectificaciones de inventario: Restringidos a personal con facultades de auditoría pericial (`warehouse.audit`, `warehouse.manage`, `system.admin`).
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_

from db.base import (
    Order, OrderItem, WarehouseItem, WarehouseSplit, WarehouseContainer, WarehouseContainerItem, User
)
from crud.crud_warehouse_status import _recalculate_order_warehouse_status
from crud.crud_warehouse_containers import get_split_containers_summary
from crud.crud_commercial_group import user_can_manage_order


""" Generar reporte pericial de auditoria de un pedido en bodega """
def get_order_warehouse_audit(
    db: Session,
    order_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: Optional[User] = None
) -> Dict[str, Any]:
    order = db.query(Order).options(
        selectinload(Order.items).joinedload(OrderItem.product),
        selectinload(Order.items).selectinload(OrderItem.warehouse_items).joinedload(WarehouseItem.picker),
        selectinload(Order.items).selectinload(OrderItem.warehouse_items).joinedload(WarehouseItem.checker),
        selectinload(Order.items).selectinload(OrderItem.warehouse_items).joinedload(WarehouseItem.admin_editor),
        selectinload(Order.items).selectinload(OrderItem.warehouse_items).joinedload(WarehouseItem.split),
        selectinload(Order.splits).joinedload(WarehouseSplit.picker),
        selectinload(Order.splits).joinedload(WarehouseSplit.checker),
        selectinload(Order.splits).joinedload(WarehouseSplit.admin_editor),
        selectinload(Order.splits).selectinload(WarehouseSplit.warehouse_items),
        selectinload(Order.splits).selectinload(WarehouseSplit.containers),
        selectinload(Order.splits).selectinload(WarehouseSplit.container_items).joinedload(WarehouseContainerItem.product),
        selectinload(Order.splits).selectinload(WarehouseSplit.container_items).joinedload(WarehouseContainerItem.container),
        joinedload(Order.warehouse_sender)
    ).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido #{order_id} no encontrado"
        )

    can_audit = bool(
        current_user and (
            getattr(current_user, "role_slug", None) == "admin"
            or getattr(current_user, "role", None) == "admin"
            or (hasattr(current_user, "has_permission") and (
                current_user.has_permission("system.admin")
                or current_user.has_permission("warehouse.audit")
                or current_user.has_permission("warehouse.manage")
            ))
        )
    )
    is_admin = can_audit
    can_supervise = bool(current_user and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.supervisor") or current_user.has_permission("orders.approve") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))
    is_warehouse_operator = bool(current_user and not is_admin and not can_supervise and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.operator") or current_user.has_permission("warehouse.checker") or current_user.has_permission("warehouse.pack") or current_user.has_permission("warehouse.check")))
    is_blind_mode = bool(not getattr(order, "warehouse_show_details", False))

    my_split_ids = set()
    if is_warehouse_operator and current_user:
        my_split_ids = {
            b.split_id for b in (order.splits or [])
            if b.picker_id == current_user.user_id or b.checker_id == current_user.user_id
        }

    # Restricción RBAC para usuarios no supervisores (Operadores bajo Surtido Ciego o Comerciales fuera de su cartera)
    if current_user and not can_supervise:
        if is_warehouse_operator:
            if is_blind_mode and not my_split_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Surtido Ciego: No has participado en ningún split de este pedido."
                )
        else:
            is_own = (order.assigned_user_id == current_user.user_id)
            can_manage = user_can_manage_order(db, current_user.user_id, order.customer_id, current_user)
            if not (is_own or can_manage):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puede consultar la auditoría de pedidos vinculados a su cartera comercial."
                )

    forensic_items = []
    all_verified = True
    total_ordered = 0
    total_verified_sum = 0

    show_final_price = not is_warehouse_operator
    show_base_price = is_admin

    for it in (order.items or []):
        ful = it.warehouse_items[0] if (it.warehouse_items and len(it.warehouse_items) > 0) else None
        boxes = ful.picked_boxes if ful else 0
        box_prods = ful.picked_box_prods if ful else 0
        scanned_prods = ful.picked_scanned_qty if ful else 0
        manual_prods = ful.picked_manual_qty if ful else 0
        manual_reason = ful.picked_manual_reason if ful else None
        item_status = ful.status if ful else "pending"
        split_id = ful.split_id if ful else None
        split_obj = ful.split if ful else None
        verified_by = ful.picked_by if ful else None
        verifier_obj = ful.picker if ful else None
        verified_at = ful.picked_at if ful else None
        checker_boxes = ful.checked_boxes if ful else 0
        checker_box_prods = ful.checked_box_prods if ful else 0
        checker_scanned_prods = ful.checked_scanned_qty if ful else 0
        checker_manual_prods = ful.checked_manual_qty if ful else 0
        checker_manual_reason = ful.checked_manual_reason if ful else None
        checker_verified_at = ful.checked_at if ful else None
        admin_edited_by = ful.admin_override_by if (ful and is_admin) else None
        admin_edited_by_name = (ful.admin_editor.full_name or ful.admin_editor.username) if (ful and ful.admin_editor and is_admin) else None
        admin_edited_at = ful.admin_override_at if (ful and is_admin) else None

        tot = (box_prods or 0) + (scanned_prods or 0) + (manual_prods or 0)
        diff = it.quantity - tot
        if diff != 0:
            all_verified = False

        total_ordered += it.quantity
        total_verified_sum += tot

        checker_total_verified = (checker_box_prods or 0) + (checker_scanned_prods or 0) + (checker_manual_prods or 0)
        is_confidence_val = bool(checker_manual_reason and "Confianza" in checker_manual_reason)

        has_forensic_discrepancy = False
        discrepancy_note = None

        if checker_total_verified > 0 and not is_confidence_val:
            diff_tot = (tot != checker_total_verified)
            diff_bx = ((boxes or 0) != (checker_boxes or 0))
            diff_bx_p = ((box_prods or 0) != (checker_box_prods or 0))
            diff_scn = ((scanned_prods or 0) != (checker_scanned_prods or 0))
            diff_man = ((manual_prods or 0) != (checker_manual_prods or 0))

            if diff_tot:
                has_forensic_discrepancy = True
                discrepancy_note = f"Discrepancia en total: 1er filtro={tot} pzs vs 2do filtro={checker_total_verified} pzs"
            elif diff_bx or diff_bx_p or diff_scn or diff_man:
                has_forensic_discrepancy = True
                # Desglose claro de las diferencias
                disc_parts_1st = []
                disc_parts_2nd = []
                if box_prods > 0 or checker_box_prods > 0:
                    disc_parts_1st.append(f"{boxes} cjas ({box_prods} pz)")
                    disc_parts_2nd.append(f"{checker_boxes} cjas ({checker_box_prods} pz)")
                if scanned_prods > 0 or checker_scanned_prods > 0:
                    disc_parts_1st.append(f"{scanned_prods} lsr")
                    disc_parts_2nd.append(f"{checker_scanned_prods} lsr")
                if manual_prods > 0 or checker_manual_prods > 0:
                    disc_parts_1st.append(f"{manual_prods} man")
                    disc_parts_2nd.append(f"{checker_manual_prods} man")

                str_1st = " + ".join(disc_parts_1st) if disc_parts_1st else f"{tot} pzs"
                str_2nd = " + ".join(disc_parts_2nd) if disc_parts_2nd else f"{checker_total_verified} pzs"
                discrepancy_note = f"Discrepancia de empaque: Surtidor [{str_1st}] vs Revisor [{str_2nd}]"

        is_masked = bool(is_warehouse_operator and is_blind_mode and (split_id not in my_split_ids))
        show_forensic_note = can_audit

        forensic_items.append({
            "order_item_id": it.order_item_id,
            "product_id": "[PROTEGIDO]" if is_masked else it.product_id,
            "product_name": "[Partida protegida por Surtido Ciego]" if is_masked else (it.product.name if it.product else ""),
            "codebar": "—" if is_masked else (it.product.codebar if it.product else None),
            "location": "[CIEGO]" if is_masked else (it.product.location if it.product else ""),
            "ordered_quantity": it.quantity,
            "boxes": 0 if is_masked else boxes,
            "box_prods": 0 if is_masked else box_prods,
            "scanned_prods": 0 if is_masked else scanned_prods,
            "manual_prods": 0 if is_masked else manual_prods,
            "manual_reason": None if is_masked else manual_reason,
            "total_verified": 0 if is_masked else tot,
            "difference": it.quantity if is_masked else diff,
            "status": "pending" if is_masked else item_status,
            "split_number": split_obj.split_number if split_obj else None,
            "split_code": (split_obj.split_code if split_obj and split_obj.split_code else (f"{order.order_id}-{split_obj.split_number}" if split_obj else None)),
            "verified_by": None if is_masked else verified_by,
            "verified_by_name": None if is_masked else ((verifier_obj.full_name or verifier_obj.username) if verifier_obj else None),
            "verified_at": None if is_masked else verified_at,
            "admin_edited_by": admin_edited_by,
            "admin_edited_by_name": admin_edited_by_name,
            "admin_edited_at": admin_edited_at,
            "final_price": it.final_price if show_final_price and not is_masked else None,
            "base_price": it.base_price if show_base_price and not is_masked else None,
            "is_blind_masked": is_masked,
            "checker_boxes": 0 if is_masked else checker_boxes,
            "checker_box_prods": 0 if is_masked else checker_box_prods,
            "checker_scanned_prods": 0 if is_masked else checker_scanned_prods,
            "checker_manual_prods": 0 if is_masked else checker_manual_prods,
            "checker_manual_reason": None if is_masked else checker_manual_reason,
            "checker_verified_at": None if is_masked else checker_verified_at,
            "checker_total_verified": 0 if is_masked else checker_total_verified,
            "checker_difference": it.quantity if is_masked else max(0, it.quantity - checker_total_verified),
            "has_forensic_discrepancy": False if (is_masked or not show_forensic_note) else has_forensic_discrepancy,
            "discrepancy_note": None if (is_masked or not show_forensic_note) else discrepancy_note
        })

    sender_name = None
    if order.warehouse_sender:
        sender_name = order.warehouse_sender.full_name or order.warehouse_sender.username

    security_seals = [b.security_seal_folio for b in (order.splits or []) if b.security_seal_folio]

    formatted_splits = []
    for b in (order.splits or []):
        is_masked = bool(is_warehouse_operator and is_blind_mode and (b.split_id not in my_split_ids))
        b_items = [it for it in (order.items or []) if any(wi.split_id == b.split_id for wi in (it.warehouse_items or []))]

        formatted_items = []
        for it in b_items:
            ful = next((wi for wi in (it.warehouse_items or []) if wi.split_id == b.split_id), None)
            boxes = ful.picked_boxes if ful else 0
            box_prods = ful.picked_box_prods if ful else 0
            scanned_prods = ful.picked_scanned_qty if ful else 0
            manual_prods = ful.picked_manual_qty if ful else 0
            manual_reason = ful.picked_manual_reason if ful else None
            item_status = ful.status if ful else "pending"
            verified_by = ful.picked_by if ful else None
            verifier_obj = ful.picker if ful else None
            verified_at = ful.picked_at if ful else None
            checker_boxes = ful.checked_boxes if ful else 0
            checker_box_prods = ful.checked_box_prods if ful else 0
            checker_scanned_prods = ful.checked_scanned_qty if ful else 0
            checker_manual_prods = ful.checked_manual_qty if ful else 0
            checker_manual_reason = ful.checked_manual_reason if ful else None
            checker_verified_at = ful.checked_at if ful else None
            admin_edited_by = ful.admin_override_by if (ful and is_admin) else None
            admin_edited_by_name = (ful.admin_editor.full_name or ful.admin_editor.username) if (ful and ful.admin_editor and is_admin) else None
            admin_edited_at = ful.admin_override_at if (ful and is_admin) else None

            tot = (box_prods or 0) + (scanned_prods or 0) + (manual_prods or 0)
            checker_total_verified = (checker_box_prods or 0) + (checker_scanned_prods or 0) + (checker_manual_prods or 0)
            is_checker_fully = checker_total_verified >= it.quantity
            is_confidence_val = bool(checker_manual_reason and "Confianza" in checker_manual_reason)

            has_forensic_discrepancy = False
            discrepancy_note = None

            if checker_total_verified > 0 and not is_confidence_val:
                diff_tot = (tot != checker_total_verified)
                diff_bx = ((boxes or 0) != (checker_boxes or 0))
                diff_bx_p = ((box_prods or 0) != (checker_box_prods or 0))
                diff_scn = ((scanned_prods or 0) != (checker_scanned_prods or 0))
                diff_man = ((manual_prods or 0) != (checker_manual_prods or 0))

                if diff_tot:
                    has_forensic_discrepancy = True
                    discrepancy_note = f"Discrepancia en total: 1er filtro={tot} pzs vs 2do filtro={checker_total_verified} pzs"
                elif diff_bx or diff_bx_p or diff_scn or diff_man:
                    has_forensic_discrepancy = True
                    disc_parts_1st = []
                    disc_parts_2nd = []
                    if box_prods > 0 or checker_box_prods > 0:
                        disc_parts_1st.append(f"{boxes} cjas ({box_prods} pz)")
                        disc_parts_2nd.append(f"{checker_boxes} cjas ({checker_box_prods} pz)")
                    if scanned_prods > 0 or checker_scanned_prods > 0:
                        disc_parts_1st.append(f"{scanned_prods} lsr")
                        disc_parts_2nd.append(f"{checker_scanned_prods} lsr")
                    if manual_prods > 0 or checker_manual_prods > 0:
                        disc_parts_1st.append(f"{manual_prods} man")
                        disc_parts_2nd.append(f"{checker_manual_prods} man")

                    str_1st = " + ".join(disc_parts_1st) if disc_parts_1st else f"{tot} pzs"
                    str_2nd = " + ".join(disc_parts_2nd) if disc_parts_2nd else f"{checker_total_verified} pzs"
                    discrepancy_note = f"Discrepancia de empaque: Surtidor [{str_1st}] vs Revisor [{str_2nd}]"

            if not is_masked:
                formatted_items.append({
                    "warehouse_item_id": ful.warehouse_item_id if ful else None,
                    "split_id": b.split_id,
                    "order_item_id": it.order_item_id,
                    "order_id": it.order_id,
                    "product_id": it.product_id,
                    "product_name": it.product.name if it.product else "",
                    "codebar": it.product.codebar if it.product else None,
                    "barcode": it.product.codebar if it.product else None,
                    "location": it.product.location if it.product else "",
                    "image_url": it.product.image_url if it.product else None,
                    "container_id": ful.container_id if ful else None,
                    "container_qr": ful.container_qr if ful else None,
                    "quantity": it.quantity,
                    "quantity_required": it.quantity,
                    "required_quantity": it.quantity,
                    "picked_boxes": boxes,
                    "picked_box_prods": box_prods,
                    "picked_scanned_qty": scanned_prods,
                    "picked_manual_qty": manual_prods,
                    "picked_manual_reason": manual_reason,
                    "picked_total_qty": tot,
                    "picked_by": verified_by,
                    "picked_by_name": (verifier_obj.full_name or verifier_obj.username) if verifier_obj else None,
                    "picked_at": verified_at,
                    "boxes": boxes,
                    "box_prods": box_prods,
                    "scanned_prods": scanned_prods,
                    "manual_prods": manual_prods,
                    "verified_by_box_count": box_prods,
                    "verified_by_scan_count": scanned_prods,
                    "verified_by_manual_count": manual_prods,
                    "manual_reason": manual_reason,
                    "total_verified": tot,
                    "remaining_quantity": max(0, it.quantity - tot),
                    "item_status": item_status,
                    "verified_by": verified_by,
                    "verified_by_name": (verifier_obj.full_name or verifier_obj.username) if verifier_obj else None,
                    "verified_at": verified_at,
                    "admin_edited_by": admin_edited_by,
                    "admin_edited_by_name": admin_edited_by_name,
                    "admin_edited_at": admin_edited_at,
                    "final_price": it.final_price if show_final_price else None,
                    "base_price": it.base_price if show_base_price else None,
                    "checked_boxes": checker_boxes,
                    "checked_box_prods": checker_box_prods,
                    "checked_scanned_qty": checker_scanned_prods,
                    "checked_manual_qty": checker_manual_prods,
                    "checked_manual_reason": checker_manual_reason,
                    "checked_total_qty": checker_total_verified,
                    "checked_by": ful.checked_by if ful else None,
                    "checked_by_name": (ful.checker.full_name or ful.checker.username) if (ful and ful.checker) else None,
                    "checked_at": checker_verified_at,
                    "checker_boxes": checker_boxes,
                    "checker_box_prods": checker_box_prods,
                    "checker_scanned_prods": checker_scanned_prods,
                    "checker_manual_prods": checker_manual_prods,
                    "checker_manual_reason": checker_manual_reason,
                    "checker_verified_at": checker_verified_at,
                    "checker_total_verified": checker_total_verified,
                    "is_checker_fully_verified": is_checker_fully,
                    "has_forensic_discrepancy": False if (is_warehouse_operator or not can_audit) else has_forensic_discrepancy,
                    "discrepancy_note": None if (is_warehouse_operator or not can_audit) else discrepancy_note
                })

        b_admin_edited_by = b.admin_override_by if is_admin else None
        b_admin_edited_by_name = (b.admin_editor.full_name or b.admin_editor.username) if (b.admin_editor and is_admin) else None
        b_admin_edited_at = b.admin_override_at if is_admin else None

        raw_containers = getattr(b, "containers", []) or []
        containers_list = [
            {
                "container_id": c.container_id,
                "qr_code": c.qr_code,
                "status": c.status,
                "current_split_id": c.current_split_id,
                "current_user_id": c.current_user_id
            }
            for c in raw_containers
        ]
        uses_containers_val = bool(
            getattr(b, "uses_containers", False)
            or len(raw_containers) > 0
            or getattr(b, "active_container_id", None)
        )

        containers_summary_list = []
        if uses_containers_val:
            grouped = {}
            for c in raw_containers:
                grouped[c.container_id] = {
                    "container_id": c.container_id,
                    "qr_code": c.qr_code,
                    "status": c.status,
                    "total_pieces": 0,
                    "total_products": 0,
                    "items": []
                }
            for ci in (getattr(b, "container_items", None) or []):
                cid = ci.container_id
                if cid not in grouped:
                    c_qr = ci.container.qr_code if ci.container else (ci.container_qr or f"Canasta #{cid}")
                    c_status = ci.container.status if ci.container else "in_use"
                    grouped[cid] = {
                        "container_id": cid,
                        "qr_code": c_qr,
                        "status": c_status,
                        "total_pieces": 0,
                        "total_products": 0,
                        "items": []
                    }
                tot_p = ci.picked_total_qty or 0
                grouped[cid]["total_pieces"] += tot_p
                grouped[cid]["total_products"] += 1
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
            containers_summary_list = list(grouped.values())

        formatted_splits.append({
            "split_id": b.split_id,
            "order_id": b.order_id,
            "split_number": b.split_number,
            "split_code": b.split_code or f"{b.order_id}-{b.split_number}",
            "split_index": b.split_number,
            "total_splits": b.total_splits,
            "total_splits_in_order": b.total_splits,
            "items_count": len(b_items),
            "status": b.status,
            "picker_id": b.picker_id,
            "picker_name": b.picker_name,
            "checker_id": b.checker_id,
            "checker_name": b.checker_name,
            "admin_edited_by": b_admin_edited_by,
            "admin_edited_by_name": b_admin_edited_by_name,
            "admin_edited_at": b_admin_edited_at,
            "customer_name": "[Protegido - Surtido Ciego]" if is_masked else (order.customer_name if order else None),
            "assigned_user_name": None if is_masked else (order.assigned_user_name if order else None),
            "seller_name": None if is_masked else (order.assigned_user_name if order else None),
            "security_seal_folio": b.security_seal_folio,
            "started_at": b.started_at,
            "completed_at": b.completed_at,
            "checking_started_at": b.checking_started_at,
            "audited_at": b.completed_at,
            "duration_seconds": b.duration_seconds,
            "duration_formatted": b.duration_formatted,
            "checking_duration_seconds": b.checking_duration_seconds,
            "checking_duration_formatted": b.checking_duration_formatted,
            "uses_containers": uses_containers_val,
            "containers": containers_list,
            "containers_count": len(containers_list),
            "containers_summary": containers_summary_list,
            "active_container_id": getattr(b, "active_container_id", None),
            "active_container_qr": getattr(b, "active_container_qr", None),
            "items": formatted_items,
            "is_blind_masked": is_masked,
            "blind_notice": "Partidas protegidas por modo Surtido Ciego" if is_masked else None,
            "total_items": len(b_items)
        })

    total_forensic_items = len(forensic_items)
    paged_forensic_items = forensic_items[skip : skip + limit]

    return {
        "order_id": order.order_id,
        "warehouse_status": order.warehouse_status,
        "audit_verdict": order.audit_verdict if can_audit else "clean",
        "warehouse_show_details": order.warehouse_show_details or False,
        "total_splits": order.total_splits or 1,
        "warehouse_sent_at": order.warehouse_sent_at,
        "sent_to_warehouse_at": order.warehouse_sent_at,
        "warehouse_sent_by_name": sender_name,
        "all_items_verified": all_verified,
        "total_ordered_items": total_ordered,
        "total_verified_items": total_verified_sum,
        "security_seals": security_seals,
        "splits": formatted_splits,
        "forensic_items": paged_forensic_items,
        "total_forensic_items": total_forensic_items,
        "skip": skip,
        "limit": limit
    }


""" Metricas operativas de bodega en tiempo real """
def get_warehouse_stats(db: Session, current_user: Optional[User] = None) -> Dict[str, Any]:
    try:
        from zoneinfo import ZoneInfo
        MX_TZ = ZoneInfo("America/Mexico_City")
    except Exception:
        try:
            import pytz
            MX_TZ = pytz.timezone("America/Mexico_City")
        except Exception:
            MX_TZ = timezone.utc

    now_local = datetime.now(MX_TZ)
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = today_start_local.astimezone(timezone.utc)

    base_orders_query = db.query(Order).filter(Order.sent_to_warehouse == True)
    base_splits_query = db.query(WarehouseSplit).join(Order, WarehouseSplit.order_id == Order.order_id).filter(Order.sent_to_warehouse == True)

    is_admin = bool(current_user and (getattr(current_user, "role_slug", None) == "admin" or getattr(current_user, "role", None) == "admin" or (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("warehouse.audit")))))
    has_warehouse_perm = bool(current_user and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.view") or current_user.has_permission("warehouse.operator") or current_user.has_permission("warehouse.supervisor") or current_user.has_permission("warehouse.audit") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.pack") or current_user.has_permission("warehouse.check")))

    if current_user and not is_admin and not has_warehouse_perm:
        from crud.crud_commercial_group import get_user_groups
        from db.base import CustomerInfo

        user_group_ids = get_user_groups(db, current_user.user_id)
        if not user_group_ids:
            base_orders_query = base_orders_query.filter(Order.assigned_user_id == current_user.user_id)
            base_splits_query = base_splits_query.filter(Order.assigned_user_id == current_user.user_id)
        else:
            base_orders_query = base_orders_query.join(
                CustomerInfo, Order.customer_id == CustomerInfo.customer_id
            ).filter(
                or_(
                    CustomerInfo.sales_group_id.in_(user_group_ids),
                    Order.assigned_user_id == current_user.user_id
                )
            )
            base_splits_query = base_splits_query.join(
                CustomerInfo, Order.customer_id == CustomerInfo.customer_id
            ).filter(
                or_(
                    CustomerInfo.sales_group_id.in_(user_group_ids),
                    Order.assigned_user_id == current_user.user_id
                )
            )

    orders_pending = base_orders_query.filter(
        Order.warehouse_status == "pending"
    ).with_entities(func.count(Order.order_id)).scalar() or 0

    orders_in_prog = base_orders_query.filter(
        Order.warehouse_status.in_(["in_progress_partial", "in_progress_full", "checking", "ready_for_check"])
    ).with_entities(func.count(Order.order_id)).scalar() or 0

    orders_completed = base_orders_query.join(Order.splits).filter(
        Order.warehouse_status.in_(["completed", "splits_completed"]),
        WarehouseSplit.completed_at >= today_start
    ).with_entities(func.count(func.distinct(Order.order_id))).scalar() or 0

    active_splits = base_splits_query.filter(
        WarehouseSplit.status.in_(["pending", "picking", "in_progress", "ready_for_check", "checking"])
    ).with_entities(func.count(WarehouseSplit.split_id)).scalar() or 0

    completed_splits = base_splits_query.filter(
        WarehouseSplit.status == "completed",
        WarehouseSplit.completed_at >= today_start
    ).with_entities(func.count(WarehouseSplit.split_id)).scalar() or 0

    return {
        "pending_orders": orders_pending + orders_in_prog,
        "orders_pending_queue": orders_pending,
        "orders_in_progress": orders_in_prog,
        "completed_orders_today": orders_completed,
        "orders_completed_today": orders_completed,
        "active_splits": active_splits,
        "active_splits_in_floor": active_splits,
        "completed_splits_today": completed_splits
    }


""" Actualizar justificacion de verificacion manual """
def update_order_item_manual_reason(
    db: Session,
    order_item_id: UUID,
    manual_reason: str,
    current_user: User
) -> OrderItem:
    item = db.query(OrderItem).options(
        joinedload(OrderItem.order)
    ).filter(OrderItem.order_item_id == order_item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida no encontrada"
        )

    ful = db.query(WarehouseItem).options(
        joinedload(WarehouseItem.split)
    ).filter(WarehouseItem.order_item_id == order_item_id).first()
    split = ful.split if ful else None

    is_admin = bool(current_user and (getattr(current_user, "role_slug", None) == "admin" or getattr(current_user, "role", None) == "admin" or (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("warehouse.audit") or current_user.has_permission("warehouse.manage")))))
    can_supervise = bool(current_user and hasattr(current_user, "has_permission") and (current_user.has_permission("warehouse.supervisor") or current_user.has_permission("orders.approve") or current_user.has_permission("warehouse.manage") or current_user.has_permission("warehouse.audit")))

    if not is_admin:
        if split:
            if split.status in ["completed", "ready_for_check", "checking"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No es posible modificar la justificación: la fase de surtido o el split ya han concluido. Solo un Administrador o Auditor de Bodega puede realizar modificaciones forenses en este estado."
                )
        elif item.order and item.order.warehouse_status in ["completed"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No es posible modificar la justificación: el pedido en bodega ya se encuentra completado/sellado."
            )

        if not can_supervise and item.order:
            from crud.crud_commercial_group import user_can_manage_order
            can_manage = user_can_manage_order(db, current_user.user_id, item.order.customer_id, getattr(current_user, "role", None))
            is_assigned = (item.order.assigned_user_id == current_user.user_id)
            if not can_manage and not is_assigned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para modificar notas de pedidos fuera de tus grupos o asignación"
                )

    if not ful:
        split_obj = db.query(WarehouseSplit).filter(WarehouseSplit.order_id == item.order_id).first()
        if split_obj:
            ful = WarehouseItem(
                split_id=split_obj.split_id,
                order_item_id=item.order_item_id,
                product_id=item.product_id,
                required_quantity=item.quantity
            )
            db.add(ful)

    if ful:
        ful.picked_manual_reason = manual_reason.strip() if manual_reason else None
    db.commit()
    db.refresh(item)
    return item


""" Acciones exclusivas de administrador sobre splits """
def admin_override_split(
    db: Session,
    split_id: UUID,
    status_override: Optional[str] = None,
    security_seal_folio: Optional[str] = None,
    clear_seal: bool = False,
    admin_user: Optional[User] = None
) -> WarehouseSplit:
    from crud.crud_warehouse_operations import _get_split_model
    split = _get_split_model(db, split_id)
    now = datetime.now(timezone.utc)

    if clear_seal:
        split.security_seal_folio = None

    if security_seal_folio is not None:
        split.security_seal_folio = security_seal_folio.strip() if security_seal_folio.strip() else None

    if status_override:
        valid_statuses = ["pending", "picking", "in_progress", "ready_for_check", "checking", "completed"]
        if status_override not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estatus invalido. Valores permitidos: {', '.join(valid_statuses)}"
            )
        if status_override == "in_progress":
            status_override = "picking"
        old_status = split.status
        split.status = status_override
        if status_override == "completed":
            if not split.completed_at:
                split.completed_at = now
        elif status_override in ["pending", "picking", "in_progress"]:
            split.completed_at = None
            split.checking_started_at = None
            if status_override == "pending":
                split.picker_id = None
                split.started_at = None

            # Resetear a 0 cualquier partida que tenga más piezas verificadas que lo requerido en el pedido
            for f in (split.warehouse_items or []):
                it = f.order_item
                req_qty = it.quantity if it else 0
                tot_1st = (f.picked_box_prods or 0) + (f.picked_scanned_qty or 0) + (f.picked_manual_qty or 0)
                if tot_1st > req_qty:
                    f.picked_boxes = 0
                    f.picked_box_prods = 0
                    f.picked_scanned_qty = 0
                    f.picked_manual_qty = 0
                    f.picked_manual_reason = None
                    f.picked_at = None
                    f.picked_by = None
                    f.status = "pending"
                tot_2nd = (f.checked_box_prods or 0) + (f.checked_scanned_qty or 0) + (f.checked_manual_qty or 0)
                if tot_2nd > req_qty:
                    f.checked_boxes = 0
                    f.checked_box_prods = 0
                    f.checked_scanned_qty = 0
                    f.checked_manual_qty = 0
                    f.checked_manual_reason = None
                    f.checked_at = None

        elif status_override in ["ready_for_check", "checking"]:
            split.completed_at = None
            if status_override == "ready_for_check":
                split.checker_id = None
                split.checking_started_at = None

            # En 2do filtro, si lo revisado superaba el requerimiento, resetear el 2do filtro a 0
            for f in (split.warehouse_items or []):
                it = f.order_item
                req_qty = it.quantity if it else 0
                tot_2nd = (f.checked_box_prods or 0) + (f.checked_scanned_qty or 0) + (f.checked_manual_qty or 0)
                if tot_2nd > req_qty:
                    f.checked_boxes = 0
                    f.checked_box_prods = 0
                    f.checked_scanned_qty = 0
                    f.checked_manual_qty = 0
                    f.checked_manual_reason = None
                    f.checked_at = None
                    f.checker_boxes = 0
                    f.checker_box_prods = 0
                    f.checker_scanned_prods = 0
                    f.checker_manual_prods = 0
                    f.checker_manual_reason = None
                    f.checker_verified_at = None

    if admin_user:
        split.admin_override_by = admin_user.user_id
        split.admin_override_at = now

    _recalculate_order_warehouse_status(db, split.order)
    db.commit()
    db.refresh(split)
    return split


""" Accion pericial exclusiva de administrador para ajustar conteos en 1er y 2do filtro """
def admin_override_order_item_counts(
    db: Session,
    order_item_id: UUID,
    scanned_prods: Optional[int] = None,
    boxes: Optional[int] = None,
    box_prods: Optional[int] = None,
    manual_prods: Optional[int] = None,
    manual_reason: Optional[str] = None,
    checker_scanned_prods: Optional[int] = None,
    checker_boxes: Optional[int] = None,
    checker_box_prods: Optional[int] = None,
    checker_manual_prods: Optional[int] = None,
    checker_manual_reason: Optional[str] = None,
    admin_user: User = None
) -> OrderItem:
    item = db.query(OrderItem).options(
        joinedload(OrderItem.order)
    ).filter(OrderItem.order_item_id == order_item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida no encontrada"
        )

    ful = db.query(WarehouseItem).options(
        joinedload(WarehouseItem.split)
    ).filter(WarehouseItem.order_item_id == order_item_id).first()

    if not ful:
        split_obj = db.query(WarehouseSplit).filter(WarehouseSplit.order_id == item.order_id).first()
        if split_obj:
            ful = WarehouseItem(
                split_id=split_obj.split_id,
                order_item_id=item.order_item_id,
                product_id=item.product_id,
                required_quantity=item.quantity
            )
            db.add(ful)

    now = datetime.now(timezone.utc)

    # 1er Filtro (Surtidor de piso)
    if scanned_prods is not None:
        ful.picked_scanned_qty = max(0, scanned_prods)
    if boxes is not None:
        ful.picked_boxes = max(0, boxes)
    if box_prods is not None:
        ful.picked_box_prods = max(0, box_prods)
    elif boxes is not None and (ful.picked_boxes or 0) == 0:
        ful.picked_box_prods = 0
    if (ful.picked_boxes or 0) == 0:
        ful.picked_box_prods = 0
    if manual_prods is not None:
        ful.picked_manual_qty = max(0, manual_prods)
    if manual_reason is not None:
        ful.picked_manual_reason = manual_reason.strip() if manual_reason.strip() else None

    tot_1st = (ful.picked_box_prods or 0) + (ful.picked_scanned_qty or 0) + (ful.picked_manual_qty or 0)
    if tot_1st > item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exceso en 1er filtro: el total ({tot_1st} pzs) no puede superar la cantidad requerida del pedido ({item.quantity} pzs)"
        )

    if tot_1st > 0:
        if not ful.picked_at:
            ful.picked_at = now
        if not ful.picked_by and admin_user:
            ful.picked_by = admin_user.user_id
        ful.status = "completed" if tot_1st >= item.quantity else "partial"
    else:
        ful.status = "pending"

    # 2do Filtro (Revisor / Checker)
    if checker_scanned_prods is not None:
        ful.checked_scanned_qty = max(0, checker_scanned_prods)
    if checker_boxes is not None:
        ful.checked_boxes = max(0, checker_boxes)
    if checker_box_prods is not None:
        ful.checked_box_prods = max(0, checker_box_prods)
    elif checker_boxes is not None and (ful.checked_boxes or 0) == 0:
        ful.checked_box_prods = 0
    if (ful.checked_boxes or 0) == 0:
        ful.checked_box_prods = 0
    if checker_manual_prods is not None:
        ful.checked_manual_qty = max(0, checker_manual_prods)
    if checker_manual_reason is not None:
        ful.checked_manual_reason = checker_manual_reason.strip() if checker_manual_reason.strip() else None

    tot_2nd = (ful.checked_box_prods or 0) + (ful.checked_scanned_qty or 0) + (ful.checked_manual_qty or 0)
    if tot_2nd > item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exceso en 2do filtro: el total de revisión ({tot_2nd} pzs) no puede superar la cantidad requerida del pedido ({item.quantity} pzs)"
        )
    if tot_2nd > 0:
        if not ful.checked_at:
            ful.checked_at = now

    if admin_user:
        ful.admin_override_by = admin_user.user_id
        ful.admin_override_at = now

    if ful.split:
        _recalculate_order_warehouse_status(db, item.order)

    db.commit()
    db.refresh(item)
    return item
