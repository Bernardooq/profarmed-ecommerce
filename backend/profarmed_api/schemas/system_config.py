"""
Schemas de Pydantic para Configuraciones del Sistema (system_configs)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SystemConfigBase(BaseModel):
    config_name: str = Field(..., max_length=100, description="Nombre único identificador de la configuración")
    description: Optional[str] = Field(None, max_length=255, description="Descripción de la función de la configuración")
    is_active: bool = Field(False, description="Estado de activación de la configuración")


class SystemConfigUpdate(BaseModel):
    """Solo se permite actualizar el estado is_active"""
    is_active: bool = Field(..., description="Nuevo estado booleano para la configuración")


class SystemConfigResponse(SystemConfigBase):
    config_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
