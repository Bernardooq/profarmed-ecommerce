"""
Routes para Terminal de Surtido Láser y Operaciones en Piso (Floor Scanning Operations)

Proporciona las acciones atómicas en piso de almacén ejecutadas desde la terminal láser:
- Pistoleo por código de barras individual (pistola lectora USB/Bluetooth o cámara WebRTC).
- Validación en bloque por empaque cerrado de cajas maestras (master boxes).
- Captura de conteo manual justificado para artículos con etiqueta dañada o inaccesible.

ENDPOINTS:
- POST /splits/{id}/scan-barcode - Pistoleo láser individual (+1 pieza o canasta) (requiere 'warehouse.operator' o 'warehouse.checker')
- POST /splits/{id}/add-boxes - Empaque acelerado por cajas cerradas (requiere 'warehouse.operator' o 'warehouse.checker')
- POST /splits/{id}/add-manual - Conteo manual con motivo obligatorio (requiere 'warehouse.operator' o 'warehouse.checker')

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from db.base import User
from dependencies import get_db, require_permission
from crud.crud_warehouse import (
    scan_barcode_laser,
    add_boxes_master,
    add_manual_verification,
)
from schemas.warehouse import (
    WarehouseScanBarcodeRequest,
    WarehouseAddBoxesRequest,
    WarehouseAddManualRequest,
    WarehouseSplitItemResponse,
)

router = APIRouter()


# ============================================================================
# OPERACIONES DE SURTIDO Y PISTOLEO LÁSER EN PISO
# ============================================================================

""" POST /splits/{split_id}/scan-barcode - Pistoleo de código de barras individual (+1 pz) o QR de canasta """
@router.post("/splits/{split_id}/scan-barcode")
def scan_barcode_route(
    split_id: UUID,
    payload: WarehouseScanBarcodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.operator", "warehouse.checker", "system.admin"))
):
    """
    Registra un evento atómico de pistoleo láser en la terminal de piso.
    
    Flujo operativo inteligente:
    1. Si el código corresponde al QR de una canasta registrada, la activa como canasta de depósito actual.
    2. Si corresponde al código de barras del producto, incrementa +1 pieza verificada.
    3. Si el split opera en modo canastas, asocia el producto directamente al tote activo.
    4. Valida en tiempo real que no se exceda la cantidad requerida por el pedido.
    """
    return scan_barcode_laser(
        db=db,
        split_id=split_id,
        barcode=payload.codebar,
        user_id=current_user.user_id,
        current_user=current_user,
        container_qr=payload.container_qr
    )


""" POST /splits/{split_id}/add-boxes - Registro de cajas maestras (master pack) """
@router.post(
    "/splits/{split_id}/add-boxes",
    response_model=WarehouseSplitItemResponse
)
def add_boxes_route(
    split_id: UUID,
    payload: WarehouseAddBoxesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.operator", "warehouse.checker", "system.admin"))
):
    """
    Registra el surtido o verificación de mercancía en cajas cerradas de fábrica.
    
    Multiplica el número de cajas por las unidades declaradas por caja y suma el total
    a la partida de forma atómica, validando contra el límite del pedido.
    """
    item_id = payload.order_item_id or payload.warehouse_item_id
    if not item_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere order_item_id o warehouse_item_id")
    return add_boxes_master(
        db=db,
        split_id=split_id,
        order_item_id=item_id,
        boxes_count=payload.boxes,
        units_per_box=payload.units_per_box,
        user_id=current_user.user_id,
        current_user=current_user,
        container_qr=payload.container_qr
    )


""" POST /splits/{split_id}/add-manual - Validación manual justificada por excepción operativa """
@router.post(
    "/splits/{split_id}/add-manual",
    response_model=WarehouseSplitItemResponse
)
def add_manual_route(
    split_id: UUID,
    payload: WarehouseAddManualRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.operator", "warehouse.checker", "system.admin"))
):
    """
    Permite asentar piezas verificadas manualmente cuando el código de barras está ilegible,
    arrugado o el producto carece de etiqueta física.
    
    Exige obligatoriamente un motivo operativo para auditoría posterior (ej: 'Código borroso').
    """
    item_id = payload.order_item_id or payload.warehouse_item_id
    if not item_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere order_item_id o warehouse_item_id")
    qty = payload.quantity or payload.manual_quantity or 1
    return add_manual_verification(
        db=db,
        split_id=split_id,
        order_item_id=item_id,
        quantity=qty,
        reason=payload.reason,
        user_id=current_user.user_id,
        current_user=current_user,
        container_qr=payload.container_qr
    )
