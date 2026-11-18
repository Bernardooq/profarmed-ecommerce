"""
Modelos SQLAlchemy para PROFARMED v2.2 (PBAC & RBAC Dinámico)

Arquitectura de base de datos:
- Los usuarios internos y colaboradores con N roles dinámicos están en la tabla 'users'
- Catálogo maestro de roles dinámicos ('roles') y permisos jerárquicos PBAC ('permissions', 'role_permissions')
- Los clientes están separados en la tabla 'customers'
- Relaciones N:M unificadas para grupos de ventas ('salesgroups', 'group_users')
- Listas de precios con markup por producto ('pricelists', 'pricelistitems')
- Sistema de pedidos con asignación de agentes comerciales ('orders', 'orderitems')
- Operación y logística física de almacén ('warehouse_splits', 'order_item_split_fulfillment')
"""

import enum
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, Enum as SQLAlchemyEnum, 
    ForeignKey, Numeric, TIMESTAMP, func, Text, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
import uuid6
from sqlalchemy.orm import relationship, declarative_base, column_property

# Clase base de la que heredan todos los modelos
Base = declarative_base()


# ENUMS - Tipos enumerados para campos especificos


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    cancelled = "cancelled"
    escalated = "escalated"

class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class CreatorType(str, enum.Enum):
    customer = "customer"
    user = "user"  # Colaborador / Usuario interno con rol dinámico

class SenderType(str, enum.Enum):
    customer = "customer"
    user = "user"

class OrderStatus(str, enum.Enum):
    """
    Estados del ciclo de vida de un pedido
    
    - pending_validation: Pedido creado, esperando asignación o validación
    - approved: Colaborador autorizado aprobó el pedido
    - shipped: Pedido en tránsito o despachado
    - delivered: Entregado al cliente
    - cancelled: Cancelado (por colaborador autorizado o cliente)
    """
    pending_validation = "pending_validation"
    approved = "approved"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


# MODELOS - Definicion de tablas

class Role(Base):
    """
    Roles dinámicos del sistema para usuarios internos (PBAC / RBAC).
    Controla el conjunto de permisos y facultades de los colaboradores de la empresa.
    """
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    users = relationship("User", back_populates="role_rel")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan", lazy="joined")


class Permission(Base):
    """
    Catálogo maestro PBAC de permisos del sistema.
    Define capacidades granulares con soporte de jerarquía mediante depends_on.
    """
    __tablename__ = "permissions"

    permission_code = Column(String(100), primary_key=True)
    module = Column(String(50), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    depends_on = Column(String(100), ForeignKey("permissions.permission_code", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relación jerárquica reflexiva (auto-referencia)
    parent_permission = relationship("Permission", remote_side=[permission_code], backref="child_permissions")
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    """
    Matriz relacional N:M de permisos asignados a cada rol del sistema.
    """
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
    permission_code = Column(String(100), ForeignKey("permissions.permission_code", ondelete="CASCADE"), primary_key=True)
    granted_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relaciones
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles", lazy="joined")


class User(Base):
    """
    Usuarios INTERNOS del sistema con asignación de roles dinámicos PBAC.
    
    Esta tabla NO incluye clientes. Los clientes están en 'customers'.
    Estos usuarios son empleados, colaboradores o agentes comerciales de PROFARMED vinculados a un rol dinámico en 'roles'.
    
    NOTA: user_id puede ser asignado manualmente o auto-generado.
    """
    __tablename__ = "users"

    # Campos principales
    # IMPORTANTE: autoincrement=False fuerza a SQLAlchemy a enviar el user_id en el INSERT
    # Esto permite asignación manual de IDs
    # RANGOS: Agentes comerciales 1-9000, Administración y otros roles 9001+
    user_id = Column(Integer, primary_key=True, autoincrement=False)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), index=True)
    password_hash = Column(String(255), nullable=False)  # Hash Argon2
    full_name = Column(String(255))
    role_id = Column(Integer, ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active = Column(Boolean, default=True)  # Para desactivar usuarios sin eliminarlos
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Constraint: user_id debe ser positivo
    __table_args__ = (
        CheckConstraint('user_id > 0', name='check_user_id_positive'),
    )

    # Relaciones con otras tablas
    # Relación con su Rol
    role_rel = relationship("Role", back_populates="users", lazy="joined")

    # Pedidos donde este usuario es el colaborador/usuario asignado
    orders_assigned = relationship("Order", back_populates="assigned_user", foreign_keys="[Order.assigned_user_id]")
    # Pedidos donde este usuario hizo la asignacion (quien asigno el colaborador)
    orders_assigned_by = relationship("Order", back_populates="assigned_by", foreign_keys="[Order.assigned_by_user_id]")
    # Membresías en grupos de venta (unificado N:M)
    group_memberships = relationship("GroupUser", back_populates="user", cascade="all, delete-orphan")
    # Clientes asignados a este usuario como agente comercial (sincronizados desde DBF)
    customers_as_agent = relationship("Customer", back_populates="agent", foreign_keys="[Customer.agent_id]")

    @property
    def role(self):
        """
        Retorna el slug del rol dinámico asignado (ej: 'admin', 'seller', etc.).
        """
        if self.role_rel:
            return self.role_rel.slug
        return None

    @role.setter
    def role(self, value):
        """Asigna el rol del usuario mediante instancia de Role o role_id."""
        if hasattr(value, "role_id"):
            self.role_id = value.role_id
            self.role_rel = value

    @property
    def role_slug(self):
        return self.role_rel.slug if self.role_rel else None

    @property
    def role_name(self):
        return self.role_rel.name if self.role_rel else None

    @property
    def permissions(self):
        """Lista plana de códigos de permisos asignados a través de su rol."""
        if self.role_rel and getattr(self.role_rel, "permissions", None):
            return [rp.permission_code for rp in self.role_rel.permissions]
        return []

    def has_permission(self, permission_code: str, _visited: Optional[set] = None) -> bool:
        """
        Verifica si el usuario posee un permiso específico (admin posee todos).
        Si el permiso depende de otro permiso (depends_on), valida que el usuario
        también posea el permiso del cual depende para conceder el acceso efectivo.
        """
        if self.role == "admin" or (self.role_rel and self.role_rel.slug == "admin"):
            return True
        if permission_code not in self.permissions:
            return False

        # Prevenir posibles ciclos en el grafo de dependencias
        if _visited is None:
            _visited = set()
        if permission_code in _visited:
            return True
        _visited.add(permission_code)

        # Validar la jerarquía de dependencias contra la relación RolePermission
        if self.role_rel and getattr(self.role_rel, "permissions", None):
            for rp in self.role_rel.permissions:
                if rp.permission_code == permission_code and rp.permission and rp.permission.depends_on:
                    parent_code = rp.permission.depends_on
                    if not self.has_permission(parent_code, _visited):
                        return False

        return True


class Customer(Base):
    """
    Clientes del e-commerce (SEPARADO de Users)
    
    Los clientes son usuarios externos que compran productos.
    Tienen su propia tabla separada de usuarios internos.
    
    NOTA: agent_id vincula al cliente con un agente comercial específico (agente del DBF).
    """
    __tablename__ = "customers"

    # Campos principales (similares a User pero en tabla separada)
    customer_id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), index=True)  # Email NO es único - varios clientes pueden compartirlo
    password_hash = Column(String(255), nullable=False)  # Hash Argon2
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Agente comercial asignado desde el DBF (opcional)
    agent_id = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    notificate = Column(Boolean, nullable=False, default=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones con otras tablas
    # Informacion adicional del cliente (direcciones, grupo, lista de precios)
    customer_info = relationship("CustomerInfo", back_populates="customer", uselist=False)
    # Pedidos realizados por este cliente
    orders = relationship("Order", back_populates="customer")
    # Carrito de compras temporal
    cart_cache = relationship("CartCache", back_populates="customer", cascade="all, delete")
    # Agente comercial asignado a este cliente
    agent = relationship("User", back_populates="customers_as_agent", foreign_keys=[agent_id])
    # Listas de compras favoritas
    favorite_lists = relationship("FavoriteList", back_populates="customer", cascade="all, delete-orphan")

    # Propiedades para aplanar el acceso a CustomerInfo (facilita serializacion Pydantic)
    @property
    def rfc(self):
        return self.customer_info.rfc if self.customer_info else None

    @property
    def business_name(self):
        return self.customer_info.business_name if self.customer_info else None

    @property
    def price_list_id(self):
        return self.customer_info.price_list_id if self.customer_info else None

    @property
    def sales_group_id(self):
        return self.customer_info.sales_group_id if self.customer_info else None

    @property
    def address_1(self):
        return self.customer_info.address_1 if self.customer_info else None

    @property
    def address_2(self):
        return self.customer_info.address_2 if self.customer_info else None

    @property
    def address_3(self):
        return self.customer_info.address_3 if self.customer_info else None

    @property
    def telefono_1(self):
        return self.customer_info.telefono_1 if self.customer_info else None

    @property
    def telefono_2(self):
        return self.customer_info.telefono_2 if self.customer_info else None


class PasswordReset(Base):
    """
    Códigos temporales para recuperación de contraseñas (Customer o User).
    Tiene ventana de expiración de 5 minutos y bandera 'allow' para autorizar el cambio.
    """
    __tablename__ = "password_resets"

    reset_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    code = Column(String(50), nullable=True)
    allow = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relaciones
    customer = relationship("Customer", foreign_keys=[customer_id])
    user = relationship("User", foreign_keys=[user_id])


class SalesGroup(Base):
    """
    Grupos de ventas para organizar clientes y miembros del equipo comercial
    
    Cada grupo puede tener:
    - Múltiples colaboradores y agentes comerciales asignados (relación N:M unificada en GroupUser)
    - Múltiples clientes asignados (CustomerInfo)
    """
    __tablename__ = "salesgroups"

    sales_group_id = Column(Integer, primary_key=True)
    group_name = Column(String(255), nullable=False)  # Ej: "Farmacias Zona Norte"
    description = Column(Text)  # Descripcion opcional del grupo
    is_active = Column(Boolean, default=True)  # Para desactivar sin eliminar
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relaciones N:M (muchos a muchos)
    # Usuarios miembros asignados a este grupo (unificado N:M)
    members = relationship("GroupUser", back_populates="sales_group", cascade="all, delete-orphan")
    # Clientes que pertenecen a este grupo
    customers = relationship("CustomerInfo", back_populates="sales_group")


class GroupUser(Base):
    """
    Tabla de relación N:M unificada entre SalesGroup y User.
    Reemplaza a groupmarketingmanagers y groupsellers.
    PK compuesta: (sales_group_id, user_id).
    """
    __tablename__ = "group_users"

    sales_group_id = Column(Integer, ForeignKey("salesgroups.sales_group_id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, index=True)
    assigned_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relaciones
    sales_group = relationship("SalesGroup", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class Category(Base):
    """
    Categorias para organizar productos
    
    Ejemplos: "Analgesicos", "Antibioticos", "Vitaminas", etc.
    """
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)  # Nombre de la categoria
    description = Column(Text)  # Descripcion opcional
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Productos que pertenecen a esta categoria
    products = relationship("Product", back_populates="category")


class Product(Base):
    """
    Productos del catalogo
    
    El precio final se calcula como:
    precio_final = (base_price + base_price * markup) * (1 + iva_percentage)
    Donde markup viene de la lista de precios del cliente
    """
    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True)  # ID tipo "FAR74" (no numerico)
    codebar = Column(String(100), nullable=True, index=True)  # Codigo de barras (puede ser None)
    name = Column(String(255), nullable=False)  # Nombre del producto
    description = Column(Text)  # Descripcion principal (del DBF/sincronizacion)
    descripcion_2 = Column(Text)  # Descripcion adicional (editable por admin, ej: receta medica)
    unidad_medida = Column(String(10))  # Unidad: "piezas", "cajas", "frascos", etc.
    base_price = Column(Numeric(10, 2), nullable=False, default=0.00)  # Precio base sin markup ni IVA
    iva_percentage = Column(Numeric(5, 2), default=0.00)  # % de IVA (ej: 16.00)
    image_url = Column(String(255), default=None)  # URL de la imagen del producto (puede ser None)
    image_version = Column(Integer, default=1)  # Version de la imagen para control de cache
    stock_count = Column(Integer, default=0)  # Cantidad en inventario
    location = Column(String(100), nullable=False, default="", server_default="")  # Ubicación / anaquel
    display_priority = Column(Integer, nullable=False, default=1000000, server_default="1000000", index=True)  # Prioridad en catálogo (1-999,999 fijo, >=1,000,000 rotativo)
    is_active = Column(Boolean, default=True, index=True)  # Para ocultar productos sin eliminarlos
    lock = Column(Boolean, nullable=False, default=False, server_default="false", index=True)  # Bloqueo operativo de producto
    category_id = Column(Integer, ForeignKey("categories.category_id"), index=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")  # Items en pedidos
    cart_entries = relationship("CartCache", back_populates="product")  # Items en carritos
    price_list_items = relationship("PriceListItem", back_populates="product", cascade="all, delete-orphan", passive_deletes=True)  # Markup por lista
    suggested_products = relationship("ProductRecommendation", foreign_keys="[ProductRecommendation.product_id]", back_populates="product", cascade="all, delete-orphan")
    favorite_list_items = relationship("FavoriteListItem", back_populates="product", cascade="all, delete-orphan")
    discounts = relationship("ProductDiscount", back_populates="product", cascade="all, delete-orphan")


class PriceList(Base):
    """
    Lista de precios (contenedor)
    
    Cada lista agrupa multiples productos con sus respectivos markups.
    Los clientes se asignan a una lista de precios que determina
    su porcentaje de ganancia sobre el precio base.
    """
    __tablename__ = "pricelists"

    price_list_id = Column(Integer, primary_key=True)
    list_name = Column(String(100), nullable=False)  # Ej: "Farmacias Premium", "Hospitales"
    description = Column(Text)  # Descripcion de a quien aplica
    is_active = Column(Boolean, default=True)
    is_public_internal = Column(Boolean, nullable=False, default=False, server_default="false", index=True)  # Visible para agentes/internos con permiso
    is_public_storefront = Column(Boolean, nullable=False, default=False, server_default="false", index=True)  # Visible para storefront público general
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    # Clientes asignados a esta lista
    customers = relationship("CustomerInfo", back_populates="price_list")
    # Items (productos) con su markup especifico en esta lista
    price_list_items = relationship("PriceListItem", back_populates="price_list", cascade="all, delete-orphan")
    discounts = relationship("ProductDiscount", back_populates="price_list", cascade="all, delete-orphan")


class PriceListItem(Base):
    """
    Markup especifico de un producto en una lista de precios
    
    Define el porcentaje de ganancia que se aplica al precio base
    de un producto especifico para una lista especifica.
    """
    __tablename__ = "pricelistitems"

    price_list_id = Column(Integer, ForeignKey("pricelists.price_list_id", ondelete="CASCADE"), primary_key=True, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True, index=True)
    markup_percentage = Column(Numeric(5, 2), nullable=False)  # % de ganancia (ej: 25.00)
    final_price = Column(Numeric(10, 2), nullable=False)  # Precio final calculado 
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    price_list = relationship("PriceList", back_populates="price_list_items")
    product = relationship("Product", back_populates="price_list_items")


class CustomerInfo(Base):
    """
    Informacion adicional de clientes (1:1 con Customer)
    
    Almacena datos comerciales del cliente:
    - Informacion fiscal (RFC, razon social)
    - Grupo de ventas al que pertenece
    - Lista de precios asignada
    - Hasta 3 direcciones de envio
    """
    __tablename__ = "customerinfo"

    customer_info_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), unique=True, nullable=False)
    business_name = Column(String(255), nullable=False)  # Razon social de la empresa
    rfc = Column(String(13))  # RFC mexicano (12-13 caracteres)
    sales_group_id = Column(Integer, ForeignKey("salesgroups.sales_group_id"), index=True)  # Grupo asignado
    price_list_id = Column(Integer, ForeignKey("pricelists.price_list_id"), index=True)  # Lista de precios
    # Tres direcciones posibles (el cliente elige cual usar al hacer pedido)
    address_1 = Column(Text)  # Direccion principal
    address_2 = Column(Text)  # Direccion secundaria (opcional)
    address_3 = Column(Text)  # Direccion terciaria (opcional)
    telefono_1 = Column(String(15))  # Telefono principal
    telefono_2 = Column(String(15))  # Telefono secundario (opcional)

    # Relaciones
    customer = relationship("Customer", back_populates="customer_info")  # Usuario cliente
    sales_group = relationship("SalesGroup", back_populates="customers")  # Grupo de ventas
    price_list = relationship("PriceList", back_populates="customers")  # Lista de precios


class Order(Base):
    """
    Pedidos de clientes y ciclo de vida de compras.
    
    Flujo típico:
    1. Cliente crea pedido (status: pending_validation)
    2. Colaborador autorizado asigna agente comercial (status: assigned / registro assigned_user_id)
    3. Colaborador autorizado aprueba pedido (status: approved)
    4. Logística de almacén surte y despacha (status: shipped)
    5. Se entrega al cliente (status: delivered)
    """
    __tablename__ = "orders"

    order_id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.user_id"), index=True)  # Usuario/Colaborador comercial asignado
    assigned_by_user_id = Column(Integer, ForeignKey("users.user_id"))  # Quien hizo la asignacion
    status = Column(SQLAlchemyEnum(OrderStatus), nullable=False, default=OrderStatus.pending_validation, index=True)
    total_amount = Column(Numeric(12, 2), default=0.00)  # Monto total calculado
    order_profit = Column(Numeric(12, 2), default=0.00)  # Ganancia por markup: sum((price_without_iva - base_price) * qty)
    shipping_cost = Column(Numeric(10, 2), default=0.00)  # Costo de envío
    shipping_address_number = Column(Integer)  # 1, 2 o 3 (cual de las 3 direcciones usar)
    shipping_address_snapshot = Column(Text, nullable=True)  # Direccion completa al momento del pedido
    assignment_notes = Column(Text)  # Notas al asignar colaborador responsable
    order_notes = Column(Text)  # Notas del cliente al hacer el pedido
    invoice_type = Column(String(50), nullable=False, default="factura")  # factura, remision, etc.
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    assigned_at = Column(TIMESTAMP(timezone=True))  # Cuando se asigno el colaborador
    validated_at = Column(TIMESTAMP(timezone=True))  # Cuando se aprobo el pedido

    # Constraint: numero de direccion debe ser 1, 2 o 3
    __table_args__ = (
        CheckConstraint('shipping_address_number BETWEEN 1 AND 3', name='check_address_number'),
    )

    # Control de bodega / almacen
    sent_to_warehouse = Column(Boolean, nullable=False, default=False, index=True)
    warehouse_status = Column(String(50), nullable=True, index=True)  # pending, in_progress_partial, in_progress_full, ready_for_check, checking, completed, splits_completed
    audit_verdict = Column(String(50), nullable=False, default="clean")  # clean, incomplete, inconsistent, incomplete_and_inconsistent
    total_splits = Column(Integer, nullable=False, default=1)
    warehouse_sent_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    warehouse_sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    warehouse_show_details = Column(Boolean, nullable=False, default=False)

    # Control de sincronización con ERP (cotiza3)
    is_synced = Column(Boolean, nullable=False, default=False, server_default='false', index=True)

    # Relaciones
    customer = relationship("Customer", back_populates="orders")  # Cliente que hizo el pedido
    assigned_user = relationship("User", back_populates="orders_assigned", foreign_keys=[assigned_user_id])  # Usuario asignado
    assigned_by = relationship("User", back_populates="orders_assigned_by", foreign_keys=[assigned_by_user_id])  # Quien asigno
    warehouse_sender = relationship("User", foreign_keys=[warehouse_sent_by])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")  # Productos del pedido
    splits = relationship("WarehouseSplit", back_populates="order", cascade="all, delete-orphan", order_by="WarehouseSplit.split_number")

    @property
    def assigned_user_name(self) -> Optional[str]:
        if not self.assigned_user:
            return None
        return self.assigned_user.full_name or self.assigned_user.username

    @property
    def customer_name(self) -> str:
        if not self.customer:
            return "Sin cliente"
        return self.customer.full_name or self.customer.username or f"Cliente #{self.customer_id}"


    @property
    def warehouse_sent_by_name(self) -> Optional[str]:
        if not self.warehouse_sender:
            return None
        return self.warehouse_sender.full_name or self.warehouse_sender.username

    @property
    def completed_splits_count(self) -> int:
        if not self.splits:
            return 0
        return sum(1 for b in self.splits if b.status == "completed")

    @property
    def sent_to_warehouse_at(self) -> Optional[datetime]:
        return self.warehouse_sent_at




class WarehouseContainer(Base):
    """
    Canastas físicas reutilizables con código QR (Totes de Almacén).
    """
    __tablename__ = "warehouse_containers"

    container_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.uuid_generate_v4())
    qr_code = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="available", index=True)  # available, in_use, damaged, maintenance
    current_split_id = Column(PG_UUID(as_uuid=True), ForeignKey("warehouse_splits.split_id", ondelete="SET NULL"), nullable=True, index=True)
    current_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    current_split = relationship("WarehouseSplit", back_populates="containers", foreign_keys=[current_split_id])
    current_user = relationship("User", foreign_keys=[current_user_id])
    items = relationship("WarehouseItem", back_populates="container")
    container_items = relationship("WarehouseContainerItem", back_populates="container", cascade="all, delete-orphan")

    @property
    def is_available(self) -> bool:
        return self.status == "available"


class WarehouseSplit(Base):
    """
    Lotes de surtido lógico/físico de un Pedido en Almacén (Splits).
    """
    __tablename__ = "warehouse_splits"

    split_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.uuid_generate_v4())
    order_id = Column(BigInteger, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True)
    split_number = Column(Integer, nullable=False)
    total_splits = Column(Integer, nullable=False, default=1)
    split_code = Column(String(50), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="pending", index=True)  # pending, picking, ready_for_check, checking, completed, cancelled
    picker_id = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    checker_id = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    security_seal_folio = Column(String(50), nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    picking_completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    checking_started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    admin_override_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    admin_override_at = Column(TIMESTAMP(timezone=True), nullable=True)
    active_container_id = Column(PG_UUID(as_uuid=True), ForeignKey("warehouse_containers.container_id", ondelete="SET NULL"), nullable=True, index=True)
    uses_containers = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint('order_id', 'split_number', name='uq_order_split'),
    )

    # Relaciones
    order = relationship("Order", back_populates="splits")
    picker = relationship("User", foreign_keys=[picker_id])
    checker = relationship("User", foreign_keys=[checker_id])
    admin_editor = relationship("User", foreign_keys=[admin_override_by])
    warehouse_items = relationship("WarehouseItem", back_populates="split", cascade="all, delete-orphan")
    containers = relationship("WarehouseContainer", back_populates="current_split", foreign_keys="WarehouseContainer.current_split_id")
    active_container = relationship("WarehouseContainer", foreign_keys=[active_container_id])
    container_items = relationship("WarehouseContainerItem", back_populates="split", cascade="all, delete-orphan")

    @property
    def items(self):
        return [wi.order_item for wi in self.warehouse_items if wi.order_item]

    @property
    def items_count(self) -> int:
        return len(self.warehouse_items)

    @property
    def active_container_qr(self) -> Optional[str]:
        if self.active_container:
            return self.active_container.qr_code
        if self.containers:
            return self.containers[-1].qr_code
        return None

    @property
    def container_qr(self) -> Optional[str]:
        return self.active_container_qr

    @property
    def duration_seconds(self) -> Optional[int]:
        start = self.started_at
        end = self.picking_completed_at or self.completed_at
        if not start or not end:
            return None
        return int((end - start).total_seconds())

    @property
    def duration_formatted(self) -> Optional[str]:
        sec = self.duration_seconds
        if sec is None:
            return None
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"

    @property
    def checking_duration_seconds(self) -> Optional[int]:
        if not self.checking_started_at or not self.completed_at:
            return None
        return int((self.completed_at - self.checking_started_at).total_seconds())

    @property
    def checking_duration_formatted(self) -> Optional[str]:
        sec = self.checking_duration_seconds
        if sec is None:
            return None
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"

    @property
    def picker_name(self) -> Optional[str]:
        if not self.picker:
            return None
        return self.picker.full_name or self.picker.username

    @property
    def checker_name(self) -> Optional[str]:
        if not self.checker:
            return None
        return self.checker.full_name or self.checker.username

    @property
    def admin_override_by_name(self) -> Optional[str]:
        if not self.admin_editor:
            return None
        return self.admin_editor.full_name or self.admin_editor.username

    @property
    def customer_name(self) -> Optional[str]:
        if not self.order:
            return None
        return self.order.customer_name

    @property
    def assigned_user_name(self) -> Optional[str]:
        if not self.order:
            return None
        return self.order.assigned_user_name

    @property
    def active_container_qr(self) -> Optional[str]:
        if self.active_container:
            return self.active_container.qr_code
        if self.containers:
            return self.containers[-1].qr_code
        return None

    @property
    def container_qr(self) -> Optional[str]:
        return self.active_container_qr

    @property
    def container_id(self) -> Optional[UUID]:
        if self.active_container_id:
            return self.active_container_id
        if self.containers:
            return self.containers[-1].container_id
        return None


class OrderItem(Base):
    """
    Items individuales dentro de un pedido
    
    Cada item representa un producto con su cantidad y precios.
    Los precios se 'congelan' al momento de crear el pedido para
    mantener historial preciso aunque los precios cambien despues.
    """
    __tablename__ = "orderitems"

    order_item_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.uuid_generate_v4())
    order_id = Column(BigInteger, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)  # Cantidad del producto
    base_price = Column(Numeric(10, 2), nullable=False)  # Precio base snapshot
    markup_percentage = Column(Numeric(5, 2), nullable=False)  # % markup snapshot
    iva_percentage = Column(Numeric(5, 2), nullable=False)  # % IVA snapshot
    price_without_iva = Column(Numeric(10, 2), nullable=False)  # Precio con markup SIN IVA (para TXT/ERP)
    final_price = Column(Numeric(10, 2), nullable=False)  # Precio final CON IVA
    discount_applied = Column(Numeric(5, 2), nullable=False, default=0.00)  # % descuento snapshot congelado
    discount_type = Column(String(20), nullable=False, default="none")       # 'price_list', 'general' o 'none'

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
    )

    # Relaciones
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    warehouse_items = relationship("WarehouseItem", back_populates="order_item", cascade="all, delete-orphan")

    # Propiedades de conveniencia directa del producto
    @property
    def product_name(self) -> str:
        return self.product.name if self.product else f"Producto {self.product_id}"

    @property
    def codebar(self) -> Optional[str]:
        return self.product.codebar if self.product else None

    @property
    def barcode(self) -> Optional[str]:
        return self.product.codebar if self.product else None

    @property
    def location(self) -> str:
        return (self.product.location or "") if self.product else ""

    @property
    def image_url(self) -> Optional[str]:
        return self.product.image_url if self.product else None


class WarehouseItem(Base):
    """
    Partidas granulares de almacén vinculadas a un split y opcionalmente a una canasta QR.
    Reemplaza a OrderItemSplitFulfillment permitiendo fraccionar partidas de pedidos entre splits/canastas.
    """
    __tablename__ = "warehouse_items"

    warehouse_item_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.uuid_generate_v4())
    split_id = Column(PG_UUID(as_uuid=True), ForeignKey("warehouse_splits.split_id", ondelete="CASCADE"), nullable=False, index=True)
    order_item_id = Column(PG_UUID(as_uuid=True), ForeignKey("orderitems.order_item_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False, index=True)
    container_id = Column(PG_UUID(as_uuid=True), ForeignKey("warehouse_containers.container_id", ondelete="SET NULL"), nullable=True, index=True)

    required_quantity = Column(Integer, nullable=False)

    # 1er Filtro: Surtido en Piso (Picker)
    picked_scanned_qty = Column(Integer, nullable=False, default=0)
    picked_boxes = Column(Integer, nullable=False, default=0)
    picked_box_prods = Column(Integer, nullable=False, default=0)
    picked_manual_qty = Column(Integer, nullable=False, default=0)
    picked_manual_reason = Column(String(255), nullable=True)
    picked_total_qty = column_property(picked_scanned_qty + picked_box_prods + picked_manual_qty)
    picked_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    picked_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # 2do Filtro: Mesa de Control y Revisión (Checker)
    checked_scanned_qty = Column(Integer, nullable=False, default=0)
    checked_boxes = Column(Integer, nullable=False, default=0)
    checked_box_prods = Column(Integer, nullable=False, default=0)
    checked_manual_qty = Column(Integer, nullable=False, default=0)
    checked_manual_reason = Column(String(255), nullable=True)
    checked_total_qty = column_property(checked_scanned_qty + checked_box_prods + checked_manual_qty)
    checked_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    checked_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Estatus y Auditoría
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, partial, completed, discrepancy
    admin_override_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    admin_override_at = Column(TIMESTAMP(timezone=True), nullable=True)
    admin_override_note = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    split = relationship("WarehouseSplit", back_populates="warehouse_items")
    order_item = relationship("OrderItem", back_populates="warehouse_items")
    product = relationship("Product")
    container = relationship("WarehouseContainer", back_populates="items")
    picker = relationship("User", foreign_keys=[picked_by])
    checker = relationship("User", foreign_keys=[checked_by])
    admin_editor = relationship("User", foreign_keys=[admin_override_by])
    container_items = relationship("WarehouseContainerItem", back_populates="warehouse_item", cascade="all, delete-orphan")

    @property
    def picker_name(self) -> Optional[str]:
        if not self.picker:
            return None
        return self.picker.full_name or self.picker.username

    @property
    def checker_name(self) -> Optional[str]:
        if not self.checker:
            return None
        return self.checker.full_name or self.checker.username

    @property
    def admin_override_by_name(self) -> Optional[str]:
        if not self.admin_editor:
            return None
        return self.admin_editor.full_name or self.admin_editor.username

    @property
    def container_qr(self) -> Optional[str]:
        return self.container.qr_code if self.container else None

    @container_qr.setter
    def container_qr(self, value: Optional[str]) -> None:
        """Setter defensivo: el contenedor físico se resuelve mediante container_id."""
        pass


class WarehouseContainerItem(Base):
    """
    Distribución consolidada de productos por canasta física QR dentro de un split.
    Permite conocer exactamente qué productos, cajas y cantidades están depositadas en cada canasta.
    """
    __tablename__ = "warehouse_container_items"

    container_item_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.uuid_generate_v4())
    split_id = Column(PG_UUID(as_uuid=True), ForeignKey("warehouse_splits.split_id", ondelete="CASCADE"), nullable=False, index=True)
    container_id = Column(PG_UUID(as_uuid=True), ForeignKey("warehouse_containers.container_id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_item_id = Column(PG_UUID(as_uuid=True), ForeignKey("warehouse_items.warehouse_item_id", ondelete="CASCADE"), nullable=True, index=True)
    order_item_id = Column(PG_UUID(as_uuid=True), ForeignKey("orderitems.order_item_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False, index=True)

    # 1er Filtro: Surtido en Piso (Picker) en esta canasta
    picked_scanned_qty = Column(Integer, nullable=False, default=0)
    picked_boxes = Column(Integer, nullable=False, default=0)
    picked_box_prods = Column(Integer, nullable=False, default=0)
    picked_manual_qty = Column(Integer, nullable=False, default=0)
    picked_total_qty = column_property(picked_scanned_qty + picked_box_prods + picked_manual_qty)

    # 2do Filtro: Mesa de Control y Revisión (Checker) en esta canasta
    checked_scanned_qty = Column(Integer, nullable=False, default=0)
    checked_boxes = Column(Integer, nullable=False, default=0)
    checked_box_prods = Column(Integer, nullable=False, default=0)
    checked_manual_qty = Column(Integer, nullable=False, default=0)
    checked_total_qty = column_property(checked_scanned_qty + checked_box_prods + checked_manual_qty)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('split_id', 'container_id', 'product_id', name='uq_split_container_product'),
    )

    # Relaciones
    split = relationship("WarehouseSplit", back_populates="container_items")
    container = relationship("WarehouseContainer", back_populates="container_items")
    warehouse_item = relationship("WarehouseItem", back_populates="container_items")
    order_item = relationship("OrderItem")
    product = relationship("Product")

    @property
    def container_qr(self) -> Optional[str]:
        return self.container.qr_code if self.container else None

    @property
    def product_name(self) -> str:
        return self.product.name if self.product else f"Producto {self.product_id}"


class CartCache(Base):
    """
    Carrito de compras temporal de clientes
    
    Almacena los productos que el cliente ha agregado al carrito
    pero aun no ha convertido en pedido. Se limpia al crear el pedido.
    """
    __tablename__ = "cartcache"

    cart_cache_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)  # Cantidad a ordenar
    added_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))  # Primera vez agregado
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))  # ultima modificacion

    __table_args__ = (
        # Un producto solo puede aparecer una vez en el carrito de un cliente
        UniqueConstraint('customer_id', 'product_id'),
        # La cantidad debe ser positiva
        CheckConstraint('quantity > 0', name='check_cart_quantity_positive'),
    )

    # Relaciones
    customer = relationship("Customer", back_populates="cart_cache")  # Cliente dueño del carrito
    product = relationship("Product", back_populates="cart_entries")  # Producto en el carrito


class ProductRecommendation(Base):
    __tablename__ = "product_recommendations"

    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    recommended_product_id = Column(String(50), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    recommendation_type = Column(String(50), default='intersection/union')
    score = Column(Numeric(3, 2), default=1.0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint('product_id <> recommended_product_id', name='check_not_self_recommended'),
    )

    # Relaciones para navegar fácilmente
    product = relationship("Product", foreign_keys=[product_id], back_populates="suggested_products")
    recommended_product = relationship("Product", foreign_keys=[recommended_product_id], backref="recommendations_in")


class Ticket(Base):
    """
    Tickets de Soporte generados por Clientes o Colaboradores.
    Los tickets son atendidos por colaboradores autorizados o administradores.
    """
    __tablename__ = "tickets"

    ticket_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLAlchemyEnum(TicketStatus), nullable=False, default=TicketStatus.open, index=True)
    priority = Column(SQLAlchemyEnum(TicketPriority), nullable=False, default=TicketPriority.medium)
    creator_id = Column(Integer, nullable=False, index=True)
    creator_type = Column(SQLAlchemyEnum(CreatorType), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)  # Colaborador asignado
    order_id = Column(BigInteger, ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True, index=True)  # Pedido asociado opcional
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    assignee = relationship("User", foreign_keys=[assigned_to])
    order = relationship("Order", foreign_keys=[order_id])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at")


class TicketMessage(Base):
    """
    Mensajes dentro de un hilo de Ticket de Soporte.
    Pueden ser enviados por el Creador (Customer/Colaborador) o por el Agente de Soporte asignado.
    """
    __tablename__ = "ticket_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, nullable=False)
    sender_type = Column(SQLAlchemyEnum(SenderType), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)

    ticket = relationship("Ticket", back_populates="messages")


class FavoriteList(Base):
    """
    Listas de compras preestablecidas (Favoritos) de los clientes
    """
    __tablename__ = "favoritelists"

    list_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.uuid_generate_v4())
    customer_id = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Constraints
    __table_args__ = (
        UniqueConstraint('customer_id', 'name', name='unique_list_name_per_customer'),
    )

    # Relaciones
    customer = relationship("Customer", back_populates="favorite_lists")
    items = relationship("FavoriteListItem", back_populates="favorite_list", cascade="all, delete-orphan")


class FavoriteListItem(Base):
    """
    Items individuales dentro de una lista de favoritos
    """
    __tablename__ = "favoritelistitems"

    list_item_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.uuid_generate_v4())
    list_id = Column(PG_UUID(as_uuid=True), ForeignKey("favoritelists.list_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    added_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Constraints
    __table_args__ = (
        UniqueConstraint('list_id', 'product_id', name='unique_product_per_list'),
        CheckConstraint('quantity > 0', name='check_fav_quantity_positive'),
    )

    # Relaciones
    favorite_list = relationship("FavoriteList", back_populates="items")
    product = relationship("Product", back_populates="favorite_list_items")

    @property
    def product_name(self):
        return self.product.name if self.product else None

    @property
    def product_image_url(self):
        return self.product.image_url if self.product else None

    @property
    def product_codebar(self):
        return self.product.codebar if self.product else None


    @property
    def product_stock(self):
        return self.product.stock_count if self.product else 0

    @property
    def is_active(self):
        return self.product.is_active if self.product else False

class ContactMessageModel(Base):
    """
    Mensajes de Contacto recibidos desde la pagina web.
    """
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(150), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(30), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    message = Column(String(500), nullable=False)
    status = Column(String(20), default='pending')  # 'pending', 'contacted'
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'contacted')", name='check_contact_status'),
    )

class ClientRequestModel(Base):
    """
    Solicitudes para ser Cliente con documentos PDF en S3.
    """
    __tablename__ = "client_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(150), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(30), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    message = Column(String(500), nullable=False)
    status = Column(String(20), default='pending')  # 'pending', 'approved', 'rejected'
    
    # S3 Keys
    id_pdf_key = Column(String(500), nullable=False)
    sanitary_license_pdf_key = Column(String(500), nullable=False)
    proof_of_address_pdf_key = Column(String(500), nullable=False)
    tax_cert_pdf_key = Column(String(500), nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='check_client_request_status'),
    )

class OrderStat(Base):
    """
    Conteos desnormalizados de pedidos por (grupo, status).
    Mantenida desde Python (crud_order_stats).
    sales_group_id = 0 → conteo global (administración / permisos globales)
    sales_group_id > 0 → conteo por grupo de ventas asignado
    """
    __tablename__ = "order_stats"

    sales_group_id = Column(Integer, primary_key=True)
    status = Column(String(50), primary_key=True)
    count = Column(Integer, nullable=False, default=0)


class AnnouncementModel(Base):
    """
    Anuncios y Promos (para el Admin Panel)
    """
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    img = Column(String(255), nullable=True)
    img_version = Column(Integer, default=1)
    type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default='activo', index=True)
    start_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_send = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("type IN ('story', 'popup', 'footer')", name='check_announcement_type'),
        CheckConstraint("status IN ('activo', 'inactivo')", name='check_announcement_status'),
    )



class ProductDiscount(Base):
    """
    Descuentos temporales por producto (Generales o por Lista de Precios)
    
    - Si price_list_id es NULL: Descuento General (reduce base_price de todos)
    - Si price_list_id tiene valor: Descuento exclusivo para esa lista de precios (reduce precio con markup)
    """
    __tablename__ = "product_discounts"

    discount_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.gen_random_uuid())
    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    price_list_id = Column(Integer, ForeignKey("pricelists.price_list_id", ondelete="CASCADE"), nullable=True, index=True)
    discount_percentage = Column(Numeric(5, 2), nullable=False)
    start_date = Column(TIMESTAMP(timezone=True), nullable=False)
    end_date = Column(TIMESTAMP(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint('discount_percentage > 0 AND discount_percentage <= 100', name='check_discount_percentage_range'),
        CheckConstraint('start_date < end_date', name='check_discount_dates'),
    )

    # Relaciones
    product = relationship("Product", back_populates="discounts")
    price_list = relationship("PriceList", back_populates="discounts")
    creator = relationship("User", foreign_keys=[created_by_user_id])

    @property
    def product_name(self) -> str:
        return self.product.name if self.product else None

    @property
    def price_list_name(self) -> str:
        return self.price_list.list_name if self.price_list else None

    @property
    def created_by_name(self) -> str:
        if not self.creator:
            return None
        return self.creator.full_name or self.creator.username

    @property
    def discount_scope(self) -> str:
        return "price_list" if self.price_list_id is not None else "general"

    @property
    def is_current(self) -> bool:
        if not self.is_active:
            return False
        now = datetime.now(timezone.utc)
        start = self.start_date
        end = self.end_date
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return bool(start and end and start <= now <= end)

    @property
    def base_price(self):
        return Decimal(str(self.product.base_price)) if self.product and self.product.base_price is not None else None

    @property
    def iva_percentage(self):
        return Decimal(str(self.product.iva_percentage)) if self.product and self.product.iva_percentage is not None else Decimal("0.00")

    @property
    def markup_percentage(self):
        if self.price_list_id and self.product:
            for item in getattr(self.product, "price_list_items", []):
                if item.price_list_id == self.price_list_id:
                    return Decimal(str(item.markup_percentage))
        return Decimal("0.00")

    @property
    def original_price(self):
        if not self.product:
            return None
        base = Decimal(str(self.product.base_price or 0))
        if self.price_list_id:
            markup = self.markup_percentage or Decimal("0.00")
            return round(base * (Decimal("1") + markup / Decimal("100")), 2)
        return round(base, 2)

    @property
    def discount_amount(self):
        orig = self.original_price
        if orig is None:
            return None
        pct = Decimal(str(self.discount_percentage or 0))
        return round(orig * (pct / Decimal("100")), 2)

    @property
    def discounted_price(self):
        orig = self.original_price
        disc = self.discount_amount
        if orig is None or disc is None:
            return None
        return round(orig - disc, 2)

    @property
    def final_price_with_iva(self):
        disc_price = self.discounted_price
        if disc_price is None or not self.product:
            return None
        iva = self.iva_percentage or Decimal("0.00")
        return round(disc_price * (Decimal("1") + iva / Decimal("100")), 2)



class ProductYearlyStat(Base):
    """
    Estadísticas anuales acumuladas por producto (O(1) para el dashboard).
    Mantiene pedidos únicos, unidades vendidas, ingresos y ganancias por año.
    """
    __tablename__ = "product_yearly_stats"

    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True)
    year = Column(Integer, primary_key=True)
    orders_count = Column(Integer, nullable=False, default=0)
    units_sold = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_profit = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", backref="yearly_stats")


class SystemConfig(Base):
    """
    Configuraciones globales persistentes del sistema (flags operacionales).
    No se eliminan, controlan flujos dinámicos como apartados de inventario.
    """
    __tablename__ = "system_configs"

    config_id = Column(Integer, primary_key=True)
    config_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class OrderStockHold(Base):
    """
    Apartados temporales de stock asociados a un pedido.
    Se mantienen mientras el pedido está pendiente de validación o proceso en almacén/ERP,
    y se eliminan en cuanto el pedido pasa a aprobado (ya descontado en ERP) o cancelado.
    """
    __tablename__ = "order_stock_holds"

    order_id = Column(Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(String(50), ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True, index=True)
    quantity = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    order = relationship("Order", backref="stock_holds")
    product = relationship("Product", backref="stock_holds")


class PromoAdSection(Base):
    """
    Bloques o secciones de publicidad en la página de inicio del cliente.
    Cada sección define el número de columnas (layout_type: 1, 2, 3 o 4) y su orden vertical.
    """
    __tablename__ = "promo_ad_sections"

    section_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.gen_random_uuid())
    title = Column(String(150), nullable=True)
    layout_type = Column(Integer, nullable=False)
    display_order = Column(Integer, nullable=False, default=0, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    start_date = Column(TIMESTAMP(timezone=True), nullable=True)
    end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = relationship(
        "PromoAdItem",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="PromoAdItem.slot, PromoAdItem.display_order",
    )

    __table_args__ = (
        CheckConstraint("layout_type IN (1, 2, 3, 4)", name="check_promo_ad_layout_type"),
    )


class PromoAdItem(Base):
    """
    Anuncios individuales dentro de una columna (slot) de una sección de publicidad.
    Soporta múltiples anuncios por slot (carrusel) e imágenes adaptables (desktop, tablet, móvil).
    """
    __tablename__ = "promo_ad_items"

    item_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7, server_default=func.gen_random_uuid())
    section_id = Column(PG_UUID(as_uuid=True), ForeignKey("promo_ad_sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    slot = Column(Integer, nullable=False, default=1)
    display_order = Column(Integer, nullable=False, default=0)
    title = Column(String(150), nullable=True)
    link_url = Column(String(500), nullable=True)
    img_desktop = Column(String(255), nullable=False)
    img_tablet = Column(String(255), nullable=True)
    img_mobile = Column(String(255), nullable=True)
    img_version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    start_date = Column(TIMESTAMP(timezone=True), nullable=True)
    end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    section = relationship("PromoAdSection", back_populates="items")

    __table_args__ = (
        CheckConstraint("slot BETWEEN 1 AND 4", name="check_promo_ad_item_slot"),
    )


