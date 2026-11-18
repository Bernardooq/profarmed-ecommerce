"""
Schemas para Grupos de Ventas (SalesGroups)

Los grupos de ventas organizan la estructura comercial:
- Multiples users/managers pueden administrar un grupo
- Multiples users/sellers pueden atender un grupo
- Multiples customers pertenecen a un grupo

Esto permite segmentar clientes y asignar equipos especificos.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# SALES GROUPS (Grupos de Ventas)

class SalesGroupBase(BaseModel):
    """Schema base con campos comunes de grupo de ventas"""
    group_name: str = Field(..., max_length=255)  # Nombre del grupo (ej: "Farmacias Zona Norte")
    description: Optional[str] = None  # Descripcion del grupo


class SalesGroupCreate(SalesGroupBase):
    """
    Schema para crear un nuevo grupo de ventas
    
    Por defecto se crea activo.
    """
    is_active: Optional[bool] = True  # Activo por defecto


class SalesGroupUpdate(BaseModel):
    """
    Schema para actualizar un grupo existente
    
    Todos los campos son opcionales.
    """
    group_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None  # Activar/desactivar grupo


class SalesGroupInDBBase(SalesGroupBase):
    """Schema base de grupo en la base de datos"""
    sales_group_id: int  # ID unico del grupo
    is_active: bool  # Estado del grupo
    created_at: datetime  # Fecha de creacion

    model_config = {"from_attributes": True}


class SalesGroup(SalesGroupInDBBase):
    """Schema completo de grupo para responses"""
    pass


# GROUP USERS (N:M Relationship Unificada)

class GroupUserBase(BaseModel):
    """
    Relación N:M entre un grupo de ventas y un usuario (marketing o seller).
    PK compuesta: (sales_group_id, user_id).
    """
    sales_group_id: int
    user_id: int


class GroupUserCreate(GroupUserBase):
    """Schema para asignar un usuario a un grupo"""
    pass


class GroupUserInDBBase(GroupUserBase):
    """Schema de relación en base de datos"""
    assigned_at: datetime

    model_config = {"from_attributes": True}


class GroupUser(GroupUserInDBBase):
    """Schema completo de la relación para responses"""
    pass





# ASSIGNMENT SCHEMAS (para requests de asignacion)

class UserAssignment(BaseModel):
    """Schema para asignar un usuario a un grupo via POST body"""
    user_id: int


# SCHEMAS EXTENDIDOS

class RoleMemberBreakdown(BaseModel):
    """Desglose dinámico de miembros asignados al grupo por rol"""
    role_id: int
    name: str
    slug: str
    count: int

class SalesGroupWithMembers(SalesGroupInDBBase):
    """
    Grupo con contadores de miembros y estadisticas de pedidos (N roles dinámicos).
    """
    member_count: Optional[int] = 0
    members_by_role: Optional[List[RoleMemberBreakdown]] = None
    customer_count: Optional[int] = 0
    order_stats: Optional[dict] = None

class SalesGroupPaginatedResponse(BaseModel):
    items: List[SalesGroupWithMembers]
    total: int
