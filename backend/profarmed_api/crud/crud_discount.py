"""
CRUD y Gestión de Descuentos y Promociones (ProductDiscount):

Funciones y Operaciones:
- Consultar descuentos activos para un producto evaluando jerarquía de prioridad.
- Consultar listado completo de promociones con paginación, filtros de estado y vigencias.
- Crear, actualizar y eliminar promociones con control de fechas inicio/fin y asignación por lista de precios.
- Activar o pausar promociones (`is_active`).

Reglas de Negocio y Jerarquía de Prioridad:
1. Regla de Resolución de Descuentos:
   - 1º Prioridad: Descuento específico vinculado a la `price_list_id` del cliente.
   - 2º Prioridad: Descuento global (`price_list_id is NULL`) aplicable a todas las listas de precios.
2. Control de Vigencia Temporal:
   - Un descuento solo es aplicable si `is_active == True` y `start_date <= current_time <= end_date`.
3. Aplicación en Cascada:
   - Los descuentos se deducen del precio final con IVA en el catálogo, carrito y generación del pedido.
4. Permisos y Control de Acceso (PBAC / RBAC Dinámico):
   - Lectura de promociones calculadas permitida en storefront y catálogo para clientes y visitantes (`catalog.view`).
   - Gestión integral de promociones (crear, editar, activar/pausar, eliminar) reservada para roles con permisos específicos (`discounts.manage`, `catalog.prices`) o rol superusuario `admin`.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, or_

from db.base import ProductDiscount, Product, PriceList
from schemas.discount import ProductDiscountCreate, ProductDiscountUpdate, ActiveDiscountInfo


""" Obtiene el descuento activo aplicable a un producto con regla de prioridad """
def get_active_discount_for_product(
    db: Session,
    product_id: str,
    price_list_id: Optional[int] = None,
    current_time: Optional[datetime] = None
) -> ActiveDiscountInfo:
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # 1. Prioridad: Descuento especifico para la lista de precios
    if price_list_id is not None:
        plist_discount = db.query(ProductDiscount).filter(
            ProductDiscount.product_id == product_id,
            ProductDiscount.price_list_id == price_list_id,
            ProductDiscount.is_active == True,
            ProductDiscount.start_date <= current_time,
            ProductDiscount.end_date >= current_time
        ).order_by(ProductDiscount.discount_id.desc()).first()

        if plist_discount:
            return ActiveDiscountInfo(
                has_discount=True,
                discount_type="price_list",
                discount_percentage=plist_discount.discount_percentage,
                discount_id=plist_discount.discount_id,
                description=plist_discount.description
            )

    # 2. Prioridad: Descuento general (aplica sobre precio base)
    general_discount = db.query(ProductDiscount).filter(
        ProductDiscount.product_id == product_id,
        ProductDiscount.price_list_id.is_(None),
        ProductDiscount.is_active == True,
        ProductDiscount.start_date <= current_time,
        ProductDiscount.end_date >= current_time
    ).order_by(ProductDiscount.discount_id.desc()).first()

    if general_discount:
        return ActiveDiscountInfo(
            has_discount=True,
            discount_type="general",
            discount_percentage=general_discount.discount_percentage,
            discount_id=general_discount.discount_id,
            description=general_discount.description
        )

    # 3. Sin descuento activo
    return ActiveDiscountInfo(
        has_discount=False,
        discount_type="none",
        discount_percentage=Decimal("0.00"),
        discount_id=None,
        description=None
    )


""" Obtiene en una sola consulta O(1) los descuentos activos aplicables para múltiples productos """
def get_active_discounts_for_products(
    db: Session,
    product_ids: Optional[List[str]] = None,
    price_list_id: Optional[int] = None,
    current_time: Optional[datetime] = None
) -> Dict[str, ActiveDiscountInfo]:
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    if product_ids is not None and len(product_ids) == 0:
        return {}

    query = db.query(ProductDiscount).filter(
        ProductDiscount.is_active == True,
        ProductDiscount.start_date <= current_time,
        ProductDiscount.end_date >= current_time
    )

    if product_ids is not None:
        query = query.filter(ProductDiscount.product_id.in_(product_ids))

    if price_list_id is not None:
        query = query.filter(
            or_(
                ProductDiscount.price_list_id == price_list_id,
                ProductDiscount.price_list_id.is_(None)
            )
        )
    else:
        query = query.filter(ProductDiscount.price_list_id.is_(None))

    # El orden descendente por discount_id asegura que el más nuevo gane
    discounts = query.order_by(ProductDiscount.discount_id.desc()).all()

    # Mapear respetando jerarquía: price_list tiene prioridad 1, general tiene prioridad 2
    result: Dict[str, ActiveDiscountInfo] = {}
    general_discounts: Dict[str, ActiveDiscountInfo] = {}

    for d in discounts:
        pid = d.product_id
        if d.price_list_id == price_list_id:
            if pid not in result:
                result[pid] = ActiveDiscountInfo(
                    has_discount=True,
                    discount_type="price_list",
                    discount_percentage=d.discount_percentage,
                    discount_id=d.discount_id,
                    description=d.description
                )
        elif d.price_list_id is None:
            if pid not in general_discounts:
                general_discounts[pid] = ActiveDiscountInfo(
                    has_discount=True,
                    discount_type="general",
                    discount_percentage=d.discount_percentage,
                    discount_id=d.discount_id,
                    description=d.description
                )

    # Si no tiene descuento específico por lista, hereda el descuento general
    for pid, g_info in general_discounts.items():
        if pid not in result:
            result[pid] = g_info

    return result


""" Obtiene un descuento por ID con relaciones cargadas """
def get_discount(db: Session, discount_id: UUID) -> Optional[ProductDiscount]:
    return db.query(ProductDiscount).options(
        joinedload(ProductDiscount.product).joinedload(Product.price_list_items),
        joinedload(ProductDiscount.price_list),
        joinedload(ProductDiscount.creator)
    ).filter(ProductDiscount.discount_id == discount_id).first()


""" Obtiene lista de descuentos con filtros opcionales y busqueda """
def get_discounts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[str] = None,
    search: Optional[str] = None,
    price_list_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    only_current: bool = False
) -> List[ProductDiscount]:
    query = db.query(ProductDiscount).join(ProductDiscount.product).outerjoin(ProductDiscount.price_list).options(
        joinedload(ProductDiscount.product).joinedload(Product.price_list_items),
        joinedload(ProductDiscount.price_list),
        joinedload(ProductDiscount.creator)
    )

    if search:
        search_terms = search.strip().split()
        if search_terms:
            word_filters = []
            for term in search_terms:
                pattern = f"%{term}%"
                word_filters.append(
                    (ProductDiscount.product_id.ilike(pattern)) |
                    (Product.name.ilike(pattern)) |
                    (Product.description.ilike(pattern)) |
                    (Product.descripcion_2.ilike(pattern)) |
                    (Product.codebar.ilike(pattern)) |
                    (ProductDiscount.description.ilike(pattern)) |
                    (PriceList.list_name.ilike(pattern))
                )
            query = query.filter(and_(*word_filters))

    if product_id:
        query = query.filter(ProductDiscount.product_id == product_id)

    if price_list_id is not None:
        if price_list_id == 0:
            query = query.filter(ProductDiscount.price_list_id.is_(None))
        else:
            query = query.filter(ProductDiscount.price_list_id == price_list_id)

    if is_active is not None:
        query = query.filter(ProductDiscount.is_active == is_active)

    if only_current:
        now = datetime.now(timezone.utc)
        query = query.filter(
            ProductDiscount.is_active == True,
            ProductDiscount.start_date <= now,
            ProductDiscount.end_date >= now
        )

    return query.order_by(ProductDiscount.created_at.desc(), ProductDiscount.discount_id.desc()).offset(skip).limit(limit).all()


""" Crea un nuevo registro de descuento """
def create_discount(
    db: Session,
    discount_in: ProductDiscountCreate,
    created_by_user_id: Optional[int] = None
) -> ProductDiscount:
    db_discount = ProductDiscount(
        product_id=discount_in.product_id,
        price_list_id=discount_in.price_list_id,
        discount_percentage=discount_in.discount_percentage,
        start_date=discount_in.start_date,
        end_date=discount_in.end_date,
        is_active=discount_in.is_active,
        description=discount_in.description,
        created_by_user_id=created_by_user_id
    )
    db.add(db_discount)
    db.commit()
    db.refresh(db_discount)
    return db_discount


""" Actualiza un descuento existente """
def update_discount(
    db: Session,
    discount_id_or_obj,
    discount_in: ProductDiscountUpdate
) -> Optional[ProductDiscount]:
    if isinstance(discount_id_or_obj, ProductDiscount):
        db_discount = discount_id_or_obj
    else:
        db_discount = db.query(ProductDiscount).filter(ProductDiscount.discount_id == discount_id_or_obj).first()
    if not db_discount:
        return None

    update_data = discount_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_discount, field, value)

    db_discount.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_discount)
    return db_discount


""" Elimina un descuento por ID """
def delete_discount(db: Session, discount_id: UUID) -> bool:
    db_discount = db.query(ProductDiscount).filter(ProductDiscount.discount_id == discount_id).first()
    if not db_discount:
        return False
    db.delete(db_discount)
    db.commit()
    return True


""" Obtiene metricas globales de descuentos """
def get_discount_stats(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    total = db.query(func.count(ProductDiscount.discount_id)).scalar() or 0
    active = db.query(func.count(ProductDiscount.discount_id)).filter(
        ProductDiscount.is_active == True,
        ProductDiscount.start_date <= now,
        ProductDiscount.end_date >= now
    ).scalar() or 0
    general = db.query(func.count(ProductDiscount.discount_id)).filter(
        ProductDiscount.price_list_id.is_(None)
    ).scalar() or 0
    price_list = db.query(func.count(ProductDiscount.discount_id)).filter(
        ProductDiscount.price_list_id.isnot(None)
    ).scalar() or 0
    return {
        "total": total,
        "active": active,
        "general": general,
        "price_list": price_list
    }
