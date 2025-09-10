"""
Herramientas personalizadas para los agentes
"""
import logging
from typing import Optional
import langroid as lr

logger = logging.getLogger(__name__)

class CourseSearchTool(lr.ToolMessage):
    """Herramienta para búsqueda de cursos"""
    request: str = "course_search"
    purpose: str = "Buscar cursos en la base de datos usando embeddings vectoriales"
    query: str
    category: Optional[str] = None
    max_results: int = 5
    
    def handle(self) -> str:
        """Responde sobre cursos o categorías según los resultados de Qdrant."""
        try:
            from app.services.qdrant import QdrantService
            from app.services.embedding import EmbeddingService
            
            qdrant_service = QdrantService()
            embedding_service = EmbeddingService()
            query_embedding = embedding_service.encode_query(self.query)

            # Buscar documentos similares
            results = qdrant_service.search_similar(
                query_embedding,
                limit=self.max_results
            )

            if not results:
                return "No se encontraron resultados que coincidan con tu búsqueda."

            # Determinar el tipo de información predominante en los resultados
            tipo_predominante = None
            tipo_count = {"curso": 0, "categoria": 0, "promocion": 0}
            for result in results:
                tipo = result.get("tipo") or result.get("metadata", {}).get("type")
                if tipo in tipo_count:
                    tipo_count[tipo] += 1
            tipo_predominante = max(tipo_count, key=tipo_count.get) if any(tipo_count.values()) else None

            formatted_results = []
            for result in results:
                tipo = result.get("tipo") or result.get("metadata", {}).get("type")
                payload = result.get("payload", {})
                disponible_final = payload.get("disponible", False)

                if tipo_predominante == "categoria" and tipo == "categoria":
                    # Responder sobre categoría
                    formatted_result = (
                        f"Categoría: {payload.get('nombre', 'N/A')}\n"
                        f"Descripción: {payload.get('descripcion', 'N/A')}\n"
                    )
                    formatted_results.append(formatted_result)
                elif tipo_predominante == "curso" and tipo == "curso":
                        # Responder sobre curso asegurando que titulo y descripcion se obtienen correctamente
                        titulo = payload.get('titulo') or payload.get('metadata', {}).get('titulo', 'N/A')
                        descripcion = payload.get('descripcion') or payload.get('metadata', {}).get('descripcion', 'N/A')
                        nivel = payload.get('nivel') or payload.get('metadata', {}).get('nivel', 'N/A')
                        idioma = payload.get('idioma') or payload.get('metadata', {}).get('idioma', 'N/A')
                        precio = payload.get('precio') or payload.get('metadata', {}).get('precio', 'N/A')
                        cupo = payload.get('cupo') or payload.get('metadata', {}).get('cupo', 'N/A')
                        promociones = payload.get('promociones_activas') or payload.get('metadata', {}).get('promociones_activas', '')
                        formatted_result = (
                            f"Curso: {titulo}\n"
                            f"Descripción: {descripcion}\n"
                            f"Nivel: {nivel}\n"
                            f"Idioma: {idioma}\n"
                            f"Precio: ${precio}\n"
                            f"Cupo disponible: {cupo} estudiantes\n"
                            f"Disponible: {'Sí' if disponible_final else 'No'}\n"
                        )
                        if promociones:
                            formatted_result += f"Promociones activas: {promociones}\n"
                        formatted_results.append(formatted_result)
                elif tipo_predominante == "promocion" and tipo == "promocion":
                    # Responder sobre promoción
                    formatted_result = (
                        f"Promoción: {payload.get('nombre', 'N/A')}\n"
                        f"Descripción: {payload.get('descripcion', 'N/A')}\n"
                        f"Descuento: {payload.get('descuentoPorcentaje', 'N/A')}%\n"
                    )
                    formatted_results.append(formatted_result)

            if not formatted_results:
                return "No se encontraron resultados que coincidan con tu búsqueda."

            return "\n---\n".join(formatted_results)

        except Exception as e:
            logger.error(f"Error in CourseSearchTool: {str(e)}")
            return f"Error ejecutando búsqueda: {str(e)}"


class PromotionSearchTool(lr.ToolMessage):
    """Herramienta para búsqueda de promociones activas"""
    request: str = "promotion_search"
    purpose: str = "Buscar promociones y ofertas activas en la base de datos"
    query: str = ""
    
    def handle(self) -> str:
        """Busca promociones activas"""
        try:
            from app.services.qdrant import QdrantService
            from app.services.embedding import EmbeddingService
            
            qdrant_service = QdrantService()
            embedding_service = EmbeddingService()
            
            # Usar el mensaje recibido del usuario como query para el embedding
            promotion_query = self.query if self.query else "promociones descuentos ofertas especiales cursos en oferta"
            query_embedding = embedding_service.encode_query(promotion_query)
            
            filters = {"tipo": "promocion", "activa": True}
            results = qdrant_service.search_similar(
                query_embedding,  # Usar embedding real en lugar de vector cero
                limit=10,
                filters=filters
            )
            
            if not results:
                return "No hay promociones activas en este momento."
            
            promotions_info = []
            for result in results:
                payload = result.get("payload", {})
                
                # Extraer información completa de la promoción
                promocion_info = {
                    "descripcion": payload.get("descripcion", "Promoción sin descripción"),
                    "descuento": payload.get("descuento", 0),
                    "fecha_fin": payload.get("fecha_fin", "Fecha no especificada"),
                    "total_cursos": payload.get("total_cursos", 0)
                }
                
                # Extraer información detallada de cursos desde metadata
                metadata = payload.get("metadata", {})
                cursos_nombres = metadata.get("cursos_nombres", "") or payload.get("cursos_nombres", "")
                cursos_detalles = metadata.get("cursos_detalles", "") or payload.get("cursos_detalles", "")
                
                if cursos_nombres and cursos_nombres.strip():
                    promocion_info["cursos_incluidos"] = cursos_nombres
                else:
                    promocion_info["cursos_incluidos"] = "No se especifican cursos"
                
                if cursos_detalles and cursos_detalles.strip():
                    promocion_info["cursos_con_precios"] = cursos_detalles
                else:
                    promocion_info["cursos_con_precios"] = "Precios no disponibles"
                
                promotions_info.append(promocion_info)
            
            # Formatear respuesta de manera legible
            formatted_response = "🎉 PROMOCIONES ACTIVAS:\n\n"
            for i, promo in enumerate(promotions_info, 1):
                formatted_response += f"📍 PROMOCIÓN {i}:\n"
                formatted_response += f"   • Descripción: {promo['descripcion']}\n"
                formatted_response += f"   • Descuento: {promo['descuento']}%\n"
                formatted_response += f"   • Válida hasta: {promo['fecha_fin']}\n"
                formatted_response += f"   • Total cursos: {promo['total_cursos']}\n"
                formatted_response += f"   • cursos incluidos: {promo['cursos_incluidos']}\n"
                if promo['cursos_con_precios'] != "Precios no disponibles":
                    formatted_response += f"   • Detalles con precios: {promo['cursos_con_precios']}\n"
                formatted_response += "\n"
            
            return formatted_response
                
        except Exception as e:
            logger.error(f"Error in PromotionSearchTool: {str(e)}")
            return "Lo siento, hubo un error accediendo a la base de conocimiento."
        

class UserHistoryTool(lr.ToolMessage):
    """Herramienta para obtener historial de usuario"""
    request: str = "user_history"
    purpose: str = "Obtener historial de conversaciones y compras del usuario"
    user_id: int
    limit: int = 10
    
    def handle(self) -> str:
        """Obtiene historial reciente del usuario"""
        try:
            from app.controllers.chat.ChatController import ChatController
            from app.controllers.mensaje.MensajeController import MensajeController
            
            # Obtener chats del usuario
            chat_controller = ChatController()
            user_chats = chat_controller.get_chats_by_usuario(self.user_id)
            
            if not user_chats:
                return "Usuario sin historial previo"
            
            # Obtener mensajes recientes del chat más reciente
            latest_chat = user_chats[0]  # Asumiendo orden cronológico
            mensaje_controller = MensajeController()
            recent_messages = mensaje_controller.get_mensajes_by_chat(
                latest_chat.id, self.limit, 0
            )
            
            # Formatear historial
            history = []
            for msg in recent_messages:
                history.append({
                    "rol": msg.rol,
                    "contenido": msg.contenido[:200],  # Truncar para contexto
                    "fecha": msg.fechaCreacion.isoformat() if msg.fechaCreacion else None
                })
            
            return str(history)
            
        except Exception as e:
            logger.error(f"Error in UserHistoryTool: {str(e)}")
            return f"Error obteniendo historial: {str(e)}"
