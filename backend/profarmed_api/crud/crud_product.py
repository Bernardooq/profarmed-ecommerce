"""
CRUD y Gestión Integral de Productos del Catálogo (Products & Inventory):

Funciones y Operaciones:
- Operaciones CRUD de productos (crear, consultar por ID o código de barras, actualizar, eliminar/desactivar).
- Consultas avanzadas con filtros dinámicos (categoría, stock bajo/agotado, activo, con imagen).
- Algoritmo inteligente de productos similares / recomendaciones basado en componentes activos y descripción.
- Control y ajuste de inventario (`stock_count`).
- Cálculo de precios con desglose de IVA y formato comercial.

Estructura de Datos y Reglas de Negocio:
1. Identificadores:
   - `product_id`: Código alfanumérico único del producto (ej. "FAR74").
   - `codebar`: Código de barras EAN/UPC para pistolas lectoras láser de almacén.
2. Control de Inventario:
   - Umbral de bajo stock: `stock_count <= 10`.
   - `is_active = False`: Oculta el producto de catálogos y búsquedas públicas sin romper pedidos históricos.
3. Recomendaciones Inteligentes:
   - Extrae principios activos y dosificaciones desde `description` y `descripcion_2` para sugerir alternativas terapéuticas.
4. Control de Acceso y Reglas PBAC / RBAC Dinámico:
   - Consulta pública / comercial de productos y recomendaciones: Requiere permiso `catalog.view` o acceso público autenticado.
   - Creación y edición de productos: Requiere permiso `products.create`, `products.edit` o `catalog.manage`.
   - Ajuste manual de inventario (`stock_count`): Requiere permiso `catalog.stock` o `inventory.manage`.
   - Eliminación / Desactivación: Requiere permiso `products.delete` o `catalog.manage`.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, Query
from sqlalchemy import and_
from utils.price_utils import get_product_final_price, format_price_info, apply_iva

from db.base import Product, ProductRecommendation
from schemas.product import ProductCreate, ProductUpdate
from utils.product_similarity import extract_active_components, calculate_similarity_score


""" Obtiene un producto por ID con su categoria """
def get_product(db: Session, product_id: str) -> Optional[Product]:
    return db.query(Product).options(
        joinedload(Product.category)  
    ).filter(Product.product_id == product_id).first()

""" Obtiene un producto por codigo de barras con su categoria """
def get_product_by_codebar(db: Session, codebar: str) -> Optional[Product]:
    return db.query(Product).options(
        joinedload(Product.category)
    ).filter(Product.codebar == codebar).first()

def is_catalog_priority_enabled(db: Session) -> bool:
    """Verifica si la configuración catalog.order_by_priority está activa en system_configs"""
    from db.base import SystemConfig
    cfg = db.query(SystemConfig).filter(
        (SystemConfig.config_id == 103) | (SystemConfig.config_name == "catalog.order_by_priority")
    ).first()
    return cfg.is_active if cfg else True

""" Obtiene el objeto Query de productos con filtros y ordenamiento """
def get_products_query(db: Session, category_id: Optional[int] = None, 
                       is_active: Optional[bool] = None, stock_filter: Optional[str] = None,
                       sort_by: Optional[str] = None, sort_order: Optional[str] = "asc", 
                       image: Optional[bool] = None, search: Optional[str] = None,
                       codebar_search: Optional[str] = None) -> Query:
    LOW_STOCK_THRESHOLD = 10  # Umbral para considerar bajo stock
    query = db.query(Product).options(joinedload(Product.category))
    
    # Filtros base
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    if image is not None:
        if image:
            query = query.filter(Product.image_url.isnot(None), Product.image_url != "")
        else:
            query = query.filter((Product.image_url.is_(None)) | (Product.image_url == ""))
    
    # Filtro de Búsqueda (Multi-palabra)
    if search:
        search_terms = search.strip().split()
        if search_terms:
            word_filters = []
            for term in search_terms:
                pattern = f"%{term}%"
                word_filters.append(
                    (Product.product_id.ilike(pattern)) |
                    (Product.name.ilike(pattern)) |
                    (Product.description.ilike(pattern)) |
                    (Product.descripcion_2.ilike(pattern)) |
                    (Product.codebar.ilike(pattern)) |
                    (Product.location.ilike(pattern))
                )
            query = query.filter(and_(*word_filters))
    
    # Filtro por código de barras exacto/parcial
    if codebar_search:
        query = query.filter(Product.codebar.ilike(f"%{codebar_search}%"))

    # Filtrar por nivel de stock
    if stock_filter:
        if stock_filter == "out_of_stock":
            query = query.filter(Product.stock_count == 0)
        elif stock_filter == "low_stock":
            query = query.filter(Product.stock_count > 0, Product.stock_count < LOW_STOCK_THRESHOLD)
        elif stock_filter == "in_stock":
            query = query.filter(Product.stock_count >= LOW_STOCK_THRESHOLD)
        elif stock_filter in ("with_holds", "holds", "reserved"):
            from db.base import OrderStockHold
            query = query.filter(
                Product.product_id.in_(
                    db.query(OrderStockHold.product_id).filter(OrderStockHold.quantity > 0).distinct()
                )
            )

    # Ordenamiento
    if sort_by == "price":
        query = query.order_by(Product.base_price.desc()) if sort_order == "desc" else query.order_by(Product.base_price.asc())
    elif sort_by == "name":
        query = query.order_by(Product.name.desc()) if sort_order == "desc" else query.order_by(Product.name.asc())
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
        # Orden por defecto: evalúa el flag catalog.order_by_priority
        if is_catalog_priority_enabled(db):
            query = query.order_by(Product.display_priority.asc(), Product.created_at.desc(), Product.product_id.desc())
        else:
            query = query.order_by(Product.created_at.desc(), Product.product_id.desc())
    
    return query

""" Obtiene lista de productos con filtros y ordenamiento """
def get_products(db: Session, skip: int = 0, limit: int = 100, category_id: Optional[int] = None, 
                 is_active: Optional[bool] = None, stock_filter: Optional[str] = None,
                 sort_by: Optional[str] = None, sort_order: Optional[str] = "asc", 
                 image: Optional[bool] = None, search: Optional[str] = None,
                 codebar_search: Optional[str] = None) -> List[Product]:
    query = get_products_query(
        db, 
        category_id=category_id, 
        is_active=is_active, 
        stock_filter=stock_filter,
        sort_by=sort_by, 
        sort_order=sort_order, 
        image=image,
        search=search,
        codebar_search=codebar_search
    )
    return query.offset(skip).limit(limit).all()

""" Crea un nuevo producto en el catalogo """
def create_product(db: Session, product: ProductCreate) -> Product:
    product_data = product.model_dump()
    # Normalizar image_url: guardar NULL en vez de string vacío
    if not product_data.get("image_url"):
        product_data["image_url"] = None
    if product_data.get("display_priority") is None:
        product_data["display_priority"] = 1000000
    db_product = Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

""" Actualiza un producto existente """
def update_product(db: Session, product_id: str, product: ProductUpdate) -> Optional[Product]:
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    
    # Actualizar solo campos proporcionados
    update_data = product.dict(exclude_unset=True)
    # Normalizar image_url: guardar NULL en vez de string vacío
    if "image_url" in update_data and not update_data["image_url"]:
        update_data["image_url"] = None
    if "location" in update_data:
        update_data["location"] = (update_data["location"] or "").strip()
    if "display_priority" in update_data and update_data["display_priority"] is None:
        update_data["display_priority"] = 1000000
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

""" Baraja aleatoriamente los productos con display_priority >= 1,000,000 """
def shuffle_catalog_priorities(db: Session) -> int:
    from sqlalchemy import text
    result = db.execute(
        text("""
            UPDATE products 
            SET display_priority = 1000000 + FLOOR(RANDOM() * 8999999)::int
            WHERE display_priority >= 1000000 AND is_active = TRUE;
        """)
    )
    db.commit()
    return result.rowcount

""" Elimina (soft delete) un producto """
def delete_product(db: Session, product_id: str) -> Optional[Product]:
    # Elimina un producto
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product

""" Actualiza el stock de un producto """
def update_stock(db: Session, product_id: str, quantity: int) -> Optional[Product]:
    db_product = get_product(db, product_id)
    if db_product:
        if db_product.stock_count + quantity < 0:
            raise ValueError("Stock no puede ser negativo")
        db_product.stock_count += quantity
        db.commit()
        db.refresh(db_product)
    return db_product

""" Incrementa la version de la imagen para forzar refresco de cache """
def increment_image_version(db: Session, product_id: str) -> Optional[Product]:
    db_product = get_product(db, product_id)
    if db_product:
        db_product.image_version = (db_product.image_version or 0) + 1
        db.commit()
        db.refresh(db_product)
    return db_product


from utils.price_utils import get_catalog_product_info

def get_similar_products(
    db: Session,
    product_id: str,
    price_list_id: Optional[int] = None,
    limit: int = 5,
    min_similarity: float = 0.3
) -> List[dict]:
    """
    Versión Optimizada v2.2: 
    Usa la tabla pre-calculada 'product_recommendations' y el middleware de precios.
    """
    
    recommendations = (
        db.query(ProductRecommendation)
        .filter(
            ProductRecommendation.product_id == product_id,
            ProductRecommendation.score >= min_similarity
        )
        .options(joinedload(ProductRecommendation.recommended_product))
        .order_by(ProductRecommendation.score.desc())
        .limit(limit)
        .all()
    )

    if not recommendations:
        return []

    results = []
    
    for rec in recommendations:
        product = rec.recommended_product
        
        if not product.is_active:
            continue

        # Obtener datos del producto formateados para el catálogo (incluyendo precios si hay price_list_id)
        product_data = None
        if price_list_id:
            product_data = get_catalog_product_info(db, product, price_list_id)
        
        # Si no hay lista de precios o no se encontró el item, construimos un dict básico seguro
        if not product_data:
            # Reutilizamos build_catalog_product_dict con precio 0 o None si es necesario, 
            # pero mejor lo construimos aquí para casos donde no hay precio.
            product_data = {
                'product_id': product.product_id,
                'codebar': product.codebar,
                'name': product.name,
                'description': product.description,
                'descripcion_2': product.descripcion_2,
                'unidad_medida': product.unidad_medida,
                'iva_percentage': float(product.iva_percentage or 0),
                'image_url': product.image_url,
                'stock_count': product.stock_count,
                'is_active': product.is_active,
                'category_id': product.category_id,
                'category': {
                    'category_id': product.category.category_id,
                    'name': product.category.name
                } if product.category else None,
                'final_price': None,
                'image_version': product.image_version,
            }
        
        results.append({
            "product": product_data,
            "similarity_score": round(float(rec.score), 3)
        })

    return results