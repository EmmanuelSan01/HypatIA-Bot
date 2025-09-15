from pydantic import BaseModel
from typing import Optional

class PromocionCursoBase(BaseModel):
    cursoId: int
    promocionId: int

class PromocionCursoCreate(PromocionCursoBase):
    pass

class PromocionCursoUpdate(BaseModel):
    cursoId: Optional[int] = None
    promocionId: Optional[int] = None

class PromocionCursoResponse(PromocionCursoBase):
    id: int
    
    class Config:
        from_attributes = True
