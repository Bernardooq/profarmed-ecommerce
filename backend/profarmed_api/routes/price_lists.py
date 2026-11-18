"""
Routes para Listas de Precios (PriceLists)

Gestion completa de listas de precios y sus items(markups por producto):

LISTAS DE PRECIOS:
- GET / - Listar todas las listas (requiere 'catalog.prices' o permisos comerciales/descuentos de lectura)
- GET /{id} - Ver lista con sus items (requiere 'catalog.prices')
- POST / - Crear lista (requiere 'catalog.prices')
- PUT /{id} - Actualizar lista (requiere 'catalog.prices')
- DELETE /{id} - Eliminar lista (requiere 'catalog.prices' y valida integridad referencial)

ITEMS (Markups por producto):
- GET /{id}/items - Ver todos los items (requiere 'catalog.prices')
- POST /{id}/items - Agregar/actualizar item (requiere 'catalog.prices')
- POST /{id}/items/bulk - Agregar/actualizar multiples items (requiere 'catalog.prices')
- PUT /{id}/items/{product_id} - Actualizar markup especifico (requiere 'catalog.prices')
- DELETE /{id}/items/{product_id} - Eliminar item (requiere 'catalog.prices')

UTILIDADES PARA UI:
- GET /{id}/available-products - Productos no en lista (para agregar)
- GET /{id}/items-with-details - Items con info completa del producto

Sistema de Precios:
- Cada lista tiene multiples items
- Cada item define un markup% para un producto
- Precio final = (base_price * (1 + markup/100)) * (1 + iva/100)
- Los clientes ven precios segun su lista asignada

Permisos: Control dinámico PBAC ('catalog.prices')
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from dependencies import get_db, require_permission
from db.base import User, CustomerInfo
from schemas.price_list import (
    PriceList, PriceListCreate, PriceListUpdate, PriceListWithItems,
    PriceListItem, PriceListItemCreate, PriceListItemUpdate,
    PriceListItemsBulkUpdate
)
from schemas.product import Product as ProductSchema
from crud import crud_price_list
router = APIRouter()

""" GET / - Listar todas las listas de precios """
@router.get("", response_model=List[PriceList])
def get_price_lists(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"),
    is_active: bool = None,
    is_public_internal: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices", "catalog.prices_public", "catalog.discounts", "customers.edit", "customers.view"))
):
    # Evaluación PBAC: si el usuario no tiene permisos de gestión completa ni es admin, solo ve listas públicas internas
    is_admin_or_manager = (
        (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("catalog.prices")))
        or getattr(current_user, "role_id", None) == 1
    )
    filter_public_internal = is_public_internal
    if not is_admin_or_manager:
        filter_public_internal = True

    return crud_price_list.get_price_lists(db, skip=skip, limit=limit, is_active=is_active, is_public_internal=filter_public_internal)

""" GET /{id} - Ver detalle de una lista de precios con sus items """
@router.get("/{price_list_id}", response_model=PriceListWithItems)
def get_price_list(
    price_list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices", "catalog.prices_public"))
):
    price_list = crud_price_list.get_price_list(db, price_list_id)
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    is_admin_or_manager = (
        (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("catalog.prices")))
        or getattr(current_user, "role_id", None) == 1
    )
    if not is_admin_or_manager and not price_list.is_public_internal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta lista de precios es privada y no tienes permiso para consultarla"
        )
    
    # Get items
    items = crud_price_list.get_price_list_items(db, price_list_id)
    
    return PriceListWithItems(
        **price_list.__dict__,
        items=items
    )

""" POST / - Crear una nueva lista de precios """
@router.post("", response_model=PriceList, status_code=status.HTTP_201_CREATED)
def create_price_list(
    price_list: PriceListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Crear una nueva lista de precios
    return crud_price_list.create_price_list(db, price_list)

""" PUT /{id} - Actualizar una lista de precios """
@router.put("/{price_list_id}", response_model=PriceList)
def update_price_list(
    price_list_id: int,
    price_list_update: PriceListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Actualizar una lista de precios
    
    updated_list = crud_price_list.update_price_list(db, price_list_id, price_list_update)
    
    if not updated_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    return updated_list

""" DELETE /{id} - Eliminar una lista de precios """
@router.delete("/{price_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_list(
    price_list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Eliminar una lista de precios con validación de integridad referencial
    price_list = crud_price_list.get_price_list(db, price_list_id)
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    # Validar si hay clientes asignados a esta lista
    assigned_count = db.query(CustomerInfo).filter(CustomerInfo.price_list_id == price_list_id).count()
    if assigned_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la lista de precios porque está asignada a {assigned_count} cliente(s)"
        )
    
    success = crud_price_list.delete_price_list(db, price_list_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    return None


# PriceListItem Endpoints
""" GET /{id}/items - Ver todos los items de una lista de precios """
@router.get("/{price_list_id}/items", response_model=List[PriceListItem])
def get_price_list_items(
    price_list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Obtener todos los items de una lista de precios
    
    # Verify price list exists
    price_list = crud_price_list.get_price_list(db, price_list_id)
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    return crud_price_list.get_price_list_items(db, price_list_id)

""" POST /{id}/items - Crear o actualizar un item en la lista de precios """
@router.post("/{price_list_id}/items", response_model=PriceListItem, status_code=status.HTTP_201_CREATED)
def create_price_list_item(
    price_list_id: int,
    item: PriceListItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Crear o actualizar un item en la lista de precios
    
    # Verify price list exists
    price_list = crud_price_list.get_price_list(db, price_list_id)
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    return crud_price_list.create_price_list_item(db, price_list_id, item)

""" POST /{id}/items/bulk - Crear o actualizar multiples items en la lista de precios """
@router.post("/{price_list_id}/items/bulk", response_model=List[PriceListItem])
def bulk_update_price_list_items(
    price_list_id: int,
    bulk_update: PriceListItemsBulkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Crear o actualizar multiples items en la lista de precios
    
    # Verify price list exists
    price_list = crud_price_list.get_price_list(db, price_list_id)
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    return crud_price_list.bulk_update_price_list_items(db, price_list_id, bulk_update.items)

""" PUT /{id}/items/{product_id} - Actualizar un item especifico en la lista de precios """
@router.put("/{price_list_id}/items/{product_id}", response_model=PriceListItem)
def update_price_list_item(
    price_list_id: int,
    product_id: str,
    item_update: PriceListItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Actualizar un item especifico en la lista de precios
    
    updated_item = crud_price_list.update_price_list_item(db, price_list_id, product_id, item_update)
    
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado en la lista de precios"
        )
    
    return updated_item

""" DELETE /{id}/items/{product_id} - Eliminar un item de la lista de precios """
@router.delete("/{price_list_id}/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_list_item(
    price_list_id: int,
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
    # Eliminar un item de la lista de precios
    
    success = crud_price_list.delete_price_list_item(db, price_list_id, product_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado en la lista de precios"
        )
    
    return None


# Modal Helpers
""" GET /{id}/available-products - Obtener productos no en la lista de precios """
@router.get("/{price_list_id}/available-products", response_model=List[ProductSchema])
def get_available_products(
    price_list_id: int,
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Maximo de registros"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices"))
):
   # Obtener productos que NO ESTAN en la lista de precios
   # Para agregar nuevos items
    price_list = crud_price_list.get_price_list(db, price_list_id)
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    return crud_price_list.get_products_not_in_price_list(
        db=db,
        price_list_id=price_list_id,
        skip=skip,
        limit=limit,
        search=search
    )

""" GET /{id}/items-with-details - Obtener items con info completa del producto """
@router.get("/{price_list_id}/items-with-details")
def get_items_with_details(
    price_list_id: int,
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Maximo de registros"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.prices", "catalog.prices_public"))
):
    # Verificar que la lista de precios exista
    price_list = crud_price_list.get_price_list(db, price_list_id)
    if not price_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada"
        )
    
    # Evaluación PBAC: ¿Tiene permisos de administración de precios o es admin?
    is_admin_or_manager = (
        (hasattr(current_user, "has_permission") and (current_user.has_permission("system.admin") or current_user.has_permission("catalog.prices")))
        or getattr(current_user, "role_id", None) == 1
    )
    
    # Si no es administrador de precios, la lista debe ser pública interna obligatoriamente
    if not is_admin_or_manager and not price_list.is_public_internal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta lista de precios es privada y no tienes permiso para consultarla"
        )
    
    return crud_price_list.get_products_in_price_list_with_details(
        db=db,
        price_list_id=price_list_id,
        skip=skip,
        limit=limit,
        search=search,
        sanitize_costs=not is_admin_or_manager
    )


