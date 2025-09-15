from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum

class NivelEnum(str, Enum):
    PRINCIPIANTE = "Principiante"
    INTERMEDIO = "Intermedio"

class IdiomaEnum(str, Enum):
    INGLES = "Inglés"
    ESPANOL = "Español"

class CursoBase(BaseModel):
    categoriaId: int
    titulo: str
    descripcion: Optional[str] = None
    nivel: NivelEnum = NivelEnum.PRINCIPIANTE
    idioma: IdiomaEnum = IdiomaEnum.INGLES
    precio: Decimal = Field(..., ge=0)
    cupo: int = Field(default=0, ge=0)

class CursoCreate(CursoBase):
    pass

class CursoUpdate(BaseModel):
    categoriaId: Optional[int] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    nivel: Optional[NivelEnum] = None
    idioma: Optional[IdiomaEnum] = None
    precio: Optional[Decimal] = Field(None, ge=0)
    cupo: Optional[int] = Field(None, ge=0)

class CursoResponse(CursoBase):
    id: int
    fechaCreacion: datetime
    fechaActualizacion: datetime
    
    class Config:
        from_attributes = True
