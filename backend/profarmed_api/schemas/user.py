"""
Schemas para Usuarios Internos del Sistema

Define la estructura de datos para usuarios que trabajan en el sistema:
- Admins: Acceso completo
- Marketing: Gestion de grupos y clientes
- Sellers: Procesamiento de pedidos

NOTA: Los clientes estan en schemas/customer.py (tabla separada)
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Union
from datetime import datetime

class UserBase(BaseModel):
    """Schema base con campos comunes de usuario"""
    username: str = Field(..., min_length=3, max_length=50)  # Nombre de usuario unico
    email: Optional[EmailStr] = None  # Email (opcional)
    full_name: Optional[str] = Field(None, max_length=255)  # Nombre completo

class UserCreate(UserBase):
    """
    Schema para crear un nuevo usuario interno
    
    Requiere contraseña. Puede especificar role_id numérico o role slug dinámico.
    Admin puede opcionalmente asignar un ID manual.
    """
    user_id: Optional[int] = Field(None, gt=0, description="ID manual (opcional, se auto-genera si no se proporciona)")
    password: str = Field(..., min_length=8)  # Contraseña (minimo 8 caracteres)
    role_id: Optional[int] = Field(None, description="ID numérico del rol asignado")
    role: Optional[str] = Field(None, description="Slug del rol dinámico")
    is_active: Optional[bool] = True  # Usuario activo por defecto

class UserUpdate(BaseModel):
    """
    Schema para actualizar un usuario existente
    
    Todos los campos son opcionales (solo se actualiza lo que se envia).
    """
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8)  # Nueva contraseña (opcional)
    role_id: Optional[int] = None
    role: Optional[str] = Field(None, description="Slug del rol dinámico")  # Cambiar rol (opcional)
    is_active: Optional[bool] = None  # Activar/desactivar (opcional)
    failed_login_attempts: Optional[int] = Field(None, description="Conteo de intentos fallidos de contraseña")
    is_locked: Optional[bool] = Field(None, description="Estado de bloqueo por seguridad")
    notificate: Optional[bool] = None

class UserInDBBase(UserBase):
    """
    Schema base para usuarios en la base de datos
    
    Incluye campos generados automaticamente (ID, timestamps, etc.)
    """
    user_id: int  # ID unico del usuario
    role_id: Optional[int] = None  # ID de la FK de rol
    role: Optional[str] = None  # Slug del rol para compatibilidad con frontend
    is_active: bool  # Estado activo/inactivo
    failed_login_attempts: int = 0
    is_locked: bool = False
    locked_at: Optional[datetime] = None
    created_at: datetime  # Fecha de creacion

    model_config = {
        "from_attributes": True  # Permite crear desde modelo SQLAlchemy
    }

class User(UserInDBBase):
    """
    Schema completo de usuario para responses de la API
    
    Incluye detalle del rol y lista de permisos del usuario.
    No incluye el password_hash por seguridad.
    """
    role_name: Optional[str] = None
    role_slug: Optional[str] = None
    permissions: List[str] = Field(default_factory=list, description="Lista de códigos de permisos asignados")


class UserInDB(UserInDBBase):
    """
    Schema de usuario con password hash
    
    Solo se usa internamente, NUNCA se envia al frontend.
    """
    password_hash: str


class UserSync(BaseModel):
    """
    Schema para sincronización masiva de colaboradores / usuarios desde DBF.
    Conserva compatibilidad total con FoxPro legacy y la API moderna.
    """
    user_id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    is_active: bool = True
    updated_at: Optional[datetime] = None


class UserRoleChangeRequest(BaseModel):
    """
    Schema para cambiar el rol de un usuario.
    """
    role: str = Field(..., description="Slug del nuevo rol (ej: 'seller', 'marketing', 'warehouse', etc.)")


# ============================================================================
# RECUPERACIÓN DE CONTRASEÑA (PASSWORD RESET OTP)
# ============================================================================

class PasswordResetRequest(BaseModel):
    """
    Solicitud de código de restablecimiento de contraseña.
    """
    username: str = Field(..., min_length=1, description="Nombre de usuario del cliente o colaborador")


class PasswordResetVerify(BaseModel):
    """
    Verificación de código de 6 dígitos.
    """
    username: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=50)


class PasswordResetConfirm(BaseModel):
    """
    Confirmación y cambio definitivo de contraseña tras verificar código.
    """
    username: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=50)
    new_password: str = Field(..., min_length=6, description="Nueva contraseña segura")


class PasswordResetResponse(BaseModel):
    """
    Respuesta informativa de operaciones de restablecimiento.
    """
    message: str
    masked_emails: Optional[str] = None
    expires_in_seconds: Optional[int] = None
    valid: Optional[bool] = None

