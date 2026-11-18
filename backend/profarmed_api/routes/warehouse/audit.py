"""
Routes para Auditoría Forense, Bitácora de Canastas y Overrides Administrativos (Audit & Forensics)

Proporciona herramientas de control de calidad, trazabilidad y supervisión en almacén:
- Resumen consolidado y desglose de canastas físicas vinculadas a un split.
- Bitácora atómica de escaneos láser e historial de eventos de fulfillment (Event Ledger).
- Auditoría profunda por pedido con análisis de discrepancias entre surtidor y revisor.
- Actualización de motivos de validación manual para aclaraciones operativas.
- Rectificaciones administrativas de emergencia (Admin Overrides de status, sellos y conteos físicos).

ENDPOINTS:
- GET /splits/{id}/containers-summary - Resumen de canastas y piezas por tote (requiere 'warehouse.view')
- GET /splits/{id}/container-items - Desglose de partidas por canasta (requiere 'warehouse.view')
- GET /splits/{id}/events - Bitácora atómica de eventos láser (requiere 'warehouse.audit' o 'warehouse.events')
- GET /orders/{id}/audit-breakdown - Auditoría completa de pedido y partidas (requiere 'warehouse.audit')
- PATCH /order-items/{id}/manual-reason - Actualizar justificación de conteo manual (requiere 'warehouse.audit')
- PATCH /splits/{id}/admin-override - Rectificación forzada de status o sello de split (requiere 'warehouse.manage')
- PATCH /order-items/{id}/admin-override-counts - Corrección forzada de piezas de 1er/2do filtro (requiere 'warehouse.manage')

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from db.base import User, Order
from dependencies import get_db, require_permission
from crud.crud_commercial_group import user_can_manage_order
from crud.crud_warehouse import (
    get_split_containers_summary,
    get_split_container_items,
    get_order_warehouse_audit,
    update_order_item_manual_reason,
    admin_override_split,
    admin_override_order_item_counts,
)
from schemas.warehouse import (
    WarehouseContainerSummaryBreakdown,
    WarehouseContainerItemResponse,
    WarehouseAuditOrderResponse,
    WarehouseUpdateManualReasonRequest,
    WarehouseAdminSplitOverrideRequest,
    WarehouseAdminItemCountsOverrideRequest,
    WarehouseSplitResponse,
    WarehouseSplitItemResponse,
)

router = APIRouter()


# ============================================================================
# AUDITORÍA DE CANASTAS Y BITÁCORA ATÓMICA DE EVENTOS (EVENT LEDGER)
# ============================================================================

""" GET /splits/{split_id}/containers-summary - Resumen consolidado de canastas físicas por lote """
@router.get(
    "/splits/{split_id}/containers-summary",
    response_model=List[WarehouseContainerSummaryBreakdown]
)
def get_split_containers_summary_route(
    split_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.operator", "warehouse.checker", "warehouse.audit", "warehouse.manage", "system.admin"))
):
    """
    Agrupa los productos recolectados en el split por canasta física QR, indicando
    la cantidad total de piezas y tipos de productos depositados en cada tote.
    """
    return get_split_containers_summary(db=db, split_id=split_id)


""" GET /splits/{split_id}/container-items - Desglose de partidas depositadas por canasta """
@router.get(
    "/splits/{split_id}/container-items",
    response_model=List[WarehouseContainerItemResponse]
)
def get_split_container_items_route(
    split_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.operator", "warehouse.checker", "warehouse.audit", "warehouse.manage", "system.admin"))
):
    """
    Lista detallada de cada ítem asignado a las canastas del split, desglosando piezas
    escaneadas por láser, cajas maestras y conteo manual.
    """
    items = get_split_container_items(db=db, split_id=split_id)
    return [
        WarehouseContainerItemResponse(
            container_item_id=ci.container_item_id,
            split_id=ci.split_id,
            container_id=ci.container_id,
            container_qr=ci.container_qr,
            warehouse_item_id=ci.warehouse_item_id,
            order_item_id=ci.order_item_id,
            product_id=ci.product_id,
            product_name=ci.product_name,
            barcode=ci.product.codebar if ci.product else None,
            picked_scanned_qty=ci.picked_scanned_qty,
            picked_boxes=ci.picked_boxes,
            picked_box_prods=ci.picked_box_prods,
            picked_manual_qty=ci.picked_manual_qty,
            picked_total_qty=ci.picked_total_qty,
            checked_scanned_qty=ci.checked_scanned_qty,
            checked_boxes=ci.checked_boxes,
            checked_box_prods=ci.checked_box_prods,
            checked_manual_qty=ci.checked_manual_qty,
            checked_total_qty=ci.checked_total_qty,
            updated_at=ci.updated_at
        ) for ci in items
    ]


""" GET /splits/{split_id}/events - Bitácora atómica de eventos láser para peritaje forense """
@router.get(
    "/splits/{split_id}/events",
    response_model=List[WarehouseContainerItemResponse]
)
def get_split_events_route(
    split_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.audit", "warehouse.events", "warehouse.manage", "system.admin"))
):
    """
    Proporciona la pista de auditoría inmutable de cada escaneo láser, caja registrada
    o intervención manual, permitiendo reconstruir exactamente quién pistoleó qué pieza y cuándo.
    """
    items = get_split_container_items(db=db, split_id=split_id)
    return [
        WarehouseContainerItemResponse(
            container_item_id=ci.container_item_id,
            split_id=ci.split_id,
            container_id=ci.container_id,
            container_qr=ci.container_qr,
            warehouse_item_id=ci.warehouse_item_id,
            order_item_id=ci.order_item_id,
            product_id=ci.product_id,
            product_name=ci.product_name,
            barcode=ci.product.codebar if ci.product else None,
            picked_scanned_qty=ci.picked_scanned_qty,
            picked_boxes=ci.picked_boxes,
            picked_box_prods=ci.picked_box_prods,
            picked_manual_qty=ci.picked_manual_qty,
            picked_total_qty=ci.picked_total_qty,
            checked_scanned_qty=ci.checked_scanned_qty,
            checked_boxes=ci.checked_boxes,
            checked_box_prods=ci.checked_box_prods,
            checked_manual_qty=ci.checked_manual_qty,
            checked_total_qty=ci.checked_total_qty,
            updated_at=ci.updated_at
        ) for ci in items
    ]


# ============================================================================
# AUDITORÍA DE PEDIDO Y DESGLOSE FORENSE
# ============================================================================

""" GET /orders/{order_id}/audit-breakdown - Desglose comparativo de piezas por partida de pedido """
@router.get(
    "/orders/{order_id}/audit-breakdown",
    response_model=WarehouseAuditOrderResponse
)
def get_order_audit_breakdown_route(
    order_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.audit", "warehouse.view", "system.admin"))
):
    """
    Auditoría exhaustiva a nivel de pedido completo:
    - Compara cantidad requerida vs piezas pistoleadas en piso (1er filtro) vs piezas revisadas (2do filtro).
    - Detecta discrepancias forenses positivas (+pz sobrantes) o negativas (-pz faltantes).
    - Desglosa motivos manuales y precintos de seguridad aplicados a cada split.
    """
    return get_order_warehouse_audit(
        db=db,
        order_id=order_id,
        skip=skip,
        limit=limit,
        current_user=current_user
    )


""" PATCH /order-items/{order_item_id}/manual-reason - Actualizar justificación de conteo manual """
@router.patch("/order-items/{order_item_id}/manual-reason")
def update_order_item_manual_reason_route(
    order_item_id: UUID,
    payload: WarehouseUpdateManualReasonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.audit", "warehouse.manage", "warehouse.operator", "warehouse.checker", "system.admin"))
):
    """
    Permite rectificar o complementar el motivo documentado de un escaneo manual
    en una partida (ej: reclasificar de 'Rapidez operativa' a 'Código de barras deteriorado').
    """
    item = update_order_item_manual_reason(
        db=db,
        order_item_id=order_item_id,
        manual_reason=payload.manual_reason,
        current_user=current_user
    )
    return {
        "success": True,
        "order_item_id": item.order_item_id,
        "manual_reason": item.manual_reason
    }


# ============================================================================
# RECTIFICACIONES Y OVERRIDES ADMINISTRATIVOS
# ============================================================================

""" PATCH /splits/{split_id}/admin-override - Override administrativo de estado y precinto del lote """
@router.patch(
    "/splits/{split_id}/admin-override",
    response_model=WarehouseSplitResponse
)
def admin_override_split_route(
    split_id: UUID,
    payload: WarehouseAdminSplitOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.manage", "system.admin"))
):
    """
    Intervención administrativa de nivel gerencial sobre un lote:
    - Permite forzar el status a cualquier etapa del ciclo de vida.
    - Permite sobreescribir o limpiar el folio del precinto de seguridad.
    """
    return admin_override_split(
        db=db,
        split_id=split_id,
        status_override=payload.status,
        security_seal_folio=payload.security_seal_folio,
        clear_seal=payload.clear_seal,
        admin_user=current_user
    )


""" PATCH /order-items/{order_item_id}/admin-override-counts - Corrección forzada de conteos de mercancía """
@router.patch(
    "/order-items/{order_item_id}/admin-override-counts",
    response_model=WarehouseSplitItemResponse
)
def admin_override_item_counts_route(
    order_item_id: UUID,
    payload: WarehouseAdminItemCountsOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.manage", "system.admin"))
):
    """
    Permite al Gerente de Almacén o Administrador corregir directamente el conteo físico
    de piezas pistoleadas, cajas o manuales tanto de 1er como de 2do filtro.
    
    Recalcula automáticamente los totales y revalúa el veredicto forense de discrepancia.
    """
    item = admin_override_order_item_counts(
        db=db,
        order_item_id=order_item_id,
        scanned_prods=payload.scanned_prods,
        boxes=payload.boxes,
        box_prods=payload.box_prods,
        manual_prods=payload.manual_prods,
        manual_reason=payload.manual_reason,
        checker_scanned_prods=payload.checker_scanned_prods,
        checker_boxes=payload.checker_boxes,
        checker_box_prods=payload.checker_box_prods,
        checker_manual_prods=payload.checker_manual_prods,
        checker_manual_reason=payload.checker_manual_reason,
        admin_user=current_user
    )

    ful = item.warehouse_items[0] if item.warehouse_items else None
    tot = (ful.picked_box_prods or 0) + (ful.picked_scanned_qty or 0) + (ful.picked_manual_qty or 0) if ful else 0
    checker_tot = (ful.checked_box_prods or 0) + (ful.checked_scanned_qty or 0) + (ful.checked_manual_qty or 0) if ful else 0
    return {
        "order_item_id": item.order_item_id,
        "order_id": item.order_id,
        "product_id": item.product_id,
        "product_name": item.product.name if item.product else "",
        "codebar": item.product.codebar if item.product else None,
        "barcode": item.product.codebar if item.product else None,
        "location": item.product.location if item.product else "",
        "quantity": item.quantity,
        "quantity_required": item.quantity,
        "picked_boxes": ful.picked_boxes if ful else 0,
        "picked_box_prods": ful.picked_box_prods if ful else 0,
        "picked_scanned_qty": ful.picked_scanned_qty if ful else 0,
        "picked_manual_qty": ful.picked_manual_qty if ful else 0,
        "picked_manual_reason": ful.picked_manual_reason if ful else None,
        "picked_total_qty": tot,
        "boxes": ful.picked_boxes if ful else 0,
        "box_prods": ful.picked_box_prods if ful else 0,
        "scanned_prods": ful.picked_scanned_qty if ful else 0,
        "manual_prods": ful.picked_manual_qty if ful else 0,
        "verified_by_box_count": ful.picked_box_prods if ful else 0,
        "verified_by_scan_count": ful.picked_scanned_qty if ful else 0,
        "verified_by_manual_count": ful.picked_manual_qty if ful else 0,
        "manual_reason": ful.picked_manual_reason if ful else None,
        "total_verified": tot,
        "remaining_quantity": max(0, item.quantity - tot),
        "status": ful.status if ful else "pending",
        "item_status": ful.status if ful else "pending",
        "picked_by": ful.picked_by if ful else None,
        "picked_at": ful.picked_at if ful else None,
        "verified_by": ful.picked_by if ful else None,
        "verified_by_name": ful.picker_name if ful else None,
        "verified_at": ful.picked_at if ful else None,
        "final_price": item.final_price,
        "base_price": item.base_price,
        "checked_boxes": ful.checked_boxes if ful else 0,
        "checked_box_prods": ful.checked_box_prods if ful else 0,
        "checked_scanned_qty": ful.checked_scanned_qty if ful else 0,
        "checked_manual_qty": ful.checked_manual_qty if ful else 0,
        "checked_manual_reason": ful.checked_manual_reason if ful else None,
        "checked_total_qty": checker_tot,
        "checker_boxes": ful.checked_boxes if ful else 0,
        "checker_box_prods": ful.checked_box_prods if ful else 0,
        "checker_scanned_prods": ful.checked_scanned_qty if ful else 0,
        "checker_manual_prods": ful.checked_manual_qty if ful else 0,
        "checker_manual_reason": ful.checked_manual_reason if ful else None,
        "checker_verified_at": ful.checked_at if ful else None,
        "checker_total_verified": checker_tot,
        "is_checker_fully_verified": (checker_tot >= item.quantity) if ful else False,
        "has_forensic_discrepancy": (checker_tot != tot) if (ful and (ful.checked_at or checker_tot > 0 or ful.checked_manual_reason)) else False,
        "discrepancy_note": f"Diferencia de {('+' if (checker_tot - tot) > 0 else '')}{checker_tot - tot} pz entre Surtidor ({tot}) y Revisor ({checker_tot})" if (ful and (checker_tot != tot) and (ful.checked_at or checker_tot > 0 or ful.checked_manual_reason)) else None
    }
