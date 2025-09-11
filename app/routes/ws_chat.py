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
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Mensaje recibido por WebSocket: {data}")
            # Procesar el mensaje con el agente
            response = ""
            try:
                # Puedes agregar lógica para extraer user_id si lo envía el frontend
                result = await langroid_service.process_message(message=data)
                response = result.get("reply", "Error procesando mensaje")
                # Asegurar que la respuesta sea string
                if not isinstance(response, str):
                    # Intentar extraer texto de atributos comunes
                    for attr in ["content", "text", "message", "body"]:
                        if hasattr(response, attr):
                            response = getattr(response, attr)
                            break
                    # Si sigue sin ser string, convertir a string
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
        logger.info("WebSocket desconectado")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        await websocket.close()
