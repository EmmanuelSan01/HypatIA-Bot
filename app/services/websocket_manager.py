"""
WebSocket Manager para enviar notificaciones en tiempo real
"""
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Maneja conexiones WebSocket activas para notificaciones en tiempo real"""
    
    def __init__(self):
        # Almacenar conexiones WebSocket activas
        self.active_connections: Set[WebSocket] = set()
        # Mapear usuarios a sus conexiones (para notificaciones específicas)
        self.user_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Acepta una nueva conexión WebSocket"""
        await websocket.accept()
        self.active_connections.add(websocket)
        if user_id:
            self.user_connections[user_id] = websocket
        logger.info(f"Nueva conexión WebSocket activa. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Remueve una conexión WebSocket"""
        self.active_connections.discard(websocket)
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        logger.info(f"Conexión WebSocket desconectada. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Envía un mensaje a una conexión específica"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error enviando mensaje personal: {e}")
            self.active_connections.discard(websocket)
    
    async def send_to_user(self, user_id: int, message: str):
        """Envía un mensaje a un usuario específico"""
        if user_id in self.user_connections:
            websocket = self.user_connections[user_id]
            await self.send_personal_message(message, websocket)
    
    async def broadcast(self, message: str):
        """Envía un mensaje a todas las conexiones activas"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error en broadcast: {e}")
                disconnected.add(connection)
        
        # Limpiar conexiones muertas
        for connection in disconnected:
            self.active_connections.discard(connection)
    
    async def notify_new_message(self, chat_id: str, user_id: int, message: str, is_user: bool = True):
        """Notifica sobre un nuevo mensaje en el chat"""
        notification = {
            "type": "chat_update",
            "data": {
                "chatId": chat_id,
                "userId": user_id,
                "ultimoMensaje": message[:100],  # Limitar longitud
                "isUser": is_user,
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast(json.dumps(notification, ensure_ascii=False))
        logger.info(f"Notificación de nuevo mensaje enviada para chat {chat_id}")
    
    async def notify_user_activity(self, user_id: int, activity: str):
        """Notifica sobre actividad del usuario"""
        notification = {
            "type": "user_update",
            "data": {
                "id": user_id,
                "activity": activity,
                "isOnline": True,
                "lastSeen": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast(json.dumps(notification, ensure_ascii=False))

# Instancia global del manager
websocket_manager = WebSocketManager()
