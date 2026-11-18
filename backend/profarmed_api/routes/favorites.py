"""
Routes para Listas de Favoritos (Favorite Lists)

Gestión completa de las listas de favoritos y sus productos con carga directa al carrito.

LISTAS DE FAVORITOS (CRUD):
- GET / - Obtener todas las listas de favoritos (Cliente / Storefront)
- POST / - Crear nueva lista de favoritos (Cliente / Storefront)
- GET /{list_id} - Obtener detalles de una lista con productos y precios enriquecidos (Cliente)
- PUT /{list_id} - Actualizar nombre de una lista de favoritos (Cliente)
- DELETE /{list_id} - Eliminar permanentemente una lista (Cliente)

PRODUCTOS DE LA LISTA:
- POST /{list_id}/items - Agregar o actualizar cantidad de un producto en la lista (Cliente)
- DELETE /{list_id}/items/{product_id} - Eliminar un producto específico de la lista (Cliente)

UTILIDADES:
- POST /{list_id}/load-to-cart - Cargar todos los productos de la lista de favoritos al carrito actual (Cliente)

Sistema de Permisos:
- Storefront B2B: Aislamiento estricto por identidad y propiedad (sesión directa de cliente / customer_id)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from dependencies import get_db, get_current_user
from db.base import Customer
from schemas.favorite import FavoriteList, FavoriteListCreate, FavoriteListUpdate, FavoriteListItem, FavoriteListItemCreate
from crud import crud_favorite

router = APIRouter(tags=["favorites"])

""" UTILIDAD - Extraer y validar el ID de cliente del usuario autenticado """
def get_customer_id(current_user):
    if isinstance(current_user, Customer):
        return current_user.customer_id
    customer_id = getattr(current_user, 'customer_id', None)
    if customer_id:
        return customer_id
    user_id = getattr(current_user, 'user_id', None)
    if user_id:
        return user_id
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo identificar el cliente")

""" GET / - Obtener todas las listas de favoritos del cliente """
@router.get("", response_model=List[FavoriteList])
@router.get("/", response_model=List[FavoriteList], include_in_schema=False)
def list_favorites(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    customer_id = get_customer_id(current_user)
    return crud_favorite.get_favorite_lists(db, customer_id)

""" POST / - Crear una nueva lista de favoritos """
@router.post("", response_model=FavoriteList)
@router.post("/", response_model=FavoriteList, include_in_schema=False)
def create_favorite(obj_in: FavoriteListCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    customer_id = get_customer_id(current_user)
    try:
        return crud_favorite.create_favorite_list(db, customer_id, obj_in)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

""" GET /{list_id} - Obtener detalles de una lista con productos y precios enriquecidos """
@router.get("/{list_id}", response_model=FavoriteList)
def get_favorite(
    list_id: UUID, 
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"), 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    customer_id = get_customer_id(current_user)
    db_obj = crud_favorite.get_favorite_list_details(db, list_id, customer_id, skip=skip, limit=limit)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista no encontrada")
    return db_obj

""" PUT /{list_id} - Actualizar nombre de una lista de favoritos """
@router.put("/{list_id}", response_model=FavoriteList)
def update_favorite(list_id: UUID, obj_in: FavoriteListUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    customer_id = get_customer_id(current_user)
    try:
        db_obj = crud_favorite.update_favorite_list(db, list_id, customer_id, obj_in)
        if not db_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista no encontrada")
        return db_obj
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

""" DELETE /{list_id} - Eliminar permanentemente una lista de favoritos """
@router.delete("/{list_id}")
def delete_favorite(list_id: UUID, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    customer_id = get_customer_id(current_user)
    if not crud_favorite.delete_favorite_list(db, list_id, customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista no encontrada")
    return {"message": "Lista eliminada correctamente"}

# --- Items en la lista ---

""" POST /{list_id}/items - Agregar o actualizar cantidad de un producto en la lista """
@router.post("/{list_id}/items", response_model=FavoriteListItem)
def add_item(list_id: UUID, item_in: FavoriteListItemCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    customer_id = get_customer_id(current_user)
    try:
        return crud_favorite.add_item_to_favorite_list(db, list_id, customer_id, item_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

""" DELETE /{list_id}/items/{product_id} - Eliminar un producto de la lista de favoritos """
@router.delete("/{list_id}/items/{product_id}")
def remove_item(list_id: UUID, product_id: str, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    customer_id = get_customer_id(current_user)
    if not crud_favorite.remove_item_from_favorite_list(db, list_id, customer_id, product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    return {"message": "Item eliminado de la lista"}

""" POST /{list_id}/load-to-cart - Cargar todos los productos de la lista de favoritos al carrito """
@router.post("/{list_id}/load-to-cart")
def load_to_cart(list_id: UUID, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    customer_id = get_customer_id(current_user)
    try:
        return crud_favorite.load_favorite_list_to_cart(db, list_id, customer_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
