"""
Inicializador de aplicación para pre-cargar servicios y optimizar latencia
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AppInitializer:
    """Inicializador que pre-carga servicios críticos para reducir latencia"""
    
    def __init__(self):
        self._initialization_status: Dict[str, Any] = {}
        self._startup_time: float = 0
        
    async def initialize_application(self) -> Dict[str, Any]:
        """
        Inicializa todos los servicios críticos de la aplicación
        Se debe llamar al startup de FastAPI
        """
        logger.info("🚀 Iniciando pre-carga de servicios de la aplicación...")
        start_time = datetime.now()
        
        # 1. Pre-cargar ServiceManager y servicios singleton
        await self._preload_service_manager()
        
        # 2. Verificar conexiones de base de datos
        await self._verify_database_connections()
        
        # 3. Inicializar Qdrant collection si no existe
        await self._initialize_vector_store()
        
        # 4. Pre-cargar agentes Langroid
        await self._preload_agents()
        
        # 5. Verificar Redis cache
        await self._verify_redis_cache()
        
        self._startup_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Aplicación inicializada en {self._startup_time:.2f}s")
        
        return {
            "status": "success",
            "startup_time": self._startup_time,
            "services_status": self._initialization_status,
            "timestamp": datetime.now().isoformat(),
            "ready_for_requests": True
        }
    
    async def _preload_service_manager(self):
        """Pre-carga el ServiceManager y todos sus servicios"""
        try:
            logger.info("📦 Pre-cargando ServiceManager...")
            
            from app.services.service_manager import service_manager
            stats = service_manager.preload_services()
            
            self._initialization_status['service_manager'] = {
                "status": "success",
                "stats": stats,
                "message": "ServiceManager pre-cargado exitosamente"
            }
            
        except Exception as e:
            logger.error(f"❌ Error pre-cargando ServiceManager: {e}")
            self._initialization_status['service_manager'] = {
                "status": "error",
                "error": str(e),
                "message": "Error pre-cargando ServiceManager"
            }
    
    async def _verify_database_connections(self):
        """Verifica las conexiones de base de datos"""
        try:
            logger.info("🗄️  Verificando conexiones de base de datos...")
            
            # Verificar MySQL
            from app.database import get_sync_connection
            connection = get_sync_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                connection.close()
                
                self._initialization_status['mysql'] = {
                    "status": "success",
                    "message": "Conexión MySQL verificada"
                }
                
            except Exception as e:
                logger.error(f"❌ Error verificando MySQL: {e}")
                self._initialization_status['mysql'] = {
                    "status": "error",
                    "error": str(e)
                }
            
        except Exception as e:
            logger.error(f"❌ Error en verificación de bases de datos: {e}")
            self._initialization_status['database'] = {
                "status": "error",
                "error": str(e)
            }
    
    async def _initialize_vector_store(self):
        """Inicializa Qdrant vector store"""
        try:
            logger.info("🔍 Inicializando vector store...")
            
            from app.services.service_manager import service_manager
            qdrant_service = service_manager.get_qdrant_service()
            
            # Crear collection si no existe
            qdrant_service.create_collection_if_not_exists()
            
            # Verificar estado de la collection
            collection_info = qdrant_service.get_collection_info()
            
            self._initialization_status['vector_store'] = {
                "status": "success",
                "collection_info": collection_info,
                "message": "Vector store inicializado"
            }
            
        except Exception as e:
            logger.error(f"❌ Error inicializando vector store: {e}")
            self._initialization_status['vector_store'] = {
                "status": "error",
                "error": str(e)
            }
    
    async def _preload_agents(self):
        """Pre-carga los agentes Langroid"""
        try:
            logger.info("🤖 Pre-cargando agentes Langroid...")
            
            from app.agents import HypatiaAgentFactory
            
            # Pre-crear el agente principal
            main_agent = HypatiaAgentFactory.create_main_agent()
            
            self._initialization_status['langroid_agents'] = {
                "status": "success",
                "agent_type": type(main_agent).__name__,
                "message": "Agentes Langroid pre-cargados"
            }
            
        except Exception as e:
            logger.error(f"❌ Error pre-cargando agentes: {e}")
            self._initialization_status['langroid_agents'] = {
                "status": "error",
                "error": str(e)
            }
    
    async def _verify_redis_cache(self):
        """Verifica la conexión y funcionamiento de Redis cache"""
        try:
            logger.info("🔴 Verificando Redis cache...")
            
            from app.services.service_manager import service_manager
            redis_cache = service_manager.get_redis_cache()
            
            # Test básico de Redis
            test_key = "health_check"
            test_value = "ok"
            
            redis_cache.set(test_key, test_value, expire_seconds=10)
            retrieved_value = redis_cache.get(test_key)
            
            if retrieved_value == test_value:
                redis_cache.delete(test_key)
                
                self._initialization_status['redis_cache'] = {
                    "status": "success",
                    "message": "Redis cache funcionando correctamente"
                }
            else:
                raise Exception("Test de lectura/escritura falló")
            
        except Exception as e:
            logger.error(f"❌ Error verificando Redis cache: {e}")
            self._initialization_status['redis_cache'] = {
                "status": "error",
                "error": str(e)
            }
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de inicialización"""
        return {
            "startup_time": self._startup_time,
            "services_status": self._initialization_status,
            "total_services": len(self._initialization_status),
            "successful_services": len([s for s in self._initialization_status.values() if s["status"] == "success"]),
            "failed_services": len([s for s in self._initialization_status.values() if s["status"] == "error"]),
            "ready": all(s["status"] == "success" for s in self._initialization_status.values())
        }
    
    def is_ready(self) -> bool:
        """Verifica si la aplicación está lista para recibir requests"""
        return bool(self._initialization_status) and all(
            s["status"] == "success" for s in self._initialization_status.values()
        )

# Instancia global del inicializador
app_initializer = AppInitializer()
