from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Import all route modules
from app.routes.categoria.CategoriaRoutes import router as categoria_router
from app.routes.curso.CursoRoutes import router as curso_router
from app.routes.promocion.PromocionRoutes import router as promocion_router
from app.routes.promocionCurso.PromocionCursoRoutes import router as promocion_curso_router
from app.routes.usuario.UsuarioRoutes import router as usuario_router
from app.routes.chat.ChatRoutes import router as chat_router, admin_router as chat_admin_router, messages_router
from app.routes.ingest.IngestRoutes import router as ingest_router
from app.routes.whatsapp.WhatsAppWebhookRoutes import whatsapp_router as whatsapp_webhook_router

from app.services.qdrant import QdrantService
from app.services.data_sync import DataSyncService
from app.services.langroid_service import LangroidAgentService
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="DeepLearning Backend API with Langroid Multi-Agent System, RAG capabilities, complete CRUD operations, and persistent chat system",
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(categoria_router, prefix="/api/v1")
app.include_router(curso_router, prefix="/api/v1")
app.include_router(promocion_router, prefix="/api/v1")
app.include_router(promocion_curso_router, prefix="/api/v1")
app.include_router(usuario_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(chat_admin_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")  # Nueva ruta para mensajes
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(whatsapp_webhook_router)

langroid_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize RAG components and Langroid Multi-Agent System on application startup"""
    global langroid_service
    try:
        logger.info("Initializing RAG components and Langroid Multi-Agent System...")
        
        # Initialize Qdrant service
        qdrant_service = QdrantService()
        qdrant_service.create_collection_if_not_exists()
        logger.info("Qdrant collection initialized successfully")
        
        logger.info("Initializing Langroid Multi-Agent System...")
        langroid_service = LangroidAgentService()
        if langroid_service.is_available():
            logger.info("✅ Langroid Multi-Agent System initialized successfully")
            agent_info = langroid_service.get_agent_info()
            logger.info(f"Available agents: {list(agent_info['agents'].keys())}")
        else:
            logger.warning("⚠️ Langroid system initialized but agents not available")
        
        logger.info("Starting initial data synchronization...")
        data_sync = DataSyncService()
        sync_result = await data_sync.sync_all_data()
        
        if sync_result['status'] == 'success':
            logger.info(f"✅ Initial sync completed: {sync_result['synced_count']} documents")
        else:
            logger.error(f"❌ Sync failed: {sync_result['message']}")
        
        logger.info("RAG and Langroid initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        # Don't fail startup, but log the error
        logger.warning("Application started with limited capabilities")

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "DeepLearning Backend API with Langroid Multi-Agent System",
        "version": settings.VERSION,
        "status": "running",
        "features": [
            "CRUD Operations", 
            "Langroid Multi-Agent Chat System",
            "RAG with Semantic Search", 
            "Data Synchronization",
            "Persistent Chat System",
            "Message History",
            "Telegram Integration",
            "Conversation Analytics",
            "Sales Recommendations"
        ],
        "agent_system": "Langroid Multi-Agent Framework"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/rag-status")
async def rag_status():
    """Check RAG system status"""
    try:
        data_sync = DataSyncService()
        status = await data_sync.get_sync_status()
        return {
            "rag_enabled": True,
            "sync_status": status
        }
    except Exception as e:
        return {
            "rag_enabled": False,
            "error": str(e)
        }

@app.get("/langroid-status")
async def langroid_status():
    """Check Langroid Multi-Agent System status"""
    global langroid_service
    try:
        if langroid_service:
            agent_info = langroid_service.get_agent_info()
            return {
                "langroid_enabled": True,
                "agents_available": langroid_service.is_available(),
                "system_info": agent_info
            }
        else:
            return {
                "langroid_enabled": False,
                "error": "Langroid service not initialized"
            }
    except Exception as e:
        return {
            "langroid_enabled": False,
            "error": str(e)
        }

@app.get("/api/v1/assistant")
async def get_assistant_info():
    """Información del asistente comercial"""
    global langroid_service
    base_info = {
        "name": "HypatIA 🎓",
        "type": "multi_agent_educational_assistant",
        "capabilities": [
            "multi_agent_orchestration",
            "semantic_course_search",
            "educational_recommendations", 
            "conversation_analytics",
            "persistent_conversations",
            "chat_history",
            "message_management",
            "real_time_knowledge_access"
        ]
    }
    
    if langroid_service and langroid_service.is_available():
        langroid_info = langroid_service.get_agent_info()
        base_info.update({
            "framework": langroid_info.get("framework"),
            "agents": langroid_info.get("agents"),
            "version": langroid_info.get("version")
        })
    
    return base_info

@app.get("/api/v1/conversation-analytics")
async def get_conversation_analytics(chat_id: int = None, user_id: int = None):
    """Get conversation analytics from Langroid system"""
    global langroid_service
    try:
        if langroid_service:
            analytics = await langroid_service.get_conversation_analytics(chat_id, user_id)
            return {
                "status": "success",
                "data": analytics
            }
        else:
            return {
                "status": "error",
                "message": "Langroid service not available"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error obteniendo analytics: {str(e)}"
        }

@app.post("/api/v1/reset-conversation")
async def reset_conversation_context(user_id: int = None):
    """Reset conversation context for user"""
    global langroid_service
    try:
        if langroid_service:
            await langroid_service.reset_conversation_context(user_id)
            return {
                "status": "success",
                "message": f"Contexto de conversación reseteado para usuario {user_id}"
            }
        else:
            return {
                "status": "error",
                "message": "Langroid service not available"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error reseteando contexto: {str(e)}"
        }


from fastapi import HTTPException
import requests

@app.post("/setup-webhook")
async def setup_webhook(webhook_url: str):
    """
    Configura el webhook de Telegram
    """
    from app.config import Config
    if not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url es requerido")

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
    from app.config import Config
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
    from app.config import Config
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

@app.post("/api/v1/sync-data")
async def manual_sync():
    """Endpoint para sincronización manual de datos"""
    try:
        logger.info("Manual data synchronization requested")
        data_sync = DataSyncService()
        sync_result = await data_sync.sync_all_data()
        return sync_result
    except Exception as e:
        logger.error(f"Error in manual sync: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en sincronización manual: {str(e)}",
            "synced_count": 0
        }

@app.get("/api/v1/sync-status")
async def get_sync_status():
    """Obtener estado actual de la sincronización"""
    try:
        data_sync = DataSyncService()
        status = await data_sync.get_sync_status()
        return status
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error obteniendo estado: {str(e)}",
            "data": None
        }

from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"}
    )


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Obtener puerto y host de variables de entorno (para Render) o usar valores por defecto
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=settings.DEBUG
    )