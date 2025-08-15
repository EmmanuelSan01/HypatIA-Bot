import os
from decouple import config


class Config:
    
    # Configuración simplificada para el bot de Telegram
    
    
    # Configuración básica
    DEBUG = config('DEBUG', default=True, cast=bool)
    SECRET_KEY = config('SECRET_KEY', default='change-this-secret-key')
    
    # Telegram Bot (REQUERIDO)
    TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
    
    # LLM - Groq
    GROQ_API_KEY = config('GROQ_API_KEY', default='')
    
    # Base de datos (opcional)
    DB_HOST = config('DB_HOST', default='localhost')
    DB_USER = config('DB_USER', default='root')
    DB_PASSWORD = config('DB_PASSWORD', default='')
    DB_NAME = config('DB_NAME', default='baekho')
    
    # Configuración del servidor
    HOST = config('HOST', default='0.0.0.0')
    PORT = config('PORT', default=8000, cast=int)
    
    # Bot settings
    BOT_NAME = config('BOT_NAME', default='BaekhoBot')
    
    @classmethod
    def validate_required(cls):
        # Valida configuración mínima requerida
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("❌ TELEGRAM_BOT_TOKEN es requerido")
        
        if not any([cls.GROQ_API_KEY]):
            raise ValueError("❌ Se requiere al menos una API key de LLM (GROQ_API_KEY recomendado)")
        
        print("✅ Configuración válida")
        return True