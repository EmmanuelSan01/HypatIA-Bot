"""
Servicio principal que reemplaza el AgentService original usando Langroid
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.agents import HypatiaAgentFactory, MainHypatiaAgent
from app.agents.config import langroid_config
from app.models.chat.ChatModel import ChatCreate
from app.models.mensaje.MensajeModel import MensajeCreate

logger = logging.getLogger(__name__)

class LangroidAgentService:
    """
    Servicio principal que usa Langroid Multi-Agent Framework
    para reemplazar el AgentService original
    """
    
    def __init__(self):
        self.main_agent: Optional[MainHypatiaAgent] = None
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Inicializa los agentes Langroid"""
        try:
            self.main_agent = HypatiaAgentFactory.create_main_agent()
            logger.info("✅ Agentes Langroid inicializados correctamente")
        except Exception as e:
            logger.error(f"❌ Error inicializando agentes Langroid: {str(e)}")
            self.main_agent = None
    
    async def process_message(self, message: str, user_id: Optional[int] = None,
                            persist_conversation: bool = True) -> Dict[str, Any]:
        """
        Procesa un mensaje usando el sistema multi-agente de Langroid
        
        Args:
            message: Mensaje del usuario
            user_id: ID del usuario (opcional)
            persist_conversation: Si persistir la conversación en BD
            
        Returns:
            Dict con la respuesta y metadatos
        """
        try:
            if not self.main_agent:
                return {
                    "status": "error",
                    "message": "El sistema de agentes no está disponible",
                    "reply": "Lo siento, el sistema no está disponible en este momento. Por favor contacta al administrador.",
                    "agent_used": "none",
                    "conversation_stats": {}
                }
            
            logger.info(f"Procesando mensaje con Langroid: {message[:50]}...")
            
            # Obtener contexto de conversación si existe usuario
            conversation_context = {}
            active_chat_id = None
            
            if user_id and persist_conversation:
                from app.controllers.mensaje.MensajeController import MensajeController
                
                # Obtener o crear chat activo
                active_chat_id = await self._get_or_create_active_chat(user_id)
                
                # Obtener contexto reciente
                if active_chat_id:
                    mensaje_controller = MensajeController()
                    recent_messages = mensaje_controller.get_mensajes_by_chat(
                        active_chat_id, limit=5, offset=0
                    )
                    conversation_context = {
                        "recent_messages": [
                            {
                                "tipo": msg.tipo,
                                "contenido": msg.contenido,
                                "fecha": msg.fechaEnvio.isoformat() if msg.fechaEnvio else None
                            }
                            for msg in recent_messages
                        ]
                    }
            
            bot_response = await self.main_agent.handle_user_message(
                message=message,
                user_id=user_id,
                conversation_context=conversation_context
            )
            
            # Obtener estadísticas de la conversación
            conversation_stats = self.main_agent.get_conversation_stats()
            
            # Persistir conversación si se requiere
            if persist_conversation and user_id and active_chat_id:
                await self._persist_conversation(
                    chat_id=active_chat_id,
                    user_message=message,
                    bot_response=bot_response
                )
            
            logger.info("✅ Mensaje procesado exitosamente con Langroid")
            
            return {
                "status": "success",
                "message": "Mensaje procesado exitosamente",
                "reply": bot_response,
                "agent_used": "langroid_multi_agent",
                "conversation_stats": conversation_stats,
                "chat_id": active_chat_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje con Langroid: {str(e)}")
            return {
                "status": "error",
                "message": f"Error procesando mensaje: {str(e)}",
                "reply": "Lo siento, hubo un error procesando tu consulta. Por favor intenta de nuevo.",
                "agent_used": "error",
                "conversation_stats": {},
                "error_details": str(e)
            }
    
    async def _get_or_create_active_chat(self, user_id: int) -> Optional[int]:
        """Obtiene o crea un chat activo para el usuario"""
        try:
            from app.controllers.chat.ChatController import ChatController
            
            chat_controller = ChatController()
            # Buscar chats existentes del usuario
            user_chats = chat_controller.get_chats_by_usuario(user_id)
            
            if user_chats:
                # Retornar el chat más reciente
                latest_chat = max(user_chats, key=lambda x: x.fechaCreacion)
                return latest_chat.id
            else:
                # Crear nuevo chat con campos válidos del modelo ChatCreate
                new_chat = ChatCreate(
                    usuarioId=user_id,
                    chatId=f"telegram_{user_id}_{int(datetime.now().timestamp())}"
                )
                created_chat = chat_controller.create_chat(new_chat)
                return created_chat.id if created_chat else None
                
        except Exception as e:
            logger.error(f"Error gestionando chat activo: {str(e)}")
            return None
    
    async def _persist_conversation(self, chat_id: int, user_message: str, bot_response: str):
        """Persiste la conversación en la base de datos"""
        try:
            from app.controllers.mensaje.MensajeController import MensajeController
            
            mensaje_controller = MensajeController()
            
            user_content = user_message
            if hasattr(user_message, 'content'):
                user_content = user_message.content
            elif not isinstance(user_message, str):
                user_content = str(user_message)
            
            bot_content = bot_response
            if hasattr(bot_response, 'content'):
                bot_content = bot_response.content
            elif not isinstance(bot_response, str):
                bot_content = str(bot_response)
            
            # Guardar mensaje del usuario
            user_msg = MensajeCreate(
                chatId=chat_id,
                tipo="usuario",
                contenido=user_content
            )
            mensaje_controller.create_mensaje(user_msg)
            
            # Guardar respuesta del bot
            bot_msg = MensajeCreate(
                chatId=chat_id,
                tipo="bot",
                contenido=bot_content
            )
            mensaje_controller.create_mensaje(bot_msg)
            
            logger.debug(f"Conversación persistida en chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error persistiendo conversación: {str(e)}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Obtiene información sobre el sistema de agentes"""
        return {
            "framework": "Langroid Multi-Agent System",
            "version": "1.0.0",
            "agents_available": bool(self.main_agent),
            "agents": {
                "main_agent": "MainHypatiaAgent - Orquestador principal",
                "knowledge_agent": "KnowledgeAgent - Búsqueda en base de conocimiento",
                "sales_agent": "SalesAgent - Recomendaciones y ventas",
                "analytics_agent": "AnalyticsAgent - Análisis y métricas"
            },
            "capabilities": [
                "Multi-agent orchestration",
                "Semantic course search", 
                "Sales recommendations",
                "Conversation analytics",
                "Persistent chat history",
                "Real-time knowledge base access"
            ],
            "configuration": {
                "llm_model": langroid_config.LLM_CONFIG.chat_model,
                "embedding_model": langroid_config.EMBEDDING_CONFIG.model_type,
                "vector_store": "Qdrant",
                "max_tokens": langroid_config.LLM_CONFIG.max_output_tokens
            }
        }
    
    def is_available(self) -> bool:
        """Verifica si el servicio está disponible"""
        return self.main_agent is not None
    
    async def get_conversation_analytics(self, chat_id: Optional[int] = None, 
                                       user_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtiene análiticas de conversación"""
        try:
            if not self.main_agent:
                return {"error": "Sistema de agentes no disponible"}
            
            # Obtener métricas del agente de analytics
            base_stats = self.main_agent.get_conversation_stats()
            
            # Agregar métricas de base de datos si se especifica chat o usuario
            db_stats = {}
            if chat_id:
                from app.controllers.mensaje.MensajeController import MensajeController
                mensaje_controller = MensajeController()
                db_stats = mensaje_controller.get_chat_statistics(chat_id)
            elif user_id:
                from app.controllers.chat.ChatController import ChatController
                chat_controller = ChatController()
                user_chats = chat_controller.get_chats_by_usuario(user_id)
                db_stats = {
                    "total_chats": len(user_chats),
                    "active_chats": len([c for c in user_chats if c.activo])
                }
            
            return {
                "langroid_stats": base_stats,
                "database_stats": db_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo analytics: {str(e)}")
            return {"error": str(e)}
    
    async def reset_conversation_context(self, user_id: Optional[int] = None):
        """Resetea el contexto de conversación"""
        try:
            if self.main_agent:
                # Reinicializar agentes para limpiar contexto
                self._initialize_agents()
                logger.info(f"Contexto de conversación reseteado para usuario {user_id}")
                
        except Exception as e:
            logger.error(f"Error reseteando contexto: {str(e)}")

# ============================
# BACKWARD COMPATIBILITY
# ============================

class HypatiaLangroidAgent:
    """
    Clase de compatibilidad que mantiene la interfaz original
    pero usa Langroid internamente
    """
    
    def __init__(self):
        self.langroid_service = LangroidAgentService()
    
    async def process_message(self, message: str, user_info: Dict[str, Any] = None) -> str:
        """
        Interfaz compatible con la implementación original
        """
        user_id = user_info.get("id") if user_info else None
        
        result = await self.langroid_service.process_message(message, user_id)
        return result.get("reply", "Error procesando mensaje")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Información del modelo compatible con la interfaz original"""
        return self.langroid_service.get_agent_info()
    
    def is_available(self) -> bool:
        """Verifica disponibilidad compatible con interfaz original"""
        return self.langroid_service.is_available()
