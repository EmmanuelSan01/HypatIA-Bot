<<<<<<< HEAD
# SportBot Backend - Asistente de Taekwondo para Telegram

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests

# Importar configuración y rutas
from app.config import Config
from app.routes.telegram.TelegramRoutes import telegram_router

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validar configuración al inicio
try:
    Config.validate_required()
except ValueError as e:
    logger.error(e)
    exit(1)

# Crear aplicación FastAPI
app = FastAPI(
    title="🥋 SportBot - Asistente de Taekwondo🥋",
    description="🤖 Bot de Telegram especializado en Taekwondo 🤖 ",
=======
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Crear instancia de FastAPI
app = FastAPI(
    title="SportBot API",
    description="API para asistente comercial deportivo",
>>>>>>> 3ae1d24c790c49c79141f24f2dc6eb23d67313e9
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
<<<<<<< HEAD
    allow_origins=["*"],
=======
    allow_origins=["*"],  # En producción, especificar dominios específicos
>>>>>>> 3ae1d24c790c49c79141f24f2dc6eb23d67313e9
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
# Incluir rutas de Telegram
app.include_router(telegram_router)


@app.get("/")
async def root():
    # Endpoint raíz
    return {
        "message": f"¡{Config.BOT_NAME} está funcionando! 🥋",
        "status": "active",
        "telegram_configured": bool(Config.TELEGRAM_BOT_TOKEN),
        "llm_configured": bool(Config.OPENAI_API_KEY)
    }


@app.get("/health")
async def health():
    # Health check
    return {"status": "healthy", "bot": Config.BOT_NAME}

# ENDPOINTS PARA CONFIGURAR WEBHOOK 

@app.post("/setup-webhook")
async def setup_webhook(webhook_url: str):
    
    # Configura el webhook de Telegram
    
    if not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url es requerido")
    
    # Construir la URL completa del webhook
    full_webhook_url = f"{webhook_url.rstrip('/')}/telegram/webhook"
    telegram_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook"
    
    try:
        response = requests.post(telegram_url, json={"url": full_webhook_url})
        result = response.json()
        
        if result.get("ok"):
            return {
                "status": "success",
                "message": "✅ Webhook configurado correctamente",
                "webhook_url": full_webhook_url,
                "telegram_response": result
            }
        else:
            raise HTTPException(status_code=400, detail=f"❌ Error de Telegram: {result}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error: {str(e)}")


@app.get("/webhook-info")
async def get_webhook_info():
    
    # Obtiene información del webhook actual de Telegram
    telegram_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(telegram_url)
        result = response.json()
        
        if result.get("ok"):
            webhook_info = result.get("result", {})
            return {
                "status": "success",
                "webhook_configured": bool(webhook_info.get("url")),
                "webhook_url": webhook_info.get("url", "No configurado"),
                "pending_updates": webhook_info.get("pending_update_count", 0),
                "last_error": webhook_info.get("last_error_message", "Ninguno"),
                "full_info": webhook_info
            }
        else:
            raise HTTPException(status_code=400, detail=f"❌ Error de Telegram: {result}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error: {str(e)}")


@app.delete("/webhook")
async def delete_webhook():
    # Elimina el webhook de Telegram
    telegram_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/deleteWebhook"
    
    try:
        response = requests.post(telegram_url)
        result = response.json()
        
        if result.get("ok"):
            return {
                "status": "success",
                "message": "✅ Webhook eliminado correctamente",
                "telegram_response": result
            }
        else:
            raise HTTPException(status_code=400, detail=f"❌ Error de Telegram: {result}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error: {str(e)}")


if __name__ == "__main__":
    logger.info(f"🚀 Iniciando {Config.BOT_NAME}...")
    uvicorn.run(
        "app.main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info"
    )
=======
@app.get("/")
async def root():
    """Endpoint raíz de la API"""
    return {
        "message": "SportBot API está funcionando correctamente",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Endpoint para verificar el estado de salud de la API"""
    return {
        "status": "healthy",
        "database": "connected",  # Aquí puedes agregar verificación real de DB
        "qdrant": "connected"     # Aquí puedes agregar verificación real de Qdrant
    }

@app.get("/api/v1/assistant")
async def get_assistant_info():
    """Información del asistente comercial"""
    return {
        "name": "SportBot Assistant",
        "type": "commercial_assistant",
        "capabilities": [
            "product_recommendations",
            "customer_support",
            "sales_analytics"
        ]
    }

# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
>>>>>>> 3ae1d24c790c49c79141f24f2dc6eb23d67313e9
