from fastapi import APIRouter, HTTPException, status
from typing import List
from app.controllers.promocionCurso.PromocionCursoController import PromocionCursoController
from app.models.promocionCurso.PromocionCursoModel import PromocionCursoCreate, PromocionCursoResponse

router = APIRouter(prefix="/promocion-cursos", tags=["promocion-cursos"])

@router.post("/", response_model=PromocionCursoResponse, status_code=status.HTTP_201_CREATED)
def create_promocion_curso(promocion_curso: PromocionCursoCreate):
    """Create a new promocion-curso association"""
    try:
        return PromocionCursoController.create_promocion_curso(promocion_curso)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[PromocionCursoResponse])
def get_all_promocion_cursos():
    """Get all promocion-curso associations"""
    return PromocionCursoController.get_all_promocion_cursos()

@router.get("/{promocion_curso_id}", response_model=PromocionCursoResponse)
def get_promocion_curso(promocion_curso_id: int):
    """Get promocion-curso by ID"""
    promocion_curso = PromocionCursoController.get_promocion_curso_by_id(promocion_curso_id)
    if not promocion_curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promocion-Curso association not found")
    return promocion_curso

@router.get("/promocion/{promocion_id}", response_model=List[PromocionCursoResponse])
def get_cursos_by_promocion(promocion_id: int):
    """Get cursos by promocion"""
    return PromocionCursoController.get_cursos_by_promocion(promocion_id)

@router.get("/curso/{curso_id}", response_model=List[PromocionCursoResponse])
def get_promociones_by_curso(curso_id: int):
    """Get promociones by curso"""
    return PromocionCursoController.get_promociones_by_curso(curso_id)

@router.delete("/{promocion_curso_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promocion_curso(promocion_curso_id: int):
    """Delete promocion-curso association"""
    if not PromocionCursoController.delete_promocion_curso(promocion_curso_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promocion-Curso association not found")

@router.delete("/curso/{curso_id}/promocion/{promocion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promocion_curso_by_ids(curso_id: int, promocion_id: int):
    """Delete promocion-curso association by curso and promocion IDs"""
    if not PromocionCursoController.delete_promocion_curso_by_ids(curso_id, promocion_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promocion-Curso association not found")
