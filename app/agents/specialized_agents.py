"""
Agentes especializados del sistema
"""
import logging
from typing import Optional
from langroid import ChatAgent, ChatAgentConfig
from langroid.agent.tools import PassTool

from .tools import CourseSearchTool, PromotionSearchTool, UserHistoryTool

logger = logging.getLogger(__name__)

class KnowledgeAgent(ChatAgent):
    """Agente especializado en búsqueda de conocimiento"""
    
    def __init__(self, config: ChatAgentConfig):
        super().__init__(config)
        self.enable_message(CourseSearchTool)
        self.enable_message(PromotionSearchTool)
        self.enable_message(PassTool)
        
    def handle_message_fallback(self, msg: str) -> str:
        """Maneja consultas de conocimiento"""
        try:
            # Determinar tipo de consulta
            if "promocion" in msg.lower() or "descuento" in msg.lower() or "oferta" in msg.lower():
                # Buscar promociones pasando el mensaje del usuario
                promotion_tool = PromotionSearchTool(query=msg)
                return promotion_tool.handle()
            else:
                # Búsqueda general de cursos
                search_tool = CourseSearchTool(query=msg)
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
        
    def handle_message_fallback(self, msg: str, user_id: Optional[int] = None) -> str:
        """Maneja lógica de ventas"""
        try:
            # Analizar mensaje para oportunidades de recomendación de cursos
            recommendations = []
            # Keywords para cursos complementarios
            if "principiante" in msg.lower() or "básico" in msg.lower():
                recommendations.append("¿Te interesaría ver nuestros cursos de nivel intermedio después?")
            elif "intermedio" in msg.lower() or "avanzado" in msg.lower():
                recommendations.append("¿Has considerado complementar con cursos de aplicaciones prácticas?")
            elif "deep learning" in msg.lower():
                recommendations.append("¿Te gustaría explorar también nuestros cursos de Machine Learning?")
            elif "machine learning" in msg.lower():
                recommendations.append("¿Has pensado en profundizar con nuestros cursos de Deep Learning?")
            elif "python" in msg.lower():
                recommendations.append("¿Te interesaría ver cursos de frameworks específicos como TensorFlow o PyTorch?")
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
            
        conversion_indicators = ["comprar", "precio", "disponible"]
        if any(indicator in user_msg.lower() for indicator in conversion_indicators):
            self.conversation_metrics["conversion_indicators"].append(user_msg[:50])
    
    def get_metrics(self):
        """Obtiene métricas actuales"""
        return self.conversation_metrics.copy()
