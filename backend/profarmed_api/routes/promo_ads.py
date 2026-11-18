"""
Routes para Publicidad de Inicio (Lab Ads)

Gestión completa de las secciones de publicidad (1 a 4 columnas, con carrusel por cuadro
e imágenes responsivas para desktop, tablet y móvil) con almacenamiento en S3.

STOREFRONT (Cliente Autenticado):
- GET /active - Obtener secciones y anuncios activos ordenados (has_ads + sections)

ADMINISTRACIÓN (CRUD PBAC):
- GET /                              - Listar todas las secciones y anuncios (promo_ads.view)
- POST /sections                     - Crear nueva sección (promo_ads.create)
- PUT /sections/reorder              - Reordenar secciones (promo_ads.edit)
- PUT /sections/{section_id}         - Actualizar sección (promo_ads.edit)
- DELETE /sections/{section_id}      - Eliminar sección y sus imágenes en S3 (promo_ads.delete)
- POST /sections/{section_id}/items  - Agregar anuncio a un slot de la sección (promo_ads.create)
- PUT /items/{item_id}               - Actualizar anuncio y limpiar S3 obsoleto (promo_ads.edit)
- DELETE /items/{item_id}            - Eliminar anuncio y sus imágenes en S3 (promo_ads.delete)
- POST /upload-image                 - Subir, comprimir a WEBP y guardar imagen en S3 (promo_ads.upload)
- DELETE /image                      - Eliminar imagen huérfana de S3 por img_key (promo_ads.upload)
"""

import io
from typing import List, Literal, Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from PIL import Image
from sqlalchemy.orm import Session
import uuid6

from core.config import settings
from crud import crud_promo_ad
from db.base import PromoAdItem
from dependencies import get_current_active_user, get_db, require_permission
from schemas.promo_ad import (
    PromoAdActiveResponse,
    PromoAdItemCreate,
    PromoAdItemOut,
    PromoAdItemUpdate,
    PromoAdReorderRequest,
    PromoAdSectionCreate,
    PromoAdSectionOut,
    PromoAdSectionUpdate,
    _build_promo_url,
)

router = APIRouter()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)

VARIANT_MAX_WIDTH = {
    "desktop": 1920,
    "tablet": 1280,
    "mobile": 900,
}


def _delete_s3_keys(keys: List[Optional[str]]) -> None:
    """Elimina de forma segura una lista de claves en BUCKET_PROMOS."""
    if not settings.BUCKET_PROMOS:
        return
    for key in keys:
        if key:
            try:
                s3_client.delete_object(Bucket=settings.BUCKET_PROMOS, Key=key)
            except ClientError:
                pass


""" GET /active - Obtener publicidad activa ordenada para la página de inicio del cliente """
@router.get("/active", response_model=PromoAdActiveResponse)
def api_get_active_promo_ads(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    sections = crud_promo_ad.get_active_promo_ad_sections(db)
    return PromoAdActiveResponse(has_ads=len(sections) > 0, sections=sections)


""" GET / - Listar todas las secciones de publicidad para administración """
@router.get("/", response_model=List[PromoAdSectionOut])
def api_get_all_promo_ads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.view")),
):
    return crud_promo_ad.get_all_promo_ad_sections(db, skip=skip, limit=limit)


""" POST /sections - Crear una nueva sección de publicidad """
@router.post("/sections", response_model=PromoAdSectionOut)
def api_create_promo_ad_section(
    section_in: PromoAdSectionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.create")),
):
    return crud_promo_ad.create_section(db, section_in)


""" PUT /sections/reorder - Actualizar el orden vertical de múltiples secciones """
@router.put("/sections/reorder")
def api_reorder_promo_ad_sections(
    payload: PromoAdReorderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.edit")),
):
    crud_promo_ad.reorder_sections(db, payload.sections)
    return {"message": "Secciones reordenadas correctamente"}


""" PUT /sections/{section_id} - Actualizar metadatos, layout u orden de una sección """
@router.put("/sections/{section_id}", response_model=PromoAdSectionOut)
def api_update_promo_ad_section(
    section_id: UUID,
    section_in: PromoAdSectionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.edit")),
):
    existing = crud_promo_ad.get_section_by_id(db, section_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Sección de publicidad no encontrada")

    # Si disminuye el número de columnas, eliminar anuncios de slots sobrantes y purgar sus imágenes en S3
    if section_in.layout_type is not None and section_in.layout_type < existing.layout_type:
        overflow_items = [it for it in existing.items if it.slot > section_in.layout_type]
        if overflow_items:
            s3_keys: List[Optional[str]] = []
            overflow_ids = []
            for item in overflow_items:
                s3_keys.extend([item.img_desktop, item.img_tablet, item.img_mobile])
                overflow_ids.append(item.item_id)
            _delete_s3_keys(s3_keys)
            db.query(PromoAdItem).filter(PromoAdItem.item_id.in_(overflow_ids)).delete(
                synchronize_session=False
            )
            db.commit()

    updated = crud_promo_ad.update_section(db, section_id, section_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Sección de publicidad no encontrada")
    return updated


""" DELETE /sections/{section_id} - Eliminar sección y purgar imágenes de S3 """
@router.delete("/sections/{section_id}")
def api_delete_promo_ad_section(
    section_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.delete")),
):
    existing = crud_promo_ad.get_section_by_id(db, section_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Sección de publicidad no encontrada")

    s3_keys: List[Optional[str]] = []
    for item in existing.items:
        s3_keys.extend([item.img_desktop, item.img_tablet, item.img_mobile])
    _delete_s3_keys(s3_keys)

    if not crud_promo_ad.delete_section(db, section_id):
        raise HTTPException(status_code=500, detail="No se pudo eliminar la sección")
    return {"message": "Sección de publicidad eliminada correctamente"}


""" POST /sections/{section_id}/items - Agregar anuncio a un slot de la sección """
@router.post("/sections/{section_id}/items", response_model=PromoAdItemOut)
def api_create_promo_ad_item(
    section_id: UUID,
    item_in: PromoAdItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.create")),
):
    section = crud_promo_ad.get_section_by_id(db, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Sección de publicidad no encontrada")

    try:
        return crud_promo_ad.create_item(db, section, item_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


""" PUT /items/{item_id} - Actualizar anuncio y purgar imágenes reemplazadas en S3 """
@router.put("/items/{item_id}", response_model=PromoAdItemOut)
def api_update_promo_ad_item(
    item_id: UUID,
    item_in: PromoAdItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.edit")),
):
    existing = crud_promo_ad.get_item_by_id(db, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    section = crud_promo_ad.get_section_by_id(db, existing.section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Sección padre no encontrada")

    update_data = item_in.model_dump(exclude_unset=True)
    obsolete_keys: List[Optional[str]] = []
    for field in ("img_desktop", "img_tablet", "img_mobile"):
        if field in update_data and update_data[field] != getattr(existing, field):
            obsolete_keys.append(getattr(existing, field))

    try:
        updated = crud_promo_ad.update_item(db, existing, section, item_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _delete_s3_keys(obsolete_keys)
    return updated


""" DELETE /items/{item_id} - Eliminar anuncio y sus imágenes de S3 """
@router.delete("/items/{item_id}")
def api_delete_promo_ad_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("promo_ads.delete")),
):
    existing = crud_promo_ad.get_item_by_id(db, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    _delete_s3_keys([existing.img_desktop, existing.img_tablet, existing.img_mobile])

    if not crud_promo_ad.delete_item(db, item_id):
        raise HTTPException(status_code=500, detail="No se pudo eliminar el anuncio")
    return {"message": "Anuncio eliminado correctamente"}


""" POST /upload-image - Subir, optimizar a WEBP y almacenar imagen en S3 según tamaño de pantalla """
@router.post("/upload-image")
def api_upload_promo_ad_image(
    file: UploadFile = File(...),
    variant: Literal["desktop", "tablet", "mobile"] = Form("desktop"),
    current_user=Depends(require_permission("promo_ads.upload")),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")

    s3_key = f"promo-ads/{variant}/{uuid6.uuid7().hex}.webp"
    max_dim = VARIANT_MAX_WIDTH.get(variant, 1920)

    try:
        image_bytes = file.file.read()
        img = Image.open(io.BytesIO(image_bytes))

        if img.mode in ("RGBA", "LA", "P") or (hasattr(img, "info") and "transparency" in img.info):
            img = img.convert("RGBA")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        if max(img.size) > max_dim:
            if img.width > img.height:
                new_w = max_dim
                new_h = int((max_dim / img.width) * img.height)
            else:
                new_h = max_dim
                new_w = int((max_dim / img.height) * img.width)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        out_io = io.BytesIO()
        img.save(out_io, "WEBP", quality=92, method=6)
        out_io.seek(0)

        s3_client.upload_fileobj(
            out_io,
            settings.BUCKET_PROMOS,
            s3_key,
            ExtraArgs={
                "ContentType": "image/webp",
                "CacheControl": "max-age=2592000",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al procesar o subir imagen: {str(e)}")

    return {
        "img_key": s3_key,
        "img_url": _build_promo_url(s3_key, 1),
        "variant": variant,
    }


""" DELETE /image - Eliminar una imagen subida en S3 dentro de la carpeta promo-ads/ """
@router.delete("/image")
def api_delete_promo_ad_image(
    img_key: str = Query(..., min_length=1, description="Clave S3 dentro de promo-ads/"),
    current_user=Depends(require_permission("promo_ads.upload")),
):
    clean_key = img_key.lstrip("/")
    if not clean_key.startswith("promo-ads/"):
        raise HTTPException(
            status_code=400,
            detail="Solo se permite eliminar imágenes dentro de la carpeta promo-ads/.",
        )

    _delete_s3_keys([clean_key])
    return {"message": "Imagen eliminada de S3 correctamente", "img_key": clean_key}
