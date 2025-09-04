"""
Implementación de agentes base usando Langroid Framework
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

import langroid as lr
from langroid import ChatAgent, ChatAgentConfig
from langroid import Task
from langroid.language_models import OpenAIGPTConfig
from langroid.utils.types import *
from langroid.agent.tools import AgentDoneTool, PassTool, ForwardTool

from app.agents.config import langroid_config
from app.services.qdrant import QdrantService
from app.database import get_sync_connection
from app.controllers.usuario.UsuarioController import UsuarioController

logger = logging.getLogger(__name__)
logging.getLogger("langroid").setLevel(logging.ERROR)

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
            
            formatted_results = []
            for result in results:
                payload = result.get("payload", {})
                score = result.get("score", 0)
                
                disponible_final = payload.get("disponible", False)
                
                logger.debug(f"Product {payload.get('nombre', 'N/A')}: disponible={disponible_final}")
                
                formatted_results.append({
                    "nombre": payload.get("nombre", "N/A"),
                    "descripcion": payload.get("descripcion", "N/A"),
                    "precio": payload.get("precio", "N/A"),
                    "categoria": payload.get("categoria", "N/A"),
                    "disponible": disponible_final,  # Usar valor directo del payload
                    "promociones_activas": payload.get("promociones_activas", ""),
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

class PhoneValidationTool(lr.ToolMessage):
    """Herramienta para validar números de teléfono colombianos"""
    request: str = "phone_validation"
    purpose: str = "Validar formato de números de teléfono colombianos"
    phone_number: str
    user_id: Optional[int] = None  # Added user_id to get current phone from database
    
    def handle(self) -> str:
        """Valida el formato del número de teléfono"""
        try:
            # Limpiar el número (remover espacios, guiones, paréntesis)
            clean_number = re.sub(r'[^\d+]', '', self.phone_number.strip())
            
            # Remover prefijo +57 si existe
            if clean_number.startswith('+57'):
                clean_number = clean_number[3:]
            elif clean_number.startswith('57') and len(clean_number) == 12:
                clean_number = clean_number[2:]
            
            # Validar formato: 10 dígitos que empiecen con 3
            if len(clean_number) == 10 and clean_number.startswith('3') and clean_number.isdigit():
                return f"VALID:{clean_number}"
            else:
                current_phone = "ninguno registrado"
                if self.user_id:
                    try:
                        usuario_controller = UsuarioController()
                        usuario = usuario_controller.get_usuario_by_id(self.user_id)
                        if usuario and usuario.telefono:
                            current_phone = usuario.telefono
                    except Exception as e:
                        logger.error(f"Error getting current phone: {str(e)}")
                
                return f"INVALID:El número debe tener 10 dígitos y empezar con 3|CURRENT:{current_phone}"
                
        except Exception as e:
            logger.error(f"Error validating phone: {str(e)}")
            return "INVALID:Error procesando el número|CURRENT:ninguno registrado"

class SavePhoneTool(lr.ToolMessage):
    """Herramienta para guardar número de teléfono validado"""
    request: str = "save_phone"
    purpose: str = "Guardar número de teléfono del usuario en la base de datos"
    user_id: int
    phone_number: str
    
    def handle(self) -> str:
        """Guarda el número de teléfono en la base de datos"""
        try:
            usuario_controller = UsuarioController()
            
            # Actualizar el teléfono del usuario
            success = usuario_controller.update_usuario_telefono(self.user_id, self.phone_number)
            
            if success:
                usuario = usuario_controller.get_usuario_by_id(self.user_id)
                if usuario and usuario.telefono:
                    saved_phone = usuario.telefono
                    return f"SAVED:{saved_phone}"
                else:
                    return f"SAVED:{self.phone_number}"
            else:
                return "ERROR:No se pudo guardar el número"
                
        except Exception as e:
            logger.error(f"Error saving phone: {str(e)}")
            return f"ERROR:Error guardando número: {str(e)}"

class CheckUserPhoneTool(lr.ToolMessage):
    """Herramienta para verificar si el usuario ya tiene un número de teléfono registrado"""
    request: str = "check_user_phone"
    purpose: str = "Verificar si el usuario ya tiene un número de teléfono en la base de datos"
    user_id: int
    
    def handle(self) -> str:
        """Verifica si el usuario ya tiene un número de teléfono registrado"""
        try:
            usuario_controller = UsuarioController()
            usuario = usuario_controller.get_usuario_by_id(self.user_id)
            
            if usuario and usuario.telefono and usuario.telefono.strip():
                return f"HAS_PHONE:{usuario.telefono}"
            else:
                return "NO_PHONE:Usuario no tiene número registrado"
                
        except Exception as e:
            logger.error(f"Error checking user phone: {str(e)}")
            return "NO_PHONE:Error verificando número"

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
        self.enable_message(PhoneValidationTool)
        self.enable_message(SavePhoneTool)
        self.enable_message(CheckUserPhoneTool)  # Agregada nueva herramienta para verificar teléfono
        self.enable_message(PassTool)
        
    def handle_message_fallback(self, msg: str, user_id: Optional[int] = None) -> str:
        """Maneja lógica de ventas"""
        try:
            phone_patterns = [
                r'\+?57\s*3\d{9}',  # +57 3xxxxxxxxx
                r'3\d{9}',          # 3xxxxxxxxx
                r'\d{10}'           # 10 digits
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, msg)
                if matches:
                    # Found potential phone number, validate it
                    potential_phone = matches[0]
                    validation_tool = PhoneValidationTool(phone_number=potential_phone, user_id=user_id)
                    validation_result = validation_tool.handle()
                    
                    if validation_result.startswith("VALID:"):
                        return f"PHONE_DETECTED:{validation_result}"
                    else:
                        return f"PHONE_INVALID:{validation_result}"
            
            # Analizar mensaje para oportunidades de venta
            recommendations = []
            
            # Keywords para productos complementarios
            if "uniforme" in msg.lower():
                recommendations.append("¿Has considerado también un cinturón o protecciones?")
            elif "cinturon" in msg.lower():
                recommendations.append("¿Te interesaría ver nuestros uniformes a juego?")
            elif "proteccion" in msg.lower():
                recommendations.append("¿Necesitas también guantes o espinilleras?")
            
            purchase_keywords = ["comprar", "compra", "precio", "cuanto cuesta", "quiero", "necesito"]
            if any(keyword in msg.lower() for keyword in purchase_keywords):
                if user_id:
                    check_phone_tool = CheckUserPhoneTool(user_id=user_id)
                    phone_check_result = check_phone_tool.handle()
                    
                    if phone_check_result.startswith("HAS_PHONE:"):
                        # Usuario ya tiene teléfono, no solicitar nuevamente
                        recommendations.append("PURCHASE_INTENT_DETECTED_WITH_PHONE")
                    else:
                        # Usuario no tiene teléfono, solicitar
                        recommendations.append("PURCHASE_INTENT_DETECTED")
                else:
                    recommendations.append("PURCHASE_INTENT_DETECTED")
            
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
        self.enable_message(PhoneValidationTool)
        self.enable_message(SavePhoneTool)
        self.enable_message(CheckUserPhoneTool)  # Agregada herramienta para verificar teléfono
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
        """Maneja mensaje de usuario orquestando múltiples agentes"""
        try:
            # Rastrear con Analytics Agent
            self.analytics_agent.track_conversation(message, "")
            
            sales_response = self.sales_agent.handle_message_fallback(message, user_id)
            
            # Handle phone number detection and validation
            if "PHONE_DETECTED:" in sales_response:
                phone_number = sales_response.split("PHONE_DETECTED:VALID:")[1]
                if user_id:
                    save_tool = SavePhoneTool(user_id=user_id, phone_number=phone_number)
                    save_result = save_tool.handle()
                    
                    if save_result.startswith("SAVED:"):
                        saved_phone = save_result.split("SAVED:")[1]
                        return f"¡Perfecto! He recibido y guardado tu número de teléfono {saved_phone}. 📞✨"
                    else:
                        return "He recibido tu número de teléfono. 📞"
                else:
                    return "He recibido tu número de teléfono. 📞"
            
            elif "PHONE_INVALID:" in sales_response:
                parts = sales_response.split("PHONE_INVALID:")[1].split("|CURRENT:")
                error_msg = parts[0]
                current_phone = parts[1] if len(parts) > 1 else "ninguno registrado"
                
                response = f"Parece que el número que ingresaste no es correcto. {error_msg}. Por favor, envíalo nuevamente. 📱"
                if current_phone != "ninguno registrado":
                    response += f"\n\nTu número actual registrado es: {current_phone}"
                else:
                    response += f"\n\nActualmente no tienes ningún número registrado."
                
                return response
            
            # 1. Consultar Knowledge Agent para obtener contexto
            logger.info("Consultando Knowledge Agent...")
            knowledge_response = self.knowledge_agent.handle_message_fallback(message)
            
            phone_status_for_context = ""
            if user_id:
                check_phone_tool = CheckUserPhoneTool(user_id=user_id)
                phone_check_result = check_phone_tool.handle()
                
                if phone_check_result.startswith("HAS_PHONE:"):
                    phone_status_for_context = "USER_HAS_PHONE_REGISTERED"
                else:
                    phone_status_for_context = "USER_NO_PHONE_REGISTERED"
            
            # 2. Generate final response combining information
            context_prompt = f"""
            Consulta del usuario: {message}
            
            Información de productos encontrada:
            {knowledge_response}
            
            Recomendaciones de ventas:
            {sales_response}
            
            Estado actual del teléfono del usuario: {phone_status_for_context}
            
            INSTRUCCIONES CRÍTICAS PARA DISPONIBILIDAD:
            - La información de productos incluye el campo 'disponible' que indica la disponibilidad
            - Si 'disponible' es True, el producto ESTÁ DISPONIBLE para compra
            - Si 'disponible' es False, el producto NO ESTÁ DISPONIBLE para compra
            - Responde con precisión sobre la disponibilidad basándote en este campo booleano
            - NO asumas que no hay disponibilidad si no tienes información clara
            - La cantidad exacta de unidades no es relevante para el cliente
            
            INSTRUCCIONES CRÍTICAS PARA SOLICITAR TELÉFONO:
            - Si el estado actual del teléfono es "USER_HAS_PHONE_REGISTERED", NUNCA solicites el número de teléfono
            - Si el estado actual del teléfono es "USER_NO_PHONE_REGISTERED" Y detectas intención de compra, entonces SÍ solicita el número de teléfono
            - Si detectas "PURCHASE_INTENT_DETECTED" en las recomendaciones de ventas pero el estado es "USER_HAS_PHONE_REGISTERED", NO solicites el teléfono
            - Si detectas "PURCHASE_INTENT_DETECTED_WITH_PHONE" en las recomendaciones de ventas, NO solicites el teléfono
            - SIEMPRE verifica el estado actual del teléfono antes de decidir si solicitarlo o no
            
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
