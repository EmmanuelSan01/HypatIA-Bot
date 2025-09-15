from typing import List, Optional
import pymysql
from app.database import get_sync_connection
from app.models.curso.CursoModel import CursoCreate, CursoUpdate, CursoResponse

class CursoController:
    
    @staticmethod
    def create_curso(curso: CursoCreate) -> CursoResponse:
        """Create a new curso"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO curso (categoriaId, titulo, descripcion, nivel, idioma, precio, cupo) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    curso.categoriaId, curso.titulo, curso.descripcion,
                    curso.nivel.value, curso.idioma.value, curso.precio, curso.cupo
                ))
                connection.commit()
                
                curso_id = cursor.lastrowid
                return CursoController.get_curso_by_id(curso_id)
        finally:
            connection.close()
    
    @staticmethod
    def get_all_cursos() -> List[CursoResponse]:
        """Get all cursos"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM curso ORDER BY fechaCreacion DESC"
                cursor.execute(sql)
                result = cursor.fetchall()
                return [CursoResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def get_curso_by_id(curso_id: int) -> Optional[CursoResponse]:
        """Get curso by ID"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM curso WHERE id = %s"
                cursor.execute(sql, (curso_id,))
                result = cursor.fetchone()
                return CursoResponse(**result) if result else None
        finally:
            connection.close()
    
    @staticmethod
    def get_cursos_by_categoria(categoria_id: int) -> List[CursoResponse]:
        """Get cursos by categoria"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM curso WHERE categoriaId = %s ORDER BY fechaCreacion DESC"
                cursor.execute(sql, (categoria_id,))
                result = cursor.fetchall()
                return [CursoResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def get_cursos_by_nivel(nivel: str) -> List[CursoResponse]:
        """Get cursos by nivel"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM curso WHERE nivel = %s ORDER BY fechaCreacion DESC"
                cursor.execute(sql, (nivel,))
                result = cursor.fetchall()
                return [CursoResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def get_cursos_by_idioma(idioma: str) -> List[CursoResponse]:
        """Get cursos by idioma"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM curso WHERE idioma = %s ORDER BY fechaCreacion DESC"
                cursor.execute(sql, (idioma,))
                result = cursor.fetchall()
                return [CursoResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def update_curso(curso_id: int, curso: CursoUpdate) -> Optional[CursoResponse]:
        """Update curso"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                update_fields = []
                values = []
                
                if curso.categoriaId is not None:
                    update_fields.append("categoriaId = %s")
                    values.append(curso.categoriaId)
                
                if curso.titulo is not None:
                    update_fields.append("titulo = %s")
                    values.append(curso.titulo)
                
                if curso.descripcion is not None:
                    update_fields.append("descripcion = %s")
                    values.append(curso.descripcion)
                
                if curso.nivel is not None:
                    update_fields.append("nivel = %s")
                    values.append(curso.nivel.value)
                
                if curso.idioma is not None:
                    update_fields.append("idioma = %s")
                    values.append(curso.idioma.value)
                
                if curso.precio is not None:
                    update_fields.append("precio = %s")
                    values.append(curso.precio)
                
                if curso.cupo is not None:
                    update_fields.append("cupo = %s")
                    values.append(curso.cupo)
                
                if not update_fields:
                    return CursoController.get_curso_by_id(curso_id)
                
                values.append(curso_id)
                sql = f"UPDATE curso SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(sql, values)
                connection.commit()
                
                return CursoController.get_curso_by_id(curso_id)
        finally:
            connection.close()
    
    @staticmethod
    def delete_curso(curso_id: int) -> bool:
        """Delete curso"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "DELETE FROM curso WHERE id = %s"
                cursor.execute(sql, (curso_id,))
                connection.commit()
                return cursor.rowcount > 0
        finally:
            connection.close()
