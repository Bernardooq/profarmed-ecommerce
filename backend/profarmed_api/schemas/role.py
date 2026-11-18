"""
Schemas para Roles y Permisos (RBAC / PBAC Dinámico)

Define la estructura de datos para:
- Permissions (Catálogo de permisos y capacidades granulares)
- Roles (Roles dinámicos configurables por administradores)
- RolePermissions (Asignaciones N:M de permisos a roles)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==========================================
# SCHEMAS DE PERMISOS (SÓLO LECTURA)
# ==========================================

class PermissionBase(BaseModel):
    """Schema base con campos informativos de un permiso"""
    permission_code: str = Field(..., max_length=100, description="Código único identificador (ej: 'products.view')")
    module: str = Field(..., max_length=50, description="Módulo al que pertenece (ej: 'products', 'orders')")
    name: str = Field(..., max_length=150, description="Nombre legible para humanos")
    description: Optional[str] = Field(None, description="Descripción de lo que permite este permiso")
    depends_on: Optional[str] = Field(None, max_length=100, description="Permiso padre del cual depende (si aplica)")


class PermissionResponse(PermissionBase):
    """Schema de respuesta para un permiso del catálogo maestro del sistema"""
    created_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


# ==========================================
# SCHEMAS DE ROLES
# ==========================================

class RoleBase(BaseModel):
    """Schema base con campos comunes de un rol"""
    name: str = Field(..., min_length=2, max_length=100, description="Nombre descriptivo del rol (ej: 'Administrador')")
    slug: str = Field(..., min_length=2, max_length=50, description="Slug único identificador en minúsculas (ej: 'admin', 'seller')")
    description: Optional[str] = Field(None, description="Descripción del rol y responsabilidades")
    is_active: bool = Field(True, description="Indica si el rol está activo en el sistema")


class RoleCreate(RoleBase):
    """Schema para crear un nuevo rol junto con su conjunto inicial de permisos"""
    permissions: List[str] = Field(default_factory=list, description="Lista de códigos de permisos asignados al rol")


class RoleUpdate(BaseModel):
    """Schema para actualizar un rol existente y/o sus permisos asignados"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = Field(None, description="Lista de códigos de permisos (reemplaza los existentes si se especifica)")


class RoleResponse(RoleBase):
    """Schema de respuesta estándar para un rol"""
    role_id: int
    is_system: bool = Field(False, description="Indica si es un rol protegido del sistema")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class RoleWithPermissionsResponse(RoleResponse):
    """Schema de respuesta para un rol incluyendo la lista detallada de permisos asignados"""
    permissions: List[str] = Field(default_factory=list, description="Códigos de permisos asignados")
    permissions_detail: Optional[List[PermissionResponse]] = Field(default_factory=list, description="Detalle completo de permisos")

    model_config = {
        "from_attributes": True
    }


class RolePermissionsAssignRequest(BaseModel):
    """Schema para asignar o revocar permisos masivamente a un rol"""
    permissions: Optional[List[str]] = Field(None, description="Lista completa de permission_codes que tendrá el rol")
    permission_slugs: Optional[List[str]] = Field(None, description="Alias para compatibilidad frontend")

    @property
    def final_permissions(self) -> List[str]:
        if self.permissions is not None:
            return self.permissions
        if self.permission_slugs is not None:
            return self.permission_slugs
        return []
