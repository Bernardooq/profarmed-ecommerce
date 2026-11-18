"""
Routes para Descuentos de Productos (ProductDiscounts)

Gestion completa de descuentos de productos:
- Descuentos Generales (sobre precio base)
- Descuentos por Lista de Precios (sobre base + markup)

ENDPOINTS:
- POST / - Crear descuento (requiere 'catalog.discounts')
- GET / - Listar descuentos con filtros (requiere 'catalog.discounts')
- GET /active/{product_id} - Obtener descuento activo para un producto (Customer o 'catalog.view')
- GET /stats - Metricas globales de descuentos (requiere 'catalog.discounts')
- GET /{discount_id} - Ver detalle de descuento (requiere 'catalog.discounts')
- PUT /{discount_id} - Actualizar descuento (requiere 'catalog.discounts')
- DELETE /{discount_id} - Eliminar descuento (requiere 'catalog.discounts')

Regla de Prioridad de Descuentos:
1. Descuento especifico de lista de precios (price_list_id)
2. Descuento general (price_list_id IS NULL)
3. Sin descuento
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from dependencies import get_db, require_permission, get_current_user
from db.base import User, Customer
from schemas.discount import (
    ProductDiscountCreate,
    ProductDiscountUpdate,
    ProductDiscountResponse,
    ActiveDiscountInfo
)
from crud import crud_discount

router = APIRouter()


def check_active_discount_access(current_user = Depends(get_current_user)):
    """Permite el acceso a clientes del e-commerce o colaboradores con permiso 'catalog.view', 'catalog.customer_view', 'orders.create' o 'system.admin'"""
    if isinstance(current_user, Customer):
        return current_user
    if hasattr(current_user, "has_permission") and (
        current_user.has_permission("catalog.view")
        or current_user.has_permission("catalog.customer_view")
        or current_user.has_permission("orders.create")
        or current_user.has_permission("system.admin")
    ):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No posee los permisos necesarios para consultar descuentos"
    )


""" POST / - Crear un nuevo descuento para un producto """
@router.post("", response_model=ProductDiscountResponse, status_code=status.HTTP_201_CREATED)
def create_discount(
    discount_in: ProductDiscountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.discounts"))
):
    return crud_discount.create_discount(db=db, discount_in=discount_in, created_by_user_id=current_user.user_id)


""" GET / - Listar descuentos con filtros opcionales """
@router.get("", response_model=List[ProductDiscountResponse])
def get_discounts(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Limite de registros"),
    product_id: Optional[str] = Query(None, description="Filtrar por producto"),
    search: Optional[str] = Query(None, description="Busqueda en codigo, nombre, descripcion y listas"),
    price_list_id: Optional[int] = Query(None, description="Filtrar por lista de precios"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    only_current: Optional[bool] = Query(None, description="Filtrar solo vigentes (activo y en rango de fechas)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.discounts"))
):
    return crud_discount.get_discounts(
        db=db,
        skip=skip,
        limit=limit,
        product_id=product_id,
        search=search,
        price_list_id=price_list_id,
        is_active=is_active,
        only_current=bool(only_current)
    )


""" GET /active/{product_id} - Obtener descuento activo para un producto segun prioridad """
@router.get("/active/{product_id}", response_model=Optional[ActiveDiscountInfo])
def get_active_product_discount(
    product_id: str,
    price_list_id: Optional[int] = Query(None, description="ID de lista de precios"),
    db: Session = Depends(get_db),
    current_user = Depends(check_active_discount_access)
):
    discount = crud_discount.get_active_discount_for_product(
        db=db,
        product_id=product_id,
        price_list_id=price_list_id
    )
    if not discount or not discount.has_discount:
        return None
    
    return discount


""" GET /stats - Metricas globales de descuentos """
@router.get("/stats")
def get_discount_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.discounts"))
):
    return crud_discount.get_discount_stats(db)


""" GET /{discount_id} - Obtener detalle de un descuento por ID """
@router.get("/{discount_id}", response_model=ProductDiscountResponse)
def get_discount(
    discount_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.discounts"))
):
    discount = crud_discount.get_discount(db=db, discount_id=discount_id)
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Descuento no encontrado"
        )
    return discount


""" PUT /{discount_id} - Actualizar un descuento existente """
@router.put("/{discount_id}", response_model=ProductDiscountResponse)
def update_discount(
    discount_id: UUID,
    discount_in: ProductDiscountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.discounts"))
):
    updated = crud_discount.update_discount(db=db, discount_id_or_obj=discount_id, discount_in=discount_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Descuento no encontrado"
        )
    return updated


""" DELETE /{discount_id} - Eliminar un descuento por ID """
@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount(
    discount_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.discounts"))
):
    success = crud_discount.delete_discount(db=db, discount_id=discount_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Descuento no encontrado"
        )
    return None

