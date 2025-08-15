# Lógica de interacción con el LLM.

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

from app.config import Config

logger = logging.getLogger(__name__)

class TaekwondoAgent:
    """
    Agente especializado en Taekwondo que maneja las conversaciones con el LLM
    """
    
    def __init__(self):
        self.groq_client = None
        self.anthropic_client = None
        
        # Configurar clientes según las variables de entorno disponibles
        if Config.GROQ_API_KEY and AsyncGroq:
            try:
                self.groq_client = AsyncGroq(api_key=Config.GROQ_API_KEY)
                self.primary_provider = "groq"
                logger.info("✅ Cliente Groq inicializado")
            except Exception as e:
                logger.error(f"Error inicializando Groq: {e}")
        else:
            logger.warning("⚠️ No se encontró configuración válida para LLM")
            self.primary_provider = None
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el asistente de Taekwondo
        """
        return """
Eres un asistente especializado en Taekwondo, conocido como BaekhoBot. Tu objetivo es brindar información precisa, útil sobre productos respecto a esta arte marcial.

CARACTERÍSTICAS PRINCIPALES:
- Eres experto en Taekwondo: productos, tallas, colores, equipamiento
- Brindas información sobre productos relacionados (doboks, cinturones, protecciones, etc.)
- Puedes informar sobre promociones, descuentos y recomendaciones de productos
- Eres motivador y alentador con los practicantes
- Mantienes un tono amigable y profesional

INFORMACIÓN QUE PUEDES PROPORCIONAR:
- Técnicas básicas y avanzadas de Taekwondo
- Información sobre grados/cinturones y requisitos
- Consejos de entrenamiento y acondicionamiento físico
- Información sobre equipamiento y gear necesario
- Beneficios físicos y mentales de practicar Taekwondo
- Promociones y descuentos disponibles en productos

ESTILO DE COMUNICACIÓN:
- Usa emojis relacionados con artes marciales cuando sea apropiado (🥋 🥇 💪 ⚡)
- Sé conciso pero informativo
- Si no sabes algo específico, sé honesto y ofrece buscar la información
- Siempre mantén una actitud positiva y motivadora

IMPORTANTE: 
- No eres una tienda, pero puedes dar información sobre productos y promociones
- Si alguien pregunta sobre compras, dirige hacia los canales de venta apropiados
- Prioriza siempre la seguridad en la práctica del Taekwondo
        """.strip()
    
    async def process_message(
        self, 
        message: str, 
        user_info: str = "", 
        context: Optional[str] = None,
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        try:
            # Construir el prompt completo
            full_prompt = self._build_full_prompt(message, user_info, context, chat_history)
            
            # Procesar con el proveedor principal
            if self.primary_provider == "groq" and self.groq_client:
                return await self._process_with_groq(full_prompt)
            elif self.primary_provider == "anthropic" and self.anthropic_client:
                return await self._process_with_anthropic(full_prompt)
            else:
                return self._get_fallback_response(message)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje con LLM: {str(e)}")
            return self._get_error_response()
    
    def _build_full_prompt(
        self, 
        message: str, 
        user_info: str = "", 
        context: Optional[str] = None,
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        
        # Construye el prompt completo para el LLM
        
        prompt_parts = []
        
        # Agregar contexto si está disponible
        if context:
            prompt_parts.append(f"CONTEXTO RELEVANTE:\n{context}\n")
        
        # Agregar historial de chat si está disponible
        if chat_history:
            prompt_parts.append("CONVERSACIÓN RECIENTE:")
            for msg in chat_history[-3:]:  # Solo los últimos 3 mensajes
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prompt_parts.append(f"{role}: {content}")
            prompt_parts.append("")
        
        # Agregar información del usuario
        if user_info:
            prompt_parts.append(f"USUARIO: {user_info}\n")
        
        # Agregar mensaje actual
        prompt_parts.append(f"MENSAJE: {message}")
        
        return "\n".join(prompt_parts)
    
    async def _process_with_groq(self, prompt: str) -> str:
        
        # Procesa el mensaje usando Groq
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            response = await asyncio.wait_for(
                self.groq_client.chat.completions.create(
                    model="mixtral-8x7b-32768",  # o "llama2-70b-4096"
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                ),
                timeout=30.0
            )
            
            return response.choices[0].message.content.strip()
            
        except asyncio.TimeoutError:
            raise Exception("Timeout al procesar con Groq")
        except Exception as e:
            logger.error(f"Error con Groq: {str(e)}")
            raise e
    
    def _get_fallback_response(self, message: str) -> str:
        
        # Genera una respuesta básica cuando no hay LLM disponible
        
        message_lower = message.lower()
        
        # Respuestas básicas para consultas comunes
        if any(word in message_lower for word in ['hola', 'hello', 'hi', 'buenas']):
            return "🥋 ¡Hola! Soy BaekhoBot, tu asistente de Taekwondo. ¿En qué puedo ayudarte hoy?"
        
        elif any(word in message_lower for word in ['cinturon', 'grado', 'nivel']):
            return """🥋 En Taekwondo tenemos diferentes grados:
            
**Grados KUP (cinturones de color):**
- 10º-9º KUP: Blanco
- 8º KUP: Amarillo
- 7º KUP: Naranja
- 6º KUP: Verde
- 5º KUP: Azul
- 4º-1º KUP: Rojo

**Grados DAN (cinturón negro):**
- 1º a 9º DAN

¿Te gustaría saber sobre los requisitos para algún grado específico?"""
        
        elif any(word in message_lower for word in ['tecnica', 'patada', 'golpe']):
            return """🥇 El Taekwondo se caracteriza por sus técnicas de pierna:

**Patadas básicas:**
- Ap chagi (patada frontal)
- Dollyo chagi (patada circular)
- Yeop chagi (patada lateral)
- Dwi chagi (patada hacia atrás)

**Técnicas de mano:**
- Jireugi (puñetazo directo)
- Makki (bloqueos)

¿Quieres información más detallada sobre alguna técnica específica?"""
        
        elif any(word in message_lower for word in ['equipo', 'dobok', 'proteccion']):
            return """🥋 **Equipamiento básico de Taekwondo:**

- **Dobok**: Uniforme tradicional
- **Ti**: Cinturón según tu grado
- **Protecciones**: Peto, casco, espinilleras, antebrazos
- **Bucal**: Protector dental

¡Tenemos promociones especiales en equipamiento! ¿Te interesa algún producto en particular?"""
        
        else:
            return """🤖 Lo siento, en este momento tengo capacidades limitadas. 

Soy BaekhoBot, tu asistente de Taekwondo. Puedo ayudarte con:
- Información sobre técnicas y grados
- Equipamiento y productos
- Historia y filosofía del Taekwondo
- Consejos de entrenamiento

¿En qué te gustaría que te ayude? 🥋"""
    
    def _get_error_response(self) -> str:
        """
        Respuesta de error genérica
        """
        return """🤖 Disculpa, tuve un problema técnico momentáneo. 

Soy BaekhoBot, tu asistente de Taekwondo 🥋. Por favor, intenta tu pregunta de nuevo en unos segundos.

Mientras tanto, ¿sabías que el Taekwondo significa "el camino del pie y el puño"? ¡Sigamos entrenando juntos! 💪"""
    
    async def get_product_recommendations(self, user_query: str, user_level: str = "") -> str:
        """
        Obtiene recomendaciones de productos basadas en la consulta del usuario
        """
        # Esta función podría conectar con la base de datos para obtener productos reales
        recommendations_prompt = f"""
El usuario pregunta: {user_query}
Nivel del usuario: {user_level}

Basándote en esta información, recomienda productos de Taekwondo apropiados y menciona si hay promociones disponibles.
        """
        
        return await self.process_message(recommendations_prompt)
    
    def is_available(self) -> bool:
        return self.primary_provider is not None