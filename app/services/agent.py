"""
Agent.py - BaekhoBot: Asistente comercial especializado en productos de Taekwondo
Versión corregida con implementación adecuada de persistencia y mejoras en RAG
"""

import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

# Core imports
import openai
from sentence_transformers import SentenceTransformer
import numpy as np

# Database imports
from app.database import get_async_connection
from app.config import settings

logger = logging.getLogger(__name__)

# ==============================
# SISTEMA DE ESTADO CONVERSACIONAL
# ==============================

class ConversationPhase(Enum):
    GREETING = "greeting"
    NEEDS_ASSESSMENT = "needs_assessment"
    PRODUCT_RECOMMENDATION = "product_recommendation"
    PRICE_DISCUSSION = "price_discussion"
    SIZE_FITTING = "size_fitting"
    CLOSING = "closing"

class UserLevel(Enum):
    BEGINNER = "principiante"
    INTERMEDIATE = "intermedio"
    ADVANCED = "avanzado"
    COMPETITOR = "competidor"
    INSTRUCTOR = "instructor"

@dataclass
class ConversationState:
    """Estado conversacional con persistencia en BD"""
    user_id: str
    chat_id: int
    name: Optional[str] = None
    level: Optional[UserLevel] = None
    budget_range: Optional[str] = None
    phase: ConversationPhase = ConversationPhase.GREETING
    was_greeted: bool = False
    identified_needs: List[str] = None
    interested_categories: List[str] = None
    last_activity: datetime = None
    message_count: int = 0
    context_summary: str = ""
    
    def __post_init__(self):
        if self.identified_needs is None:
            self.identified_needs = []
        if self.interested_categories is None:
            self.interested_categories = []
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def to_dict(self) -> dict:
        """Convierte el estado a diccionario para BD"""
        return {
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'name': self.name,
            'level': self.level.value if self.level else None,
            'budget_range': self.budget_range,
            'phase': self.phase.value,
            'was_greeted': self.was_greeted,
            'identified_needs': json.dumps(self.identified_needs),
            'interested_categories': json.dumps(self.interested_categories),
            'last_activity': self.last_activity,
            'message_count': self.message_count,
            'context_summary': self.context_summary
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationState':
        """Crea estado desde diccionario de BD"""
        return cls(
            user_id=data['user_id'],
            chat_id=data['chat_id'],
            name=data.get('name'),
            level=UserLevel(data['level']) if data.get('level') else None,
            budget_range=data.get('budget_range'),
            phase=ConversationPhase(data['phase']),
            was_greeted=data.get('was_greeted', False),
            identified_needs=json.loads(data.get('identified_needs', '[]')),
            interested_categories=json.loads(data.get('interested_categories', '[]')),
            last_activity=data.get('last_activity', datetime.now()),
            message_count=data.get('message_count', 0),
            context_summary=data.get('context_summary', '')
        )

# ==============================
# SERVICIO DE PERSISTENCIA
# ==============================

class ConversationPersistence:
    """Maneja la persistencia de conversaciones en base de datos"""
    
    @staticmethod
    async def save_conversation_state(state: ConversationState) -> bool:
        """Guarda el estado conversacional en BD"""
        try:
            connection = await get_async_connection()
            async with connection.cursor() as cursor:
                # Crear tabla si no existe
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_states (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(100) NOT NULL,
                        chat_id BIGINT NOT NULL,
                        name VARCHAR(255),
                        level VARCHAR(50),
                        budget_range VARCHAR(100),
                        phase VARCHAR(50),
                        was_greeted BOOLEAN DEFAULT FALSE,
                        identified_needs JSON,
                        interested_categories JSON,
                        last_activity DATETIME,
                        message_count INT DEFAULT 0,
                        context_summary TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_user_chat (user_id, chat_id)
                    )
                """)
                
                # Insertar o actualizar estado
                state_dict = state.to_dict()
                await cursor.execute("""
                    INSERT INTO conversation_states 
                    (user_id, chat_id, name, level, budget_range, phase, was_greeted,
                        identified_needs, interested_categories, last_activity, 
                        message_count, context_summary)
                    VALUES (%(user_id)s, %(chat_id)s, %(name)s, %(level)s, %(budget_range)s,
                            %(phase)s, %(was_greeted)s, %(identified_needs)s, 
                            %(interested_categories)s, %(last_activity)s, 
                            %(message_count)s, %(context_summary)s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        level = VALUES(level),
                        budget_range = VALUES(budget_range),
                        phase = VALUES(phase),
                        was_greeted = VALUES(was_greeted),
                        identified_needs = VALUES(identified_needs),
                        interested_categories = VALUES(interested_categories),
                        last_activity = VALUES(last_activity),
                        message_count = VALUES(message_count),
                        context_summary = VALUES(context_summary)
                """, state_dict)
                
                await connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error guardando estado conversacional: {e}")
            return False
        finally:
            if 'connection' in locals():
                await connection.ensure_closed()
    
    @staticmethod
    async def load_conversation_state(user_id: str, chat_id: int) -> Optional[ConversationState]:
        """Carga el estado conversacional desde BD"""
        try:
            connection = await get_async_connection()
            async with connection.cursor() as cursor:
                await cursor.execute("""
                    SELECT * FROM conversation_states 
                    WHERE user_id = %s AND chat_id = %s
                """, (user_id, chat_id))
                
                result = await cursor.fetchone()
                if result:
                    return ConversationState.from_dict(result)
                return None
                
        except Exception as e:
            logger.error(f"Error cargando estado conversacional: {e}")
            return None
        finally:
            if 'connection' in locals():
                await connection.ensure_closed()
    
    @staticmethod
    async def save_message(user_id: str, chat_id: int, message: str, response: str, 
                            message_type: str = 'text') -> bool:
        """Guarda mensaje individual en el historial"""
        try:
            connection = await get_async_connection()
            async with connection.cursor() as cursor:
                # Crear tabla si no existe
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(100) NOT NULL,
                        chat_id BIGINT NOT NULL,
                        user_message TEXT NOT NULL,
                        bot_response TEXT NOT NULL,
                        message_type VARCHAR(50) DEFAULT 'text',
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_chat (user_id, chat_id),
                        INDEX idx_timestamp (timestamp)
                    )
                """)
                
                # Insertar mensaje
                await cursor.execute("""
                    INSERT INTO conversation_messages 
                    (user_id, chat_id, user_message, bot_response, message_type)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, chat_id, message, response, message_type))
                
                await connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error guardando mensaje: {e}")
            return False
        finally:
            if 'connection' in locals():
                await connection.ensure_closed()
    
    @staticmethod
    async def get_conversation_history(user_id: str, chat_id: int, 
                                        limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene historial de conversación"""
        try:
            connection = await get_async_connection()
            async with connection.cursor() as cursor:
                await cursor.execute("""
                    SELECT user_message, bot_response, timestamp, message_type
                    FROM conversation_messages 
                    WHERE user_id = %s AND chat_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (user_id, chat_id, limit))
                
                results = await cursor.fetchall()
                return list(reversed(results))  # Orden cronológico
                
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return []
        finally:
            if 'connection' in locals():
                await connection.ensure_closed()

# ==============================
# SERVICIO RAG SIMPLIFICADO
# ==============================

class SimpleRAGService:
    """Servicio RAG simplificado sin Langroid"""
    
    def __init__(self):
        self.model = None
        self.openai_client = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Inicializa los servicios RAG"""
        try:
            # Inicializar embedding model
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            logger.info("✅ Modelo de embeddings cargado")
            
            # Inicializar OpenAI
            if settings.OPENAI_API_KEY:
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("✅ Cliente OpenAI inicializado")
            else:
                logger.warning("⚠️ OpenAI API Key no configurada")
                
        except Exception as e:
            logger.error(f"Error inicializando servicios RAG: {e}")
    
    async def search_products(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Busca productos relevantes (implementación simplificada)"""
        try:
            # En una implementación real, aquí haríamos búsqueda vectorial en Qdrant
            # Por ahora, simulamos con búsqueda en BD
            connection = await get_async_connection()
            async with connection.cursor() as cursor:
                # Buscar productos por nombre o descripción
                search_terms = query.lower().split()
                conditions = []
                params = []
                
                for term in search_terms:
                    conditions.append("(LOWER(nombre) LIKE %s OR LOWER(descripcion) LIKE %s)")
                    params.extend([f'%{term}%', f'%{term}%'])
                
                if conditions:
                    sql = f"""
                        SELECT p.*, c.nombre as categoria_nombre
                        FROM productos p
                        LEFT JOIN categorias c ON p.categoriaId = c.id
                        WHERE {' OR '.join(conditions)}
                        LIMIT %s
                    """
                    params.append(limit)
                    await cursor.execute(sql, params)
                    results = await cursor.fetchall()
                    return results
                
            return []
            
        except Exception as e:
            logger.error(f"Error en búsqueda de productos: {e}")
            return []
        finally:
            if 'connection' in locals():
                await connection.ensure_closed()
    
    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Genera respuesta usando OpenAI"""
        try:
            if not self.openai_client:
                return self._get_fallback_response(prompt)
            
            full_prompt = f"{context}\n\nUsuario: {prompt}\nBaekhoBot:" if context else f"Usuario: {prompt}\nBaekhoBot:"
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=400,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generando respuesta OpenAI: {e}")
            return self._get_fallback_response(prompt)
    
    def _get_system_prompt(self) -> str:
        """Prompt del sistema optimizado"""
        return """Eres BaekhoBot 🥋, asistente comercial especializado en productos de Taekwondo.

CARACTERÍSTICAS:
- Experto en equipamiento: doboks, protecciones, cinturones, accesorios
- Asesor comercial enfocado en ventas y recomendaciones
- Respuestas concisas (máximo 400 caracteres)
- Siempre termina con pregunta para continuar la venta

PRODUCTOS PRINCIPALES:
🥋 DOBOKS: 100.000-1.000.000 COP (principiante a premium)
🛡️ PROTECCIONES: 160.000-4.000.000 COP (básicas a electrónicas)
🏅 CINTURONES: 32.000-240.000 COP (todos colores)
🥊 ACCESORIOS: 60.000-1.200.000 COP (paos, sacos, bolsas)

PROMOCIONES:
- Pack Inicio: 336.000 COP (ahorra 144.000)
- Pack Competidor: 1.200.000 COP (ahorra 400.000)
- Descuentos grupales: 15-25%

INSTRUCCIONES:
1. Identifica nivel del usuario (principiante, intermedio, avanzado)
2. Pregunta presupuesto antes de recomendar productos caros
3. Ofrece opciones específicas con precios
4. Menciona promociones relevantes
5. Guía hacia la compra con preguntas directas

ESTILO: Amigable, profesional, directo. Sin formato markdown visible."""
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Respuesta de emergencia"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["hola", "buenos", "saludos"]):
            return "🥋 ¡Hola! Soy BaekhoBot, especialista en productos de Taekwondo. ¿Qué necesitas: dobok, protecciones o cinturón? 🎯"
        elif "dobok" in prompt_lower:
            return "🥋 Tenemos doboks desde 100.000 COP (principiante) hasta 1.000.000 COP (premium). ¿Cuál es tu nivel en Taekwondo?"
        elif any(word in prompt_lower for word in ["proteccion", "casco", "peto"]):
            return "🛡️ Protecciones disponibles: básicas (160.000 COP) hasta completas electrónicas (4.000.000 COP). ¿Para qué nivel?"
        elif "precio" in prompt_lower:
            return "💰 Los precios varían según el nivel. ¿Eres principiante, intermedio o avanzado? Así te doy opciones exactas."
        else:
            return "🥋 Te ayudo con equipamiento de Taekwondo: doboks, protecciones, cinturones y accesorios. ¿Qué específicamente necesitas?"

# ==============================
# AGENTE PRINCIPAL MEJORADO
# ==============================

class EnhancedBaekhoAgent:
    """Agente principal con persistencia y RAG mejorado"""
    
    def __init__(self):
        self.rag_service = SimpleRAGService()
        self.persistence = ConversationPersistence()
        self.active_states: Dict[str, ConversationState] = {}
        logger.info("✅ EnhancedBaekhoAgent inicializado")
    
    def _get_state_key(self, user_id: str, chat_id: int) -> str:
        """Genera clave única para el estado"""
        return f"{user_id}_{chat_id}"
    
    async def get_conversation_state(self, user_id: str, chat_id: int) -> ConversationState:
        """Obtiene o crea estado conversacional"""
        state_key = self._get_state_key(user_id, chat_id)
        
        # Intentar desde cache
        if state_key in self.active_states:
            state = self.active_states[state_key]
            # Verificar si no es muy antigua (más de 1 hora)
            if datetime.now() - state.last_activity < timedelta(hours=1):
                return state
        
        # Cargar desde BD
        state = await self.persistence.load_conversation_state(user_id, chat_id)
        if not state:
            # Crear nuevo estado
            state = ConversationState(user_id=user_id, chat_id=chat_id)
        
        # Actualizar cache
        self.active_states[state_key] = state
        return state
    
    async def save_state(self, state: ConversationState) -> bool:
        """Guarda el estado en cache y BD"""
        state_key = self._get_state_key(state.user_id, state.chat_id)
        
        # Actualizar cache
        self.active_states[state_key] = state
        
        # Guardar en BD
        return await self.persistence.save_conversation_state(state)
    
    def analyze_message(self, message: str, state: ConversationState) -> Dict[str, Any]:
        """Analiza el mensaje y actualiza el estado"""
        message_lower = message.lower()
        
        analysis = {
            "intent": "general",
            "needs_rag_search": False,
            "search_query": "",
            "confidence": 0.8
        }
        
        # Detectar saludos
        if any(word in message_lower for word in ["hola", "buenos", "buenas", "saludos", "hi"]):
            analysis["intent"] = "greeting"
            state.was_greeted = True
            state.phase = ConversationPhase.NEEDS_ASSESSMENT
        
        # Detectar productos específicos
        elif "dobok" in message_lower or "uniforme" in message_lower:
            analysis["intent"] = "dobok_inquiry"
            analysis["needs_rag_search"] = True
            analysis["search_query"] = f"dobok uniforme taekwondo {message_lower}"
            if "doboks" not in state.interested_categories:
                state.interested_categories.append("doboks")
        
        elif any(word in message_lower for word in ["proteccion", "casco", "peto", "espinillera", "guante"]):
            analysis["intent"] = "protection_inquiry"
            analysis["needs_rag_search"] = True
            analysis["search_query"] = f"protecciones {message_lower}"
            if "protecciones" not in state.interested_categories:
                state.interested_categories.append("protecciones")
        
        elif "cinturon" in message_lower or "cinta" in message_lower:
            analysis["intent"] = "belt_inquiry"
            analysis["needs_rag_search"] = True
            analysis["search_query"] = f"cinturon cinta {message_lower}"
            if "cinturones" not in state.interested_categories:
                state.interested_categories.append("cinturones")
        
        # Detectar nivel del usuario
        if any(word in message_lower for word in ["principiante", "comenzar", "empezar", "nuevo"]):
            state.level = UserLevel.BEGINNER
        elif any(word in message_lower for word in ["intermedio", "verde", "azul"]):
            state.level = UserLevel.INTERMEDIATE
        elif any(word in message_lower for word in ["avanzado", "negro", "competir"]):
            state.level = UserLevel.ADVANCED
        
        # Detectar presupuesto
        if any(word in message_lower for word in ["barato", "economico", "poco dinero"]):
            state.budget_range = "Bajo (menos de 300.000 COP)"
        elif any(word in message_lower for word in ["premium", "mejor calidad", "alto"]):
            state.budget_range = "Alto (más de 800.000 COP)"
        
        return analysis
    
    async def process_message(self, message: str, user_info: Dict[str, Any] = None) -> str:
        """Procesa mensaje con persistencia y RAG"""
        try:
            # Extraer información del usuario
            user_id = user_info.get('user_id', 'unknown') if user_info else 'unknown'
            chat_id = user_info.get('chat_id', 0) if user_info else 0
            
            # Obtener estado conversacional
            state = await self.get_conversation_state(user_id, chat_id)
            
            # Analizar mensaje
            analysis = self.analyze_message(message, state)
            
            # Construir contexto para la respuesta
            context = self._build_context(state, analysis)
            
            # Realizar búsqueda RAG si es necesario
            if analysis["needs_rag_search"]:
                products = await self.rag_service.search_products(analysis["search_query"])
                if products:
                    context += self._format_product_context(products)
            
            # Generar respuesta
            response = await self.rag_service.generate_response(message, context)
            response = self._clean_response(response)
            
            # Actualizar estado
            state.message_count += 1
            state.last_activity = datetime.now()
            state.context_summary = f"Últimos temas: {', '.join(state.interested_categories[-3:])}" if state.interested_categories else ""
            
            # Guardar estado y mensaje
            await self.save_state(state)
            await self.persistence.save_message(user_id, chat_id, message, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            return "🥋 Tengo un pequeño problema técnico. ¿Puedes repetir tu consulta? Estoy aquí para ayudarte con productos de Taekwondo."
    
    def _build_context(self, state: ConversationState, analysis: Dict[str, Any]) -> str:
        """Construye contexto conversacional"""
        context_parts = ["CONTEXTO DEL USUARIO:"]
        
        if state.name:
            context_parts.append(f"- Nombre: {state.name}")
        if state.level:
            context_parts.append(f"- Nivel: {state.level.value}")
        if state.budget_range:
            context_parts.append(f"- Presupuesto: {state.budget_range}")
        if state.interested_categories:
            context_parts.append(f"- Intereses: {', '.join(state.interested_categories)}")
        
        context_parts.append(f"- Fase conversacional: {state.phase.value}")
        context_parts.append(f"- Mensajes intercambiados: {state.message_count}")
        context_parts.append(f"- Ya saludado: {'Sí' if state.was_greeted else 'No'}")
        
        return "\n".join(context_parts)
    
    def _format_product_context(self, products: List[Dict[str, Any]]) -> str:
        """Formatea contexto de productos encontrados"""
        if not products:
            return ""
        
        context_parts = ["\n\nPRODUCTOS DISPONIBLES EN CATÁLOGO:"]
        
        for product in products[:3]:  # Máximo 3 productos
            context_parts.append(f"- {product.get('nombre', 'N/A')}")
            context_parts.append(f"  💰 Precio: ${product.get('precio', 'N/A')} COP")
            context_parts.append(f"  📂 Categoría: {product.get('categoria_nombre', 'N/A')}")
            if product.get('descripcion'):
                context_parts.append(f"  📝 {product['descripcion'][:100]}...")
        
        context_parts.append("\n⚠️ USA ESTA INFORMACIÓN PRIORITARIAMENTE")
        
        return "\n".join(context_parts)
    
    def _clean_response(self, response: str) -> str:
        """Limpia la respuesta eliminando formato markdown"""
        response = response.replace("**", "").replace("__", "").replace("~~", "")
        response = response.replace("###", "").replace("##", "").replace("#", "")
        response = response.strip()
        
        # Limitar longitud si es muy larga
        if len(response) > 600:
            cutoff = response[:550].rfind('.')
            if cutoff > 400:
                response = response[:cutoff + 1]
                response += "\n\n¿Te ayudo con algo más específico? 🤔"
        
        return response
    
    async def get_conversation_summary(self, user_id: str, chat_id: int = 0) -> Dict[str, Any]:
        """Obtiene resumen de conversación"""
        try:
            state = await self.get_conversation_state(user_id, chat_id)
            history = await self.persistence.get_conversation_history(user_id, chat_id, 5)
            
            return {
                "user_id": user_id,
                "chat_id": chat_id,
                "state": {
                    "phase": state.phase.value,
                    "level": state.level.value if state.level else None,
                    "budget_range": state.budget_range,
                    "message_count": state.message_count,
                    "interested_categories": state.interested_categories,
                    "was_greeted": state.was_greeted
                },
                "recent_messages": len(history),
                "last_activity": state.last_activity.isoformat() if state.last_activity else None
            }
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {"error": str(e)}
    
    async def reset_conversation(self, user_id: str, chat_id: int = 0) -> bool:
        """Reinicia conversación específica"""
        try:
            state_key = self._get_state_key(user_id, chat_id)
            if state_key in self.active_states:
                del self.active_states[state_key]
            
            # Marcar como inactiva en BD (no eliminar historial)
            state = ConversationState(user_id=user_id, chat_id=chat_id)
            await self.save_state(state)
            
            logger.info(f"Conversación reiniciada: {user_id}_{chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error reiniciando conversación: {e}")
            return False
    
    async def get_active_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene conversaciones activas"""
        try:
            connection = await get_async_connection()
            async with connection.cursor() as cursor:
                await cursor.execute("""
                    SELECT user_id, chat_id, name, level, message_count, last_activity
                    FROM conversation_states 
                    WHERE last_activity > DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    ORDER BY last_activity DESC
                    LIMIT %s
                """, (limit,))
                
                return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error obteniendo conversaciones activas: {e}")
            return []
        finally:
            if 'connection' in locals():
                await connection.ensure_closed()

# ==============================
# FUNCIONES DE UTILIDAD Y TESTING
# ==============================

async def test_agent():
    """Función de prueba del agente"""
    agent = EnhancedBaekhoAgent()
    
    test_messages = [
        "Hola, necesito un dobok",
        "Soy cinturón verde intermedio",
        "Mi presupuesto es de 500,000 pesos",
        "También necesito protecciones"
    ]
    
    user_info = {"user_id": "test_123", "chat_id": 456}
    
    for message in test_messages:
        print(f"\n👤 Usuario: {message}")
        response = await agent.process_message(message, user_info)
        print(f"🤖 BaekhoBot: {response}")
        await asyncio.sleep(0.5)
    
    # Mostrar resumen
    summary = await agent.get_conversation_summary("test_123", 456)
    print(f"\n📊 Resumen: {summary}")

def get_agent_instance() -> EnhancedBaekhoAgent:
    """Obtiene instancia singleton del agente"""
    if not hasattr(get_agent_instance, "_instance"):
        get_agent_instance._instance = EnhancedBaekhoAgent()
    return get_agent_instance._instance

# ==============================
# EXPORTACIONES
# ==============================

__all__ = [
    "EnhancedBaekhoAgent",
    "ConversationState", 
    "ConversationPersistence",
    "SimpleRAGService",
    "ConversationPhase",
    "UserLevel",
    "get_agent_instance",
    "test_agent"
]

# Para compatibilidad con imports existentes
BaekhoAgent = EnhancedBaekhoAgent
TaekwondoAgent = EnhancedBaekhoAgent

if __name__ == "__main__":
    # Ejecutar pruebas si se ejecuta directamente
    asyncio.run(test_agent())