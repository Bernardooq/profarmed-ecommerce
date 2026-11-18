"""
CRUD y Gestión de Publicidad de Inicio (Lab Ads):

Funciones y Operaciones:
- Administrar secciones de publicidad configurables en 1, 2, 3 o 4 columnas.
- Administrar múltiples anuncios por columna (slot) para carruseles independientes.
- Versionado dinámico de imágenes (`img_version`) para invalidación de caché en CloudFront/S3.
- Consulta optimizada para el storefront B2B filtrando vigencia temporal y slots válidos.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import asc, or_
from sqlalchemy.orm import Session, selectinload

from db.base import PromoAdItem, PromoAdSection
from schemas.promo_ad import (
    PromoAdItemCreate,
    PromoAdItemUpdate,
    PromoAdSectionCreate,
    PromoAdSectionOrderItem,
    PromoAdSectionUpdate,
)


def get_all_promo_ad_sections(db: Session, skip: int = 0, limit: int = 100) -> List[PromoAdSection]:
    """Obtiene todas las secciones de publicidad ordenadas para el panel administrativo."""
    return (
        db.query(PromoAdSection)
        .options(selectinload(PromoAdSection.items))
        .order_by(asc(PromoAdSection.display_order), asc(PromoAdSection.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normaliza cualquier datetime a UTC aware para comparaciones seguras."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def get_active_promo_ad_sections(db: Session) -> List[PromoAdSection]:
    """
    Obtiene las secciones activas y vigentes para la vista de inicio del cliente.
    Filtra ítems inactivos o fuera de rango de columnas y omite secciones sin anuncios activos.
    """
    now = datetime.now(timezone.utc)
    sections = (
        db.query(PromoAdSection)
        .options(selectinload(PromoAdSection.items))
        .filter(
            PromoAdSection.is_active == True,
            or_(PromoAdSection.start_date == None, PromoAdSection.start_date <= now),
            or_(PromoAdSection.end_date == None, PromoAdSection.end_date >= now),
        )
        .order_by(asc(PromoAdSection.display_order), asc(PromoAdSection.created_at))
        .all()
    )

    visible_sections: List[PromoAdSection] = []
    for section in sections:
        active_items = [
            item
            for item in section.items
            if (
                item.is_active
                and 1 <= item.slot <= section.layout_type
                and (item.start_date is None or _as_utc(item.start_date) <= now)
                and (item.end_date is None or _as_utc(item.end_date) >= now)
            )
        ]
        if active_items:
            # Desacoplar del session antes de filtrar items para no disparar delete-orphan
            db.expunge(section)
            section.items = sorted(active_items, key=lambda i: (i.slot, i.display_order))
            visible_sections.append(section)

    return visible_sections


def get_section_by_id(db: Session, section_id: UUID) -> Optional[PromoAdSection]:
    """Obtiene una sección por su UUID junto con sus anuncios."""
    return (
        db.query(PromoAdSection)
        .options(selectinload(PromoAdSection.items))
        .filter(PromoAdSection.section_id == section_id)
        .first()
    )


def create_section(db: Session, section_in: PromoAdSectionCreate) -> PromoAdSection:
    """Crea una nueva sección publicitaria."""
    db_section = PromoAdSection(**section_in.model_dump())
    db.add(db_section)
    db.commit()
    db.refresh(db_section)
    return db_section


def update_section(db: Session, section_id: UUID, section_in: PromoAdSectionUpdate) -> Optional[PromoAdSection]:
    """Actualiza los metadatos, layout u orden de una sección."""
    db_section = get_section_by_id(db, section_id)
    if not db_section:
        return None

    update_data = section_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_section, key, value)

    db.commit()
    db.refresh(db_section)
    return db_section


def reorder_sections(db: Session, orders: List[PromoAdSectionOrderItem]) -> None:
    """Actualiza el orden vertical de múltiples secciones en una sola transacción."""
    for entry in orders:
        db.query(PromoAdSection).filter(
            PromoAdSection.section_id == entry.section_id
        ).update({PromoAdSection.display_order: entry.display_order}, synchronize_session=False)
    db.commit()


def delete_section(db: Session, section_id: UUID) -> bool:
    """Elimina una sección y en cascada todos sus anuncios."""
    db_section = get_section_by_id(db, section_id)
    if not db_section:
        return False

    db.delete(db_section)
    db.commit()
    return True


def get_item_by_id(db: Session, item_id: UUID) -> Optional[PromoAdItem]:
    """Obtiene un anuncio individual por su UUID."""
    return db.query(PromoAdItem).filter(PromoAdItem.item_id == item_id).first()


def create_item(db: Session, section: PromoAdSection, item_in: PromoAdItemCreate) -> PromoAdItem:
    """Crea un anuncio dentro de un slot válido de la sección."""
    if item_in.slot > section.layout_type:
        raise ValueError(
            f"El slot {item_in.slot} excede el número de columnas de la sección ({section.layout_type})."
        )

    db_item = PromoAdItem(section_id=section.section_id, **item_in.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_item(db: Session, db_item: PromoAdItem, section: PromoAdSection, item_in: PromoAdItemUpdate) -> PromoAdItem:
    """Actualiza un anuncio individual e incrementa img_version si cambia alguna imagen."""
    update_data = item_in.model_dump(exclude_unset=True)

    target_slot = update_data.get("slot", db_item.slot)
    if target_slot > section.layout_type:
        raise ValueError(
            f"El slot {target_slot} excede el número de columnas de la sección ({section.layout_type})."
        )

    if any(k in update_data for k in ("img_desktop", "img_tablet", "img_mobile")):
        db_item.img_version = (db_item.img_version or 1) + 1

    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: UUID) -> bool:
    """Elimina un anuncio individual."""
    db_item = get_item_by_id(db, item_id)
    if not db_item:
        return False

    db.delete(db_item)
    db.commit()
    return True
