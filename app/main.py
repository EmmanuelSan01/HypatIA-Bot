"""
SportBot Backend - Asistente de Taekwondo para Telegram
Versión simplificada para funcionamiento básico
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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
    title="SportBot - Asistente de Taekwondo",
    description="Bot de Telegram especializado en Taekwondo",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de Telegram
app.include_router(telegram_router)


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": f"¡{Config.BOT_NAME} está funcionando! 🥋",
        "status": "active",
        "telegram_configured": bool(Config.TELEGRAM_BOT_TOKEN),
        "llm_configured": any([Config.GROQ_API_KEY])
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "bot": Config.BOT_NAME}


if __name__ == "__main__":
    logger.info(f"🚀 Iniciando {Config.BOT_NAME}...")
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info"
    )