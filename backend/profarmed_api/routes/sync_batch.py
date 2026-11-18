"""
Routes para Sincronización Síncrona por Lotes (Sync Batch REST).

Endpoints (/api/v1/sync):
- POST /price-lists       - Sincronizar listas de precios
- POST /categories        - Sincronizar categorías
- POST /products          - Sincronizar productos (bulk upsert)
- POST /price-list-items  - Sincronizar items de listas de precios
- POST /customers         - Sincronizar clientes
- POST /users             - Sincronizar colaboradores comerciales (/sellers y /commercial-users)
- POST /cleanup           - Desactivar entidades no sincronizadas
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from crud import crud_sync_batch
from db.base import User
from dependencies import get_db, require_permission
from schemas.category import CategorySync
from schemas.customer import CustomerSync
from schemas.price_list import PriceListCreate, PriceListItemSync
from schemas.product import ProductCreate2
from schemas.user import UserSync

router = APIRouter()
logger = logging.getLogger(__name__)


class CleanupSchema(BaseModel):
    last_sync: datetime
    force: bool = False


class SyncResult(BaseModel):
    total_recibidos: int
    creados: int
    actualizados: int
    errores: int = 0
    detalle_errores: List[str] = []


def _commit_or_500(db: Session, error_prefix: str = "No se pudieron guardar los cambios"):
    try:
        db.commit()
    except Exception as commit_error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{error_prefix}: {commit_error}",
        )


@router.post("/price-lists", response_model=SyncResult)
@router.post("/price-lists/", response_model=SyncResult, include_in_schema=False)
def sync_price_lists(
    price_lists: List[PriceListCreate],
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
    db: Session = Depends(get_db),
):
    result = SyncResult(total_recibidos=len(price_lists), creados=0, actualizados=0, errores=0, detalle_errores=[])

    for item in price_lists:
        try:
            was_created, error_message = crud_sync_batch.save_or_update_price_list(
                db=db,
                list_id=item.price_list_id,
                name=item.list_name,
                description=item.description,
                is_active=item.is_active if item.is_active is not None else True,
                updated_at=item.updated_at if item.updated_at else None,
            )
            if error_message:
                result.errores += 1
                result.detalle_errores.append(f"Lista ID {item.price_list_id}: {error_message}")
            elif was_created:
                result.creados += 1
            else:
                result.actualizados += 1
        except Exception as exc:
            result.errores += 1
            result.detalle_errores.append(f"Lista ID {item.price_list_id}: Error inesperado - {exc}")

    _commit_or_500(db)
    return result


@router.post("/categories", response_model=SyncResult)
@router.post("/categories/", response_model=SyncResult, include_in_schema=False)
def sync_categories(
    categories: List[CategorySync],
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
    db: Session = Depends(get_db),
):
    result = SyncResult(total_recibidos=len(categories), creados=0, actualizados=0, errores=0, detalle_errores=[])

    for category in categories:
        try:
            was_created, error_message = crud_sync_batch.save_or_update_category(
                db=db,
                name=category.name,
                description=category.description,
                updated_at=category.updated_at if category.updated_at else None,
            )
            if error_message:
                result.errores += 1
                result.detalle_errores.append(f"Categoría '{category.name}': {error_message}")
            elif was_created:
                result.creados += 1
            else:
                result.actualizados += 1
        except Exception as exc:
            result.errores += 1
            result.detalle_errores.append(f"Categoría '{category.name}': Error inesperado - {exc}")

    _commit_or_500(db)
    return result


@router.post("/products", response_model=SyncResult)
@router.post("/products/", response_model=SyncResult, include_in_schema=False)
def sync_products(
    products: List[ProductCreate2],
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
    db: Session = Depends(get_db),
):
    products_dict = [
        {
            "product_id": p.product_id.strip(),
            "codebar": p.codebar,
            "name": p.name,
            "description": p.description or None,
            "descripcion_2": p.descripcion_2 or None,
            "unidad_medida": p.unidad_medida,
            "base_price": float(p.base_price),
            "iva_percentage": float(p.iva_percentage) if p.iva_percentage else 0.0,
            "stock_count": p.stock_count if p.stock_count else 0,
            "is_active": p.is_active if p.is_active is not None else True,
            "category_name": p.category_name or None,
            "image_url": p.image_url or None,
            "updated_at": p.updated_at or None,
        }
        for p in products
    ]

    created_count, updated_count, error_list = crud_sync_batch.bulk_sync_products(db, products_dict)
    _commit_or_500(db)
    return SyncResult(
        total_recibidos=len(products),
        creados=created_count,
        actualizados=updated_count,
        errores=len(error_list),
        detalle_errores=error_list,
    )


@router.post("/price-list-items", response_model=SyncResult)
@router.post("/price-list-items/", response_model=SyncResult, include_in_schema=False)
def sync_price_list_items(
    items: List[PriceListItemSync],
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
    db: Session = Depends(get_db),
):
    items_dict = [
        {
            "price_list_id": item.price_list_id,
            "product_id": item.product_id.strip(),
            "markup_percentage": float(item.markup_percentage),
            "final_price": float(item.final_price) if item.final_price is not None else 0.0,
            "updated_at": item.updated_at or datetime.now(timezone.utc),
        }
        for item in items
    ]

    created_count, updated_count, skipped_count, error_list = crud_sync_batch.bulk_upsert_price_list_items(
        db, items_dict
    )
    _commit_or_500(db, error_prefix="Error al guardar los cambios")
    return SyncResult(
        total_recibidos=len(items),
        creados=created_count,
        actualizados=updated_count,
        errores=skipped_count,
        detalle_errores=error_list,
    )


@router.post("/customers", response_model=SyncResult)
@router.post("/customers/", response_model=SyncResult, include_in_schema=False)
def sync_customers(
    customers: List[CustomerSync],
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
    db: Session = Depends(get_db),
):
    customers_dict = [
        {
            "customer_id": customer.customer_id,
            "username": customer.username,
            "email": customer.email or f"{customer.username}@profarmed.com.mx",
            "full_name": customer.full_name or customer.username,
            "password": customer.password,
            "business_name": customer.business_name or None,
            "rfc": customer.rfc or None,
            "price_list_id": customer.price_list_id or None,
            "address_1": customer.address_1 or None,
            "address_2": customer.address_2 or None,
            "address_3": customer.address_3 or None,
            "telefono_1": customer.telefono_1 or None,
            "telefono_2": customer.telefono_2 or None,
            "agent_id": customer.agent_id or None,
            "updated_at": customer.updated_at or None,
        }
        for customer in customers
    ]

    created_count, updated_count, error_list = crud_sync_batch.bulk_upsert_customers(db, customers_dict)
    _commit_or_500(db, error_prefix="Error al guardar los cambios")
    return SyncResult(
        total_recibidos=len(customers),
        creados=created_count,
        actualizados=updated_count,
        errores=len(error_list),
        detalle_errores=error_list,
    )


@router.post("/users", response_model=SyncResult, summary="Sync usuarios y colaboradores")
@router.post("/users/", response_model=SyncResult, include_in_schema=False)
@router.post("/commercial-users", response_model=SyncResult, summary="Sync colaboradores comerciales (Legacy)")
@router.post("/commercial-users/", response_model=SyncResult, include_in_schema=False)
@router.post("/sellers", response_model=SyncResult, summary="Sync agentes de venta (Legacy)")
@router.post("/sellers/", response_model=SyncResult, include_in_schema=False)
def sync_users(
    users: List[UserSync],
    role_slug: str = "seller",
    ensure_groups: bool = True,
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
    db: Session = Depends(get_db),
):
    users_dict = [
        {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email or f"{user.username}@profarmed.local",
            "full_name": user.full_name or user.username,
            "password": user.password,
            "is_active": user.is_active,
            "updated_at": user.updated_at or None,
        }
        for user in users
    ]

    created_count, updated_count, error_list = crud_sync_batch.bulk_upsert_users(
        db=db,
        users=users_dict,
        role_slug=role_slug,
        ensure_groups=ensure_groups,
    )
    _commit_or_500(db, error_prefix="Error al guardar los cambios")
    return SyncResult(
        total_recibidos=len(users),
        creados=created_count,
        actualizados=updated_count,
        errores=len(error_list),
        detalle_errores=error_list,
    )


# Aliases de compatibilidad
sync_sellers = sync_users
sync_commercial_users = sync_users


@router.post("/cleanup", response_model=CleanupSchema)
@router.post("/cleanup/", response_model=CleanupSchema, include_in_schema=False)
def cleanup_post_sync(
    last_sync: CleanupSchema,
    current_user: User = Depends(require_permission("system.sync", "system.admin")),
    db: Session = Depends(get_db),
):
    logger.debug(f"CLEANUP: Received last_sync={last_sync}")
    try:
        success = crud_sync_batch.cleanup_unsynced_items(
            db=db, last_sync=last_sync.last_sync, force=last_sync.force
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operación cancelada por seguridad: se desactivarían demasiados productos. Use force=true para confirmar.",
            )
        db.commit()
    except HTTPException:
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al limpiar items no sincronizados: {error}",
        )
    return last_sync
