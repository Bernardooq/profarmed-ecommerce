"""
Routes para Catalogo de Clientes

Endpoints para que los clientes naveguen productos con precios personalizados:
- GET /products - Lista de productos con precios calculados
- GET /products/{id} - Detalle de producto con precio calculado
- GET /products/export - Exportar catalogo a XLSX
- GET /customer/{customer_id}/products - Lista de productos con precios del cliente (comercial)
- GET /customer/{customer_id}/products/{product_id}/similar - Productos similares con precios del cliente

Sistema de Precios:
1. Cada cliente tiene una PriceList asignada (via CustomerInfo)
2. La PriceList contiene PriceListItems con markup por producto
3. Se calcula: final_price = (base_price * (1 + markup/100)) * (1 + iva/100)

Clientes autenticados y usuarios internos con capacidad correspondiente tienen acceso.
"""

from io import BytesIO
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import List, Optional
from urllib.parse import quote
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse, Response
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy.orm import Session

from db.base import CustomerInfo, Customer, Product, PriceListItem, PriceList, User
from core import config
from crud.crud_product import get_similar_products
from crud.crud_commercial_group import user_can_manage_order
from crud import crud_catalog
from dependencies import get_db, get_current_user, require_permission
from utils.price_utils import calculate_catalog_price

router = APIRouter()


def check_catalog_access(current_user = Depends(get_current_user)):
    """
    Permite el acceso al catálogo tanto a clientes (storefront)
    como a usuarios internos que posean 'catalog.view', 'catalog.customer_view' u 'orders.create'.
    """
    if isinstance(current_user, Customer):
        return current_user
    if isinstance(current_user, User):
        if (
            current_user.has_permission("catalog.view")
            or current_user.has_permission("catalog.customer_view")
            or current_user.has_permission("orders.create")
            or current_user.has_permission("system.admin")
        ):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso insuficiente: Se requiere la capacidad 'catalog.view' o 'catalog.customer_view'"
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales no válidas"
    )


""" GET /products - Lista de productos con precios calculados """
@router.get("/products")
def get_catalog_products(
    skip: int = Query(0, ge=0, description="Registros a saltar (paginacion)"),
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"),
    search: Optional[str] = Query(None, description="Buscar por nombre, descripcion o codebar"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoria"),
    sort_by: Optional[str] = Query(None, description="Ordenar por: name, price, discount, created_at, newest, priority, relevance"),
    sort_order: Optional[str] = Query("asc", description="Orden: asc o desc"),
    has_discount: Optional[bool] = Query(None, description="Filtrar solo productos con descuentos activos"),
    current_user = Depends(check_catalog_access),
    db: Session = Depends(get_db)
):
    # Obtiene productos del catalogo con precios personalizados
    return crud_catalog.get_catalog_products(
        db=db, current_user=current_user, skip=skip, limit=limit,
        search=search, category_id=category_id, sort_by=sort_by,
        sort_order=sort_order, has_discount=has_discount
    )


""" GET /products/export - Exportar catalogo a XLSX """
@router.get("/products/export")
def export_catalog_xlsx(
    price_list_id: Optional[int] = Query(None, description="ID de lista de precios (requiere catalog.prices)"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if isinstance(current_user, User):
        has_export_perm = current_user.has_permission("catalog.export") or current_user.has_permission("system.admin")
        if not has_export_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permiso insuficiente: Se requiere la capacidad 'catalog.export'"
            )
        
        has_prices_perm = current_user.has_permission("catalog.prices") or current_user.has_permission("system.admin")
        if price_list_id is not None and not has_prices_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permiso insuficiente: Se requiere la capacidad 'catalog.prices' para especificar listas de precios"
            )
        
        if price_list_id is None:
            default_list = db.query(PriceList).filter(PriceList.is_active == True).order_by(PriceList.price_list_id.asc()).first()
            price_list_id = default_list.price_list_id if default_list else 1

        show_confidential_columns = has_prices_perm

    elif isinstance(current_user, Customer):
        customer_info = db.query(CustomerInfo).filter(
            CustomerInfo.customer_id == current_user.customer_id
        ).first()
        if not customer_info or not customer_info.price_list_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tienes lista de precios asignada"
            )
        price_list_id = customer_info.price_list_id
        show_confidential_columns = False
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para exportar catálogos"
        )

    results = crud_catalog.get_all_catalog_products_for_export(db, price_list_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Catalogo"

    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    if show_confidential_columns:
        headers = ["ID", "Código Barras", "Nombre", "Descripción", "Precio Base", "Markup %", "IVA %", "IVA $", "Precio Final", "Stock"]
    else:
        headers = ["ID", "Código Barras", "Nombre", "Piezas por caja", "Precio Final", "Stock", "Pedido"]

    ws.append(headers)
    for col_idx, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    for product, price_item in results:
        final_price = calculate_catalog_price(product, price_item)
        if show_confidential_columns:
            iva_pct = Decimal(str(product.iva_percentage or 0))
            iva_multiplier = Decimal('1') + (iva_pct / Decimal('100'))
            price_without_iva = (Decimal(str(final_price)) / iva_multiplier).quantize(Decimal('0.01'))
            iva_amount = float(Decimal(str(final_price)) - price_without_iva)
            ws.append([
                product.product_id,
                product.codebar or "",
                product.name,
                product.description or "",
                float(product.base_price or 0),
                float(price_item.markup_percentage or 0),
                float(product.iva_percentage or 0),
                round(iva_amount, 2),
                float(final_price),
                product.stock_count
            ])
        else:
            desc = (product.description or "").strip()
            match = re.search(r'(?:CAJA?|PZ)\s*(\d+)', desc, re.IGNORECASE)
            if not match:
                match = re.search(r'Caja:\s*(\d+)', desc, re.IGNORECASE)
            if not match:
                match = re.search(r'^\s*(\d+)\s*$', desc)
            compra_estandar = match.group(1) if match else "N/A"
            ws.append([
                product.product_id,
                product.codebar or "",
                product.name,
                compra_estandar,
                float(final_price),
                product.stock_count,
                ""
            ])

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val = str(cell.value) if cell.value is not None else ""
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 3, 50)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    label = f"lista_{price_list_id}" if show_confidential_columns else "catalogo"
    filename = f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


""" GET /products/{id} - Detalle de producto con precio calculado """
@router.get("/products/{product_id}")
def get_catalog_product(
    product_id: str,
    current_user = Depends(check_catalog_access),
    db: Session = Depends(get_db)
):
    # Obtiene un producto especifico del catalogo
    return crud_catalog.get_catalog_product(db=db, current_user=current_user, product_id=product_id)


""" GET /customer/{customer_id}/products - Lista de productos con precios del cliente (Comercial) """
@router.get("/customer/{customer_id}/products")
def get_customer_catalog_products(
    customer_id: int,
    skip: int = Query(0, ge=0, description="Registros a saltar (paginacion)"),
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"),
    search: Optional[str] = Query(None, description="Buscar por ID, nombre, descripcion o codebar"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoria"),
    sort_by: Optional[str] = Query(None, description="Ordenar por: name, price, discount, created_at, newest, priority, relevance"),
    sort_order: Optional[str] = Query("asc", description="Orden: asc o desc"),
    current_user: User = Depends(require_permission("catalog.customer_view")),
    db: Session = Depends(get_db)
):
    # Verificar alcance de grupo comercial: usuarios con system.admin pueden ver cualquier cliente; otros según asignación
    if not current_user.has_permission("system.admin"):
        if not user_can_manage_order(db, current_user.user_id, customer_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver el catalogo de este cliente"
            )
    
    return crud_catalog.get_customer_catalog_products(
        db=db, customer_id=customer_id, skip=skip, limit=limit, search=search, category_id=category_id,
        sort_by=sort_by, sort_order=sort_order
    )


""" GET /customer/{customer_id}/products/{product_id}/similar - Productos similares con precios del cliente """
@router.get("/customer/{customer_id}/products/{product_id}/similar")
def get_product_similar_for_customer(
    customer_id: int,
    product_id: str,
    limit: int = Query(8, ge=1, le=20, description="Numero de productos similares"),
    current_user: User = Depends(require_permission("catalog.customer_view")),
    db: Session = Depends(get_db)
):
    """Obtiene productos similares usando get_similar_products con price_list del cliente"""

    # Verificar alcance de grupo comercial
    if not current_user.has_permission("system.admin"):
        if not user_can_manage_order(db, current_user.user_id, customer_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver productos de este cliente"
            )
    
    # Obtener price_list_id del cliente
    customer_info = db.query(CustomerInfo).filter(
        CustomerInfo.customer_id == customer_id
    ).first()
    
    if not customer_info or not customer_info.price_list_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente no tiene lista de precios asignada"
        )
    
    # Llamar a get_similar_products con price_list_id del cliente
    results = get_similar_products(
        db=db,
        product_id=product_id,
        price_list_id=customer_info.price_list_id,
        limit=limit
    )
    
    # Retornar productos con su similarity_score inyectado
    response = []
    for item in results:
        product_dict = item["product"]
        # Inyectar el score. Asegurarse de que el objeto sea mutable (dict)
        if hasattr(product_dict, "dict"):
            product_dict = product_dict.dict()
        
        product_dict["similarity_score"] = item["similarity_score"]
        response.append(product_dict)
    
    return response


""" GET /public/price-lists - Obtener listas de precios publicas para el storefront """
@router.get("/public/price-lists")
def get_public_storefront_price_lists(db: Session = Depends(get_db)):
    """
    Retorna la lista de PriceLists activas marcadas como publicas para el storefront general
    (is_public_storefront == True), sin requerir autenticacion.
    """
    lists = crud_catalog.get_public_storefront_price_lists(db=db)
    return [
        {
            "price_list_id": pl.price_list_id,
            "list_name": pl.list_name,
            "description": pl.description
        }
        for pl in lists
    ]


""" GET /public/products - Obtener productos paginados de una lista de precios publica storefront """
@router.get("/public/products")
def get_public_storefront_products(
    price_list_id: Optional[int] = Query(None, description="ID de la lista de precios publica"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(12, ge=1, le=100, description="Limite de registros"),
    search: Optional[str] = Query(None, description="Buscar por nombre, descripcion o codigo de barras"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoria"),
    sort_by: Optional[str] = Query(None, description="Ordenar por: name, price, discount, created_at, newest, priority, relevance"),
    sort_order: Optional[str] = Query("asc", description="Orden: asc o desc"),
    has_discount: Optional[bool] = Query(None, description="Filtrar solo con descuento"),
    db: Session = Depends(get_db)
):
    """
    Consulta productos y precios de una lista publica sin requerir autenticacion.
    Valida que la lista de precios exista, este activa y tenga is_public_storefront == True.
    """
    return crud_catalog.get_public_storefront_products(
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


@router.get("/public/products/{product_id}")
def get_public_storefront_product_detail(
    product_id: str,
    price_list_id: Optional[int] = Query(None, description="ID de lista publica opcional"),
    db: Session = Depends(get_db)
):
    """
    Retorna el detalle público de un producto activo si pertenece a una lista pública
    activa (`is_public_storefront == True`). Ideal para SEO, Google Rich Results y enlaces compartibles.
    """
    product = crud_catalog.get_public_storefront_product_detail(
        db=db,
        product_id=product_id,
        price_list_id=price_list_id,
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no disponible en el catálogo público"
        )
    return product


def _resolve_frontend_base_url(default_domain: str = "https://profarmed.com.mx") -> str:
    """Resuelve la URL pública canónica del frontend para emitir URLs en el sitemap."""
    raw = (getattr(config, "FRONTEND_URL", None) or "").strip()
    if raw and raw != "*":
        candidates = [c.strip().rstrip("/") for c in raw.split(",") if c.strip()]
        for url in candidates:
            if url.startswith("https://") and "localhost" not in url:
                return url
        for url in candidates:
            if url.startswith("http") and "localhost" not in url:
                return url
    return default_domain.rstrip("/")


def build_public_sitemap_xml(db: Session, default_domain: str = "https://profarmed.com.mx") -> str:
    """
    Genera dinámicamente el XML Sitemap de páginas institucionales y, si existe al menos una
    PriceList activa marcada con is_public_storefront == True, incluye /catalogo y todos
    los productos públicos con su imagen para indexación automática en Google.
    """
    base_url = _resolve_frontend_base_url(default_domain)
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    static_pages = [
        {"path": "/", "changefreq": "daily", "priority": "1.0"},
        {"path": "/quiero-ser-cliente", "changefreq": "monthly", "priority": "0.8"},
        {"path": "/about", "changefreq": "monthly", "priority": "0.8"},
        {"path": "/contact", "changefreq": "monthly", "priority": "0.8"},
        {"path": "/terms", "changefreq": "yearly", "priority": "0.5"},
        {"path": "/privacy", "changefreq": "yearly", "priority": "0.5"},
    ]

    sitemap_data = crud_catalog.get_public_storefront_sitemap_items(db=db)
    has_storefront = sitemap_data.get("has_public_storefront", False)
    products = sitemap_data.get("products", [])

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]

    for page in static_pages:
        loc = escape(f"{base_url}{page['path']}")
        lines.extend([
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{today_iso}</lastmod>",
            f"    <changefreq>{page['changefreq']}</changefreq>",
            f"    <priority>{page['priority']}</priority>",
            "  </url>",
        ])

    if has_storefront:
        catalog_loc = escape(f"{base_url}/catalogo")
        lines.extend([
            "  <url>",
            f"    <loc>{catalog_loc}</loc>",
            f"    <lastmod>{today_iso}</lastmod>",
            "    <changefreq>daily</changefreq>",
            "    <priority>0.9</priority>",
            "  </url>",
        ])

        for item in products:
            encoded_id = quote(str(item["product_id"]), safe="")
            product_loc = escape(f"{base_url}/catalogo/producto/{encoded_id}")
            updated_at = item.get("updated_at")
            lastmod_str = (
                updated_at.strftime("%Y-%m-%d")
                if hasattr(updated_at, "strftime")
                else today_iso
            )

            lines.extend([
                "  <url>",
                f"    <loc>{product_loc}</loc>",
                f"    <lastmod>{lastmod_str}</lastmod>",
                "    <changefreq>daily</changefreq>",
                "    <priority>0.8</priority>",
            ])

            raw_img = (item.get("image_url") or "").strip()
            if raw_img.startswith("http"):
                sep = "&" if "?" in raw_img else "?"
                img_loc = escape(f"{raw_img}{sep}v={item.get('image_version', 1)}")
                img_title = escape(str(item.get("name") or item["product_id"]))
                lines.extend([
                    "    <image:image>",
                    f"      <image:loc>{img_loc}</image:loc>",
                    f"      <image:title>{img_title}</image:title>",
                    "    </image:image>",
                ])

            lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


@router.get("/public/sitemap.xml")
def get_public_storefront_sitemap(db: Session = Depends(get_db)):
    """Sitemap XML dinámico del storefront público (incluye productos si is_public_storefront está activo)."""
    xml_content = build_public_sitemap_xml(db=db)
    return Response(
        content=xml_content,
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


