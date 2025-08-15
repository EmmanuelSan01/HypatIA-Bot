from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Import all route modules
from app.routes.categoria.CategoriaRoutes import router as categoria_router
from app.routes.producto.ProductoRoutes import router as producto_router
from app.routes.promocion.PromocionRoutes import router as promocion_router
from app.routes.usuario.UsuarioRoutes import router as usuario_router
from app.routes.chat.ChatRoutes import router as chat_router

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="SportBot Backend API with complete CRUD operations",
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

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "SportBot Backend API",
        "version": settings.VERSION,
        "status": "running"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
