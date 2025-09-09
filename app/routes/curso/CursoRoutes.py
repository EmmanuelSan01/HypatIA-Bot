from fastapi import APIRouter, HTTPException, status
from typing import List
from app.controllers.curso.CursoController import CursoController
from app.models.curso.CursoModel import CursoCreate, CursoUpdate, CursoResponse

router = APIRouter(prefix="/cursos", tags=["cursos"])

@router.post("/", response_model=CursoResponse, status_code=status.HTTP_201_CREATED)
def create_curso(curso: CursoCreate):
    """Create a new curso"""
    try:
        return CursoController.create_curso(curso)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[CursoResponse])
def get_all_cursos():
    """Get all cursos"""
    return CursoController.get_all_cursos()

@router.get("/{curso_id}", response_model=CursoResponse)
def get_curso(curso_id: int):
    """Get curso by ID"""
    curso = CursoController.get_curso_by_id(curso_id)
    if not curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso not found")
    return curso

@router.get("/categoria/{categoria_id}", response_model=List[CursoResponse])
def get_cursos_by_categoria(categoria_id: int):
    """Get cursos by categoria"""
    return CursoController.get_cursos_by_categoria(categoria_id)

@router.get("/nivel/{nivel}", response_model=List[CursoResponse])
def get_cursos_by_nivel(nivel: str):
    """Get cursos by nivel"""
    return CursoController.get_cursos_by_nivel(nivel)

@router.get("/idioma/{idioma}", response_model=List[CursoResponse])
def get_cursos_by_idioma(idioma: str):
    """Get cursos by idioma"""
    return CursoController.get_cursos_by_idioma(idioma)

@router.put("/{curso_id}", response_model=CursoResponse)
def update_curso(curso_id: int, curso: CursoUpdate):
    """Update curso"""
    updated_curso = CursoController.update_curso(curso_id, curso)
    if not updated_curso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso not found")
    return updated_curso

@router.delete("/{curso_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_curso(curso_id: int):
    """Delete curso"""
    if not CursoController.delete_curso(curso_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso not found")
