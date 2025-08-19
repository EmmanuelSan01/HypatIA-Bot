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
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
