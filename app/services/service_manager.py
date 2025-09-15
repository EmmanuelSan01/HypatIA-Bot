"""
Gestor centralizado de servicios para optimizar la latencia del chatbot
Implementa singleton pattern y connection pooling para servicios críticos
"""
import logging
import threading
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ServiceManager:
    """Gestor singleton para servicios críticos del chatbot"""
    
    _instance: Optional['ServiceManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._embedding_service: Optional[Any] = None
            self._qdrant_service: Optional[Any] = None
            self._redis_cache: Optional[Any] = None
            self._initialization_times: Dict[str, float] = {}
            self._initialized = True
            logger.info("ServiceManager singleton inicializado")
    
    def get_embedding_service(self):
        """Obtiene instancia singleton del EmbeddingService"""
        if self._embedding_service is None:
            logger.info("Inicializando EmbeddingService singleton...")
            start_time = datetime.now()
            
            from app.services.embedding import EmbeddingService
            self._embedding_service = EmbeddingService()
            
            init_time = (datetime.now() - start_time).total_seconds()
            self._initialization_times['embedding'] = init_time
            logger.info(f"EmbeddingService inicializado en {init_time:.2f}s")
        
        return self._embedding_service
    
    def get_qdrant_service(self):
        """Obtiene instancia singleton del QdrantService"""
        if self._qdrant_service is None:
            logger.info("Inicializando QdrantService singleton...")
            start_time = datetime.now()
            
            from app.services.qdrant import QdrantService
            self._qdrant_service = QdrantService()
            
            init_time = (datetime.now() - start_time).total_seconds()
            self._initialization_times['qdrant'] = init_time
            logger.info(f"QdrantService inicializado en {init_time:.2f}s")
        
        return self._qdrant_service
    
    def get_redis_cache(self):
        """Obtiene instancia singleton del RedisCache"""
        if self._redis_cache is None:
            logger.info("Inicializando RedisCache singleton...")
            start_time = datetime.now()
            
            from app.services.redis_cache import RedisCache
            self._redis_cache = RedisCache()
            
            init_time = (datetime.now() - start_time).total_seconds()
            self._initialization_times['redis'] = init_time
            logger.info(f"RedisCache inicializado en {init_time:.2f}s")
        
        return self._redis_cache
    
    def preload_services(self):
        """Pre-carga todos los servicios críticos al inicio de la aplicación"""
        logger.info("🚀 Iniciando pre-carga de servicios críticos...")
        
        services = [
            ('embedding', self.get_embedding_service),
            ('qdrant', self.get_qdrant_service),
            ('redis', self.get_redis_cache)
        ]
        
        total_start = datetime.now()
        
        for service_name, service_getter in services:
            try:
                service_getter()
                logger.info(f"✅ {service_name} service pre-cargado")
            except Exception as e:
                logger.error(f"❌ Error pre-cargando {service_name} service: {e}")
        
        total_time = (datetime.now() - total_start).total_seconds()
        logger.info(f"🎯 Pre-carga completada en {total_time:.2f}s")
        
        return self.get_initialization_stats()
    
    def get_initialization_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de inicialización de servicios"""
        return {
            "total_services": len(self._initialization_times),
            "initialization_times": self._initialization_times.copy(),
            "total_init_time": sum(self._initialization_times.values()),
            "services_loaded": {
                "embedding": self._embedding_service is not None,
                "qdrant": self._qdrant_service is not None,
                "redis": self._redis_cache is not None
            }
        }
    
    def reset_services(self):
        """Reinicia todos los servicios (útil para testing)"""
        logger.warning("🔄 Reiniciando todos los servicios...")
        self._embedding_service = None
        self._qdrant_service = None
        self._redis_cache = None
        self._initialization_times.clear()

# Instancia global del service manager
service_manager = ServiceManager()
