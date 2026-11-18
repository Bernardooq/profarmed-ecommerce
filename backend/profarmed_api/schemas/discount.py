from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, model_validator, field_validator


class ProductDiscountBase(BaseModel):
    product_id: str = Field(..., max_length=50, description="ID del producto (ej: FAR74)")
    price_list_id: Optional[int] = Field(None, description="ID de lista de precios. NULL si es descuento general a la base")
    discount_percentage: Decimal = Field(..., gt=Decimal("0.00"), le=Decimal("100.00"), description="Porcentaje de descuento (0.01 a 100.00)")
    start_date: datetime = Field(..., description="Fecha y hora de inicio de vigencia")
    end_date: datetime = Field(..., description="Fecha y hora de expiración de vigencia")
    is_active: bool = Field(True, description="Estado activo/pausado del descuento")
    description: Optional[str] = Field(None, max_length=255, description="Motivo o etiqueta de la promoción")

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_start_date(cls, v):
        if isinstance(v, str) and len(v.strip()) == 10:
            return f"{v.strip()}T00:00:00"
        return v

    @field_validator("end_date", mode="before")
    @classmethod
    def parse_end_date(cls, v):
        if isinstance(v, str) and len(v.strip()) == 10:
            return f"{v.strip()}T23:59:59"
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("start_date debe ser estrictamente anterior a end_date")
        return self


class ProductDiscountCreate(ProductDiscountBase):
    pass


class ProductDiscountUpdate(BaseModel):
    product_id: Optional[str] = Field(None, max_length=50)
    price_list_id: Optional[int] = None
    discount_percentage: Optional[Decimal] = Field(None, gt=Decimal("0.00"), le=Decimal("100.00"))
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_start_date(cls, v):
        if isinstance(v, str) and len(v.strip()) == 10:
            return f"{v.strip()}T00:00:00"
        return v

    @field_validator("end_date", mode="before")
    @classmethod
    def parse_end_date(cls, v):
        if isinstance(v, str) and len(v.strip()) == 10:
            return f"{v.strip()}T23:59:59"
        return v

    @model_validator(mode="after")
    def validate_dates_if_both(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("start_date debe ser estrictamente anterior a end_date")
        return self


class ProductDiscountResponse(BaseModel):
    discount_id: UUID
    product_id: str
    price_list_id: Optional[int] = None
    discount_percentage: Decimal
    start_date: datetime
    end_date: datetime
    is_active: bool
    description: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    # Campos enriquecidos para la UI
    product_name: Optional[str] = None
    price_list_name: Optional[str] = None
    created_by_name: Optional[str] = None
    is_current: bool = False
    discount_scope: str = "general"

    # Previews de precio
    base_price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    discounted_price: Optional[Decimal] = None
    final_price_with_iva: Optional[Decimal] = None
    iva_percentage: Optional[Decimal] = None
    markup_percentage: Optional[Decimal] = None

    class Config:
        from_attributes = True


class ActiveDiscountInfo(BaseModel):
    has_discount: bool = False
    discount_type: str = "none"
    discount_percentage: Decimal = Decimal("0.00")
    discount_id: Optional[UUID] = None
    description: Optional[str] = None
