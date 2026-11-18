"""
CRUD y Gestión de Anuncios Publicitarios e Historias (Announcements & Stories):

Funciones y Operaciones:
- Crear, consultar, actualizar y eliminar anuncios para banners e historias tipo red social.
- Versionado dinámico de imágenes (`image_version`) para invalidación inmediata de caché en CDN/navegadores.
- Consulta aleatoria ponderada de anuncios e historias activas para la pantalla de inicio y catálogo.
- Desactivación automática de anuncios y promociones cuya fecha de vigencia haya expirado.

Reglas de Negocio y Formatos:
1. Tipos de Contenido (`type`):
   - `banner`: Anuncios horizontales principales desplegados en la parte superior del home/catálogo.
   - `story`: Formato vertical/historia para promociones rápidas o lanzamientos.
2. Control de Vigencia y Visibilidad:
   - Un anuncio es elegible si `is_active = True` y la fecha actual se encuentra dentro del rango `[start_date, end_date]`.
   - Si no se especifica fecha de fin, el anuncio permanece indefinidamente hasta su desactivación manual.
3. Permisos y Control de Acceso (PBAC / RBAC Dinámico):
   - Clientes y Visitantes: Consumen anuncios e historias activas vigentes vía endpoints públicos o autenticados.
   - Colaboradores Internos: La gestión (crear, editar, eliminar, subir multimedia, difusión masiva) se valida mediante capacidades granulares (`announcements.view`, `announcements.create`, `announcements.edit`, `announcements.delete`, `announcements.upload`, `announcements.broadcast`) asignadas a cualquier rol dinámico o superusuario `admin`.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_
from datetime import datetime, timezone
from schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from db.base import AnnouncementModel

"""Obtiene todos los anuncios con paginación"""
def get_announcements(db: Session, skip: int = 0, limit: int = 100):
    return db.query(AnnouncementModel).order_by(desc(AnnouncementModel.created_at)).offset(skip).limit(limit).all()

"""Obtiene un anuncio específico por su ID"""
def get_announcement_by_id(db: Session, announcement_id: int):
    return db.query(AnnouncementModel).filter(AnnouncementModel.id == announcement_id).first()

"""Crea un nuevo anuncio o historia en el sistema"""
def create_announcement(db: Session, announcement: AnnouncementCreate):
    db_announcement = AnnouncementModel(**announcement.model_dump())
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    return db_announcement

"""Actualiza los datos de un anuncio y maneja el versionado de su imagen"""
def update_announcement(db: Session, announcement_id: int, announcement: AnnouncementUpdate):
    db_announcement = get_announcement_by_id(db, announcement_id)
    if not db_announcement:
        return None

    update_data = announcement.model_dump(exclude_unset=True)

    if 'img' in update_data:
        db_announcement.img_version = (db_announcement.img_version or 0) + 1

    for key, value in update_data.items():
        setattr(db_announcement, key, value)

    db.commit()
    db.refresh(db_announcement)
    return db_announcement

"""Elimina un anuncio del sistema por su ID"""
def delete_announcement(db: Session, announcement_id: int):
    db_announcement = get_announcement_by_id(db, announcement_id)
    if not db_announcement:
        return False

    db.delete(db_announcement)
    db.commit()
    return True

"""Obtiene un anuncio activo aleatorio según su tipo"""
def get_random_active_announcement(db: Session, ann_type: str):
    now = datetime.now(timezone.utc)
    return db.query(AnnouncementModel).filter(
        AnnouncementModel.type == ann_type,
        AnnouncementModel.status == 'activo',
        AnnouncementModel.start_date <= now,
        or_(
            AnnouncementModel.end_date == None,
            AnnouncementModel.end_date >= now
        )
    ).order_by(func.random()).first()

"""Obtiene una lista de historias activas de forma aleatoria"""
def get_active_stories(db: Session, limit: int = 100):
    now = datetime.now(timezone.utc)
    return db.query(AnnouncementModel).filter(
        AnnouncementModel.type == 'story',
        AnnouncementModel.status == 'activo',
        AnnouncementModel.start_date <= now,
        or_(
            AnnouncementModel.end_date == None,
            AnnouncementModel.end_date >= now
        )
    ).order_by(func.random()).limit(limit).all()

"""Desactiva automáticamente los anuncios que han superado su fecha de fin"""
def deactivate_expired_announcements(db: Session) -> int:
    now = datetime.now(timezone.utc)
    count = db.query(AnnouncementModel).filter(
        AnnouncementModel.status == 'activo',
        AnnouncementModel.end_date != None,
        AnnouncementModel.end_date < now
    ).update(
        {AnnouncementModel.status: 'inactivo'},
        synchronize_session='fetch'
    )
    db.commit()
    return count
