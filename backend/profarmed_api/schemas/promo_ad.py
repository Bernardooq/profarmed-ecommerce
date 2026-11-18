"""
Esquemas Pydantic para Publicidad de Inicio (Lab Ads).

Modela secciones configurables de 1 a 4 columnas y sus anuncios individuales
con soporte para carruseles por slot e imágenes responsivas (desktop, tablet, móvil).
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.config import settings


def _build_promo_url(key: Optional[str], img_version: int) -> Optional[str]:
    """Construye la URL pública de CloudFront o S3 con cache-busting."""
    if not key:
        return None
    cf_domain = settings.CLOUDFRONT_PROMOS_URL.strip("/")
    if cf_domain:
        return f"https://{cf_domain}/{key}?v={img_version}"
    return f"https://{settings.BUCKET_PROMOS}.s3.{settings.AWS_REGION}.amazonaws.com/{key}?v={img_version}"


class PromoAdItemBase(BaseModel):
    slot: int = Field(1, ge=1, le=4, description="Columna destino (1..layout_type)")
    display_order: int = Field(0, ge=0, description="Orden dentro del carrusel de la columna")
    title: Optional[str] = Field(None, max_length=150)
    link_url: Optional[str] = Field(None, max_length=500)
    img_desktop: str = Field(..., min_length=1, max_length=255)
    img_tablet: Optional[str] = Field(None, max_length=255)
    img_mobile: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class PromoAdItemCreate(PromoAdItemBase):
    pass


class PromoAdItemUpdate(BaseModel):
    slot: Optional[int] = Field(None, ge=1, le=4)
    display_order: Optional[int] = Field(None, ge=0)
    title: Optional[str] = Field(None, max_length=150)
    link_url: Optional[str] = Field(None, max_length=500)
    img_desktop: Optional[str] = Field(None, min_length=1, max_length=255)
    img_tablet: Optional[str] = Field(None, max_length=255)
    img_mobile: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class PromoAdItemOut(BaseModel):
    item_id: UUID
    section_id: UUID
    slot: int
    display_order: int
    title: Optional[str] = None
    link_url: Optional[str] = None
    img_desktop: str
    img_tablet: Optional[str] = None
    img_mobile: Optional[str] = None
    img_desktop_url: Optional[str] = None
    img_tablet_url: Optional[str] = None
    img_mobile_url: Optional[str] = None
    img_version: int = 1
    is_active: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_image_urls(cls, values):
        if not isinstance(values, dict):
            values = {c.name: getattr(values, c.name) for c in values.__table__.columns}

        img_version = values.get("img_version") or 1
        values["img_desktop_url"] = _build_promo_url(values.get("img_desktop"), img_version)
        values["img_tablet_url"] = _build_promo_url(values.get("img_tablet"), img_version)
        values["img_mobile_url"] = _build_promo_url(values.get("img_mobile"), img_version)
        return values


class PromoAdSectionBase(BaseModel):
    title: Optional[str] = Field(None, max_length=150)
    layout_type: Literal[1, 2, 3, 4]
    display_order: int = Field(0, ge=0)
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class PromoAdSectionCreate(PromoAdSectionBase):
    pass


class PromoAdSectionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=150)
    layout_type: Optional[Literal[1, 2, 3, 4]] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class PromoAdSectionOut(BaseModel):
    section_id: UUID
    title: Optional[str] = None
    layout_type: int
    display_order: int
    is_active: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[PromoAdItemOut] = []

    model_config = ConfigDict(from_attributes=True)


class PromoAdSectionOrderItem(BaseModel):
    section_id: UUID
    display_order: int = Field(..., ge=0)


class PromoAdReorderRequest(BaseModel):
    sections: List[PromoAdSectionOrderItem]


class PromoAdActiveResponse(BaseModel):
    has_ads: bool
    sections: List[PromoAdSectionOut]
