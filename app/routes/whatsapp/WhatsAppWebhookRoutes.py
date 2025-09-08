from fastapi import APIRouter, Request, HTTPException
import logging
from app.config import Config

logger = logging.getLogger(__name__)

whatsapp_router = APIRouter(prefix="/webhook", tags=["whatsapp"])


@whatsapp_router.get("")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    verify_token = params.get("hub.verify_token")
    if mode == "subscribe" and verify_token == Config.VERIFY_TOKEN:
        logger.info(f"Webhook verificado correctamente: challenge={challenge}")
        return int(challenge)
    logger.warning(f"Intento de verificación fallido: mode={mode}, token={verify_token}")
    raise HTTPException(status_code=403, detail="Verificación de webhook fallida")


# Endpoint POST para recibir mensajes de WhatsApp y procesarlos
from app.controllers.whatsapp.WhatsAppController import WhatsAppController
whatsapp_controller = WhatsAppController()

@whatsapp_router.post("")
async def receive_whatsapp_webhook(request: Request):
    body = await request.json()
    logger.info(f"Webhook POST recibido: {body}")
    try:
        await whatsapp_controller.process_message(body)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
