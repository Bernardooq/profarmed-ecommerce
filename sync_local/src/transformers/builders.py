"""
Builders - Transformación de filas DBF a diccionarios JSON para la API (Profarmed).
"""

from .data_cleaning import (
    clean_text,
    clean_number,
    build_phone,
    build_username,
)

DEFAULT_EMAIL_DOMAIN = "profarmed.com.mx"
DEFAULT_SELLER_PASSWORD = "vendedor2026"
DEFAULT_CUSTOMER_PASSWORD = "profarmed2026"


def build_product_dict(row, descriptions_map, stock_map, verify_image_fn, sync_time):
    """Construye diccionario de producto desde una fila de producto.dbf."""
    product_id = clean_text(row.get("CVE_PROD"))

    desc_parts = []
    if row.get("FACT_PESO"):
        desc_parts.append(f"Costo Público: {clean_text(row.get('FACT_PESO'))}")
    if row.get("DATO_4"):
        desc_parts.append(f"Caja: {clean_text(row.get('DATO_4'))}")
    technical_desc = " | ".join(desc_parts) or None

    raw_name = clean_text(row.get("DESC_PROD"))
    product_name = (raw_name[:255] if raw_name else None) or "Sin Nombre"

    return {
        "product_id": product_id,
        "codebar": clean_text(row.get("CODBAR")) or None,
        "name": product_name,
        "description": technical_desc,
        "descripcion_2": descriptions_map.get(product_id),
        "stock_count": int(stock_map.get(product_id, 0)),
        "base_price": clean_number(row.get("CTO_ENT")),
        "iva_percentage": clean_number(row.get("PORCENIVA"), 16.0),
        "category_name": clean_text(row.get("CSE_PROD")) or None,
        "is_active": True,
        "unidad_medida": clean_text(row.get("UNI_MED")) or None,
        "image_url": verify_image_fn(product_id),
        "updated_at": sync_time,
    }


def build_category_dict(name, sync_time):
    """Construye diccionario de categoría."""
    return {
        "name": name,
        "description": None,
        "updated_at": sync_time,
    }


def build_seller_dict(row, sync_time=None):
    """Construye diccionario de vendedor desde una fila de agentes.dbf."""
    first_name = row["NOM_AGE"].split()[0].lower()

    seller = {
        "user_id": int(row["CVE_AGE"]),
        "username": f"{first_name}_S{row['CVE_AGE']}",
        "email": row.get("EMAIL_AGE") or f"seller{row['CVE_AGE']}@{DEFAULT_EMAIL_DOMAIN}",
        "full_name": str(row.get("NOM_AGE", "")).strip(),
        "password": DEFAULT_SELLER_PASSWORD,
        "is_active": True,
    }

    if sync_time:
        seller["updated_at"] = sync_time

    return seller


def build_customer_dict(row, sync_time=None):
    """Construye diccionario de cliente desde una fila de clientes.dbf."""
    customer_id = int(row["CVE_CTE"])

    address = (
        f"{row.get('DIR_CTE', '')} "
        f"{row.get('NE_CTE', '')}, "
        f"{row.get('COL_CTE', '')}, "
        f"{row.get('CP_CTE', '')}, "
        f"{row.get('CD_CTE', '')}, "
        f"{row.get('EDO_CTE', '')}."
    ).strip() or None

    customer = {
        "customer_id": customer_id,
        "username": build_username(row.get("NOM_CTE", "CLIENTE"), customer_id),
        "email": row.get("EMAIL_CTE") or f"client{customer_id}@{DEFAULT_EMAIL_DOMAIN}",
        "full_name": str(row.get("NOM_CTE", "")).strip(),
        "password": DEFAULT_CUSTOMER_PASSWORD,
        "agent_id": str(row["CVE_AGE"]) if row.get("CVE_AGE") else None,
        "business_name": str(row.get("NOM_FAC", row.get("NOM_CTE", ""))).strip(),
        "rfc": str(row.get("RFC_CTE", ""))[:13] or None,
        "price_list_id": int(float(row["LISTA_PREC"])) if row.get("LISTA_PREC") else None,
        "address_1": address,
        "telefono_1": build_phone(row.get("LADA_CTE"), row.get("TEL1_CTE")),
        "telefono_2": build_phone(row.get("LADA_CTE"), row.get("TEL2_CTE")),
    }

    if sync_time:
        customer["updated_at"] = sync_time

    return customer


def build_pricelist_dict(pricelist_id, sync_time):
    """Construye diccionario de lista de precios."""
    return {
        "price_list_id": int(pricelist_id),
        "list_name": f"Lista {int(pricelist_id)}",
        "description": None,
        "is_active": True,
        "updated_at": sync_time,
    }


def build_pricelist_item_dict(row, sync_time):
    """Construye diccionario de item de lista de precios."""
    return {
        "price_list_id": int(clean_text(row.get("NLISPRE"))),
        "product_id": clean_text(row.get("CVE_PROD")),
        "markup_percentage": clean_number(row.get("LMARGEN")),
        "final_price": clean_number(row.get("LPRECPROD")),
        "updated_at": sync_time,
    }


# Alias retrocompatibles
build_producto_dict = build_product_dict
build_categoria_dict = build_category_dict
build_vendedor_dict = build_seller_dict
build_cliente_dict = build_customer_dict
build_lista_precios_dict = build_pricelist_dict
build_item_lista_dict = build_pricelist_item_dict
