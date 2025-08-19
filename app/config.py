import os
from decouple import config

class Config:
    
    # Configuración para el bot de Telegram
    DEBUG = config('DEBUG', default=True, cast=bool)
    SECRET_KEY = config('SECRET_KEY', default='change-this-secret-key')
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
    
    # LLM - OpenAI
    OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
    
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
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("❌ OPENAI_API_KEY es requerido")
        elif not cls.OPENAI_API_KEY.startswith('sk-'):
            errors.append("❌ OPENAI_API_KEY debe comenzar con 'sk-'")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        print("✅ Configuración válida")
        return True
