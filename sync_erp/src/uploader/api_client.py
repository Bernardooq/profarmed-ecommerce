"""
API Client - Autenticación, compresión GZIP y comunicación con la API de Profarmed.
"""

import gzip
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote
import requests
from ..config import (
    BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD,
    IMAGES_FOLDER, CDN_URL
)


def login(backend_url: str = None, username: str = None, password: str = None) -> str:
    """
    Inicia sesión contra el endpoint /auth/login/sync y retorna el JWT access_token.
    """
    url = (backend_url or BACKEND_URL).rstrip("/")
    u = username or ADMIN_USERNAME
    p = password or ADMIN_PASSWORD
    
    try:
        response = requests.post(
            f"{url}/auth/login/sync",
            data={"username": u, "password": p},
            timeout=30
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("Respuesta de login no contiene access_token")
        return token
    except Exception as e:
        print(f"[ERROR] Falló la autenticación con la API ({url}): {e}")
        return None


def upload_compressed_json(endpoint: str, data: dict, token: str) -> dict:
    """
    Serializa el diccionario a JSON, lo comprime con GZIP y lo envía
    vía HTTP POST con Content-Encoding: gzip a la API de backend.
    """
    json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
    original_size = len(json_bytes)
    compressed_bytes = gzip.compress(json_bytes)
    compressed_size = len(compressed_bytes)
    
    savings = 100.0 - ((compressed_size / original_size) * 100.0) if original_size > 0 else 0.0
    print(f"  Enviando {endpoint}...")
    print(f"  Tamaño: {original_size/1024/1024:.2f}MB -> {compressed_size/1024/1024:.2f}MB ({savings:.1f}% ahorro GZIP)")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json"
    }
    
    full_url = f"{BACKEND_URL.rstrip('/')}{endpoint}"
    response = requests.post(full_url, data=compressed_bytes, headers=headers, timeout=300)
    
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"  [ERROR HTTP {response.status_code}] {e}")
        try:
            print(f"  [DETALLE] {response.text}")
        except Exception:
            pass
        raise e
    
    result = response.json()
    if response.status_code == 202 or 'status' in result:
        print(f"  [OK] Encolado en background: {result.get('message', 'Procesando')}")
    elif 'actualizados' in result:
        print(f"  [OK] Completado: {result['actualizados']} registros actualizados")
    
    return result


def cleanup_non_synced(token: str, start_time: datetime, safety_minutes: int = 5):
    """
    Ejecuta el cleanup de productos/categorías/listas no sincronizados.
    Resta safety_minutes al tiempo de inicio para dar margen a la cola background.
    """
    cleanup_time = (start_time - timedelta(minutes=safety_minutes)).isoformat()
    print(f"\n--- CLEANUP DE REGISTROS OBSOLETOS (last_sync < {cleanup_time}) ---")
    try:
        response = requests.post(
            f"{BACKEND_URL.rstrip('/')}/sync/cleanup",
            json={"last_sync": cleanup_time},
            headers={"Authorization": f"Bearer {token}"},
            timeout=45
        )
        response.raise_for_status()
        print("  [OK] Limpieza ejecutada exitosamente.")
    except Exception as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 400:
            print(f"  [!] Cleanup abortado por regla de seguridad: {e.response.json().get('detail')}")
        else:
            print(f"  [!] Advertencia en cleanup: {e}")


IMAGE_EXTENSIONS = (".webp", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif")


def _natural_sort_key(path: Path):
    """Orden natural para priorizar 2.webp antes de 10.webp dentro de una subcarpeta."""
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def _resolve_cover_in_dir(product_dir: Path) -> str:
    """
    Selecciona la imagen de portada dentro de `<images_folder>/<codigo_barras>/`:
    1. `1.webp` (o `1.<ext>` convertido a `1.webp` si aún no se comprime) si existe.
    2. El primer archivo de imagen válido encontrado en orden natural (priorizando `.webp`).
    3. `None` si la subcarpeta no existe o está vacía.
    """
    if not product_dir.is_dir():
        return None

    image_files = [
        p for p in product_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not image_files:
        return None

    # 1. Prioridad por defecto: 1.webp
    for img in image_files:
        if img.name.lower() == "1.webp":
            return img.name

    # 2. Si existe 1.<ext> (sin comprimir), en S3 vivirá como 1.webp
    for img in image_files:
        if img.stem == "1":
            return "1.webp"

    # 3. Fallback: primera imagen válida encontrada (orden natural, priorizando .webp)
    webp_files = [p for p in image_files if p.suffix.lower() == ".webp"]
    candidates = webp_files if webp_files else image_files
    chosen = sorted(candidates, key=_natural_sort_key)[0]
    return chosen.name if chosen.suffix.lower() == ".webp" else f"{chosen.stem}.webp"


def verificar_imagen_existe(codebar, images_folder: Path = None, cdn_url: str = None, fallback_id=None) -> str:
    """
    Resuelve la URL de portada en CloudFront usando subcarpetas por código de barras:
      `<cdn_url>/<codigo_barras>/<imagen>`

    Si el código de barras no tiene subcarpeta o está vacía, retorna `None`
    para mandar la URL vacía en el upsert del producto.
    """
    folder_raw = images_folder or IMAGES_FOLDER
    if not folder_raw:
        return None

    folder = Path(folder_raw)
    cdn = (cdn_url or CDN_URL or "").rstrip("/")
    if not cdn:
        return None

    def _clean(val) -> str:
        text = str(val).strip() if val is not None else ""
        return "" if text.lower() in ("none", "nan", "null") else text

    clean_codebar = _clean(codebar)
    if clean_codebar:
        chosen_name = _resolve_cover_in_dir(folder / clean_codebar)
        if not chosen_name:
            return None
        encoded_rel = quote(f"{clean_codebar}/{chosen_name}", safe="/-_.~")
        return f"{cdn}/{encoded_rel}"

    clean_fallback = _clean(fallback_id)
    if clean_fallback:
        chosen_name = _resolve_cover_in_dir(folder / clean_fallback)
        if chosen_name:
            encoded_rel = quote(f"{clean_fallback}/{chosen_name}", safe="/-_.~")
            return f"{cdn}/{encoded_rel}"

    return None


def fetch_unsynced_orders(token: str, limit: int = 100) -> list:
    """
    Obtiene todos los pedidos pendientes de sincronizar con el ERP (is_synced=false)
    mediante paginación lookahead contra GET /orders/all.
    """
    base_url = BACKEND_URL.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    orders = []
    skip = 0

    while True:
        response = requests.get(
            f"{base_url}/orders/all",
            params={"is_synced": "false", "skip": skip, "limit": limit},
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        page_items = payload.get("items", []) if isinstance(payload, dict) else []
        if not page_items:
            break
        orders.extend(page_items)
        if not payload.get("has_more"):
            break
        skip += len(page_items)

    return orders


def fetch_order_details(order_id: int, token: str) -> dict:
    """Obtiene el detalle completo de un pedido (incluyendo partidas) desde GET /orders/{id}/details."""
    base_url = BACKEND_URL.rstrip("/")
    response = requests.get(
        f"{base_url}/orders/{order_id}/details",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def mark_order_synced(order_id: int, token: str, is_synced: bool = True) -> dict:
    """Marca el estado is_synced de un pedido en el backend vía PATCH /sync-upload/orders/{id}/sync."""
    base_url = BACKEND_URL.rstrip("/")
    response = requests.patch(
        f"{base_url}/sync-upload/orders/{order_id}/sync",
        json={"is_synced": is_synced},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

