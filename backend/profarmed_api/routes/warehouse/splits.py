"""
Routes para Gestión y Ciclo de Vida de Splits (Assignment, Mode, Transitions & State Machine)

Controla el flujo de trabajo atómico de los lotes de surtido (Splits):
- Búsqueda por folio legible (ej: "7-1") y consulta por UUID.
- Autoasignación de colaboradores en piso de acuerdo a su rol PBAC (Surtidor o Revisor).
- Conmutación dinámica de modalidad: Surtido Directo por Split vs. Modalidad Con Canastas QR.
- Reasignación administrativa y balanceo de carga por supervisores de almacén.
- Asociación y activación de canastas QR físicas.
- Máquina de estados blindada: 1er Filtro (picking) -> 2do Filtro (checking) -> Sellado (completed) o Fast-Track.

ENDPOINTS:
- GET /splits/by-code/{code} - Buscar lote por código legible (requiere 'warehouse.view' o 'warehouse.operator')
- GET /splits/{id} - Detalle exhaustivo de split e ítems (requiere 'warehouse.view' o 'warehouse.operator')
- POST /splits/{id}/claim - Autoasignación de colaborador al lote (requiere 'warehouse.operator' o 'warehouse.checker')
- POST /splits/{id}/set-container-mode - Alternar modalidad de canastas (requiere 'warehouse.mode_direct' o 'warehouse.mode_containers')
- POST /splits/{id}/reassign - Reasignar surtidor o revisor (requiere 'warehouse.supervisor')
- POST /splits/{id}/bind-container - Vincular canasta QR física al split (requiere 'warehouse.operator')
- POST /splits/{id}/activate-container - Seleccionar canasta activa para pistoleo (requiere 'warehouse.operator')
- POST /splits/{id}/advance-status - Avanzar lote o aplicar precinto de seguridad (requiere 'warehouse.filter2_send' o 'warehouse.seal_direct')
- POST /splits/{id}/checker-fast-track - Validar 2do filtro confiando en piso (requiere 'warehouse.supervisor')

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from db.base import User
from dependencies import get_db, require_permission
from crud.crud_user import get_user
from crud.crud_warehouse import (
    get_split_by_id,
    get_split_by_code,
    claim_split,
    set_split_container_mode,
    reassign_split,
    bind_container_to_split,
    activate_container_for_split,
    advance_split_status,
    fast_track_approve_second_filter,
)
from schemas.warehouse import (
    WarehouseSplitResponse,
    WarehouseClaimSplitRequest,
    WarehouseSetContainerModeRequest,
    WarehouseReassignSplitRequest,
    WarehouseBindContainerRequest,
    WarehouseContainerResponse,
    WarehouseAdvanceStatusRequest,
)

router = APIRouter()


# ============================================================================
# CONSULTA Y BÚSQUEDA DE SPLITS
# ============================================================================

""" GET /splits/by-code/{code} - Búsqueda rápida por código compuesto del lote (ej: '7-1') """
@router.get(
    "/splits/by-code/{code}",
    response_model=WarehouseSplitResponse
)
def get_split_by_code_route(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.operator", "warehouse.checker", "warehouse.manage", "system.admin"))
):
    """
    Obtiene la información y partidas de un split a partir de su código visible o folio
    (ej: '7-1' para Pedido #7 Split #1).
    """
    return get_split_by_code(db=db, code=code, current_user=current_user)


""" GET /splits/{split_id} - Detalle completo de un lote por UUID """
@router.get(
    "/splits/{split_id}",
    response_model=WarehouseSplitResponse
)
def get_split_detail_route(
    split_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.operator", "warehouse.checker", "warehouse.manage", "system.admin"))
):
    """
    Devuelve la ficha completa del split, incluyendo:
    - Estado actual del ciclo de vida y modalidad operativa.
    - Colaboradores asignados (Picker y Checker).
    - Canastas QR vinculadas y canasta activa.
    - Partidas de productos requeridas con conteos de 1er y 2do filtro.
    """
    return get_split_by_id(db=db, split_id=split_id, current_user=current_user)


# ============================================================================
# ASIGNACIÓN Y CONFIGURACIÓN OPERATIVA DEL LOTE
# ============================================================================

""" POST /splits/{split_id}/claim - Autoasignación de operario de piso (Picker o Checker) """
@router.post(
    "/splits/{split_id}/claim",
    response_model=WarehouseSplitResponse
)
def claim_split_route(
    split_id: UUID,
    payload: WarehouseClaimSplitRequest = WarehouseClaimSplitRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.operator", "warehouse.checker", "warehouse.manage", "system.admin"))
):
    """
    Permite a un colaborador en terminal tomar posesión de un split para surtir o revisar.
    
    Validaciones de seguridad:
    - Impide que un usuario con rol de Administrador sea asignado a tareas de piso.
    - Exige 'warehouse.checker' si se autoasigna como Revisor (2do filtro).
    - Exige 'warehouse.operator' si se autoasigna como Surtidor (1er filtro).
    """
    role_type = payload.role_type or "picker"
    is_admin_or_mgr = (
        (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("warehouse.manage")))
        or current_user.role_id == 1
    )
    if not is_admin_or_mgr:
        if role_type == "checker":
            if not (hasattr(current_user, "has_permission") and current_user.has_permission("warehouse.checker")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requiere el permiso 'warehouse.checker' para autoasignarse como Revisor (2do Filtro)."
                )
        else:
            if not (hasattr(current_user, "has_permission") and current_user.has_permission("warehouse.operator")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requiere el permiso 'warehouse.operator' para autoasignarse como Surtidor (1er Filtro)."
                )

    return claim_split(
        db=db,
        split_id=split_id,
        user_id=current_user.user_id,
        as_role=role_type,
        uses_containers=payload.uses_containers
    )


""" POST /splits/{split_id}/set-container-mode - Conmutar modalidad entre Surtido Directo y Canastas QR """
@router.post(
    "/splits/{split_id}/set-container-mode",
    response_model=WarehouseSplitResponse
)
def set_split_container_mode_route(
    split_id: UUID,
    payload: WarehouseSetContainerModeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(
        "warehouse.mode_direct",
        "warehouse.mode_containers",
        "warehouse.operator",
        "warehouse.checker",
        "warehouse.supervisor",
        "warehouse.manage",
        "system.admin"
    ))
):
    """
    Alterna la modalidad de recolección del split:
    - `uses_containers = true`: Habilita canastas físicas QR ('warehouse.mode_containers').
    - `uses_containers = false`: Surtido directo por lote sin canastas ('warehouse.mode_direct').
    - Permite opcionalmente resetear el avance acumulado en caso de reconfiguración radical.
    """
    has_perm = getattr(current_user, "has_permission", lambda p: False)
    is_admin_or_super = current_user.role_id == 1 or has_perm("system.admin") or has_perm("warehouse.manage") or has_perm("warehouse.supervisor")

    if payload.uses_containers:
        if not (is_admin_or_super or has_perm("warehouse.mode_containers")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para activar la modalidad de Canastas QR (warehouse.mode_containers)"
            )
    else:
        if not (is_admin_or_super or has_perm("warehouse.mode_direct")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para activar la modalidad de Surtido Directo por Split (warehouse.mode_direct)"
            )

    return set_split_container_mode(
        db=db,
        split_id=split_id,
        uses_containers=payload.uses_containers,
        reset_progress=payload.reset_progress,
        user_id=current_user.user_id,
        current_user=current_user
    )


""" POST /splits/{split_id}/reassign - Reasignación administrativa de picker o checker """
@router.post(
    "/splits/{split_id}/reassign",
    response_model=WarehouseSplitResponse
)
def reassign_split_route(
    split_id: UUID,
    payload: WarehouseReassignSplitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.supervisor", "warehouse.manage", "system.admin"))
):
    """
    Permite al supervisor reasignar el lote a otro colaborador o desasignarlo (`target_user_id = null`).
    
    Verifica que el usuario destino no sea administrador y cuente con los permisos operativos necesarios.
    """
    if payload.target_user_id is not None:
        target = get_user(db, payload.target_user_id)
        if target:
            target_slug = getattr(target.role_rel, "slug", "") if target.role_rel else ""
            if target.role_id == 1 or target_slug == "admin" or target.user_id >= 15_000_000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede asignar un lote de surtido de bodega a un usuario con rol de Administrador."
                )
            required_perm = "warehouse.checker" if payload.role_type == "checker" else "warehouse.operator"
            has_perm = hasattr(target, "has_permission") and target.has_permission(required_perm)
            if not (has_perm or (hasattr(target, "has_permission") and (target.has_permission("warehouse.manage") or target.has_permission("system.admin")))):
                role_label = "Revisor (2do Filtro)" if payload.role_type == "checker" else "Surtidor (1er Filtro)"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El colaborador asignado no cuenta con el permiso '{required_perm}' para operar como {role_label}."
                )

    return reassign_split(
        db=db,
        split_id=split_id,
        role_type=payload.role_type,
        target_user_id=payload.target_user_id
    )


# ============================================================================
# VINCULACIÓN Y ACTIVACIÓN DE CANASTAS QR
# ============================================================================

""" POST /splits/{split_id}/bind-container - Asociar una nueva canasta QR al lote """
@router.post(
    "/splits/{split_id}/bind-container",
    response_model=WarehouseContainerResponse
)
def bind_container_to_split_route(
    split_id: UUID,
    payload: WarehouseBindContainerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.operator", "warehouse.checker", "warehouse.manage", "system.admin"))
):
    """
    Vincula una canasta física disponible (`available`) al lote en curso.
    La canasta pasa inmediatamente a estado `in_use`.
    """
    return bind_container_to_split(
        db=db,
        split_id=split_id,
        qr_code=payload.qr_code,
        user_id=current_user.user_id
    )


""" POST /splits/{split_id}/activate-container - Seleccionar canasta como receptora activa de escaneos """
@router.post(
    "/splits/{split_id}/activate-container",
    response_model=WarehouseSplitResponse
)
def activate_container_route(
    split_id: UUID,
    payload: WarehouseBindContainerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.operator", "warehouse.checker", "warehouse.manage", "system.admin"))
):
    """
    Marca una canasta ya vinculada como la canasta de depósito actual (`active_container_qr`),
    hacia la cual se sumarán los siguientes productos pistoleados.
    """
    activate_container_for_split(
        db=db,
        split_id=split_id,
        qr_code=payload.qr_code,
        user_id=current_user.user_id
    )
    return get_split_by_id(db=db, split_id=split_id, current_user=current_user)


# ============================================================================
# TRANSICIÓN DE ESTADOS Y CIERRE DE LOTE
# ============================================================================

""" POST /splits/{split_id}/advance-status - Transición del lote (2do Filtro, Regreso a Piso o Sellado) """
@router.post(
    "/splits/{split_id}/advance-status",
    response_model=WarehouseSplitResponse
)
def advance_split_status_route(
    split_id: UUID,
    payload: WarehouseAdvanceStatusRequest = WarehouseAdvanceStatusRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(
        "warehouse.filter2_send",
        "warehouse.seal_direct",
        "warehouse.operator",
        "warehouse.checker",
        "warehouse.supervisor",
        "warehouse.manage",
        "system.admin"
    ))
):
    """
    Avanza el estado del lote en la máquina de estados del almacén:
    1. Regresar a Surtido por discrepancia (`in_progress`/`picking`): Exige 'warehouse.checker'.
    2. Enviar a 2do Filtro (`ready_for_check`/`checking`): Exige 'warehouse.filter2_send'.
    3. Cierre y sellado definitivo (`completed` o precinto):
       - Si viene de 2do filtro: Exige 'warehouse.checker'.
       - Si viene directo de piso: Exige 'warehouse.seal_direct'.
    """
    has_perm = getattr(current_user, "has_permission", lambda p: False)
    is_admin_or_super = current_user.role_id == 1 or has_perm("system.admin") or has_perm("warehouse.manage") or has_perm("warehouse.supervisor")

    # 1. Regresar a surtido por discrepancia detectada en mesa de control
    if payload.new_status in ["in_progress", "picking"]:
        if not (is_admin_or_super or has_perm("warehouse.checker")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para devolver un lote a surtido (warehouse.checker)"
            )

    # 2. Enviar a Segundo Filtro
    elif payload.new_status in ["ready_for_check", "checking"]:
        if not (is_admin_or_super or has_perm("warehouse.filter2_send")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para enviar splits a segundo filtro (warehouse.filter2_send)"
            )

    # 3. Cierre y sellado inviolable (completed o folio de precinto de seguridad)
    else:
        from db.base import WarehouseSplit as WSModel
        split_obj = db.query(WSModel).filter(WSModel.split_id == split_id).first()
        is_sealing_from_checker = split_obj and (split_obj.status in ["ready_for_check", "checking"])
        if is_sealing_from_checker:
            if not (is_admin_or_super or has_perm("warehouse.checker")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para sellar la revisión de segundo filtro (warehouse.checker)"
                )
        else:
            if not (is_admin_or_super or has_perm("warehouse.seal_direct")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para sellar y finalizar directamente en piso (warehouse.seal_direct)"
                )

    return advance_split_status(
        db=db,
        split_id=split_id,
        user_id=current_user.user_id,
        security_seal_folio=payload.security_seal_folio,
        force_status=payload.new_status
    )


""" POST /splits/{split_id}/checker-fast-track - Validación en bloque confiando en surtido de piso """
@router.post(
    "/splits/{split_id}/checker-fast-track",
    response_model=WarehouseSplitResponse
)
def checker_fast_track_route(
    split_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.supervisor", "system.admin"))
):
    """
    Autoriza por fast-track el segundo filtro copiando automáticamente las cantidades verificadas
    en el primer filtro de piso, permitiendo un despacho expedito sin conteo ciego pieza por pieza.
    """
    return fast_track_approve_second_filter(
        db=db,
        split_id=split_id,
        user_id=current_user.user_id
    )
