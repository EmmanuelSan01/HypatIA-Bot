import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuración de la aplicación usando Pydantic"""
    
    # Configuración de la base de datos
    database_url: str = "mysql://root:admin@db:3306/sportbot_db"
    mysql_root_password: str = "admin"
    mysql_database: str = "sportbot_db"
    mysql_user: str = "sportbot_user"
    mysql_password: str = "sportbot_pass"
    
    # Configuración de Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "sportbot_collection"
    
    # Configuración de Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    
    # Configuración de la API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Configuración de seguridad
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Configuración de logs
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Instancia global de configuración
settings = Settings()

# Función para obtener la URL de conexión a la base de datos
def get_database_url() -> str:
    """Obtiene la URL de conexión a la base de datos"""
    return settings.database_url

# Función para obtener la configuración de Qdrant
def get_qdrant_config() -> dict:
    """Obtiene la configuración de Qdrant"""
    return {
        "host": settings.qdrant_host,
        "port": settings.qdrant_port,
        "collection": settings.qdrant_collection
    }

# Función para obtener la configuración de Redis
def get_redis_config() -> dict:
    """Obtiene la configuración de Redis"""
    return {
        "host": settings.redis_host,
        "port": settings.redis_port
    }
