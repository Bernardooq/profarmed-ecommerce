from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class ContactMessageCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    email: EmailStr
    phone: str = Field(..., max_length=30)
    subject: str = Field(..., max_length=200)
    message: Optional[str] = Field(None, max_length=500)

class ContactMessageUpdateStatus(BaseModel):
    status: str = Field(..., pattern="^(pending|contacted)$")

class ContactMessageResponse(ContactMessageCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClientRequestCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    email: EmailStr
    phone: str = Field(..., max_length=30)
    subject: str = Field(..., max_length=200)
    message: Optional[str] = Field(None, max_length=500)

class ClientRequestUpdateStatus(BaseModel):
    status: str = Field(..., pattern="^(pending|approved|rejected)$")

class ClientRequestResponse(ClientRequestCreate):
    id: int
    status: str
    id_pdf_key: str
    sanitary_license_pdf_key: str
    proof_of_address_pdf_key: str
    tax_cert_pdf_key: str
    created_at: datetime

    class Config:
        from_attributes = True
