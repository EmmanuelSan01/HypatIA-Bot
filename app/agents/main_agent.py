"""
Agente principal que orquesta el sistema multi-agente
"""
import logging
import json
import hashlib
from typing import Dict, Any, Optional
from langroid import ChatAgent, ChatAgentConfig
from langroid.agent.tools import ForwardTool

from app.agents.config import langroid_config
from .specialized_agents import KnowledgeAgent, SalesAgent, AnalyticsAgent
from .utils import safe_stringify

logger = logging.getLogger(__name__)

# Configuración explícita del logger para mostrar logs INFO
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MainHypatiaAgent(ChatAgent):
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
        
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de conversación del analytics agent"""
        try:
            if hasattr(self, 'analytics_agent') and self.analytics_agent:
                return self.analytics_agent.get_metrics()
            else:
                # Retornar estadísticas por defecto si no hay analytics agent
                return {
                    "total_messages": 0,
                    "user_satisfaction": [],
                    "conversion_indicators": [],
                    "status": "analytics_agent_not_available"
                }
        except Exception as e:
            logger.error(f"Error getting conversation stats: {str(e)}")
            return {
                "total_messages": 0,
                "user_satisfaction": [],
                "conversion_indicators": [],
                "error": str(e)
            }


    async def handle_user_message(self, message: str, user_id: Optional[int] = None, 
                                  conversation_context: Optional[Dict] = None) -> str:
        """Maneja mensaje de usuario orquestando múltiples agentes, usando Redis para cacheo de resultados."""
        import time
        start_time = time.time()
        try:
            # Usar ServiceManager para obtener instancias singleton optimizadas
            from app.services.service_manager import service_manager
            redis_cache = service_manager.get_redis_cache()

            # Mejorar la clave de cache usando hash para evitar colisiones y asegurar unicidad
            cache_key = f"cursos:busqueda:{hashlib.sha256(message.strip().lower().encode()).hexdigest()}"
            cached_result = redis_cache.get(cache_key)
            if cached_result:
                logger.info(f"[CACHE HIT] Resultado recuperado desde Redis para clave: {cache_key}")
                knowledge_response = cached_result
            else:
                logger.info(f"[CACHE MISS] Generando nuevo resultado para clave: {cache_key}")
                knowledge_response = self.knowledge_agent.handle_message_fallback(message)
                knowledge_response = safe_stringify(knowledge_response)
                if isinstance(knowledge_response, (dict, list)):
                    knowledge_response = json.dumps(knowledge_response, ensure_ascii=False)
                if knowledge_response is None:
                    knowledge_response = ""
                redis_cache.set(cache_key, knowledge_response, expire_seconds=600)  # Cache por 10 minutos

            self.analytics_agent.track_conversation(message, "")
            sales_response = self.sales_agent.handle_message_fallback(message, user_id)
            sales_response = safe_stringify(sales_response)
            if isinstance(sales_response, (dict, list)):
                sales_response = json.dumps(sales_response, ensure_ascii=False)

            context_prompt = f"""
            Consulta del usuario: {message}

            Información de cursos encontrada:
            {knowledge_response}

            Recomendaciones de ventas:
            {sales_response}

            Basándote en esta información, proporciona una respuesta completa y útil al usuario.
            Mantén el tono amigable y comercial de DeepLearning.IA 🥋.
            """
            try:
                final_response = await self.llm_response_async(context_prompt)
            except Exception as e:
                error_msg = str(e)
                if "shorten prompt history" in error_msg or "token len" in error_msg:
                    logger.error("[CONTEXT RESET] Se alcanzó el límite de tokens. Limpiando contexto del agente.")
                    if hasattr(self, 'conversation_history'):
                        self.conversation_history = []
                    if hasattr(self.knowledge_agent, 'conversation_history'):
                        self.knowledge_agent.conversation_history = []
                    if hasattr(self.sales_agent, 'conversation_history'):
                        self.sales_agent.conversation_history = []
                    try:
                        final_response = await self.llm_response_async(context_prompt)
                    except Exception as e2:
                        logger.error(f"[CONTEXT RESET] Error tras limpiar contexto: {str(e2)}")
                        return "El contexto de la conversación era demasiado largo y ha sido reiniciado. Por favor, intenta de nuevo tu consulta."
                else:
                    logger.error(f"Error in MainHypatiaAgent: {error_msg}")
                    return "Lo siento, hubo un error procesando tu consulta. Por favor intenta de nuevo."

            self.analytics_agent.track_conversation(message, final_response)
            elapsed = time.time() - start_time
            logger.info(f"[RESPONSE TIME] El agente tardó {elapsed:.2f} segundos en generar la respuesta.")
            return final_response
        except Exception as e:
            logger.error(f"Error in MainHypatiaAgent: {str(e)}")
            return "Lo siento, hubo un error procesando tu consulta. Por favor intenta de nuevo."
