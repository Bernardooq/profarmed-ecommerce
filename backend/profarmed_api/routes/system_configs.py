"""
Routes para Configuraciones del Sistema (system_configs)
Protegidas exclusivamente para administradores con el permiso system.admin.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from dependencies import get_db, require_permission
from db.base import User
from schemas.system_config import SystemConfigResponse, SystemConfigUpdate
from crud.crud_system_config import get_system_configs, get_system_config_by_id, update_system_config_active

router = APIRouter()


@router.get("", response_model=List[SystemConfigResponse], summary="Listar configuraciones del sistema")
@router.get("/", response_model=List[SystemConfigResponse], include_in_schema=False)
def list_configs(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Límite de registros"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre o descripción"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin"))
):
    """
    Lista configuraciones globales del sistema con paginación y búsqueda.
    Acceso restringido estrictamente a administradores del sistema.
    """
    items, _ = get_system_configs(db, skip=skip, limit=limit, search=search)
    return items


@router.put("/{config_id}", response_model=SystemConfigResponse, summary="Actualizar estado activo de una configuración")
def update_config_status(
    config_id: int,
    payload: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin"))
):
    """
    Actualiza exclusivamente el campo is_active de una configuración del sistema.
    Acceso restringido estrictamente a administradores del sistema.
    """
    updated = update_system_config_active(db, config_id=config_id, config_update=payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuración con ID {config_id} no encontrada"
        )
    return updated
