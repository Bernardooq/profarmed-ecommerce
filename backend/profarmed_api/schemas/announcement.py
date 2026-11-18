from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, Literal
from datetime import datetime

from core.config import settings


class AnnouncementBase(BaseModel):
    title: str
    content: str
    img: Optional[str] = None
    img_version: int = 1
    type: Literal['story', 'popup', 'footer']
    status: Literal['activo', 'inactivo'] = 'activo'
    start_date: datetime
    end_date: Optional[datetime] = None

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    img: Optional[str] = None
    type: Optional[Literal['story', 'popup', 'footer']] = None
    status: Optional[Literal['activo', 'inactivo']] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class AnnouncementOut(BaseModel):
    id: int
    title: str
    content: str
    img_version: int = 1
    type: Literal['story', 'popup', 'footer']
    status: Literal['activo', 'inactivo'] = 'activo'
    start_date: datetime
    end_date: Optional[datetime] = None
    img_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_send: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def compute_img_url(cls, values):
        if not isinstance(values, dict):
            d = {c.name: getattr(values, c.name) for c in values.__table__.columns}
            values = d

        img = values.get('img')
        if img:
            img_version = values.get('img_version', 1)
            cf_domain = settings.CLOUDFRONT_PROMOS_URL.strip("/")
            if cf_domain:
                values['img_url'] = f"https://{cf_domain}/{img}?v={img_version}"
            else:
                values['img_url'] = f"https://{settings.BUCKET_PROMOS}.s3.{settings.AWS_REGION}.amazonaws.com/{img}?v={img_version}"

        return values
