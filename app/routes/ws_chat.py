from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
import logging
from app.services.langroid_service import LangroidAgentService

logger = logging.getLogger(__name__)
ws_router = APIRouter()

# Instancia global del servicio de agentes
langroid_service = LangroidAgentService()

@ws_router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket conectado")
    import json
    try:
        while True:
            try:
                data = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info("WebSocket desconectado por el cliente.")
                break
            
            logger.info(f"Mensaje recibido por WebSocket: {data}")
            
            # Validar que el mensaje no esté vacío ni sea solo espacios
            if not data or not data.strip():
                continue
                
            # Intentar parsear como JSON para filtrar mensajes tipo 'ping'
            try:
                msg_obj = json.loads(data)
                msg_type = msg_obj.get("type")
                
                # Ignorar mensajes tipo 'ping' y otros que no sean de usuario
                if msg_type == "ping":
                    logger.info("🚫 Ignorando mensaje tipo 'ping'")
                    continue
                    
                if msg_type != "message":
                    logger.info(f"🚫 Ignorando mensaje tipo '{msg_type}'")
                    continue
                    
                user_message = msg_obj.get("data", {}).get("message", "")
                if not user_message.strip():
                    logger.info("🚫 Ignorando mensaje vacío dentro de JSON")
                    continue
                    
                # Procesar solo el mensaje del usuario
                process_input = user_message
                logger.info(f"✅ Procesando mensaje de usuario: {process_input}")
                
            except Exception:
                # Si no es JSON, procesar como antes
                process_input = data
                logger.info(f"✅ Procesando mensaje de texto plano: {process_input}")
            
            response = ""
            try:
                result = await langroid_service.process_message(message=process_input)
                response = result.get("reply", "Error procesando mensaje")
                
                # Asegurar que la respuesta sea string
                if not isinstance(response, str):
                    for attr in ["content", "text", "message", "body"]:
                        if hasattr(response, attr):
                            response = getattr(response, attr)
                            break
                    if not isinstance(response, str):
                        try:
                            response_dict = response if isinstance(response, dict) else response.__dict__
                            for key in ["content", "text", "message", "body"]:
                                if key in response_dict:
                                    response = response_dict[key]
                                    break
                        except Exception:
                            pass
                    if not isinstance(response, str):
                        response = str(response)
                        
            except Exception as e:
                logger.error(f"Error procesando mensaje por WebSocket: {e}")
                response = "Error interno del chatbot."
                
            await websocket.send_text(response)
            
    except WebSocketDisconnect:
        logger.info("WebSocket desconectado por el cliente (fuera del bucle).")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        await websocket.close()
