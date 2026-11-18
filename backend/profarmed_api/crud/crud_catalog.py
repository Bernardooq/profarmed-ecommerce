"""
CRUD y Consulta del Catálogo de Productos y Precios Dinámicos:

Funciones y Operaciones:
- Obtener lista de precios asignada al cliente (`CustomerInfo.price_list_id`) o lista activa para staff interno (User).
- Consultar catálogo paginado con paginación Lookahead (`get_lookahead_pagination`), ordenamiento y filtros múltiples.
- Búsqueda全文 por texto (SKU/código de barras, nombre, descripción), filtros de categoría, stock y promociones.
- Obtener detalle de un producto específico con desglose completo de costos, impuestos, márgenes y descuentos.

Reglas de Negocio y Permisos (PBAC / RBAC Dinámico):
1. Asignación de Precios según Tipo de Usuario y Rol:
   - Clientes B2B (`Customer`): Requieren obligatoriamente tener un `price_list_id` asignado en `CustomerInfo`.
   - Colaboradores Internos (`User` - cualquier rol dinámico): Se les asigna la primera lista de precios activa por defecto (o ID 1) para visualización general del catálogo (`catalog.view`).
2. Fórmula Oficial de Precios:
   - Precio sin IVA = Precio Base × (1 + Markup% de la lista)
   - Precio con IVA = Precio sin IVA × (1 + IVA%)
   - Precio Final = Precio con IVA - Descuento aplicable (si existe promoción activa)
3. Visibilidad:
   - Solo se devuelven productos con `is_active == True`.
"""

from datetime import datetime, timezone
from typing import Optional, Any, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_

from db.base import Customer, CustomerInfo, Product, PriceListItem, PriceList, User, ProductDiscount
from utils.price_utils import build_catalog_product_dict, calculate_product_price_breakdown
from utils.pagination import get_lookahead_pagination
from crud.crud_discount import get_active_discounts_for_products


"""Obtiene el ID de la lista de precios del cliente actual o asigna la lista activa para colaboradores internos"""
def _get_customer_price_list(current_user, db: Session) -> int:
    # Si es cliente, obtener su price_list_id asignada
    if isinstance(current_user, Customer):
        customer_info = db.query(CustomerInfo).filter(
            CustomerInfo.customer_id == current_user.customer_id
        ).first()
        
        if not customer_info or not customer_info.price_list_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tienes lista de precios. Contacta al administrador"
            )
        
        return customer_info.price_list_id

    # Si es colaborador interno (User con cualquier rol dinámico), asignar la primera lista de precios activa
    if isinstance(current_user, User):
        default_list = db.query(PriceList).filter(PriceList.is_active == True).order_by(PriceList.price_list_id.asc()).first()
        if default_list:
            return default_list.price_list_id
        return 1

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo clientes o usuarios autorizados pueden acceder al catalogo"
    )


def _query_catalog_by_price_list(
    db: Session,
    price_list_id: int,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    has_discount: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Función interna centralizada para consultar el catálogo de una lista de precios
    con filtros de búsqueda multi-campo, categorías, descuentos y ordenamiento Lookahead.
    """
    # Query base: productos activos en la lista de precios especificada
    query = db.query(Product, PriceListItem).join(
        PriceListItem,
        Product.product_id == PriceListItem.product_id
    ).options(
        joinedload(Product.category)
    ).filter(
        PriceListItem.price_list_id == price_list_id,
        Product.is_active == True
    )
    
    # Filtros de búsqueda multi-palabra
    if search:
        search_terms = search.strip().lower().split()
        if search_terms:
            word_filters = []
            for term in search_terms:
                pattern = f"%{term}%"
                word_filters.append(
                    (func.lower(Product.name).ilike(pattern)) |
                    (func.lower(Product.description).ilike(pattern)) |
                    (func.lower(Product.descripcion_2).ilike(pattern)) |
                    (func.lower(Product.codebar).ilike(pattern)) |
                    (Product.product_id.ilike(pattern))
                )
            query = query.filter(and_(*word_filters))
    
    # Filtro por categoría
    if category_id:
        query = query.filter(Product.category_id == category_id)
        
    # Filtro opcional por descuentos activos
    if has_discount:
        now = datetime.now(timezone.utc)
        disc_exists = db.query(ProductDiscount.product_id).filter(
            ProductDiscount.product_id == Product.product_id,
            ProductDiscount.is_active == True,
            ProductDiscount.start_date <= now,
            ProductDiscount.end_date >= now,
            (ProductDiscount.price_list_id == price_list_id) | (ProductDiscount.price_list_id.is_(None))
        ).exists()
        query = query.filter(disc_exists)
    
    # CASO ESPECIAL: Ordenamiento por precio o descuento en memoria
    # Asegura consistencia con las reglas de negocio dinámicas y Lookahead
    if sort_by in ["price", "discount"]:
        all_results = query.all()
        
        # Optimizacion O(1) queries: Cargar en un solo viaje todos los descuentos activos para los productos filtrados
        product_ids = [product.product_id for product, _ in all_results]
        discounts_map = get_active_discounts_for_products(
            db=db,
            product_ids=product_ids,
            price_list_id=price_list_id
        )
        
        catalog_products = []
        for product, price_item in all_results:
            active_disc = discounts_map.get(product.product_id)
            breakdown = calculate_product_price_breakdown(
                product=product,
                price_item=price_item,
                db=None,
                active_discount=active_disc
            )
            catalog_products.append(build_catalog_product_dict(product, breakdown["final_price"], discount_info=breakdown))
            
        if sort_by == "discount":
            catalog_products.sort(
                key=lambda x: float(x.get('discount_applied', 0)), 
                reverse=(sort_order == "desc")
            )
        else:
            catalog_products.sort(
                key=lambda x: x['final_price'], 
                reverse=(sort_order == "desc")
            )
        
        remaining_items = len(catalog_products) - (skip + limit)
        lookahead_pages = 0
        if remaining_items > 0:
            lookahead_pages = min(5, (remaining_items + limit - 1) // limit)
            
        return {
            "items": catalog_products[skip : skip + limit],
            "lookahead_pages": lookahead_pages
        }
    
    # OTROS CASOS: Ordenamiento en SQL (más eficiente para nombres/IDs/fechas)
    if sort_by == "name":
        query = query.order_by(Product.name.desc() if sort_order == "desc" else Product.name.asc())
    elif sort_by in ("created_at", "newest"):
        query = query.order_by(
            Product.created_at.desc() if sort_order == "desc" else Product.created_at.asc(),
            Product.product_id.desc()
        )
    elif sort_by == "priority":
        query = query.order_by(
            Product.display_priority.desc() if sort_order == "desc" else Product.display_priority.asc(),
            Product.created_at.desc(),
            Product.product_id.desc()
        )
    else:
        from crud.crud_product import is_catalog_priority_enabled
        if is_catalog_priority_enabled(db):
            query = query.order_by(Product.display_priority.asc(), Product.created_at.desc(), Product.product_id.desc())
        else:
            query = query.order_by(Product.created_at.desc(), Product.product_id.desc())
    
    # Paginación Lookahead
    res = get_lookahead_pagination(
        query=query,
        model_id_column=Product.product_id,
        skip=skip,
        limit=limit
    )
    
    # Construcción de respuesta con precios y descuentos calculados
    # Optimizacion O(1) queries: Cargar descuentos activos en un solo viaje para los items de la pagina
    page_product_ids = [product.product_id for product, _ in res["items"]]
    discounts_map = get_active_discounts_for_products(
        db=db,
        product_ids=page_product_ids,
        price_list_id=price_list_id
    )

    catalog_items = []
    for product, price_item in res["items"]:
        active_disc = discounts_map.get(product.product_id)
        breakdown = calculate_product_price_breakdown(
            product=product,
            price_item=price_item,
            db=None,
            active_discount=active_disc
        )
        catalog_items.append(build_catalog_product_dict(product, breakdown["final_price"], discount_info=breakdown))
    res["items"] = catalog_items
    
    return res


# =====================================================================
# FUNCIONES DE API PÚBLICAS
# =====================================================================

"""Lista productos del catálogo con precios personalizados del usuario o cliente autenticado"""
def get_catalog_products(
    db: Session,
    current_user,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    has_discount: Optional[bool] = None
) -> Dict[str, Any]:
    price_list_id = _get_customer_price_list(current_user, db)
    return _query_catalog_by_price_list(
        db=db,
        price_list_id=price_list_id,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
        has_discount=has_discount
    )


"""Obtiene un producto específico del catálogo con precio personalizado del cliente"""
def get_catalog_product(db: Session, current_user, product_id: str) -> dict:
    price_list_id = _get_customer_price_list(current_user, db)
    
    result = db.query(Product, PriceListItem).join(
        PriceListItem,
        Product.product_id == PriceListItem.product_id
    ).options(
        joinedload(Product.category)
    ).filter(
        Product.product_id == product_id,
        PriceListItem.price_list_id == price_list_id,
        Product.is_active == True
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no disponible en tu catalogo"
        )
    
    product, price_item = result
    breakdown = calculate_product_price_breakdown(product, price_item, db=db)
    return build_catalog_product_dict(product, breakdown["final_price"], discount_info=breakdown)


"""Obtiene productos del catálogo con precios de un cliente específico para pedidos manuales"""
def get_customer_catalog_products(
    db: Session,
    customer_id: int,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    has_discount: Optional[bool] = None
) -> Dict[str, Any]:
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == customer_id
    ).first()
    
    if not customer_info or not customer_info.price_list_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente no tiene lista de precios asignada"
        )
    
    return _query_catalog_by_price_list(
        db=db,
        price_list_id=customer_info.price_list_id,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
        has_discount=has_discount
    )


"""Obtiene todos los productos activos de una lista de precios (sin paginación) para exportación a Excel"""
def get_all_catalog_products_for_export(db: Session, price_list_id: int) -> list:
    return db.query(Product, PriceListItem).join(
        PriceListItem,
        Product.product_id == PriceListItem.product_id
    ).options(
        joinedload(Product.category)
    ).filter(
        PriceListItem.price_list_id == price_list_id,
        Product.is_active == True
    ).order_by(Product.name.asc()).all()


"""Obtiene las listas de precios activas marcadas como publicas para storefront general"""
def get_public_storefront_price_lists(db: Session):
    return db.query(PriceList).filter(
        PriceList.is_active == True,
        PriceList.is_public_storefront == True
    ).order_by(PriceList.price_list_id.asc()).all()


"""Consulta productos y precios de una lista publica storefront sin requerir autenticacion"""
def get_public_storefront_products(
    db: Session,
    price_list_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 12,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    has_discount: Optional[bool] = None
) -> Dict[str, Any]:
    if price_list_id is None:
        target_list = db.query(PriceList).filter(
            PriceList.is_active == True,
            PriceList.is_public_storefront == True
        ).order_by(PriceList.price_list_id.asc()).first()
        
        if not target_list:
            return {"items": [], "lookahead_pages": 0}
        selected_id = target_list.price_list_id
    else:
        target_list = db.query(PriceList).filter(
            PriceList.price_list_id == price_list_id,
            PriceList.is_active == True,
            PriceList.is_public_storefront == True
        ).first()
        
        if not target_list:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta lista de precios no esta autorizada para consulta publica en storefront"
            )
        selected_id = target_list.price_list_id

    return _query_catalog_by_price_list(
        db=db,
        price_list_id=selected_id,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
        has_discount=has_discount
    )



def get_public_storefront_product_detail(
    db: Session,
    product_id: str,
    price_list_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Obtiene el detalle público de un producto activo dentro de una lista de precios
    marcada con is_public_storefront == True (sin exponer costos ni markups internos).
    Retorna None si no hay lista pública activa o el producto no pertenece a ella.
    """
    query_list = db.query(PriceList).filter(
        PriceList.is_active == True,
        PriceList.is_public_storefront == True,
    )
    if price_list_id is not None:
        target_list = query_list.filter(PriceList.price_list_id == price_list_id).first()
    else:
        target_list = query_list.order_by(PriceList.price_list_id.asc()).first()

    if not target_list:
        return None

    row = db.query(Product, PriceListItem).join(
        PriceListItem,
        Product.product_id == PriceListItem.product_id,
    ).options(
        joinedload(Product.category)
    ).filter(
        PriceListItem.price_list_id == target_list.price_list_id,
        Product.product_id == product_id,
        Product.is_active == True,
    ).first()

    if not row:
        return None

    product, price_item = row
    discounts_map = get_active_discounts_for_products(
        db,
        [product.product_id],
        target_list.price_list_id,
    )
    breakdown = calculate_product_price_breakdown(
        product=product,
        price_item=price_item,
        db=db,
        active_discount=discounts_map.get(product.product_id),
    )

    product_dict = build_catalog_product_dict(
        product=product,
        final_price=breakdown["final_price"],
        discount_info=breakdown,
    )
    product_dict["price_list_id"] = target_list.price_list_id
    product_dict["price_list_name"] = target_list.list_name
    if product.updated_at:
        product_dict["updated_at"] = product.updated_at.isoformat()
    return product_dict


def get_public_storefront_sitemap_items(
    db: Session,
    limit: int = 45000,
) -> Dict[str, Any]:
    """
    Retorna los productos activos indexables pertenecientes a listas de precios
    activas con is_public_storefront == True para generación de sitemap XML.
    Si no existe ninguna lista pública activa, retorna has_public_storefront=False.
    """
    public_lists = get_public_storefront_price_lists(db)
    if not public_lists:
        return {"has_public_storefront": False, "products": []}

    list_ids = [pl.price_list_id for pl in public_lists]
    rows = (
        db.query(
            Product.product_id,
            Product.name,
            Product.image_url,
            Product.image_version,
            Product.updated_at,
        )
        .join(PriceListItem, Product.product_id == PriceListItem.product_id)
        .filter(
            PriceListItem.price_list_id.in_(list_ids),
            Product.is_active == True,
        )
        .distinct()
        .order_by(Product.product_id.asc())
        .limit(limit)
        .all()
    )

    return {
        "has_public_storefront": True,
        "products": [
            {
                "product_id": r.product_id,
                "name": r.name,
                "image_url": r.image_url,
                "image_version": r.image_version or 1,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }
