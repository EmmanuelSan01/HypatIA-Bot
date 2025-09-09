from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class PromocionBase(BaseModel):
    descripcion: str
    descuentoPorcentaje: int = Field(..., ge=0, le=100)
    fechaInicio: date
    fechaFin: date

class PromocionCreate(PromocionBase):
    pass

class PromocionUpdate(BaseModel):
    descripcion: Optional[str] = None
    descuentoPorcentaje: Optional[int] = Field(None, ge=0, le=100)
    fechaInicio: Optional[date] = None
    fechaFin: Optional[date] = None

class PromocionResponse(PromocionBase):
    id: int
    
    class Config:
        from_attributes = True