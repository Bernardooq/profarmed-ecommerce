"""
Schemas para Pedidos (Orders) y OrderItems

Sistema completo de pedidos con:
- Creacion de pedidos por clientes
- Asignacion a vendedores por admin/marketing
- Seguimiento de estados
- Items con precios congelados al momento del pedido

Flujo tipico:
1. Cliente crea pedido (status: pending_validation)
2. Admin/Marketing asigna a vendedor (status: assigned)
3. Vendedor aprueba (status: approved)
4. Se envia (status: shipped)
5. Se entrega (status: delivered)
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from db.base import OrderStatus
from .product import Product


# ORDER USER (Usuario simplificado para pedidos)

class OrderUser(BaseModel):
    """
    Schema simplificado de usuario/cliente para mostrar en pedidos
    
    Puede representar tanto un usuario interno (seller, admin)
    como un cliente (customer). Se distinguen por que ID esta presente.
    """
    user_id: Optional[int] = None  # Para usuarios internos (seller, admin, marketing)
    customer_id: Optional[int] = None  # Para clientes
    username: str  # Nombre de usuario
    email: Optional[str] = None  # Email
    full_name: Optional[str] = None  # Nombre completo

    model_config = {"from_attributes": True}


# ORDER ITEMS (Items del pedido)

class OrderItemBase(BaseModel):
    """Schema base de item de pedido"""
    product_id: str  # ID del producto (tipo texto)
    quantity: int = Field(..., gt=0)  # Cantidad (debe ser > 0)


class OrderItemCreate(OrderItemBase):
    """
    Schema para agregar un producto al pedido
    
    Solo se necesita el ID del producto y la cantidad.
    Los precios se calculan automaticamente en el backend.
    """
    pass


class OrderItem(OrderItemBase):
    """
    Schema completo de item de pedido
    
    Los precios se "congelan" al momento de crear el pedido,
    manteniendo un historial preciso aunque los precios cambien despues.
    """
    order_item_id: UUID  # ID unico del item
    # Precios congelados (snapshot al momento del pedido)
    base_price: Optional[Decimal] = None  # Precio base (solo admin)
    markup_percentage: Optional[Decimal] = None  # % de markup (solo admin)
    iva_percentage: Decimal  # % de IVA cuando se ordeno
    price_without_iva: Optional[Decimal] = None  # Precio con markup SIN IVA (solo admin)
    final_price: Decimal  # Precio final CON IVA
    discount_applied: Optional[Decimal] = Field(default=Decimal("0.00"))  # % descuento aplicado
    discount_type: Optional[str] = None  # Tipo de descuento ('general', 'price_list' o None)
    # Trazabilidad de bodega
    split_id: Optional[UUID] = None
    box_prods: int = 0
    scanned_prods: int = 0
    manual_prods: int = 0
    item_status: str = "pending"
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    product: Optional[Product] = None  # Informacion del producto (opcional)

    model_config = {"from_attributes": True}


# ORDERS (Pedidos)

class OrderBase(BaseModel):
    """Schema base de pedido"""
    status: OrderStatus = OrderStatus.pending_validation  # Estado inicial


class OrderCreate(OrderBase):
    """
    Schema para crear un nuevo pedido
    
    El cliente solo especifica que direccion usar (1, 2 o 3).
    Los items se agregan despues con OrderItemCreate.
    """
    shipping_address_number: Optional[int] = Field(None, ge=1, le=3)  # Cual direccion usar (1, 2 o 3)
    shipping_cost: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)  # Costo de envío
    order_notes: Optional[str] = None  # Notas del pedido escritas por el cliente
    invoice_type: Optional[str] = Field("factura", description="Tipo de comprobante: factura, remision, etc.")


class OrderUpdate(BaseModel):
    """
    Schema para actualizar un pedido
    
    Usado principalmente para cambiar estado o asignar usuario responsable.
    """
    status: Optional[OrderStatus] = None  # Cambiar estado
    assigned_user_id: Optional[int] = None  # Asignar/cambiar usuario responsable
    shipping_address_number: Optional[int] = Field(None, ge=1, le=3)  # Cambiar direccion
    assignment_notes: Optional[str] = None  # Notas al asignar
    shipping_cost: Optional[Decimal] = Field(None, ge=0)  # Costo de envío
    invoice_type: Optional[str] = Field(None, description="Tipo de comprobante: factura, remision, etc.")
    is_synced: Optional[bool] = Field(None, description="Estado de sincronización ERP")


class OrderAssign(BaseModel):
    """
    Schema especifico para asignar un pedido a un usuario responsable
    
    Usado por administracion para delegar pedidos.
    """
    assigned_user_id: Optional[int] = None  # ID del usuario a asignar
    assignment_notes: Optional[str] = None  # Notas sobre la asignacion


class OrderItemEdit(BaseModel):
    """
    Schema para editar items de un pedido existente
    
    Si order_item_id es None, es un nuevo producto a agregar.
    Si existe, se actualiza la cantidad de ese item.
    """
    order_item_id: Optional[UUID] = None  # ID del item existente (None para nuevos)
    product_id: str  # ID del producto
    quantity: int = Field(..., gt=0)  # Nueva cantidad


class OrderEditRequest(BaseModel):
    """
    Schema para solicitud de edición de pedido
    
    Permite actualizar los items de un pedido, costos, notas y estado de sincronización.
    Los precios se recalculan automáticamente en el backend.
    """
    items: List[OrderItemEdit]  # Lista de items actualizados
    shipping_cost: Optional[Decimal] = Field(None, ge=0)
    assignment_notes: Optional[str] = None
    shipping_address_number: Optional[int] = Field(None, ge=1, le=3)
    invoice_type: Optional[str] = None
    is_synced: Optional[bool] = None


class Order(OrderBase):
    """
    Schema completo de pedido para responses
    
    Incluye toda la informacion del pedido con relaciones.
    """
    order_id: int  # ID unico del pedido (BIGSERIAL)
    customer_id: int  # ID del cliente que hizo el pedido (cambio de user_id)
    assigned_user_id: Optional[int] = None  # ID del usuario asignado
    assigned_by_user_id: Optional[int] = None  # ID de quien hizo la asignacion (si hay)
    total_amount: Decimal  # Monto total del pedido
    order_profit: Optional[Decimal] = None  # Ganancia por markup (solo admin)
    shipping_cost: Decimal = Decimal("0.00")  # Costo de envío
    shipping_address_number: Optional[int] = None  # Que direccion se usa (1, 2 o 3)
    shipping_address_snapshot: Optional[str] = None  # Direccion completa al momento del pedido
    assignment_notes: Optional[str] = None  # Notas de asignacion
    order_notes: Optional[str] = None  # Notas del pedido escritas por el cliente
    invoice_type: str = "factura"  # Tipo de comprobante: factura, remision, etc.
    
    # Control de bodega / almacen
    sent_to_warehouse: bool = False
    warehouse_status: Optional[str] = None
    total_splits: int = 1
    warehouse_sent_by: Optional[int] = None
    warehouse_sent_at: Optional[datetime] = None
    warehouse_show_details: bool = False
    
    # Control de sincronización ERP (cotiza3)
    is_synced: bool = False
    
    # Timestamps
    created_at: datetime  # Cuando se creo el pedido
    assigned_at: Optional[datetime] = None  # Cuando se asigno usuario
    validated_at: Optional[datetime] = None  # Cuando se aprobo
    
    # Relaciones
    items: List[OrderItem] = []  # Lista de productos en el pedido
    customer: Optional[OrderUser] = None  # Informacion del cliente
    assigned_user: Optional[OrderUser] = None  # Informacion del usuario asignado
    assigned_by: Optional[OrderUser] = None  # Informacion de quien asigno

    # Campo extra — NO está en el ORM Order. Lo inyecta el route handler
    # a partir de un batch lookup de CustomerInfo → sales_group_id.
    sales_group_id: Optional[int] = None
    items_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class OrderWithAddress(Order):
    """
    Pedido con la direccion de envio completa
    
    Incluye el texto completo de la direccion seleccionada,
    no solo el numero (1, 2 o 3).
    
    util para mostrar en detalles de pedido o para impresion.
    """
    shipping_address: Optional[str] = None  # Direccion completa basada en shipping_address_number
    customerInfo: Optional[dict] = None  # Informacion completa del cliente (RFC, business_name, telefonos)



