from typing import List, Optional, Dict
import pymysql
from datetime import datetime
from app.database import get_sync_connection
from app.models.chat.ChatModel import ChatCreate, ChatUpdate, ChatResponse
from app.models.mensaje.MensajeModel import MensajeCreate, MensajeResponse
from app.services.langroid_service import LangroidAgentService, HypatiaLangroidAgent
from app.services.data_sync import DataSyncService

class ChatController:
    def __init__(self):
        self.agent_service = HypatiaLangroidAgent()
        self.langroid_service = LangroidAgentService()
        self.data_sync_service = DataSyncService()
        self.user_course_context = {}  # Diccionario para guardar el curso actual por usuario
        self.recent_context = {}  # Diccionario para guardar los últimos 4 mensajes por usuario

    async def process_message(self, message: str, user_id: Optional[int] = None, chat_external_id: Optional[str] = None) -> Dict:
        """Process message using Langroid Multi-Agent System and persist conversation, manteniendo solo los últimos 4 mensajes en contexto"""
        try:
            # --- Actualizar contexto reciente ---
            if user_id is not None:
                if user_id not in self.recent_context:
                    self.recent_context[user_id] = []
                # Añadir mensaje del usuario
                self.recent_context[user_id].append({"role": "user", "message": message})
                # Mantener solo los últimos 4 mensajes
                self.recent_context[user_id] = self.recent_context[user_id][-4:]
            
            curso_actual = self.user_course_context.get(user_id)
            curso_id = self._extract_curso_id(message)
            if curso_id:
                self.user_course_context[user_id] = curso_id
                curso_actual = curso_id
            # Preparar contexto para el modelo: 2 últimos usuario, 2 últimos bot
            context_msgs = self.recent_context.get(user_id, [])
            user_msgs = [m["message"] for m in context_msgs if m["role"] == "user"][-2:]
            bot_msgs = [m["message"] for m in context_msgs if m["role"] == "bot"][-2:]
            context_for_model = []
            # Intercalar para mantener orden cronológico
            for m in context_msgs[-4:]:
                context_for_model.append(m)
            # --- Llamar al modelo con contexto ---
            if self._is_detalle_query(message) and curso_actual:
                response = await self.langroid_service.process_message(
                    message=message,
                    user_id=user_id,
                    persist_conversation=True,
                    curso_id=curso_actual,
                    context=context_for_model
                )
            else:
                response = await self.langroid_service.process_message(
                    message=message,
                    user_id=user_id,
                    persist_conversation=True,
                    context=context_for_model
                )
            bot_reply = response.get("reply", "")
            chat_id = response.get("chat_id")
            conversation_stats = response.get("conversation_stats", {})
            # Guardar mensajes en la base de datos y actualizar contexto reciente
            if user_id and not chat_id:
                chat_record = await self._get_or_create_chat(user_id, chat_external_id)
                await self._store_message(
                    chat_id=chat_record['id'],
                    tipo='usuario',
                    contenido=message
                )
                await self._store_message(
                    chat_id=chat_record['id'],
                    tipo='bot',
                    contenido=bot_reply
                )
                await self._update_chat_summary(chat_record['id'], message)
                chat_id = chat_record['id']
            # Añadir respuesta del bot al contexto reciente
            if user_id is not None:
                self.recent_context[user_id].append({"role": "bot", "message": bot_reply})
                self.recent_context[user_id] = self.recent_context[user_id][-4:]
            return {
                "status": response.get("status", "success"),
                "message": response.get("message", "Consulta procesada exitosamente"),
                "data": {
                    "reply": bot_reply,
                    "sources": [],
                    "relevance_score": 1.0,
                    "context_used": context_for_model,
                    "chat_id": chat_id,
                    "agent_used": response.get("agent_used", "langroid_multi_agent"),
                    "conversation_stats": conversation_stats,
                    "timestamp": response.get("timestamp")
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error procesando mensaje: {str(e)}",
                "data": {
                    "reply": "Lo siento, ocurrió un error procesando tu consulta. Por favor intenta nuevamente.",
                    "sources": [],
                    "relevance_score": 0.0,
                    "agent_used": "error",
                    "error_details": str(e)
                }
            }
    
    async def get_conversation_analytics(self, chat_id: Optional[int] = None, user_id: Optional[int] = None) -> Dict:
        """Get conversation analytics from Langroid system"""
        try:
            return await self.langroid_service.get_conversation_analytics(chat_id, user_id)
        except Exception as e:
            return {"error": f"Error obteniendo analytics: {str(e)}"}
    
    async def reset_conversation_context(self, user_id: Optional[int] = None):
        """Reset conversation context in Langroid system"""
        try:
            await self.langroid_service.reset_conversation_context(user_id)
        except Exception as e:
            print(f"Error resetting context: {str(e)}")
    
    def get_agent_system_info(self) -> Dict:
        """Get information about the current agent system"""
        return self.langroid_service.get_agent_info()
    
    def is_agent_system_available(self) -> bool:
        """Check if the Langroid agent system is available"""
        return self.langroid_service.is_available()

    async def _get_or_create_chat(self, user_id: int, chat_external_id: Optional[str] = None) -> Dict:
        """Get existing chat or create new one for user"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                # Try to find existing chat
                if chat_external_id:
                    sql_check = """
                    SELECT * FROM chat 
                    WHERE usuarioId = %s AND chatId = %s 
                    ORDER BY fechaCreacion DESC LIMIT 1
                    """
                    cursor.execute(sql_check, (user_id, chat_external_id))
                else:
                    sql_check = """
                    SELECT * FROM chat 
                    WHERE usuarioId = %s 
                    ORDER BY fechaCreacion DESC LIMIT 1
                    """
                    cursor.execute(sql_check, (user_id,))
                
                chat_record = cursor.fetchone()
                
                if not chat_record:
                    # Create new chat
                    chat_id_external = chat_external_id or f"chat_{user_id}_{int(datetime.now().timestamp())}"
                    sql_insert = """
                    INSERT INTO chat (usuarioId, chatId, ultimoMensaje, totalMensajes, fechaCreacion, fechaActualizcion) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    now = datetime.now()
                    cursor.execute(sql_insert, (user_id, chat_id_external, "", 0, now, now))
                    connection.commit()
                    
                    # Get the created chat
                    new_chat_id = cursor.lastrowid
                    cursor.execute("SELECT * FROM chat WHERE id = %s", (new_chat_id,))
                    chat_record = cursor.fetchone()
                
                return chat_record
        finally:
            connection.close()
    
    async def _store_message(self, chat_id: int, tipo: str, contenido: str) -> int:
        """Store a message in the mensaje table"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO mensaje (chatId, tipo, contenido, fechaCreacion) 
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (chat_id, tipo, contenido, datetime.now()))
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()
    
    async def _update_chat_summary(self, chat_id: int, last_message: str):
        """Update chat with last message and increment message count"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                UPDATE chat 
                SET ultimoMensaje = %s, 
                    totalMensajes = totalMensajes + 2, 
                    fechaActualizcion = %s
                WHERE id = %s
                """
                cursor.execute(sql, (last_message, datetime.now(), chat_id))
                connection.commit()
        finally:
            connection.close()
    
    def get_chat_history(self, chat_id: int, limit: int = 50) -> List[MensajeResponse]:
        """Get chat message history"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT * FROM mensaje 
                WHERE chatId = %s 
                ORDER BY fechaCreacion ASC 
                LIMIT %s
                """
                cursor.execute(sql, (chat_id, limit))
                messages = cursor.fetchall()
                return [MensajeResponse(**msg) for msg in messages]
        finally:
            connection.close()
    
    def get_recent_chat_history(self, chat_id: int, minutes: int = 60) -> List[MensajeResponse]:
        """Get recent chat messages within specified minutes"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT * FROM mensaje 
                WHERE chatId = %s 
                AND fechaCreacion >= DATE_SUB(NOW(), INTERVAL %s MINUTE)
                ORDER BY fechaCreacion ASC
                """
                cursor.execute(sql, (chat_id, minutes))
                messages = cursor.fetchall()
                return [MensajeResponse(**msg) for msg in messages]
        finally:
            connection.close()
    
    @staticmethod
    def create_chat(chat: ChatCreate) -> ChatResponse:
        """Create a new chat"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO chat (usuarioId, chatId, ultimoMensaje, totalMensajes, fechaCreacion, fechaActualizcion) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                now = datetime.now()
                cursor.execute(sql, (
                    chat.usuarioId, chat.chatId, chat.ultimoMensaje, 
                    chat.totalMensajes, now, now
                ))
                connection.commit()
                
                chat_id = cursor.lastrowid
                return ChatController.get_chat_by_id(chat_id)
        finally:
            connection.close()
    
    @staticmethod
    def get_all_chats() -> List[ChatResponse]:
        """Get all chats"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM chat ORDER BY fechaCreacion DESC"
                cursor.execute(sql)
                result = cursor.fetchall()
                return [ChatResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def get_chat_by_id(chat_id: int) -> Optional[ChatResponse]:
        """Get chat by ID"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM chat WHERE id = %s"
                cursor.execute(sql, (chat_id,))
                result = cursor.fetchone()
                return ChatResponse(**result) if result else None
        finally:
            connection.close()
    
    @staticmethod
    def get_chats_by_usuario(usuario_id: int) -> List[ChatResponse]:
        """Get chats by usuario"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM chat WHERE usuarioId = %s ORDER BY fechaCreacion DESC"
                cursor.execute(sql, (usuario_id,))
                result = cursor.fetchall()
                return [ChatResponse(**row) for row in result]
        finally:
            connection.close()
    
    @staticmethod
    def update_chat(chat_id: int, chat: ChatUpdate) -> Optional[ChatResponse]:
        """Update chat"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                update_fields = []
                values = []
                
                if chat.ultimoMensaje is not None:
                    update_fields.append("ultimoMensaje = %s")
                    values.append(chat.ultimoMensaje)
                
                if chat.totalMensajes is not None:
                    update_fields.append("totalMensajes = %s")
                    values.append(chat.totalMensajes)
                
                if update_fields:
                    update_fields.append("fechaActualizcion = %s")
                    values.append(datetime.now())
                    values.append(chat_id)
                    
                    sql = f"UPDATE chat SET {', '.join(update_fields)} WHERE id = %s"
                    cursor.execute(sql, values)
                    connection.commit()
                
                return ChatController.get_chat_by_id(chat_id)
        finally:
            connection.close()
    
    @staticmethod
    def delete_chat(chat_id: int) -> bool:
        """Delete chat and all its messages"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                # Delete messages first (due to foreign key)
                sql_messages = "DELETE FROM mensaje WHERE chatId = %s"
                cursor.execute(sql_messages, (chat_id,))
                
                # Delete chat
                sql_chat = "DELETE FROM chat WHERE id = %s"
                cursor.execute(sql_chat, (chat_id,))
                connection.commit()
                return cursor.rowcount > 0
        finally:
            connection.close()
    
    def _is_curso_query(self, message: str) -> bool:
        # Implementa lógica para detectar si el mensaje es sobre un curso específico
        return "curso" in message.lower()

    def _extract_curso_id(self, message: str) -> Optional[str]:
        # Buscar el curso por nombre en la base de datos solo si hay nombre
        from app.models.curso.CursoModel import CursoModel
        nombre = self._extract_curso_nombre(message)
        if not nombre or len(nombre) < 3:
            return None
        cursos = CursoModel.get_all_cursos()
        for curso in cursos:
            if nombre.lower() in curso.titulo.lower():
                return str(curso.id)
        # Si no se encuentra ningún curso, retorna None sin provocar error
        return None

    def _extract_curso_nombre(self, message: str) -> Optional[str]:
        # Extrae el nombre del curso usando una expresión regular simple
        import re
        match = re.search(r'curso\s+([\w\s]+)', message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _is_detalle_query(self, message: str) -> bool:
        # Detecta si el usuario pregunta por detalles como precio, idioma, nivel, etc.
        detalles = ["precio", "idioma", "nivel", "cupo"]
        return any(det in message.lower() for det in detalles)