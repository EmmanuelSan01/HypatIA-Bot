from typing import List, Optional
import pymysql
from app.database import get_sync_connection
from app.models.promocionCurso.PromocionCursoModel import PromocionCursoCreate, PromocionCursoUpdate, PromocionCursoResponse

class PromocionCursoController:
    
    @staticmethod
    def create_promocion_curso(promocion_curso: PromocionCursoCreate) -> PromocionCursoResponse:
        """Create a new promocion-curso association"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO promocionCurso (cursoId, promocionId) 
                VALUES (%s, %s)
                """
                cursor.execute(sql, (promocion_curso.cursoId, promocion_curso.promocionId))
                connection.commit()
                
                promocion_curso_id = cursor.lastrowid
                return PromocionCursoController.get_promocion_curso_by_id(promocion_curso_id)
        finally:
            connection.close()
    
    @staticmethod
    def get_all_promocion_cursos() -> List[PromocionCursoResponse]:
        """Get all promocion-curso associations"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM promocionCurso"
                cursor.execute(sql)
                result = cursor.fetchall()
                return [PromocionCursoResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def get_promocion_curso_by_id(promocion_curso_id: int) -> Optional[PromocionCursoResponse]:
        """Get promocion-curso by ID"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM promocionCurso WHERE id = %s"
                cursor.execute(sql, (promocion_curso_id,))
                result = cursor.fetchone()
                return PromocionCursoResponse(**result) if result else None
        finally:
            connection.close()
    
    @staticmethod
    def get_cursos_by_promocion(promocion_id: int) -> List[PromocionCursoResponse]:
        """Get cursos by promocion"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM promocionCurso WHERE promocionId = %s"
                cursor.execute(sql, (promocion_id,))
                result = cursor.fetchall()
                return [PromocionCursoResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def get_promociones_by_curso(curso_id: int) -> List[PromocionCursoResponse]:
        """Get promociones by curso"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM promocionCurso WHERE cursoId = %s"
                cursor.execute(sql, (curso_id,))
                result = cursor.fetchall()
                return [PromocionCursoResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def delete_promocion_curso(promocion_curso_id: int) -> bool:
        """Delete promocion-curso association"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "DELETE FROM promocionCurso WHERE id = %s"
                cursor.execute(sql, (promocion_curso_id,))
                connection.commit()
                return cursor.rowcount > 0
        finally:
            connection.close()
    
    @staticmethod
    def delete_promocion_curso_by_ids(curso_id: int, promocion_id: int) -> bool:
        """Delete promocion-curso association by curso and promocion IDs"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "DELETE FROM promocionCurso WHERE cursoId = %s AND promocionId = %s"
                cursor.execute(sql, (curso_id, promocion_id))
                connection.commit()
                return cursor.rowcount > 0
        finally:
            connection.close()
