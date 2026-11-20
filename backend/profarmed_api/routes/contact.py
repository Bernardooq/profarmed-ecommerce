"""
Routes para Formularios de Contacto (Contact Messages)

Gestión y recepción de mensajes de contacto enviados por la página web de Profarmed.

CONTACTO:
- GET /admin/all - Obtener lista de mensajes recibidos (requiere 'contact.view')
- POST /send - Enviar y registrar mensaje de contacto con validación Turnstile CAPTCHA y encolado SMTP (Público)
- PATCH /{message_id} - Actualizar estado de seguimiento (requiere 'contact.manage')
- DELETE /{message_id} - Eliminar permanentemente un mensaje (requiere 'contact.manage')

Sistema de Permisos:
- Público: Envío de mensajes
- Usuarios internos: Según permisos granulares PBAC ('contact.view', 'contact.manage')
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging

from core.config import settings, TURNSTILE_SECRET_KEY
from utils.email_utils import send_email_background
from db.base import User
from dependencies import get_db, require_permission
from crud.crud_contact_client import get_contact_messages, create_contact_message, get_contact_message, update_contact_status, delete_contact_message
from schemas.contact_client import ContactMessageCreate, ContactMessageUpdateStatus
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

class ContactMessage(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(None, max_length=30)
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)

# ==========================================
# ENDPOINTS: MENSAJES DE CONTACTO
# ==========================================

""" GET /admin/all - Obtener lista de mensajes con filtros y búsqueda """
@router.get("/admin/all")
def api_get_contact_messages(
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"), 
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contact.view"))
):
    messages = get_contact_messages(db, skip=skip, limit=limit, search=search, status=status_filter)
    return messages

""" POST /send - Enviar mensaje de contacto y guardar en base de datos """
@router.post("/send")
def send_contact_email(
    contact: ContactMessage, 
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    
    # Validar Cloudflare Turnstile
    if TURNSTILE_SECRET_KEY:
        captcha_token = request.headers.get("X-Turnstile-Token", "")
        
        if not captcha_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verificación CAPTCHA requerida"
            )
        
        try:
            response = httpx.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": TURNSTILE_SECRET_KEY,
                    "response": captcha_token
                },
                timeout=10.0
            )
            
            # Si Cloudflare responde un error 500 o rate limit, dejamos pasar
            if response.status_code != 200:
                logger.warning(f"Turnstile API falló en contacto con status {response.status_code}. Permitiendo envío por fallback.")
                pass
            else:
                result = response.json()
                if not result.get("success"):
                    logger.warning(f"Turnstile rechazó el token de contacto: {result.get('error-codes')}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Verificación CAPTCHA fallida. Intenta de nuevo."
                    )
        except httpx.RequestError as e:
            # Si Turnstile está caído/timeout, dejamos que el formulario pase
            logger.warning(f"Error de red contactando Turnstile en contacto: {str(e)}. Permitiendo envío por fallback.")
            pass
    
    try:
        # === GUARDAR EN BASE DE DATOS SQL ===
        message_data = ContactMessageCreate(
            full_name=contact.name,
            email=contact.email,
            phone=contact.phone or "",
            subject=contact.subject,
            message=contact.message
        )
        create_contact_message(db, message_data)

        # === CREAR CUERPO HTML ESPECÍFICO DE CONTACTO ===
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
              <h2 style="color: #63c1a5; border-bottom: 2px solid #63c1a5; padding-bottom: 10px;">
                Nuevo Mensaje de Contacto
              </h2>
              
              <div style="margin: 20px 0;">
                <p><strong>Nombre:</strong> {contact.name}</p>
                <p><strong>Email:</strong> <a href="mailto:{contact.email}">{contact.email}</a></p>
                {f'<p><strong>Teléfono:</strong> {contact.phone}</p>' if contact.phone else ''}
                <p><strong>Asunto:</strong> {contact.subject}</p>
              </div>
              
              <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #555;">Mensaje:</h3>
                <p style="white-space: pre-wrap;">{contact.message}</p>
              </div>
              
              <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
              
              <p style="font-size: 12px; color: #888;">
                Este mensaje fue enviado desde el formulario de contacto de Profarmed.
              </p>
            </div>
          </body>
        </html>
        """
        
        # logger.info(f"Encolando envío de email de contacto de {contact.name} ({contact.email})")
        
        # Enviar email de forma asíncrona real con BackgroundTasks
        # background_tasks.add_task(
        #     send_email_background,
        #     to_email=settings.CONTACT_EMAIL,
        #     subject=f"Contacto Web: {contact.subject}",
        #     html_body=html_body,
        #     reply_to=contact.email
        # )
        
        # logger.info(f"Email encolado para {settings.CONTACT_EMAIL}")
        
        return {"message": "Mensaje guardado exitosamente"}
        
    except Exception as e:
        logger.error(f"Error procesando contacto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el mensaje: {str(e)}"
        )

""" PATCH /{message_id} - Actualizar estado de seguimiento del mensaje """
@router.patch("/{message_id}")
def api_update_contact_status(
    message_id: int,
    status_update: ContactMessageUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contact.manage"))
):
    db_obj = get_contact_message(db, message_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return update_contact_status(db, db_obj, status_update)

""" DELETE /{message_id} - Eliminar permanentemente un mensaje de contacto """
@router.delete("/{message_id}")
def api_delete_contact_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("contact.manage"))
):
    db_obj = get_contact_message(db, message_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    delete_contact_message(db, db_obj)
    return {"message": "Mensaje eliminado exitosamente"}
