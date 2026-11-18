"""
CRUD y Gestión de Listas de Precios y Márgenes por Producto (PriceList & PriceListItem):

Funciones y Operaciones:
- Crear, listar, actualizar y desactivar listas de precios maestras.
- Asignar y actualizar markups porcentuales (`markup_percentage`) y precios fijos por producto en cada lista.
- Consultar productos de una lista con cálculo dinámico de precio base, IVA, margen bruto y precio final al público.
- Asignación de listas de precios a clientes a través de `CustomerInfo.price_list_id`.

Reglas de Negocio y Estructura de Precios:
1. Arquitectura de Precios Dinámicos:
   - Las listas de precios almacenan el factor de ganancia / markup por cada producto (`PriceListItem`).
   - El precio al cliente se deriva de `Product.base_price` + `markup_percentage` + `Product.iva_percentage`.
2. Sincronización ERP:
   - Permite coexistencia de listas generales (p. ej. Lista 1 Mostrador, Lista 2 Mayoreo, Lista 3 Especial) y listas personalizadas por cliente.
3. Fallbacks de Catálogo:
   - Si un producto no tiene markup explícito en una lista dada, se toma el precio base o markup estándar configurado.
4. Control de Acceso y Reglas PBAC / RBAC Dinámico:
   - Consulta de listas y precios de catálogo: Requiere permiso `prices.view` o `catalog.view`.
   - Modificación y creación de listas y markups: Requiere permiso `prices.manage` o `catalog.prices`.
   - Visualización de márgenes y precios base confidenciales reservada a usuarios autorizados.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from decimal import Decimal

from db.base import PriceList, PriceListItem, Product
from schemas.price_list import (
    PriceListCreate, PriceListUpdate,
    PriceListItemCreate, PriceListItemUpdate
)
from utils.price_utils import (
    get_product_final_price, 
    format_price_info, 
    calculate_final_price_with_markup,
    calculate_catalog_price,
    calculate_product_price_breakdown
)

""" Obtiene una lista de precios por ID """
def get_price_list(db: Session, price_list_id: int) -> Optional[PriceList]:
    # Obtiene una lista de precios por ID
    return db.query(PriceList).filter(
        PriceList.price_list_id == price_list_id
    ).first()

""" Obtiene todas las listas de precios con filtrado opcional """
def get_price_lists(db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None, is_public_internal: Optional[bool] = None) -> List[PriceList]:
    query = db.query(PriceList)
    
    if is_active is not None:
        query = query.filter(PriceList.is_active == is_active)
    if is_public_internal is not None:
        query = query.filter(PriceList.is_public_internal == is_public_internal)
    
    return query.order_by(PriceList.price_list_id.asc()).offset(skip).limit(limit).all()

""" Crea una nueva lista de precios """
def create_price_list(db: Session, price_list: PriceListCreate) -> PriceList:
    # Crea una nueva lista de precios
    db_price_list = PriceList(
        list_name=price_list.list_name,
        description=price_list.description,
        is_active=price_list.is_active if price_list.is_active is not None else True,
        is_public_internal=bool(price_list.is_public_internal),
        is_public_storefront=bool(price_list.is_public_storefront)
    )
    
    # Si se proporciona un ID, usarlo (para sincronizacion externa)
    if price_list.price_list_id:
        db_price_list.price_list_id = price_list.price_list_id
    
    db.add(db_price_list)
    db.commit()
    db.refresh(db_price_list)
    return db_price_list

""" Actualiza una lista de precios existente """
def update_price_list(db: Session, price_list_id: int, price_list_update: PriceListUpdate) -> Optional[PriceList]:    
    db_price_list = get_price_list(db, price_list_id)
    if not db_price_list:
        return None
    
    update_data = price_list_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_price_list, field, value)
    
    db.commit()
    db.refresh(db_price_list)
    return db_price_list

""" Elimina una lista de precios (hard delete) """
def delete_price_list(db: Session, price_list_id: int) -> Optional[PriceList]:
    db_price_list = get_price_list(db, price_list_id)
    if db_price_list:
        db.delete(db_price_list)
        db.commit()
    return db_price_list

""" Obtiene todos los items de una lista de precios """
def get_price_list_items(db: Session, price_list_id: int) -> List[PriceListItem]:    
    return db.query(PriceListItem).options(
        joinedload(PriceListItem.product)
    ).filter(PriceListItem.price_list_id == price_list_id).all()

""" Obtiene un item especifico de una lista de precios """
def get_price_list_item(db: Session, price_list_id: int, product_id: str) -> Optional[PriceListItem]:
    return db.query(PriceListItem).filter(
        and_(
            PriceListItem.price_list_id == price_list_id,
            PriceListItem.product_id == product_id
        )
    ).first()

""" Crea o actualiza un item en la lista de precios """
def create_price_list_item(db: Session, price_list_id: int, item: PriceListItemCreate) -> PriceListItem:
    existing = get_price_list_item(db, price_list_id, item.product_id)
    product = db.query(Product).filter(Product.product_id == item.product_id).first()
    base_price = Decimal(str(product.base_price or 0))
    markup_percentage = Decimal(str(item.markup_percentage or 0))
    
    # Calcular el precio sin IVA usando el middleware (para consistencia)
    final_price_calculated = calculate_final_price_with_markup(
        base_price=base_price,
        markup_percentage=markup_percentage
    )
    
    if existing:
        # Actualizar markup existente
        existing.markup_percentage = item.markup_percentage
        existing.final_price = final_price_calculated
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Crear nuevo item
        db_item = PriceListItem(
            price_list_id=price_list_id,
            product_id=item.product_id,
            markup_percentage=item.markup_percentage,
            final_price=final_price_calculated
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

""" Actualiza un item en la lista de precios """
def update_price_list_item(db: Session, price_list_id: int, product_id: str, item_update: PriceListItemUpdate) -> Optional[PriceListItem]:    
    db_item = get_price_list_item(db, price_list_id, product_id)
    if not db_item:
        return None
    
    db_item.markup_percentage = item_update.markup_percentage
    db.commit()
    db.refresh(db_item)
    return db_item

""" Elimina un item de la lista de precios """
def delete_price_list_item(db: Session, price_list_id: int, product_id: str) -> bool:    
    db_item = get_price_list_item(db, price_list_id, product_id)
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False

""" Actualizacion masiva de items en la lista de precios """
def bulk_update_price_list_items(db: Session, price_list_id: int, items: List[PriceListItemCreate]) -> List[PriceListItem]:
    result = []
    for item in items:
        db_item = create_price_list_item(db, price_list_id, item)
        result.append(db_item)
    return result

""" Obtiene el markup de un producto en una lista de precios """
def get_product_markup(db: Session, price_list_id: int, product_id: str) -> Optional[Decimal]:
    item = get_price_list_item(db, price_list_id, product_id)
    if item:
        return Decimal(str(item.markup_percentage))
    return None

""" Obtiene productos que NO estan en una lista de precios """
def get_products_not_in_price_list(db: Session, price_list_id: int, skip: int = 0, limit: int = 10, search: Optional[str] = None) -> List[Product]:
    product_ids_in_list = db.query(PriceListItem.product_id).filter(
        PriceListItem.price_list_id == price_list_id
    ).scalar_subquery()
    
    # Query: productos que NO estan en esa subquery
    query = db.query(Product).filter(
        ~Product.product_id.in_(product_ids_in_list),
        Product.is_active == True  # Solo productos activos
    )
    # Busqueda opcional
    if search:
        search_terms = search.strip().lower().split()
        if search_terms:
            word_filters = []
            for term in search_terms:
                pattern = f"%{term}%"
                word_filters.append(
                    (Product.product_id.ilike(pattern)) |
                    (Product.name.ilike(pattern)) |
                    (Product.codebar.ilike(pattern))
                )
            query = query.filter(and_(*word_filters))
    return query.offset(skip).limit(limit).all()

""" Obtiene productos que SI estan en una lista de precios con detalles calculados """
def get_products_in_price_list_with_details(
    db: Session, 
    price_list_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None,
    sanitize_costs: bool = False
) -> List[dict]:
    query = db.query(PriceListItem, Product).join(
        Product,
        PriceListItem.product_id == Product.product_id
    ).filter(
        PriceListItem.price_list_id == price_list_id,
        Product.is_active == True
    )
    
    # Busqueda opcional
    if search:
        search_terms = search.strip().lower().split()
        if search_terms:
            word_filters = []
            for term in search_terms:
                pattern = f"%{term}%"
                word_filters.append(
                    (Product.product_id.ilike(pattern)) |
                    (Product.name.ilike(pattern)) |
                    (Product.codebar.ilike(pattern))
                )
            query = query.filter(and_(*word_filters))
    
    # Ejecutar query con paginacion
    results = query.offset(skip).limit(limit).all()
    
    # Formatear resultados con cálculo de precios unificado
    formatted_results = []
    for price_list_item, product in results:
        # Usar el desglose centralizado unificado (soporta tax_inclusive y descuentos)
        breakdown = calculate_product_price_breakdown(
            product=product,
            price_item=price_list_item,
            db=db
        )
        final_price_with_iva = breakdown["final_price_with_iva"]
        price_without_iva = breakdown["price_without_iva"]
        base_price = breakdown["base_price"]
        markup_percentage = breakdown["markup_percentage"]
        
        if sanitize_costs:
            # Sanitizamos y sustraemos costos base y markups para roles de solo consulta pública interna
            sanitized_product = {
                "product_id": product.product_id,
                "name": product.name,
                "codebar": product.codebar,
                "description": product.description,
                "descripcion_2": product.descripcion_2,
                "unidad_medida": product.unidad_medida,
                "iva_percentage": float(product.iva_percentage or 0),
                "image_url": product.image_url,
                "image_version": product.image_version,
                "stock_count": product.stock_count,
                "is_active": product.is_active,
                "category_id": product.category_id,
                "display_priority": product.display_priority,
                "base_price": None
            }
            formatted_results.append({
                "product": sanitized_product,
                "base_price": None,
                "markup_percentage": None,
                "markup_amount": None,
                "price_with_markup": None,
                "iva_percentage": float(product.iva_percentage or 0),
                "final_price": round(float(final_price_with_iva), 2)
            })
        else:
            # Desglose financiero completo para administradores con catalog.prices
            formatted_results.append({
                "product": product,
                "base_price": round(float(base_price), 2),
                "markup_percentage": round(float(markup_percentage), 2),
                "markup_amount": round(float(price_without_iva - base_price), 2), # Ganancia sin IVA
                "price_with_markup": round(float(price_without_iva), 2), # Subtotal sin IVA
                "iva_percentage": float(product.iva_percentage or 0),
                "final_price": round(float(final_price_with_iva), 2) # Total con IVA
            })
    
    return formatted_results
