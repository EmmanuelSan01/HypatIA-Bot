from typing import List, Optional
import pymysql
from app.database import get_sync_connection
from app.models.chat.ChatModel import ChatCreate, ChatUpdate, ChatResponse

class ChatController:
    
    @staticmethod
    def create_chat(chat: ChatCreate) -> ChatResponse:
        """Create a new chat"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO chat (usuarioId, chatId, ultimoMensaje, totalMensajes) 
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    chat.usuarioId, chat.chatId, chat.ultimoMensaje, chat.totalMensajes
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
                
                if not update_fields:
                    return ChatController.get_chat_by_id(chat_id)
                
                values.append(chat_id)
                sql = f"UPDATE chat SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(sql, values)
                connection.commit()
                
                return ChatController.get_chat_by_id(chat_id)
        finally:
            connection.close()
    
    @staticmethod
    def delete_chat(chat_id: int) -> bool:
        """Delete chat"""
        connection = get_sync_connection()
        try:
            with connection.cursor() as cursor:
                sql = "DELETE FROM chat WHERE id = %s"
                cursor.execute(sql, (chat_id,))
                connection.commit()
                return cursor.rowcount > 0
        finally:
            connection.close()
