"""
Routes para Carga de Sincronización ERP Asíncrona (GZIP + ThreadPool).

Endpoints (/api/v1/sync-upload):
- POST /productos-json                 - Encola categorías y productos (202)
- POST /listas-precios-json            - Encola encabezados de listas de precios (202)
- POST /items-precios-json             - Encola items de listas de precios (202)
- POST /users-json                     - Encola colaboradores comerciales / vendedores (202)
- POST /customers-json                 - Encola clientes y grupos comerciales (202)
- PATCH /orders/{order_id}/sync        - Actualiza bandera is_synced de un pedido
"""

import gzip
import json
import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from crud import crud_sync_upload
from crud.crud_order import set_order_sync_status
from db.base import User
from db.session import SessionLocal
from dependencies import get_db, require_permission

logger = logging.getLogger(__name__)

# Pool dedicado con max_workers=1: serializa escrituras pesadas sin bloquear workers de Uvicorn
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sync_thread_")
logger.info("ThreadPoolExecutor iniciado con max_workers=1")

router = APIRouter()


class SyncResult(BaseModel):
    creados: int
    actualizados: int
    errores: int = 0
    detalle_errores: List[str] = []


class OrderSyncStatusUpdate(BaseModel):
    is_synced: bool = True


async def decompress_request(request: Request) -> Dict[str, Any]:
    """Descomprime payload GZIP (si aplica) y parsea el JSON resultante."""
    try:
        body = await request.body()
        if request.headers.get("Content-Encoding") == "gzip":
            logger.debug(f"Decompressing GZIP payload: {len(body) / 1024:.2f} KB")
            try:
                decompressed = gzip.decompress(body)
                return json.loads(decompressed.decode("utf-8", errors="replace"))
            except gzip.BadGzipFile:
                raise HTTPException(status_code=400, detail="Corrupted GZIP payload")
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"GZIP/JSON Error: {exc}")

        return json.loads(body.decode("utf-8", errors="replace"))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Request parse error: {exc}")
        raise HTTPException(status_code=400, detail=f"Decompression/JSON error: {exc}")


def _run_sync_job(job_label: str, handler, **kwargs):
    """Ejecuta un job de ingesta en sesión aislada con medición de tiempo y cierre seguro."""
    db = SessionLocal()
    try:
        start = time.time()
        result = handler(db=db, **kwargs)
        elapsed = time.time() - start
        logger.info(
            f"[THREAD-SYNC] {job_label} completado en {elapsed:.2f}s - "
            f"Creados: {result['creados']}, Actualizados: {result['actualizados']}, Errores: {result['errores']}"
        )
        return elapsed
    except Exception as exc:
        logger.error(f"[THREAD-SYNC] Error fatal en {job_label}: {exc}")
        traceback.print_exc()
        return None
    finally:
        db.close()


# ============================================================================
# BACKGROUND JOB WORKERS
# ============================================================================


def _process_products_thread(categories: list, products: list):
    logger.info(f"[THREAD-SYNC] Iniciando sync de {len(products)} productos + {len(categories)} categorias")
    _run_sync_job(
        "Productos",
        crud_sync_upload.process_products_from_json,
        categories=categories,
        products=products,
    )


def _process_price_lists_thread(price_lists: list):
    logger.info(f"[THREAD-SYNC] Iniciando sync de {len(price_lists)} listas de precios")
    _run_sync_job(
        "Listas",
        crud_sync_upload.process_price_lists_from_json,
        price_lists=price_lists,
    )


def _process_price_items_thread(items: list):
    logger.info(f"[THREAD-SYNC] Iniciando sync de {len(items)} items de listas")
    elapsed = _run_sync_job(
        "Items",
        crud_sync_upload.process_price_items_from_json,
        items=items,
    )
    if elapsed is not None and elapsed > 10:
        logger.warning(f"Items tardó {elapsed:.2f}s - considerar batching")


def _process_commercial_users_thread(users: list):
    logger.info(f"[THREAD-SYNC] Iniciando sync de {len(users)} colaboradores/agentes comerciales")
    _run_sync_job(
        "Colaboradores comerciales",
        crud_sync_upload.process_commercial_users_from_json,
        users=users,
    )


def _process_customers_thread(customers: list):
    logger.info(f"[THREAD-SYNC] Iniciando sync de {len(customers)} clientes")
    _run_sync_job(
        "Customers",
        crud_sync_upload.process_customers_from_json,
        customers=customers,
    )


# Aliases retrocompatibles internos
_process_listas_thread = _process_price_lists_thread
_process_items_thread = _process_price_items_thread
_process_users_thread = _process_commercial_users_thread
_process_sellers_thread = _process_commercial_users_thread


# ============================================================================
# ENDPOINTS DE INGESTA ASÍNCRONA (GZIP 202)
# ============================================================================


@router.post("/productos-json", status_code=202)
@router.post("/productos-json/", status_code=202, include_in_schema=False)
async def upload_products_json(
    request: Request,
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
):
    """Encola procesamiento de categorías y productos (Step 1)."""
    try:
        data = await decompress_request(request)
        if "productos" not in data:
            raise HTTPException(status_code=400, detail="Missing 'productos' list")

        categories = data.get("categorias", [])
        products = data["productos"]
        executor.submit(_process_products_thread, categories, products)

        return {
            "status": "sync_initiated",
            "message": f"Procesando {len(products)} productos en thread pool",
            "total_items": len(products) + len(categories),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error en upload_products_json: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")


@router.post("/listas-precios-json", status_code=202)
@router.post("/listas-precios-json/", status_code=202, include_in_schema=False)
async def upload_price_lists_json(
    request: Request,
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
):
    """Encola procesamiento de encabezados de listas de precios (Step 2)."""
    try:
        data = await decompress_request(request)
        if "listas" not in data:
            raise HTTPException(status_code=400, detail="Missing 'listas' list")

        price_lists = data["listas"]
        executor.submit(_process_price_lists_thread, price_lists)

        return {
            "status": "sync_initiated",
            "message": f"Procesando {len(price_lists)} listas en thread pool",
            "total_items": len(price_lists),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error en upload_price_lists_json: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")


upload_listas_precios_json = upload_price_lists_json


@router.post("/items-precios-json", status_code=202)
@router.post("/items-precios-json/", status_code=202, include_in_schema=False)
async def upload_price_items_json(
    request: Request,
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
):
    """Encola procesamiento de relaciones producto-lista de precios (Step 3)."""
    try:
        data = await decompress_request(request)
        if "items" not in data:
            raise HTTPException(status_code=400, detail="Missing 'items' list")

        items = data["items"]
        executor.submit(_process_price_items_thread, items)

        return {
            "status": "sync_initiated",
            "message": f"Procesando {len(items)} items en thread pool",
            "total_items": len(items),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error en upload_price_items_json: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")


@router.post("/users-json", status_code=202, summary="Sync colaboradores y usuarios")
@router.post("/users-json/", status_code=202, include_in_schema=False)
@router.post("/commercial-users-json", status_code=202, summary="Sync colaboradores comerciales (Legacy)")
@router.post("/commercial-users-json/", status_code=202, include_in_schema=False)
@router.post("/sellers-json", status_code=202, summary="Sync agentes de venta (Legacy)")
@router.post("/sellers-json/", status_code=202, include_in_schema=False)
async def upload_users_json(
    request: Request,
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
):
    """Encola colaboradores/vendedores sanitizando role/role_id para no degradar permisos existentes (Step 4)."""
    try:
        data = await decompress_request(request)
        users_list = data.get("users") or data.get("commercial_users") or data.get("sellers")
        if users_list is None or not isinstance(users_list, list):
            raise HTTPException(
                status_code=400,
                detail="Se requiere la lista de usuarios bajo las claves 'users', 'commercial_users' o 'sellers'",
            )

        sanitized_users = [
            {k: v for k, v in u.items() if k not in ("role", "role_id")} if isinstance(u, dict) else u
            for u in users_list
        ]
        executor.submit(_process_commercial_users_thread, sanitized_users)

        return {
            "status": "sync_initiated",
            "message": f"Procesando {len(users_list)} colaboradores/usuarios en thread pool",
            "total_items": len(users_list),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error en upload_users_json: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")


upload_sellers_json = upload_users_json
upload_commercial_users_json = upload_users_json


@router.post("/customers-json", status_code=202)
@router.post("/customers-json/", status_code=202, include_in_schema=False)
async def upload_customers_json(
    request: Request,
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
):
    """Encola procesamiento masivo de clientes (Step 5)."""
    try:
        data = await decompress_request(request)
        if "customers" not in data:
            raise HTTPException(status_code=400, detail="Missing 'customers' list")

        customers = data["customers"]
        executor.submit(_process_customers_thread, customers)

        return {
            "status": "sync_initiated",
            "message": f"Procesando {len(customers)} clientes en thread pool",
            "total_items": len(customers),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error en upload_customers_json: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}")


# ============================================================================
# ACTUALIZACIÓN DE SINCRONIZACIÓN ERP DE PEDIDOS
# ============================================================================


@router.patch("/orders/{order_id}/sync")
@router.patch("/orders/{order_id}/sync/", include_in_schema=False)
def update_order_sync_status_endpoint(
    order_id: int,
    payload: OrderSyncStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.sync", "system.admin", "orders.edit", "orders.status")),
):
    """Actualiza el estado de sincronización ERP (`is_synced`) de un pedido."""
    order = set_order_sync_status(db, order_id=order_id, is_synced=payload.is_synced)
    if not order:
        raise HTTPException(status_code=404, detail=f"Pedido #{order_id} no encontrado")

    return {
        "status": "success",
        "order_id": order.order_id,
        "is_synced": order.is_synced,
        "message": f"Pedido #{order_id} actualizado exitosamente: is_synced={order.is_synced}",
    }
