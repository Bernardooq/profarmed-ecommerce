"""
Utilidades centralizadas para cálculo de precios y descuentos.

Flujo estándar de precios:
1. base_price × (1 + markup%) = precio sin IVA (price_without_iva)
2. price_without_iva × (1 + iva%) = precio final con IVA (final_price)

Flujo con Descuentos (Reglas de Negocio):
- Prioridad 1: Descuento por Lista de Precios (específico para product_id y price_list_id).
  Fórmula: (base + markup) - descuento%, luego aplicar IVA.
- Prioridad 2: Descuento General (específico para product_id con price_list_id IS NULL).
  Fórmula: base - descuento%, luego aplicar markup%, luego aplicar IVA.
- Si no hay descuento: Flujo estándar sin modificaciones.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import time
from sqlalchemy.orm import Session
from db.base import Product, PriceListItem, ProductDiscount


# Tolerancia para considerar precios "similares" (1%)
PRICE_TOLERANCE_PERCENTAGE = Decimal('0.01')

# Caché en memoria de la configuración pricing.tax_inclusive para O(1) en catálogos masivos
_TAX_INCLUSIVE_CACHE = {"value": None, "timestamp": 0.0}
_CACHE_TTL_SECONDS = 30.0


def clear_tax_inclusive_cache():
    """Invalida la caché en memoria de la configuración pricing.tax_inclusive."""
    _TAX_INCLUSIVE_CACHE["value"] = None
    _TAX_INCLUSIVE_CACHE["timestamp"] = 0.0


def is_tax_inclusive(db: Optional[Session] = None) -> bool:
    """
    Verifica si el sistema tiene activa la configuración 'pricing.tax_inclusive'.
    Si está activa, los precios de listas del ERP ya vienen con IVA incluido (modelo neto mostrador/farmacia).
    Utiliza caché en memoria con TTL de 30s para evitar sobrecarga en listados grandes.
    """
    now = time.time()
    if _TAX_INCLUSIVE_CACHE["value"] is not None and (now - _TAX_INCLUSIVE_CACHE["timestamp"]) < _CACHE_TTL_SECONDS:
        return _TAX_INCLUSIVE_CACHE["value"]

    if db is not None:
        try:
            from db.base import SystemConfig
            cfg = db.query(SystemConfig).filter(SystemConfig.config_name == "pricing.tax_inclusive").first()
            val = bool(cfg.is_active) if cfg else False
            _TAX_INCLUSIVE_CACHE["value"] = val
            _TAX_INCLUSIVE_CACHE["timestamp"] = now
            return val
        except Exception:
            pass

    if _TAX_INCLUSIVE_CACHE["value"] is not None:
        return _TAX_INCLUSIVE_CACHE["value"]

    try:
        from db.session import SessionLocal
        from db.base import SystemConfig
        with SessionLocal() as session:
            cfg = session.query(SystemConfig).filter(SystemConfig.config_name == "pricing.tax_inclusive").first()
            val = bool(cfg.is_active) if cfg else False
            _TAX_INCLUSIVE_CACHE["value"] = val
            _TAX_INCLUSIVE_CACHE["timestamp"] = now
            return val
    except Exception:
        return False


def calculate_final_price_with_markup(
    base_price: Decimal,
    markup_percentage: Decimal,
    stored_final_price: Optional[Decimal] = None
) -> Decimal:
    """
    Calcula el precio CON MARKUP pero SIN IVA.
    Este es el precio que se guarda en price_without_iva de orderitems.
    
    Args:
        base_price: Precio base del producto (sin IVA, sin markup)
        markup_percentage: Porcentaje de markup a aplicar
        stored_final_price: Precio final almacenado en BD de pricelistitems (opcional)
    
    Returns:
        Precio con markup, SIN IVA, redondeado a 2 decimales
    """
    base_price = Decimal(str(base_price))
    markup_percentage = Decimal(str(markup_percentage))
    
    # Calcular precio con markup
    markup_multiplier = Decimal('1') + (markup_percentage / Decimal('100'))
    calculated_price = base_price * markup_multiplier
    
    # Redondear a 2 decimales
    two_places = Decimal('0.01')
    calculated_price = calculated_price.quantize(two_places, rounding=ROUND_HALF_UP)
    
    if stored_final_price is None:
        return calculated_price
    
    stored_final_price = Decimal(str(stored_final_price))
    return max(calculated_price, stored_final_price)


def apply_iva(price: Decimal, iva_percentage: Decimal) -> Decimal:
    """
    Aplica IVA a un precio.
    
    Args:
        price: Precio sin IVA (ya con markup)
        iva_percentage: Porcentaje de IVA (ej: 16.0)
    
    Returns:
        Precio con IVA, redondeado a 2 decimales
    """
    price = Decimal(str(price))
    iva_percentage = Decimal(str(iva_percentage))
    
    iva_multiplier = Decimal('1') + (iva_percentage / Decimal('100'))
    price_with_iva = price * iva_multiplier
    
    two_places = Decimal('0.01')
    return price_with_iva.quantize(two_places, rounding=ROUND_HALF_UP)


def calculate_product_price_breakdown(
    product: Product,
    price_item: PriceListItem,
    db: Optional[Session] = None,
    active_discount: Optional[ProductDiscount] = None
) -> Dict[str, Any]:
    """
    Motor centralizado de cálculo de precios y resolución de descuentos.
    
    Aplica la regla de prioridad:
    1. Descuento por Lista de Precios (price_list):
       Aplica sobre (base + markup) antes de IVA.
    2. Descuento General (general):
       Aplica sobre base_price antes de markup e IVA.
    3. Ninguno:
       Precios estándar.
    """
    two_places = Decimal('0.01')
    base_price = Decimal(str(product.base_price or 0))
    markup_percentage = Decimal(str(price_item.markup_percentage or 0))
    stored_final_price = Decimal(str(price_item.final_price)) if price_item.final_price else None
    iva_percentage = Decimal(str(product.iva_percentage or 0))
    
    tax_inclusive = is_tax_inclusive(db)
    
    # 1. Cálculo base original sin descuentos
    if tax_inclusive:
        # Modo con IVA incluido (ej. Farmacias / Grupo DMI):
        # stored_final_price ya contiene el precio final neto al consumidor con IVA incluido.
        if stored_final_price is not None:
            markup_multiplier = Decimal('1') + (markup_percentage / Decimal('100'))
            calc_from_base = (base_price * markup_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)
            original_final_price = max(calc_from_base, stored_final_price).quantize(two_places, rounding=ROUND_HALF_UP)
        else:
            markup_multiplier = Decimal('1') + (markup_percentage / Decimal('100'))
            original_final_price = (base_price * markup_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)

        if iva_percentage > Decimal('0'):
            iva_multiplier = Decimal('1') + (iva_percentage / Decimal('100'))
            original_price_without_iva = (original_final_price / iva_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)
        else:
            original_price_without_iva = original_final_price
    else:
        # Modo estándar (tax-exclusive): precios base y de lista son subtotal; se suma IVA encima
        original_price_without_iva = calculate_final_price_with_markup(
            base_price=base_price,
            markup_percentage=markup_percentage,
            stored_final_price=stored_final_price
        )
        original_final_price = apply_iva(original_price_without_iva, iva_percentage)
    
    # 2. Resolución de descuento activo si no se pasó explícitamente
    if active_discount is None:
        if db is not None:
            from crud.crud_discount import get_active_discount_for_product
            active_discount = get_active_discount_for_product(
                db=db,
                product_id=product.product_id,
                price_list_id=price_item.price_list_id
            )
        elif hasattr(product, 'discounts') and product.discounts:
            now = datetime.now(timezone.utc)
            # Prioridad 1: Por lista de precios
            pl_discounts = [
                d for d in product.discounts
                if d.is_active and d.price_list_id == price_item.price_list_id
                and (d.start_date is None or (d.start_date.tzinfo and d.start_date <= now or not d.start_date.tzinfo and d.start_date <= datetime.utcnow()))
                and (d.end_date is None or (d.end_date.tzinfo and d.end_date >= now or not d.end_date.tzinfo and d.end_date >= datetime.utcnow()))
            ]
            if pl_discounts:
                active_discount = pl_discounts[0]
            else:
                # Prioridad 2: General
                gen_discounts = [
                    d for d in product.discounts
                    if d.is_active and d.price_list_id is None
                    and (d.start_date is None or (d.start_date.tzinfo and d.start_date <= now or not d.start_date.tzinfo and d.start_date <= datetime.utcnow()))
                    and (d.end_date is None or (d.end_date.tzinfo and d.end_date >= now or not d.end_date.tzinfo and d.end_date >= datetime.utcnow()))
                ]
                if gen_discounts:
                    active_discount = gen_discounts[0]

    # 3. Normalizar y verificar si hay descuento activo
    has_disc = False
    disc_type = None
    disc_pct = Decimal('0.00')
    disc_id = None
    
    if active_discount is not None:
        if hasattr(active_discount, "has_discount"):
            # Es un objeto ActiveDiscountInfo
            if active_discount.has_discount:
                has_disc = True
                disc_type = active_discount.discount_type
                disc_pct = Decimal(str(active_discount.discount_percentage))
                disc_id = active_discount.discount_id
        else:
            # Es un objeto ProductDiscount (ORM)
            has_disc = True
            disc_type = "price_list" if getattr(active_discount, "price_list_id", None) is not None else "general"
            disc_pct = Decimal(str(active_discount.discount_percentage))
            disc_id = getattr(active_discount, "discount_id", None)

    # 4. Aplicar descuento según corresponda
    if has_disc:
        if tax_inclusive:
            if disc_type == "price_list":
                disc_multiplier = Decimal('1') - (disc_pct / Decimal('100'))
                final_price = (original_final_price * disc_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)
            else:
                disc_multiplier = Decimal('1') - (disc_pct / Decimal('100'))
                discounted_base = (base_price * disc_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)
                markup_multiplier = Decimal('1') + (markup_percentage / Decimal('100'))
                final_price = (discounted_base * markup_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)

            if iva_percentage > Decimal('0'):
                iva_multiplier = Decimal('1') + (iva_percentage / Decimal('100'))
                price_without_iva = (final_price / iva_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)
            else:
                price_without_iva = final_price
        else:
            if disc_type == "price_list":
                # Descuento en lista de precio: (base + markup) - descuento%
                disc_multiplier = Decimal('1') - (disc_pct / Decimal('100'))
                price_without_iva = (original_price_without_iva * disc_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)
                final_price = apply_iva(price_without_iva, iva_percentage)
            else:
                # Descuento general: base - descuento%, luego aplicar markup
                disc_multiplier = Decimal('1') - (disc_pct / Decimal('100'))
                discounted_base = (base_price * disc_multiplier).quantize(two_places, rounding=ROUND_HALF_UP)
                price_without_iva = calculate_final_price_with_markup(
                    base_price=discounted_base,
                    markup_percentage=markup_percentage,
                    stored_final_price=None
                )
                final_price = apply_iva(price_without_iva, iva_percentage)
        
        has_discount = True
        discount_applied = disc_pct
        discount_type = disc_type
        savings = max(Decimal('0.00'), (original_final_price - final_price).quantize(two_places, rounding=ROUND_HALF_UP))
    else:
        price_without_iva = original_price_without_iva
        final_price = original_final_price
        has_discount = False
        discount_applied = Decimal('0.00')
        discount_type = None
        savings = Decimal('0.00')
        
    return {
        "base_price": base_price,
        "markup_percentage": markup_percentage,
        "iva_percentage": iva_percentage,
        "price_without_iva": price_without_iva,
        "final_price": final_price,
        "final_price_with_iva": final_price,
        "has_discount": has_discount,
        "discount_applied": discount_applied,
        "discount_type": discount_type,
        "original_price_without_iva": original_price_without_iva,
        "original_final_price": original_final_price,
        "savings": savings,
        "active_discount_id": disc_id
    }


def get_product_final_price(
    db: Session,
    product: Product,
    price_list_id: int
) -> Optional[dict]:
    """
    Obtiene la información detallada de precio (con y sin IVA, y descuentos si aplican)
    de un producto para una lista de precios.
    """
    price_item = db.query(PriceListItem).filter(
        PriceListItem.price_list_id == price_list_id,
        PriceListItem.product_id == product.product_id
    ).first()
    
    if not price_item:
        return None
    
    breakdown = calculate_product_price_breakdown(
        product=product,
        price_item=price_item,
        db=db
    )
    
    return {
        "base_price": breakdown["base_price"],
        "markup_percentage": breakdown["markup_percentage"],
        "final_price": breakdown["final_price_with_iva"] if is_tax_inclusive(db) else breakdown["price_without_iva"],  # En tax_inclusive el precio final es el neto con IVA
        "price_without_iva": breakdown["price_without_iva"],
        "final_price_with_iva": breakdown["final_price_with_iva"],
        "has_discount": breakdown["has_discount"],
        "discount_applied": breakdown["discount_applied"],
        "discount_type": breakdown["discount_type"],
        "original_price_without_iva": breakdown["original_price_without_iva"],
        "original_final_price": breakdown["original_final_price"],
        "savings": breakdown["savings"]
    }


def format_price_info(
    base_price: Decimal,
    markup_percentage: Decimal,
    final_price: Decimal
) -> dict:
    """Formatea información de precio para respuestas API."""
    base_price = Decimal(str(base_price))
    markup_percentage = Decimal(str(markup_percentage))
    final_price = Decimal(str(final_price))
    
    markup_amount = final_price - base_price
    
    return {
        "base_price": round(float(base_price), 2),
        "markup_percentage": round(float(markup_percentage), 2),
        "markup_amount": round(float(markup_amount), 2),
        "final_price": round(float(final_price), 2)
    }


def calculate_catalog_price(
    product: Product,
    price_item: PriceListItem,
    db: Optional[Session] = None
) -> Decimal:
    """
    Calcula el precio final (CON IVA y CON DESCUENTOS si aplican) para el catálogo.
    """
    breakdown = calculate_product_price_breakdown(
        product=product,
        price_item=price_item,
        db=db
    )
    return breakdown["final_price"]


def build_catalog_product_dict(
    product: Product,
    final_price: Decimal,
    discount_info: Optional[dict] = None
) -> dict:
    """
    Construye el diccionario de producto para el catálogo ocultando datos sensibles
    (base_price y markup_percentage) e incluyendo información del descuento si aplica.
    """
    has_disc = bool(discount_info.get("has_discount", False)) if discount_info else False
    disc_applied = float(discount_info.get("discount_applied", 0)) if (discount_info and has_disc) else 0.0
    disc_type = discount_info.get("discount_type") if (discount_info and has_disc) else None
    orig_price = float(discount_info.get("original_final_price")) if (discount_info and has_disc and discount_info.get("original_final_price") is not None) else None
    savings = float(discount_info.get("savings", 0)) if (discount_info and has_disc) else 0.0
    
    return {
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
        'lock': bool(getattr(product, 'lock', False)),
        'display_priority': getattr(product, 'display_priority', 1000000),
        'category_id': product.category_id,
        'category': {
            'category_id': product.category.category_id,
            'name': product.category.name
        } if product.category else None,
        'final_price': float(final_price),
        'has_discount': has_disc,
        'discount_applied': disc_applied,
        'discount_type': disc_type,
        'original_price': orig_price,
        'savings': savings,
        'image_version': product.image_version,
        'created_at': product.created_at.isoformat() if getattr(product, 'created_at', None) else None,
        'updated_at': product.updated_at.isoformat() if getattr(product, 'updated_at', None) else None,
    }


def get_catalog_product_info(db: Session, product: Product, price_list_id: int) -> Optional[dict]:
    """
    Obtiene la información completa del catálogo para un producto y lista de precios,
    incluyendo descuentos automáticos.
    """
    price_data = get_product_final_price(db, product, price_list_id)
    if not price_data:
        return None
    
    return build_catalog_product_dict(
        product=product,
        final_price=price_data["final_price_with_iva"],
        discount_info=price_data
    )
