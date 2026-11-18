"""
CRUD y Gestión de Mensajes de Contacto y Solicitudes de Nuevos Clientes:

Funciones y Operaciones:
- SECCIÓN 1: Mensajes de Contacto General ("Contáctanos"):
  - Crear registros de dudas o peticiones de información.
  - Consultar mensajes paginados con filtros por estado (`pending`, `in_review`, `resolved`).
  - Actualizar estado administrativo y eliminar mensajes resueltos.
- SECCIÓN 2: Solicitudes de Alta de Cliente ("Quiero ser cliente"):
  - Registro de prospectos comerciales incluyendo datos fiscales y de entrega.
  - Almacenamiento y vinculación de archivos PDF adjuntos (Constancia de Situación Fiscal, comprobantes de domicilio).
  - Consulta paginada, actualización de estatus y eliminación de solicitudes.

Reglas de Negocio y Permisos (PBAC / RBAC Dinámico):
1. Flujo de Prospectos:
   - Las solicitudes públicas se registran inicialmente en estado pendiente (`pending`) sin requerir autenticación previa.
   - La revisión, actualización de estado y aprobación se realiza por colaboradores con permisos granulares de gestión de clientes (`customers.requests_view`, `customers.requests_manage`) o rol `admin`, procediendo al alta de `Customer` en `crud_customer.py`.
2. Gestión Documental:
   - Las llaves de almacenamiento para archivos PDF se validan y registran para descarga segura y auditoría documental.
"""

from sqlalchemy.orm import Session
from db.base import ContactMessageModel, ClientRequestModel
from schemas.contact_client import ContactMessageCreate, ContactMessageUpdateStatus, ClientRequestCreate
from typing import Optional, List
from sqlalchemy import or_

# ==========================================
# SECCIÓN 1: MENSAJES DE CONTACTO
# ==========================================

"""Crea un nuevo mensaje de contacto y lo guarda en la base de datos"""
def create_contact_message(db: Session, message: ContactMessageCreate) -> ContactMessageModel:
    db_obj = ContactMessageModel(**message.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

"""Obtiene un mensaje de contacto específico por su ID"""
def get_contact_message(db: Session, message_id: int) -> Optional[ContactMessageModel]:
    return db.query(ContactMessageModel).filter(ContactMessageModel.id == message_id).first()

"""Obtiene una lista de mensajes de contacto con paginación, filtro de estado y búsqueda por palabras clave"""
def get_contact_messages(db: Session, skip: int = 0, limit: int = 10, search: Optional[str] = None, status: Optional[str] = None) -> List[ContactMessageModel]:
    query = db.query(ContactMessageModel)
    if status:
        query = query.filter(ContactMessageModel.status == status)
    if search:
        query = query.filter(or_(
            ContactMessageModel.full_name.ilike(f"%{search}%"),
            ContactMessageModel.email.ilike(f"%{search}%"),
            ContactMessageModel.subject.ilike(f"%{search}%")
        ))
    return query.order_by(ContactMessageModel.created_at.desc()).offset(skip).limit(limit).all()

"""Actualiza el estado de un mensaje de contacto (ej. de 'pending' a 'contacted')"""
def update_contact_status(db: Session, db_obj: ContactMessageModel, status_update: ContactMessageUpdateStatus) -> ContactMessageModel:
    db_obj.status = status_update.status
    db.commit()
    db.refresh(db_obj)
    return db_obj

"""Elimina permanentemente un mensaje de contacto de la base de datos"""
def delete_contact_message(db: Session, db_obj: ContactMessageModel) -> None:
    db.delete(db_obj)
    db.commit()


# ==========================================
# SECCIÓN 2: SOLICITUDES "QUIERO SER CLIENTE"
# ==========================================

"""Crea una nueva solicitud de cliente y asocia las llaves (keys) de los PDFs en S3"""
def create_client_request(db: Session, request: ClientRequestCreate, file_keys: dict) -> ClientRequestModel:
    db_obj = ClientRequestModel(
        **request.model_dump(),
        id_pdf_key=file_keys.get("id_pdf_key"),
        sanitary_license_pdf_key=file_keys.get("sanitary_license_pdf_key"),
        proof_of_address_pdf_key=file_keys.get("proof_of_address_pdf_key"),
        tax_cert_pdf_key=file_keys.get("tax_cert_pdf_key")
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

"""Obtiene una solicitud de cliente específica por su ID"""
def get_client_request(db: Session, request_id: int) -> Optional[ClientRequestModel]:
    return db.query(ClientRequestModel).filter(ClientRequestModel.id == request_id).first()

"""Obtiene una lista de solicitudes de cliente con paginación, filtro de estado y búsqueda por palabras clave"""
def get_client_requests(db: Session, skip: int = 0, limit: int = 10, search: Optional[str] = None, status: Optional[str] = None) -> List[ClientRequestModel]:
    query = db.query(ClientRequestModel)
    if status:
        query = query.filter(ClientRequestModel.status == status)
    if search:
        query = query.filter(or_(
            ClientRequestModel.full_name.ilike(f"%{search}%"),
            ClientRequestModel.email.ilike(f"%{search}%"),
            ClientRequestModel.subject.ilike(f"%{search}%")
        ))
    return query.order_by(ClientRequestModel.created_at.desc()).offset(skip).limit(limit).all()

"""Actualiza el estado de la solicitud de cliente (ej. 'pending', 'approved', 'rejected')"""
def update_client_request_status(db: Session, db_obj: ClientRequestModel, status: str) -> ClientRequestModel:
    db_obj.status = status
    db.commit()
    db.refresh(db_obj)
    return db_obj

"""Elimina permanentemente una solicitud de cliente de la base de datos"""
def delete_client_request(db: Session, db_obj: ClientRequestModel) -> None:
    db.delete(db_obj)
    db.commit()
