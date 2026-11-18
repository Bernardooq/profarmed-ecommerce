"""
Builders - Funciones para construir las estructuras de datos JSON que espera la API de Profarmed.
Soporta tanto filas de pandas (Series) como diccionarios SQL.
"""

import re
from .data_cleaning import (
    limpiar_texto, limpiar_numero, safe_int, construir_telefono, crear_username
)


def _get_val(row, key, default=None):
    """Obtiene un valor de una fila (dict o pandas Series) sin fallar por mayúsculas/minúsculas."""
    if hasattr(row, 'get'):
        val = row.get(key)
        if val is None and hasattr(key, 'lower'):
            val = row.get(key.lower()) or row.get(key.upper())
        return val if val is not None else default
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, IndexError):
        try:
            return row[key.lower()]
        except (KeyError, IndexError):
            try:
                return row[key.upper()]
            except (KeyError, IndexError):
                return default


# ============================================================================
# PRODUCTO
# ============================================================================

def build_producto_dict(row, descripciones_map, stock_map, verificar_imagen_fn, sync_time):
    """
    Construye diccionario de producto para la API.
    
    Args:
        row: Fila (dict o Series) con datos de producto
        descripciones_map: Dict {producto_id: descripcion_larga}
        stock_map: Dict {producto_id: stock_int}
        verificar_imagen_fn: Función para resolver URL de imagen CDN
        sync_time: Timestamp ISO de sincronización
    """
    producto_id = limpiar_texto(_get_val(row, 'CVE_PROD') or _get_val(row, 'product_id') or _get_val(row, 'cve_prod'))
    codebar = limpiar_texto(_get_val(row, 'CODBAR') or _get_val(row, 'codebar')) or None
    
    desc_tecnica_parts = []
    linea_val = limpiar_texto(_get_val(row, 'LINEA_NAME'))
    if linea_val:
        desc_tecnica_parts.append(f"Laboratorio: {linea_val}")
    
    dato_4 = _get_val(row, 'DATO_4') or _get_val(row, 'CORRUGADO')
    if dato_4 and float(limpiar_numero(dato_4)) > 0:
        desc_tecnica_parts.append(f"Caja: {int(float(dato_4))}")
        
    desc_tecnica = " | ".join(desc_tecnica_parts) or None
    
    name_val = limpiar_texto(_get_val(row, 'DESC_PROD') or _get_val(row, 'name') or _get_val(row, 'DESCRI'))[:255] or "Sin Nombre"
    desc_2_val = descripciones_map.get(producto_id) if (descripciones_map and producto_id in descripciones_map) else name_val

    image_url = None
    if verificar_imagen_fn:
        try:
            image_url = verificar_imagen_fn(codebar, fallback_id=producto_id)
        except TypeError:
            image_url = verificar_imagen_fn(codebar or producto_id)

    return {
        "product_id": producto_id,
        "codebar": codebar,
        "name": name_val,
        "description": desc_tecnica,
        "descripcion_2": desc_2_val,
        "stock_count": safe_int(stock_map.get(producto_id, 0), default=0) if stock_map else 0,
        "base_price": limpiar_numero(_get_val(row, 'CTO_ENT') or _get_val(row, 'base_price') or _get_val(row, 'cto_ent')),
        "iva_percentage": limpiar_numero(_get_val(row, 'PORCENIVA') or _get_val(row, 'iva_percentage') or _get_val(row, 'porceniva'), 16.0),
        "category_name": limpiar_texto(_get_val(row, 'CSE_PROD') or _get_val(row, 'category_name')) or "MED",
        "is_active": True,
        "unidad_medida": limpiar_texto(_get_val(row, 'UNI_MED') or _get_val(row, 'unidad_medida') or _get_val(row, 'uni_med')) or "PZA",
        "image_url": image_url,
        "updated_at": sync_time
    }


# ============================================================================
# CATEGORÍA
# ============================================================================

def build_categoria_dict(nombre, sync_time):
    """Construye diccionario de categoría."""
    return {
        "name": nombre,
        "description": None,
        "updated_at": sync_time
    }


# ============================================================================
# VENDEDOR (SELLER / AGENT)
# ============================================================================

def build_vendedor_dict(row, sync_time=None):
    """
    Construye diccionario de vendedor/empleado para la API de Profarmed.
    Extraído desde dbo.empleado en SQL Server 2000.
    """
    cve_raw = (
        _get_val(row, 'NUMERO') or 
        _get_val(row, 'CVE_AGE') or 
        _get_val(row, 'user_id') or 
        _get_val(row, 'numero')
    )
    cve_id = safe_int(cve_raw)
    if cve_id is None:
        return None
        
    nom_emp = str(
        _get_val(row, 'NOMBRE') or 
        _get_val(row, 'NOM_AGE') or 
        _get_val(row, 'full_name') or ''
    ).strip()
    
    user_code = limpiar_texto(_get_val(row, 'USER') or _get_val(row, 'user'))
    if user_code and len(user_code) >= 3:
        clean_user = re.sub(r'[^a-zA-Z0-9_]', '', user_code).lower()
        username = f"{clean_user}_{cve_id}"
    else:
        primer_nombre = nom_emp.split()[0].lower() if nom_emp else "vendedor"
        clean_user = re.sub(r'[^a-zA-Z0-9_]', '', primer_nombre)
        username = f"{clean_user}_{cve_id}"
        
    email_emp = (
        limpiar_texto(_get_val(row, 'EMAIL')) or 
        limpiar_texto(_get_val(row, 'EMAIL_AGE'))
    )
    if not email_emp or '@' not in email_emp:
        email_emp = f"vendedor_{cve_id}@profarmed.com.mx"
        
    vendedor = {
        "user_id": cve_id,
        "username": username,
        "email": email_emp,
        "full_name": nom_emp,
        "password": "profarmed2026",
        "is_active": True
    }
    
    if sync_time:
        vendedor["updated_at"] = sync_time
        
    return vendedor


# ============================================================================
# CLIENTE (CUSTOMER)
# ============================================================================

def build_cliente_dict(row, sync_time=None):
    """
    Construye diccionario de cliente para la API.
    Compatible con dbo.socios de SQL Server 2000 y formato heredado DBF.
    """
    cve_cte = (
        _get_val(row, 'NUMERO') or 
        _get_val(row, 'CVE_CTE') or 
        _get_val(row, 'customer_id') or 
        _get_val(row, 'numero') or 
        _get_val(row, 'cve_cte')
    )
    cid = safe_int(cve_cte)
    if cid is None:
        return None
    
    nom_cte = str(
        _get_val(row, 'NOMBRE') or 
        _get_val(row, 'NOM_CTE') or 
        _get_val(row, 'full_name') or 
        _get_val(row, 'nombre') or 
        _get_val(row, 'nom_cte') or ''
    ).strip()
    
    # Construcción limpia de dirección
    calle = _get_val(row, 'CALLE') or _get_val(row, 'DIR_CTE') or _get_val(row, 'calle') or ''
    numext = _get_val(row, 'NUMEXT') or _get_val(row, 'NE_CTE') or _get_val(row, 'numext') or ''
    numint = _get_val(row, 'NUMINT') or _get_val(row, 'numint') or ''
    colonia = _get_val(row, 'COLONIA') or _get_val(row, 'COL_CTE') or _get_val(row, 'colonia') or ''
    cp = _get_val(row, 'CP') or _get_val(row, 'CP_CTE') or _get_val(row, 'cp') or ''
    ciudad = _get_val(row, 'CIUDAD') or _get_val(row, 'CD_CTE') or _get_val(row, 'ciudad') or ''
    estado = _get_val(row, 'ESTADO') or _get_val(row, 'EDO_CTE') or _get_val(row, 'estado') or ''
    
    num_part = str(numext).strip()
    if numint and str(numint).strip():
        num_part = f"{num_part} Int. {str(numint).strip()}".strip()
        
    dir_line = f"{str(calle).strip()} {num_part}".strip()
    direccion_parts = [dir_line, str(colonia).strip(), str(cp).strip(), str(ciudad).strip(), str(estado).strip()]
    direccion = ", ".join([p for p in direccion_parts if p]).strip() or None
    
    # Agente / Vendedor asignado
    cve_age = _get_val(row, 'VENDEDOR') or _get_val(row, 'CVE_AGE') or _get_val(row, 'agent_id') or _get_val(row, 'vendedor')
    
    # Lista de precios (PRECIO o LISTA_PREC)
    lista_prec = _get_val(row, 'PRECIO') or _get_val(row, 'LISTA_PREC') or _get_val(row, 'price_list_id') or _get_val(row, 'precio')
    
    # Teléfono
    raw_tel = _get_val(row, 'TELEFONO') or _get_val(row, 'TEL1_CTE') or _get_val(row, 'telefono')
    tel_limpio = construir_telefono(_get_val(row, 'LADA_CTE'), raw_tel) if raw_tel else None
    
    # Email (con fallback robusto a cliente_{cid}@profarmed.com.mx)
    email_val = (
        limpiar_texto(_get_val(row, 'EMAIL')) or 
        limpiar_texto(_get_val(row, 'EMAIL2')) or 
        limpiar_texto(_get_val(row, 'EMAIL3')) or 
        limpiar_texto(_get_val(row, 'EMAIL_CTE')) or 
        limpiar_texto(_get_val(row, 'email'))
    )
    if not email_val or '@' not in email_val:
        email_val = f"cliente_{cid}@profarmed.com.mx"
    
    # RFC limpio a 13 chars
    rfc_raw = _get_val(row, 'RFC') or _get_val(row, 'RFC_CTE') or _get_val(row, 'rfc') or ''
    rfc_limpio = limpiar_texto(rfc_raw)
    if rfc_limpio:
        rfc_limpio = rfc_limpio[:13]
    
    aid = safe_int(cve_age)
    pl_id = safe_int(lista_prec)
    
    cliente = {
        "customer_id": cid,
        "username": crear_username(nom_cte or 'CLIENTE', cid),
        "email": email_val,
        "full_name": nom_cte,
        "password": "profarmed2026",
        "agent_id": str(aid) if aid is not None else None,
        "business_name": nom_cte,
        "rfc": rfc_limpio or None,
        "price_list_id": pl_id,
        "address_1": direccion,
        "telefono_1": tel_limpio,
        "telefono_2": None
    }
    
    if sync_time:
        cliente["updated_at"] = sync_time
        
    return cliente


# ============================================================================
# LISTAS DE PRECIOS
# ============================================================================

def build_lista_precios_dict(lista_id, sync_time):
    """Construye diccionario de cabecera de lista de precios."""
    return {
        "price_list_id": int(lista_id),
        "list_name": f"Lista {int(lista_id)}",
        "description": None,
        "is_active": True,
        "updated_at": sync_time
    }


def build_item_lista_dict(row, sync_time):
    """Construye diccionario de item (renglón) de lista de precios."""
    nlispre = _get_val(row, 'NLISPRE') or _get_val(row, 'price_list_id') or _get_val(row, 'nlispre')
    cve_prod = _get_val(row, 'CVE_PROD') or _get_val(row, 'product_id') or _get_val(row, 'cve_prod')
    lmargen = _get_val(row, 'LMARGEN') or _get_val(row, 'markup_percentage') or _get_val(row, 'lmargen')
    lprecprod = _get_val(row, 'LPRECPROD') or _get_val(row, 'final_price') or _get_val(row, 'lprecprod')
    
    return {
        "price_list_id": int(limpiar_texto(nlispre)),
        "product_id": limpiar_texto(cve_prod),
        "markup_percentage": limpiar_numero(lmargen),
        "final_price": limpiar_numero(lprecprod),
        "updated_at": sync_time
    }


# ============================================================================
# PEDIDOS -> dbo.cotiza3 (SQL SERVER 2000)
# ============================================================================

def _parse_order_datetime_mx(iso_str: str) -> str:
    """
    Convierte un timestamp ISO-8601 (UTC o con offset) a hora estándar de México (UTC-6)
    en formato compatible con SQL Server 2000 datetime ('YYYY-MM-DD HH:MM:SS').
    """
    from datetime import datetime, timezone, timedelta

    mx_tz = timezone(timedelta(hours=-6))
    if not iso_str:
        return datetime.now(mx_tz).strftime("%Y-%m-%d %H:%M:%S")
    try:
        cleaned = str(iso_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(mx_tz).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now(mx_tz).strftime("%Y-%m-%d %H:%M:%S")


def build_cotiza3_rows(order: dict) -> list:
    """
    Transforma un pedido completo del E-Commerce en renglones normalizados para dbo.cotiza3.
    Consolida por BARCODE dentro del mismo pedido para garantizar upsert idempotente 1:1.

    Nota de precios:
    `price_without_iva` ya viene neto con descuento aplicado desde el backend, por lo que
    `DESCUEN` se inserta en 0.00 y `NETO = round(CANTIDAD * PRECIO, 2)` evitando doble descuento.
    """
    order_id = safe_int(order.get("order_id"))
    if not order_id:
        raise ValueError("Pedido sin order_id válido")

    socio_id = safe_int(order.get("customer_id"))
    if not socio_id:
        raise ValueError(f"Pedido #{order_id} sin customer_id válido")

    vendedor_raw = safe_int(order.get("assigned_user_id"))
    vendedor_id = vendedor_raw if vendedor_raw and vendedor_raw > 0 else None
    fecha_sql = _parse_order_datetime_mx(order.get("created_at"))

    consolidated = {}
    for item in order.get("items") or []:
        barcode = limpiar_texto(item.get("product_id"))[:100]
        if not barcode:
            continue

        qty = round(float(limpiar_numero(item.get("quantity"), 0.0)), 2)
        if qty <= 0:
            continue

        product = item.get("product") or {}
        descri = (limpiar_texto(product.get("name")) or barcode)[:100]
        barras = (limpiar_texto(product.get("codebar")) or "")[:120] or None

        # En Profarmed (precios netos con IVA incluido), cotiza3.PRECIO es el precio final acordado con el cliente (final_price, ej. $6.00).
        # Si no estuviera final_price disponible, usamos price_without_iva como fallback seguro.
        final_p = item.get("final_price")
        if final_p is not None and float(limpiar_numero(final_p, 0.0)) > 0:
            precio = round(float(limpiar_numero(final_p, 0.0)), 2)
        else:
            raw_price = item.get("price_without_iva")
            precio = round(float(limpiar_numero(raw_price, 0.0)), 2)

        line_neto = round(qty * precio, 2)

        if barcode in consolidated:
            prev = consolidated[barcode]
            new_qty = round(prev["CANTIDAD"] + qty, 2)
            new_neto = round(prev["NETO"] + line_neto, 2)
            prev["CANTIDAD"] = new_qty
            prev["NETO"] = new_neto
            prev["PRECIO"] = round(new_neto / new_qty, 2) if new_qty > 0 else precio
        else:
            consolidated[barcode] = {
                "TIENDA": 1,
                "NUMERO": order_id,
                "BARCODE": barcode,
                "CANTIDAD": qty,
                "PRECIO": precio,
                "DESCUEN": 0.00,
                "DESCRI": descri,
                "NETO": line_neto,
                "CAJERO": 1,
                "VENDEDOR": vendedor_id,
                "FECHA": fecha_sql,
                "CAJA": 1,
                "SOCIO": socio_id,
                "COSTO": 0.00,
                "LOTE": "-",
                "CADUCA": "2030-01-01 00:00:00",
                "V2": 1,
                "DONE": 0,
                "BARRAS": barras,
            }

    return list(consolidated.values())

