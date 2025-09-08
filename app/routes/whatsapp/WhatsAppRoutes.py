from fastapi import APIRouter, HTTPException
from app.controllers.whatsapp.WhatsAppController import WhatsAppController
import logging

logger = logging.getLogger(__name__)

whatsapp_router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
whatsapp_controller = WhatsAppController()

@whatsapp_router.post("/webhook")
async def whatsapp_webhook(request: dict):
    try:
        logger.info(f"Webhook recibido: {request}")
        await whatsapp_controller.process_message(request)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@whatsapp_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "whatsapp_bot"}
