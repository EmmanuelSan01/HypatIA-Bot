from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Import all route modules
from app.routes.categoria.CategoriaRoutes import router as categoria_router
from app.routes.producto.ProductoRoutes import router as producto_router
from app.routes.promocion.PromocionRoutes import router as promocion_router
from app.routes.usuario.UsuarioRoutes import router as usuario_router
from app.routes.chat.ChatRoutes import router as chat_router
from app.routes.ingest.IngestRoutes import router as ingest_router

from app.services.qdrant import QdrantService
from app.services.data_sync import DataSyncService
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="SportBot Backend API with RAG capabilities and complete CRUD operations",
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
app.include_router(producto_router, prefix="/api/v1")
app.include_router(promocion_router, prefix="/api/v1")
app.include_router(usuario_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize RAG components on application startup"""
    try:
        logger.info("Initializing RAG components...")
        
        # Initialize Qdrant service
        qdrant_service = QdrantService()
        qdrant_service.create_collection_if_not_exists()
        logger.info("Qdrant collection initialized successfully")
        
        # Optional: Perform initial data synchronization
        # Uncomment the following lines if you want automatic sync on startup
        # logger.info("Starting initial data synchronization...")
        # data_sync = DataSyncService()
        # sync_result = await data_sync.sync_all_data()
        # logger.info(f"Initial sync completed: {sync_result['synced_count']} documents")
        
        logger.info("RAG initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error during RAG initialization: {str(e)}")
        # Don't fail startup, but log the error
        logger.warning("Application started without RAG capabilities")

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "SportBot Backend API with RAG",
        "version": settings.VERSION,
        "status": "running",
        "features": ["CRUD Operations", "RAG Chat", "Data Synchronization"]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
