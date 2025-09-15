from typing import List, Dict, Optional
import asyncio
from datetime import datetime
from app.database import get_sync_connection
from app.services.qdrant import QdrantService
from app.services.embedding import EmbeddingService
import logging

logger = logging.getLogger(__name__)

class DataSyncService:
    """Service for synchronizing MySQL data with Qdrant vector database"""
    
    def __init__(self):
        self.qdrant_service = QdrantService()
        self.embedding_service = EmbeddingService()
    
    async def sync_all_data(self) -> Dict:
        """Perform complete data synchronization from MySQL to Qdrant"""
        try:
            logger.info("Starting complete data synchronization")
            
            # Initialize Qdrant collection if not exists
            self.qdrant_service.create_collection_if_not_exists()
            
            # Sync all data types
            cursos_count = await self._sync_cursos()
            categorias_count = await self._sync_categorias()
            promociones_count = await self._sync_promociones()
            
            total_synced = cursos_count + categorias_count + promociones_count
            
            logger.info(f"Synchronization completed. Total documents: {total_synced}")
            
            return {
                "status": "success",
                "message": "Sincronización completa exitosa",
                "synced_count": total_synced,
                "details": {
                    "cursos": cursos_count,
                    "categorias": categorias_count,
                    "promociones": promociones_count
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during synchronization: {str(e)}")
            return {
                "status": "error",
                "message": f"Error en sincronización: {str(e)}",
                "synced_count": 0,
                "errors": [str(e)]
            }
    
    async def sync_incremental(self, last_sync_time: Optional[datetime] = None) -> Dict:
        """Perform incremental synchronization based on modification timestamps"""
        try:
            logger.info("Starting incremental synchronization")
            
            if not last_sync_time:
                # If no timestamp provided, sync last 24 hours
                from datetime import timedelta
                last_sync_time = datetime.now() - timedelta(hours=24)
            
            # Sync only modified data
            cursos_count = await self._sync_cursos_incremental(last_sync_time)
            categorias_count = await self._sync_categorias_incremental(last_sync_time)
            promociones_count = await self._sync_promociones_incremental(last_sync_time)
            
            total_synced = cursos_count + categorias_count + promociones_count
            
            return {
                "status": "success",
                "message": "Sincronización incremental exitosa",
                "synced_count": total_synced,
                "last_sync_time": last_sync_time.isoformat(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during incremental sync: {str(e)}")
            return {
                "status": "error",
                "message": f"Error en sincronización incremental: {str(e)}",
                "synced_count": 0,
                "errors": [str(e)]
            }
    
    async def _sync_cursos(self) -> int:
        """Sync all cursos to Qdrant"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT c.*, cat.nombre as categoria_nombre,
                       GROUP_CONCAT(DISTINCT CONCAT(pr.descripcion, ':', pr.descuentoPorcentaje, '%') SEPARATOR ' | ') as promociones_activas
                FROM curso c 
                LEFT JOIN categoria cat ON c.categoriaId = cat.id
                LEFT JOIN promocionCurso pc ON c.id = pc.cursoId
                LEFT JOIN promocion pr ON pc.promocionId = pr.id 
                    AND pr.fechaInicio <= CURDATE() 
                    AND pr.fechaFin >= CURDATE()
                GROUP BY c.id, c.titulo, c.descripcion, c.precio, c.cupo, c.nivel, c.idioma, c.categoriaId, cat.nombre
                """
                cursor.execute(sql)
                cursos = cursor.fetchall()
                
                synced_count = 0
                for curso in cursos:
                    # Create searchable text content
                    content = self._create_curso_content(curso)
                    
                    # Generate embedding
                    embedding = await self.embedding_service.generate_embedding(content)
                    
                    doc_id = int(curso['id'])
                    
                    # Calcular disponibilidad basado en cupo
                    disponible = int(curso.get('cupo', 0)) > 0
                    
                    # Store in Qdrant
                    await self.qdrant_service.upsert_document(
                        doc_id=doc_id,
                        content=content,
                        embedding=embedding,
                        metadata={
                            "type": "curso",
                            "id": curso['id'],
                            "titulo": curso['titulo'],
                            "categoria": curso.get('categoria_nombre', ''),
                            "categoria_id": curso['categoriaId'],
                            "precio": float(curso['precio']) if curso['precio'] else 0.0,
                            "disponible": disponible,
                            "descripcion": curso.get('descripcion', ''),
                            "nivel": curso.get('nivel', ''),
                            "idioma": curso.get('idioma', ''),
                            "cupo": int(curso.get('cupo', 0)),
                            "promociones_activas": curso.get('promociones_activas', '') or ''
                        }
                    )
                    synced_count += 1
                
                return synced_count
                
        finally:
            connection.close()
    
    async def _sync_categorias(self) -> int:
        """Sync all categorias to Qdrant"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM categoria"
                cursor.execute(sql)
                categorias = cursor.fetchall()
                
                synced_count = 0
                for categoria in categorias:
                    content = self._create_categoria_content(categoria)
                    embedding = await self.embedding_service.generate_embedding(content)
                    
                    doc_id = int(categoria['id']) + 1000000
                    
                    await self.qdrant_service.upsert_document(
                        doc_id=doc_id,
                        content=content,
                        embedding=embedding,
                        metadata={
                            "type": "categoria",
                            "id": categoria['id'],
                            "nombre": categoria['nombre'],
                            "descripcion": categoria.get('descripcion', '')
                        }
                    )
                    synced_count += 1
                
                return synced_count
                
        finally:
            connection.close()
    
    async def _sync_promociones(self) -> int:
        """Sync all promociones to Qdrant with associated courses"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT pr.*, 
                       GROUP_CONCAT(DISTINCT c.titulo SEPARATOR ', ') as cursos_nombres,
                       GROUP_CONCAT(DISTINCT CONCAT(c.titulo, ' ($', c.precio, ')') SEPARATOR ', ') as cursos_detalles,
                       COUNT(DISTINCT c.id) as total_cursos
                FROM promocion pr
                LEFT JOIN promocionCurso pc ON pr.id = pc.promocionId
                LEFT JOIN curso c ON pc.cursoId = c.id
                GROUP BY pr.id
                """
                cursor.execute(sql)
                promociones = cursor.fetchall()
                
                synced_count = 0
                for promocion in promociones:
                    content = self._create_promocion_content(promocion)
                    embedding = await self.embedding_service.generate_embedding(content)
                    
                    from datetime import date
                    today = date.today()
                    is_active = (promocion['fechaInicio'] <= today <= promocion['fechaFin'])
                    
                    doc_id = int(promocion['id']) + 2000000
                    
                    import logging
                    logging.getLogger(__name__).info(f"Promoción id={promocion['id']} activa={is_active} tipo={type(is_active)}")
                    await self.qdrant_service.upsert_document(
                        doc_id=doc_id,
                        content=content,
                        embedding=embedding,
                        metadata={
                            "type": "promocion",
                            "id": promocion['id'],
                            "descripcion": promocion['descripcion'],
                            "descuento": float(promocion['descuentoPorcentaje']) if promocion['descuentoPorcentaje'] else 0.0,
                            "fecha_inicio": promocion['fechaInicio'].isoformat() if promocion['fechaInicio'] else None,
                            "fecha_fin": promocion['fechaFin'].isoformat() if promocion['fechaFin'] else None,
                            "activa": bool(is_active),
                            "cursos_nombres": promocion.get('cursos_nombres', '') or '',
                            "cursos_detalles": promocion.get('cursos_detalles', '') or '',
                            "total_cursos": promocion.get('total_cursos', 0) or 0
                        }
                    )
                    synced_count += 1
                
                return synced_count
                
        finally:
            connection.close()

    def _create_curso_content(self, curso: Dict) -> str:
        """Create searchable content for curso"""
        # Calcular disponibilidad basada en cupo
        cupo_value = int(curso.get('cupo', 0))
        disponibilidad_texto = 'Sí' if cupo_value > 0 else 'No'
        
        parts = [
            f"Curso: {curso['titulo']}",
            f"Descripción: {curso.get('descripcion', '')}" if curso.get('descripcion') else "",
            f"Categoría: {curso.get('categoria_nombre', '')}" if curso.get('categoria_nombre') else "",
            f"Precio: ${curso['precio']}" if curso['precio'] else "",
            f"Nivel: {curso.get('nivel', '')}" if curso.get('nivel') else "",
            f"Idioma: {curso.get('idioma', '')}" if curso.get('idioma') else "",
            f"Cupo: {cupo_value} estudiantes",
            f"Disponible: {disponibilidad_texto}"
        ]
        
        if curso.get('promociones_activas'):
            parts.append(f"Promociones activas: {curso['promociones_activas']}")
        
        return " | ".join([p for p in parts if p])

    def _create_categoria_content(self, categoria: Dict) -> str:
        """Create searchable content for categoria"""
        parts = [
            f"Categoría: {categoria['nombre']}",
            f"Descripción: {categoria.get('descripcion', '')}" if categoria.get('descripcion') else ""
        ]
        return " | ".join([p for p in parts if p])
    
    def _create_promocion_content(self, promocion: Dict) -> str:
        """Create searchable content for promocion"""
        parts = [
            f"Promoción: {promocion['descripcion']}",
            f"Descuento: {promocion['descuentoPorcentaje']}%" if promocion['descuentoPorcentaje'] else "",
            f"Válida desde: {promocion['fechaInicio']}" if promocion['fechaInicio'] else "",
            f"Válida hasta: {promocion['fechaFin']}" if promocion['fechaFin'] else ""
        ]
        
        if promocion.get('cursos_nombres'):
            parts.append(f"Cursos en promoción: {promocion['cursos_nombres']}")
        if promocion.get('cursos_detalles'):
            parts.append(f"Detalles de cursos: {promocion['cursos_detalles']}")
        if promocion.get('total_cursos', 0) > 0:
            parts.append(f"Total de cursos: {promocion['total_cursos']}")
        
        return " | ".join([p for p in parts if p])
    
    async def _sync_cursos_incremental(self, since: datetime) -> int:
        """Sync cursos modified since timestamp"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT c.*, cat.nombre as categoria_nombre,
                       GROUP_CONCAT(DISTINCT CONCAT(pr.descripcion, ':', pr.descuentoPorcentaje, '%') SEPARATOR ' | ') as promociones_activas
                FROM curso c 
                LEFT JOIN categoria cat ON c.categoriaId = cat.id
                LEFT JOIN promocionCurso pc ON c.id = pc.cursoId
                LEFT JOIN promocion pr ON pc.promocionId = pr.id 
                    AND pr.fechaInicio <= CURDATE() 
                    AND pr.fechaFin >= CURDATE()
                WHERE c.fechaActualizacion >= %s
                GROUP BY c.id, c.titulo, c.descripcion, c.precio, c.cupo, c.nivel, c.idioma, c.categoriaId, cat.nombre
                """
                cursor.execute(sql, (since,))
                cursos = cursor.fetchall()
                
                synced_count = 0
                for curso in cursos:
                    content = self._create_curso_content(curso)
                    embedding = await self.embedding_service.generate_embedding(content)
                    
                    doc_id = int(curso['id'])
                    
                    # Calcular disponibilidad basado en cupo
                    disponible = int(curso.get('cupo', 0)) > 0
                    
                    await self.qdrant_service.upsert_document(
                        doc_id=doc_id,
                        content=content,
                        embedding=embedding,
                        metadata={
                            "type": "curso",
                            "id": curso['id'],
                            "titulo": curso['titulo'],
                            "categoria": curso.get('categoria_nombre', ''),
                            "categoria_id": curso['categoriaId'],
                            "precio": float(curso['precio']) if curso['precio'] else 0.0,
                            "disponible": disponible,
                            "descripcion": curso.get('descripcion', ''),
                            "nivel": curso.get('nivel', ''),
                            "idioma": curso.get('idioma', ''),
                            "cupo": int(curso.get('cupo', 0)),
                            "promociones_activas": curso.get('promociones_activas', '') or ''
                        }
                    )
                    synced_count += 1
                
                return synced_count
        finally:
            connection.close()
    
    async def _sync_categorias_incremental(self, since: datetime) -> int:
        """Sync categorias modified since timestamp"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM categoria WHERE fechaActualizacion >= %s"
                cursor.execute(sql, (since,))
                categorias = cursor.fetchall()
                
                synced_count = 0
                for categoria in categorias:
                    content = self._create_categoria_content(categoria)
                    embedding = await self.embedding_service.generate_embedding(content)
                    
                    doc_id = int(categoria['id']) + 1000000
                    
                    await self.qdrant_service.upsert_document(
                        doc_id=doc_id,
                        content=content,
                        embedding=embedding,
                        metadata={
                            "type": "categoria",
                            "id": categoria['id'],
                            "nombre": categoria['nombre'],
                            "descripcion": categoria.get('descripcion', '')
                        }
                    )
                    synced_count += 1
                
                return synced_count
        finally:
            connection.close()

    async def _sync_promociones_incremental(self, since: datetime) -> int:
        """Sync promociones modified since timestamp"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT pr.*, 
                       GROUP_CONCAT(DISTINCT c.titulo SEPARATOR ', ') as cursos_nombres,
                       GROUP_CONCAT(DISTINCT CONCAT(c.titulo, ' ($', c.precio, ')') SEPARATOR ', ') as cursos_detalles,
                       COUNT(DISTINCT c.id) as total_cursos
                FROM promocion pr
                LEFT JOIN promocionCurso pc ON pr.id = pc.promocionId
                LEFT JOIN curso c ON pc.cursoId = c.id
                WHERE pr.fechaInicio <= CURDATE() 
                    AND pr.fechaFin >= CURDATE()
                GROUP BY pr.id
                """
                cursor.execute(sql, (since,))
                promociones = cursor.fetchall()
                
                synced_count = 0
                for promocion in promociones:
                    content = self._create_promocion_content(promocion)
                    embedding = await self.embedding_service.generate_embedding(content)
                    
                    from datetime import date
                    today = date.today()
                    is_active = (promocion['fechaInicio'] <= today <= promocion['fechaFin'])
                    
                    doc_id = int(promocion['id']) + 2000000
                    
                    await self.qdrant_service.upsert_document(
                        doc_id=doc_id,
                        content=content,
                        embedding=embedding,
                        metadata={
                            "type": "promocion",
                            "id": promocion['id'],
                            "descripcion": promocion['descripcion'],
                            "descuento": float(promocion['descuentoPorcentaje']) if promocion['descuentoPorcentaje'] else 0.0,
                            "fecha_inicio": promocion['fechaInicio'].isoformat() if promocion['fechaInicio'] else None,
                            "fecha_fin": promocion['fechaFin'].isoformat() if promocion['fechaFin'] else None,
                            "activa": is_active,
                            "cursos_nombres": promocion.get('cursos_nombres', '') or '',
                            "cursos_detalles": promocion.get('cursos_detalles', '') or '',
                            "total_cursos": promocion.get('total_cursos', 0) or 0
                        }
                    )
                    synced_count += 1
                
                return synced_count
        finally:
            connection.close()

    async def get_sync_status(self) -> Dict:
        """Get current synchronization status"""
        try:
            collection_info = self.qdrant_service.get_collection_info()
            
            return {
                "status": "success",
                "message": "Estado de sincronización obtenido",
                "data": {
                    "collection_exists": bool(collection_info),
                    "total_documents": collection_info.get("points_count", 0) if collection_info else 0,
                    "collection_name": collection_info.get("name", "") if collection_info else "",
                    "last_check": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error obteniendo estado: {str(e)}",
                "data": None
            }