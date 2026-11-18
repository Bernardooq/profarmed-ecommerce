"""
Routes de Restablecimiento de Contraseñas (Password Reset OTP):

Endpoints Públicos (sin requerir token de autenticación previa):
- POST /request-code - Solicitar código OTP de 6 dígitos por correo (Customer o User)
- POST /send-code - Alias retrocompatible de solicitud de código
- POST /resend-code - Generar y reenviar un nuevo código si no llegó el anterior
- POST /verify-code - Validar código ingresado y habilitar 'allow' = True
- POST /confirm - Establecer la nueva contraseña si 'allow' es True y dentro de los 5 minutos
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from dependencies import get_db
from schemas.user import (
    PasswordResetRequest, 
    PasswordResetVerify, 
    PasswordResetConfirm, 
    PasswordResetResponse
)
from crud.crud_password_reset import (
    request_password_reset_code,
    verify_password_reset_code,
    confirm_password_reset
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/request-code", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
@router.post("/send-code", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
def send_reset_code(
    payload: PasswordResetRequest, 
    db: Session = Depends(get_db)
):
    """
    Genera un código OTP de 6 dígitos con vigencia de 5 minutos y lo envía a la(s)
    dirección(es) de correo asociadas a la cuenta. Muestra los correos enmascarados.
    """
    success, msg, masked_emails, expires_in = request_password_reset_code(db, payload.username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return PasswordResetResponse(
        message=msg,
        masked_emails=masked_emails,
        expires_in_seconds=expires_in,
        valid=None
    )


@router.post("/resend-code", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
def resend_reset_code(
    payload: PasswordResetRequest, 
    db: Session = Depends(get_db)
):
    """
    Genera forzosamente un nuevo código de 6 dígitos y refresca la ventana de 5 minutos.
    """
    success, msg, masked_emails, expires_in = request_password_reset_code(db, payload.username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return PasswordResetResponse(
        message=f"Se ha reenviado un nuevo código a: {masked_emails}",
        masked_emails=masked_emails,
        expires_in_seconds=expires_in,
        valid=None
    )


@router.post("/verify-code", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
def verify_code(
    payload: PasswordResetVerify, 
    db: Session = Depends(get_db)
):
    """
    Verifica que el código de 6 dígitos coincida con el almacenado y esté vigente (< 5 min).
    Si es correcto, autoriza la cuenta marcando allow = True.
    """
    success, msg = verify_password_reset_code(db, payload.username, payload.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return PasswordResetResponse(
        message=msg,
        masked_emails=None,
        expires_in_seconds=None,
        valid=True
    )


@router.post("/confirm", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
@router.post("/reset-password", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK)
def reset_password(
    payload: PasswordResetConfirm, 
    db: Session = Depends(get_db)
):
    """
    Cambia definitivamente la contraseña del usuario tras validar código y 'allow' == True.
    """
    success, msg = confirm_password_reset(db, payload.username, payload.code, payload.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return PasswordResetResponse(
        message=msg,
        masked_emails=None,
        expires_in_seconds=None,
        valid=True
    )
