import logging
import httpx
import time
from app.config import Config
from typing import Dict, Any, Optional
import logging
import asyncio
import re
from fastapi import HTTPException
from app.database import get_sync_connection
from app.controllers.chat.ChatController import ChatController
from app.services.websocket_manager import websocket_manager
from app.controllers.usuario.UsuarioController import UsuarioController

logger = logging.getLogger(__name__)

class WhatsAppController:
    """
    Controlador para manejar la lógica de interacción con WhatsApp y el LLM
    """
    def __init__(self):
        self.app_id = Config.APP_ID
        self.app_secret = Config.APP_SECRET
        self.access_token = Config.ACCESS_TOKEN
        self.phone_id = Config.PHONE_ID
        self.webhook_url = Config.WEBHOOK
        self.chat_controller = ChatController()
        self.usuario_controller = UsuarioController()

    def _fix_markdown_format(self, text: str) -> str:
        """Reemplaza pares de asteriscos dobles por uno solo en el texto."""
        if not isinstance(text, str):
            return text
        return text.replace('**', '*')

    async def process_message(self, webhook_data: dict) -> None:
        try:
            # Extraer el mensaje y datos del usuario desde el webhook de WhatsApp
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            contacts = value.get("contacts", [{}])

            # Validar timestamp del mensaje para evitar procesar mensajes antiguos
            MAX_AGE_SECONDS = 300  # 5 minutos
            if messages and isinstance(messages, list) and len(messages) > 0:
                message_ts = messages[0].get("timestamp")
                if message_ts:
                    try:
                        # WhatsApp timestamp is usually in seconds (UNIX epoch)
                        msg_time = int(message_ts)
                        now = int(time.time())
                        age = now - msg_time
                        if age > MAX_AGE_SECONDS:
                            logger.info(f"Mensaje ignorado por antigüedad ({age}s > {MAX_AGE_SECONDS}s): {messages[0]}")
                            return
                    except Exception as e:
                        logger.error(f"Error validando timestamp del mensaje: {e}")
                        # Si hay error, procesar normalmente
            # Solo procesar si hay mensajes y el tipo es 'text'
            if not messages or not isinstance(messages, list) or len(messages) == 0:
                logger.info("Evento recibido sin mensajes de usuario. Ignorando.")
                return
            message = messages[0]
            if message.get("type") != "text":
                logger.info(f"Evento recibido de tipo '{message.get('type')}'. Solo se procesan mensajes de texto.")
                return
            text = message.get("text", {}).get("body")
            wa_user = message.get("from")
            wa_id = wa_user
            # Ignorar mensajes enviados por el propio bot para evitar bucles
            if wa_id == self.phone_id:
                logger.info(f"Mensaje recibido desde el propio bot (wa_id={wa_id}). Ignorando para evitar bucle.")
                return
            profile_name = None
            if contacts and isinstance(contacts, list) and contacts[0].get("profile"):
                profile_name = contacts[0]["profile"].get("name")
            if not text:
                logger.info("Mensaje de tipo texto recibido sin contenido. Ignorando.")
                return
            logger.info(f"Procesando mensaje de WhatsApp {wa_id}: {text}")
            usuario_id = await self._get_or_create_usuario(wa_id, profile_name)
            response_result = await self.chat_controller.process_message(
                message=text,
                user_id=usuario_id,
                chat_external_id=f"whatsapp_{wa_id}"
            )
            if response_result["status"] == "success":
                reply = response_result["data"]["reply"]
                # Si es string, usar directamente
                if isinstance(reply, str):
                    response_text = reply
                else:
                    # Intentar extraer el texto real de los atributos más comunes
                    response_text = None
                    for attr in ["content", "text", "message", "body"]:
                        if hasattr(reply, attr):
                            response_text = getattr(reply, attr)
                            break
                    # Si no se encontró, intentar convertir a dict y buscar claves
                    if response_text is None:
                        try:
                            reply_dict = reply if isinstance(reply, dict) else reply.__dict__
                            for key in ["content", "text", "message", "body"]:
                                if key in reply_dict:
                                    response_text = reply_dict[key]
                                    break
                        except Exception:
                            pass
                    # Si sigue sin encontrarse, usar str pero loggear advertencia
                    if response_text is None:
                        logger.warning(f"Respuesta LLM enviada como objeto: {type(reply)}. Usando str(reply).")
                        response_text = str(reply)
            else:
                response_text = "🤖 Disculpa, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?"
            # Corrige el formato Markdown antes de enviar
            response_text = self._fix_markdown_format(response_text)
            await self._send_whatsapp_message(wa_id, response_text)
            
            # Enviar UNA SOLA notificación WebSocket sobre la conversación actualizada
            await websocket_manager.notify_new_message(
                chat_id=f"whatsapp_{wa_id}",
                user_id=usuario_id,
                message=response_text[:50] + "..." if len(response_text) > 50 else response_text,
                is_user=False
            )
            
            logger.info(f"Mensaje procesado exitosamente para usuario {wa_id}")
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            if 'wa_id' in locals():
                await self._send_error_message(wa_id)

    async def _get_or_create_usuario(self, wa_id: str, profile_name: str = None) -> int:
        try:
            usuarios = self.usuario_controller.get_all_usuarios()
            existing_user = None
            for usuario in usuarios:
                if usuario.username == (profile_name if profile_name else wa_id):
                    existing_user = usuario
                    break
            if existing_user:
                return existing_user.id
            from app.models.usuario.UsuarioModel import UsuarioCreate
            new_user = UsuarioCreate(
                username=profile_name if profile_name else wa_id,
                telefono=wa_id
            )
            created_user = self.usuario_controller.create_usuario(new_user)
            logger.info(f"Usuario creado: {created_user.username} (ID: {created_user.id})")
            return created_user.id
        except Exception as e:
            logger.error(f"Error obteniendo/creando usuario: {str(e)}")
            raise

    async def _send_whatsapp_message(self, wa_id: str, text: str) -> bool:
        try:
            url = f"https://graph.facebook.com/v23.0/{self.phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": wa_id,
                "type": "text",
                "text": {"body": text}
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
            logger.info(f"Mensaje enviado exitosamente a WhatsApp {wa_id}")
            return True
        except httpx.TimeoutException:
            logger.error(f"Timeout enviando mensaje a WhatsApp {wa_id}")
            return False
        except Exception as e:
            logger.error(f"Error enviando mensaje a WhatsApp: {str(e)}")
            return False

    async def _send_error_message(self, wa_id: str) -> None:
        error_message = (
            "🚫 Ups! Algo salió mal. Nuestro equipo técnico ya está trabajando en solucionarlo. "
            "Por favor, intenta de nuevo en unos minutos."
        )
        await self._send_whatsapp_message(wa_id, error_message)
