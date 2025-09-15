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
import asyncio
import time

whatsapp_controller = WhatsAppController()

@whatsapp_router.post("")
async def receive_whatsapp_webhook(request: Request):
    start_time = time.time()
    body = await request.json()
    logger.info(f"Webhook POST recibido: {body}")
    # Procesar el mensaje en segundo plano para responder rápido
    asyncio.create_task(whatsapp_controller.process_message(body))
    elapsed = time.time() - start_time
    logger.info(f"Tiempo de respuesta webhook: {elapsed:.3f} segundos")
    return {"status": "ok"}
