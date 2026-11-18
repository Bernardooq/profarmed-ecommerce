"""
Routes para Parque Físico y Mantenimiento de Canastas QR Reutilizables (Containers / Totes)

Gestiona el ciclo de vida del parque físico de canastas/totes de surtido en almacén:
- Consulta, búsqueda por código QR y filtrado por estado operativo (available, in_use, maintenance, retired).
- Alta, actualización de estado y baja física de contenedores.
- Liberación atómica de canastas vinculadas a splits de surtido.

ENDPOINTS:
- GET /containers - Listar todas las canastas del parque físico (requiere 'warehouse.view' o 'warehouse.containers')
- GET /containers/{id} - Obtener canasta por UUID interno (requiere 'warehouse.view' o 'warehouse.containers')
- GET /containers/by-qr/{qr} - Consultar canasta por código QR físico escaneado (requiere 'warehouse.operator')
- POST /containers - Registrar nueva canasta física en el sistema (requiere 'warehouse.containers')
- PUT /containers/{id} - Actualizar estado operativo de una canasta (requiere 'warehouse.containers')
- DELETE /containers/{id} - Eliminar canasta del parque (requiere 'warehouse.containers')
- POST /containers/release - Liberar canasta en uso y marcarla como disponible (requiere 'warehouse.operator')

Sistema de Permisos: PBAC dinámico según PERMISSIONS_AND_CONSTRAINTS.md
"""

from typing import Optional, List, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from db.base import User
from dependencies import get_db, require_permission
from crud.crud_warehouse import (
    list_warehouse_containers,
    get_warehouse_containers_stats,
    get_warehouse_container_by_id,
    get_warehouse_container_by_qr,
    create_warehouse_container,
    update_warehouse_container_status,
    release_warehouse_container,
    delete_warehouse_container,
)
from schemas.warehouse import (
    WarehouseContainerResponse,
    WarehouseContainerCreate,
    WarehouseContainerUpdate,
    WarehouseReleaseContainerRequest,
)

router = APIRouter()


# ============================================================================
# CONSULTA Y BÚSQUEDA DE CANASTAS QR
# ============================================================================

""" GET /containers/stats - Métricas consolidadas del parque físico de canastas QR """
@router.get(
    "/containers/stats",
    response_model=Dict[str, int]
)
def get_containers_stats_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.containers", "warehouse.manage", "system.admin"))
):
    """
    Retorna los conteos totales y por estado físico de todas las canastas QR.
    """
    return get_warehouse_containers_stats(db=db)


""" GET /containers - Listar todas las canastas físicas con filtros de estado y búsqueda """
@router.get(
    "/containers",
    response_model=List[WarehouseContainerResponse]
)
def list_containers_route(
    status: Optional[str] = Query(None, description="Filtrar por estado: 'available', 'in_use', 'maintenance', 'retired'"),
    search: Optional[str] = Query(None, description="Búsqueda por código QR, ID o split"),
    skip: int = Query(0, ge=0, description="Paginación skip"),
    limit: int = Query(100, ge=1, le=500, description="Límite de resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.containers", "warehouse.manage", "system.admin"))
):
    """
    Devuelve el catálogo de canastas QR físicas registradas en la bodega.
    
    Permite a los supervisores auditar qué canastas están activas en piso, cuáles
    se encuentran en mantenimiento y cuáles están libres para nuevos lotes.
    """
    return list_warehouse_containers(db=db, status_filter=status, search=search, skip=skip, limit=limit)


""" GET /containers/{container_id} - Obtener información detallada de una canasta por UUID """
@router.get(
    "/containers/{container_id}",
    response_model=WarehouseContainerResponse
)
def get_container_by_id_route(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.containers", "warehouse.manage", "system.admin"))
):
    """
    Obtiene el registro maestro de una canasta por su identificador UUID.
    """
    c = get_warehouse_container_by_id(db, container_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Canasta #{container_id} no encontrada")
    return c


""" GET /containers/by-qr/{qr_code} - Búsqueda en tiempo real por escaneo de QR físico """
@router.get(
    "/containers/by-qr/{qr_code}",
    response_model=WarehouseContainerResponse
)
def get_container_by_qr_route(
    qr_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.view", "warehouse.operator", "warehouse.checker", "warehouse.containers", "warehouse.manage", "system.admin"))
):
    """
    Identifica una canasta física al ser escaneada con la pistola lectora o cámara.
    
    Verifica si la canasta existe, su estado actual y si ya se encuentra asignada
    a otro lote en proceso o libre para recolección.
    """
    c = get_warehouse_container_by_qr(db, qr_code)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Canasta con QR '{qr_code}' no encontrada")
    return c


# ============================================================================
# ADMINISTRACIÓN Y CICLO DE VIDA DE CANASTAS
# ============================================================================

""" POST /containers - Dar de alta una nueva canasta QR física en el sistema """
@router.post(
    "/containers",
    response_model=WarehouseContainerResponse,
    status_code=status.HTTP_201_CREATED
)
def create_container_route(
    payload: WarehouseContainerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.containers", "warehouse.manage", "system.admin"))
):
    """
    Registra una nueva canasta o tote físico en el parque de almacén.
    
    El código QR debe ser único. Inicialmente se crea en estado `available`.
    """
    return create_warehouse_container(db=db, qr_code=payload.qr_code)


""" PUT /containers/{container_id} - Actualizar estado operativo de una canasta """
@router.put(
    "/containers/{container_id}",
    response_model=WarehouseContainerResponse
)
def update_container_status_route(
    container_id: UUID,
    payload: WarehouseContainerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.containers", "warehouse.manage", "system.admin"))
):
    """
    Actualiza el estado operativo de la canasta (ej: enviar a reparación o dar de baja).
    """
    if not payload.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere el campo 'status'")
    return update_warehouse_container_status(db=db, container_id=container_id, new_status=payload.status)


""" DELETE /containers/{container_id} - Eliminar una canasta del sistema """
@router.delete("/containers/{container_id}")
def delete_container_route(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.containers", "warehouse.manage", "system.admin"))
):
    """
    Elimina físicamente el registro de la canasta del catálogo maestro.
    
    Restricción: No se puede eliminar una canasta si está actualmente en uso en un lote activo.
    """
    delete_warehouse_container(db=db, container_id=container_id)
    return {"success": True, "message": f"Canasta #{container_id} eliminada exitosamente"}


""" POST /containers/release - Liberar manualmente una canasta física """
@router.post(
    "/containers/release",
    response_model=WarehouseContainerResponse
)
def release_container_route(
    payload: WarehouseReleaseContainerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("warehouse.operator", "warehouse.checker", "warehouse.supervisor", "warehouse.manage", "system.admin"))
):
    """
    Libera la vinculación física de una canasta hacia un split, marcándola como `available`.
    
    Útil cuando una canasta se daña durante el surtido o se completa el vaciado en empaque.
    """
    return release_warehouse_container(
        db=db,
        qr_code=payload.qr_code,
        container_id=payload.container_id,
        current_user=current_user,
        empty_items=payload.empty_items or False
    )
