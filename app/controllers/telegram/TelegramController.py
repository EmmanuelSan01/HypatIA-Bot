# Controlador mejorado con mejor manejo de respuestas largas y contexto

import asyncio
import logging
from typing import Optional, List
import httpx
from datetime import datetime
import re

from app.models.telegram.TelegramModel import (
    TelegramWebhookRequest, 
    TelegramResponse, 
    TelegramMessage,
    ChatSession
)
from app.services.agent import EnhancedBaekhoAgent  
from app.config import Config

logger = logging.getLogger(__name__)

class EnhancedTelegramController:
    # Controlador mejorado con división automática de mensajes largos
    
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.telegram_api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.agent = EnhancedBaekhoAgent()
        self.active_sessions = {}
        
        # Configuración de mensajes
        self.max_message_length = 4096  # Límite de Telegram
        self.preferred_message_length = 600  # Longitud preferida para UX
        
    async def process_message(self, webhook_data: TelegramWebhookRequest) -> None:
        # Procesa mensaje con mejor manejo de respuestas largas
        try:
            # Extraer el mensaje
            message = webhook_data.message or webhook_data.edited_message
            
            if not message or not message.text:
                logger.warning("Mensaje sin texto recibido")
                return
                
            user = message.from_user
            chat = message.chat
            
            if not user:
                logger.warning("Mensaje sin información de usuario")
                return
            
            logger.info(f"📨 Mensaje de {user.first_name} ({user.id}): {message.text[:100]}...")
            
            # Crear sesión
            session = await self._get_or_create_session(user, chat)
            
            # Procesar con el agente mejorado
            response_text = await self._process_with_enhanced_agent(message.text, session)
            
            # Dividir y enviar respuesta si es muy larga
            await self._send_smart_response(chat.id, response_text, message.message_id)
            
            # Actualizar sesión
            await self._update_session(session)
            
            # Log para seguimiento
            await self._log_interaction(session, message.text, response_text)
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {str(e)}")
            if 'message' in locals() and message:
                await self._send_error_message(message.chat.id)
    
    async def _get_or_create_session(self, user, chat) -> ChatSession:
        # Gestión mejorada de sesiones
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
    
    async def _process_with_enhanced_agent(self, message_text: str, session: ChatSession) -> str:
        """Procesa con el agente mejorado usando contexto de sesión"""
        try:
            # Información del usuario para el agente
            user_info = {
                "user_id": str(session.user_id),
                "chat_id": session.chat_id,
                "username": session.username,
                "first_name": session.first_name,
                "last_name": session.last_name,
                "message_count": session.message_count
            }

            # Procesar con timeout
            response = await asyncio.wait_for(
                self.agent.process_message(message_text, user_info),
                timeout=15.0
            )
            
            return response
        
        except asyncio.TimeoutError:
            logger.error("⏰ Timeout procesando con agente mejorado")
            return "⏰ Disculpa, estoy procesando tu consulta. Dame un momento y vuelve a preguntar."
            
        except Exception as e:
            logger.error(f"❌ Error con agente mejorado: {str(e)}")
            return "🤖 Tuve un pequeño problema. ¿Puedes repetir tu consulta de otra forma?"
    
    async def _send_smart_response(self, chat_id: int, response_text: str, reply_to_message_id: Optional[int] = None) -> None:
        """Envía respuesta dividiéndola inteligentemente si es muy larga"""
        
        # Si el mensaje es corto, enviarlo completo
        if len(response_text) <= self.preferred_message_length:
            await self._send_telegram_message(chat_id, response_text, reply_to_message_id)
            return
        
        # Dividir el mensaje de forma inteligente
        message_parts = self._split_message_intelligently(response_text)
        
        # Enviar cada parte con pequeño delay
        for i, part in enumerate(message_parts):
            if i == 0:
                # Primera parte con reply
                await self._send_telegram_message(chat_id, part, reply_to_message_id)
            else:
                # Partes subsiguientes sin reply, con delay
                await asyncio.sleep(0.5)  # Pequeña pausa entre mensajes
                await self._send_telegram_message(chat_id, part)
    
    def _split_message_intelligently(self, text: str) -> List[str]:
        """Divide mensajes largos de forma inteligente"""
        if len(text) <= self.preferred_message_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Dividir por párrafos primero
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # Si añadir este párrafo excede el límite
            if len(current_part + paragraph) > self.preferred_message_length:
                # Si hay contenido actual, guardarlo
                if current_part:
                    parts.append(current_part.strip())
                    current_part = ""
                
                # Si el párrafo solo es muy largo, dividirlo por oraciones
                if len(paragraph) > self.preferred_message_length:
                    sentences = self._split_by_sentences(paragraph)
                    for sentence in sentences:
                        if len(current_part + sentence) > self.preferred_message_length:
                            if current_part:
                                parts.append(current_part.strip())
                                current_part = sentence
                            else:
                                # Oración muy larga, forzar división
                                parts.append(sentence[:self.preferred_message_length])
                                current_part = sentence[self.preferred_message_length:]
                        else:
                            current_part += sentence
                else:
                    current_part = paragraph
            else:
                current_part += "\n\n" + paragraph if current_part else paragraph
        
        # Añadir la última parte
        if current_part:
            parts.append(current_part.strip())
        
        # Asegurar que ninguna parte exceda el límite absoluto de Telegram
        final_parts = []
        for part in parts:
            if len(part) > self.max_message_length:
                # División forzada si excede límite de Telegram
                while part:
                    final_parts.append(part[:self.max_message_length])
                    part = part[self.max_message_length:]
            else:
                final_parts.append(part)
        
        return final_parts
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Divide texto por oraciones"""
        # Usar regex para dividir por puntos, pero evitar abreviaciones comunes
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _send_telegram_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> bool:
        """Envía mensaje individual a Telegram"""
        try:
            telegram_response = TelegramResponse(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id,
                parse_mode="HTML"  # Permitir formato HTML básico
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.telegram_api_url}/sendMessage",
                    json=telegram_response.dict(exclude_none=True),
                    timeout=30.0
                )
                
                response.raise_for_status()
                logger.debug(f"✅ Mensaje enviado a chat {chat_id}")
                return True
                
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout enviando mensaje a chat {chat_id}")
            return False
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {str(e)}")
            return False
    
    async def _send_error_message(self, chat_id: int) -> None:
        """Mensaje de error más amigable"""
        error_message = "🤖 ¡Ups! Algo salió mal temporalmente.\n\n¿Puedes intentar de nuevo? Estoy aquí para ayudarte. 🥋"
        await self._send_telegram_message(chat_id, error_message)
    
    async def _update_session(self, session: ChatSession) -> None:
        """Actualiza información de sesión"""
        session.last_activity = datetime.now()
        session.message_count += 1
    
    async def _log_interaction(self, session: ChatSession, user_message: str, bot_response: str) -> None:
        """Log de interacciones para análisis"""
        try:
            # Truncar mensajes muy largos para logging
            user_msg_short = user_message[:200] + "..." if len(user_message) > 200 else user_message
            bot_response_short = bot_response[:200] + "..." if len(bot_response) > 200 else bot_response
            
            logger.info(
                f"💬 Chat {session.chat_id} | Usuario: {user_msg_short} | "
                f"Bot: {bot_response_short} | Msg#{session.message_count}"
            )
            
            # Aquí se puede implementar guardado en BD
            # await self._save_to_database(session, user_message, bot_response)
            
        except Exception as e:
            logger.error(f"❌ Error registrando interacción: {str(e)}")
    
    async def cleanup_inactive_sessions(self, max_idle_minutes: int = 30) -> None:
        """Limpieza automática de sesiones inactivas"""
        current_time = datetime.now()
        inactive_sessions = []
        
        for session_key, session in self.active_sessions.items():
            idle_time = (current_time - session.last_activity).total_seconds() / 60
            if idle_time > max_idle_minutes:
                inactive_sessions.append(session_key)
        
        for session_key in inactive_sessions:
            del self.active_sessions[session_key]
            
        if inactive_sessions:
            logger.info(f"🧹 Limpiadas {len(inactive_sessions)} sesiones inactivas")
    
    async def get_session_summary(self, user_id: str) -> dict:
        """Obtiene resumen de sesión para debugging"""
        try:
            return self.agent.get_conversation_summary(user_id)
        except Exception as e:
            logger.error(f"Error obteniendo resumen de sesión: {e}")
            return {"error": "No se pudo obtener resumen"}
    
    async def force_reset_session(self, user_id: str, chat_id: int) -> bool:
        """Reinicia sesión de usuario forzadamente"""
        try:
            session_key = f"{user_id}_{chat_id}"
            if session_key in self.active_sessions:
                del self.active_sessions[session_key]
                logger.info(f"🔄 Sesión reiniciada para usuario {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error reiniciando sesión: {e}")
            return False