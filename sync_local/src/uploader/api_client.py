"""
API Client - Cliente HTTP centralizado para comunicación con el backend.
"""

import gzip
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

from ..config import BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD, IMAGES_FOLDER, CDN_URL


def login(backend_url=BACKEND_URL, username=ADMIN_USERNAME, password=ADMIN_PASSWORD):
    """Obtiene token JWT de sincronización contra /auth/login/sync."""
    try:
        response = requests.post(
            f"{backend_url}/auth/login/sync",
            data={"username": username, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as exc:
        print(f"Login failed: {exc}")
        return None


def verify_product_image(product_id, images_folder=IMAGES_FOLDER, cdn_url=CDN_URL):
    """
    Entorno demo: verifica si existe .webp local y, en cualquier caso válido,
    retorna la URL del CDN configurada para el producto.
    """
    clean_id = str(product_id).strip()
    if not clean_id:
        return None
    if images_folder:
        try:
            image_path = Path(images_folder) / f"{clean_id}.webp"
            if image_path.exists():
                return f"{cdn_url}/{clean_id}.webp"
        except Exception:
            pass
    return f"{cdn_url}/{clean_id}.webp"


def upload_compressed_json(endpoint, data, token):
    """Comprime payload JSON con GZIP y lo envía a los endpoints /sync-upload/*."""
    json_str = json.dumps(data)
    original_bytes = len(json_str.encode("utf-8"))
    compressed = gzip.compress(json_str.encode("utf-8"))
    compressed_bytes = len(compressed)

    savings = 100 - (compressed_bytes / original_bytes) * 100 if original_bytes else 0.0
    print(f"  Uploading {endpoint}...")
    print(
        f"  Size: {original_bytes / 1024 / 1024:.2f}MB -> "
        f"{compressed_bytes / 1024 / 1024:.2f}MB ({savings:.1f}% savings)"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{BACKEND_URL}{endpoint}",
        data=compressed,
        headers=headers,
        timeout=300,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        print(f"  [ERROR] {exc}")
        print(f"  [DETALLE] {response.text[:500]}")
        raise

    result = response.json()
    if response.status_code == 202 or "status" in result:
        print(f"  [OK] Encolado: {result.get('message', 'Procesando en background')}")
    elif "actualizados" in result:
        print(f"  [OK] Completado: {result['actualizados']} actualizados")

    return result


def send_batch(endpoint, data, token, entity_name, verbose_errors=False):
    """Envía un lote JSON estándar al backend."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    clean_endpoint = endpoint.lstrip("/")
    try:
        response = requests.post(
            f"{BACKEND_URL}/{clean_endpoint}",
            json=data,
            headers=headers,
        )
        if response.status_code != 200 and verbose_errors:
            print(f"  DEBUG {entity_name}: Status {response.status_code}, Content: {response.text[:300]}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", str(exc)) if exc.response else str(exc)
        except Exception:
            detail = str(exc)
        print(f"  [ERR] {entity_name} Batch Failed: {detail or exc}")
        return {"creados": 0, "actualizados": 0, "errores": len(data)}
    except Exception as exc:
        print(f"  [ERR] {entity_name} Batch Failed: {exc}")
        return {"creados": 0, "actualizados": 0, "errores": len(data)}


def sync_in_parallel(data, batch_size, endpoint, token, entity_name, max_workers=5, verbose_errors=False):
    """Divide una colección en lotes y los envía en paralelo con ThreadPoolExecutor."""
    if not data:
        print(f"[{entity_name}] No data to sync.")
        return {"creados": 0, "actualizados": 0, "errores": 0}

    total = len(data)
    batches = [data[i:i + batch_size] for i in range(0, total, batch_size)]
    print(f"[{entity_name}] Syncing {total} records -> {len(batches)} batches ({max_workers} workers)...")

    stats = {"creados": 0, "actualizados": 0, "errores": 0}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(send_batch, endpoint, batch, token, entity_name, verbose_errors): idx
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                res = future.result()
                stats["creados"] += res.get("creados", 0)
                stats["actualizados"] += res.get("actualizados", 0)
                stats["errores"] += res.get("errores", 0)
            except Exception as exc:
                print(f"  Batch {batch_idx + 1}/{len(batches)} failed: {exc}")
                stats["errores"] += len(batches[batch_idx])

    print(
        f"[{entity_name}] DONE: {stats['creados']} created, "
        f"{stats['actualizados']} updated, {stats['errores']} errors"
    )
    return stats


def cleanup_non_synced(token, last_sync):
    """Desactiva productos, categorías y listas de precios no actualizados en el ciclo."""
    print("\n--- CLEANUP: PRODUCTS ---")
    try:
        response = requests.post(
            f"{BACKEND_URL}/sync/cleanup",
            json={"last_sync": last_sync},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        print("  [OK] Productos/categorías/listas limpiados")
    except Exception as exc:
        if "400" in str(exc) and getattr(exc, "response", None) is not None:
            try:
                print(f"  [!] CLEANUP ABORTADO: {exc.response.json().get('detail')}")
                return
            except Exception:
                pass
        print(f"  [!] Cleanup warning: {exc}")


def cleanup_non_synced_users(token, last_sync):
    """Desactiva usuarios no actualizados en el ciclo."""
    print("\n--- CLEANUP: USERS ---")
    try:
        response = requests.post(
            f"{BACKEND_URL}/sync/cleanup-users",
            json={"last_sync": last_sync},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        print("  [OK] Usuarios limpiados")
    except Exception as exc:
        print(f"  [!] Cleanup warning: {exc}")


# Alias retrocompatibles
verificar_imagen_existe = verify_product_image
