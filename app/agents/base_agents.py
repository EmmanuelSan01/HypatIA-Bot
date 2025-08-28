"""
Implementación de agentes base usando Langroid Framework
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import langroid as lr
from langroid import ChatAgent, ChatAgentConfig
from langroid import Task
from langroid.language_models import OpenAIGPTConfig
from langroid.utils.types import *
from langroid.agent.tools import AgentDoneTool, PassTool, ForwardTool

from app.agents.config import langroid_config
from app.services.qdrant import QdrantService
from app.database import get_sync_connection

logger = logging.getLogger(__name__)

# ============================
# HERRAMIENTAS PERSONALIZADAS
# ============================

class ProductSearchTool(lr.ToolMessage):
    """Herramienta para búsqueda de productos"""
    request: str = "product_search"
    purpose: str = "Buscar productos en la base de datos usando embeddings vectoriales"
    query: str
    category: Optional[str] = None
    max_results: int = 5
    
    def handle(self) -> str:
        """Ejecuta búsqueda de productos en Qdrant"""
        try:
            qdrant_service = QdrantService()
            
            from app.services.embedding import EmbeddingService
            embedding_service = EmbeddingService()
            query_embedding = embedding_service.encode_query(self.query)
            
            # Aplicar filtros si se especifica categoría
            filters = {}
            if self.category:
                filters["categoria"] = self.category
            
            # Buscar documentos similares
            results = qdrant_service.search_similar(
                query_embedding, 
                limit=self.max_results,
                filters=filters
            )
            
            if not results:
                return "No se encontraron productos que coincidan con tu búsqueda."
            
            # Formatear resultados
            formatted_results = []
            for result in results:
                payload = result.get("payload", {})
                score = result.get("score", 0)
                
                formatted_results.append({
                    "nombre": payload.get("nombre", "N/A"),
                    "descripcion": payload.get("descripcion", "N/A"),
                    "precio": payload.get("precio", "N/A"),
                    "categoria": payload.get("categoria", "N/A"),
                    "disponible": payload.get("disponible", True),
                    "stock": payload.get("stock", 0),
                    "relevance_score": score
                })
            
            return str(formatted_results)
            
        except Exception as e:
            logger.error(f"Error in ProductSearchTool: {str(e)}")
            return f"Error ejecutando búsqueda: {str(e)}"


class PromotionSearchTool(lr.ToolMessage):
    """Herramienta para búsqueda de promociones activas"""
    request: str = "promotion_search"
    purpose: str = "Buscar promociones y ofertas activas en la base de datos"
    
    def handle(self) -> str:
        """Busca promociones activas"""
        try:
            qdrant_service = QdrantService()
            
            from app.services.embedding import EmbeddingService
            embedding_service = EmbeddingService()
            
            # Generar embedding para consulta de promociones
            promotion_query = "promociones descuentos ofertas especiales productos en oferta"
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
                    "total_productos": payload.get("total_productos", 0)
                }
                
                # Extraer información detallada de productos desde metadata
                metadata = payload.get("metadata", {})
                productos_nombres = metadata.get("productos_nombres", "") or payload.get("productos_nombres", "")
                productos_detalles = metadata.get("productos_detalles", "") or payload.get("productos_detalles", "")
                
                if productos_nombres and productos_nombres.strip():
                    promocion_info["productos_incluidos"] = productos_nombres
                else:
                    promocion_info["productos_incluidos"] = "No se especifican productos"
                
                if productos_detalles and productos_detalles.strip():
                    promocion_info["productos_con_precios"] = productos_detalles
                else:
                    promocion_info["productos_con_precios"] = "Precios no disponibles"
                
                promotions_info.append(promocion_info)
            
            # Formatear respuesta de manera legible
            formatted_response = "🎉 PROMOCIONES ACTIVAS:\n\n"
            for i, promo in enumerate(promotions_info, 1):
                formatted_response += f"📍 PROMOCIÓN {i}:\n"
                formatted_response += f"   • Descripción: {promo['descripcion']}\n"
                formatted_response += f"   • Descuento: {promo['descuento']}%\n"
                formatted_response += f"   • Válida hasta: {promo['fecha_fin']}\n"
                formatted_response += f"   • Total productos: {promo['total_productos']}\n"
                formatted_response += f"   • Productos incluidos: {promo['productos_incluidos']}\n"
                if promo['productos_con_precios'] != "Precios no disponibles":
                    formatted_response += f"   • Detalles con precios: {promo['productos_con_precios']}\n"
                formatted_response += "\n"
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error in PromotionSearchTool: {str(e)}")
            return f"Error obteniendo promociones: {str(e)}"


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

# ============================
# AGENTES PRINCIPALES
# ============================

class KnowledgeAgent(ChatAgent):
    """Agente especializado en búsqueda de conocimiento"""
    
    def __init__(self, config: ChatAgentConfig):
        super().__init__(config)
        self.enable_message(ProductSearchTool)
        self.enable_message(PromotionSearchTool)
        self.enable_message(PassTool)
        
    def handle_message_fallback(self, msg: str) -> str:
        """Maneja consultas de conocimiento"""
        try:
            # Determinar tipo de consulta
            if "promocion" in msg.lower() or "descuento" in msg.lower() or "oferta" in msg.lower():
                # Buscar promociones
                promotion_tool = PromotionSearchTool()
                return promotion_tool.handle()
            else:
                # Búsqueda general de productos
                search_tool = ProductSearchTool(query=msg)
                return search_tool.handle()
                
        except Exception as e:
            logger.error(f"Error in KnowledgeAgent: {str(e)}")
            return "Lo siento, hubo un error accediendo a la base de conocimiento."


class SalesAgent(ChatAgent):
    """Agente especializado en ventas y recomendaciones"""
    
    def __init__(self, config: ChatAgentConfig):
        super().__init__(config)
        self.enable_message(UserHistoryTool)
        self.enable_message(PassTool)
        
    def handle_message_fallback(self, msg: str) -> str:
        """Maneja lógica de ventas"""
        try:
            # Analizar mensaje para oportunidades de venta
            recommendations = []
            
            # Keywords para productos complementarios
            if "uniforme" in msg.lower():
                recommendations.append("¿Has considerado también un cinturón o protecciones?")
            elif "cinturon" in msg.lower():
                recommendations.append("¿Te interesaría ver nuestros uniformes a juego?")
            elif "proteccion" in msg.lower():
                recommendations.append("¿Necesitas también guantes o espinilleras?")
            
            if recommendations:
                return f"Sugerencias adicionales: {' '.join(recommendations)}"
            else:
                return "Continuando con la conversación..."
                
        except Exception as e:
            logger.error(f"Error in SalesAgent: {str(e)}")
            return "Error en análisis de ventas"

class AnalyticsAgent(ChatAgent):
    """Agente para análisis y métricas"""
    
    def __init__(self, config: ChatAgentConfig):
        super().__init__(config)
        self.conversation_metrics = {
            "total_messages": 0,
            "user_satisfaction": [],
            "conversion_indicators": []
        }
        
    def track_conversation(self, user_msg: str, bot_response: str):
        """Rastrea métricas de conversación"""
        self.conversation_metrics["total_messages"] += 1
        
        # Detectar indicadores de satisfacción
        positive_indicators = ["gracias", "perfecto", "excelente", "me gusta"]
        if any(indicator in user_msg.lower() for indicator in positive_indicators):
            self.conversation_metrics["user_satisfaction"].append("positive")
            
        # Detectar indicadores de conversión
        conversion_indicators = ["comprar", "precio", "disponible", "stock"]
        if any(indicator in user_msg.lower() for indicator in conversion_indicators):
            self.conversation_metrics["conversion_indicators"].append(user_msg[:50])
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas actuales"""
        return self.conversation_metrics.copy()


class MainBaekhoAgent(ChatAgent):
    """Agente principal que orquesta el sistema multi-agente"""
    
    def __init__(self, config: ChatAgentConfig):
        super().__init__(config)
        
        # Configurar agentes subordinados
        self.knowledge_agent = KnowledgeAgent(
            ChatAgentConfig(
                llm=config.llm,
                system_message=langroid_config.SYSTEM_PROMPTS["knowledge_agent"],
                name="KnowledgeAgent"
            )
        )
        
        self.sales_agent = SalesAgent(
            ChatAgentConfig(
                llm=config.llm,
                system_message=langroid_config.SYSTEM_PROMPTS["sales_agent"],
                name="SalesAgent"
            )
        )
        
        self.analytics_agent = AnalyticsAgent(
            ChatAgentConfig(
                llm=config.llm,
                system_message=langroid_config.SYSTEM_PROMPTS["analytics_agent"],
                name="AnalyticsAgent"
            )
        )
        
        # Herramientas habilitadas
        self.enable_message(ForwardTool)
        self.enable_message(AgentDoneTool)
        
    async def handle_user_message(self, message: str, user_id: Optional[int] = None, 
                                  conversation_context: Optional[Dict] = None) -> str:
        """Maneja mensaje de usuario orquestando múltiples agentes"""
        try:
            # Rastrear con Analytics Agent
            self.analytics_agent.track_conversation(message, "")
            
            # 1. Consultar Knowledge Agent para obtener contexto
            logger.info("Consultando Knowledge Agent...")
            knowledge_response = self.knowledge_agent.handle_message_fallback(message)
            
            # 2. Consultar Sales Agent para recomendaciones
            logger.info("Consultando Sales Agent...")
            sales_response = self.sales_agent.handle_message_fallback(message)
            
            # 3. Generar respuesta final combinando información
            context_prompt = f"""
            Consulta del usuario: {message}
            
            Información de productos encontrada:
            {knowledge_response}
            
            Recomendaciones de ventas:
            {sales_response}
            
            Basándote en esta información, proporciona una respuesta completa y útil al usuario.
            Mantén el tono amigable y comercial de BaekhoBot 🥋.
            """
            
            final_response = await self.llm_response_async(context_prompt)
            
            # Rastrear respuesta con Analytics Agent
            self.analytics_agent.track_conversation(message, final_response)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in MainBaekhoAgent: {str(e)}")
            return "Lo siento, hubo un error procesando tu consulta. Por favor intenta de nuevo."
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la conversación"""
        return self.analytics_agent.get_metrics()

# ============================
# FACTORY PARA CREAR AGENTES
# ============================

class BaekhoAgentFactory:
    """Factory para crear y configurar agentes Langroid"""
    
    @staticmethod
    def create_main_agent() -> MainBaekhoAgent:
        """Crea el agente principal configurado"""
        config = ChatAgentConfig(
            llm=langroid_config.LLM_CONFIG,
            system_message=langroid_config.SYSTEM_PROMPTS["main_agent"],
            name="BaekhoBot",
        )
        
        return MainBaekhoAgent(config)
    
    @staticmethod
    def create_task_for_agent(agent: ChatAgent, user_message: str) -> Task:
        """Crea una tarea Langroid para el agente"""
        task = Task(
            agent=agent,
            name="BaekhoConversation",
            system_message=agent.config.system_message,
            llm_delegate=True,
            single_round=False,
        )
        
        return task
