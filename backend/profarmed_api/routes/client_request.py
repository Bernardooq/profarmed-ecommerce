"""
Routes para Solicitudes "Quiero ser cliente" (Client Requests)

Gestión completa de las solicitudes de nuevos clientes con sus documentos en S3.

SOLICITUDES:
- GET /admin/all - Obtener lista de solicitudes (requiere 'customers.requests_view')
- POST / - Crear nueva solicitud con validación y subida de archivos PDF a S3 (Público)
- GET /admin/{request_id}/download/{doc_type} - Generar descarga temporal de un documento PDF (requiere 'customers.requests_download')
- PATCH /admin/{request_id}/status - Actualizar estado de una solicitud (requiere 'customers.requests_manage')
- DELETE /admin/{request_id} - Eliminar solicitud y sus archivos de S3 (requiere 'customers.requests_manage')

Sistema de Permisos:
- Público: Envío de solicitudes
- Usuarios internos: Según permisos granulares PBAC ('customers.requests_view', 'customers.requests_download', 'customers.requests_manage')
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
import logging
import httpx
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

from core.config import settings, TURNSTILE_SECRET_KEY
from utils.email_utils import send_email_background
from db.base import User
from dependencies import get_db, require_permission
from schemas.contact_client import ClientRequestCreate, ClientRequestUpdateStatus
from crud.crud_contact_client import create_client_request, get_client_request, get_client_requests, update_client_request_status, delete_client_request
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

""" GET /admin/all - Obtener lista de solicitudes con filtros y búsqueda """
@router.get("/admin/all")
def api_get_client_requests(
    skip: int = Query(0, ge=0, description="Registros a saltar"), 
    limit: int = Query(100, ge=1, le=200, description="Límite de registros"), 
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.requests_view"))
):
    requests = get_client_requests(db, skip=skip, limit=limit, search=search, status=status)
    return requests

# Initialize boto3 S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

""" UTILIDAD - Generar una URL prefirmada de S3 para descarga temporal de documentos """
def generate_presigned_url(object_name: str, expiration: int = 300, filename: Optional[str] = None):
    try:
        params = {'Bucket': settings.BUCKET_DOCS, 'Key': object_name}
        if filename:
            params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
            
        response = s3_client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=expiration
        )
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        return None
    return response

""" POST / - Crear una nueva solicitud con validación y subida de PDFs a S3 """
@router.post("/")
def api_create_client_request(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    subject: str = Form(...),
    message: Optional[str] = Form("", max_length=500),
    id_pdf: UploadFile = File(...),
    sanitary_license_pdf: UploadFile = File(...),
    proof_of_address_pdf: UploadFile = File(...),
    tax_cert_pdf: UploadFile = File(...),
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

            if response.status_code != 200:
                logger.warning(f"Turnstile API falló en client_request con status {response.status_code}. Permitiendo envío por fallback.")
            else:
                result = response.json()
                if not result.get("success"):
                    logger.warning(f"Turnstile rechazó el token de client_request: {result.get('error-codes')}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Verificación CAPTCHA fallida. Intenta de nuevo."
                    )
        except httpx.RequestError as e:
            logger.warning(f"Error de red contactando Turnstile en client_request: {str(e)}. Permitiendo envío por fallback.")
    
    files = {
        "id_pdf_key": id_pdf,
        "sanitary_license_pdf_key": sanitary_license_pdf,
        "proof_of_address_pdf_key": proof_of_address_pdf,
        "tax_cert_pdf_key": tax_cert_pdf
    }
    
    # Validation (PDF format and maximum 5MB size limit)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Megabytes
    for key, file in files.items():
        # 1. Validar formato PDF
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"El archivo {file.filename} debe ser formato PDF.")
            
        # 2. Validar tamaño del archivo leyendo temporalmente los bytes
        try:
            file.file.seek(0, 2)  # Mover puntero al final del archivo
            file_size = file.file.tell()  # Obtener tamaño del archivo
            file.file.seek(0)  # Devolver puntero al inicio
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"El archivo {file.filename} supera el tamaño límite permitido de 5 MB."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error midiendo tamaño de archivo {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno al validar el archivo.")
            
    # Upload to S3 (with dynamic collision detection and auto-incrementing suffixes)
    file_keys = {}
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    for key, file in files.items():
        base_s3_key = f"clients/{email}/{timestamp}_{key}"
        s3_key = f"{base_s3_key}.pdf"
        
        # Comprobar colisiones de archivos y aplicar sufijo incremental (_1, _2, ...)
        counter = 1
        while True:
            try:
                # Comprobar si el archivo ya existe en S3
                s3_client.head_object(Bucket=settings.BUCKET_DOCS, Key=s3_key)
                # Si no arrojó ClientError (404), significa que sí existe. Incrementamos sufijo:
                s3_key = f"{base_s3_key}_{counter}.pdf"
                counter += 1
            except ClientError as e:
                # Si da un error 404 de AWS, el objeto no existe. La ruta es libre para subir.
                error_code = e.response.get('Error', {}).get('Code')
                if error_code in ['404', 'NoSuchKey']:
                    break
                else:
                    logger.error(f"Error checking S3 key collision: {str(e)}")
                    raise HTTPException(status_code=500, detail="Error de verificación de almacenamiento S3.")

        try:
            file.file.seek(0)  # Asegurar que el puntero esté al inicio antes de subir
            s3_client.upload_fileobj(file.file, settings.BUCKET_DOCS, s3_key)
            file_keys[key] = s3_key
        except ClientError as e:
            logger.error(f"Failed to upload {file.filename} to S3: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Fallo al subir el archivo {file.filename} a S3.")
            
    # Usar string vacío si no hay mensaje (la columna es NOT NULL)
    db_message = message.strip() if message else ""
    
    # Save to DB
    client_request_data = ClientRequestCreate(
        full_name=full_name, email=email, phone=phone, 
        subject=subject, message=db_message
    )
    create_client_request(db, client_request_data, file_keys)
    
    # Send Notification Email
    html_body = f"""
    <html>
      <body>
        <h2>Nueva Solicitud de Cliente</h2>
        <p><strong>Nombre:</strong> {full_name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Asunto:</strong> {subject}</p>
        <p><strong>Mensaje:</strong> {message}</p>
      </body>
    </html>
    """
    
    # background_tasks.add_task(
    #     send_email_background,
    #     to_email=settings.CONTACT_EMAIL,
    #     subject=f"Solicitud de Cliente: {subject}",
    #     html_body=html_body,
    #     reply_to=email
    # )
    
    return {"message": "Solicitud enviada exitosamente."}

""" GET /admin/{request_id}/download/{doc_type} - Descargar un documento de solicitud del cliente """
@router.get("/admin/{request_id}/download/{doc_type}")
def download_client_doc(
    request_id: int, 
    doc_type: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.requests_download"))
):
    req = get_client_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    key_map = {
        "id": req.id_pdf_key,
        "sanitary": req.sanitary_license_pdf_key,
        "address": req.proof_of_address_pdf_key,
        "tax": req.tax_cert_pdf_key
    }
    
    if doc_type not in key_map:
        raise HTTPException(status_code=400, detail="Invalid document type")
        
    clean_name = "".join(c for c in req.full_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    filename_map = {
        "id": f"Identificacion_Oficial_{clean_name}.pdf",
        "sanitary": f"Aviso_Funcionamiento_{clean_name}.pdf",
        "address": f"Comprobante_Domicilio_{clean_name}.pdf",
        "tax": f"Constancia_Situacion_Fiscal_{clean_name}.pdf"
    }
    filename = filename_map.get(doc_type)
        
    url = generate_presigned_url(key_map[doc_type], expiration=300, filename=filename)
    if not url:
        raise HTTPException(status_code=500, detail="Could not generate presigned URL")
        
    return {"download_url": url}

""" DELETE /admin/{request_id} - Eliminar permanentemente una solicitud y sus archivos de S3 """
@router.delete("/admin/{request_id}")
def api_delete_client_request(
    request_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.requests_manage"))
):
    req = get_client_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    # Delete from S3
    keys_to_delete = [
        {'Key': req.id_pdf_key}, 
        {'Key': req.sanitary_license_pdf_key}, 
        {'Key': req.proof_of_address_pdf_key}, 
        {'Key': req.tax_cert_pdf_key}
    ]
    try:
        s3_client.delete_objects(Bucket=settings.BUCKET_DOCS, Delete={'Objects': keys_to_delete})
    except ClientError as e:
        logger.error(f"Failed to delete S3 objects for request {request_id}: {str(e)}")
        # Continue with DB deletion even if S3 fails or is partially successful
        
    delete_client_request(db, req)
    return {"message": "Client request and associated documents deleted"}

""" PATCH /admin/{request_id}/status - Actualizar estado de una solicitud """
@router.patch("/admin/{request_id}/status")
def api_update_client_request_status(
    request_id: int,
    status_update: ClientRequestUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customers.requests_manage"))
):
    db_obj = get_client_request(db, request_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return update_client_request_status(db, db_obj, status_update.status)
