"""
Routes Públicas para Anuncios e Historias (Public Announcements)

Consulta rápida y pública de anuncios promocionales e historias vigentes.

ANUNCIOS ACTIVOS:
- GET /popup - Obtener un popup promocional activo al azar
- GET /footer - Obtener un banner inferior activo al azar
- GET /stories - Obtener lista de hasta 100 historias vigentes (Autenticado)

Sistema de Acceso:
- Público: Obtención de popups y footers (sin autenticación requerida)
- Usuarios autenticados (Clientes y Colaboradores): Obtención de historias vigentes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from dependencies import get_db, get_current_user
from schemas.announcement import AnnouncementOut
from crud.crud_announcement import (
    get_random_active_announcement,
    get_active_stories
)

router = APIRouter()

""" GET /popup - Obtener un popup promocional activo al azar """
@router.get("/popup", response_model=Optional[AnnouncementOut])
@router.get("/popup/", response_model=Optional[AnnouncementOut], include_in_schema=False)
def api_get_random_popup(db: Session = Depends(get_db)):
    return get_random_active_announcement(db, 'popup')

""" GET /footer - Obtener un banner inferior activo al azar """
@router.get("/footer", response_model=Optional[AnnouncementOut])
@router.get("/footer/", response_model=Optional[AnnouncementOut], include_in_schema=False)
def api_get_random_footer(db: Session = Depends(get_db)):
    return get_random_active_announcement(db, 'footer')

""" GET /stories - Obtener lista de hasta 100 historias vigentes para usuarios autenticados """
@router.get("/stories", response_model=List[AnnouncementOut])
@router.get("/stories/", response_model=List[AnnouncementOut], include_in_schema=False)
def api_get_active_stories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return get_active_stories(db, limit=100)

