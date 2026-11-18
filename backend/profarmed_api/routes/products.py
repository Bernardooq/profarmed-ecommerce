"""
Routes para Administracion de Productos

Endpoints CRUD para gestion de productos del catalogo:
- GET / - Lista de productos con filtros
- GET /{id} - Detalle de producto
- GET /codebar/{codebar} - Buscar por codebar
- GET /{id}/similar - Productos similares basados en componentes
- POST / - Crear producto
- PUT /{id} - Actualizar producto
- DELETE /{id} - Eliminar producto (soft delete)
- PATCH /{id}/stock - Ajustar inventario

Permisos:
- GET: Según capacidades ('catalog.view', 'products.cost')
- POST/PUT/DELETE/PATCH: PBAC granular ('products.create', 'products.edit', 'products.delete', 'products.stock')

Nota: Los precios finales para clientes se calculan en /catalog
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
import boto3
from botocore.exceptions import ClientError
import io
from PIL import Image

from dependencies import get_db, get_current_user, require_permission
from db.base import User
from schemas.product import ProductCreate, ProductUpdate, Product, ProductStockHoldsResponse, ProductStockHoldItem
from crud.crud_product import (
    get_products,
    get_products_query,
    get_product, 
    get_product_by_codebar,
    create_product,
    update_product,
    delete_product,
    update_stock,
    get_similar_products,
    increment_image_version,
    shuffle_catalog_priorities
)
from utils.pagination import get_lookahead_pagination
from db.base import Product as ProductModel
from core.config import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

router = APIRouter()


class StockUpdate(BaseModel):
    # Schema para ajustar inventario
    quantity: int


class ProductLookaheadResponse(BaseModel):
    items: List[Product]
    lookahead_pages: int

""" GET / - Lista de productos con filtros """
@router.get("/", response_model=ProductLookaheadResponse)
def read_products(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Maximo de registros"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoria"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado: True=activos, False=inactivos, None=todos"),
    search: Optional[str] = Query(None, description="Buscar por nombre/descripcion"),
    codebar_search: Optional[str] = Query(None, description="Buscar por codigo de barras"),
    stock_filter: Optional[str] = Query(None, description="Filtrar por stock: in_stock, out_of_stock, low_stock, with_holds"),
    sort_by: Optional[str] = Query(None, description="Ordenar por: price, name, created_at, newest, priority, relevance"),
    sort_order: Optional[str] = Query("asc", description="Orden: asc o desc"),
    image: Optional[bool] = Query(None, description="Filtrar por imagen"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Obtener el query sin ejecutarlo
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
    
    # Paginar con lookahead
    res = get_lookahead_pagination(
        query=query,
        model_id_column=ProductModel.product_id,
        skip=skip,
        limit=limit
    )
    
    # Validar permisos PBAC de acceso al catálogo para usuarios internos
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and has_perm("system.admin")
    can_view_catalog = has_admin or (callable(has_perm) and (
        has_perm("catalog.view") or has_perm("warehouse.view") or has_perm("warehouse.operator")
    ))
    if not can_view_catalog and hasattr(current_user, "role_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso 'catalog.view' para consultar productos del catálogo."
        )

    can_view_location = has_admin or (callable(has_perm) and (has_perm("catalog.view") or has_perm("warehouse.view") or has_perm("warehouse.operator")))
    can_view_cost = has_admin or (callable(has_perm) and (has_perm("products.cost") or has_perm("catalog.prices")))
    can_view_reserved = has_admin or (callable(has_perm) and (
        has_perm("catalog.view") and (has_perm("products.stock") or has_perm("products.edit"))
    ))

    # Verificar si la regla 101 (order.apartar) está activa en system_configs
    from utils.stock_rules_utils import is_config_active, CONFIG_ID_APARTAR
    from db.base import OrderStockHold
    from sqlalchemy import func

    config_101_active = is_config_active(db, CONFIG_ID_APARTAR)

    # Si se cumplen permisos y config 101 activa, calcular apartados de stock por producto
    reserved_map = {}
    if config_101_active and can_view_reserved and res["items"]:
        pids = [p.product_id for p in res["items"]]
        holds_grouped = db.query(
            OrderStockHold.product_id,
            func.coalesce(func.sum(OrderStockHold.quantity), 0)
        ).filter(OrderStockHold.product_id.in_(pids)).group_by(OrderStockHold.product_id).all()
        reserved_map = {row[0]: int(row[1]) for row in holds_grouped}

    for p in res["items"]:
        if not can_view_location:
            p.location = ""
        if not can_view_cost:
            p.base_price = None

        if config_101_active and can_view_reserved:
            p.reserved_stock = reserved_map.get(p.product_id, 0)
        else:
            p.reserved_stock = None
            
    return res

""" GET /{id} - Detalle de producto especifico """
@router.get("/{product_id}", response_model=Product)
def read_product(product_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Detalle de un producto especifico
    product = get_product(db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    # Validar permisos PBAC de acceso al catálogo para usuarios internos
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and has_perm("system.admin")
    can_view_catalog = has_admin or (callable(has_perm) and (
        has_perm("catalog.view") or has_perm("warehouse.view") or has_perm("warehouse.operator")
    ))
    if not can_view_catalog and hasattr(current_user, "role_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso 'catalog.view' para consultar productos del catálogo."
        )

    can_view_location = has_admin or (callable(has_perm) and (has_perm("catalog.view") or has_perm("warehouse.view") or has_perm("warehouse.operator")))
    can_view_cost = has_admin or (callable(has_perm) and (has_perm("products.cost") or has_perm("catalog.prices")))
    can_view_reserved = has_admin or (callable(has_perm) and (
        has_perm("catalog.view") and (has_perm("products.stock") or has_perm("products.edit"))
    ))

    if not can_view_location:
        product.location = ""
    if not can_view_cost:
        product.base_price = None

    from utils.stock_rules_utils import is_config_active, CONFIG_ID_APARTAR
    from db.base import OrderStockHold
    from sqlalchemy import func

    if is_config_active(db, CONFIG_ID_APARTAR) and can_view_reserved:
        hold_total = db.query(func.coalesce(func.sum(OrderStockHold.quantity), 0)).filter(
            OrderStockHold.product_id == product_id
        ).scalar() or 0
        product.reserved_stock = int(hold_total)
    else:
        product.reserved_stock = None
        
    return product

""" GET /codebar/{codebar} - Buscar producto por codebar (codigo unico) """
@router.get("/codebar/{codebar}", response_model=Product)
def read_product_by_codebar(codebar: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Buscar producto por codebar (codigo unico) 
    product = get_product_by_codebar(db, codebar=codebar)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    # Validar permisos PBAC de acceso al catálogo para usuarios internos
    has_perm = getattr(current_user, "has_permission", None)
    has_admin = callable(has_perm) and has_perm("system.admin")
    can_view_catalog = has_admin or (callable(has_perm) and (
        has_perm("catalog.view") or has_perm("warehouse.view") or has_perm("warehouse.operator")
    ))
    if not can_view_catalog and hasattr(current_user, "role_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso 'catalog.view' para consultar productos del catálogo."
        )

    can_view_location = has_admin or (callable(has_perm) and (has_perm("catalog.view") or has_perm("warehouse.view") or has_perm("warehouse.operator")))
    can_view_cost = has_admin or (callable(has_perm) and (has_perm("products.cost") or has_perm("catalog.prices")))

    if not can_view_location:
        product.location = ""
    if not can_view_cost:
        product.base_price = None
        
    return product

""" POST / - Crear un nuevo producto """
@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_new_product(product: ProductCreate, db: Session = Depends(get_db), current_user = Depends(require_permission("products.create"))):
    # Crea un nuevo producto
    if product.base_price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El precio base no puede ser negativo"
        )
    
    if product.base_price == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El precio base debe ser mayor a 0"
        )
    
    # === VALIDAR IVA ===
    if product.iva_percentage < 0 or product.iva_percentage > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El porcentaje de IVA debe estar entre 0 y 100"
        )
    
    # === VALIDAR STOCK ===
    if product.stock_count < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El stock no puede ser negativo"
        )
    
    # === VERIFICAR codebar uNICO ===
    db_product = get_product_by_codebar(db, codebar=product.codebar)
    if db_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El codebar '{product.codebar}' ya esta registrado"
        )
    
    return create_product(db=db, product=product)

""" PUT /{product_id} - Actualizar un producto existente """
@router.put("/{product_id}", response_model=Product)
def update_existing_product(product_id: str, product: ProductUpdate,
    db: Session = Depends(get_db), current_user = Depends(require_permission("products.edit"))):
    # Actualiza un producto existente
    if product.base_price is not None:
        if product.base_price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El precio base no puede ser negativo"
            )
        if product.base_price == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El precio base debe ser mayor a 0"
            )
    
    # validar IVA
    if product.iva_percentage is not None:
        if product.iva_percentage < 0 or product.iva_percentage > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El porcentaje de IVA debe estar entre 0 y 100"
            )
    
    db_product = update_product(db, product_id=product_id, product=product)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    return db_product

""" DELETE /{product_id} - Eliminar un producto (soft delete) """
@router.delete("/{product_id}", response_model=Product)
def delete_existing_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("products.delete"))
):
    # Elimina un producto (soft delete)
    try:
        db_product = get_product(db, product_id=product_id)
        if not db_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )

        # Eliminar imagen de S3 si existe
        if db_product.image_url and settings.CLOUDFRONT_IMGS_URL in db_product.image_url:
            s3_key = db_product.image_url.split("/")[-1].split("?")[0]
            try:
                s3_client.delete_object(Bucket=settings.BUCKET_IMGS, Key=s3_key)
            except ClientError:
                pass

        db_product = delete_product(db, product_id=product_id)
        return db_product
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el producto porque ya forma parte de uno o más pedidos."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error inesperado al eliminar: {str(e)}"
        )

""" PATCH /{product_id}/stock - Ajustar inventario de un producto """
@router.patch("/{product_id}/stock", response_model=Product)
def adjust_product_stock(
    product_id: str,
    stock_update: StockUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("products.stock"))
):
    # Ajusta el inventario de un producto (positivo o negativo)
    current_product = get_product(db, product_id=product_id)
    if not current_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    new_stock = current_product.stock_count + stock_update.quantity
    
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede restar {abs(stock_update.quantity)} unidades. Stock actual: {current_product.stock_count}"
        )
    
    db_product = update_stock(db, product_id=product_id, quantity=stock_update.quantity)
    
    return db_product


""" GET /{product_id}/stock-holds - Listar apartados activos (order_stock_holds) de un producto """
@router.get("/{product_id}/stock-holds", response_model=ProductStockHoldsResponse)
def get_product_stock_holds(
    product_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.view", "products.stock", "products.edit", "system.admin"))
):
    has_perm = getattr(current_user, "has_permission", None)
    is_admin = getattr(current_user, "role", None) == "admin" or (callable(has_perm) and has_perm("system.admin"))
    can_view = is_admin or (callable(has_perm) and has_perm("catalog.view") and (has_perm("products.stock") or has_perm("products.edit")))
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren los permisos 'catalog.view' y ('products.stock' o 'products.edit'), o 'system.admin', para consultar los apartados de reserva."
        )

    product = get_product(db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto {product_id} no encontrado"
        )
    
    from db.base import OrderStockHold, Order, Customer
    from sqlalchemy import func

    total_holds = db.query(func.count(OrderStockHold.order_id)).filter(
        OrderStockHold.product_id == product_id
    ).scalar() or 0

    total_quantity = db.query(func.coalesce(func.sum(OrderStockHold.quantity), 0)).filter(
        OrderStockHold.product_id == product_id
    ).scalar() or 0

    holds_query = (
        db.query(
            OrderStockHold.order_id,
            OrderStockHold.product_id,
            OrderStockHold.quantity,
            OrderStockHold.created_at,
            Order.customer_id,
            Customer.full_name.label("customer_name"),
            Order.status.label("order_status"),
            Order.total_amount.label("order_total"),
        )
        .outerjoin(Order, OrderStockHold.order_id == Order.order_id)
        .outerjoin(Customer, Order.customer_id == Customer.customer_id)
        .filter(OrderStockHold.product_id == product_id)
        .order_by(OrderStockHold.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    items = []
    for h in holds_query:
        status_val = h.order_status.value if hasattr(h.order_status, "value") else str(h.order_status or "")
        items.append(
            ProductStockHoldItem(
                order_id=h.order_id,
                product_id=h.product_id,
                quantity=h.quantity,
                created_at=h.created_at,
                customer_id=h.customer_id,
                customer_name=h.customer_name or (f"Cliente #{h.customer_id}" if h.customer_id else "N/A"),
                order_status=status_val,
                order_total=h.order_total,
            )
        )

    return ProductStockHoldsResponse(
        product_id=product.product_id,
        product_name=product.name,
        total_holds=total_holds,
        total_quantity=int(total_quantity),
        items=items
    )


""" DELETE /{product_id}/stock-holds/{order_id} - Liberar/eliminar apartado de stock de un pedido """
@router.delete("/{product_id}/stock-holds/{order_id}")
def delete_product_stock_hold(
    product_id: str,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.view", "products.stock", "products.edit", "system.admin"))
):
    has_perm = getattr(current_user, "has_permission", None)
    is_admin = getattr(current_user, "role", None) == "admin" or (callable(has_perm) and has_perm("system.admin"))
    can_delete = is_admin or (callable(has_perm) and has_perm("catalog.view") and (has_perm("products.stock") or has_perm("products.edit")))
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren los permisos 'catalog.view' y ('products.stock' o 'products.edit'), o 'system.admin', para eliminar apartados de reserva."
        )

    from db.base import OrderStockHold

    hold = db.query(OrderStockHold).filter(
        OrderStockHold.product_id == product_id,
        OrderStockHold.order_id == order_id
    ).first()

    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró apartado para la orden #{order_id} y producto {product_id}"
        )

    released_qty = hold.quantity
    db.delete(hold)
    db.commit()

    return {
        "message": f"Apartado de {released_qty} piezas de la orden #{order_id} liberado exitosamente",
        "released_quantity": released_qty,
        "order_id": order_id,
        "product_id": product_id
    }



@router.post("/upload-image")
def api_upload_product_image(
    product_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("products.edit"))
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    product = get_product(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    s3_key = f"{product_id}.webp"

    try:
        image_bytes = file.file.read()
        img = Image.open(io.BytesIO(image_bytes))

        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        TARGET_SIZE_BYTES = 50 * 1024
        MAX_DIMENSION = 1200
        current_dimension = MAX_DIMENSION
        current_quality = 70
        out_io = io.BytesIO()

        for intento in range(6):
            img_procesada = img.copy()

            if max(img_procesada.size) > current_dimension:
                if img_procesada.width > img_procesada.height:
                    new_w = current_dimension
                    new_h = int((current_dimension / img_procesada.width) * img_procesada.height)
                else:
                    new_h = current_dimension
                    new_w = int((current_dimension / img_procesada.height) * img_procesada.width)
                img_procesada = img_procesada.resize((new_w, new_h), Image.Resampling.LANCZOS)

            out_io.seek(0)
            out_io.truncate(0)
            img_procesada.save(out_io, 'WEBP', quality=current_quality, method=6)

            if out_io.tell() <= TARGET_SIZE_BYTES:
                break

            if intento <= 2:
                current_quality = max(45, current_quality - 12)
            else:
                current_dimension = int(current_dimension * 0.80)
                current_quality = max(45, current_quality - 8)

        out_io.seek(0)

        s3_client.upload_fileobj(
            out_io,
            settings.BUCKET_IMGS,
            s3_key,
            ExtraArgs={
                'ContentType': 'image/webp',
                'CacheControl': 'max-age=2592000'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al procesar o subir imagen: {str(e)}")

    product = increment_image_version(db, product_id=product_id)
    image_url = f"https://{settings.CLOUDFRONT_IMGS_URL}/{s3_key}?v={product.image_version}"
    product.image_url = image_url
    db.commit()
    db.refresh(product)
    return {"image_url": image_url}


class ImageUrlUpdate(BaseModel):
    image_url: str


""" PATCH /{product_id}/image - Actualizar la URL de la imagen de un producto """
@router.patch("/{product_id}/image", response_model=Product)
def update_product_image_url(
    product_id: str,
    body: ImageUrlUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("products.edit"))
):
    # Actualiza la URL de la imagen de un producto
    db_product = get_product(db, product_id=product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    db_product.image_url = body.image_url
    db.commit()
    db.refresh(db_product)
    return db_product


""" PATCH /{product_id}/image-version - Incrementar la version de la imagen """
@router.patch("/{product_id}/image-version", response_model=Product)
def increment_image_version_route(
    product_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("products.edit"))
):
    # Incrementa la version de la imagen para forzar refresco de cache
    from crud.crud_product import increment_image_version
    db_product = increment_image_version(db, product_id=product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    return db_product


""" GET /{product_id}/similar - Obtiene productos similares basados en componentes activos """
@router.get("/{product_id}/similar")
def read_similar_products(
    product_id: str,
    limit: int = Query(5, ge=1, le=10, description="Cantidad maxima de productos similares (max 10)"),
    min_similarity: float = Query(0.3, ge=0.1, le=1.0, description="Umbral minimo de similitud (0.1-1.0)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Encuentra productos similares basados en componentes activos en descripcion_2.
    
    Algoritmo:
    - Extrae componentes de descripcion_2 (ej: AMANTADINA, CLORFENAMINA, PARACETAMOL)
    - Calcula similitud con otros productos usando Jaccard similarity
    - Retorna top N productos con mayor similitud
    - Si el usuario está autenticado, usa su lista de precios para calcular precios
    
    Returns:
        {
            "target_product": {...},
            "similar_products": [
                {
                    "product": {...},
                    "similarity_score": 0.85,
                    "price_info": {...}
                }
            ]
        }
    """
    # Verificar que el producto existe
    target_product = get_product(db, product_id=product_id)
    if not target_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    # Obtener price_list_id del cliente autenticado
    price_list_id = None
    if current_user and hasattr(current_user, 'customer_info') and current_user.customer_info:
        price_list_id = current_user.customer_info.price_list_id
    
    # Obtener productos similares
    similar_products = get_similar_products(
        db=db,
        product_id=product_id,
        price_list_id=price_list_id,
        limit=limit,
        min_similarity=min_similarity
    )
    
    return {
        "target_product": target_product,
        "similar_products": similar_products
    }

""" POST /shuffle-catalog - Barajar productos sin prioridad fija (display_priority >= 1,000,000) """
@router.post("/shuffle-catalog", status_code=status.HTTP_200_OK)
def shuffle_catalog(
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("products.edit"))
):
    count = shuffle_catalog_priorities(db)
    return {
        "success": True,
        "message": f"Catálogo barajado exitosamente. {count} productos actualizados.",
        "shuffled_count": count
    }