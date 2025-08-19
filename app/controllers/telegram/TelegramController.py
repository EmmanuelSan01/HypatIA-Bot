# Procesar el mensaje recibido y enviarlo al LLM.

import asyncio
import logging
from typing import Optional
import httpx
from datetime import datetime

from app.models.telegram.TelegramModel import (
    TelegramWebhookRequest, 
    TelegramResponse, 
    TelegramMessage,
    ChatSession
)
from app.services.agent import TaekwondoAgent
from app.config import Config

# Configurar logger
logger = logging.getLogger(__name__)

class TelegramController:
    
    # Controlador para manejar la lógica de interacción con Telegram y el LLM
    
    
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.telegram_api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.agent = TaekwondoAgent()
        self.active_sessions = {}  
        
    async def process_message(self, webhook_data: TelegramWebhookRequest) -> None:
        try:
            # Extraer el mensaje (puede ser mensaje nuevo o editado)
            message = webhook_data.message or webhook_data.edited_message
            
            if not message or not message.text:
                logger.warning("Mensaje sin texto recibido")
                return
                
            # Obtener información del usuario y chat
            user = message.from_user
            chat = message.chat
            
            if not user:
                logger.warning("Mensaje sin información de usuario")
                return
            
            logger.info(f"Procesando mensaje de {user.first_name} ({user.id}): {message.text}")
            
            # Crear o actualizar sesión de chat
            session = await self._get_or_create_session(user, chat)
            
            # Procesar mensaje con el LLM
            response_text = await self._process_with_llm(message.text, session)
            
            # Enviar respuesta a Telegram
            await self._send_telegram_message(chat.id, response_text, message.message_id)
            
            # Actualizar sesión
            await self._update_session(session)
            
            # Registrar interacción en la base de datos
            await self._log_interaction(session, message.text, response_text)
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            # Enviar mensaje de error al usuario
            if 'message' in locals() and message:
                await self._send_error_message(message.chat.id)
    
    async def _get_or_create_session(self, user, chat) -> ChatSession:
        
        # Obtiene o crea una sesión de chat para el usuario
        
        session_key = f"{user.id}_{chat.id}"
        
        if session_key in self.active_sessions:
            session = self.active_sessions[session_key]
            session.last_activity = datetime.now()
        else:
            session = ChatSession(
                user_id=user.id,
                chat_id=chat.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            self.active_sessions[session_key] = session
            
        return session
    
    async def _process_with_llm(self, message_text: str, session: ChatSession) -> str:
    
        try:
            # Definir user_info usando datos de la sesión
            user_info = {
                "user_id": session.user_id,
                "chat_id": session.chat_id,
                "username": session.username,
                "first_name": session.first_name,
                "last_name": session.last_name
            }

            # Procesar con el agente de Taekwondo (sin Qdrant por ahora)
            response = await self.agent.process_message(
                message_text, 
                user_info=user_info,
                context=None,       # Sin contexto vectorial por simplicidad
                chat_history=[]     # Sin historial por simplicidad
            )
        
            return response
        
        except asyncio.TimeoutError:
            logger.error("Timeout al procesar mensaje con LLM")
            return "⏰ Lo siento, la respuesta está tardando más de lo esperado. Por favor, intenta de nuevo."
            
        except Exception as e:
            logger.error(f"Error al procesar con LLM: {str(e)}")
            return "🤖 Disculpa, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?"
        
    async def _get_relevant_context(self, message_text: str) -> Optional[str]:
        return None
    
    async def _get_recent_chat_history(self, session: ChatSession) -> list:
        
        # Obtiene el historial reciente de chat para contexto
        
        return []
    
    async def _send_telegram_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> bool:
        
        try:
            telegram_response = TelegramResponse(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.telegram_api_url}/sendMessage",
                    json=telegram_response.dict(exclude_none=True),
                    timeout=30.0
                )
                
                response.raise_for_status()
                logger.info(f"Mensaje enviado exitosamente a chat {chat_id}")
                return True
                
        except httpx.TimeoutException:
            logger.error(f"Timeout enviando mensaje a chat {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Error enviando mensaje a Telegram: {str(e)}")
            return False
    
    async def _send_error_message(self, chat_id: int) -> None:
        
        # Envía un mensaje de error genérico al usuario
        
        error_message = "🚫 Ups! Algo salió mal. Nuestro equipo técnico ya está trabajando en solucionarlo. Por favor, intenta de nuevo en unos minutos."
        await self._send_telegram_message(chat_id, error_message)
    
    async def _update_session(self, session: ChatSession) -> None:
        
        # Actualiza la información de la sesión
        
        session.last_activity = datetime.now()
        session.message_count += 1
    
    async def _log_interaction(self, session: ChatSession, user_message: str, bot_response: str) -> None:
        
        # Registra la interacción en la base de datos para logs y análisis
        
        try:
            # Aquí implementarías la lógica para guardar en la BD
            # usando las tablas chat y mensaje del DDL proporcionado
            logger.info(f"Interacción registrada - Usuario: {session.user_id}, Mensajes: {session.message_count}")
        except Exception as e:
            logger.error(f"Error registrando interacción: {str(e)}")
    
    async def cleanup_inactive_sessions(self, max_idle_minutes: int = 30) -> None:
        
        # Limpia sesiones inactivas para liberar memoria
        
        current_time = datetime.now()
        inactive_sessions = []
        
        for session_key, session in self.active_sessions.items():
            idle_time = (current_time - session.last_activity).total_seconds() / 60
            if idle_time > max_idle_minutes:
                inactive_sessions.append(session_key)
        
        for session_key in inactive_sessions:
            del self.active_sessions[session_key]
            
        if inactive_sessions:
            logger.info(f"Limpiadas {len(inactive_sessions)} sesiones inactivas")