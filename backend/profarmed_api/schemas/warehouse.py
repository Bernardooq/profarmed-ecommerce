"""
Schemas Pydantic para el Módulo de Almacén / Bodega (Warehouse v2.2)

Arquitectura de Alto Rendimiento:
- Particionamiento lógico/físico de órdenes en Splits concurrentes (warehouse_splits).
- Canastas físicas reutilizables con código QR (warehouse_containers / Totes).
- Partidas granulares desacopladas de orden física (warehouse_items) con recuento nativo.
- Bitácora atómica de eventos en tiempo real Append-Only (warehouse_scan_events).
- Operación láser sin ratón (pistolas lectoras con empaque rápido por cajas y excepciones manuales).
- Auditoría pericial antifraude con separación estricta entre 1er filtro (Picker) y 2do filtro (Checker).
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ============================================================================
# CANASTAS FÍSICAS REUTILIZABLES CON QR (WAREHOUSE CONTAINERS / TOTES)
# ============================================================================

class WarehouseContainerBase(BaseModel):
    """Atributos base de una canasta física de almacén"""
    qr_code: str = Field(..., min_length=1, max_length=50, description="Código QR único de la canasta")
    status: str = Field(default="available", description="available, in_use, damaged, maintenance, retired, unavailable")


class WarehouseContainerCreate(BaseModel):
    """Alta de una nueva canasta QR física en el sistema"""
    qr_code: str = Field(..., min_length=1, max_length=50, description="Código QR o folio grabado en la canasta")


class WarehouseContainerUpdate(BaseModel):
    """Actualización del estado físico de una canasta"""
    status: Optional[str] = Field(None, description="available, in_use, damaged, maintenance, retired, unavailable")


class WarehouseContainerSummary(BaseModel):
    """Vista resumida de una canasta QR para visualización en splits y listas rápidas"""
    container_id: UUID
    qr_code: str
    status: str = "available"
    is_available: bool = True

    model_config = {"from_attributes": True}


class WarehouseContainerResponse(WarehouseContainerSummary):
    """Detalle completo de una canasta física con su asignación actual y trazabilidad"""
    current_split_id: Optional[UUID] = None
    current_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WarehouseBindContainerRequest(BaseModel):
    """Vinculación de una canasta QR a un split activo por parte del surtidor"""
    qr_code: str = Field(..., min_length=1, max_length=50, description="Código QR escaneado de la canasta física")
    split_id: Optional[UUID] = Field(None, description="UUID del split al que se vincula")


class WarehouseReleaseContainerRequest(BaseModel):
    """Liberación de una canasta QR al retornar a la zona de canastas disponibles"""
    qr_code: Optional[str] = Field(None, description="Código QR de la canasta a liberar")
    container_id: Optional[UUID] = Field(None, description="UUID de la canasta a liberar")
    empty_items: Optional[bool] = Field(False, description="Si es True, descuenta y reinicia los escaneos de las partidas en esta canasta para preservar la integridad física")


# ============================================================================
# DISTRIBUCIÓN CONSOLIDADA POR CANASTA FÍSICA (WAREHOUSE CONTAINER ITEMS)
# ============================================================================

class WarehouseContainerItemResponse(BaseModel):
    """Distribución consolidada de un producto depositado en una canasta física QR"""
    container_item_id: UUID
    split_id: UUID
    container_id: UUID
    container_qr: Optional[str] = None
    warehouse_item_id: Optional[UUID] = None
    order_item_id: UUID
    product_id: str
    product_name: Optional[str] = None
    barcode: Optional[str] = None

    # 1er Filtro: Surtido en Piso (Picker)
    picked_scanned_qty: int = 0
    picked_boxes: int = 0
    picked_box_prods: int = 0
    picked_manual_qty: int = 0
    picked_total_qty: int = 0

    # 2do Filtro: Mesa de Control y Revisión (Checker)
    checked_scanned_qty: int = 0
    checked_boxes: int = 0
    checked_box_prods: int = 0
    checked_manual_qty: int = 0
    checked_total_qty: int = 0

    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WarehouseContainerSummaryBreakdown(BaseModel):
    """Resumen agrupado por canasta física con sus totales de piezas y productos"""
    container_id: UUID
    qr_code: str
    status: str
    total_pieces: int
    total_products: int
    picked_total_units: int = 0
    picked_laser_qty: int = 0
    picked_boxes: int = 0
    picked_box_prods: int = 0
    picked_manual_qty: int = 0
    checked_total_units: int = 0
    checked_laser_qty: int = 0
    checked_boxes: int = 0
    checked_box_prods: int = 0
    checked_manual_qty: int = 0
    items: List[WarehouseContainerItemResponse] = []


# Alias de retrocompatibilidad
WarehouseScanEventResponse = WarehouseContainerItemResponse


# ============================================================================
# PARTIDAS / ÍTEMS DENTRO DE UN SPLIT (GRANULAR WAREHOUSE ITEMS)
# ============================================================================

class WarehouseItemResponse(BaseModel):
    """Información completa de una partida física de almacén (WarehouseItem)"""
    warehouse_item_id: Optional[UUID] = None
    split_id: Optional[UUID] = None
    order_item_id: UUID
    order_id: int
    product_id: str
    product_name: str
    codebar: Optional[str] = None
    barcode: Optional[str] = None
    location: str = ""
    image_url: Optional[str] = None
    container_id: Optional[UUID] = None
    container_qr: Optional[str] = None

    required_quantity: Optional[int] = None
    quantity: Optional[int] = None
    quantity_required: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def sync_quantities_and_aliases(cls, data):
        if isinstance(data, dict):
            qty = data.get("required_quantity")
            if qty is None:
                qty = data.get("quantity")
            if qty is None:
                qty = data.get("quantity_required")
            if qty is None:
                qty = 0
            data["required_quantity"] = qty
            data["quantity"] = qty
            data["quantity_required"] = qty

            # Sincronizar 1er filtro si vienen aliases anteriores
            if "picked_boxes" not in data and "boxes" in data:
                data["picked_boxes"] = data.get("boxes", 0)
            if "picked_box_prods" not in data and "box_prods" in data:
                data["picked_box_prods"] = data.get("box_prods", 0)
            if "picked_scanned_qty" not in data and "scanned_prods" in data:
                data["picked_scanned_qty"] = data.get("scanned_prods", 0)
            if "picked_manual_qty" not in data and "manual_prods" in data:
                data["picked_manual_qty"] = data.get("manual_prods", 0)
            if "picked_manual_reason" not in data and "manual_reason" in data:
                data["picked_manual_reason"] = data.get("manual_reason")
            if "picked_total_qty" not in data and "total_verified" in data:
                data["picked_total_qty"] = data.get("total_verified", 0)
            if "picked_by" not in data and "verified_by" in data:
                data["picked_by"] = data.get("verified_by")
            if "picked_by_name" not in data and "verified_by_name" in data:
                data["picked_by_name"] = data.get("verified_by_name")
            if "picked_at" not in data and "verified_at" in data:
                data["picked_at"] = data.get("verified_at")

            # Sincronizar 2do filtro si vienen aliases anteriores
            if "checked_boxes" not in data and "checker_boxes" in data:
                data["checked_boxes"] = data.get("checker_boxes", 0)
            if "checked_box_prods" not in data and "checker_box_prods" in data:
                data["checked_box_prods"] = data.get("checker_box_prods", 0)
            if "checked_scanned_qty" not in data and "checker_scanned_prods" in data:
                data["checked_scanned_qty"] = data.get("checker_scanned_prods", 0)
            if "checked_manual_qty" not in data and "checker_manual_prods" in data:
                data["checked_manual_qty"] = data.get("checker_manual_prods", 0)
            if "checked_manual_reason" not in data and "checker_manual_reason" in data:
                data["checked_manual_reason"] = data.get("checker_manual_reason")
            if "checked_total_qty" not in data and "checker_total_verified" in data:
                data["checked_total_qty"] = data.get("checker_total_verified", 0)
            if "checked_at" not in data and "checker_verified_at" in data:
                data["checked_at"] = data.get("checker_verified_at")
        return data

    # 1er Filtro: Surtido en Piso (Picker)
    picked_scanned_qty: int = 0
    picked_boxes: int = 0
    picked_box_prods: int = 0
    picked_manual_qty: int = 0
    picked_manual_reason: Optional[str] = None
    picked_total_qty: int = 0
    picked_by: Optional[int] = None
    picked_by_name: Optional[str] = None
    picked_at: Optional[datetime] = None

    # Aliases de compatibilidad con frontend anterior (1er filtro)
    boxes: int = 0
    box_prods: int = 0
    scanned_prods: int = 0
    manual_prods: int = 0
    verified_by_box_count: Optional[int] = 0
    verified_by_scan_count: Optional[int] = 0
    verified_by_manual_count: Optional[int] = 0
    manual_reason: Optional[str] = None
    total_verified: int = 0
    remaining_quantity: int = 0
    item_status: str = "pending"  # pending, partial, completed
    verified_by: Optional[int] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None

    # 2do Filtro: Mesa de Control y Revisión (Checker)
    checked_scanned_qty: int = 0
    checked_boxes: int = 0
    checked_box_prods: int = 0
    checked_manual_qty: int = 0
    checked_manual_reason: Optional[str] = None
    checked_total_qty: int = 0
    checked_by: Optional[int] = None
    checked_by_name: Optional[str] = None
    checked_at: Optional[datetime] = None

    # Aliases de compatibilidad con frontend anterior (2do filtro)
    checker_boxes: int = 0
    checker_scanned_prods: int = 0
    checker_box_prods: int = 0
    checker_manual_prods: int = 0
    checker_manual_reason: Optional[str] = None
    checker_verified_at: Optional[datetime] = None
    checker_total_verified: int = 0
    is_checker_fully_verified: bool = False
    has_forensic_discrepancy: bool = False
    discrepancy_note: Optional[str] = None

    # Rectificación Administrativa (Admin Override)
    admin_override_by: Optional[int] = None
    admin_override_by_name: Optional[str] = None
    admin_override_at: Optional[datetime] = None
    admin_override_note: Optional[str] = None
    admin_edited_by: Optional[int] = None
    admin_edited_by_name: Optional[str] = None
    admin_edited_at: Optional[datetime] = None

    # Precios (para supervisión de auditoría por Admin/Marketing/Vendedor)
    base_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None

    model_config = {"from_attributes": True}

    @classmethod
    def build_from_fulfillment(
        cls,
        ful,
        order_item=None,
        is_warehouse_operator: bool = False,
        is_checker_mode: bool = False
    ) -> "WarehouseItemResponse":
        """Factory method limpio para construir el schema desde WarehouseItem + OrderItem sin inflar los modelos ORM"""
        it = order_item or (ful.order_item if ful and hasattr(ful, "order_item") else None)

        # 1er Filtro (Picker)
        boxes_1st = getattr(ful, "picked_boxes", None) if ful else None
        if boxes_1st is None:
            boxes_1st = getattr(ful, "boxes", 0) or 0

        box_prods_1st = getattr(ful, "picked_box_prods", None) if ful else None
        if box_prods_1st is None:
            box_prods_1st = getattr(ful, "box_prods", 0) or 0

        scanned_1st = getattr(ful, "picked_scanned_qty", None) if ful else None
        if scanned_1st is None:
            scanned_1st = getattr(ful, "scanned_prods", 0) or 0

        manual_1st = getattr(ful, "picked_manual_qty", None) if ful else None
        if manual_1st is None:
            manual_1st = getattr(ful, "manual_prods", 0) or 0

        man_reason_1st = getattr(ful, "picked_manual_reason", None) if ful else None
        if man_reason_1st is None:
            man_reason_1st = getattr(ful, "manual_reason", None)

        p_by = getattr(ful, "picked_by", None) if ful else None
        if p_by is None:
            p_by = getattr(ful, "verified_by", None)

        p_at = getattr(ful, "picked_at", None) if ful else None
        if p_at is None:
            p_at = getattr(ful, "verified_at", None)

        p_name = None
        if ful:
            picker_obj = getattr(ful, "picker", None) or getattr(ful, "verifier", None)
            if picker_obj:
                p_name = picker_obj.full_name or picker_obj.username

        # 2do Filtro (Checker)
        boxes_2nd = getattr(ful, "checked_boxes", None) if ful else None
        if boxes_2nd is None:
            boxes_2nd = getattr(ful, "checker_boxes", 0) or 0

        box_prods_2nd = getattr(ful, "checked_box_prods", None) if ful else None
        if box_prods_2nd is None:
            box_prods_2nd = getattr(ful, "checker_box_prods", 0) or 0

        scanned_2nd = getattr(ful, "checked_scanned_qty", None) if ful else None
        if scanned_2nd is None:
            scanned_2nd = getattr(ful, "checker_scanned_prods", 0) or 0

        manual_2nd = getattr(ful, "checked_manual_qty", None) if ful else None
        if manual_2nd is None:
            manual_2nd = getattr(ful, "checker_manual_prods", 0) or 0

        man_reason_2nd = getattr(ful, "checked_manual_reason", None) if ful else None
        if man_reason_2nd is None:
            man_reason_2nd = getattr(ful, "checker_manual_reason", None)

        c_by = getattr(ful, "checked_by", None) if ful else None
        c_at = getattr(ful, "checked_at", None) if ful else None
        if c_at is None:
            c_at = getattr(ful, "checker_verified_at", None)

        c_name = None
        if ful and getattr(ful, "checker", None):
            c_name = ful.checker.full_name or ful.checker.username

        tot = box_prods_1st + scanned_1st + manual_1st
        c_tot = box_prods_2nd + scanned_2nd + manual_2nd

        is_confidence_val = bool(man_reason_2nd and 'Confianza' in man_reason_2nd)

        has_disc = False
        disc_note = None

        if c_tot > 0 and not is_confidence_val:
            diff_tot = (tot != c_tot)
            diff_bx = (boxes_1st != boxes_2nd)
            diff_bx_p = (box_prods_1st != box_prods_2nd)
            diff_scn = (scanned_1st != scanned_2nd)
            diff_man = (manual_1st != manual_2nd)

            if diff_tot:
                has_disc = True
                disc_note = f"Discrepancia en total: Surtidor={tot} vs Revisor={c_tot}"
            elif diff_bx or diff_bx_p or diff_scn or diff_man:
                has_disc = True
                disc_parts_1st = []
                disc_parts_2nd = []
                if box_prods_1st > 0 or box_prods_2nd > 0:
                    disc_parts_1st.append(f"{boxes_1st} cjas ({box_prods_1st} pz)")
                    disc_parts_2nd.append(f"{boxes_2nd} cjas ({box_prods_2nd} pz)")
                if scanned_1st > 0 or scanned_2nd > 0:
                    disc_parts_1st.append(f"{scanned_1st} lsr")
                    disc_parts_2nd.append(f"{scanned_2nd} lsr")
                if manual_1st > 0 or manual_2nd > 0:
                    disc_parts_1st.append(f"{manual_1st} man")
                    disc_parts_2nd.append(f"{manual_2nd} man")

                str_1st = " + ".join(disc_parts_1st) if disc_parts_1st else f"{tot} pzs"
                str_2nd = " + ".join(disc_parts_2nd) if disc_parts_2nd else f"{c_tot} pzs"
                disc_note = f"Discrepancia de empaque: Surtidor [{str_1st}] vs Revisor [{str_2nd}]"

        # Precios sensibles: ocultar para operadores de almacén
        show_prices = not is_warehouse_operator

        # Seguridad de revisión ciega: ocultar desglose del 1er filtro si está en modo Checker
        hide_1st_filter_breakdown = bool(is_warehouse_operator and is_checker_mode)

        # Discrepancias forenses: exclusivas para administración y auditoría
        show_forensic_discrepancies = not is_warehouse_operator

        req_qty = getattr(ful, "required_quantity", None)
        if req_qty is None:
            req_qty = it.quantity if it else 0

        w_item_id = getattr(ful, "warehouse_item_id", None)
        c_id = getattr(ful, "container_id", None)
        c_qr = getattr(ful, "container_qr", None)
        s_id = getattr(ful, "split_id", None)

        adm_id = getattr(ful, "admin_override_by", None) or getattr(ful, "admin_edited_by", None)
        adm_at = getattr(ful, "admin_override_at", None) or getattr(ful, "admin_edited_at", None)
        adm_note = getattr(ful, "admin_override_note", None)
        adm_name = None
        if ful and getattr(ful, "admin_editor", None):
            adm_name = ful.admin_editor.full_name or ful.admin_editor.username

        return cls(
            warehouse_item_id=w_item_id,
            split_id=s_id,
            order_item_id=it.order_item_id if it else ful.order_item_id,
            order_id=it.order_id if it else 0,
            product_id=it.product_id if it else (ful.product_id if ful else ""),
            product_name=it.product.name if (it and it.product) else (it.product_id if it else (ful.product_id if ful else "")),
            codebar=it.product.codebar if (it and it.product) else None,
            barcode=it.product.codebar if (it and it.product) else None,
            location=(it.product.location or "") if (it and it.product and it.product.location) else "",
            image_url=it.product.image_url if (it and it.product) else None,
            container_id=c_id,
            container_qr=c_qr,
            required_quantity=req_qty,
            quantity=req_qty,
            quantity_required=req_qty,
            # 1er Filtro
            picked_scanned_qty=0 if hide_1st_filter_breakdown else scanned_1st,
            picked_boxes=0 if hide_1st_filter_breakdown else boxes_1st,
            picked_box_prods=0 if hide_1st_filter_breakdown else box_prods_1st,
            picked_manual_qty=0 if hide_1st_filter_breakdown else manual_1st,
            picked_manual_reason=None if hide_1st_filter_breakdown else man_reason_1st,
            picked_total_qty=0 if hide_1st_filter_breakdown else tot,
            picked_by=p_by,
            picked_by_name=p_name,
            picked_at=p_at,
            # Aliases 1er filtro
            boxes=0 if hide_1st_filter_breakdown else boxes_1st,
            box_prods=0 if hide_1st_filter_breakdown else box_prods_1st,
            scanned_prods=0 if hide_1st_filter_breakdown else scanned_1st,
            manual_prods=0 if hide_1st_filter_breakdown else manual_1st,
            verified_by_box_count=0 if hide_1st_filter_breakdown else box_prods_1st,
            verified_by_scan_count=0 if hide_1st_filter_breakdown else scanned_1st,
            verified_by_manual_count=0 if hide_1st_filter_breakdown else manual_1st,
            manual_reason=None if hide_1st_filter_breakdown else man_reason_1st,
            total_verified=tot,
            remaining_quantity=max(0, req_qty - tot),
            item_status=getattr(ful, "status", None) or getattr(ful, "item_status", "pending") if ful else "pending",
            verified_by=p_by,
            verified_by_name=p_name,
            verified_at=p_at,
            # 2do Filtro
            checked_scanned_qty=scanned_2nd,
            checked_boxes=boxes_2nd,
            checked_box_prods=box_prods_2nd,
            checked_manual_qty=manual_2nd,
            checked_manual_reason=man_reason_2nd,
            checked_total_qty=c_tot,
            checked_by=c_by,
            checked_by_name=c_name,
            checked_at=c_at,
            # Aliases 2do filtro
            checker_boxes=boxes_2nd,
            checker_scanned_prods=scanned_2nd,
            checker_box_prods=box_prods_2nd,
            checker_manual_prods=manual_2nd,
            checker_manual_reason=man_reason_2nd,
            checker_verified_at=c_at,
            checker_total_verified=c_tot,
            is_checker_fully_verified=bool(c_tot >= req_qty),
            has_forensic_discrepancy=has_disc if show_forensic_discrepancies else False,
            discrepancy_note=disc_note if show_forensic_discrepancies else None,
            # Admin Override
            admin_override_by=adm_id,
            admin_override_by_name=adm_name,
            admin_override_at=adm_at,
            admin_override_note=adm_note,
            admin_edited_by=adm_id,
            admin_edited_by_name=adm_name,
            admin_edited_at=adm_at,
            # Precios
            base_price=it.base_price if (it and show_prices) else None,
            final_price=it.final_price if (it and show_prices) else None
        )


# Alias exacto para retrocompatibilidad total en código existente
WarehouseSplitItemResponse = WarehouseItemResponse


# ============================================================================
# SPLITS / LOTES DE SURTIDO EN ALMACÉN
# ============================================================================

class WarehouseSplitSummary(BaseModel):
    """Resumen liviano de un split para listados, terminales y colas de trabajo"""
    split_id: UUID
    order_id: int
    split_number: int
    split_index: Optional[int] = None
    total_splits: int
    total_splits_in_order: Optional[int] = None
    split_code: Optional[str] = None
    status: str  # pending, picking, ready_for_check, checking, completed, cancelled
    picker_id: Optional[int] = None
    picker_name: Optional[str] = None
    checker_id: Optional[int] = None
    checker_name: Optional[str] = None
    admin_override_by: Optional[int] = None
    admin_override_by_name: Optional[str] = None
    admin_override_at: Optional[datetime] = None
    admin_edited_by: Optional[int] = None
    admin_edited_by_name: Optional[str] = None
    admin_edited_at: Optional[datetime] = None
    customer_name: Optional[str] = None
    assigned_user_name: Optional[str] = None
    seller_name: Optional[str] = None
    security_seal_folio: Optional[str] = None
    started_at: Optional[datetime] = None
    picking_completed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    checking_started_at: Optional[datetime] = None
    audited_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    duration_formatted: Optional[str] = None
    checking_duration_seconds: Optional[int] = None
    checking_duration_formatted: Optional[str] = None
    items_count: Optional[int] = None
    containers: List[WarehouseContainerSummary] = []
    containers_count: int = 0
    active_container_id: Optional[UUID] = None
    active_container_qr: Optional[str] = None
    container_qr: Optional[str] = None
    container_id: Optional[UUID] = None
    uses_containers: bool = False
    containers_summary: List[WarehouseContainerSummaryBreakdown] = []

    model_config = {"from_attributes": True}


class WarehouseSplitResponse(WarehouseSplitSummary):
    """Detalle completo de un split incluyendo todas sus partidas físicas y canastas QR asociadas"""
    items: List[WarehouseItemResponse] = []
    containers_summary: List[WarehouseContainerSummaryBreakdown] = []
    is_blind_masked: bool = False
    blind_notice: Optional[str] = None
    total_items: Optional[int] = None

    @classmethod
    def build_from_split(
        cls,
        split,
        is_warehouse_operator: bool = False,
        is_blind_masked: bool = False,
        blind_notice: Optional[str] = None
    ) -> "WarehouseSplitResponse":
        """Factory method para construir el response completo del split usando los schemas Pydantic"""
        is_checker = split.status in ["ready_for_check", "checking"]
        items_list = []

        raw_items = getattr(split, "warehouse_items", []) or []
        for ful in raw_items:
            it = getattr(ful, "order_item", None)
            items_list.append(WarehouseItemResponse.build_from_fulfillment(
                ful,
                it,
                is_warehouse_operator=is_warehouse_operator,
                is_checker_mode=is_checker
            ))

        c_name = None
        if split.order and split.order.customer:
            c_name = split.order.customer.full_name or split.order.customer.username

        assigned_name = split.order.assigned_user_name if split.order else None

        # Canastas QR vinculadas a este split
        raw_containers = getattr(split, "containers", []) or []
        containers_list = [WarehouseContainerSummary.model_validate(c) for c in raw_containers]
        uses_containers_val = bool(
            getattr(split, "uses_containers", False)
            or len(containers_list) > 0
            or getattr(split, "active_container_id", None)
        )

        adm_by = getattr(split, "admin_override_by", None)
        adm_at = getattr(split, "admin_override_at", None)
        adm_name = (split.admin_editor.full_name or split.admin_editor.username) if getattr(split, "admin_editor", None) else None

        act_qr = None
        if getattr(split, "active_container", None):
            act_qr = split.active_container.qr_code
        elif getattr(split, "active_container_qr", None):
            act_qr = split.active_container_qr
        elif raw_containers:
            act_qr = raw_containers[-1].qr_code

        act_cid = getattr(split, "active_container_id", None)
        if not act_cid and raw_containers:
            act_cid = raw_containers[-1].container_id

        # Resumen consolidado de canastas físicas y piezas depositadas
        containers_summary_list = []
        if uses_containers_val or raw_containers:
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
            raw_cis = getattr(split, "container_items", None) or []
            for ci in raw_cis:
                cid = ci.container_id
                if cid not in grouped:
                    c_qr = ci.container.qr_code if getattr(ci, "container", None) else (getattr(ci, "container_qr", None) or f"Canasta #{cid}")
                    c_status = ci.container.status if getattr(ci, "container", None) else "in_use"
                    grouped[cid] = {
                        "container_id": cid,
                        "qr_code": c_qr,
                        "status": c_status,
                        "total_pieces": 0,
                        "total_products": 0,
                        "items": []
                    }
                tot_p = (getattr(ci, "picked_total_qty", None) or 0) + (getattr(ci, "checked_total_qty", None) or 0)
                grouped[cid]["total_pieces"] += tot_p
                grouped[cid]["total_products"] += 1
                grouped[cid]["items"].append({
                    "container_item_id": ci.container_item_id,
                    "split_id": ci.split_id,
                    "container_id": ci.container_id,
                    "container_qr": getattr(ci, "container_qr", None) or (ci.container.qr_code if getattr(ci, "container", None) else None),
                    "warehouse_item_id": ci.warehouse_item_id,
                    "order_item_id": ci.order_item_id,
                    "product_id": ci.product_id,
                    "product_name": getattr(ci, "product_name", None) or (ci.product.name if getattr(ci, "product", None) else None),
                    "barcode": ci.product.codebar if getattr(ci, "product", None) else None,
                    "picked_scanned_qty": ci.picked_scanned_qty or 0,
                    "picked_boxes": ci.picked_boxes or 0,
                    "picked_box_prods": ci.picked_box_prods or 0,
                    "picked_manual_qty": ci.picked_manual_qty or 0,
                    "picked_total_qty": ci.picked_total_qty or 0,
                    "checked_scanned_qty": ci.checked_scanned_qty or 0,
                    "checked_boxes": ci.checked_boxes or 0,
                    "checked_box_prods": ci.checked_box_prods or 0,
                    "checked_manual_qty": ci.checked_manual_qty or 0,
                    "checked_total_qty": ci.checked_total_qty or 0,
                    "updated_at": ci.updated_at
                })
            containers_summary_list = [WarehouseContainerSummaryBreakdown(**data) for data in grouped.values()]

        return cls(
            split_id=split.split_id,
            order_id=split.order_id,
            split_number=split.split_number,
            split_index=split.split_number,
            total_splits=split.total_splits,
            total_splits_in_order=split.total_splits,
            split_code=getattr(split, "split_code", None) or f"{split.order_id}-{split.split_number}",
            status=split.status,
            picker_id=split.picker_id,
            picker_name=(split.picker.full_name or split.picker.username) if split.picker else None,
            checker_id=split.checker_id,
            checker_name=(split.checker.full_name or split.checker.username) if split.checker else None,
            admin_override_by=adm_by,
            admin_override_by_name=adm_name,
            admin_override_at=adm_at,
            admin_edited_by=adm_by,
            admin_edited_by_name=adm_name,
            admin_edited_at=adm_at,
            customer_name=c_name,
            assigned_user_name=assigned_name,
            seller_name=assigned_name,
            security_seal_folio=split.security_seal_folio,
            started_at=split.started_at,
            picking_completed_at=getattr(split, "picking_completed_at", None),
            completed_at=split.completed_at,
            checking_started_at=split.checking_started_at,
            audited_at=split.completed_at if split.status in ["completed", "audited"] else None,
            duration_seconds=split.duration_seconds,
            duration_formatted=split.duration_formatted,
            checking_duration_seconds=split.checking_duration_seconds,
            checking_duration_formatted=split.checking_duration_formatted,
            items_count=len(items_list),
            total_items=len(items_list),
            uses_containers=uses_containers_val,
            containers=containers_list,
            containers_count=len(containers_list),
            active_container_id=act_cid,
            active_container_qr=act_qr,
            container_qr=act_qr,
            container_id=act_cid,
            containers_summary=containers_summary_list,
            items=items_list,
            is_blind_masked=is_blind_masked,
            blind_notice=blind_notice
        )


# ============================================================================
# SOLICITUDES / ACCIONES DE ALMACÉN (REQUEST BODY SCHEMAS)
# ============================================================================

class WarehouseToggleDetailsRequest(BaseModel):
    """Permite a Admin o Marketing alternar el modo de visibilidad (Surtido Ciego vs Detallado)"""
    show_details: bool = Field(..., description="True para mostrar detalles; False para surtido ciego")


class WarehouseSendToWarehouseRequest(BaseModel):
    """Envío explícito de un pedido a bodega dividiéndolo en N splits concurrentes"""
    total_splits: int = Field(default=1, ge=1, le=20, description="Número de splits para surtido (1 a 20)")
    show_details: bool = Field(default=False, description="True: almacenista ve cliente y partidas antes de tomar; False: surtido ciego")


class WarehouseScanBarcodeRequest(BaseModel):
    """Disparo de pistola lectora láser con código de barras en piso o mesa de revisión"""
    codebar: str = Field(..., min_length=1, max_length=100, description="Código de barras escaneado")
    container_qr: Optional[str] = Field(None, max_length=50, description="Código QR de la canasta física receptora (opcional)")


class WarehouseFastScanRequest(BaseModel):
    """Escaneo atómico ultra-rápido para terminales láser de alta eficiencia"""
    barcode: str = Field(..., min_length=1, max_length=100, description="Código de barras del producto o QR")
    container_qr: Optional[str] = Field(None, max_length=50, description="Canasta QR física donde se deposita el producto")
    filter_phase: Optional[str] = Field("picker", pattern="^(picker|checker)$", description="Fase: picker o checker")


class WarehouseAddBoxesRequest(BaseModel):
    """Empaque rápido en lote mediante cajas maestras cerradas"""
    order_item_id: Optional[UUID] = Field(None, description="ID de la partida de pedido (order_item_id)")
    warehouse_item_id: Optional[UUID] = Field(None, description="ID de la partida de almacén (warehouse_item_id)")
    boxes: int = Field(..., gt=0, description="Número de cajas maestras completas")
    units_per_box: int = Field(..., gt=0, description="Unidades contenidas en cada caja maestra")
    container_qr: Optional[str] = Field(None, max_length=50, description="Canasta QR física (opcional)")


class WarehouseManualVerificationRequest(BaseModel):
    """Validación manual por excepción con auditoría estricta"""
    order_item_id: Optional[UUID] = Field(None, description="ID de la partida")
    warehouse_item_id: Optional[UUID] = Field(None, description="ID de la partida de almacén")
    verified_quantity: int = Field(..., gt=0, description="Cantidad manual verificada")
    reason: str = Field(..., min_length=3, max_length=255, description="Motivo justificado de excepción")
    container_qr: Optional[str] = Field(None, max_length=50, description="Canasta QR física (opcional)")


class WarehouseAddManualRequest(BaseModel):
    """Payload flexible para validación manual de partidas dañadas o sin código"""
    order_item_id: Optional[UUID] = Field(None, description="ID de la partida a verificar")
    warehouse_item_id: Optional[UUID] = Field(None, description="ID de la partida de almacén")
    manual_quantity: Optional[int] = Field(None, gt=0, description="Cantidad verificada manualmente")
    quantity: Optional[int] = Field(None, gt=0, description="Alias de cantidad verificada manualmente")
    reason: Optional[str] = Field(None, max_length=255, description="Motivo de la verificación manual")
    container_qr: Optional[str] = Field(None, max_length=50, description="Canasta QR física (opcional)")


class WarehouseAdvanceStatusRequest(BaseModel):
    """Avanza el split en la máquina de estados y registra el sello de seguridad"""
    new_status: Optional[str] = Field(None, description="Nuevo estado opcional (picking, in_progress, ready_for_check, checking, completed)")
    security_seal_folio: Optional[str] = Field(None, max_length=50, description="Folio del cincho o sello físico inviolable")
    auto_generate_seal: bool = Field(False, description="Generar automáticamente un folio de sello con prefijo SL-")


class WarehouseClaimSplitRequest(BaseModel):
    """Auto-asignación de un split para surtido (picker) o revisión (checker)"""
    role_type: str = Field(default="picker", pattern="^(picker|checker)$", description="Rol que toma el split")
    uses_containers: Optional[bool] = Field(None, description="Modo inicial opcional: True para usar canastas QR, False para surtido directo")


class WarehouseSetContainerModeRequest(BaseModel):
    """Configura explícitamente si el split utiliza canastas QR o surtido directo"""
    uses_containers: bool = Field(..., description="True para surtido con canastas QR; False para surtido directo por split")
    reset_progress: bool = Field(default=False, description="Si es True, autoriza reiniciar los contadores de piezas a 0 al pasar de directo a canastas")


class WarehouseReassignSplitRequest(BaseModel):
    """Reasignación forzada de split por supervisor o admin"""
    target_user_id: Optional[int] = Field(None, description="ID del nuevo usuario asignado (None para desasignar)")
    role_type: str = Field(default="picker", pattern="^(picker|checker)$", description="picker o checker")


# ============================================================================
# COLA DE TRABAJO, HISTORIAL Y REPORTES DE AUDITORÍA FORENSE
# ============================================================================

class WarehouseQueueOrderResponse(BaseModel):
    """Elemento de la cola de trabajo FIFO para la mesa de surtido de almacén"""
    order_id: int
    customer_id: int
    customer_name: str
    assigned_user_name: Optional[str] = None
    seller_name: Optional[str] = None
    total_amount: Optional[Decimal] = None
    shipping_address_snapshot: Optional[str] = None
    created_at: datetime
    warehouse_sent_at: Optional[datetime] = None
    sent_to_warehouse_at: Optional[datetime] = None
    warehouse_sent_by_name: Optional[str] = None
    warehouse_status: Optional[str] = None
    audit_verdict: Optional[str] = "clean"
    warehouse_show_details: bool = False
    total_splits: int = 1
    completed_splits_count: int = 0
    splits: List[WarehouseSplitSummary] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def populate_seller_name(self) -> "WarehouseQueueOrderResponse":
        if self.seller_name is None and self.assigned_user_name is not None:
            self.seller_name = self.assigned_user_name
        return self


class WarehouseQueuePaginatedResponse(BaseModel):
    """Respuesta paginada para la cola de trabajo o historial de bodega"""
    total: int = 0
    orders: List[WarehouseQueueOrderResponse]
    skip: int = 0
    limit: int = 20
    lookahead_pages: int = 0


class WarehouseAuditForensicItem(BaseModel):
    """Desglose pericial de una partida para auditoría antifraude y control pericial"""
    warehouse_item_id: Optional[UUID] = None
    order_item_id: UUID
    product_id: str
    product_name: str
    codebar: Optional[str] = None
    location: str = ""
    container_id: Optional[UUID] = None
    container_qr: Optional[str] = None
    ordered_quantity: int

    # 1er Filtro (Picker)
    boxes: int = 0
    box_prods: int = 0
    scanned_prods: int = 0
    manual_prods: int = 0
    manual_reason: Optional[str] = None
    total_verified: int = 0
    difference: int = 0
    status: str
    split_number: Optional[int] = None
    split_code: Optional[str] = None
    verified_by: Optional[int] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None

    # 2do Filtro (Checker)
    checker_boxes: int = 0
    checker_scanned_prods: int = 0
    checker_box_prods: int = 0
    checker_manual_prods: int = 0
    checker_manual_reason: Optional[str] = None
    checker_verified_at: Optional[datetime] = None
    checker_total_verified: int = 0
    checker_difference: int = 0
    has_forensic_discrepancy: bool = False
    discrepancy_note: Optional[str] = None

    # Trazabilidad de Rectificación Administrativa
    admin_edited_by: Optional[int] = None
    admin_edited_by_name: Optional[str] = None
    admin_edited_at: Optional[datetime] = None
    final_price: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    is_blind_masked: Optional[bool] = False


class WarehouseUpdateManualReasonRequest(BaseModel):
    """Actualización del motivo o comentario de auditoría manual por Admin, Marketing o Vendedor"""
    manual_reason: str = Field(..., max_length=255, description="Nuevo motivo justificado o nota de auditoría")


class WarehouseAdminSplitOverrideRequest(BaseModel):
    """Acciones periciales exclusivas de Administrador para modificar estatus o sellos de split"""
    status: Optional[str] = Field(None, description="Nuevo estatus forzado (pending, picking, ready_for_check, checking, completed, cancelled)")
    security_seal_folio: Optional[str] = Field(None, max_length=50, description="Folio de sello o cincho de seguridad rectificado")
    clear_seal: bool = Field(False, description="Si es True, retira el sello de seguridad")


class WarehouseAdminItemCountsOverrideRequest(BaseModel):
    """Acción de auditoría pericial exclusiva de Administrador para rectificar conteos físicos en 1er y 2do filtro"""
    scanned_prods: Optional[int] = Field(None, ge=0, description="Piezas verificadas con láser (1er filtro)")
    boxes: Optional[int] = Field(None, ge=0, description="Cajas maestras verificadas (1er filtro)")
    box_prods: Optional[int] = Field(None, ge=0, description="Piezas verificadas por caja maestra (1er filtro)")
    manual_prods: Optional[int] = Field(None, ge=0, description="Piezas verificadas manualmente (1er filtro)")
    manual_reason: Optional[str] = Field(None, max_length=255, description="Motivo / justificación 1er filtro")
    checker_scanned_prods: Optional[int] = Field(None, ge=0, description="Piezas verificadas con láser (2do filtro)")
    checker_boxes: Optional[int] = Field(None, ge=0, description="Cajas maestras verificadas (2do filtro)")
    checker_box_prods: Optional[int] = Field(None, ge=0, description="Piezas verificadas por caja maestra (2do filtro)")
    checker_manual_prods: Optional[int] = Field(None, ge=0, description="Piezas verificadas manualmente (2do filtro)")
    checker_manual_reason: Optional[str] = Field(None, max_length=255, description="Motivo / justificación 2do filtro")


class WarehouseAuditOrderResponse(BaseModel):
    """Reporte forense completo del pedido para auditoría antes de despacho"""
    order_id: int
    warehouse_status: Optional[str] = None
    audit_verdict: Optional[str] = "clean"
    warehouse_show_details: bool = False
    total_splits: int = 1
    warehouse_sent_at: Optional[datetime] = None
    sent_to_warehouse_at: Optional[datetime] = None
    warehouse_sent_by_name: Optional[str] = None
    all_items_verified: bool = False
    total_ordered_items: int = 0
    total_verified_items: int = 0
    security_seals: List[str] = []
    splits: List[WarehouseSplitResponse] = []
    forensic_items: List[WarehouseAuditForensicItem] = []
    total_forensic_items: int = 0
    skip: int = 0
    limit: int = 20


class WarehouseStatsResponse(BaseModel):
    """Métricas operativas del almacén en tiempo real"""
    pending_orders: int
    orders_pending_queue: Optional[int] = 0
    orders_in_progress: Optional[int] = 0
    completed_orders_today: int
    orders_completed_today: Optional[int] = 0
    active_splits: int
    active_splits_in_floor: Optional[int] = 0
    completed_splits_today: int
    available_containers: Optional[int] = 0
    in_use_containers: Optional[int] = 0
