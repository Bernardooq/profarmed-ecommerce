"""
Routes para Anuncios e Historias (Announcements)

Gestión completa de los banners, popups e historias del sistema con almacenamiento de imágenes en S3.

ANUNCIOS (CRUD):
- GET / - Obtener todos los anuncios registrados (requiere announcements.view)
- POST / - Crear anuncio nuevo (requiere announcements.create)
- PUT /{announcement_id} - Actualizar anuncio existente (requiere announcements.edit)
- DELETE /{announcement_id} - Eliminar anuncio y su imagen de S3 (requiere announcements.delete)

IMÁGENES:
- POST /upload-image - Subir, comprimir a WEBP y guardar imagen promocional en S3 (requiere announcements.upload)

Sistema de Permisos (PBAC / RBAC Dinámico):
- announcements.view: Obtener lista de anuncios e historias
- announcements.create: Crear nuevo anuncio o historia
- announcements.edit: Modificar anuncio existente
- announcements.delete: Eliminar anuncio e imagen S3
- announcements.upload: Subir y optimizar imagen promocional a S3
- announcements.broadcast: Enviar difusión masiva por email
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError
import uuid6
import io
from PIL import Image
from datetime import datetime, timezone

from core.config import settings
from dependencies import get_db, require_permission
from schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementOut
from db.base import Customer
from utils.email_utils import send_announcement_email, send_mass_announcement_emails
from crud.crud_announcement import (
    get_announcements,
    get_announcement_by_id,
    create_announcement,
    update_announcement,
    delete_announcement,
    deactivate_expired_announcements
)
from db.session import SessionLocal

router = APIRouter()

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

""" UTILIDAD - Desactivar en segundo plano anuncios cuya fecha de fin ha expirado """
def _deactivate_expired_bg():
    db = SessionLocal()
    try:
        deactivate_expired_announcements(db)
    finally:
        db.close()

""" GET / - Obtener todos los anuncios registrados con limpieza en segundo plano de expirados """
@router.get("/", response_model=List[AnnouncementOut])
def api_get_announcements(
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"), 
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("announcements.view")),
    bg_tasks: BackgroundTasks = None,
):
    if bg_tasks:
        bg_tasks.add_task(_deactivate_expired_bg)
    return get_announcements(db, skip=skip, limit=limit)

""" POST / - Crear un nuevo anuncio o historia en la base de datos """
@router.post("/", response_model=AnnouncementOut)
def api_create_announcement(
    announcement: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("announcements.create"))
):
    return create_announcement(db, announcement)

""" PUT /{announcement_id} - Actualizar datos de un anuncio y borrar imágenes obsoletas en S3 """
@router.put("/{announcement_id}", response_model=AnnouncementOut)
def api_update_announcement(
    announcement_id: int,
    announcement: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("announcements.edit"))
):
    existing = get_announcement_by_id(db, announcement_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    update_data = announcement.model_dump(exclude_unset=True)

    if 'img' in update_data and update_data['img'] != existing.img:
        old_img = existing.img
        if old_img:
            try:
                s3_client.delete_object(Bucket=settings.BUCKET_PROMOS, Key=old_img)
            except ClientError:
                pass

    db_announcement = update_announcement(db, announcement_id, announcement)
    if not db_announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return db_announcement

""" DELETE /{announcement_id} - Eliminar permanentemente un anuncio y su imagen de S3 """
@router.delete("/{announcement_id}")
def api_delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("announcements.delete"))
):
    db_announcement = get_announcement_by_id(db, announcement_id)
    if not db_announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Si hay imagen, intentar borrarla de S3
    if db_announcement.img:
        try:
            s3_client.delete_object(Bucket=settings.BUCKET_PROMOS, Key=db_announcement.img)
        except ClientError:
            pass # Ignoramos error en S3 si no existe o falla

    success = delete_announcement(db, announcement_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete announcement")
        
    return {"message": "Announcement deleted successfully"}

""" POST /upload-image - Subir, optimizar y almacenar una imagen promocional en S3 en formato WEBP """
@router.post("/upload-image")
def api_upload_promo_image(
    file: UploadFile = File(...),
    current_user = Depends(require_permission("announcements.upload"))
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen.")
        
    s3_key = f"promos/{uuid6.uuid7().hex}.webp"
    
    try:
        # Leer archivo y abrir con Pillow
        image_bytes = file.file.read()
        img = Image.open(io.BytesIO(image_bytes))
        
        # Mantener transparencia (RGBA) o convertir a RGB
        if img.mode in ('RGBA', 'LA', 'P') or (hasattr(img, 'info') and 'transparency' in img.info):
            img = img.convert('RGBA')
        elif img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Redimensionar si es muy grande (> 1920)
        max_dim = 1920
        if max(img.size) > max_dim:
            if img.width > img.height:
                new_w = max_dim
                new_h = int((max_dim / img.width) * img.height)
            else:
                new_h = max_dim
                new_w = int((max_dim / img.height) * img.width)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
        # Guardar como webp en memoria con ALTA calidad
        out_io = io.BytesIO()
        img.save(out_io, 'WEBP', quality=95, method=6)
        out_io.seek(0)
        
        # Subir a S3 con caché de 1 mes
        s3_client.upload_fileobj(
            out_io, 
            settings.BUCKET_PROMOS, 
            s3_key,
            ExtraArgs={
                'ContentType': 'image/webp',
                'CacheControl': 'max-age=2592000'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al procesar o subir imagen: {str(e)}")
        
    return {"img_key": s3_key}


""" POST /{announcement_id}/send - Enviar anuncio a todos los clientes con notificaciones activas """
@router.post("/{announcement_id}/send")
def api_send_announcement(
    announcement_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("announcements.broadcast"))
):
    announcement = get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Actualizar last_send
    announcement.last_send = datetime.now(timezone.utc)
    db.commit()
    db.refresh(announcement)
    
    # Obtener el img_url computado del esquema Pydantic
    announcement_out = AnnouncementOut.model_validate(announcement)
    img_url = announcement_out.img_url
            
    # Obtener correos únicos de clientes que desean recibir notificaciones
    customers = db.query(Customer.email).filter(
        Customer.notificate == True, 
        Customer.email != None, 
        Customer.email != ""
    ).all()
    
    recipient_emails = list(set(c.email.strip() for c in customers if c.email and '@' in c.email))
    
    if recipient_emails:
        # Enviar lote masivo en segundo plano reutilizando 1 sola conexión SMTP persistente
        background_tasks.add_task(
            send_mass_announcement_emails,
            recipient_emails=recipient_emails,
            title=announcement.title,
            content=announcement.content,
            img_url=img_url
        )
        
    return {
        "message": f"Envío masivo programado en segundo plano para {len(recipient_emails)} usuarios",
        "total_recipients": len(recipient_emails),
        "last_send": announcement.last_send
    }

